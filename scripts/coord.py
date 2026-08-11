#!/usr/bin/env python3
"""coord.py — shared task board for coordinating agents across Freebuff accounts.

Uses coordination/tasks.json as the single source of truth in this repo.
Commands:
  new   "<task text>" [--priority low|mid|high] [--me NAME]
  list  [--status TODO|IN_PROGRESS|DONE] [--me NAME]
  claim <id> [--me NAME]
  done  <id> "<one-line result>" [--me NAME]
  log   [--tail N]

Discipline: pull before list/claim, push right after claim, push after done.
Last-writer-wins on tasks.json is mitigated by the claim lock: never edit a task
whose owner is not you while it is IN_PROGRESS.
"""
import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "coordination" / "tasks.json"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load():
    if not BOARD.exists():
        return {"tasks": [], "log": []}
    return json.loads(BOARD.read_text(encoding="utf-8"))


def save(board):
    BOARD.parent.mkdir(exist_ok=True)
    BOARD.write_text(json.dumps(board, indent=2), encoding="utf-8")


def who(args):
    return args.me or os.environ.get("AGENT_ID") or socket.gethostname()


def next_id(tasks):
    used = {t["id"] for t in tasks}
    n = 1
    while f"T{n}" in used:
        n += 1
    return f"T{n}"


def log_event(board, ev):
    board.setdefault("log", []).append(ev)


def cmd_new(args):
    b = load()
    tid = next_id(b["tasks"])
    b["tasks"].append({"id": tid, "text": args.text, "priority": args.priority,
                       "status": "TODO", "owner": None, "created": now(),
                       "claimed": None, "result": None, "done": None})
    log_event(b, {"t": now(), "who": who(args), "event": "new", "id": tid, "text": args.text})
    save(b)
    print(f"created {tid}: {args.text} [{args.priority}]")


def cmd_list(args):
    b = load()
    rows = [t for t in b["tasks"] if not args.status or t["status"] == args.status]
    rows.sort(key=lambda t: ({"high": 0, "mid": 1, "low": 2}[t["priority"]], t["id"]))
    if not rows:
        print("(no tasks)")
        return
    for t in rows:
        owner = f" by {t['owner']}" if t["owner"] else ""
        res = f" -> {t['result']}" if t.get("result") else ""
        print(f"{t['id']:4s} [{t['priority']:4s}] {t['status']:10s} {t['text']}{owner}{res}")


def cmd_claim(args):
    b = load()
    for t in b["tasks"]:
        if t["id"] == args.id:
            if t["status"] == "IN_PROGRESS" and t.get("owner") and t["owner"] != who(args):
                sys.exit(f"refusing: {args.id} is IN_PROGRESS by {t['owner']}")
            t["status"] = "IN_PROGRESS"
            t["owner"] = who(args)
            t["claimed"] = now()
            log_event(b, {"t": now(), "who": who(args), "event": "claim", "id": args.id})
            save(b)
            print(f"claimed {args.id} by {who(args)}")
            return
    sys.exit(f"no task {args.id}")


def cmd_done(args):
    b = load()
    for t in b["tasks"]:
        if t["id"] == args.id:
            if t["status"] == "IN_PROGRESS" and t.get("owner") and t["owner"] != who(args):
                sys.exit(f"refusing: {args.id} is IN_PROGRESS by {t['owner']}")
            t["status"] = "DONE"
            t["owner"] = who(args)
            t["result"] = args.result
            t["done"] = now()
            log_event(b, {"t": now(), "who": who(args), "event": "done", "id": args.id,
                          "result": args.result})
            save(b)
            print(f"done {args.id} by {who(args)}: {args.result}")
            return
    sys.exit(f"no task {args.id}")


def cmd_log(args):
    b = load()
    rows = b.get("log", [])
    for ev in rows[-args.tail:]:
        print(f"{ev['t']} {ev['who']:12s} {ev['event']:6s} {ev.get('id','')} {ev.get('text','')}{ev.get('result','')}")


def main():
    ap = argparse.ArgumentParser(prog="coord.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("text"); p.add_argument("--priority", default="mid",
        choices=["low", "mid", "high"]); p.add_argument("--me", default=None)
    p = sub.add_parser("list"); p.add_argument("--status", default=None,
        choices=["TODO", "IN_PROGRESS", "DONE"]); p.add_argument("--me", default=None)
    p = sub.add_parser("claim"); p.add_argument("id"); p.add_argument("--me", default=None)
    p = sub.add_parser("done"); p.add_argument("id"); p.add_argument("result"); p.add_argument("--me", default=None)
    p = sub.add_parser("log"); p.add_argument("--tail", type=int, default=20)
    args = ap.parse_args()
    {"new": cmd_new, "list": cmd_list, "claim": cmd_claim, "done": cmd_done,
     "log": cmd_log}[args.cmd](args)


if __name__ == "__main__":
    main()
