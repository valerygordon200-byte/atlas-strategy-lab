#!/usr/bin/env python3
"""coord_watch.py — poll the coordination board for new activity.

One-shot (default): pull quietly, print anything newer than the last-seen marker.
--watch: keep polling every N seconds.
State kept in coordination/.watch_state (git-ignored).

Run on either side in a terminal:
  python scripts/coord_watch.py            # one-shot
  python scripts/coord_watch.py --watch    # poll forever
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "coordination" / ".watch_state"


def git(args, quiet=False):
    r = subprocess.run(["git", "-C", str(ROOT)] + args, capture_output=True, text=True)
    if r.returncode != 0 and not quiet:
        print("git", " ".join(args), "failed:", r.stderr.strip()[:300], file=sys.stderr)
    return r.stdout.strip()


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"last_ts": None}


def save_state(s):
    STATE.write_text(json.dumps(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--tail", type=int, default=10)
    args = ap.parse_args()

    while True:
        git(["pull", "--ff-only", "-q"], quiet=True)
        board_file = ROOT / "coordination" / "tasks.json"
        st = load_state()
        new_rows = []
        if board_file.exists():
            board = json.loads(board_file.read_text(encoding="utf-8"))
            for ev in board.get("log", []):
                ts = ev.get("t", "")
                if st.get("last_ts") is None or ts > st["last_ts"]:
                    new_rows.append(ev)
        if new_rows:
            last = st.get("last_ts")
            shown = 0
            for ev in new_rows:
                print(f"{ev['t']} {ev['who']:12s} {ev['event']:6s} {ev.get('id','')} "
                      f"{ev.get('text','')}{ev.get('result','')}")
                shown += 1
                if shown >= args.tail:
                    break
            st["last_ts"] = max(ev["t"] for ev in new_rows)
            save_state(st)
        elif not args.watch and st.get("last_ts") is None:
            print("no board activity seen yet; run again after the other side pushes")
        if not args.watch:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
