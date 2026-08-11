#!/usr/bin/env python3
"""Start the laptop relay bridge fully detached (new session, own log)."""
import os
import subprocess
import sys

REPO = "/Volumes/ATLAS /dourmouse-4.0.0/atlas-strategy-lab"
LOG = os.path.join(REPO, "relay", "bridge_laptop.log")
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
