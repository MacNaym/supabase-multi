
from __future__ import annotations
import base64, ctypes, ctypes.wintypes, hashlib, json, os, secrets, shutil, subprocess, sys, threading, time
import urllib.parse, urllib.request, urllib.error, webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
UI_DIR = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry.json"
BACKUPS = ROOT / "backups"
MANAGER = ROOT / "scripts" / "supabase-manager.ps1"
OAUTH_STORE = UI_DIR / "oauth-sessions.dat"
HOST = "127.0.0.1"
PORT = 8765
CALLBACK = f"http://{HOST}:{PORT}/oauth/callback"
MCP_URL = "https://mcp.supabase.com/mcp"
MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_USER_AGENT = "Supabase-Multi/0.2"
DEFAULT_FEATURES = ["database", "debugging", "development", "functions", "docs"]
BROWSER_PROFILES = UI_DIR / "browser-profiles"


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in str(value or "").strip()) or "default"

def browser_profile_dir(account):
    return BROWSER_PROFILES / safe_name(account)

def browser_candidates():
    if os.name != "nt":
        return {}
    env = os.environ
    candidates = {
        "brave": [
            shutil.which("brave"),
            str(Path(env.get("PROGRAMFILES", "")) / "BraveSoftware/Brave-Browser/Application/brave.exe"),
            str(Path(env.get("PROGRAMFILES(X86)", "")) / "BraveSoftware/Brave-Browser/Application/brave.exe"),
            str(Path(env.get("LOCALAPPDATA", "")) / "BraveSoftware/Brave-Browser/Application/brave.exe"),
        ],
        "edge": [
            shutil.which("msedge"),
            str(Path(env.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe"),
            str(Path(env.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe"),
        ],
        "chrome": [
            shutil.which("chrome"),
            str(Path(env.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe"),
            str(Path(env.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe"),
            str(Path(env.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"),
        ],
    }
    found = {}
    for kind, items in candidates.items():
        for item in items:
            if item and Path(item).exists():
                found[kind] = str(Path(item))
                break
    return found

def windows_default_browser_kind():
    """Best-effort detection of the Windows default HTTPS browser."""
    if os.name != "nt":
        return None
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            progid, _ = winreg.QueryValueEx(k, "ProgId")
        p = str(progid).lower()
        if "brave" in p:
            return "brave"
        if "chrome" in p:
            return "chrome"
        if "edge" in p or "microsoftedge" in p or "mse" in p:
            return "edge"
    except Exception:
        pass
    return None

def resolve_browser(preference="default"):
    found = browser_candidates()
    pref = (preference or "default").lower()

    if pref == "default":
        detected = windows_default_browser_kind()
        if detected and detected in found:
            return detected, found[detected]
        # Fallback order favors Brave, then Edge, then Chrome.
        for kind in ("brave", "edge", "chrome"):
            if kind in found:
                return kind, found[kind]
        raise RuntimeError("Compatible Chromium browser not found. Install Brave, Edge, or Chrome.")

    if pref in ("brave", "edge", "chrome"):
        if pref not in found:
            raise RuntimeError(f"Browser {pref} non trovato. Installa il browser o cambia la preferenza dell'account.")
        return pref, found[pref]

    raise RuntimeError("Browser non valido.")

def launch_project_browser(account, project_ref):
    reg = read_registry()
    acc = reg.get("accounts", {}).get(account)
    if not acc:
        raise ValueError("Supabase account not found.")
    if not project_ref:
        raise ValueError("Missing project_ref.")
    browser_kind, exe = resolve_browser(acc.get("browser", "default"))
    profile_dir = browser_profile_dir(account)
    profile_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://supabase.com/dashboard/project/{urllib.parse.quote(project_ref, safe='')}"
    cmd = [
        exe,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]
    subprocess.Popen(cmd, cwd=str(UI_DIR))
    return {
        "browser": browser_kind,
        "profile_dir": str(profile_dir),
        "url": url,
        "first_use": not any(profile_dir.iterdir()),
    }

def migrate_registry_v3(reg):
    """Upgrade old v2 registry without losing working MCP token mappings."""
    changed = False
    if int(reg.get("version", 2) or 2) < 3:
        reg["version"] = 3
        changed = True

    accounts = reg.setdefault("accounts", {})
    projects = reg.setdefault("projects", {})

    for name, acc in accounts.items():
        if "email" not in acc:
            acc["email"] = ""
            changed = True
        if "browser" not in acc:
            acc["browser"] = "default"
            changed = True
        if "login_method" not in acc:
            acc["login_method"] = "unknown"
            changed = True

    # Old versions allowed an operational token_env on the account and projects
    # inherited it. In v3 every project owns its operational token_env.
    for pname, project in projects.items():
        if not project.get("token_env"):
            account = accounts.get(project.get("account", ""), {})
            legacy = account.get("token_env")
            if legacy:
                project["token_env"] = legacy
                changed = True

    return reg, changed

def cli_candidates():
    candidates = []
    if shutil.which("supabase"):
        candidates.append(["supabase"])
    if shutil.which("npx"):
        candidates.append(["npx", "--yes", "supabase"])
    return candidates

def cli_base():
    c = cli_candidates()
    if not c:
        raise RuntimeError("Supabase CLI non trovata. Installa la CLI oppure usa la modalitÃ  PAT manuale.")
    return c[0]

def cli_profile_name(account):
    # Account alias is already controlled by our UI; keep a conservative profile string.
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in account.strip())
    return safe or "supabase-multi"

def run_supabase(args, timeout=60):
    base = cli_base()
    proc = subprocess.run(base + args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, cwd=str(ROOT))
    return {"ok": proc.returncode == 0, "code": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def migrate_legacy_cli_profile_flags(reg):
    changed = False
    for account, acc in reg.get("accounts", {}).items():
        if "cli_profile_managed" in acc:
            continue
        profile = cli_profile_name(account)
        managed = False
        try:
            r = run_supabase(["--profile", profile, "projects", "list", "-o", "json"], timeout=45)
            if r["ok"]:
                try:
                    json.loads(r["stdout"] or "[]")
                    managed = True
                except Exception:
                    managed = False
        except Exception:
            managed = False
        acc["cli_profile_managed"] = managed
        changed = True
    if changed:
        write_registry(reg)
    return reg

def cli_profile_status(account, account_record=None):
    # A successful generic CLI command is not enough: on some setups the CLI can
    # fall back to existing/default credentials even when this named profile was
    # never created by Supabase Multi.
    if not (account_record or {}).get("cli_profile_managed", False):
        return False
    profile = cli_profile_name(account)
    try:
        r = run_supabase(["--profile", profile, "projects", "list", "-o", "json"], timeout=45)
        if not r["ok"]:
            return False
        try:
            json.loads(r["stdout"] or "[]")
        except Exception:
            return False
        return True
    except Exception:
        return False

def cli_profile_login(account):
    profile = cli_profile_name(account)
    base = cli_base()
    cmd = base + ["--profile", profile, "login", "--name", profile]
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(cmd, cwd=str(ROOT), creationflags=flags)
    else:
        subprocess.Popen(cmd, cwd=str(ROOT))
    return profile

def cli_profile_logout(account):
    profile = cli_profile_name(account)
    r = run_supabase(["--profile", profile, "logout"], timeout=45)
    return r

def supabase_list_projects_cli(account):
    profile = cli_profile_name(account)
    r = run_supabase(["--profile", profile, "projects", "list", "-o", "json"], timeout=60)
    if not r["ok"]:
        detail = (r["stderr"] or r["stdout"] or "").strip()
        raise RuntimeError("Profilo Supabase non autenticato o CLI non disponibile. " + detail[:500])
    try:
        data = json.loads(r["stdout"])
    except Exception:
        raise RuntimeError("La Supabase CLI non ha restituito JSON valido.")
    return normalize_projects(data)
OAUTH_PENDING = {}

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

def _blob(data: bytes):
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf

def dpapi_encrypt(data: bytes) -> bytes:
    if os.name != "nt":
        return data
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, in_buf = _blob(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptProtectData(ctypes.byref(in_blob), "SupabaseMultiOAuth", None, None, None, 0, ctypes.byref(out_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)

def dpapi_decrypt(data: bytes) -> bytes:
    if os.name != "nt":
        return data
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, in_buf = _blob(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)

def load_oauth_store():
    if not OAUTH_STORE.exists():
        return {}
    try:
        raw = base64.b64decode(OAUTH_STORE.read_bytes())
        return json.loads(dpapi_decrypt(raw).decode("utf-8"))
    except Exception:
        return {}

def save_oauth_store(store):
    raw = json.dumps(store, ensure_ascii=False).encode("utf-8")
    OAUTH_STORE.write_bytes(base64.b64encode(dpapi_encrypt(raw)))

def read_registry():
    if not REGISTRY.exists():
        return {"version":3,"defaults":{"read_only_production":True,"features":DEFAULT_FEATURES,"mcp_prefix":"sb_"},"accounts":{},"projects":{}}
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    reg, changed = migrate_registry_v3(reg)
    if changed:
        REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    return reg

def backup_registry():
    if not REGISTRY.exists(): return None
    BACKUPS.mkdir(parents=True, exist_ok=True)
    dest = BACKUPS / f"registry.ui.{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    shutil.copy2(REGISTRY, dest)
    return str(dest)

def write_registry(data):
    backup_registry()
    REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def env_get(name):
    if not name: return None
    if os.environ.get(name): return os.environ.get(name)
    if os.name != "nt": return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except Exception:
        return None

def env_exists(name): return bool(env_get(name))

def set_user_env(name, value):
    if os.name != "nt": raise RuntimeError("PAT automatici previsti per Windows.")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    os.environ[name] = value

def clear_user_env(name):
    if os.name != "nt" or not name: return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass
    os.environ.pop(name, None)

def read_user_env_value(name):
    """Read a Windows user environment variable without exposing it through state payloads."""
    if not name:
        return None
    if os.name != "nt":
        return os.environ.get(name)
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, name)
            return str(value)
    except FileNotFoundError:
        return os.environ.get(name)

def copy_user_env_secret(source_env, target_env):
    source_env=(source_env or "").strip()
    target_env=(target_env or "").strip()
    if not source_env or not target_env:
        raise ValueError("source_env and target_env are required.")
    value=read_user_env_value(source_env)
    if not value:
        raise ValueError(f"Source environment variable '{source_env}' is empty or missing.")
    set_user_env(target_env,value)
    return target_env

def list_user_env_names():
    if os.name != "nt":
        return []
    import winreg
    names=[]
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
            i=0
            while True:
                try:
                    name, _value, _kind = winreg.EnumValue(key, i)
                    names.append(name)
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        return []
    return names

def referenced_secret_envs(reg):
    refs=set()
    for acc in reg.get("accounts",{}).values():
        for key in ("discovery_token_env","token_env"):
            name=(acc.get(key) or "").strip()
            if name:
                refs.add(name.upper())
    for p in reg.get("projects",{}).values():
        name=(p.get("token_env") or "").strip()
        if name:
            refs.add(name.upper())
    return refs

def orphaned_supabase_secret_envs(reg):
    refs=referenced_secret_envs(reg)
    out=[]
    for name in list_user_env_names():
        upper=name.upper()
        # Conservative scope: only variables that clearly look like Supabase PAT vars.
        if not upper.startswith("SUPABASE_"):
            continue
        if not ("PAT" in upper or "TOKEN" in upper):
            continue
        if upper not in refs:
            out.append(name)
    return sorted(out, key=str.upper)

def delete_orphan_secret(reg, name):
    name=(name or "").strip()
    if not name:
        raise ValueError("Missing environment variable name.")
    current={x.upper():x for x in orphaned_supabase_secret_envs(reg)}
    actual=current.get(name.upper())
    if not actual:
        raise ValueError("Environment variable is not currently an orphaned Supabase secret.")
    clear_user_env(actual)
    return actual

def run_ps_manager(*args):
    if not MANAGER.exists(): raise RuntimeError(f"Manager not found: {MANAGER}")
    p = subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(MANAGER),*args],
                       cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return {"ok":p.returncode==0,"code":p.returncode,"stdout":p.stdout,"stderr":p.stderr}

def account_token_env(reg, name): return reg.get("accounts",{}).get(name,{}).get("token_env")
def account_discovery_env(reg, name): return reg.get("accounts",{}).get(name,{}).get("discovery_token_env")
def project_token_env(reg, p): return p.get("token_env") or account_token_env(reg,p.get("account",""))  # legacy fallback


def _repo_target_from_path(repo_path):
    """Walk upward looking for .supabase-target.json and return configured target if present."""
    if not repo_path:
        return None, None
    try:
        p=Path(repo_path).expanduser().resolve()
    except Exception:
        p=Path(repo_path).expanduser()
    if p.is_file():
        p=p.parent
    for cur in [p, *p.parents]:
        cfg=cur / ".supabase-target.json"
        if cfg.exists():
            try:
                data=json.loads(cfg.read_text(encoding="utf-8"))
                target=(data.get("default_target") or data.get("production_target") or data.get("target") or "").strip()
                return target or None, str(cfg)
            except Exception:
                return None, str(cfg)
    return None, None

def resolve_project_candidates(reg, target=None, project_ref=None, account=None, repo_path=None, name=None):
    """
    Resolve a project without guessing.
    Returns status=resolved|ambiguous|not_found and never returns secret values.
    """
    projects=reg.get("projects",{})
    target=(target or "").strip()
    project_ref=(project_ref or "").strip()
    account=(account or "").strip()
    name=(name or "").strip()

    repo_target, repo_config = _repo_target_from_path(repo_path)

    def public_project(project_name, p):
        acc=reg.get("accounts",{}).get(p.get("account",""),{})
        token_env=(p.get("token_env") or "").strip()
        return {
            "target":project_name,
            "label":p.get("label",project_name),
            "account":p.get("account",""),
            "account_email":acc.get("email",""),
            "project_ref":p.get("project_ref",""),
            "environment":p.get("environment","production"),
            "read_only":bool(p.get("read_only",False)),
            "enabled":bool(p.get("enabled",True)),
            "token_env":token_env,
            "token_present":bool(read_token_env_value(token_env)) if token_env else False,
            "mcp":f"{reg.get('defaults',{}).get('mcp_prefix','sb_')}{project_name}",
        }

    candidates=[]
    for project_name,p in projects.items():
        if target and project_name != target:
            continue
        if project_ref and p.get("project_ref","") != project_ref:
            continue
        if account and p.get("account","") != account:
            continue
        candidates.append((project_name,p))

    # Strong repo mapping overrides fuzzy name matching, but not explicit contradictory filters.
    if repo_target:
        repo_match=[(n,p) for n,p in candidates if n==repo_target]
        if repo_match:
            candidates=repo_match
        elif not any([target,project_ref,account]):
            candidates=[(n,p) for n,p in projects.items() if n==repo_target]

    if name and not target and not project_ref:
        q=name.lower()
        exact=[(n,p) for n,p in candidates if n.lower()==q or str(p.get("label","")).lower()==q]
        if exact:
            candidates=exact
        else:
            candidates=[(n,p) for n,p in candidates if q in n.lower() or q in str(p.get("label","")).lower()]

    public=[public_project(n,p) for n,p in candidates]
    if len(public)==1:
        return {"status":"resolved","project":public[0],"candidates":public,"repo_config":repo_config}
    if len(public)>1:
        return {"status":"ambiguous","project":None,"candidates":public,"repo_config":repo_config}
    return {"status":"not_found","project":None,"candidates":[],"repo_config":repo_config}

def normalize_status(status):
    s=(status or "UNKNOWN").upper()
    if s=="ACTIVE_HEALTHY": return "active"
    if s=="INACTIVE": return "paused"
    if s in {"COMING_UP","RESTARTING","RESTORING","UPGRADING","RESIZING","GOING_DOWN","PAUSING"}: return "transition"
    if s in {"ACTIVE_UNHEALTHY","RESTORE_FAILED","PAUSE_FAILED","INIT_FAILED"}: return "warning"
    if s=="REMOVED": return "removed"
    return "unknown"

def http_json(url, method="GET", headers=None, data=None, timeout=30):
    h={"Accept":"application/json", "User-Agent":"supabase-multi-local-ui/3.5"}
    if headers: h.update(headers)
    body=None
    if data is not None:
        if isinstance(data, dict):
            body=urllib.parse.urlencode(data).encode()
            h.setdefault("Content-Type","application/x-www-form-urlencoded")
        else:
            body=data
    req=urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")), dict(resp.headers)

def supabase_list_projects_pat(token):
    try:
        data,_=http_json("https://api.supabase.com/v1/projects", headers={"Authorization":f"Bearer {token}"})
    except urllib.error.HTTPError as e:
        if e.code==401: raise RuntimeError("Discovery PAT rejected (401).")
        if e.code==403: raise RuntimeError("Account-wide Discovery PAT lacks permission to list projects (403).")
        raise
    return normalize_projects(data)

def normalize_projects(data):
    out=[]
    for p in data if isinstance(data,list) else []:
        out.append({"name":p.get("name") or p.get("ref") or "senza nome",
                    "ref":p.get("ref") or p.get("id") or "",
                    "organization_id":p.get("organization_id") or "",
                    "organization_slug":p.get("organization_slug") or "",
                    "region":p.get("region") or "",
                    "created_at":p.get("created_at") or "",
                    "status":p.get("status") or "UNKNOWN",
                    "status_group":normalize_status(p.get("status"))})
    return out

def discover_mcp_oauth():
    # Probe protected resource metadata via RFC 9728-style WWW-Authenticate header.
    req=urllib.request.Request(MCP_URL, headers={"Accept":"application/json, text/event-stream"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as e:
        www=e.headers.get("WWW-Authenticate","")
        meta=None
        for part in www.split(","):
            if "resource_metadata=" in part:
                meta=part.split("resource_metadata=",1)[1].strip().strip('"')
        if not meta:
            # Known MCP metadata fallback.
            meta="https://mcp.supabase.com/.well-known/oauth-protected-resource"
        resource,_=http_json(meta)
        auth_servers=resource.get("authorization_servers") or []
        if not auth_servers: raise RuntimeError("Nessun authorization server pubblicato da Supabase MCP.")
        issuer=auth_servers[0].rstrip("/")
        # OAuth AS metadata.
        candidates=[
            issuer+"/.well-known/oauth-authorization-server",
            issuer+"/.well-known/openid-configuration",
            "https://mcp.supabase.com/.well-known/oauth-authorization-server",
        ]
        last=None
        for u in candidates:
            try:
                meta_as,_=http_json(u)
                return resource,meta_as
            except Exception as ex: last=ex
        raise RuntimeError(f"Metadata OAuth non disponibile: {last}")
    raise RuntimeError("Risposta OAuth inattesa da Supabase MCP.")

def oauth_register(meta_as):
    reg=meta_as.get("registration_endpoint")
    if not reg: raise RuntimeError("Dynamic client registration non pubblicata dal server OAuth.")
    payload=json.dumps({
        "client_name":"Supabase Multi Local UI",
        "redirect_uris":[CALLBACK],
        "grant_types":["authorization_code","refresh_token"],
        "response_types":["code"],
        "token_endpoint_auth_method":"none"
    }).encode()
    req=urllib.request.Request(reg,data=payload,headers={"Content-Type":"application/json","Accept":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=30) as resp:
        return json.loads(resp.read().decode())

def oauth_start(account):
    resource,meta_as=discover_mcp_oauth()
    client=oauth_register(meta_as)
    client_id=client["client_id"]
    verifier=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state=secrets.token_urlsafe(24)
    OAUTH_PENDING[state]={"account":account,"verifier":verifier,"client_id":client_id,"meta":meta_as,
                          "resource":resource.get("resource") or MCP_URL,"created":time.time()}
    q={"response_type":"code","client_id":client_id,"redirect_uri":CALLBACK,
       "code_challenge":challenge,"code_challenge_method":"S256","state":state}
    scopes=meta_as.get("scopes_supported")
    if scopes: q["scope"]=" ".join(scopes)
    # Resource indicator is supported by MCP OAuth servers.
    q["resource"]=resource.get("resource") or MCP_URL
    return meta_as["authorization_endpoint"]+"?"+urllib.parse.urlencode(q)

def oauth_exchange(state, code):
    pending=OAUTH_PENDING.pop(state,None)
    if not pending: raise RuntimeError("Sessione OAuth scaduta o sconosciuta.")
    meta=pending["meta"]
    data={"grant_type":"authorization_code","code":code,"redirect_uri":CALLBACK,
          "client_id":pending["client_id"],"code_verifier":pending["verifier"],
          "resource":pending["resource"]}
    tokens,_=http_json(meta["token_endpoint"], method="POST", data=data)
    store=load_oauth_store()
    store[pending["account"]]={"client_id":pending["client_id"],"token_endpoint":meta["token_endpoint"],
                               "access_token":tokens.get("access_token"),"refresh_token":tokens.get("refresh_token"),
                               "expires_at":time.time()+int(tokens.get("expires_in",3600)),
                               "resource":pending["resource"]}
    save_oauth_store(store)
    return pending["account"]

def oauth_access_token(account):
    store=load_oauth_store()
    s=store.get(account)
    if not s: raise RuntimeError("Account non connesso in modalitÃ  semplice.")
    if s.get("access_token") and time.time()<float(s.get("expires_at",0))-60: return s["access_token"]
    if not s.get("refresh_token"): raise RuntimeError("Sessione OAuth scaduta e senza refresh token.")
    data={"grant_type":"refresh_token","refresh_token":s["refresh_token"],"client_id":s["client_id"],"resource":s.get("resource",MCP_URL)}
    tokens,_=http_json(s["token_endpoint"], method="POST", data=data)
    s["access_token"]=tokens.get("access_token")
    if tokens.get("refresh_token"): s["refresh_token"]=tokens["refresh_token"]
    s["expires_at"]=time.time()+int(tokens.get("expires_in",3600))
    store[account]=s; save_oauth_store(store)
    return s["access_token"]

def mcp_post(token, payload, session_id=None, endpoint=MCP_URL, *, protocol_version=MCP_PROTOCOL_VERSION, return_meta=False):
    body=json.dumps(payload).encode("utf-8")
    method=str(payload.get("method") or "")
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json",
             "Accept":"application/json, text/event-stream","MCP-Protocol-Version":protocol_version,
             "User-Agent":MCP_USER_AGENT}
    if session_id: headers["Mcp-Session-Id"]=session_id
    req=urllib.request.Request(endpoint,data=body,headers=headers,method="POST")

    status=0
    response_headers={}
    text=""
    http_error=""
    try:
        with urllib.request.urlopen(req,timeout=40) as resp:
            status=int(getattr(resp,"status",resp.getcode()))
            response_headers=resp.headers
            text=resp.read().decode("utf-8",errors="replace")
    except urllib.error.HTTPError as exc:
        status=int(exc.code)
        response_headers=exc.headers or {}
        text=exc.read().decode("utf-8",errors="replace")
        http_error=str(exc)
        if not return_meta:
            raise

    sid=response_headers.get("Mcp-Session-Id") or session_id
    parsed={}
    if "data:" in text:
        events=[]
        for line in text.splitlines():
            if line.startswith("data:"):
                try: events.append(json.loads(line[5:].strip()))
                except Exception: pass
        parsed=events[-1] if events else {}
    else:
        try: parsed=json.loads(text) if text else {}
        except Exception: parsed={}

    meta={
        "method":method,
        "status":status,
        "content_type":str(response_headers.get("Content-Type") or ""),
        "request_protocol_version":protocol_version,
        "request_session_id_present":bool(session_id),
        "response_session_id_present":bool(response_headers.get("Mcp-Session-Id")),
        "body_bytes":len(text.encode("utf-8")),
        "user_agent":MCP_USER_AGENT,
        "http_error":http_error,
    }
    if return_meta:
        return parsed,sid,meta
    return parsed,sid

def _mcp_phase_error(phase, payload, meta):
    msg=_mcp_error_message(payload)
    parts=[
        f"phase={phase}",
        f"http_status={meta.get('status')}",
        f"content_type={meta.get('content_type') or 'none'}",
        f"request_protocol={meta.get('request_protocol_version')}",
        f"request_session={meta.get('request_session_id_present')}",
        f"response_session={meta.get('response_session_id_present')}",
        f"body_bytes={meta.get('body_bytes')}",
    ]
    if msg:
        parts.append("mcp_error="+msg)
    if meta.get("http_error"):
        parts.append("http_error="+str(meta["http_error"]))
    return " | ".join(parts)

def supabase_list_projects_oauth(account):
    token=oauth_access_token(account)
    init,sid,init_meta=mcp_post(token,{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":MCP_PROTOCOL_VERSION,"capabilities":{},"clientInfo":{"name":"supabase-multi-ui","version":"3.1"}}},return_meta=True)
    if init_meta["status"]>=400 or _mcp_error_message(init):
        raise RuntimeError("Supabase MCP initialize failed: "+_mcp_phase_error("initialize",init,init_meta))
    negotiated=str(((init or {}).get("result") or {}).get("protocolVersion") or MCP_PROTOCOL_VERSION)
    if negotiated!=MCP_PROTOCOL_VERSION:
        raise RuntimeError("Supabase MCP negotiated an unsupported protocol version: "+negotiated)
    initialized,sid,initialized_meta=mcp_post(
        token,{"jsonrpc":"2.0","method":"notifications/initialized","params":{}},sid,
        protocol_version=negotiated,return_meta=True
    )
    if initialized_meta["status"]!=202:
        raise RuntimeError("Supabase MCP notifications/initialized failed: "+_mcp_phase_error(
            "notifications/initialized",initialized,initialized_meta
        ))
    result,sid=mcp_post(
        token,{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_projects","arguments":{}}},sid,
        protocol_version=negotiated
    )
    r=result.get("result",{})
    content=r.get("content",[])
    for item in content:
        if item.get("type")=="text":
            txt=item.get("text","")
            try:
                data=json.loads(txt)
                if isinstance(data,dict) and "projects" in data: data=data["projects"]
                return normalize_projects(data)
            except:
                pass
    # Some servers may return structuredContent.
    data=r.get("structuredContent")
    if isinstance(data,dict) and "projects" in data: data=data["projects"]
    if isinstance(data,list): return normalize_projects(data)
    raise RuntimeError("OAuth connesso, ma list_projects non ha restituito un formato riconosciuto.")



def _mcp_error_message(payload):
    if not isinstance(payload, dict):
        return "Unknown MCP error."
    err = payload.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)
    if err:
        return str(err)
    return ""

def _mcp_text_content(result):
    texts=[]
    for item in (result or {}).get("content",[]) or []:
        if isinstance(item,dict) and item.get("type")=="text":
            texts.append(str(item.get("text","")))
    return "\n".join(x for x in texts if x)

def execute_project_sql(reg, project_name, query, read_only=True):
    """Proxy SQL to the official project-scoped Supabase MCP without exposing the PAT."""
    project_name=(project_name or "").strip()
    query=(query or "").strip()
    if not project_name:
        raise ValueError("Project target is required.")
    if not query:
        raise ValueError("SQL query is required.")
    if len(query) > 100000:
        raise ValueError("SQL query is too large.")

    project=reg.get("projects",{}).get(project_name)
    if not project:
        raise ValueError("Project not found.")
    if not project.get("enabled",True):
        raise ValueError("Project target is disabled.")
    if not read_only and bool(project.get("read_only",False)):
        raise ValueError("Project target is configured read-only; SQL writes are blocked.")

    project_ref=(project.get("project_ref") or "").strip()
    token_env=(project.get("token_env") or "").strip()
    if not project_ref:
        raise ValueError("Project ref is not configured.")
    if not token_env:
        raise ValueError("Project token_env is not configured.")

    token=read_token_env_value(token_env)
    if not token:
        raise ValueError(f"No PAT found in environment variable {token_env}.")

    params={
        "project_ref":project_ref,
        "features":"database",
    }
    if read_only:
        params["read_only"]="true"
    else:
        # This proxy cannot relay nested form elicitation from the downstream
        # Supabase MCP. The outer Supabase Multi MCP requires confirm=true
        # before calling this write path, and project read_only is enforced above.
        params["skip_elicitations"]="execute_sql"
    endpoint=MCP_URL+"?"+urllib.parse.urlencode(params)

    init,sid,init_meta=mcp_post(token,{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":MCP_PROTOCOL_VERSION,
        "capabilities":{},
        "clientInfo":{"name":"supabase-multi-sql-proxy","version":"0.2"}
    }},endpoint=endpoint,return_meta=True)
    if init_meta["status"]>=400 or _mcp_error_message(init):
        raise RuntimeError("Supabase MCP initialize failed: "+_mcp_phase_error("initialize",init,init_meta))

    negotiated=str(((init or {}).get("result") or {}).get("protocolVersion") or MCP_PROTOCOL_VERSION)
    if negotiated!=MCP_PROTOCOL_VERSION:
        raise RuntimeError("Supabase MCP negotiated an unsupported protocol version: "+negotiated)

    initialized,sid,initialized_meta=mcp_post(
        token,{"jsonrpc":"2.0","method":"notifications/initialized","params":{}},sid,
        endpoint=endpoint,protocol_version=negotiated,return_meta=True
    )
    if initialized_meta["status"]!=202:
        raise RuntimeError("Supabase MCP notifications/initialized failed: "+_mcp_phase_error(
            "notifications/initialized",initialized,initialized_meta
        ))

    payload,sid,tool_meta=mcp_post(token,{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{
        "name":"execute_sql",
        "arguments":{"query":query}
    }},sid,endpoint=endpoint,protocol_version=negotiated,return_meta=True)
    msg=_mcp_error_message(payload)
    if tool_meta["status"]>=400 or msg:
        raise RuntimeError("Supabase MCP execute_sql failed: "+_mcp_phase_error("tools/call",payload,tool_meta))

    result=(payload or {}).get("result",{}) or {}
    if result.get("isError"):
        detail=_mcp_text_content(result) or "Supabase MCP execute_sql returned an error."
        raise RuntimeError(detail)

    return {
        "project":project_name,
        "project_ref":project_ref,
        "read_only":bool(read_only),
        "source":"official-supabase-mcp",
        "content":result.get("content",[]),
        "structured_content":result.get("structuredContent"),
        "mcp_transport":{
            "negotiated_protocol_version":negotiated,
            "initialize":init_meta,
            "notifications_initialized":initialized_meta,
            "tools_call":tool_meta,
        },
    }


def read_token_env_value(name):
    if not name:
        return ""
    value = os.environ.get(name, "")
    if value:
        return value
    # setx/user-scoped vars may not exist in the already-running Python process.
    if os.name == "nt":
        try:
            ps = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"[Environment]::GetEnvironmentVariable('{name}','User')"],
                capture_output=True, text=True, timeout=10
            )
            if ps.returncode == 0:
                return (ps.stdout or "").strip()
        except Exception:
            pass
    return ""

def project_status_from_pat(project_ref, token_env):
    """Verify one project with its operational scoped PAT.

    Get Project requires Project Settings: Read.
    Returns (info|None, error_kind, detail).
    """
    token = read_token_env_value(token_env)
    if not token:
        return None, "NO_TOKEN", "PAT non disponibile nell'ambiente."
    if not project_ref:
        return None, "NO_PROJECT_REF", "Project ref non configurato."

    url = "https://api.supabase.com/v1/projects/" + urllib.parse.quote(project_ref, safe="")
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "supabase-multi-local/3.5.5"
        },
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
        p = json.loads(body)
        if not isinstance(p, dict):
            return None, "BAD_RESPONSE", "Risposta Management API non valida."

        returned_ref = p.get("ref") or p.get("id") or ""
        if returned_ref and returned_ref != project_ref:
            return None, "REF_MISMATCH", "Il PAT ha risposto per un project_ref diverso da quello configurato."

        return {
            "status": p.get("status") or "UNKNOWN",
            "region": p.get("region") or "",
            "name": p.get("name") or "",
            "source": "PAT"
        }, "", ""

    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:500]
        except Exception:
            detail = str(e)

        if e.code == 401:
            return None, "AUTH_ERROR", detail or "PAT non valido/scaduto."
        if e.code == 403:
            return None, "FORBIDDEN", detail or "PAT senza Project Settings: Read per questo progetto."
        if e.code == 404:
            return None, "NOT_FOUND", detail or "Project ref non trovato o non accessibile dal PAT."
        if e.code == 429:
            return None, "RATE_LIMIT", detail or "Rate limit Management API."

        return None, f"HTTP_{e.code}", detail or str(e)

    except Exception as e:
        return None, "ERROR", str(e)[:500]

def platform_status_from_cli(account):
    """Return {project_ref: status} for one CLI profile. Never raises to callers."""
    try:
        profile = cli_profile_name(account)
        r = run_supabase(["--profile", profile, "projects", "list", "-o", "json"], timeout=45)
        if not r["ok"]:
            return {}, (r["stderr"] or r["stdout"] or "").strip()[:300]
        data = json.loads(r["stdout"] or "[]")
        items = normalize_projects(data)
        result = {}
        for p in items:
            ref = p.get("ref")
            if ref:
                result[ref] = {
                    "status": p.get("status") or "UNKNOWN",
                    "region": p.get("region") or "",
                    "name": p.get("name") or ""
                }
        return result, ""
    except Exception as e:
        return {}, str(e)[:300]

def build_platform_status_cache(reg):
    """Query every configured CLI account once, then merge by project_ref."""
    by_ref = {}
    account_errors = {}
    for account in reg.get("accounts", {}):
        statuses, err = platform_status_from_cli(account)
        if err:
            account_errors[account] = err
        for ref, info in statuses.items():
            # Prefer the status from the account the project is actually assigned to later.
            by_ref.setdefault(ref, []).append((account, info))
    return by_ref, account_errors

def normalize_platform_status(raw):
    s = str(raw or "UNKNOWN").upper()
    if s in {"ACTIVE_HEALTHY", "ACTIVE"}:
        return "ACTIVE"
    if s in {"INACTIVE", "PAUSED"}:
        return "PAUSED"
    if "RESTOR" in s:
        return "RESTORING"
    if "START" in s or "COMING_UP" in s:
        return "STARTING"
    if "FAIL" in s or "ERROR" in s or "UNHEALTHY" in s:
        return "ERROR"
    return s or "UNKNOWN"

def state_payload(check_remote=True):
    reg=migrate_legacy_cli_profile_flags(read_registry())
    remote_by_ref, remote_errors = build_platform_status_cache(reg) if check_remote else ({}, {})

    accounts=[]
    for name,acc in reg.get("accounts",{}).items():
        de=acc.get("discovery_token_env","")
        used=[n for n,p in reg.get("projects",{}).items() if p.get("account")==name]
        profile_dir=browser_profile_dir(name)
        accounts.append({
            "name":name,
            "label":acc.get("label",name),
            "email":acc.get("email",""),
            "browser":acc.get("browser","default"),
            "login_method":acc.get("login_method","unknown"),
            "browser_profile_ready":profile_dir.exists() and any(profile_dir.iterdir()),
            "discovery_token_env":de,
            "discovery_token_ok":env_exists(de) if de else False,
            "oauth_connected":cli_profile_status(name, acc) if check_remote else False,
            "platform_check_ok": name not in remote_errors,
            "platform_check_error": remote_errors.get(name,""),
            "enabled":acc.get("enabled",True),
            "identity_complete": bool(acc.get("email")) and acc.get("login_method","unknown")!="unknown",
            "used_by":used,
            "is_legacy_candidate": (not acc.get("email")) and len(used) <= 1
        })

    prefix=reg.get("defaults",{}).get("mcp_prefix","sb_")
    projects=[]
    for name,p in reg.get("projects",{}).items():
        te=project_token_env(reg,p)
        account_name=p.get("account","")
        acc=reg.get("accounts",{}).get(account_name,{})
        ref=p.get("project_ref","")

        candidates=remote_by_ref.get(ref,[])
        cli_chosen=None
        for account,info in candidates:
            if account==account_name:
                cli_chosen=info
                break
        if cli_chosen is None and candidates:
            cli_chosen=candidates[0][1]

        # Primary check: the project's own PAT via Management API.
        pat_info, pat_error_kind, pat_error_detail = project_status_from_pat(ref, te) if check_remote else (None, "NOT_CHECKED", "Remote verification not requested.")

        chosen = pat_info if pat_info is not None else cli_chosen
        status_source = "PAT" if pat_info is not None else ("CLI" if cli_chosen is not None else "NONE")

        raw_status=(chosen or {}).get("status","UNKNOWN")
        platform_status=normalize_platform_status(raw_status)
        platform_seen=chosen is not None

        projects.append({
            "name":name,
            "label":p.get("label",name),
            "account":account_name,
            "account_email":acc.get("email",""),
            "browser":acc.get("browser","default"),
            "login_method":acc.get("login_method","unknown"),
            "project_ref":ref,
            "environment":p.get("environment","production"),
            "read_only":p.get("read_only",False),
            "token_env":te or "",
            "token_ok":env_exists(te) if te else False,
            "enabled":p.get("enabled",True),
            "platform_seen":platform_seen,
            "platform_status_raw":raw_status,
            "platform_status":platform_status,
            "platform_region":(chosen or {}).get("region",""),
            "status_source":status_source,
            "pat_status_error_kind":pat_error_kind,
            "pat_status_error_detail":pat_error_detail,
            "mcp":prefix+name
        })

    return {
        "root":str(ROOT),
        "accounts":accounts,
        "projects":projects,
        "orphan_secrets":orphaned_supabase_secret_envs(reg),
        "platform_checked_at":time.strftime("%Y-%m-%dT%H:%M:%S")
    }

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(UI_DIR),**kw)
    def log_message(self,fmt,*args): sys.stdout.write("[ui] "+fmt%args+"\n")
    def send_json(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b)))
        self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(b)
    def read_json(self):
        l=int(self.headers.get("Content-Length","0")); raw=self.rfile.read(l); return json.loads(raw.decode()) if raw else {}
    def do_GET(self):
        p=urlparse(self.path)
        if p.path=="/api/state":
            try:self.send_json({"ok":True,"data":state_payload(check_remote=urllib.parse.parse_qs(p.query).get("local", ["0"])[0] != "1")})
            except Exception as e:self.send_json({"ok":False,"error":str(e)},500)
            return
        if p.path=="/oauth/callback":
            q=urllib.parse.parse_qs(p.query)
            try:
                if "error" in q: raise RuntimeError(q.get("error_description",q["error"])[0])
                account=oauth_exchange(q.get("state",[""])[0],q.get("code",[""])[0])
                html=f"<html><body style='font-family:system-ui;background:#0b0d10;color:white;padding:40px'><h2>Account connesso</h2><p>{account} Ã¨ ora collegato in modalitÃ  semplice.</p><p>Puoi chiudere questa scheda e tornare al pannello.</p><script>setTimeout(()=>window.close(),2500)</script></body></html>"
                b=html.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
            except Exception as e:
                b=f"<html><body><h2>Errore OAuth</h2><pre>{str(e)}</pre></body></html>".encode();self.send_response(400);self.send_header("Content-Type","text/html");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
            return
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        try:
            body=self.read_json()
            if path=="/api/resolve":
                reg=read_registry()
                result=resolve_project_candidates(
                    reg,
                    target=body.get("target"),
                    project_ref=body.get("project_ref"),
                    account=body.get("account"),
                    repo_path=body.get("repo_path"),
                    name=body.get("name")
                )
                self.send_json({"ok":True,**result});return
            if path=="/api/sql-query":
                project=(body.get("project") or "").strip()
                query=(body.get("query") or "").strip()
                result=execute_project_sql(read_registry(),project,query,read_only=True)
                self.send_json({"ok":True,"message":"Read-only SQL completed.","result":result});return
            if path=="/api/sql-execute":
                if body.get("confirm") is not True:
                    raise ValueError("SQL write execution requires confirm=true.")
                project=(body.get("project") or "").strip()
                query=(body.get("query") or "").strip()
                result=execute_project_sql(read_registry(),project,query,read_only=False)
                self.send_json({"ok":True,"message":"SQL execution completed.","result":result});return
            if path=="/api/project-token-copy":
                project=(body.get("project") or "").strip()
                source_env=(body.get("source_env") or "").strip()
                reg=read_registry()
                p=reg.get("projects",{}).get(project)
                if not p: raise ValueError("Project not found.")
                target_env=(p.get("token_env") or "").strip()
                if not target_env: raise ValueError("Project token_env is not configured.")
                copy_user_env_secret(source_env,target_env)
                self.send_json({"ok":True,"message":f"Project PAT copied into {target_env}.","project":project,"token_env":target_env});return
            if path=="/api/discovery-token-copy":
                account=(body.get("account") or "").strip()
                source_env=(body.get("source_env") or "").strip()
                reg=read_registry()
                acc=reg.get("accounts",{}).get(account)
                if not acc: raise ValueError("Account not found.")
                target_env=(acc.get("discovery_token_env") or "").strip()
                if not target_env: raise ValueError("Account discovery_token_env is not configured.")
                copy_user_env_secret(source_env,target_env)
                self.send_json({"ok":True,"message":f"Discovery PAT copied into {target_env}.","account":account,"token_env":target_env});return
            if path=="/api/orphan-secret-remove":
                reg=read_registry()
                removed=delete_orphan_secret(reg, body.get("name",""))
                self.send_json({"ok":True,"message":f"Environment variable '{removed}' removed."});return
            if path=="/api/orphan-secrets-clean":
                reg=read_registry()
                names=orphaned_supabase_secret_envs(reg)
                removed=[]
                for name in names:
                    # Re-check every item immediately before deletion.
                    removed.append(delete_orphan_secret(read_registry(), name))
                self.send_json({"ok":True,"message":f"Removed {len(removed)} orphaned environment variable(s).","removed":removed});return
            if path=="/api/account":
                name=body.get("name","").strip()
                label=body.get("label","").strip() or name
                email=body.get("email","").strip()
                browser=(body.get("browser","default") or "default").strip().lower()
                login_method=(body.get("login_method","unknown") or "unknown").strip().lower()
                de=body.get("discovery_token_env","").strip()
                original=body.get("original_name","").strip()
                enabled=bool(body.get("enabled",True))
                if not name: raise ValueError("Nome account obbligatorio.")
                if browser not in {"default","brave","edge","chrome"}: raise ValueError("Browser non valido.")
                if login_method not in {"unknown","classic","github","google"}: raise ValueError("Invalid login method.")
                reg=read_registry();reg.setdefault("accounts",{})
                if original and original!=name:
                    if name in reg["accounts"]: raise ValueError("Alias giÃ  esistente.")
                    reg["accounts"][name]=reg["accounts"].pop(original)
                    for p in reg.get("projects",{}).values():
                        if p.get("account")==original:p["account"]=name
                    old_dir=browser_profile_dir(original); new_dir=browser_profile_dir(name)
                    if old_dir.exists() and not new_dir.exists():
                        old_dir.rename(new_dir)
                x=reg["accounts"].get(name,{})
                if "cli_profile_managed" not in x:
                    x["cli_profile_managed"]=False
                x.update({
                    "label":label,
                    "email":email,
                    "browser":browser,
                    "login_method":login_method,
                    "discovery_token_env":de,
                    "enabled":enabled
                })
                reg["accounts"][name]=x
                write_registry(reg)
                self.send_json({"ok":True,"message":f"Account '{name}' salvato."});return
            if path=="/api/account-remove":
                name=body.get("name","");reg=read_registry()
                used=[n for n,p in reg.get("projects",{}).items() if p.get("account")==name]
                if used: raise ValueError("Account usato da: "+", ".join(used))
                acc=reg.get("accounts",{}).pop(name,None)
                if not acc: raise ValueError("Account not found.")
                write_registry(reg)
                if body.get("clear_tokens"): clear_user_env(acc.get("token_env"));clear_user_env(acc.get("discovery_token_env"))
                self.send_json({"ok":True,"message":"Account rimosso dal registry. Le variabili ambiente PAT non sono state cancellate."});return
            if path=="/api/token":
                account=body.get("account","")
                kind=body.get("kind","discovery")
                token=body.get("token","").strip()
                reg=read_registry();acc=reg.get("accounts",{}).get(account)
                if not acc or not token: raise ValueError("Account/token mancanti.")
                if kind!="discovery": raise ValueError("Il PAT operativo appartiene al progetto, non all'account.")
                env=acc.get("discovery_token_env")
                if not env: raise ValueError("discovery_token_env non configurato.")
                set_user_env(env,token)
                self.send_json({"ok":True,"message":f"Discovery PAT salvato in {env}."});return
            if path=="/api/token-clear":
                account=body.get("account","");reg=read_registry()
                env=reg.get("accounts",{}).get(account,{}).get("discovery_token_env")
                if not env: raise ValueError("Variabile Discovery PAT non configurata.")
                clear_user_env(env);self.send_json({"ok":True,"message":f"{env} rimossa."});return
            if path=="/api/oauth-start":
                account=body.get("account","")
                reg=read_registry()
                if account not in reg.get("accounts",{}): raise ValueError("Account not found.")
                profile=cli_profile_login(account)
                reg["accounts"][account]["cli_profile_managed"]=True
                write_registry(reg)
                self.send_json({"ok":True,"message":f"Supabase login started for named profile '{profile}'. Complete the flow in the opened window."});return
            if path=="/api/oauth-disconnect":
                account=body.get("account","")
                reg=read_registry()
                if account not in reg.get("accounts",{}): raise ValueError("Account not found.")
                r=cli_profile_logout(account)
                reg["accounts"][account]["cli_profile_managed"]=False
                write_registry(reg)
                if not r["ok"]:
                    raise RuntimeError((r["stderr"] or r["stdout"] or "Supabase CLI logout failed.")[:500])
                self.send_json({"ok":True,"message":"Supabase CLI profile disconnected."});return
            if path=="/api/discover":
                account=body.get("account","");mode=body.get("mode","oauth");reg=read_registry()
                if mode=="oauth": projects=supabase_list_projects_cli(account)
                else:
                    env=account_discovery_env(reg,account);token=env_get(env)
                    if not token: raise ValueError("Discovery PAT account-wide mancante.")
                    projects=supabase_list_projects_pat(token)
                known={p.get("project_ref"):n for n,p in reg.get("projects",{}).items() if p.get("project_ref")}
                for p in projects:p["already_imported"]=p["ref"] in known;p["existing_target"]=known.get(p["ref"])
                self.send_json({"ok":True,"projects":projects,"count":len(projects)});return
            if path=="/api/project":
                name=body.get("name","").strip();account=body.get("account","").strip();ref=body.get("project_ref","").strip()
                original=body.get("original_name","").strip()
                if not name or not account or not ref: raise ValueError("Target/account/project_ref obbligatori.")
                reg=read_registry();reg.setdefault("projects",{});features=reg.setdefault("defaults",{}).get("features") or DEFAULT_FEATURES
                if account not in reg.get("accounts",{}):
                    raise ValueError("Supabase account not found.")
                if original and original!=name:
                    if name in reg["projects"]:
                        raise ValueError("Esiste giÃ  un progetto con questo target.")
                    if original not in reg["projects"]:
                        raise ValueError("Progetto originale non trovato.")
                    reg["projects"][name]=reg["projects"].pop(original)
                x=reg["projects"].get(name,{})
                x.update({"label":body.get("label","").strip() or name,"account":account,"project_ref":ref,
                          "environment":body.get("environment","production"),"read_only":bool(body.get("read_only",False)),
                          "features":x.get("features") or features,"token_env":body.get("token_env","").strip() or None,
                          "enabled":bool(body.get("enabled",True))})
                reg["projects"][name]=x;write_registry(reg);self.send_json({"ok":True,"message":f"Target '{name}' salvato."});return
            if path=="/api/import-projects":
                account=body.get("account","");items=body.get("projects",[]);reg=read_registry();reg.setdefault("projects",{})
                features=reg.setdefault("defaults",{}).get("features") or DEFAULT_FEATURES;imp=[];skip=[]
                for it in items:
                    target=(it.get("target") or "").strip();ref=(it.get("ref") or "").strip()
                    if not target or not ref or target in reg["projects"]:skip.append(target or ref);continue
                    reg["projects"][target]={"label":it.get("label") or target,"account":account,"project_ref":ref,"environment":"production",
                                             "read_only":False,"features":features,"token_env":(it.get("token_env") or "").strip() or None,"enabled":True}
                    imp.append(target)
                if imp:write_registry(reg)
                self.send_json({"ok":True,"message":f"Importati {len(imp)} target.","imported":imp,"skipped":skip});return
            if path=="/api/project-remove":
                name=(body.get("name") or "").strip()
                if not name: raise ValueError("Missing project name.")
                reg=read_registry()
                p=reg.get("projects",{}).pop(name,None)
                if not p: raise ValueError("Project not found.")
                write_registry(reg)
                self.send_json({
                    "ok":True,
                    "message":f"Progetto '{name}' rimosso dal registry. Le variabili ambiente PAT non sono state cancellate."
                });return

            if path=="/api/project-token":
                project=body.get("project","").strip()
                token=body.get("token","").strip()
                reg=read_registry()
                p=reg.get("projects",{}).get(project)
                if not p: raise ValueError("Project not found.")
                env=(p.get("token_env") or "").strip()
                if not env: raise ValueError("token_env del progetto non configurato.")
                if not token: raise ValueError("Missing project PAT.")
                set_user_env(env,token)
                self.send_json({"ok":True,"message":f"PAT salvato in modo sicuro nella variabile Windows {env}. Il valore non Ã¨ stato scritto nel registry."});return
            if path=="/api/project-token-clear":
                project=body.get("project","").strip()
                reg=read_registry()
                p=reg.get("projects",{}).get(project)
                if not p: raise ValueError("Project not found.")
                env=(p.get("token_env") or "").strip()
                if not env: raise ValueError("token_env del progetto non configurato.")
                clear_user_env(env)
                self.send_json({"ok":True,"message":f"{env} rimossa."});return

            if path=="/api/project-pat-check":
                project=body.get("project","").strip()
                reg=read_registry()
                p=reg.get("projects",{}).get(project)
                if not p: raise ValueError("Project not found.")

                ref=(p.get("project_ref") or "").strip()
                account=(p.get("account") or "").strip()
                env=(p.get("token_env") or "").strip()

                pat_info=None
                pat_error_kind=""
                pat_error_detail=""

                if not env:
                    pat_error_kind="TOKEN_ENV_MISSING"
                    pat_error_detail="PAT env non configurata."
                else:
                    token=read_token_env_value(env)
                    if not token:
                        pat_error_kind="TOKEN_MISSING"
                        pat_error_detail=f"Nessun PAT trovato nella variabile {env}."
                    else:
                        pat_info, pat_error_kind, pat_error_detail=project_status_from_pat(ref,env)

                if pat_info is not None:
                    status=normalize_platform_status(pat_info.get("status"))
                    self.send_json({
                        "ok":True,
                        "message":f"Accesso verificato via PAT per {project}. Stato Supabase: {status}.",
                        "project":project,
                        "token_env":env,
                        "platform_status":status,
                        "raw_status":pat_info.get("status","UNKNOWN"),
                        "source":"PAT",
                        "fallback_used":False
                    });return

                # PAT assente, non valido o senza permessi: prova la CLI dell'account.
                cli_statuses, cli_error=platform_status_from_cli(account)
                cli_info=cli_statuses.get(ref) if ref else None
                if cli_info is not None:
                    status=normalize_platform_status(cli_info.get("status"))
                    reason=pat_error_kind or "PAT_UNAVAILABLE"
                    self.send_json({
                        "ok":True,
                        "message":f"Accesso verificato via CLI per {project}. Stato Supabase: {status}.",
                        "project":project,
                        "token_env":env,
                        "platform_status":status,
                        "raw_status":cli_info.get("status","UNKNOWN"),
                        "source":"CLI",
                        "fallback_used":True,
                        "fallback_reason":reason,
                        "pat_detail":pat_error_detail
                    });return

                parts=[]
                if pat_error_kind:
                    parts.append(f"PAT: {pat_error_kind}")
                if pat_error_detail:
                    parts.append(pat_error_detail)
                if cli_error:
                    parts.append(f"CLI: {cli_error}")
                else:
                    parts.append("CLI: progetto non trovato nel profilo dell'account.")
                self.send_json({
                    "ok":False,
                    "error":"ACCESS_CHECK_FAILED",
                    "message":" | ".join(parts),
                    "token_env":env,
                    "source":"NONE"
                },400);return

            if path=="/api/reassign-project":
                project_name=(body.get("project") or "").strip()
                target_account=(body.get("target_account") or "").strip()
                reg=read_registry()
                if target_account not in reg.get("accounts",{}):
                    raise ValueError("Account destinazione non trovato.")
                project=reg.get("projects",{}).get(project_name)
                if not project:
                    raise ValueError("Project not found.")
                old_account=project.get("account","")
                project["account"]=target_account
                write_registry(reg)
                self.send_json({
                    "ok":True,
                    "message":f"Progetto '{project_name}' riassegnato da '{old_account}' a '{target_account}'.",
                    "old_account":old_account,
                    "target_account":target_account
                });return
            if path=="/api/delete-empty-account":
                account=(body.get("account") or "").strip()
                reg=read_registry()
                if account not in reg.get("accounts",{}):
                    raise ValueError("Account not found.")
                used=[n for n,p in reg.get("projects",{}).items() if p.get("account")==account]
                if used:
                    raise ValueError("Account ancora associato a progetti: "+", ".join(used))
                reg["accounts"].pop(account,None)
                write_registry(reg)
                self.send_json({"ok":True,"message":f"Account legacy vuoto '{account}' eliminato."});return
            if path=="/api/open-project":
                reg=read_registry()
                project_name=(body.get("project") or "").strip()
                account=(body.get("account") or "").strip()
                ref=(body.get("project_ref") or "").strip()
                if project_name:
                    p=reg.get("projects",{}).get(project_name)
                    if not p: raise ValueError("Project not found.")
                    account=p.get("account","")
                    ref=p.get("project_ref","")
                if not account or not ref: raise ValueError("Account/project_ref mancanti.")
                result=launch_project_browser(account,ref)
                acc=reg.get("accounts",{}).get(account,{})
                email=acc.get("email","")
                login_method=acc.get("login_method","unknown")
                identity_complete=bool(email) and login_method!="unknown"
                self.send_json({
                    "ok":True,
                    "message":f"Progetto aperto nel profilo browser '{account}' ({result['browser']}).",
                    "result":result,
                    "login_hint":{
                        "account":account,
                        "email":email,
                        "login_method":login_method,
                        "identity_complete":identity_complete
                    }
                });return
            if path=="/api/sync":
                r=run_ps_manager("mcp-sync");self.send_json({"ok":r["ok"],"message":"mcp-sync completato." if r["ok"] else "mcp-sync fallito.","result":r},200 if r["ok"] else 500);return
            if path=="/api/doctor":
                r=run_ps_manager("doctor");self.send_json({"ok":r["ok"],"message":"Doctor completato." if r["ok"] else "Doctor ha rilevato errori.","result":r},200 if r["ok"] else 500);return
            if path=="/api/sync-doctor":
                s=run_ps_manager("mcp-sync");d=run_ps_manager("doctor") if s["ok"] else {"ok":False,"stdout":"","stderr":"Doctor non eseguito.","code":-1}
                ok=s["ok"] and d["ok"];self.send_json({"ok":ok,"message":"Sync + Doctor completati." if ok else "Sync + Doctor non completati.","sync":s,"doctor":d},200 if ok else 500);return
            self.send_json({"ok":False,"error":"Endpoint not found."},404)
        except Exception as e:self.send_json({"ok":False,"error":str(e)},400)

def main():
    print("Supabase Multi Local Admin v3.5.3")
    print(f"http://{HOST}:{PORT}  (localhost only)")
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    threading.Timer(.8,lambda:webbrowser.open(f"http://{HOST}:{PORT}")).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=="__main__":main()

