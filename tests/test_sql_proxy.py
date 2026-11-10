from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "local-ui" / "server.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_multi_local_ui_sql", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def registry(read_only=False):
    return {
        "accounts": {"company-main": {"label": "Company main"}},
        "projects": {
            "example-prod": {
                "label": "Example",
                "account": "company-main",
                "project_ref": "abcdefghijklmnopqrst",
                "token_env": "SUPABASE_PAT_EXAMPLE",
                "read_only": read_only,
                "enabled": True,
            }
        },
    }


def test_query_sql_forces_downstream_read_only(monkeypatch):
    module = load_module()
    seen = []

    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_fake_for_test")

    def fake_post(token, payload, session_id=None, endpoint=module.MCP_URL):
        seen.append((token, payload, session_id, endpoint))
        if payload.get("method") == "initialize":
            return {"jsonrpc": "2.0", "id": 1, "result": {}}, "session-1"
        if payload.get("method") == "tools/call":
            return {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "content": [{"type": "text", "text": "[{\"answer\":42}]"}],
                    "structuredContent": {"rows": [{"answer": 42}]},
                },
            }, "session-1"
        return {"jsonrpc": "2.0", "result": {}}, "session-1"

    monkeypatch.setattr(module, "mcp_post", fake_post)

    result = module.execute_project_sql(registry(), "example-prod", "select 42 as answer", read_only=True)

    tool_call = next(x for x in seen if x[1].get("method") == "tools/call")
    assert tool_call[1]["params"]["name"] == "execute_sql"
    assert tool_call[1]["params"]["arguments"]["query"] == "select 42 as answer"
    assert "project_ref=abcdefghijklmnopqrst" in tool_call[3]
    assert "features=database" in tool_call[3]
    assert "read_only=true" in tool_call[3]
    assert "skip_elicitations" not in tool_call[3]
    assert result["read_only"] is True
    assert result["source"] == "official-supabase-mcp"
    assert "sbp_fake_for_test" not in repr(result)


def test_write_sql_refuses_read_only_target(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_fake_for_test")

    try:
        module.execute_project_sql(registry(read_only=True), "example-prod", "update t set x=1", read_only=False)
    except ValueError as exc:
        assert "configured read-only" in str(exc)
    else:
        raise AssertionError("write SQL should be blocked for a read-only target")


def test_write_sql_uses_outer_confirmation_path(monkeypatch):
    module = load_module()
    seen = []
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_fake_for_test")

    def fake_post(token, payload, session_id=None, endpoint=module.MCP_URL):
        seen.append(endpoint)
        if payload.get("method") == "initialize":
            return {"jsonrpc": "2.0", "id": 1, "result": {}}, "session-1"
        if payload.get("method") == "tools/call":
            return {"jsonrpc": "2.0", "id": 2, "result": {"content": []}}, "session-1"
        return {"jsonrpc": "2.0", "result": {}}, "session-1"

    monkeypatch.setattr(module, "mcp_post", fake_post)
    result = module.execute_project_sql(registry(read_only=False), "example-prod", "update t set x=1", read_only=False)

    assert result["read_only"] is False
    assert any("skip_elicitations=execute_sql" in endpoint for endpoint in seen)
    assert all("read_only=true" not in endpoint for endpoint in seen)
