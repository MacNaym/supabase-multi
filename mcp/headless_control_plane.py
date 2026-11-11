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
MANAGEMENT_URL = "https://api.supabase.com/v1"
DEFAULT_FEATURES = "database"
MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_USER_AGENT = "Supabase-Multi/0.2"


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
    return os.environ.get(name, "").strip()


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
