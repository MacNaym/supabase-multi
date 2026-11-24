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
    listed = module.list_database_backups("example-prod")

    assert listed["count"] == 1
    assert listed["backups"][0]["backup_dir"] == created["backup_dir"]
    assert listed["backups"][0]["mode"] == "schema"
