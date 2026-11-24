from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
import restore_engine as engine

REF = "abcdefghijklmnopqrst"
SOURCE = "zyxwvutsrqponmlkjihg"
IMAGE = "supabase/postgres@sha256:" + "a"*64


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
    assert calls[-1][1:4]==["rm","-f","-v"]
    create=next(c for c in calls if c[1]=="run")
    assert create[create.index("--network")+1]=="none"
    assert not any(x in create for x in ["--privileged","-v","--mount","-p"])
    assert "private-data" not in str(report)


def test_local_restore_requires_trust(source):
    with pytest.raises(ValueError,match="trusted"):
        engine.test_restore(str(source),image=IMAGE)
