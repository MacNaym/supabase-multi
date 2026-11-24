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


def install_project(monkeypatch, module, *, db_url_env=None):
    project = {
        "enabled": True,
        "read_only": False,
        "project_ref": "abcdefghijklmnopqrst",
        "token_env": "SUPABASE_PAT_EXAMPLE",
    }
    if db_url_env:
        project["db_url_env"] = db_url_env
    monkeypatch.setattr(
        module,
        "read_registry",
        lambda: {"projects": {"example-prod": project}},
    )
    return project


def fake_cli(monkeypatch, module, tmp_path):
    secret = "postgresql://postgres.example:very-secret@pooler.example.com:5432/postgres"
    monkeypatch.setattr(module.shutil, "which", lambda name: "supabase.exe")

    def fake_env(name):
        if name in {"SUPABASE_DB_URL_EXAMPLE_PROD", "CUSTOM_DB_URL"}:
            return secret
        return ""

    monkeypatch.setattr(module, "read_token_env_value", fake_env)

    seen = []

    def fake_run(command, capture_output=True, text=True, timeout=None):
        seen.append(list(command))
        if command == ["supabase.exe", "--version"]:
            return SimpleNamespace(returncode=0, stdout="2.99.0\n", stderr="")
        assert command[:3] == ["supabase.exe", "db", "dump"]
        output = Path(command[command.index("-f") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("backup for " + output.name + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return secret, seen


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("schema", {"schema.sql"}),
        ("data", {"data.sql"}),
        ("full", {"roles.sql", "schema.sql", "data.sql"}),
    ],
)
def test_backup_database_modes_create_manifest_and_hashes(monkeypatch, tmp_path, mode, expected):
    module = load_module()
    install_project(monkeypatch, module)
    secret, seen = fake_cli(monkeypatch, module, tmp_path)

    result = module.backup_database(
        "example-prod",
        mode=mode,
        destination=str(tmp_path),
    )

    backup_dir = Path(result["backup_dir"])
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))

    assert {item["name"] for item in manifest["files"]} == expected
    assert result["verified"] is True
    assert result["db_url_env"] == "SUPABASE_DB_URL_EXAMPLE_PROD"
    assert secret not in json.dumps(result)
    assert secret not in json.dumps(manifest)

    dump_calls = [call for call in seen if call[:3] == ["supabase.exe", "db", "dump"]]
    assert len(dump_calls) == len(expected)
    for call in dump_calls:
        assert any(arg.startswith("--remote=postgresql://") for arg in call)


def test_backup_database_uses_registry_db_url_env_override(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module, db_url_env="CUSTOM_DB_URL")
    fake_cli(monkeypatch, module, tmp_path)

    result = module.backup_database(
        "example-prod",
        mode="schema",
        destination=str(tmp_path),
    )

    assert result["db_url_env"] == "CUSTOM_DB_URL"


def test_backup_database_explicit_env_wins(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module, db_url_env="SHOULD_NOT_WIN")
    fake_cli(monkeypatch, module, tmp_path)

    result = module.backup_database(
        "example-prod",
        mode="schema",
        destination=str(tmp_path),
        db_url_env="CUSTOM_DB_URL",
    )

    assert result["db_url_env"] == "CUSTOM_DB_URL"


def test_backup_database_redacts_connection_string_on_cli_failure(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    secret = "postgresql://postgres.example:very-secret@pooler.example.com:5432/postgres"
    monkeypatch.setattr(module.shutil, "which", lambda name: "supabase.exe")
    monkeypatch.setattr(module, "read_token_env_value", lambda name: secret)

    def fail_run(command, capture_output=True, text=True, timeout=None):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr=f"could not connect to {secret}",
        )

    monkeypatch.setattr(module.subprocess, "run", fail_run)

    with pytest.raises(RuntimeError) as exc:
        module.backup_database(
            "example-prod",
            mode="schema",
            destination=str(tmp_path),
        )

    assert secret not in str(exc.value)
    assert "[REDACTED_DB_URL]" in str(exc.value)
    assert not any(tmp_path.rglob("manifest.json"))


def test_verify_database_backup_detects_tampering(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    fake_cli(monkeypatch, module, tmp_path)

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


def test_backup_database_requires_connection_env(monkeypatch, tmp_path):
    module = load_module()
    install_project(monkeypatch, module)
    monkeypatch.setattr(module, "read_token_env_value", lambda name: "")

    with pytest.raises(ValueError, match="SUPABASE_DB_URL_EXAMPLE_PROD"):
        module.backup_database(
            "example-prod",
            mode="full",
            destination=str(tmp_path),
        )
