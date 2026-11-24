from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
import restore_engine as engine

REF = "abcdefghijklmnopqrst"
SOURCE = "zyxwvutsrqponmlkjihg"
IMAGE = "supabase/postgres@sha256:" + "a"*64
ECR_IMAGE = "public.ecr.aws/supabase/postgres@sha256:" + "b"*64


def registry():
    return {"accounts":{"a":{}}, "projects":{"p":{"account":"a","project_ref":REF,
            "enabled":True,"read_only":False,"environment":"test","restore_enabled":True}}}


@pytest.fixture
def source(monkeypatch,tmp_path):
    for name in (*engine.FILES,"manifest.json"):
        (tmp_path/name).write_text("fixture",encoding="utf-8")
    report={"ok":True,"full_backup":True,"project_ref":SOURCE,
            "files":[{"name":n,"sha256":"a"*64} for n in engine.FILES]}
    monkeypatch.setattr(engine,"validate_database_backup",lambda path: dict(report,backup_dir=str(path)))
    return tmp_path


def test_plan_never_connects(monkeypatch,source):
    monkeypatch.setattr(engine.subprocess,"run",lambda *a,**k:pytest.fail("unexpected process"))
    result=engine.plan_remote_restore(str(source),account="a",project="p",expected_ref=REF,trusted=True,registry=registry())
    assert result["ok"] and not result["execution_enabled"] and not result["remote_checked"]


@pytest.mark.parametrize("field,value",[
    ("read_only",True),("read_only",None),("enabled",False),
    ("environment","production"),("environment",None),("restore_enabled",False),
    ("account","other"),("project_ref",SOURCE)])
def test_plan_blocks_unsafe_target(source,field,value):
    reg=registry()
    reg["projects"]["p"][field]=value
    with pytest.raises(ValueError):
        engine.plan_remote_restore(str(source),account="a",project="p",expected_ref=REF,trusted=True,registry=reg)


def test_plan_blocks_source_and_alias(monkeypatch,source):
    reg=registry()
    reg["projects"]["other"]=dict(reg["projects"]["p"])
    with pytest.raises(ValueError,match="ambiguous"):
        engine.plan_remote_restore(str(source),account="a",project="p",expected_ref=REF,trusted=True,registry=reg)
    monkeypatch.setattr(engine,"validate_database_backup",lambda path:{"ok":True,"full_backup":True,"project_ref":REF})
    with pytest.raises(ValueError,match="source project"):
        engine.plan_remote_restore(str(source),account="a",project="p",expected_ref=REF,trusted=True,registry=registry())


@pytest.mark.parametrize("failure",[False,True])
def test_local_restore_cleanup_and_isolation(monkeypatch,source,failure):
    monkeypatch.setattr(engine.shutil,"which",lambda _: "docker")
    calls=[]
    def run(cmd,**kw):
        calls.append(cmd)
        fail=failure and "--single-transaction" in cmd
        return SimpleNamespace(returncode=int(fail),stdout='{"public_tables":1}' if "-At" in cmd else "",stderr="private-data")
    monkeypatch.setattr(engine.subprocess,"run",run)
    report=engine.test_restore(str(source),image=IMAGE,trusted=True)
    assert report["ok"] is (not failure)
    assert report["cleanup_ok"]
    assert calls[-1][3:6]==["rm","-f","-v"]
    create=next(c for c in calls if len(c)>3 and c[3]=="run")
    assert create[create.index("--network")+1]=="none"
    assert not any(x in create for x in ["--privileged","-v","--mount","-p"])
    assert "private-data" not in str(report)


def test_local_restore_requires_trust(source):
    with pytest.raises(ValueError,match="trusted"):
        engine.test_restore(str(source),image=IMAGE)


def test_local_restore_accepts_pinned_supabase_ecr_image(monkeypatch, source):
    """A locally installed official Supabase ECR image must not be rejected by its digest name."""
    monkeypatch.setattr(engine.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(
        engine.subprocess,
        "run",
        lambda cmd, **kw: SimpleNamespace(returncode=0, stdout='{"public_tables":0}' if "-At" in cmd else "", stderr=""),
    )

    assert engine.test_restore(str(source), image=ECR_IMAGE, trusted=True)["ok"] is True


def test_local_restore_forces_builtin_docker_context(monkeypatch, source):
    """Ambient remote Docker routing must never receive a backup through docker cp."""
    monkeypatch.setattr(engine.shutil, "which", lambda _: "docker")
    calls = []
    def run(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout='{"public_tables":0}' if "-At" in cmd else "", stderr="")
    monkeypatch.setattr(engine.subprocess, "run", run)
    assert engine.test_restore(str(source), image=IMAGE, trusted=True)["ok"]
    docker_calls = [call for call in calls if call[1:3] != ["context", "show"]]
    assert all(call[1:3] == ["--context", "default"] for call in docker_calls)


def test_local_restore_reports_ordered_restore_and_complete_inventory(monkeypatch, source):
    """Dropping a restore phase or inventory class must make this fail."""
    monkeypatch.setattr(engine.shutil, "which", lambda _: "docker")
    calls = []
    inventory = {
        "server_version": "16.1",
        "public_tables": 2,
        "data_rows_estimate": 3,
        "public_functions": 1,
        "constraints": 2,
        "rls_tables": 1,
        "policies": 1,
        "extensions": 4,
    }

    def run(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout=json.dumps(inventory) if "-At" in cmd else "", stderr="")

    monkeypatch.setattr(engine.subprocess, "run", run)

    report = engine.test_restore(str(source), image=IMAGE, trusted=True)

    restore_calls = [call for call in calls if "psql" in call and "--file" in call]
    restored_files = [call[call.index("--file") + 1] for call in restore_calls]
    assert restored_files == ["/tmp/roles.sql", "/tmp/schema.sql", "/tmp/data.sql"]
    assert set(inventory) <= set(report["inventory"])
    postcheck = next(call for call in calls if any("json_build_object" in str(part) for part in call))
    query = postcheck[postcheck.index("-c") + 1]
    for field in ("data_rows_estimate", "public_functions", "constraints", "rls_tables", "policies", "extensions"):
        assert field in query


@pytest.mark.skipif(
    os.environ.get("SUPABASE_MULTI_RUN_DOCKER_TESTS") != "1",
    reason="set SUPABASE_MULTI_RUN_DOCKER_TESTS=1 to run the disposable Docker restore test",
)
def test_disposable_restore_with_synthetic_database(tmp_path):
    """The real isolated restore must retain synthetic schema, data and protections."""
    image = os.environ.get(
        "SUPABASE_MULTI_RESTORE_TEST_IMAGE",
        "public.ecr.aws/supabase/postgres@sha256:0b64586fb84124b9070525a6528616594a1aa84a75d84cd4c3d43acc8de3ba92",
    )
    contents = {
        "roles.sql": "-- Roles\n",
        "schema.sql": """-- PostgreSQL database dump
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE public.restore_smoke (id integer PRIMARY KEY, label text NOT NULL CHECK (char_length(label) > 0));
ALTER TABLE public.restore_smoke ENABLE ROW LEVEL SECURITY;
CREATE POLICY restore_smoke_read ON public.restore_smoke FOR SELECT USING (true);
CREATE FUNCTION public.restore_increment(value integer) RETURNS integer LANGUAGE sql IMMUTABLE AS $$ SELECT value + 1 $$;
""",
        "data.sql": "INSERT INTO public.restore_smoke (id, label) VALUES (1, 'synthetic');\n",
    }
    files = []
    for name, content in contents.items():
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        files.append({"name": name, "bytes": path.stat().st_size, "sha256": engine.hashlib.sha256(path.read_bytes()).hexdigest()})
    (tmp_path / "manifest.json").write_text(
        json.dumps({"format": "supabase-multi-backup-v1", "mode": "full", "project": "synthetic", "project_ref": SOURCE, "files": files}),
        encoding="utf-8",
    )

    report = engine.test_restore(str(tmp_path), image=image, trusted=True)

    assert report["ok"] is True, report
    assert report["cleanup_ok"] is True
    assert report["inventory"]["public_tables"] >= 1
    assert report["inventory"]["data_rows_estimate"] >= 1
    assert report["inventory"]["public_functions"] >= 1
    assert report["inventory"]["constraints"] >= 2
    assert report["inventory"]["rls_tables"] >= 1
    assert report["inventory"]["policies"] >= 1


def test_copy_requirements_skips_payload(tmp_path):
    path=tmp_path/"data.sql"
    path.write_text('COPY "auth"."audit_log_entries" ("id", "ip_address") FROM stdin;\nCOPY fake.payload (x) FROM stdin;\n\\.\n',encoding="utf-8")
    assert engine.copy_requirements(path)=={("auth","audit_log_entries","id"),("auth","audit_log_entries","ip_address")}
    assert engine.compare_copy_columns(engine.copy_requirements(path),[["auth","audit_log_entries","id"]])==[("auth","audit_log_entries","ip_address")]


def test_copy_requirements_rejects_truncation(tmp_path):
    path=tmp_path/"data.sql"
    path.write_text("COPY public.example (id) FROM stdin;\n1\n",encoding="utf-8")
    with pytest.raises(ValueError,match="Unterminated"):
        engine.copy_requirements(path)
