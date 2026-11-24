from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Path(os.environ.get("SUPABASE_MULTI_REGISTRY", ROOT / "registry.json"))
MCP_URL = "https://mcp.supabase.com/mcp"
MANAGEMENT_URL = "https://api.supabase.com/v1"
DEFAULT_FEATURES = "database"
MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_USER_AGENT = "Supabase-Multi/0.2"
DEFAULT_BACKUP_ROOT = Path(os.environ.get("SUPABASE_MULTI_BACKUP_DIR", Path.home() / "SupabaseMultiBackups"))


def read_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {
            "version": 3,
            "defaults": {
                "read_only_production": True,
                "mcp_prefix": "sb_",
                "features": DEFAULT_FEATURES,
            },
            "accounts": {},
            "projects": {},
        }

    data = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    data.setdefault("version", 3)
    data.setdefault("defaults", {})
    data["defaults"].setdefault("features", DEFAULT_FEATURES)
    data.setdefault("accounts", {})
    data.setdefault("projects", {})
    return data


def write_registry(reg: dict[str, Any]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY.with_suffix(REGISTRY.suffix + ".tmp")
    tmp.write_text(
        json.dumps(reg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(REGISTRY)


def read_token_env_value(name: str) -> str:
    if not name:
        return ""

    value = os.environ.get(name, "").strip()
    if value:
        return value

    # Windows user-scoped variables created with setx are not injected into
    # an already-running Python process. Read them directly when necessary.
    if os.name == "nt":
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"[Environment]::GetEnvironmentVariable('{name}','User')",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                return (proc.stdout or "").strip()
        except Exception:
            pass

    return ""


def _http_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 40,
) -> Any:
    body = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": MCP_USER_AGENT,
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def supabase_list_projects_pat(token: str) -> list[dict[str, Any]]:
    data = _http_json(f"{MANAGEMENT_URL}/projects", token)
    if not isinstance(data, list):
        raise RuntimeError("Unexpected response from Supabase Management API.")
    return data


def normalize_platform_status(value: Any) -> str:
    status = str(value or "UNKNOWN").strip().upper()
    if status in {"ACTIVE", "ACTIVE_HEALTHY", "COMING_UP"}:
        return "ACTIVE"
    if status in {"INACTIVE", "PAUSED", "GOING_DOWN"}:
        return "PAUSED"
    if status in {"UNKNOWN", ""}:
        return "UNKNOWN"
    return status


def project_status_from_pat(project_ref: str, token_env: str) -> tuple[dict[str, Any] | None, str, str]:
    token = read_token_env_value(token_env)

    if not token:
        return None, "TOKEN_MISSING", f"Nessun PAT trovato nella variabile {token_env}."

    try:
        projects = supabase_list_projects_pat(token)
    except Exception as exc:
        return None, "PAT_REQUEST_FAILED", str(exc)

    for project in projects:
        if str(project.get("ref") or "") == project_ref:
            return project, "", ""

    return None, "PROJECT_NOT_VISIBLE", "Il PAT non vede il progetto richiesto."


def _used_secret_env_names(reg: dict[str, Any]) -> set[str]:
    names: set[str] = set()

    for account in reg.get("accounts", {}).values():
        name = str(account.get("discovery_token_env") or "").strip()
        if name:
            names.add(name)

    for project in reg.get("projects", {}).values():
        name = str(project.get("token_env") or "").strip()
        if name:
            names.add(name)

    return names


def orphaned_supabase_secret_envs(reg: dict[str, Any]) -> list[str]:
    used = _used_secret_env_names(reg)
    candidates = []

    for name in os.environ:
        upper = name.upper()
        if not upper.startswith("SUPABASE_"):
            continue
        if "TOKEN" not in upper and "PAT" not in upper:
            continue
        if name not in used:
            candidates.append(name)

    return sorted(candidates)


def _account_payload(
    name: str,
    account: dict[str, Any],
    reg: dict[str, Any],
) -> dict[str, Any]:
    used_by = [
        project_name
        for project_name, project in reg.get("projects", {}).items()
        if project.get("account") == name
    ]

    discovery_env = str(account.get("discovery_token_env") or "").strip()

    return {
        "name": name,
        "label": account.get("label") or name,
        "email": account.get("email") or "",
        "browser": account.get("browser") or "default",
        "login_method": account.get("login_method") or "unknown",
        "oauth_connected": False,
        "platform_check_ok": None,
        "platform_check_error": "",
        "enabled": bool(account.get("enabled", True)),
        "identity_complete": bool(account.get("email"))
        and str(account.get("login_method") or "unknown") != "unknown",
        "used_by": used_by,
        "discovery_token_env": discovery_env,
        "discovery_token_ok": bool(discovery_env and read_token_env_value(discovery_env)),
        "browser_profile_ready": False,
    }


def _project_payload(
    name: str,
    project: dict[str, Any],
    reg: dict[str, Any],
    *,
    check_remote: bool,
) -> dict[str, Any]:
    token_env = str(project.get("token_env") or "").strip()
    token_ok = bool(token_env and read_token_env_value(token_env))
    platform_status = "UNKNOWN"
    platform_seen = False
    error_kind = ""
    error_detail = ""

    if check_remote and token_ok:
        info, error_kind, error_detail = project_status_from_pat(
            str(project.get("project_ref") or ""),
            token_env,
        )
        if info is not None:
            platform_status = normalize_platform_status(info.get("status"))
            platform_seen = True

    account_name = str(project.get("account") or "")
    account = reg.get("accounts", {}).get(account_name, {})

    return {
        "name": name,
        "label": project.get("label") or name,
        "account": account_name,
        "account_email": account.get("email") or "",
        "browser": account.get("browser") or "default",
        "login_method": account.get("login_method") or "unknown",
        "project_ref": project.get("project_ref") or "",
        "environment": project.get("environment") or "production",
        "enabled": bool(project.get("enabled", True)),
        "read_only": bool(project.get("read_only", False)),
        "token_env": token_env,
        "token_ok": token_ok,
        "backup_dir": project.get("backup_dir") or "",
        "mcp": f"sb_{name}",
        "platform_status": platform_status,
        "platform_seen": platform_seen,
        "status_source": "PAT" if platform_seen else "LOCAL",
        "pat_status_error_kind": error_kind,
        "pat_status_error_detail": error_detail,
    }


def state_payload(check_remote: bool = False) -> dict[str, Any]:
    reg = read_registry()

    accounts = [
        _account_payload(name, account, reg)
        for name, account in sorted(reg.get("accounts", {}).items())
    ]

    projects = [
        _project_payload(name, project, reg, check_remote=check_remote)
        for name, project in sorted(reg.get("projects", {}).items())
    ]

    return {
        "accounts": accounts,
        "projects": projects,
        "orphan_secrets": orphaned_supabase_secret_envs(reg),
        "platform_checked_at": None,
        "mode": "headless",
    }


def resolve_project_candidates(
    reg: dict[str, Any],
    *,
    target: str | None = None,
    project_ref: str | None = None,
    account: str | None = None,
    repo_path: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    projects = reg.get("projects", {})

    target = (target or "").strip()
    project_ref = (project_ref or "").strip()
    account = (account or "").strip()
    repo_path = (repo_path or "").strip()
    name = (name or "").strip()

    if target:
        project = projects.get(target)
        if project:
            return {"status": "resolved", "target": target, "project": project}
        return {"status": "not_found", "candidates": []}

    matches: list[tuple[str, dict[str, Any]]] = []

    for key, project in projects.items():
        if project_ref and str(project.get("project_ref") or "") != project_ref:
            continue
        if account and str(project.get("account") or "") != account:
            continue
        if name:
            haystack = {
                key.lower(),
                str(project.get("label") or "").lower(),
            }
            if name.lower() not in haystack:
                continue
        matches.append((key, project))

    if repo_path:
        marker = Path(repo_path) / ".supabase-target.json"
        if marker.exists():
            try:
                marker_data = json.loads(marker.read_text(encoding="utf-8-sig"))
                marker_target = str(marker_data.get("target") or "").strip()
                if marker_target in projects:
                    return {
                        "status": "resolved",
                        "target": marker_target,
                        "project": projects[marker_target],
                        "source": "repo",
                    }
            except Exception:
                pass

    if len(matches) == 1:
        key, project = matches[0]
        return {"status": "resolved", "target": key, "project": project}

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "candidates": [
                {
                    "target": key,
                    "label": project.get("label") or key,
                    "account": project.get("account") or "",
                    "project_ref": project.get("project_ref") or "",
                }
                for key, project in matches
            ],
        }

    return {"status": "not_found", "candidates": []}


def mcp_post(
    token: str,
    payload: dict[str, Any],
    session_id: str | None = None,
    endpoint: str = MCP_URL,
    *,
    protocol_version: str = MCP_PROTOCOL_VERSION,
    return_meta: bool = False,
):
    body = json.dumps(payload).encode("utf-8")
    method = str(payload.get("method") or "")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": protocol_version,
        "User-Agent": MCP_USER_AGENT,
    }

    if session_id:
        headers["Mcp-Session-Id"] = session_id

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method="POST",
    )

    status = 0
    response_headers: Any = {}
    text = ""
    http_error = ""

    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            status = int(getattr(resp, "status", resp.getcode()))
            response_headers = resp.headers
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        response_headers = exc.headers or {}
        text = exc.read().decode("utf-8", errors="replace")
        http_error = str(exc)
        if not return_meta:
            raise

    sid = response_headers.get("Mcp-Session-Id") or session_id
    parsed: dict[str, Any] = {}

    if "data:" in text:
        events = []
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[5:].strip()))
                except Exception:
                    pass
        parsed = events[-1] if events else {}
    else:
        try:
            parsed = json.loads(text) if text else {}
        except Exception:
            parsed = {}

    meta = {
        "method": method,
        "status": status,
        "content_type": str(response_headers.get("Content-Type") or ""),
        "request_protocol_version": protocol_version,
        "request_session_id_present": bool(session_id),
        "response_session_id_present": bool(response_headers.get("Mcp-Session-Id")),
        "body_bytes": len(text.encode("utf-8")),
        "user_agent": MCP_USER_AGENT,
        "http_error": http_error,
    }

    if return_meta:
        return parsed, sid, meta
    return parsed, sid


def _mcp_phase_error(phase: str, payload: Any, meta: dict[str, Any]) -> str:
    msg = _mcp_error_message(payload)
    parts = [
        f"phase={phase}",
        f"http_status={meta.get('status')}",
        f"content_type={meta.get('content_type') or 'none'}",
        f"request_protocol={meta.get('request_protocol_version')}",
        f"request_session={meta.get('request_session_id_present')}",
        f"response_session={meta.get('response_session_id_present')}",
        f"body_bytes={meta.get('body_bytes')}",
    ]
    if msg:
        parts.append("mcp_error=" + msg)
    if meta.get("http_error"):
        parts.append("http_error=" + str(meta["http_error"]))
    return " | ".join(parts)


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



def _project_credentials(
    project_name: str,
    *,
    write: bool = False,
) -> tuple[str, str, dict[str, Any]]:
    project_name = (project_name or "").strip()
    if not project_name:
        raise ValueError("Project target is required.")

    reg = read_registry()
    project = reg.get("projects", {}).get(project_name)

    if not project:
        raise ValueError("Project not found.")
    if not project.get("enabled", True):
        raise ValueError("Project target is disabled.")
    if write and bool(project.get("read_only", False)):
        raise ValueError("Project target is configured read-only; writes are blocked.")

    project_ref = str(project.get("project_ref") or "").strip()
    token_env = str(project.get("token_env") or "").strip()

    if not project_ref:
        raise ValueError("Project ref is not configured.")
    if not token_env:
        raise ValueError("Project token_env is not configured.")

    token = read_token_env_value(token_env)
    if not token:
        raise ValueError(f"No PAT found in environment variable {token_env}.")

    return project_ref, token, project


def call_project_mcp_tool(
    project_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    write: bool = False,
) -> dict[str, Any]:
    project_ref, token, _project = _project_credentials(project_name, write=write)

    params: dict[str, str] = {"project_ref": project_ref}
    if not write:
        params["read_only"] = "true"

    endpoint = MCP_URL + "?" + urllib.parse.urlencode(params)

    init, sid, init_meta = mcp_post(
        token,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "supabase-multi-edge-proxy",
                    "version": "0.3",
                },
            },
        },
        endpoint=endpoint,
        return_meta=True,
    )

    if init_meta["status"] >= 400 or _mcp_error_message(init):
        raise RuntimeError(
            "Supabase MCP initialize failed: "
            + _mcp_phase_error("initialize", init, init_meta)
        )

    negotiated = str(
        ((init or {}).get("result") or {}).get("protocolVersion")
        or MCP_PROTOCOL_VERSION
    )
    if negotiated != MCP_PROTOCOL_VERSION:
        raise RuntimeError(
            "Supabase MCP negotiated an unsupported protocol version: "
            + negotiated
        )

    initialized, sid, initialized_meta = mcp_post(
        token,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        sid,
        endpoint=endpoint,
        protocol_version=negotiated,
        return_meta=True,
    )

    if initialized_meta["status"] != 202:
        raise RuntimeError(
            "Supabase MCP notifications/initialized failed: "
            + _mcp_phase_error(
                "notifications/initialized",
                initialized,
                initialized_meta,
            )
        )

    payload, sid, tool_meta = mcp_post(
        token,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        },
        sid,
        endpoint=endpoint,
        protocol_version=negotiated,
        return_meta=True,
    )

    msg = _mcp_error_message(payload)
    if tool_meta["status"] >= 400 or msg:
        raise RuntimeError(
            f"Supabase MCP {tool_name} failed: "
            + _mcp_phase_error("tools/call", payload, tool_meta)
        )

    result = (payload or {}).get("result", {}) or {}
    if result.get("isError"):
        detail = _mcp_text_content(result) or f"Supabase MCP {tool_name} returned an error."
        raise RuntimeError(detail)

    return {
        "project": project_name,
        "project_ref": project_ref,
        "source": "official-supabase-mcp",
        "tool": tool_name,
        "content": result.get("content", []),
        "structured_content": result.get("structuredContent"),
        "mcp_transport": {
            "negotiated_protocol_version": negotiated,
            "initialize": init_meta,
            "notifications_initialized": initialized_meta,
            "tools_call": tool_meta,
        },
    }


def list_edge_functions(project_name: str) -> dict[str, Any]:
    return call_project_mcp_tool(
        project_name,
        "list_edge_functions",
        {},
        write=False,
    )


def get_edge_function(project_name: str, function_slug: str) -> dict[str, Any]:
    function_slug = (function_slug or "").strip()
    if not function_slug:
        raise ValueError("function_slug is required.")

    return call_project_mcp_tool(
        project_name,
        "get_edge_function",
        {"function_slug": function_slug},
        write=False,
    )


def deploy_edge_function(
    project_name: str,
    name: str,
    files: list[dict[str, str]],
    *,
    entrypoint_path: str = "index.ts",
    verify_jwt: bool = True,
    import_map_path: str | None = None,
) -> dict[str, Any]:
    name = (name or "").strip()
    entrypoint_path = (entrypoint_path or "index.ts").strip()

    if not name:
        raise ValueError("Edge Function name is required.")
    if not isinstance(files, list) or not files:
        raise ValueError("Edge Function files must be a non-empty list.")

    normalized_files: list[dict[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Each Edge Function file must be an object.")
        file_name = str(item.get("name") or "").strip()
        content = item.get("content")
        if not file_name or not isinstance(content, str):
            raise ValueError("Each Edge Function file requires name and string content.")
        normalized_files.append({"name": file_name, "content": content})

    arguments: dict[str, Any] = {
        "name": name,
        "entrypoint_path": entrypoint_path,
        "files": normalized_files,
        "verify_jwt": bool(verify_jwt),
    }
    if import_map_path:
        arguments["import_map_path"] = str(import_map_path).strip()

    return call_project_mcp_tool(
        project_name,
        "deploy_edge_function",
        arguments,
        write=True,
    )


def delete_edge_function(project_name: str, function_slug: str) -> dict[str, Any]:
    function_slug = (function_slug or "").strip()
    if not function_slug:
        raise ValueError("function_slug is required.")

    project_ref, token, _project = _project_credentials(project_name, write=True)
    url = (
        f"{MANAGEMENT_URL}/projects/"
        + urllib.parse.quote(project_ref, safe="")
        + "/functions/"
        + urllib.parse.quote(function_slug, safe="")
    )

    result = _http_json(url, token, method="DELETE")

    return {
        "project": project_name,
        "project_ref": project_ref,
        "function_slug": function_slug,
        "source": "supabase-management-api",
        "deleted": True,
        "result": result,
    }



def _safe_backup_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip("-._")
    return cleaned or "project"


def _backup_source(
    project_name: str,
) -> tuple[str, str, str, str, dict[str, Any]]:
    project_name = (project_name or "").strip()
    if not project_name:
        raise ValueError("Project target is required.")

    reg = read_registry()
    project = reg.get("projects", {}).get(project_name)
    if not project:
        raise ValueError("Project not found.")
    if not project.get("enabled", True):
        raise ValueError("Project target is disabled.")

    project_ref = str(project.get("project_ref") or "").strip()
    token_env = str(project.get("token_env") or "").strip()
    if not project_ref:
        raise ValueError("Project ref is not configured.")
    if not token_env:
        raise ValueError("Project token_env is not configured.")

    access_token = read_token_env_value(token_env)
    if not access_token:
        raise ValueError(f"No PAT found in environment variable {token_env}.")

    password_env = (
        str(project.get("db_password_env") or "").strip()
        or "SUPABASE_DB_PASSWORD_"
        + re.sub(r"[^A-Za-z0-9]+", "_", project_name.upper()).strip("_")
    )
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", password_env):
        raise ValueError("db_password_env must be a valid environment-variable name.")
    db_password = read_token_env_value(password_env)

    return project_ref, token_env, access_token, password_env, project


def _supabase_cli() -> str:
    cli = shutil.which("supabase")
    if not cli:
        raise RuntimeError(
            "Supabase CLI was not found on PATH. Install it or add it to PATH before creating backups."
        )
    return cli


def _backup_preflight(cli: str) -> None:
    help_result = subprocess.run([cli, "db", "dump", "--help"], capture_output=True, text=True, timeout=20)
    if help_result.returncode or "--remote" not in (help_result.stdout or ""):
        raise RuntimeError("Backup requires Supabase CLI v3 with --remote support. Update the CLI.")
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker CLI not found. Install and start Docker before backing up.")
    result = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=30)
    if result.returncode or not (result.stdout or "").strip():
        raise RuntimeError("Docker engine is not ready. Start Docker and retry.")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backup_management_request(project_ref: str, token: str, suffix: str, body=None):
    if not re.fullmatch(r"[a-z0-9]{20}", project_ref):
        raise ValueError("Invalid Supabase project ref.")
    request = urllib.request.Request(
        f"{MANAGEMENT_URL}/projects/{project_ref}/{suffix}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": MCP_USER_AGENT},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        permission = "database_write" if body is not None else "database_pooling_config_read"
        raise RuntimeError(f"Pooler API {suffix} failed (HTTP {exc.code}). Check project PAT permission {permission}.") from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise RuntimeError(f"Pooler API {suffix} failed. Check network and API availability.") from None


def _backup_pooler_url(project_ref: str, token: str, password: str = "") -> str:
    configs = _backup_management_request(project_ref, token, "config/database/pooler")
    if not isinstance(configs, list):
        raise RuntimeError("Unexpected pooler configuration response.")
    candidates = set()
    for config in configs:
        if not isinstance(config, dict) or config.get("database_type") != "PRIMARY":
            continue
        host = str(config.get("db_host") or "").lower()
        if not re.fullmatch(r"[a-z0-9-]+\.pooler\.supabase\.com", host):
            continue
        if config.get("db_user") != "postgres." + project_ref or config.get("db_name") != "postgres":
            continue
        candidates.add(host)
    if len(candidates) != 1:
        raise RuntimeError("Could not resolve a unique primary Supabase session pooler for this project.")
    host = candidates.pop()
    role = "postgres"
    if not password:
        credentials = _backup_management_request(project_ref, token, "cli/login-role", {"read_only": False})
        if not isinstance(credentials, dict):
            raise RuntimeError("Unexpected temporary login response.")
        role = credentials.get("role")
        password = credentials.get("password")
        if not isinstance(role, str) or not re.fullmatch(r"cli_login_[a-zA-Z0-9_]+", role) or not isinstance(password, str) or not password:
            raise RuntimeError("Invalid temporary login credentials returned by Supabase.")
    user = urllib.parse.quote(role + "." + project_ref, safe="")
    secret = urllib.parse.quote(password, safe="")
    return f"postgresql://{user}:{secret}@{host}:5432/postgres?sslmode=require"


def _run_backup_dump(
    cli: str,
    project_ref: str,
    access_token: str,
    output: Path,
    extra_args: list[str],
    *,
    db_password: str = "",
    pooler_url: str = "",
) -> None:
    command = [
        cli,
        "db",
        "dump",
        f"--remote={pooler_url or project_ref}",
        "--profile", "supabase",
        "-f",
        str(output),
        *extra_args,
    ]
    if db_password:
        command.extend(["--password", db_password])

    env = os.environ.copy()
    env["SUPABASE_ACCESS_TOKEN"] = access_token
    env.pop("SUPABASE_PROFILE", None)
    env.pop("SUPABASE_DB_PASSWORD", None)
    try:
        proc = subprocess.run(
            command, capture_output=True, text=True, timeout=3600, env=env,
        )
    except (subprocess.TimeoutExpired, OSError):
        raise RuntimeError("Supabase backup process could not complete (timeout or launch failure).") from None
    if proc.returncode != 0:
        if pooler_url:
            # Never echo CLI diagnostics that may include a credential-bearing URL.
            raise RuntimeError("Session pooler dump failed. Check database login permissions, network and CLI compatibility.")
        detail = (proc.stderr or proc.stdout or "Supabase CLI db dump failed.").strip()
        detail = detail.replace(access_token, "[REDACTED_ACCESS_TOKEN]")
        if db_password:
            detail = detail.replace(db_password, "[REDACTED_DB_PASSWORD]")
        raise RuntimeError(detail)
    if not output.exists():
        raise RuntimeError(f"Supabase CLI reported success but did not create {output.name}.")


def backup_database(
    project_name: str,
    *,
    mode: str = "full",
    destination: str | None = None,
    progress=None,
) -> dict[str, Any]:
    def emit(phase, **details):
        if progress is not None:
            progress(phase, **details)

    emit("preflight")
    mode = (mode or "full").strip().lower()
    if mode not in {"full", "schema", "data"}:
        raise ValueError("mode must be one of: full, schema, data.")

    project_ref, token_env, access_token, password_env, project = _backup_source(project_name)
    cli = _supabase_cli()
    _backup_preflight(cli)

    configured_destination = str(project.get("backup_dir") or "").strip()
    root = (
        Path(destination).expanduser()
        if destination
        else Path(configured_destination).expanduser()
        if configured_destination
        else DEFAULT_BACKUP_ROOT
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    backup_dir = root / _safe_backup_name(project_name) / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)

    jobs: list[tuple[str, list[str]]] = []
    if mode == "full":
        jobs.append(("roles.sql", ["--role-only"]))
    if mode in {"full", "schema"}:
        jobs.append(("schema.sql", []))
    if mode in {"full", "data"}:
        jobs.append(
            (
                "data.sql",
                [
                    "--data-only",
                    "--use-copy",
                    "-x",
                    "storage.buckets_vectors",
                    "-x",
                    "storage.vector_indexes",
                ],
            )
        )

    credential_mode = "temporary-login"
    connection_mode = str(project.get("backup_connection_mode") or "auto").lower()
    if connection_mode not in {"auto", "direct", "session-pooler"}:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise ValueError("Invalid backup_connection_mode.")
    pooler_url = ""
    db_password = ""
    try:
        emit("connection", folder=str(backup_dir))
        if connection_mode == "session-pooler":
            pooler_url = _backup_pooler_url(project_ref, access_token, read_token_env_value(password_env))
            credential_mode = "session-pooler"
        for file_name, args in jobs:
            emit(file_name.split(".")[0], connection="session-pooler" if pooler_url else "direct")
            if pooler_url:
                _run_backup_dump(cli, project_ref, access_token, backup_dir / file_name, args, pooler_url=pooler_url)
                continue
            if db_password:
                _run_backup_dump(
                    cli,
                    project_ref,
                    access_token,
                    backup_dir / file_name,
                    args,
                    db_password=db_password,
                )
                continue
            try:
                _run_backup_dump(
                    cli,
                    project_ref,
                    access_token,
                    backup_dir / file_name,
                    args,
                )
            except RuntimeError as first_error:
                # Supabase CLI normally creates a temporary database login from
                # SUPABASE_ACCESS_TOKEN. A project-specific DB password is only
                # an optional fallback for environments where temporary login fails.
                detail = str(first_error).lower()
                if connection_mode == "auto" and "ipv6 is not supported" in detail:
                    emit("pooler", connection="session-pooler")
                    pooler_url = _backup_pooler_url(project_ref, access_token, read_token_env_value(password_env))
                    credential_mode = "session-pooler"
                    emit(file_name.split(".")[0], connection="session-pooler")
                    _run_backup_dump(cli, project_ref, access_token, backup_dir / file_name, args, pooler_url=pooler_url)
                    continue
                if not any(marker in detail for marker in ("temporary login", "temporary role", "password authentication failed", "28p01", "database_write")):
                    raise
                db_password = read_token_env_value(password_env)
                if not db_password:
                    raise RuntimeError(
                        str(first_error)
                        + f" | No fallback DB password found in {password_env}."
                    ) from first_error
                credential_mode = "database-password-fallback"
                _run_backup_dump(
                    cli,
                    project_ref,
                    access_token,
                    backup_dir / file_name,
                    args,
                    db_password=db_password,
                )

        emit("manifest")
        files = []
        for file_name, _args in jobs:
            path = backup_dir / file_name
            files.append(
                {
                    "name": file_name,
                    "bytes": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )

        version_proc = subprocess.run(
            [cli, "--version"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        cli_version = (
            (version_proc.stdout or version_proc.stderr or "").strip()
            if version_proc.returncode == 0
            else "unknown"
        )

        manifest = {
            "format": "supabase-multi-backup-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "project": project_name,
            "account": project.get("account"),
            "project_ref": project_ref,
            "mode": mode,
            "credential_mode": credential_mode,
            "token_env": token_env,
            "supabase_cli_version": cli_version,
            "files": files,
        }
        manifest_path = backup_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        emit("verify")
        if not verify_database_backup(str(backup_dir))["ok"]:
            raise RuntimeError("Backup integrity verification failed.")
        emit("complete")
    except Exception:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise

    return {
        "project": project_name,
        "project_ref": project_ref,
        "mode": mode,
        "backup_dir": str(backup_dir),
        "manifest": str(manifest_path),
        "token_env": token_env,
        "credential_mode": credential_mode,
        "files": files,
        "verified": True,
        "source": "supabase-cli",
    }


def list_database_backups(
    project_name: str,
    *,
    destination: str | None = None,
) -> dict[str, Any]:
    project_name = (project_name or "").strip()
    if not project_name:
        raise ValueError("Project target is required.")

    reg = read_registry()
    project = reg.get("projects", {}).get(project_name)
    if not project:
        raise ValueError("Project not found.")

    configured_destination = str(project.get("backup_dir") or "").strip()
    root = (
        Path(destination).expanduser()
        if destination
        else Path(configured_destination).expanduser()
        if configured_destination
        else DEFAULT_BACKUP_ROOT
    )
    project_dir = root / _safe_backup_name(project_name)
    backups: list[dict[str, Any]] = []
    if project_dir.is_dir():
        for child in sorted(project_dir.iterdir(), reverse=True):
            manifest_path = child / "manifest.json"
            if not child.is_dir() or not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("project") != project_name or manifest.get("project_ref") != project.get("project_ref"):
                    continue
                if manifest.get("account") is not None and manifest.get("account") != project.get("account"):
                    continue
                backups.append(
                    {
                        "backup_dir": str(child),
                        "manifest": str(manifest_path),
                        "created_at": manifest.get("created_at"),
                        "mode": manifest.get("mode"),
                        "files": len(manifest.get("files") or []),
                    }
                )
            except Exception:
                backups.append(
                    {
                        "backup_dir": str(child),
                        "manifest": str(manifest_path),
                        "created_at": None,
                        "mode": "unknown",
                        "files": 0,
                        "invalid_manifest": True,
                    }
                )
    return {
        "project": project_name,
        "root": str(root),
        "backups": backups,
        "count": len(backups),
    }


def verify_database_backup(path: str) -> dict[str, Any]:
    raw_path = (path or "").strip()
    if not raw_path:
        raise ValueError("Backup path is required.")

    candidate = Path(raw_path).expanduser()
    manifest_path = candidate if candidate.name.lower() == "manifest.json" else candidate / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("manifest.json was not found in the backup path.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "supabase-multi-backup-v1":
        raise ValueError("Unsupported backup manifest format.")

    backup_dir = manifest_path.parent.resolve()
    checks = []
    all_ok = True

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list) or not manifest_files:
        raise ValueError("Backup manifest contains no files.")

    for item in manifest_files:
        if not isinstance(item, dict):
            raise ValueError("Backup manifest contains an invalid file entry.")
        name = str(item.get("name") or "").strip()
        if not name:
            all_ok = False
            checks.append({"name": name, "ok": False, "error": "Missing file name."})
            continue

        file_path = (backup_dir / name).resolve()
        if file_path.parent != backup_dir:
            all_ok = False
            checks.append({"name": name, "ok": False, "error": "Unsafe manifest path."})
            continue
        if not file_path.is_file():
            all_ok = False
            checks.append({"name": name, "ok": False, "error": "File missing."})
            continue

        actual_size = file_path.stat().st_size
        actual_hash = _sha256_file(file_path)
        expected_size = int(item.get("bytes", -1))
        expected_hash = str(item.get("sha256") or "")
        ok = actual_size == expected_size and actual_hash == expected_hash
        all_ok = all_ok and ok
        checks.append(
            {
                "name": name,
                "ok": ok,
                "bytes": actual_size,
                "sha256": actual_hash,
            }
        )

    return {
        "ok": all_ok,
        "format": manifest.get("format"),
        "project": manifest.get("project"),
        "project_ref": manifest.get("project_ref"),
        "mode": manifest.get("mode"),
        "backup_dir": str(backup_dir),
        "manifest": str(manifest_path),
        "files": checks,
    }


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

    init, sid, init_meta = mcp_post(
        token,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "supabase-multi-headless",
                    "version": "0.2",
                },
            },
        },
        endpoint=endpoint,
        return_meta=True,
    )

    if init_meta["status"] >= 400 or _mcp_error_message(init):
        raise RuntimeError(
            "Supabase MCP initialize failed: "
            + _mcp_phase_error("initialize", init, init_meta)
        )

    negotiated = str(
        ((init or {}).get("result") or {}).get("protocolVersion")
        or MCP_PROTOCOL_VERSION
    )
    if negotiated != MCP_PROTOCOL_VERSION:
        raise RuntimeError(
            "Supabase MCP negotiated an unsupported protocol version: "
            + negotiated
        )

    initialized, sid, initialized_meta = mcp_post(
        token,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        sid,
        endpoint=endpoint,
        protocol_version=negotiated,
        return_meta=True,
    )

    if initialized_meta["status"] != 202:
        raise RuntimeError(
            "Supabase MCP notifications/initialized failed: "
            + _mcp_phase_error(
                "notifications/initialized",
                initialized,
                initialized_meta,
            )
        )

    payload, sid, tool_meta = mcp_post(
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
        protocol_version=negotiated,
        return_meta=True,
    )

    msg = _mcp_error_message(payload)

    if tool_meta["status"] >= 400 or msg:
        raise RuntimeError(
            "Supabase MCP execute_sql failed: "
            + _mcp_phase_error("tools/call", payload, tool_meta)
        )

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
        "mcp_transport": {
            "negotiated_protocol_version": negotiated,
            "initialize": init_meta,
            "notifications_initialized": initialized_meta,
            "tools_call": tool_meta,
        },
    }


def _unsupported_local_operation(path: str) -> None:
    raise RuntimeError(
        f"{path} is a local-desktop-only operation and is not available in headless production mode."
    )


def _headless_doctor() -> dict[str, Any]:
    reg = read_registry()
    problems: list[str] = []

    for name, project in reg.get("projects", {}).items():
        if not project.get("project_ref"):
            problems.append(f"{name}: project_ref missing")
        token_env = str(project.get("token_env") or "").strip()
        if not token_env:
            problems.append(f"{name}: token_env missing")
        elif not read_token_env_value(token_env):
            problems.append(f"{name}: secret {token_env} not loaded")

    result = {
        "ok": not problems,
        "mode": "headless",
        "registry": str(REGISTRY),
        "accounts": len(reg.get("accounts", {})),
        "projects": len(reg.get("projects", {})),
        "problems": problems,
    }

    return result


def handle_api(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    endpoint = (path or "").split("?", 1)[0]
    payload = payload or {}

    if endpoint == "/api/state":
        check_remote = "local=1" not in (path or "")
        return {"ok": True, "data": state_payload(check_remote=check_remote)}

    if endpoint == "/api/resolve":
        reg = read_registry()
        result = resolve_project_candidates(
            reg,
            target=payload.get("target"),
            project_ref=payload.get("project_ref"),
            account=payload.get("account"),
            repo_path=payload.get("repo_path"),
            name=payload.get("name"),
        )
        return {"ok": True, **result}

    if endpoint == "/api/sql-query":
        project = str(payload.get("project") or "").strip()
        query = str(payload.get("query") or "").strip()
        result = execute_project_sql(project, query, read_only=True)
        return {
            "ok": True,
            "message": "Read-only SQL completed.",
            "result": result,
        }

    if endpoint == "/api/sql-execute":
        if payload.get("confirm") is not True:
            raise ValueError("SQL write execution requires confirm=true.")
        project = str(payload.get("project") or "").strip()
        query = str(payload.get("query") or "").strip()
        result = execute_project_sql(project, query, read_only=False)
        return {
            "ok": True,
            "message": "SQL execution completed.",
            "result": result,
        }

    if endpoint == "/api/account":
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Account name is required.")

        browser = str(payload.get("browser") or "default").strip().lower()
        login_method = str(payload.get("login_method") or "unknown").strip().lower()

        if browser not in {"default", "brave", "edge", "chrome"}:
            raise ValueError("Invalid browser.")
        if login_method not in {"unknown", "classic", "github", "google"}:
            raise ValueError("Invalid login method.")

        reg = read_registry()
        accounts = reg.setdefault("accounts", {})
        original = str(payload.get("original_name") or "").strip()

        if original and original != name:
            if name in accounts:
                raise ValueError("Account alias already exists.")
            if original not in accounts:
                raise ValueError("Original account not found.")
            accounts[name] = accounts.pop(original)
            for project in reg.get("projects", {}).values():
                if project.get("account") == original:
                    project["account"] = name

        account = accounts.get(name, {})
        account.update(
            {
                "label": str(payload.get("label") or "").strip() or name,
                "email": str(payload.get("email") or "").strip(),
                "browser": browser,
                "login_method": login_method,
                "discovery_token_env": str(
                    payload.get("discovery_token_env") or ""
                ).strip(),
                "enabled": bool(payload.get("enabled", True)),
            }
        )
        accounts[name] = account
        write_registry(reg)

        return {"ok": True, "message": f"Account '{name}' saved."}

    if endpoint == "/api/account-remove":
        name = str(payload.get("name") or "").strip()
        reg = read_registry()
        used = [
            project_name
            for project_name, project in reg.get("projects", {}).items()
            if project.get("account") == name
        ]
        if used:
            raise ValueError("Account used by: " + ", ".join(used))

        account = reg.get("accounts", {}).pop(name, None)
        if not account:
            raise ValueError("Account not found.")

        write_registry(reg)
        return {
            "ok": True,
            "message": "Account removed from registry. Environment secrets were preserved.",
        }

    if endpoint == "/api/discover":
        account_name = str(payload.get("account") or "").strip()
        mode = str(payload.get("mode") or "pat").strip().lower()

        if mode != "pat":
            _unsupported_local_operation("/api/discover mode=oauth")

        reg = read_registry()
        account = reg.get("accounts", {}).get(account_name)
        if not account:
            raise ValueError("Account not found.")

        env_name = str(account.get("discovery_token_env") or "").strip()
        token = read_token_env_value(env_name)

        if not token:
            raise ValueError("Account-wide Discovery PAT is missing.")

        projects = supabase_list_projects_pat(token)
        known = {
            project.get("project_ref"): name
            for name, project in reg.get("projects", {}).items()
            if project.get("project_ref")
        }

        normalized = []
        for item in projects:
            project = dict(item)
            ref = str(project.get("ref") or "")
            project["already_imported"] = ref in known
            project["existing_target"] = known.get(ref)
            normalized.append(project)

        return {
            "ok": True,
            "projects": normalized,
            "count": len(normalized),
        }

    if endpoint == "/api/project":
        name = str(payload.get("name") or "").strip()
        account_name = str(payload.get("account") or "").strip()
        ref = str(payload.get("project_ref") or "").strip()
        original = str(payload.get("original_name") or "").strip()

        if not name or not account_name or not ref:
            raise ValueError("target/account/project_ref are required.")

        reg = read_registry()
        projects = reg.setdefault("projects", {})

        if account_name not in reg.get("accounts", {}):
            raise ValueError("Supabase account not found.")

        if original and original != name:
            if name in projects:
                raise ValueError("A project with this target already exists.")
            if original not in projects:
                raise ValueError("Original project not found.")
            projects[name] = projects.pop(original)

        project = projects.get(name, {})
        features = (
            project.get("features")
            or reg.setdefault("defaults", {}).get("features")
            or DEFAULT_FEATURES
        )

        project.update(
            {
                "label": str(payload.get("label") or "").strip() or name,
                "account": account_name,
                "project_ref": ref,
                "environment": payload.get("environment") or "production",
                "read_only": bool(payload.get("read_only", False)),
                "features": features,
                "token_env": str(payload.get("token_env") or "").strip() or None,
                "enabled": bool(payload.get("enabled", True)),
            }
        )

        projects[name] = project
        write_registry(reg)

        return {"ok": True, "message": f"Target '{name}' saved."}

    if endpoint == "/api/import-projects":
        account_name = str(payload.get("account") or "").strip()
        items = payload.get("projects") or []

        reg = read_registry()
        if account_name not in reg.get("accounts", {}):
            raise ValueError("Supabase account not found.")

        projects = reg.setdefault("projects", {})
        features = (
            reg.setdefault("defaults", {}).get("features")
            or DEFAULT_FEATURES
        )

        imported: list[str] = []
        skipped: list[str] = []

        for item in items:
            target = str(item.get("target") or "").strip()
            ref = str(item.get("ref") or "").strip()

            if not target or not ref or target in projects:
                skipped.append(target or ref)
                continue

            projects[target] = {
                "label": item.get("label") or target,
                "account": account_name,
                "project_ref": ref,
                "environment": "production",
                "read_only": False,
                "features": features,
                "token_env": str(item.get("token_env") or "").strip() or None,
                "enabled": True,
            }
            imported.append(target)

        if imported:
            write_registry(reg)

        return {
            "ok": True,
            "message": f"Imported {len(imported)} target(s).",
            "imported": imported,
            "skipped": skipped,
        }

    if endpoint == "/api/project-remove":
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Missing project name.")

        reg = read_registry()
        project = reg.get("projects", {}).pop(name, None)

        if not project:
            raise ValueError("Project not found.")

        write_registry(reg)
        return {
            "ok": True,
            "message": f"Project '{name}' removed from registry. Environment secrets were preserved.",
        }

    if endpoint == "/api/project-pat-check":
        project_name = str(payload.get("project") or "").strip()
        reg = read_registry()
        project = reg.get("projects", {}).get(project_name)

        if not project:
            raise ValueError("Project not found.")

        ref = str(project.get("project_ref") or "").strip()
        env_name = str(project.get("token_env") or "").strip()

        if not env_name:
            raise RuntimeError("PAT env is not configured.")

        info, error_kind, error_detail = project_status_from_pat(ref, env_name)

        if info is None:
            raise RuntimeError(
                " | ".join(
                    part
                    for part in [error_kind, error_detail]
                    if part
                )
            )

        status = normalize_platform_status(info.get("status"))

        return {
            "ok": True,
            "message": f"Access verified via PAT for {project_name}. Supabase status: {status}.",
            "project": project_name,
            "token_env": env_name,
            "platform_status": status,
            "raw_status": info.get("status", "UNKNOWN"),
            "source": "PAT",
            "fallback_used": False,
        }

    if endpoint == "/api/reassign-project":
        project_name = str(payload.get("project") or "").strip()
        target_account = str(payload.get("target_account") or "").strip()

        reg = read_registry()

        if target_account not in reg.get("accounts", {}):
            raise ValueError("Target account not found.")

        project = reg.get("projects", {}).get(project_name)
        if not project:
            raise ValueError("Project not found.")

        old_account = project.get("account") or ""
        project["account"] = target_account
        write_registry(reg)

        return {
            "ok": True,
            "message": f"Project '{project_name}' reassigned from '{old_account}' to '{target_account}'.",
            "old_account": old_account,
            "target_account": target_account,
        }

    if endpoint == "/api/open-project":
        reg = read_registry()
        project_name = str(payload.get("project") or "").strip()
        project = reg.get("projects", {}).get(project_name)

        if not project:
            raise ValueError("Project not found.")

        ref = str(project.get("project_ref") or "").strip()
        if not ref:
            raise ValueError("project_ref is missing.")

        return {
            "ok": True,
            "message": "Headless mode cannot open a browser; dashboard URL returned instead.",
            "url": f"https://supabase.com/dashboard/project/{ref}",
            "project": project_name,
        }

    if endpoint == "/api/doctor":
        result = _headless_doctor()
        return {
            "ok": result["ok"],
            "message": "Headless doctor completed.",
            "result": result,
        }

    if endpoint == "/api/sync":
        return {
            "ok": True,
            "message": "No MCP config sync is required in headless mode.",
            "result": {"ok": True, "mode": "headless", "action": "noop"},
        }

    if endpoint == "/api/sync-doctor":
        doctor = _headless_doctor()
        return {
            "ok": doctor["ok"],
            "message": "Headless sync + doctor completed.",
            "sync": {"ok": True, "mode": "headless", "action": "noop"},
            "doctor": doctor,
        }

    if endpoint in {
        "/api/project-token-copy",
        "/api/discovery-token-copy",
        "/api/orphan-secret-remove",
        "/api/orphan-secrets-clean",
        "/api/token",
        "/api/token-clear",
        "/api/oauth-start",
        "/api/oauth-disconnect",
        "/api/project-token",
        "/api/project-token-clear",
    }:
        _unsupported_local_operation(endpoint)

    raise RuntimeError(f"Headless API path not implemented: {endpoint}")
