from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

MCP_DIR = Path(__file__).resolve().parent
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from headless_control_plane import (
    execute_project_sql as execute_project_sql_headless,
    handle_api as headless_api,
)

ROOT = Path(__file__).resolve().parent.parent
CONTROL_PLANE = ROOT / "local-ui" / "server.py"
BASE_URL = os.environ.get("SUPABASE_MULTI_URL", "http://127.0.0.1:8765").rstrip("/")

mcp = MCPServer(
    "supabase-multi",
    title="Supabase Multi",
    description="A local Supabase control plane for humans and AI agents managing multiple accounts and projects.",
    instructions=(
        "Use Supabase Multi whenever more than one Supabase account or project may exist. "
        "Never guess a target, account, project_ref, PAT environment variable, or Supabase MCP server. "
        "Resolve the project first. If resolution is ambiguous, do not choose a candidate yourself; "
        "surface the candidates so the user can confirm the intended account/project. "
        "Never request, print, or return raw PAT values."
    ),
    version="0.2.0",
)

_control_plane_proc: subprocess.Popen | None = None


def _use_headless_backend() -> bool:
    return os.environ.get("SUPABASE_MULTI_BACKEND", "local").strip().lower() == "headless"


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


def _is_up() -> bool:
    try:
        _json_request("/api/state?local=1", timeout=2)
        return True
    except Exception:
        return False


def _ensure_control_plane() -> None:
    global _control_plane_proc
    if _is_up():
        return
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
        if _is_up():
            return
        time.sleep(0.25)
    raise RuntimeError("Supabase Multi control plane did not start on 127.0.0.1:8765.")


def _api(path: str, payload: dict[str, Any] | None = None, timeout: int = 120) -> dict[str, Any]:
    if _use_headless_backend():
        return headless_api(path, payload or {})
    _ensure_control_plane()
    return _json_request(path, payload, timeout=timeout)

def _state() -> dict[str, Any]:
    return _api("/api/state?local=1")["data"]


def _project_public(p: dict[str, Any]) -> dict[str, Any]:
    # The API state never contains raw PAT values. Keep the MCP contract explicit.
    allowed = {
        "name","label","account","account_email","browser","login_method","project_ref","environment",
        "enabled","read_only","token_env","token_ok","mcp","platform_status","platform_seen",
        "status_source","pat_status_error_kind","pat_status_error_detail"
    }
    return {k: p.get(k) for k in allowed if k in p}


def _account_public(a: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "name","label","email","browser","login_method","oauth_connected","platform_check_ok",
        "platform_check_error","enabled","identity_complete","used_by","discovery_token_env",
        "discovery_token_ok","browser_profile_ready"
    }
    return {k: a.get(k) for k in allowed if k in a}


def _require_confirmation(confirm: bool, action: str) -> None:
    if not confirm:
        raise RuntimeError(
            f"{action} is destructive. Call the tool again with confirm=true only after the user explicitly approves it."
        )


LIVE_CAPABILITY_GENERATION = "2026-11-11.1"

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


def _invoke_live_capability(operation: str, arguments: dict[str, Any], confirm: bool = False) -> dict[str, Any]:
    operation=(operation or "").strip()
    if operation not in LIVE_CAPABILITIES:
        raise RuntimeError(
            f"Unknown live capability '{operation}'. Call get_capabilities first and use one of the advertised operations."
        )
    arguments = arguments or {}

    if operation == "query_sql":
        target=str(arguments.get("target") or "").strip()
        query=str(arguments.get("query") or "")
        if not target or not query.strip():
            raise RuntimeError("query_sql requires arguments.target and arguments.query.")
        if _use_headless_backend():
            return execute_project_sql_headless(target, query, read_only=True)
        return _api("/api/sql-query", {"project": target, "query": query})

    if operation == "execute_sql":
        _require_confirmation(confirm, "Executing write-capable SQL through the live capability gateway")
        target=str(arguments.get("target") or "").strip()
        query=str(arguments.get("query") or "")
        if not target or not query.strip():
            raise RuntimeError("execute_sql requires arguments.target and arguments.query.")
        if _use_headless_backend():
            return execute_project_sql_headless(target, query, read_only=False)
        return _api("/api/sql-execute", {"project": target, "query": query, "confirm": True})

    raise RuntimeError(f"Live capability '{operation}' is advertised but not implemented.")


@mcp.tool()
def get_capabilities() -> dict[str, Any]:
    """Return the server's live capability registry. Use this when plugin metadata may be stale after a Supabase Multi update."""
    return {
        "server_version": "0.2.0",
        "generation": LIVE_CAPABILITY_GENERATION,
        "capabilities": [
            {"operation": name, **meta}
            for name, meta in sorted(LIVE_CAPABILITIES.items())
        ],
        "note": (
            "These capabilities are discovered live from the running Supabase Multi server. "
            "They can be invoked through invoke_capability without changing that tool's schema."
        ),
    }


@mcp.tool()
def invoke_capability(
    operation: str,
    arguments: dict[str, Any],
    confirm: bool = False,
) -> dict[str, Any]:
    """Invoke one operation returned by get_capabilities. Write-capable operations require explicit confirm=true."""
    return _invoke_live_capability(operation, arguments, confirm=confirm)


@mcp.tool()
def get_dashboard() -> dict[str, Any]:
    """Return a sanitized operational summary: database states, account connectivity, PAT coverage and orphaned-secret count."""
    s = _state()
    projects = s.get("projects", [])
    accounts = s.get("accounts", [])
    active = sum(1 for p in projects if str(p.get("platform_status","")).upper() == "ACTIVE")
    paused = sum(1 for p in projects if str(p.get("platform_status","")).upper() == "PAUSED")
    unknown = sum(1 for p in projects if str(p.get("platform_status","")).upper() in {"UNKNOWN","ERROR"} or not p.get("platform_seen"))
    return {
        "databases": {"total": len(projects), "active": active, "paused": paused, "unknown_or_error": unknown},
        "accounts": {"total": len(accounts), "cli_connected": sum(1 for a in accounts if a.get("oauth_connected"))},
        "project_pats": {"configured": sum(1 for p in projects if p.get("token_ok")), "total": len(projects)},
        "orphaned_secrets": len(s.get("orphan_secrets", [])),
        "checked_at": s.get("platform_checked_at"),
    }


@mcp.tool()
def list_accounts() -> list[dict[str, Any]]:
    """List all configured Supabase accounts without returning any secret values."""
    return [_account_public(a) for a in _state().get("accounts", [])]


@mcp.tool()
def get_account(account: str) -> dict[str, Any]:
    """Get one configured account by alias. Returns metadata only, never credentials."""
    for a in _state().get("accounts", []):
        if a.get("name") == account:
            return _account_public(a)
    raise RuntimeError(f"Account '{account}' not found.")


@mcp.tool()
def list_projects(account: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    """List configured projects, optionally filtered by account alias and/or normalized Supabase status."""
    items = [_project_public(p) for p in _state().get("projects", [])]
    if account:
        items = [p for p in items if p.get("account") == account]
    if status:
        q=status.upper()
        items = [p for p in items if str(p.get("platform_status","")).upper() == q]
    return items


@mcp.tool()
def get_project(target: str) -> dict[str, Any]:
    """Get one configured project by exact Supabase Multi target name."""
    for p in _state().get("projects", []):
        if p.get("name") == target:
            return _project_public(p)
    raise RuntimeError(f"Project target '{target}' not found.")


@mcp.tool()
def resolve_project(
    repo_path: str | None = None,
    name: str | None = None,
    target: str | None = None,
    project_ref: str | None = None,
    account: str | None = None,
) -> dict[str, Any]:
    """
    Resolve the intended Supabase project from repo path, project name/label, exact target, project_ref, or account.
    Never guess. A result with status='ambiguous' means the agent must ask the user which candidate to use.
    """
    return _api("/api/resolve", {
        "repo_path": repo_path or "",
        "name": name or "",
        "target": target or "",
        "project_ref": project_ref or "",
        "account": account or "",
    })


@mcp.tool()
def verify_access(target: str) -> dict[str, Any]:
    """Verify access to one project. Tries the project PAT first and falls back to the associated named CLI profile."""
    return _api("/api/project-pat-check", {"project": target})


@mcp.tool()
def query_sql(target: str, query: str) -> dict[str, Any]:
    """Run SQL through the official Supabase MCP in forced read-only mode for one exact Supabase Multi target."""
    if _use_headless_backend():
        return execute_project_sql_headless(target, query, read_only=True)
    return _api("/api/sql-query", {"project": target, "query": query})


@mcp.tool()
def execute_sql(target: str, query: str, confirm: bool = False) -> dict[str, Any]:
    """Run SQL that may write to the database. Requires explicit confirm=true and refuses targets configured read-only."""
    _require_confirmation(confirm, f"Executing write-capable SQL on '{target}'")

    if _use_headless_backend():
        return execute_project_sql_headless(target, query, read_only=False)

    return _api("/api/sql-execute", {"project": target, "query": query, "confirm": True})

@mcp.tool()
def sync_mcp() -> dict[str, Any]:
    """Synchronize all configured Supabase project targets into the local MCP configuration."""
    return _api("/api/sync", {})


@mcp.tool()
def doctor() -> dict[str, Any]:
    """Run Supabase Multi diagnostics over registry, environment, CLI and MCP configuration."""
    return _api("/api/doctor", {})


@mcp.tool()
def sync_and_doctor() -> dict[str, Any]:
    """Synchronize MCP targets and immediately run diagnostics."""
    return _api("/api/sync-doctor", {})


@mcp.tool()
def open_project(target: str) -> dict[str, Any]:
    """Open the Supabase Dashboard for a target using the isolated browser profile of its configured account."""
    return _api("/api/open-project", {"project": target})


@mcp.tool()
def discover_account(account: str, mode: str = "cli") -> dict[str, Any]:
    """
    Discover Supabase projects visible to an account.
    mode='cli' uses the account's named Supabase CLI profile; mode='pat' uses its account-wide Discovery PAT.
    """
    api_mode = "oauth" if mode.lower() in {"cli","oauth"} else "pat"
    return _api("/api/discover", {"account": account, "mode": api_mode})


@mcp.tool()
def create_or_update_account(
    name: str,
    label: str = "",
    email: str = "",
    login_method: str = "unknown",
    browser: str = "default",
    discovery_token_env: str = "",
    enabled: bool = True,
    original_name: str = "",
) -> dict[str, Any]:
    """Create or update account metadata. This never accepts or returns a PAT value."""
    return _api("/api/account", {
        "name": name,
        "label": label,
        "email": email,
        "login_method": login_method,
        "browser": browser,
        "discovery_token_env": discovery_token_env,
        "enabled": enabled,
        "original_name": original_name,
    })


@mcp.tool()
def delete_account(account: str, confirm: bool = False) -> dict[str, Any]:
    """Delete an account record only when it has no associated projects. Requires explicit confirm=true."""
    _require_confirmation(confirm, f"Deleting account '{account}'")
    return _api("/api/account-remove", {"name": account, "clear_tokens": False})


@mcp.tool()
def connect_account_cli(account: str) -> dict[str, Any]:
    """Start the official Supabase CLI login flow for the account's isolated named CLI profile. Human browser completion may be required."""
    return _api("/api/oauth-start", {"account": account})


@mcp.tool()
def disconnect_account_cli(account: str, confirm: bool = False) -> dict[str, Any]:
    """Disconnect the account's named Supabase CLI profile. Requires explicit confirm=true."""
    _require_confirmation(confirm, f"Disconnecting CLI profile for '{account}'")
    return _api("/api/oauth-disconnect", {"account": account})


@mcp.tool()
def import_projects(account: str, projects: list[dict[str, str]]) -> dict[str, Any]:
    """
    Import discovered projects.
    Each item may contain target, ref, label and token_env. Existing targets are skipped.
    """
    return _api("/api/import-projects", {"account": account, "projects": projects})


@mcp.tool()
def create_or_update_project(
    target: str,
    account: str,
    project_ref: str,
    label: str = "",
    environment: str = "production",
    token_env: str = "",
    read_only: bool = False,
    enabled: bool = True,
    original_target: str = "",
) -> dict[str, Any]:
    """Create or update a project target. This configures only the PAT environment-variable name, never the PAT value."""
    return _api("/api/project", {
        "name": target,
        "account": account,
        "project_ref": project_ref,
        "label": label,
        "environment": environment,
        "token_env": token_env,
        "read_only": read_only,
        "enabled": enabled,
        "original_name": original_target,
    })


@mcp.tool()
def reassign_project(target: str, target_account: str) -> dict[str, Any]:
    """Reassign a configured project to another existing Supabase account."""
    return _api("/api/reassign-project", {"project": target, "target_account": target_account})


@mcp.tool()
def delete_project(target: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a project record from Supabase Multi. The PAT environment variable is preserved as an orphan. Requires confirm=true."""
    _require_confirmation(confirm, f"Deleting project '{target}'")
    return _api("/api/project-remove", {"name": target})


@mcp.tool()
def copy_project_pat_from_env(target: str, source_env: str) -> dict[str, Any]:
    """
    Copy a PAT from an existing local environment variable into the project's configured token_env.
    Use this instead of sending raw PAT values through the LLM/MCP conversation.
    """
    return _api("/api/project-token-copy", {"project": target, "source_env": source_env})


@mcp.tool()
def clear_project_pat(target: str, confirm: bool = False) -> dict[str, Any]:
    """Delete the project's configured PAT environment variable. Requires confirm=true."""
    _require_confirmation(confirm, f"Clearing project PAT for '{target}'")
    return _api("/api/project-token-clear", {"project": target})


@mcp.tool()
def copy_discovery_pat_from_env(account: str, source_env: str) -> dict[str, Any]:
    """
    Copy an account-wide Discovery PAT from an existing local environment variable into the account's configured discovery_token_env.
    Raw PAT values never pass through MCP.
    """
    return _api("/api/discovery-token-copy", {"account": account, "source_env": source_env})


@mcp.tool()
def clear_discovery_pat(account: str, confirm: bool = False) -> dict[str, Any]:
    """Delete the account's configured Discovery PAT environment variable. Requires confirm=true."""
    _require_confirmation(confirm, f"Clearing Discovery PAT for '{account}'")
    return _api("/api/token-clear", {"account": account})


@mcp.tool()
def list_orphaned_secrets() -> list[str]:
    """List names of orphaned Supabase PAT/token environment variables. Secret values are never returned."""
    return list(_state().get("orphan_secrets", []))


@mcp.tool()
def delete_orphaned_secret(name: str, confirm: bool = False) -> dict[str, Any]:
    """Delete one currently orphaned Supabase secret environment variable. Requires confirm=true and server-side orphan revalidation."""
    _require_confirmation(confirm, f"Deleting orphaned secret '{name}'")
    return _api("/api/orphan-secret-remove", {"name": name})


@mcp.tool()
def clean_all_orphaned_secrets(confirm: bool = False) -> dict[str, Any]:
    """Delete all currently orphaned Supabase secret environment variables. Requires confirm=true and server-side revalidation."""
    _require_confirmation(confirm, "Cleaning all orphaned secrets")
    return _api("/api/orphan-secrets-clean", {})


def main() -> None:
    """Run Supabase Multi MCP over stdio or Streamable HTTP."""
    transport = os.environ.get("SUPABASE_MULTI_MCP_TRANSPORT", "stdio").strip().lower()

    if transport == "streamable-http":
        host = os.environ.get("SUPABASE_MULTI_MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("SUPABASE_MULTI_MCP_PORT", "8000"))
        path = os.environ.get("SUPABASE_MULTI_MCP_PATH", "/mcp")

        mcp.run(
            "streamable-http",
            host=host,
            port=port,
            streamable_http_path=path,
        )
        return

    mcp.run("stdio")

if __name__ == "__main__":
    main()
