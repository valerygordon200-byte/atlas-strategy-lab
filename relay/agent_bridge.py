#!/usr/bin/env python3
"""agent_bridge.py — connect one agent to the relay (stdlib only).

- Pulls: every message addressed to this agent arrives in INBOX within ~1-2 s.
- Pushes: any line appended to OUTBOX is sent to the relay (default broadcast).
- Durable: messages sent while this bridge was down are delivered on reconnect
  (relay keeps per-recipient files; the bridge tracks its last_id).

Usage (run on each side, in a terminal):
  python relay/agent_bridge.py --relay http://192.168.1.95:8787 \
      --token <secret> --me desktop-atlas

Files (in the repo working copy, git-ignored):
  relay/inbox_<me>.txt    <- messages, one per line:  [ts] <from>: <msg>
  relay/outbox_<me>.txt   <- append a line here to send
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLL = 1.5      # fallback short-poll interval


def get(relay, path, timeout=20):
    with urllib.request.urlopen(relay + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(relay, payload):
    req = urllib.request.Request(
        relay + "/send", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--me", required=True)
    ap.add_argument("--inbox", default=None)
    ap.add_argument("--outbox", default=None)
    args = ap.parse_args()
    inbox = Path(args.inbox or (ROOT / f"inbox_{args.me}.txt"))
    outbox = Path(args.outbox or (ROOT / f"outbox_{args.me}.txt"))
    state = ROOT / f".bridge_{args.me}.state"
    inbox.touch()
    outbox.touch()
    last_id = 0
    if state.exists():
        try:
            last_id = int(state.read_text().strip() or "0")
        except ValueError:
            last_id = 0
    sent_offset = outbox.stat().st_size  # bytes already forwarded
    print(f"bridge up: me={args.me} relay={args.relay} inbox={inbox} outbox={outbox}")

    while True:
        # --- pull ---
        try:
            d = get(args.relay, f"/recv?token={args.token}&me={args.me}"
                                f"&last_id={last_id}&timeout=15")
            for m in d.get("msgs", []):
                line = f"[{m['ts']}] {m['from']}: {m['msg']}\n"
                with open(inbox, "a", encoding="utf-8") as f:
                    f.write(line)
                try:
                    print(line.rstrip(), flush=True)
                except UnicodeEncodeError:
                    pass  # console charset (cp1252) can't print some glyphs
            if d.get("msgs"):
                last_id = d["max_id"]
                state.write_text(str(last_id))
        except Exception as e:
            print(f"[pull error] {e}", flush=True)
            time.sleep(POLL)
        # --- push ---
        try:
            size = outbox.stat().st_size
            if size > sent_offset:
                with open(outbox, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(sent_offset)
                    lines = f.read().splitlines()
                for line in lines:
                    if line.strip():
                        post(args.relay, {"token": args.token, "from": args.me,
                                          "to": "*", "msg": line})
                sent_offset = size
        except Exception as e:
            print(f"[push error] {e}", flush=True)


if __name__ == "__main__":
    main()
