from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "mcp" / "server.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_multi_mcp_app", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_uses_fast_local_endpoint(monkeypatch):
    module = load_module()
    seen = {}

    def fake_api(path, payload=None, timeout=120):
        seen["path"] = path
        return {"ok": True, "data": {"accounts": [], "projects": [], "orphan_secrets": []}}

    monkeypatch.setattr(module, "_api", fake_api)

    state = module._state()

    assert seen["path"] == "/api/state?local=1"
    assert state["projects"] == []


def test_project_public_never_exposes_raw_secret_fields():
    module = load_module()
    project = {
        "name": "example-prod",
        "project_ref": "abcdefghijklmnopqrst",
        "token_env": "SUPABASE_PAT_EXAMPLE",
        "token_ok": True,
        "token": "sbp_should_never_escape",
        "raw_pat": "sbp_should_never_escape_either",
    }

    public = module._project_public(project)

    assert public["token_env"] == "SUPABASE_PAT_EXAMPLE"
    assert public["token_ok"] is True
    assert "token" not in public
    assert "raw_pat" not in public


def test_account_public_never_exposes_raw_secret_fields():
    module = load_module()
    account = {
        "name": "company-main",
        "discovery_token_env": "SUPABASE_DISCOVERY_COMPANY",
        "discovery_token_ok": True,
        "token": "sbp_should_never_escape",
        "access_token": "secret",
    }

    public = module._account_public(account)

    assert public["discovery_token_env"] == "SUPABASE_DISCOVERY_COMPANY"
    assert public["discovery_token_ok"] is True
    assert "token" not in public
    assert "access_token" not in public


def test_destructive_actions_require_explicit_confirmation():
    module = load_module()

    with pytest.raises(RuntimeError, match="confirm=true"):
        module._require_confirmation(False, "Deleting project 'example-prod'")

    module._require_confirmation(True, "Deleting project 'example-prod'")


def test_live_capabilities_advertise_sql_operations(monkeypatch):
    module = load_module()
    current = {
        "app": "supabase-multi",
        "component": "local-control-plane",
        "source_fingerprint": module.source_fingerprint(),
    }
    monkeypatch.setattr(module, "_ensure_control_plane", lambda: None)
    monkeypatch.setattr(module, "_control_plane_runtime", lambda: current)

    caps = module.get_capabilities()

    names = {item["operation"] for item in caps["capabilities"]}
    assert "query_sql" in names
    assert "execute_sql" in names
    assert caps["generation"] == module.LIVE_CAPABILITY_GENERATION
    assert caps["runtime"]["control_plane_current"] is True


def test_live_gateway_routes_read_only_sql(monkeypatch):
    module = load_module()
    seen = {}

    def fake_api(path, payload=None, timeout=120):
        seen["path"] = path
        seen["payload"] = payload
        return {"ok": True, "result": {"content": []}}

    monkeypatch.setattr(module, "_api", fake_api)

    result = module._invoke_live_capability(
        "query_sql",
        {"target": "example-prod", "query": "select 1"},
        confirm=False,
    )

    assert seen["path"] == "/api/sql-query"
    assert seen["payload"] == {"project": "example-prod", "query": "select 1"}
    assert result["ok"] is True


def test_live_gateway_requires_confirmation_for_write(monkeypatch):
    module = load_module()

    with pytest.raises(RuntimeError, match="confirm=true"):
        module._invoke_live_capability(
            "execute_sql",
            {"target": "example-prod", "query": "update t set x=1"},
            confirm=False,
        )


def test_live_gateway_rejects_unknown_operation():
    module = load_module()

    with pytest.raises(RuntimeError, match="Unknown live capability"):
        module._invoke_live_capability("definitely_not_real", {}, confirm=False)


def test_runtime_fingerprint_detects_stale_control_plane(monkeypatch):
    module = load_module()
    current = module.source_fingerprint()

    assert module._runtime_is_current({
        "app": "supabase-multi",
        "source_fingerprint": current,
    }) is True

    assert module._runtime_is_current({
        "app": "supabase-multi",
        "source_fingerprint": "old-build",
    }) is False


def test_ensure_control_plane_restarts_stale_runtime(monkeypatch):
    module = load_module()
    expected = module.source_fingerprint()
    state = {
        "runtime": {
            "app": "supabase-multi",
            "source_fingerprint": "old-build",
        },
        "stopped": False,
        "started": False,
    }

    def fake_runtime():
        if state["started"]:
            return {
                "app": "supabase-multi",
                "source_fingerprint": expected,
            }
        if state["stopped"]:
            return None
        return state["runtime"]

    monkeypatch.setattr(module, "_control_plane_runtime", fake_runtime)
    monkeypatch.setattr(module, "_legacy_is_up", lambda: not state["stopped"] and not state["started"])

    def fake_stop():
        state["stopped"] = True

    monkeypatch.setattr(module, "_stop_stale_control_plane", fake_stop)
    monkeypatch.setattr(module.CONTROL_PLANE, "exists", lambda: True)

    class FakePopen:
        def __init__(self, *args, **kwargs):
            state["started"] = True

    monkeypatch.setattr(module.subprocess, "Popen", FakePopen)

    module._ensure_control_plane()

    assert state["stopped"] is True
    assert state["started"] is True
