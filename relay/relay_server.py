#!/usr/bin/env python3
"""relay_server.py — real-time agent-to-agent message relay (stdlib only).

Runs on the always-on machine (the laptop). Each agent connects a bridge
(agent_bridge.py) and messages are durable: every message is written to
relay/messages/<recipient>.jsonl (+ _broadcast.jsonl) and delivered to any
client that asks with a higher last_id — so a side that was offline gets
everything it missed on reconnect.

API:
  POST /send  {"token","from","to","msg"}      to="*" broadcasts
  GET  /recv  ?token&me&last_id&timeout=15     long-polls; returns msgs id>last_id
  GET  /ping  ?token                            health + participant list

Usage:  python relay_server.py --port 8787 --token <secret>
"""
import argparse
import json
import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MSG_DIR = ROOT / "messages"
PART_FILE = ROOT / "participants.json"

_lock = threading.Lock()
_participants = {}      # name -> last seen ts


def load_counter():
    cf = MSG_DIR / ".counter"
    if cf.exists():
        try:
            return int(cf.read_text().strip())
        except ValueError:
            pass
    # fallback: scan existing message files for the max id
    mx = 0
    if MSG_DIR.exists():
        for p in MSG_DIR.glob("*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line:
                    continue
                try:
                    mx = max(mx, json.loads(line)["id"])
                except Exception:
                    pass
    return mx


def rotate_archive(max_age_days: int = 30) -> int:
    """C4 milestone 2: archive message files older than max_age_days.

    Moves relay/messages/<file>.jsonl (and _broadcast) to relay/archive/ so
    the live store stays small while history is preserved. Runs on startup.
    """
    import shutil
    cutoff = time.time() - max_age_days * 86400
    arch = MSG_DIR.parent / "archive"
    arch.mkdir(exist_ok=True)
    moved = 0
    if not MSG_DIR.exists():
        return 0
    for f in MSG_DIR.glob("*.jsonl"):
        try:
            if f.stat().st_mtime < cutoff:
                shutil.move(str(f), str(arch / f.name))
                moved += 1
        except OSError:
            continue
    return moved


_counter = [load_counter()]     # monotonic message id, persisted across restarts
_N_ARCHIVED = rotate_archive()  # archive stale stores once, at startup


def next_id():
    with _lock:
        _counter[0] += 1
        try:
            (MSG_DIR / ".counter").write_text(str(_counter[0]))
        except OSError:
            pass
        return _counter[0]


def write_participants():
    # callers must already hold _lock (lock is non-reentrant)
    PART_FILE.write_text(json.dumps(_participants), encoding="utf-8")


def trim(path, cap=2000):
    if path.exists() and path.stat().st_size > 200_000:
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(lines[-cap:]) + "\n", encoding="utf-8")


def send(msg):
    mid = next_id()
    rec = {"id": mid, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "from": msg["from"], "to": msg["to"], "msg": msg["msg"]}
    with _lock:
        if msg["to"] == "*":
            path = MSG_DIR / "_broadcast.jsonl"
        else:
            path = MSG_DIR / f"{msg['to']}.jsonl"
        MSG_DIR.mkdir(exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        trim(path)
    return rec


def read_new(me, last_id):
    """All messages for `me` (direct + broadcast) with id > last_id, deduped, sorted."""
    out = {}
    with _lock:
        for fname in (f"{me}.jsonl", "_broadcast.jsonl"):
            p = MSG_DIR / fname
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec["id"] > last_id and rec["id"] not in out:
                    out[rec["id"]] = rec
    return [out[k] for k in sorted(out)]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/send":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            msg = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "bad json"})
        if msg.get("token") != self.server.token:
            return self._json(403, {"error": "bad token"})
        if not msg.get("from") or not msg.get("msg"):
            return self._json(400, {"error": "from+msg required"})
        rec = send(msg)
        with _lock:
            _participants[msg["from"]] = time.time()
            write_participants()
        return self._json(200, {"ok": True, "id": rec["id"]})

    def do_GET(self):
        if self.path.startswith("/ping"):
            with _lock:
                parts = {k: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(v))
                         for k, v in _participants.items()}
            return self._json(200, {"ok": True, "participants": parts})
        if self.path.startswith("/all"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            if q.get("token", [None])[0] != self.server.token:
                return self._json(403, {"error": "bad token"})
            try:
                since = int(q.get("since", ["0"])[0])
            except ValueError:
                since = 0
            out = {}
            with _lock:
                for p in MSG_DIR.glob("*.jsonl"):
                    for line in p.read_text(encoding="utf-8").splitlines():
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if rec["id"] > since and rec["id"] not in out:
                            out[rec["id"]] = rec
            rows = [out[k] for k in sorted(out)]
            return self._json(200, {"ok": True, "msgs": rows,
                                    "max_id": rows[-1]["id"] if rows else since})
        if self.path.startswith("/recv"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            if q.get("token", [None])[0] != self.server.token:
                return self._json(403, {"error": "bad token"})
            me = q.get("me", [""])[0]
            try:
                last_id = int(q.get("last_id", ["0"])[0])
            except ValueError:
                last_id = 0
            timeout = min(float(q.get("timeout", ["15"])[0]), 30)
            with _lock:
                _participants[me] = time.time()
                write_participants()
            deadline = time.time() + timeout
            while True:
                rows = read_new(me, last_id)
                if rows or time.time() > deadline:
                    break
                time.sleep(0.5)
            if rows:
                return self._json(200, {"ok": True, "msgs": rows,
                                        "max_id": rows[-1]["id"]})
            return self._json(200, {"ok": True, "msgs": [], "max_id": last_id})
        return self._json(404, {"error": "not found"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--token", default=os.environ.get("RELAY_TOKEN", "change-me"))
    args = ap.parse_args()
    MSG_DIR.mkdir(exist_ok=True)
    _counter[0] = load_counter()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.token = args.token
    print(f"relay listening on {args.host}:{args.port}  token={args.token}")
    print(f"archive: {_N_ARCHIVED} old store(s) moved to relay/archive/")
    print(f"messages dir: {MSG_DIR}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
