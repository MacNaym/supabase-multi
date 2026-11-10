from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "local-ui" / "server.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_multi_local_ui", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_state_skips_all_remote_status_checks(monkeypatch, tmp_path):
    module = load_module()
    registry = {
        "version": 2,
        "defaults": {"mcp_prefix": "sb_"},
        "accounts": {
            "company-main": {
                "label": "Company main",
                "email": "admin@example.com",
                "login_method": "github",
                "browser": "default",
                "discovery_token_env": "",
                "cli_profile_managed": False,
                "enabled": True,
            }
        },
        "projects": {
            "example-prod": {
                "label": "Example production",
                "account": "company-main",
                "project_ref": "abcdefghijklmnopqrst",
                "environment": "production",
                "read_only": False,
                "token_env": "SUPABASE_PAT_EXAMPLE",
                "enabled": True,
            }
        },
    }

    monkeypatch.setattr(module, "read_registry", lambda: registry)
    monkeypatch.setattr(module, "migrate_legacy_cli_profile_flags", lambda reg: reg)
    monkeypatch.setattr(module, "browser_profile_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(module, "env_exists", lambda name: False)
    monkeypatch.setattr(module, "orphaned_supabase_secret_envs", lambda reg: [])

    def remote_call_is_a_regression(*args, **kwargs):
        raise AssertionError("local state must not perform remote Supabase or CLI checks")

    monkeypatch.setattr(module, "build_platform_status_cache", remote_call_is_a_regression)
    monkeypatch.setattr(module, "cli_profile_status", remote_call_is_a_regression)
    monkeypatch.setattr(module, "project_status_from_pat", remote_call_is_a_regression)

    state = module.state_payload(check_remote=False)

    assert len(state["accounts"]) == 1
    assert len(state["projects"]) == 1
    assert state["accounts"][0]["oauth_connected"] is False
    assert state["projects"][0]["platform_status"] == "UNKNOWN"
    assert state["projects"][0]["platform_seen"] is False
    assert state["projects"][0]["status_source"] == "NONE"
    assert state["projects"][0]["pat_status_error_kind"] == "NOT_CHECKED"
