from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "mcp" / "headless_control_plane.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_multi_headless_edge", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_project(monkeypatch, module, *, read_only=False):
    registry = {
        "projects": {
            "example-prod": {
                "enabled": True,
                "read_only": read_only,
                "project_ref": "abcdefghijklmnopqrst",
                "token_env": "SUPABASE_PAT_EXAMPLE",
            }
        }
    }
    monkeypatch.setattr(module, "read_registry", lambda: registry)
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "sbp_test_token")
    return registry


def fake_mcp_lifecycle(monkeypatch, module, expected_tool, expected_arguments):
    seen = []
    responses = [
        (
            {"result": {"protocolVersion": module.MCP_PROTOCOL_VERSION}},
            "session-123",
            {
                "status": 200,
                "content_type": "application/json",
                "request_protocol_version": module.MCP_PROTOCOL_VERSION,
                "request_session_id_present": False,
                "response_session_id_present": True,
                "body_bytes": 10,
                "http_error": "",
            },
        ),
        (
            {},
            "session-123",
            {
                "status": 202,
                "content_type": "text/plain",
                "request_protocol_version": module.MCP_PROTOCOL_VERSION,
                "request_session_id_present": True,
                "response_session_id_present": False,
                "body_bytes": 0,
                "http_error": "",
            },
        ),
        (
            {
                "result": {
                    "content": [{"type": "text", "text": "ok"}],
                    "structuredContent": {"ok": True},
                }
            },
            "session-123",
            {
                "status": 200,
                "content_type": "application/json",
                "request_protocol_version": module.MCP_PROTOCOL_VERSION,
                "request_session_id_present": True,
                "response_session_id_present": False,
                "body_bytes": 10,
                "http_error": "",
            },
        ),
    ]

    def fake_post(token, payload, session_id=None, endpoint=None, **kwargs):
        seen.append(
            {
                "token": token,
                "payload": payload,
                "session_id": session_id,
                "endpoint": endpoint,
                "kwargs": kwargs,
            }
        )
        return responses[len(seen) - 1]

    monkeypatch.setattr(module, "mcp_post", fake_post)

    def assert_seen(*, write):
        assert len(seen) == 3
        assert seen[0]["payload"]["method"] == "initialize"
        assert seen[1]["payload"]["method"] == "notifications/initialized"
        assert seen[2]["payload"]["method"] == "tools/call"
        assert seen[2]["payload"]["params"]["name"] == expected_tool
        assert seen[2]["payload"]["params"]["arguments"] == expected_arguments
        assert "project_ref=abcdefghijklmnopqrst" in seen[0]["endpoint"]
        if write:
            assert "read_only=true" not in seen[0]["endpoint"]
        else:
            assert "read_only=true" in seen[0]["endpoint"]

    return assert_seen


def test_list_edge_functions_routes_to_official_mcp(monkeypatch):
    module = load_module()
    install_project(monkeypatch, module)
    assert_seen = fake_mcp_lifecycle(monkeypatch, module, "list_edge_functions", {})

    result = module.list_edge_functions("example-prod")

    assert result["source"] == "official-supabase-mcp"
    assert result["tool"] == "list_edge_functions"
    assert_seen(write=False)


def test_get_edge_function_routes_slug(monkeypatch):
    module = load_module()
    install_project(monkeypatch, module)
    assert_seen = fake_mcp_lifecycle(
        monkeypatch,
        module,
        "get_edge_function",
        {"function_slug": "hello-world"},
    )

    result = module.get_edge_function("example-prod", "hello-world")

    assert result["tool"] == "get_edge_function"
    assert_seen(write=False)


def test_deploy_edge_function_routes_exact_official_arguments(monkeypatch):
    module = load_module()
    install_project(monkeypatch, module)
    files = [
        {
            "name": "index.ts",
            "content": 'Deno.serve(() => new Response("ok"))',
        }
    ]
    expected = {
        "name": "hello-world",
        "entrypoint_path": "index.ts",
        "files": files,
        "verify_jwt": True,
    }
    assert_seen = fake_mcp_lifecycle(
        monkeypatch,
        module,
        "deploy_edge_function",
        expected,
    )

    result = module.deploy_edge_function(
        "example-prod",
        "hello-world",
        files,
        entrypoint_path="index.ts",
        verify_jwt=True,
    )

    assert result["tool"] == "deploy_edge_function"
    assert_seen(write=True)


def test_deploy_edge_function_refuses_read_only_target(monkeypatch):
    module = load_module()
    install_project(monkeypatch, module, read_only=True)

    with pytest.raises(ValueError, match="read-only"):
        module.deploy_edge_function(
            "example-prod",
            "hello-world",
            [{"name": "index.ts", "content": "Deno.serve(() => new Response())"}],
        )


def test_delete_edge_function_uses_management_api(monkeypatch):
    module = load_module()
    install_project(monkeypatch, module)
    seen = {}

    def fake_http_json(url, token, *, method="GET", payload=None, timeout=40):
        seen["url"] = url
        seen["token"] = token
        seen["method"] = method
        seen["payload"] = payload
        return {}

    monkeypatch.setattr(module, "_http_json", fake_http_json)

    result = module.delete_edge_function("example-prod", "hello world")

    assert seen["method"] == "DELETE"
    assert seen["token"] == "sbp_test_token"
    assert seen["url"].endswith(
        "/projects/abcdefghijklmnopqrst/functions/hello%20world"
    )
    assert result["deleted"] is True
    assert result["source"] == "supabase-management-api"


def test_delete_edge_function_refuses_read_only_target(monkeypatch):
    module = load_module()
    install_project(monkeypatch, module, read_only=True)

    with pytest.raises(ValueError, match="read-only"):
        module.delete_edge_function("example-prod", "hello-world")
