#!/usr/bin/env python3
"""gateway_watch.py — C8 enabler. Watches for the IBKR Gateway (paper) to come
online on port 7497, then runs the connector --check and announces readiness on
the relay. The ONE human step (logging into Gateway with the paper account,
API enabled on 7497) is now self-detected: nobody has to poll.

Run (laptop):
    /Volumes/ATLAS /dourmouse-4.0.0/.venv/bin/python scripts/gateway_watch.py

Stdlib only (the connector itself imports ib_insync via the venv).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = "/Volumes/ATLAS /dourmouse-4.0.0/.venv/bin/python"
RELAY = "http://100.98.97.23:8787"
TOKEN = "jXVXaHAeG721UkhMYRSq3rRXAK-iBIAY"
ME = "laptop-dourmouse"
HOSTS = ["127.0.0.1", "192.168.1.95", "100.84.156.49"]
PORT = 7497
POLL_SEC = 5

_state = {"announced": False, "last_up": None}


def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def say(text: str) -> None:
    payload = json.dumps({"token": TOKEN, "from": ME, "msg": text}).encode()
    req = urllib.request.Request(RELAY + "/send", data=payload, method="POST")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                print(f"[relay] {r.read().decode()}", flush=True)
                return
        except Exception as e:  # noqa: BLE001
            print(f"[relay] send failed (attempt {attempt + 1}/4): {e}", flush=True)
            time.sleep(5)
    print("[relay] GAVE UP after 4 attempts", flush=True)


def run_check() -> bool:
    """Run the connector --check with the venv python. True if it connects."""
    proc = subprocess.run(
        [PY, os.path.join(REPO, "scripts", "ibkr_connector.py"), "--check"],
        capture_output=True, text=True, timeout=90,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = "CONNECT OK" in out or "connected" in out.lower() and "fail" not in out.lower()
    print(f"[check] rc={proc.returncode} ok={ok}\n{out[-400:]}", flush=True)
    return ok


def main() -> None:
    print(f"[watch] polling {HOSTS} :{PORT} every {POLL_SEC}s — waiting for the "
          f"IBKR Gateway (paper) to come online.", flush=True)
    while True:
        up = [h for h in HOSTS if port_open(h, PORT)]
        if up:
            _state["last_up"] = time.time()
            if not _state["announced"]:
                print(f"[watch] GATEWAY UP on {up} — running connector --check", flush=True)
                if run_check():
                    say("GATEWAY UP + PAPER CONNECTOR VERIFIED on the Mac (7497 open, "
                        "ib_insync --check connects). Ready for the first real paper "
                        "fill — desktop-atlas, run it whenever you are.")
                    _state["announced"] = True
                else:
                    say("GATEWAY UP (7497 open) but connector --check failed — will "
                        "re-arm and try again on the next port-open transition.")
        else:
            # Gateway went down/never up: re-arm so the NEXT genuine boot is announced
            _state["announced"] = False
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
