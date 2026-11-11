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


def _fake_post_factory(module, seen):
    def fake_post(
        token,
        payload,
        session_id=None,
        endpoint=module.MCP_URL,
        *,
        protocol_version=module.MCP_PROTOCOL_VERSION,
        return_meta=False,
    ):
        method = payload.get("method")
        status = 202 if method == "notifications/initialized" else 200
        seen.append((token, payload, session_id, endpoint, protocol_version, status))

        if method == "initialize":
            result = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"protocolVersion": module.MCP_PROTOCOL_VERSION},
            }
            sid = "session-1"
        elif method == "tools/call":
            result = {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "content": [{"type": "text", "text": "[{\"answer\":42}]"}],
                    "structuredContent": {"rows": [{"answer": 42}]},
                },
            }
            sid = session_id or "session-1"
        else:
            result = {}
            sid = session_id or "session-1"

        meta = {
            "method": method,
            "status": status,
            "content_type": "" if status == 202 else "application/json",
            "request_protocol_version": protocol_version,
            "request_session_id_present": bool(session_id),
            "response_session_id_present": method == "initialize",
            "body_bytes": 0 if status == 202 else 2,
            "user_agent": module.MCP_USER_AGENT,
            "http_error": "",
        }
        return (result, sid, meta) if return_meta else (result, sid)

    return fake_post


def test_query_sql_forces_downstream_read_only(monkeypatch):
    module = load_module()
    seen = []
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_fake_for_test")
    monkeypatch.setattr(module, "mcp_post", _fake_post_factory(module, seen))

    result = module.execute_project_sql(
        registry(), "example-prod", "select 42 as answer", read_only=True
    )

    tool_call = next(x for x in seen if x[1].get("method") == "tools/call")
    initialized = next(
        x for x in seen if x[1].get("method") == "notifications/initialized"
    )
    assert tool_call[1]["params"]["name"] == "execute_sql"
    assert tool_call[1]["params"]["arguments"]["query"] == "select 42 as answer"
    assert "project_ref=abcdefghijklmnopqrst" in tool_call[3]
    assert "features=database" in tool_call[3]
    assert "read_only=true" in tool_call[3]
    assert "skip_elicitations" not in tool_call[3]
    assert initialized[5] == 202
    assert tool_call[4] == module.MCP_PROTOCOL_VERSION
    assert result["read_only"] is True
    assert result["source"] == "official-supabase-mcp"
    assert result["mcp_transport"]["initialize"]["status"] == 200
    assert result["mcp_transport"]["notifications_initialized"]["status"] == 202
    assert result["mcp_transport"]["tools_call"]["status"] == 200
    assert "sbp_fake_for_test" not in repr(result)


def test_write_sql_refuses_read_only_target(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_fake_for_test")

    try:
        module.execute_project_sql(
            registry(read_only=True),
            "example-prod",
            "update t set x=1",
            read_only=False,
        )
    except ValueError as exc:
        assert "configured read-only" in str(exc)
    else:
        raise AssertionError("write SQL should be blocked for a read-only target")


def test_write_sql_uses_outer_confirmation_path(monkeypatch):
    module = load_module()
    seen = []
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_fake_for_test")
    monkeypatch.setattr(module, "mcp_post", _fake_post_factory(module, seen))

    result = module.execute_project_sql(
        registry(read_only=False),
        "example-prod",
        "update t set x=1",
        read_only=False,
    )

    assert result["read_only"] is False
    assert any("skip_elicitations=execute_sql" in item[3] for item in seen)
    assert all("read_only=true" not in item[3] for item in seen)


def test_initialized_failure_is_not_swallowed(monkeypatch):
    module = load_module()
    seen = []
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_fake_for_test")
    base = _fake_post_factory(module, seen)

    def failing_post(*args, **kwargs):
        payload = args[1]
        if payload.get("method") == "notifications/initialized":
            result = {}
            sid = args[2] if len(args) > 2 else kwargs.get("session_id")
            meta = {
                "method": "notifications/initialized",
                "status": 400,
                "content_type": "application/json",
                "request_protocol_version": kwargs.get(
                    "protocol_version", module.MCP_PROTOCOL_VERSION
                ),
                "request_session_id_present": bool(sid),
                "response_session_id_present": False,
                "body_bytes": 0,
                "user_agent": module.MCP_USER_AGENT,
                "http_error": "HTTP Error 400: Bad Request",
            }
            return (result, sid, meta)
        return base(*args, **kwargs)

    monkeypatch.setattr(module, "mcp_post", failing_post)

    try:
        module.execute_project_sql(
            registry(read_only=False),
            "example-prod",
            "update t set x=1",
            read_only=False,
        )
    except RuntimeError as exc:
        text = str(exc)
        assert "notifications/initialized failed" in text
        assert "http_status=400" in text
    else:
        raise AssertionError("initialized notification failure must stop tools/call")
