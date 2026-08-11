#!/usr/bin/env python3
"""say.py — send a one-off message through the relay (no bridge needed).

Usage:
  python relay/say.py --relay http://192.168.1.95:8787 --token <secret> \
      --from laptop-dourmouse --to desktop-atlas "the message"
  (omit --to to broadcast to everyone)
"""
import argparse
import json
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--from", dest="frm", required=True)
    ap.add_argument("--to", default="*")
    ap.add_argument("msg")
    args = ap.parse_args()
    req = urllib.request.Request(
        args.relay + "/send",
        data=json.dumps({"token": args.token, "from": args.frm,
                         "to": args.to, "msg": args.msg}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        print(json.loads(r.read().decode("utf-8")))


if __name__ == "__main__":
    main()
