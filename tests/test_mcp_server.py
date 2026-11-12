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

    class FakeBridge:
        def state(self):
            seen["called"] = True
            return {"accounts": [], "projects": [], "orphan_secrets": []}

    monkeypatch.setattr(module, "_runtime_bridge", lambda: FakeBridge())

    state = module._state()

    assert seen["called"] is True
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
    assert "list_edge_functions" in names
    assert "get_edge_function" in names
    assert "deploy_edge_function" in names
    assert "delete_edge_function" in names
    assert caps["generation"] == "2026-11-12.1"
    assert caps["runtime"]["control_plane_current"] is True


def test_live_gateway_routes_read_only_sql(monkeypatch):
    module = load_module()
    seen = {}

    class FakeBridge:
        def invoke_live_capability(self, operation, arguments, confirm=False):
            seen["operation"] = operation
            seen["arguments"] = arguments
            seen["confirm"] = confirm
            return {"ok": True, "result": {"content": []}}

    monkeypatch.setattr(module, "_runtime_bridge", lambda: FakeBridge())

    result = module._invoke_live_capability(
        "query_sql",
        {"target": "example-prod", "query": "select 1"},
        confirm=False,
    )

    assert seen["operation"] == "query_sql"
    assert seen["arguments"] == {"target": "example-prod", "query": "select 1"}
    assert seen["confirm"] is False
    assert result["ok"] is True


def test_live_gateway_requires_confirmation_for_write(monkeypatch):
    module = load_module()

    with pytest.raises(RuntimeError, match="confirm=true"):
        module._invoke_live_capability(
            "execute_sql",
            {"target": "example-prod", "query": "update t set x=1"},
            confirm=False,
        )


def test_edge_function_writes_require_confirmation():
    module = load_module()

    with pytest.raises(RuntimeError, match="confirm=true"):
        module._invoke_live_capability(
            "deploy_edge_function",
            {
                "target": "example-prod",
                "name": "hello-world",
                "files": [{"name": "index.ts", "content": "Deno.serve(() => new Response())"}],
            },
            confirm=False,
        )

    with pytest.raises(RuntimeError, match="confirm=true"):
        module._invoke_live_capability(
            "delete_edge_function",
            {
                "target": "example-prod",
                "function_slug": "hello-world",
            },
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

    class FakeControlPlane:
        def exists(self):
            return True
        def __str__(self):
            return "fake-control-plane.py"

    monkeypatch.setattr(module, "CONTROL_PLANE", FakeControlPlane())

    class FakePopen:
        def __init__(self, *args, **kwargs):
            state["started"] = True

    monkeypatch.setattr(module.subprocess, "Popen", FakePopen)

    module._ensure_control_plane()

    assert state["stopped"] is True
    assert state["started"] is True


def test_runtime_bridge_hot_reloads_without_reimporting_mcp_server(monkeypatch, tmp_path):
    module = load_module()
    bridge = tmp_path / "runtime_bridge.py"
    bridge.write_text(
        "def api(path, payload=None, timeout=120):\n"
        "    return {'ok': True, 'version': 1}\n"
        "def state():\n"
        "    return {'projects': []}\n"
        "def get_capabilities():\n"
        "    return {'generation': 'one', 'capabilities': []}\n"
        "def invoke_live_capability(operation, arguments, confirm=False):\n"
        "    return {'version': 1}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "RUNTIME_BRIDGE", bridge)
    module._runtime_bridge_module = None
    module._runtime_bridge_stamp = None

    first = module._api("/anything")
    assert first["version"] == 1

    bridge.write_text(
        "def api(path, payload=None, timeout=120):\n"
        "    return {'ok': True, 'version': 2}\n"
        "def state():\n"
        "    return {'projects': []}\n"
        "def get_capabilities():\n"
        "    return {'generation': 'two', 'capabilities': []}\n"
        "def invoke_live_capability(operation, arguments, confirm=False):\n"
        "    return {'version': 2}\n",
        encoding="utf-8",
    )

    second = module._api("/anything")
    assert second["version"] == 2
    assert module.get_capabilities()["generation"] == "two"
