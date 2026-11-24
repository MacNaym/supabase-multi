from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "mcp" / "headless_control_plane.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_multi_headless_backup", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_project(monkeypatch, module, *, backup_dir=None, db_password_env=None):
    monkeypatch.setattr(module, "_backup_preflight", lambda cli: None)
    project = {
        "enabled": True,
        "read_only": False,
        "project_ref": "abcdefghijklmnopqrst",
        "token_env": "SUPABASE_PAT_EXAMPLE",
    }
    if backup_dir:
        project["backup_dir"] = str(backup_dir)
    if db_password_env:
        project["db_password_env"] = db_password_env
    monkeypatch.setattr(
        module,
        "read_registry",
        lambda: {"projects": {"example-prod": project}},
    )
    return project


def fake_cli(monkeypatch, module, *, password_available=False):
    access_token = "sbp_project_scoped_secret"
    db_password = "database-password-secret"
    monkeypatch.setattr(module.shutil, "which", lambda name: "supabase.exe")

    def fake_env(name):
        if name == "SUPABASE_PAT_EXAMPLE":
            return access_token
        if password_available and name in {"SUPABASE_DB_PASSWORD_EXAMPLE_PROD", "CUSTOM_DB_PASSWORD"}:
            return db_password
        return ""

    monkeypatch.setattr(module, "read_token_env_value", fake_env)

    seen = []

    def fake_run(command, capture_output=True, text=True, timeout=None, env=None):
        seen.append({"command": list(command), "env": dict(env or {})})
        if command == ["supabase.exe", "--version"]:
            return SimpleNamespace(returncode=0, stdout="3.0.0\n", stderr="")
        assert command[:3] == ["supabase.exe", "db", "dump"]
        output = Path(command[command.index("-f") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("backup for " + output.name + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return access_token, db_password, seen


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("schema", {"schema.sql"}),
        ("data", {"data.sql"}),
        ("full", {"roles.sql", "schema.sql", "data.sql"}),
    ],
)
def test_backup_database_uses_project_ref_and_pat(monkeypatch, tmp_path, mode, expected):
    module = load_module()
    install_project(monkeypatch, module)
    access_token, db_password, seen = fake_cli(monkeypatch, module)

    result = module.backup_database(
        "example-prod",
        mode=mode,
        destination=str(tmp_path),
    )

    backup_dir = Path(result["backup_dir"])
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))

    assert {item["name"] for item in manifest["files"]} == expected
    assert result["verified"] is True
    assert result["credential_mode"] == "temporary-login"
    assert result["token_env"] == "SUPABASE_PAT_EXAMPLE"
    assert access_token not in json.dumps(result)
    assert access_token not in json.dumps(manifest)
    assert db_password not in json.dumps(result)

    dump_calls = [x for x in seen if x["command"][:3] == ["supabase.exe", "db", "dump"]]
    assert len(dump_calls) == len(expected)
    for item in dump_calls:
        call = item["command"]
        assert "--remote=abcdefghijklmnopqrst" in call
        assert call[call.index("--profile")+1] == "supabase"
        assert "--password" not in call
        assert item["env"]["SUPABASE_ACCESS_TOKEN"] == access_token


def test_backup_database_uses_project_default_destination(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module, backup_dir=tmp_path)
    fake_cli(monkeypatch, module)

    result = module.backup_database("example-prod", mode="schema")

    assert Path(result["backup_dir"]).is_relative_to(tmp_path)


def test_backup_database_explicit_destination_wins(monkeypatch, tmp_path):
    module = load_module()
    configured = tmp_path / "configured"
    explicit = tmp_path / "explicit"
    install_project(monkeypatch, module, backup_dir=configured)
    fake_cli(monkeypatch, module)

    result = module.backup_database(
        "example-prod",
        mode="schema",
        destination=str(explicit),
    )

    assert Path(result["backup_dir"]).is_relative_to(explicit)


def test_backup_database_retries_with_password_fallback(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    access_token = "sbp_project_scoped_secret"
    db_password = "database-password-secret"
    monkeypatch.setattr(module.shutil, "which", lambda name: "supabase.exe")

    def fake_env(name):
        if name == "SUPABASE_PAT_EXAMPLE":
            return access_token
        if name == "SUPABASE_DB_PASSWORD_EXAMPLE_PROD":
            return db_password
        return ""

    monkeypatch.setattr(module, "read_token_env_value", fake_env)
    calls = []

    def fake_run(command, capture_output=True, text=True, timeout=None, env=None):
        calls.append(list(command))
        if command == ["supabase.exe", "--version"]:
            return SimpleNamespace(returncode=0, stdout="3.0.0\n", stderr="")
        output = Path(command[command.index("-f") + 1])
        if "--password" not in command:
            return SimpleNamespace(returncode=1, stdout="", stderr="temporary login failed")
        assert command[command.index("--password") + 1] == db_password
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("fallback backup\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.backup_database(
        "example-prod",
        mode="schema",
        destination=str(tmp_path),
    )

    assert result["credential_mode"] == "database-password-fallback"
    assert len([x for x in calls if x[:3] == ["supabase.exe", "db", "dump"]]) == 2


def test_backup_database_redacts_access_token_and_password(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    access_token = "sbp_project_scoped_secret"
    db_password = "database-password-secret"
    monkeypatch.setattr(module.shutil, "which", lambda name: "supabase.exe")

    def fake_env(name):
        if name == "SUPABASE_PAT_EXAMPLE":
            return access_token
        if name == "SUPABASE_DB_PASSWORD_EXAMPLE_PROD":
            return db_password
        return ""

    monkeypatch.setattr(module, "read_token_env_value", fake_env)

    def fail_run(command, capture_output=True, text=True, timeout=None, env=None):
        if "--password" in command:
            return SimpleNamespace(returncode=1, stdout="", stderr=f"auth {access_token} {db_password}")
        return SimpleNamespace(returncode=1, stdout="", stderr=f"auth {access_token}")

    monkeypatch.setattr(module.subprocess, "run", fail_run)

    with pytest.raises(RuntimeError) as exc:
        module.backup_database(
            "example-prod",
            mode="schema",
            destination=str(tmp_path),
        )

    message = str(exc.value)
    assert access_token not in message
    assert db_password not in message
    assert "[REDACTED_ACCESS_TOKEN]" in message or "[REDACTED_DB_PASSWORD]" in message
    assert not any(tmp_path.rglob("manifest.json"))


def test_verify_database_backup_detects_tampering(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    fake_cli(monkeypatch, module)

    result = module.backup_database(
        "example-prod",
        mode="schema",
        destination=str(tmp_path),
    )

    assert module.verify_database_backup(result["backup_dir"])["ok"] is True

    schema = Path(result["backup_dir"]) / "schema.sql"
    schema.write_text("tampered\n", encoding="utf-8")

    verification = module.verify_database_backup(result["backup_dir"])
    assert verification["ok"] is False
    assert verification["files"][0]["ok"] is False


def test_backup_database_requires_project_pat(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "")

    with pytest.raises(ValueError, match="SUPABASE_PAT_EXAMPLE"):
        module.backup_database(
            "example-prod",
            mode="full",
            destination=str(tmp_path),
        )


def test_list_database_backups(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module, backup_dir=tmp_path)
    fake_cli(monkeypatch, module)

    created = module.backup_database("example-prod", mode="schema")
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "")
    listed = module.list_database_backups("example-prod")

    assert listed["count"] == 1
    assert listed["backups"][0]["backup_dir"] == created["backup_dir"]
    assert listed["backups"][0]["mode"] == "schema"


def test_backup_preflight_rejects_old_cli(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="--linked", stderr=""))
    with pytest.raises(RuntimeError, match="CLI v3"):
        module._backup_preflight("supabase")


def test_backup_preflight_rejects_stopped_docker(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module.shutil, "which", lambda name: name)
    def run(command, **kwargs):
        if command[0] == "supabase":
            return SimpleNamespace(returncode=0, stdout="--remote", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="engine unavailable")
    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="Docker engine"):
        module._backup_preflight("supabase")


def test_profile_error_does_not_trigger_password_fallback(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    fake_cli(monkeypatch, module, password_available=True)
    calls = []
    def fail(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1, stdout="", stderr='failed to read profile: unsupported config file type "pes84"')
    monkeypatch.setattr(module.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="unsupported config"):
        module.backup_database("example-prod", mode="schema", destination=str(tmp_path))
    assert len(calls) == 1
    assert "--password" not in calls[0]
    assert not any(tmp_path.rglob("manifest.json"))


def test_ipv6_fallback_reuses_pooler_for_all_dumps(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    fake_cli(monkeypatch, module)
    calls = []
    pooler_requests = []
    ref = "abcdefghijklmnopqrst"
    secret = "temporary-password"
    url = f"postgresql://cli_login_postgres.{ref}:{secret}@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
    def pooler(project_ref, token, password):
        pooler_requests.append((project_ref, token, password))
        return url
    monkeypatch.setattr(module, "_backup_pooler_url", pooler)
    def run(command, **kwargs):
        if command[-1] == "--version":
            return SimpleNamespace(returncode=0, stdout="3.3.0", stderr="")
        target = next(x for x in command if x.startswith("--remote="))
        calls.append(target)
        if target == "--remote=" + ref:
            return SimpleNamespace(returncode=1, stdout="", stderr="IPv6 is not supported on your current network")
        Path(command[command.index("-f")+1]).write_text("dump", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(module.subprocess, "run", run)
    result = module.backup_database("example-prod", mode="full", destination=str(tmp_path))
    assert calls == ["--remote="+ref] + ["--remote="+url]*3
    assert len(pooler_requests) == 1
    assert pooler_requests[0][0] == ref
    assert result["credential_mode"] == "session-pooler"
    assert secret not in json.dumps(result)
    assert secret not in Path(result["manifest"]).read_text(encoding="utf-8")


def test_pooler_lookup_uses_same_project_and_encodes_password(monkeypatch):
    module = load_module()
    ref = "abcdefghijklmnopqrst"
    calls = []
    def request(project_ref, token, suffix, body=None):
        calls.append((project_ref, token, suffix, body))
        if body is None:
            return [{"database_type":"PRIMARY","db_host":"aws-0-eu-central-1.pooler.supabase.com","db_user":"postgres."+ref,"db_name":"postgres"}]
        return {"role":"cli_login_postgres","password":"p@ss:/word","ttl_seconds":600}
    monkeypatch.setattr(module, "_backup_management_request", request)
    url = module._backup_pooler_url(ref, "test-token")
    assert url == "postgresql://cli_login_postgres."+ref+":p%40ss%3A%2Fword@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
    assert all(x[0] == ref and x[1] == "test-token" for x in calls)
    assert calls[1][3] == {"read_only":False}


def test_pooler_rejects_other_project(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "_backup_management_request", lambda *a: [
        {"database_type":"PRIMARY","db_host":"aws-0-eu-central-1.pooler.supabase.com","db_user":"postgres.otherproject","db_name":"postgres"}
    ])
    with pytest.raises(RuntimeError, match="unique primary"):
        module._backup_pooler_url("abcdefghijklmnopqrst", "test-token")


def test_pooler_error_never_returns_credentials(monkeypatch, tmp_path):
    module = load_module()
    url = "postgresql://user:secret@host:5432/postgres"
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr=url))
    with pytest.raises(RuntimeError) as exc:
        module._run_backup_dump("supabase", "abcdefghijklmnopqrst", "test-token", tmp_path/"schema.sql", [], pooler_url=url)
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize("mode,expected", [
    ("full", ["preflight","connection","roles","schema","data","manifest","verify","complete"]),
    ("schema", ["preflight","connection","schema","manifest","verify","complete"]),
    ("data", ["preflight","connection","data","manifest","verify","complete"]),
])
def test_backup_reports_real_phases(monkeypatch, tmp_path, mode, expected):
    module = load_module()
    install_project(monkeypatch, module)
    fake_cli(monkeypatch, module)
    events = []
    result = module.backup_database("example-prod", mode=mode, destination=str(tmp_path),
                                    progress=lambda phase, **kw: events.append(phase))
    assert events == expected
    assert result["verified"] is True


def test_backup_job_duplicate_and_completion(monkeypatch, tmp_path):
    import threading
    import sys
    monkeypatch.syspath_prepend(str(ROOT))
    spec = importlib.util.spec_from_file_location("backup_ui_job_test", ROOT/"local-ui"/"server.py")
    ui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ui)
    release = threading.Event()
    entered = threading.Event()
    finished = threading.Event()
    reg = {"accounts":{"a":{}}, "projects":{"p":{"account":"a","project_ref":"abcdefghijklmnopqrst"}}}
    monkeypatch.setattr(ui, "read_registry", lambda: reg)
    def backup(project, **kwargs):
        kwargs["progress"]("schema", folder=str(tmp_path))
        entered.set()
        assert release.wait(5)
        kwargs["progress"]("complete")
        return {"backup_dir":str(tmp_path)}
    monkeypatch.setattr(ui, "backup_backend", lambda: SimpleNamespace(backup_database=backup))
    real_thread = threading.Thread
    def thread_factory(target, **kwargs):
        def run():
            try: target()
            finally: finished.set()
        return real_thread(target=run, **kwargs)
    monkeypatch.setattr(ui.threading, "Thread", thread_factory)
    try:
        job_id = ui.start_backup_job("p","a","schema",str(tmp_path),"abcdefghijklmnopqrst")
        assert entered.wait(5)
        job = ui.backup_job_snapshot()
        assert job["id"] == job_id and job["status"] == "running" and job["phase"] == "schema"
        with pytest.raises(ValueError, match="already in progress"):
            ui.start_backup_job("p","a","schema",str(tmp_path),"abcdefghijklmnopqrst")
    finally:
        release.set()
    assert finished.wait(5)
    assert ui.backup_job_snapshot()["status"] == "completed"


def make_validation_fixture(module, tmp_path, mode="full"):
    names = {"full":["roles.sql","schema.sql","data.sql"], "schema":["schema.sql"], "data":["data.sql"]}[mode]
    files=[]
    for name in names:
        path=tmp_path/name
        path.write_text("-- PostgreSQL database dump\nSET statement_timeout = 0;\n", encoding="utf-8")
        files.append({"name":name,"bytes":path.stat().st_size,"sha256":module._sha256_file(path)})
    manifest={"format":"supabase-multi-backup-v1","mode":mode,"project":"example","files":files}
    (tmp_path/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    return manifest


@pytest.mark.parametrize("mode",["full","schema","data"])
def test_advanced_validation_legacy_manifest(tmp_path, mode):
    module=load_module()
    make_validation_fixture(module,tmp_path,mode)
    result=module.validate_database_backup(str(tmp_path))
    assert result["ok"] and result["integrity_ok"] and result["structure_ok"]
    assert result["restore_tested"] is False
    assert result["full_backup"] == (mode=="full")


@pytest.mark.parametrize("change",["missing","duplicate","traversal","bad_hash","modified","empty","binary","not_sql"])
def test_advanced_validation_rejects_bad_backup(tmp_path,change):
    module=load_module()
    manifest=make_validation_fixture(module,tmp_path)
    item=manifest["files"][0]
    path=tmp_path/item["name"]
    if change=="missing": path.unlink()
    elif change=="duplicate": manifest["files"].append(dict(item))
    elif change=="traversal": item["name"]="../roles.sql"
    elif change=="bad_hash": item["sha256"]="bad"
    elif change=="modified": path.write_text("changed",encoding="utf-8")
    else:
        path.write_bytes({"empty":b"","binary":b"SET x=1;\x00","not_sql":b"not SQL"}[change])
        item.update(bytes=path.stat().st_size,sha256=module._sha256_file(path))
    (tmp_path/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    assert module.validate_database_backup(str(tmp_path))["ok"] is False


def test_validation_does_not_execute_sql(tmp_path,monkeypatch):
    module=load_module()
    make_validation_fixture(module,tmp_path)
    monkeypatch.setattr(module.subprocess,"run",lambda *a,**kw: pytest.fail("Validation executed a process"))
    assert module.validate_database_backup(str(tmp_path))["ok"]


def test_import_external_backup_is_report_only_and_hides_sql(tmp_path):
    """Removing import validation or returning dump content must break this."""
    module = load_module()
    make_validation_fixture(module, tmp_path)
    (tmp_path / "schema.sql").write_text(
        "-- PostgreSQL database dump\nCREATE TABLE public.safe_table(id int);\n",
        encoding="utf-8",
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    schema = next(item for item in manifest["files"] if item["name"] == "schema.sql")
    schema.update(bytes=(tmp_path / "schema.sql").stat().st_size, sha256=module._sha256_file(tmp_path / "schema.sql"))
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = module.import_database_backup(str(tmp_path))

    assert report["ok"] is True
    assert report["imported"] is True
    assert report["external"] is True
    assert report["backup_dir"] == str(tmp_path.resolve())
    assert "CREATE TABLE" not in json.dumps(report)
    assert set(path.name for path in tmp_path.iterdir()) == {"roles.sql", "schema.sql", "data.sql", "manifest.json"}


def test_import_external_backup_rejects_invalid_manifest(tmp_path):
    """Removing validation from import must never accept an unsafe source."""
    module = load_module()
    make_validation_fixture(module, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"].append(dict(manifest["files"][0]))
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = module.import_database_backup(str(tmp_path))

    assert report["ok"] is False
    assert report["imported"] is False


def test_runtime_bridge_advertises_and_dispatches_safe_backup_inspection(monkeypatch):
    """Removing a safe inspection operation from the whitelist must break this."""
    import importlib
    import sys

    monkeypatch.syspath_prepend(str(ROOT / "mcp"))
    bridge = importlib.import_module("runtime_bridge")
    backend = SimpleNamespace(
        validate_database_backup=lambda path: {"ok": True, "path": path},
        import_database_backup=lambda path: {"ok": True, "imported": True, "path": path},
    )
    monkeypatch.setattr(bridge, "_headless_module", lambda: backend)

    names = {item["operation"] for item in bridge.get_capabilities()["capabilities"]}

    assert {"validate_database_backup", "import_database_backup"} <= names
    assert bridge.invoke_live_capability("validate_database_backup", {"path": "C:/safe"})["ok"]
    assert bridge.invoke_live_capability("import_database_backup", {"path": "C:/safe"})["imported"]
    assert "remote_restore" not in names


def test_control_plane_browser_autostart_can_be_disabled(monkeypatch):
    """Ignoring --no-browser or the launcher guard must make this fail."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("backup_ui_browser_test", ROOT / "local-ui" / "server.py")
    ui = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(ui)

    assert ui.browser_autostart_enabled(["server.py"], {}) is True
    assert ui.browser_autostart_enabled(["server.py", "--no-browser"], {}) is False
    assert ui.browser_autostart_enabled(["server.py"], {"SUPABASE_MULTI_NO_BROWSER": "1"}) is False
    assert ui.browser_autostart_enabled(["server.py"], {"SUPABASE_MULTI_LAUNCHER": "1"}) is False
