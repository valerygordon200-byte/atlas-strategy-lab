#!/usr/bin/env python3
"""Keep the autonomous laptop worker alive.

Runs as a detached process next to the worker: every 30s checks whether the
worker process still exists and restarts it if not (a real crash, not the
lock-exit path — a worker that exits via its own lock guard leaves a lock
file pointing at a dead pid, which the worker reclaims on next start).

launchd cannot host the worker here: macOS TCC blocks launchd-spawned
processes from the /Volumes pen drive (EPERM), so this shell-detached
supervisor is the restart mechanism instead. Granting the pen drive Full
Disk Access would let the LaunchAgent take over (plist included).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_FILE = REPO / "relay" / "autonomous_worker.log"
WORKER = REPO / "relay" / "autonomous_worker.py"
CHECK_SECONDS = 30


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def worker_alive() -> bool:
    try:
        out = subprocess.run(
            ["pgrep", "-f", "autonomous_worker.py"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return bool(out)
    except Exception:  # noqa: BLE001
        return False


def spawn_worker() -> int:
    # stdout to DEVNULL: the worker's own log() already appends to LOG_FILE,
    # so redirecting stdout there would double-write every line.
    p = subprocess.Popen(
        [sys.executable, str(WORKER)],
        cwd=REPO, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
    return p.pid


def main() -> None:
    pid = spawn_worker()
    log(f"supervisor up: worker spawned pid {pid}, check every {CHECK_SECONDS}s")
    while True:
        time.sleep(CHECK_SECONDS)
        if worker_alive():
            continue
        log("worker not running — restarting")
        pid = spawn_worker()
        log(f"worker restarted pid {pid}")


if __name__ == "__main__":
    main()
