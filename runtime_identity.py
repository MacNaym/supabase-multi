from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUNTIME_FILES = (
    ROOT / "local-ui" / "server.py",
    ROOT / "mcp" / "server.py",
    ROOT / "mcp" / "runtime_bridge.py",
    ROOT / "mcp" / "headless_control_plane.py",
)
STARTED_AT = time.time()


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in RUNTIME_FILES:
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except FileNotFoundError:
            digest.update(b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()


def git_commit() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except Exception:
        pass
    return ""


RUNTIME_FINGERPRINT = source_fingerprint()
RUNTIME_GIT_COMMIT = git_commit()


def runtime_payload(component: str) -> dict[str, Any]:
    return {
        "app": "supabase-multi",
        "component": component,
        "pid": os.getpid(),
        "started_at_epoch": STARTED_AT,
        "source_fingerprint": RUNTIME_FINGERPRINT,
        "git_commit": RUNTIME_GIT_COMMIT,
    }
