"""Disposable restore smoke test and fail-closed remote destination planning."""
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


def plan_remote_restore(path: str, *, account: str, project: str, expected_ref: str,
                        trusted: bool = False, registry=None):
    """Read-only planning; never connects to or writes to a remote database.

    Explicit opt-in is necessary but not sufficient to execute a restore.
    Unknown environments and ambiguous aliases are rejected.
    """
    from headless_control_plane import read_registry
    if trusted is not True:
        raise ValueError("Explicit confirmation of trusted backup source is required.")
    if not all(isinstance(v, str) and v.strip() for v in (account, project, expected_ref)):
        raise ValueError("Account, target and exact reference are required.")
    if not re.fullmatch(r"[a-z0-9]{20}", expected_ref):
        raise ValueError("Invalid destination project reference.")
    reg = read_registry() if registry is None else registry
    target = reg.get("projects", {}).get(project)
    if account not in reg.get("accounts", {}) or not target or target.get("account") != account:
        raise ValueError("Target does not belong to selected account.")
    if target.get("project_ref") != expected_ref:
        raise ValueError("Destination reference mismatch.")
    if not target.get("enabled", True) or target.get("read_only") is not False:
        raise ValueError("Target disabled or protected by read-only policy.")
    if target.get("environment") not in {"development", "staging", "test"}:
        raise ValueError("Only explicitly classified non-production destinations are allowed.")
    if target.get("restore_enabled") is not True:
        raise ValueError("Destination must explicitly opt into restore.")
    aliases = [p for p in reg.get("projects", {}).values() if p.get("project_ref") == expected_ref]
    if len(aliases) != 1:
        raise ValueError("Destination reference has ambiguous registry aliases.")
    source = validate_database_backup(path)
    if not source.get("ok") or not source.get("full_backup"):
        raise ValueError("A complete validated backup is required.")
    source_ref = source.get("project_ref")
    if not isinstance(source_ref, str) or not re.fullmatch(r"[a-z0-9]{20}", source_ref):
        raise ValueError("Backup source reference is missing or invalid.")
    if source_ref == expected_ref:
        raise ValueError("Restoring onto the source project is prohibited.")
    return {
        "ok": True, "execution_enabled": False, "remote_checked": False,
        "source_ref": source_ref, "destination_ref": expected_ref,
        "account": account, "project": project,
        "backup_dir": source["backup_dir"],
        "files": [{"name": f["name"], "sha256": f["sha256"]} for f in source["files"]],
        "remaining_checks": [
            "Verify target identity, environment and database permissions remotely.",
            "Verify PostgreSQL versions, extensions and managed schemas.",
            "Require empty application target and verified preventive backup.",
            "Review cron jobs, webhooks, foreign servers and external side effects.",
            "Require explicit destination reference confirmation and isolated restore test.",
        ],
    }


def remote_restore_preflight(path: str, *, account: str, project: str, expected_ref: str,
                             trusted: bool = False, certificate: str):
    """Read-only SQL inventory using a project-specific password and verified TLS.

    No restore is authorized by this result. A baseline inventory must be reviewed.
    """
    import urllib.parse
    from headless_control_plane import _backup_source, _backup_pooler_url, read_token_env_value
    plan = plan_remote_restore(path, account=account, project=project,
                               expected_ref=expected_ref, trusted=trusted)
    ref, _, token, password_env, target = _backup_source(project)
    if ref != expected_ref or target.get("account") != account:
        raise ValueError("Destination changed.")
    password = read_token_env_value(password_env)
    if not password:
        raise ValueError("Configure the destination database password locally.")
    cert = Path(certificate).expanduser().resolve()
    if not cert.is_file():
        raise ValueError("Destination TLS root certificate is required.")
    psql = shutil.which("psql")
    if not psql:
        raise RuntimeError("psql is required for remote restore preflight.")
    url = urllib.parse.urlsplit(_backup_pooler_url(ref, token, password))
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith(("PG","SUPABASE_"))}
    env.update(PGHOST=url.hostname, PGPORT="5432", PGDATABASE="postgres",
               PGUSER="postgres."+ref, PGPASSWORD=password, PGSSLMODE="verify-full",
               PGSSLROOTCERT=str(cert), PGCONNECT_TIMEOUT="15",
               PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=30000")
    query = """SELECT json_build_object(
      'database',current_database(),
      'version_num',current_setting('server_version_num'),
      'read_only',current_setting('transaction_read_only'),
      'public_objects',(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')),
      'extensions',(SELECT coalesce(json_agg(extname ORDER BY extname),'[]'::json) FROM pg_extension),
      'schemas',(SELECT coalesce(json_agg(nspname ORDER BY nspname),'[]'::json) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema'),
      'foreign_servers',(SELECT count(*) FROM pg_foreign_server));"""
    try:
        proc = subprocess.run([psql,"-X","-w","-At","--set","ON_ERROR_STOP=1","-c",query],
                              capture_output=True,text=True,timeout=60,env=env)
        if proc.returncode:
            raise RuntimeError("Destination SQL preflight failed. Check TLS, password and permissions.")
        inventory = json.loads(proc.stdout.strip())
        if inventory.get("database") != "postgres" or inventory.get("read_only") != "on":
            raise RuntimeError("Unexpected destination database or transaction mode.")
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        raise RuntimeError("Destination preflight failed or returned invalid metadata.") from None
    plan.update(remote_checked=True, inventory=inventory,
                public_schema_empty=inventory.get("public_objects")==0)
    return plan
