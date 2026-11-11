from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_identity import source_fingerprint

BASE_URL = os.environ.get("SUPABASE_MULTI_URL", "http://127.0.0.1:8765").rstrip("/")


def _request(path: str, *, method: str = "GET", timeout: int = 2):
    req = urllib.request.Request(
        BASE_URL + path,
        data=b"{}" if method == "POST" else None,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def _legacy_up() -> bool:
    try:
        data = _request("/api/state?local=1")
        return bool(data.get("ok"))
    except Exception:
        return False


def _kill_local_8765() -> bool:
    if os.name != "nt" or BASE_URL != "http://127.0.0.1:8765":
        return False
    command = (
        "$c=Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue;"
        "if($c){$c|ForEach-Object{Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue};exit 0};exit 1"
    )
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            timeout=10,
        ).returncode == 0
    except Exception:
        return False


def main() -> int:
    expected = source_fingerprint()
    try:
        runtime = _request("/api/runtime")
        if (
            runtime.get("ok")
            and runtime.get("runtime", {}).get("app") == "supabase-multi"
            and runtime.get("runtime", {}).get("source_fingerprint") == expected
        ):
            print("CURRENT")
            return 0

        if runtime.get("ok") and runtime.get("runtime", {}).get("app") == "supabase-multi":
            try:
                _request("/api/shutdown", method="POST")
            except Exception:
                pass
            for _ in range(20):
                if not _legacy_up():
                    break
                time.sleep(0.1)
            print("STALE_STOPPED")
            return 2
    except Exception:
        pass

    if _legacy_up():
        if _kill_local_8765():
            print("LEGACY_STOPPED")
            return 2
        print("STALE_UNSTOPPABLE")
        return 3

    print("DOWN")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
