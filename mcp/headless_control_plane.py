from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Path(os.environ.get("SUPABASE_MULTI_REGISTRY", ROOT / "registry.json"))
MCP_URL = "https://mcp.supabase.com/mcp"


def read_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {
            "version": 3,
            "defaults": {
                "read_only_production": True,
                "mcp_prefix": "sb_",
            },
            "accounts": {},
            "projects": {},
        }

    return json.loads(REGISTRY.read_text(encoding="utf-8-sig"))


def read_token_env_value(name: str) -> str:
    if not name:
        return ""

    return os.environ.get(name, "").strip()


def mcp_post(
    token: str,
    payload: dict[str, Any],
    session_id: str | None = None,
    endpoint: str = MCP_URL,
):
    body = json.dumps(payload).encode()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18",
    }

    if session_id:
        headers["Mcp-Session-Id"] = session_id

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=40) as resp:
        text = resp.read().decode("utf-8", errors="replace")
        sid = resp.headers.get("Mcp-Session-Id") or session_id

    if "data:" in text:
        events = []

        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[5:].strip()))
                except Exception:
                    pass

        return (events[-1] if events else {}), sid

    try:
        return json.loads(text), sid
    except Exception:
        return {}, sid


def _mcp_error_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "Unknown MCP error."

    err = payload.get("error")

    if isinstance(err, dict):
        return str(err.get("message") or err)

    if err:
        return str(err)

    return ""


def _mcp_text_content(result: Any) -> str:
    texts = []

    for item in (result or {}).get("content", []) or []:
        if isinstance(item, dict) and item.get("type") == "text":
            texts.append(str(item.get("text", "")))

    return "\n".join(x for x in texts if x)


def execute_project_sql(
    project_name: str,
    query: str,
    read_only: bool = True,
) -> dict[str, Any]:
    project_name = (project_name or "").strip()
    query = (query or "").strip()

    if not project_name:
        raise ValueError("Project target is required.")

    if not query:
        raise ValueError("SQL query is required.")

    if len(query) > 100000:
        raise ValueError("SQL query is too large.")

    reg = read_registry()
    project = reg.get("projects", {}).get(project_name)

    if not project:
        raise ValueError("Project not found.")

    if not project.get("enabled", True):
        raise ValueError("Project target is disabled.")

    if not read_only and bool(project.get("read_only", False)):
        raise ValueError(
            "Project target is configured read-only; SQL writes are blocked."
        )

    project_ref = (project.get("project_ref") or "").strip()
    token_env = (project.get("token_env") or "").strip()

    if not project_ref:
        raise ValueError("Project ref is not configured.")

    if not token_env:
        raise ValueError("Project token_env is not configured.")

    token = read_token_env_value(token_env)

    if not token:
        raise ValueError(
            f"No PAT found in environment variable {token_env}."
        )

    params = {
        "project_ref": project_ref,
        "features": "database",
    }

    if read_only:
        params["read_only"] = "true"
    else:
        params["skip_elicitations"] = "execute_sql"

    endpoint = MCP_URL + "?" + urllib.parse.urlencode(params)

    init, sid = mcp_post(
        token,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "supabase-multi-headless",
                    "version": "0.1",
                },
            },
        },
        endpoint=endpoint,
    )

    msg = _mcp_error_message(init)

    if msg:
        raise RuntimeError("Supabase MCP initialize failed: " + msg)

    try:
        mcp_post(
            token,
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
            sid,
            endpoint=endpoint,
        )
    except Exception:
        pass

    payload, sid = mcp_post(
        token,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "execute_sql",
                "arguments": {
                    "query": query,
                },
            },
        },
        sid,
        endpoint=endpoint,
    )

    msg = _mcp_error_message(payload)

    if msg:
        raise RuntimeError("Supabase MCP execute_sql failed: " + msg)

    result = (payload or {}).get("result", {}) or {}

    if result.get("isError"):
        detail = (
            _mcp_text_content(result)
            or "Supabase MCP execute_sql returned an error."
        )
        raise RuntimeError(detail)

    return {
        "project": project_name,
        "project_ref": project_ref,
        "read_only": bool(read_only),
        "source": "official-supabase-mcp",
        "content": result.get("content", []),
        "structured_content": result.get("structuredContent"),
    }