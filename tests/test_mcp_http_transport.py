from __future__ import annotations

import importlib.util
import io
import urllib.error
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "mcp" / "headless_control_plane.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_multi_headless_http", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status, body=b"", headers=None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    def getcode(self):
        return self.status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_urllib_notification_202_is_recorded_without_body(monkeypatch):
    module = load_module()
    requests = []

    def fake_urlopen(req, timeout=40):
        requests.append(req)
        return FakeResponse(202, b"", {"Content-Type": ""})

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    payload, sid, meta = module.mcp_post(
        "secret-never-returned",
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        "session-1",
        endpoint="https://example.test/mcp",
        protocol_version="2025-06-18",
        return_meta=True,
    )

    headers = {k.lower(): v for k, v in requests[0].header_items()}
    assert payload == {}
    assert sid == "session-1"
    assert meta["status"] == 202
    assert meta["body_bytes"] == 0
    assert meta["request_session_id_present"] is True
    assert headers["mcp-protocol-version"] == "2025-06-18"
    assert headers["mcp-session-id"] == "session-1"
    assert headers["user-agent"] == module.MCP_USER_AGENT
    assert "secret-never-returned" not in repr(meta)


def test_urllib_http_error_is_available_as_phase_metadata(monkeypatch):
    module = load_module()

    def fake_urlopen(req, timeout=40):
        raise urllib.error.HTTPError(
            req.full_url,
            400,
            "Bad Request",
            {"Content-Type": "application/json"},
            io.BytesIO(
                b'{"jsonrpc":"2.0","error":{"code":-32000,"message":"not initialized"}}'
            ),
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    payload, sid, meta = module.mcp_post(
        "secret-never-returned",
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        "session-1",
        endpoint="https://example.test/mcp",
        return_meta=True,
    )

    assert sid == "session-1"
    assert meta["status"] == 400
    assert meta["http_error"].startswith("HTTP Error 400")
    assert payload["error"]["message"] == "not initialized"
    assert "secret-never-returned" not in repr(meta)
