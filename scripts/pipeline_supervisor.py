#!/usr/bin/env python3
"""pipeline_supervisor.py — T8: keep the whole commercial stack alive.

Supervises every service of the two-machine stack on this desktop:
  relay      (8787)  relay/relay_server.py         — the tailscale feed core
  feed       (8788)  relay/chat_feed.py            — the chat dashboard
  worker     (—)     relay/desktop_worker.py       — autonomous executor
  bridge     (—)     relay/agent_bridge.py         — inbox/outbox courier
  engine     (8790)  scripts/engine_api.py         — atlas backtest service
  hub        (8791)  tools/serve_hub.py (dourmouse)— the commercial shell UI

Every ~15s: HTTP ping where a port exists, process scan otherwise. Down =>
restart (kill strays first, spawn fresh, log + announce on the relay,
rate-limited). Status endpoint on 8792: GET /status -> JSON per service.

Run:  python scripts/pipeline_supervisor.py [--port 8792] [--interval 15]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # atlas-strategy-lab
DM = ROOT.parent / "dourmouse"                          # dourmouse checkout
TOKEN = (ROOT / "relay" / "relay_config.txt").read_text(encoding="utf-8") \
    if (ROOT / "relay" / "relay_config.txt").exists() else ""
TOKEN = re.search(r"^TOKEN=(.+)$", TOKEN, re.M).group(1).strip() if TOKEN else ""

PY = sys.executable

SERVICES = [
    {"name": "relay", "cwd": ROOT, "health": "http://127.0.0.1:8787/ping",
     "cmd": [PY, "relay/relay_server.py", "--port", "8787", "--token", TOKEN]},
    {"name": "feed", "cwd": ROOT, "health": "http://127.0.0.1:8788/feed?since=0",
     "cmd": [PY, "relay/chat_feed.py", "--relay", "http://127.0.0.1:8787",
             "--token", TOKEN, "--me", "desktop-atlas",
             "--send-token", TOKEN, "--port", "8788"]},
    {"name": "worker", "cwd": ROOT, "health": None, "pattern": "desktop_worker",
     "cmd": [PY, "relay/desktop_worker.py", "--poll", "5"]},
    {"name": "bridge", "cwd": ROOT, "health": None, "pattern": "agent_bridge",
     "cmd": [PY, "relay/agent_bridge.py", "--relay", "http://127.0.0.1:8787",
             "--token", TOKEN, "--me", "desktop-atlas"]},
    {"name": "engine", "cwd": ROOT, "health": "http://127.0.0.1:8790/api/health",
     "cmd": [PY, "scripts/engine_api.py", "--port", "8790"],
     "env": {"ENGINE_TOKEN": TOKEN}, "auth": True},
    {"name": "hub", "cwd": DM, "health": "http://127.0.0.1:8791/hub.html",
     "cmd": [PY, "tools/serve_hub.py", "--port", "8791"],
     "env": {"HUB_ENGINE_TOKEN": TOKEN}},
]

STATE: dict[str, dict] = {}
_log_last = 0.0


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def http_up(url: str, timeout: float = 3.0, token: str = "") -> bool:
    try:
        req = urllib.request.Request(url)
        if token:
            req.add_header("X-Engine-Token", token)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def proc_pids(pattern: str) -> list[int]:
    """All PIDs matching the pattern (wmic CSV: NODE,CMDLINE,PID — PID LAST)."""
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get",
             "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    pids = []
    for line in out.splitlines():
        if pattern in line:
            m = re.search(r",(\d+)\s*$", line.strip())
            if m:
                pids.append(int(m.group(1)))
    return pids


def kill_pids(pattern: str) -> None:
    for pid in proc_pids(pattern):
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True, text=True, timeout=15)


def start(svc: dict) -> None:
    cwd = svc["cwd"]
    cwd.mkdir(parents=True, exist_ok=True)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    env = {**os.environ, **svc.get("env", {})}
    with open(cwd / (".supervisor_" + svc["name"] + ".log"), "a",
              encoding="utf-8") as log:
        subprocess.Popen(svc["cmd"], cwd=str(cwd), stdout=log, stderr=log,
                         creationflags=flags, stdin=subprocess.DEVNULL, env=env)


def is_up(svc: dict) -> bool:
    if svc.get("health"):
        return http_up(svc["health"], token=TOKEN if svc.get("auth") else "")
    return len(proc_pids(svc["pattern"])) > 0


def relay_say(msg: str) -> None:
    if not TOKEN:
        return
    try:
        payload = json.dumps({"token": TOKEN, "from": "desktop-worker",
                              "to": "*", "msg": msg}).encode()
        req = urllib.request.Request("http://127.0.0.1:8787/send",
                                     data=payload, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def supervise() -> None:
    global _log_last
    for svc in SERVICES:
        st = STATE.setdefault(svc["name"],
                              {"up": False, "pid": None, "last_restart": None,
                               "restarts": 0})
        up = is_up(svc)
        st["up"] = up
        if svc.get("health"):
            pass
        elif up:
            st["pid"] = (proc_pids(svc["pattern"]) or [None])[0]
        if not up:
            kill_pids(svc["pattern"]) if svc.get("pattern") else None
            start(svc)
            st["last_restart"] = now()
            st["restarts"] += 1
            print(f"[{now()}] RESTART {svc['name']} (restarts={st['restarts']})")
            if time.time() - _log_last > 60:
                relay_say(f"supervisor: restarted {svc['name']} "
                          f"(restart #{st['restarts']})")
                _log_last = time.time()


class Status(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"ok": True, "services": STATE,
                           "time": now()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("SUP_PORT", 8792)))
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Status)
    import threading
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"pipeline supervisor on :{args.port} — supervising "
          f"{len(SERVICES)} services every {args.interval}s")
    while True:
        try:
            supervise()
        except Exception as e:  # noqa: BLE001
            print(f"supervisor error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
