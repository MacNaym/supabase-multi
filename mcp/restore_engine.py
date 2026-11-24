"""Local disposable restore smoke test. Never accepts a remote connection URL."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from headless_control_plane import validate_database_backup

FILES = ("roles.sql", "schema.sql", "data.sql")
IMAGE_PATTERN = re.compile(r"(?:docker\.io/)?supabase/postgres@sha256:[a-f0-9]{64}\Z")


def test_restore(path: str, *, image: str, trusted: bool = False, progress=None):
    """Restore into a new network-disabled container; discard it afterwards.

    Caller must explicitly trust the source. This is not a sandbox for hostile SQL.
    Image must already be installed and pinned by digest.
    """
    if trusted is not True:
        raise ValueError("Explicit confirmation of trusted backup source is required.")
    if not isinstance(image, str) or not IMAGE_PATTERN.fullmatch(image):
        raise ValueError("Select a locally installed Supabase PostgreSQL image pinned by digest.")
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker is required for isolated restore.")
    name = "supabase-multi-restore-" + secrets.token_hex(12)
    password = secrets.token_hex(24)
    report = {"ok":False,"restore_tested":False,"destination":"disposable-local",
              "phase":"validation","cleanup_ok":True,"image":image}
    started = time.monotonic()
    created = False

    def emit(phase):
        report["phase"] = phase
        if progress:
            progress(phase)

    # Do not forward host PATs or database passwords into the container.
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith(("SUPABASE_", "PG"))}

    def run(args, *, timeout=120, check=True):
        try:
            proc = subprocess.run([docker,*args],capture_output=True,text=True,
                                  timeout=timeout,env=env)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("Docker command failed to launch or timed out.") from None
        if check and proc.returncode:
            # SQL error output can contain actual data and secrets.
            raise RuntimeError("Docker or SQL command failed during "+report["phase"]+".")
        return proc

    try:
        emit("validation")
        source = validate_database_backup(path)
        if not source.get("ok") or not source.get("full_backup"):
            raise ValueError("A full validated backup is required.")
        with tempfile.TemporaryDirectory(prefix="supabase-multi-restore-") as tmp:
            stage = Path(tmp)
            # Stage exact bytes, then validate again before executing any SQL.
            for filename in (*FILES,"manifest.json"):
                shutil.copyfile(Path(source["backup_dir"])/filename,stage/filename)
            staged = validate_database_backup(str(stage))
            if not staged.get("ok") or not staged.get("full_backup"):
                raise ValueError("Backup changed or failed staging verification.")
            if [(f["name"],f["sha256"]) for f in staged["files"]] != [(f["name"],f["sha256"]) for f in source["files"]]:
                raise ValueError("Backup changed during staging.")
            emit("container")
            run(["image","inspect",image])
            # No host bind mounts, Docker socket, published ports or host network.
            # Mark cleanup necessary before run, including partial Docker failures.
            created = True
            run(["run","-d","--pull=never","--name",name,"--network","none",
                 "--security-opt","no-new-privileges","--memory","2g","--cpus","2",
                 "--pids-limit","256","-e","POSTGRES_PASSWORD="+password,image])
            emit("readiness")
            deadline = time.monotonic()+180
            while True:
                ready = run(["exec",name,"pg_isready","-U","postgres","-d","postgres"],timeout=10,check=False)
                if ready.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("Local database readiness timeout.")
                time.sleep(2)
            emit("copy")
            for filename in FILES:
                run(["cp",str(stage/filename),name+":/tmp/"+filename])
            emit("restore")
            run(["exec","-e","PGPASSWORD="+password,name,"psql","-X","-h","127.0.0.1",
                 "-U","postgres","-d","postgres","--single-transaction","--set","ON_ERROR_STOP=1",
                 "--file","/tmp/roles.sql","--file","/tmp/schema.sql",
                 "--command","SET session_replication_role = replica",
                 "--file","/tmp/data.sql"],timeout=3600)
            emit("postcheck")
            query = """SELECT json_build_object(
            'server_version',current_setting('server_version'),
            'public_tables',(SELECT count(*) FROM pg_tables WHERE schemaname='public'),
            'rls_tables',(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relrowsecurity),
            'policies',(SELECT count(*) FROM pg_policies WHERE schemaname='public'),
            'extensions',(SELECT count(*) FROM pg_extension));"""
            proc=run(["exec","-e","PGPASSWORD="+password,name,"psql","-X","-h","127.0.0.1",
                      "-U","postgres","-d","postgres","-At","--set","ON_ERROR_STOP=1","-c",query])
            report["inventory"]=json.loads(proc.stdout.strip())
            report.update(ok=True,restore_tested=True)
    except (ValueError,RuntimeError,OSError,json.JSONDecodeError):
        report["error"]="Restore test failed during "+report["phase"]+". Check image compatibility and trusted backup integrity."
    finally:
        if created:
            try:
                cleanup=run(["rm","-f","-v",name],check=False)
                report["cleanup_ok"]=cleanup.returncode==0
            except RuntimeError:
                report["cleanup_ok"]=False
            if not report["cleanup_ok"]:
                report["ok"]=False
                report["cleanup_container"]=name
        report["elapsed_seconds"]=round(time.monotonic()-started,2)
    return report
