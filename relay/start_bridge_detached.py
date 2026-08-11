#!/usr/bin/env python3
"""Start the laptop relay bridge fully detached (new session, own log)."""
import os
import subprocess
import sys

REPO = "/Volumes/ATLAS /dourmouse-4.0.0/atlas-strategy-lab"
LOG = os.path.join(REPO, "relay", "bridge_laptop.log")


def _cfg_token(script_path: str) -> str:
    """Read TOKEN from the gitignored relay_config.txt next to this script."""
    cfg = os.path.join(os.path.dirname(os.path.abspath(script_path)), "relay_config.txt")
    if os.path.exists(cfg):
        for line in open(cfg, encoding="utf-8"):
            if line.startswith("TOKEN="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("RELAY_TOKEN not set and relay/relay_config.txt missing")


cmd = [
    sys.executable, "relay/agent_bridge.py",
    "--relay", "http://100.98.97.23:8787",
    "--token", os.environ.get("RELAY_TOKEN", _cfg_token(__file__)),
    "--me", "laptop-dourmouse",
]
logf = open(LOG, "a")
p = subprocess.Popen(
    cmd,
    cwd=REPO,
    stdin=subprocess.DEVNULL,
    stdout=logf,
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print("bridge pid:", p.pid)
