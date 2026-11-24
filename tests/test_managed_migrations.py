"""Regression coverage for managed migration metadata extraction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
from headless_control_plane import backup_managed_migrations


def test_managed_migrations(tmp_path):
    (tmp_path / "data.sql").write_text(
        'COPY "auth"."schema_migrations" ("version") FROM stdin;\n'
        '20250101000000\n20250201000000\n\\.\n'
        'COPY "storage"."migrations" ("id", "name", "hash", "executed_at") FROM stdin;\n'
        '1\tinitial\t' + 'a'*40 + '\t2025-01-01 00:00:00\n\\.\n',
        encoding="utf-8")
    result = backup_managed_migrations(tmp_path)
    assert result["auth"] == ["20250101000000", "20250201000000"]
    assert result["storage"] == [{"id": 1, "name": "initial", "hash": "a"*40}]


def test_ignores_application_payload(tmp_path):
    (tmp_path / "data.sql").write_text(
        'COPY public.example (id) FROM stdin;\n'
        'COPY auth.schema_migrations (version) FROM stdin;\n'
        '20250101000000\n\\.\n', encoding="utf-8")
    assert backup_managed_migrations(tmp_path) == {"auth": None, "storage": None}


def test_invalid_and_truncated_migrations(tmp_path):
    (tmp_path / "data.sql").write_text(
        'COPY auth.schema_migrations (version) FROM stdin;\n'
        'secret-value\n\\.\n'
        'COPY storage.migrations (id, name, hash) FROM stdin;\n'
        '1\tinitial\t' + 'a'*40 + '\n', encoding="utf-8")
    assert backup_managed_migrations(tmp_path) == {"auth": None, "storage": None}


def test_missing_data(tmp_path):
    assert backup_managed_migrations(tmp_path) == {"auth": None, "storage": None}
