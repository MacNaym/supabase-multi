from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime_identity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_multi_runtime_identity", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_payload_uses_startup_fingerprint():
    module = load_module()
    payload = module.runtime_payload("test-component")

    assert payload["app"] == "supabase-multi"
    assert payload["component"] == "test-component"
    assert payload["source_fingerprint"] == module.RUNTIME_FINGERPRINT
    assert len(payload["source_fingerprint"]) == 64
    assert payload["pid"] > 0


def test_release_payload_reports_product_and_backup_versions_independently():
    """A prerelease product label or coupled backup version must not ship as 3.10.0."""
    module = load_module()
    payload = module.runtime_payload("release-check")

    assert payload["app_version"] == "3.10.0"
    assert payload["backup_module_version"] == "1.5.0"


def test_source_fingerprint_changes_when_runtime_source_changes(monkeypatch, tmp_path):
    module = load_module()
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    c = tmp_path / "c.py"
    for path in (a, b, c):
        path.write_text("one", encoding="utf-8")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RUNTIME_FILES", (a, b, c))
    first = module.source_fingerprint()

    b.write_text("two", encoding="utf-8")
    second = module.source_fingerprint()

    assert first != second
