from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from runtime_identity import runtime_payload, source_fingerprint

CONTROL_PLANE = ROOT / "local-ui" / "server.py"
BASE_URL = os.environ.get("SUPABASE_MULTI_URL", "http://127.0.0.1:8765").rstrip("/")
LIVE_CAPABILITY_GENERATION = "2026-11-11.2"

LIVE_CAPABILITIES: dict[str, dict[str, Any]] = {
    "query_sql": {
        "description": "Run SQL through the official Supabase MCP in forced read-only mode.",
        "confirmation_required": False,
        "write_capable": False,
    },
    "execute_sql": {
        "description": "Run write-capable SQL through the official Supabase MCP.",
        "confirmation_required": True,
        "write_capable": True,
    },
}

_control_plane_proc: subprocess.Popen | None = None


def _use_headless_backend() -> bool:
    return os.environ.get("SUPABASE_MULTI_BACKEND", "local").strip().lower() == "headless"


def _headless_module():
    import headless_control_plane
    return importlib.reload(headless_control_plane)


def _json_request(path: str, payload: dict[str, Any] | None = None, timeout: int = 120) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = None
    method = "GET"
    headers = {"Accept": "application/json"}
    if payload is not None:
        method = "POST"
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            out = json.loads(raw)
            msg = out.get("message") or out.get("error") or raw
        except Exception:
            msg = raw or str(e)
        raise RuntimeError(msg) from e
    if not out.get("ok", False):
        raise RuntimeError(out.get("message") or out.get("error") or "Supabase Multi request failed.")
    return out


def _legacy_is_up() -> bool:
    try:
        _json_request("/api/state?local=1", timeout=2)
        return True
    except Exception:
        return False


def _control_plane_runtime() -> dict[str, Any] | None:
    try:
        out = _json_request("/api/runtime", timeout=2)
        runtime = out.get("runtime")
        return runtime if isinstance(runtime, dict) else None
    except Exception:
        return None


def _runtime_is_current(runtime: dict[str, Any] | None) -> bool:
    return bool(
        runtime
        and runtime.get("app") == "supabase-multi"
        and runtime.get("source_fingerprint") == source_fingerprint()
    )


def _stop_stale_control_plane() -> None:
    try:
        _json_request("/api/shutdown", {}, timeout=3)
    except Exception:
        if os.name == "nt" and BASE_URL == "http://127.0.0.1:8765":
            command = (
                "$c=Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue;"
                "if($c){$c|ForEach-Object{Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue}}"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                timeout=10,
            )
    deadline = time.time() + 4
    while time.time() < deadline and _legacy_is_up():
        time.sleep(0.1)


def _ensure_control_plane() -> None:
    global _control_plane_proc
    runtime = _control_plane_runtime()
    if _runtime_is_current(runtime):
        return

    if runtime is not None or _legacy_is_up():
        _stop_stale_control_plane()

    if not CONTROL_PLANE.exists():
        raise RuntimeError(f"Supabase Multi control plane not found at {CONTROL_PLANE}")

    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    _control_plane_proc = subprocess.Popen(
        [sys.executable, str(CONTROL_PLANE)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )

    deadline = time.time() + 12
    while time.time() < deadline:
        runtime = _control_plane_runtime()
        if _runtime_is_current(runtime):
            return
        time.sleep(0.25)

    raise RuntimeError(
        "Supabase Multi control plane did not start with the current runtime fingerprint."
    )


def api(path: str, payload: dict[str, Any] | None = None, timeout: int = 120) -> dict[str, Any]:
    if _use_headless_backend():
        return _headless_module().handle_api(path, payload or {})
    _ensure_control_plane()
    return _json_request(path, payload, timeout=timeout)


def state() -> dict[str, Any]:
    return api("/api/state?local=1")["data"]


def _require_confirmation(confirm: bool, action: str) -> None:
    if not confirm:
        raise RuntimeError(
            f"{action} is destructive. Call the tool again with confirm=true only after the user explicitly approves it."
        )


def get_capabilities() -> dict[str, Any]:
    if _use_headless_backend():
        local_runtime = None
        control_plane_current = True
    else:
        _ensure_control_plane()
        local_runtime = _control_plane_runtime()
        control_plane_current = _runtime_is_current(local_runtime)

    return {
        "server_version": "0.2.0",
        "generation": LIVE_CAPABILITY_GENERATION,
        "runtime": {
            "bridge": runtime_payload("runtime-bridge"),
            "control_plane": local_runtime,
            "control_plane_current": control_plane_current,
        },
        "capabilities": [
            {"operation": name, **meta}
            for name, meta in sorted(LIVE_CAPABILITIES.items())
        ],
        "note": (
            "Capabilities and execution logic are loaded from the hot-reload runtime bridge. "
            "Changing tool schemas still requires reconnecting the MCP client."
        ),
    }


def invoke_live_capability(
    operation: str,
    arguments: dict[str, Any],
    confirm: bool = False,
) -> dict[str, Any]:
    operation = (operation or "").strip()
    if operation not in LIVE_CAPABILITIES:
        raise RuntimeError(
            f"Unknown live capability '{operation}'. Call get_capabilities first and use one of the advertised operations."
        )
    arguments = arguments or {}

    if operation == "query_sql":
        target = str(arguments.get("target") or "").strip()
        query = str(arguments.get("query") or "")
        if not target or not query.strip():
            raise RuntimeError("query_sql requires arguments.target and arguments.query.")
        return api("/api/sql-query", {"project": target, "query": query})

    if operation == "execute_sql":
        _require_confirmation(confirm, "Executing write-capable SQL through the live capability gateway")
        target = str(arguments.get("target") or "").strip()
        query = str(arguments.get("query") or "")
        if not target or not query.strip():
            raise RuntimeError("execute_sql requires arguments.target and arguments.query.")
        return api("/api/sql-execute", {"project": target, "query": query, "confirm": True})

    raise RuntimeError(f"Live capability '{operation}' is advertised but not implemented.")
