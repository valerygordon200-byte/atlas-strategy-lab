#!/usr/bin/env python3
"""chat_feed.py — live chat dashboard for the agent relay (stdlib only).

Run it on any machine (e.g. this desktop) pointed at the relay:
  python relay/chat_feed.py --relay http://<host>:8787 --token <secret> \
      --me desktop-atlas --port 8788

Then open http://127.0.0.1:8788/ — the page live-streams every relay message
(~2 s poll) and has a send box. Endpoints:
  GET  /           -> chat.html
  GET  /feed?since -> newest messages across all participants (proxies /all)
  GET  /who        -> participants (proxies /ping)
  POST /send       -> send as --me (proxies /send)
"""
import argparse
import json
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def get(relay, path, timeout=12):
    with urllib.request.urlopen(relay + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(relay, payload, timeout=10):
    req = urllib.request.Request(relay + "/send", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = (ROOT / "chat.html").read_bytes().replace(
                b"__ME__", self.server.me.encode())
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/feed"):
            from urllib.parse import urlparse, parse_qs
            since = 0
            try:
                since = int(parse_qs(urlparse(self.path).query).get("since", ["0"])[0])
            except ValueError:
                pass
            try:
                d = get(self.server.relay, f"/all?token={self.server.token}&since={since}")
                return self._json(200, d)
            except Exception as e:
                return self._json(502, {"ok": False, "error": str(e)})
        if self.path.startswith("/who"):
            try:
                d = get(self.server.relay, f"/ping?token={self.server.token}")
                return self._json(200, d)
            except Exception as e:
                return self._json(502, {"ok": False, "error": str(e)})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/send":
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "bad json"})
        payload = {"token": self.server.token, "from": self.server.me,
                   "to": body.get("to", "*"), "msg": body.get("msg", "").strip()}
        if not payload["msg"]:
            return self._json(400, {"error": "empty message"})
        try:
            return self._json(200, post(self.server.relay, payload))
        except Exception as e:
            return self._json(502, {"ok": False, "error": str(e)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--me", required=True)
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.relay, srv.token, srv.me = args.relay, args.token, args.me
    print(f"chat feed on http://{args.host}:{args.port}  relay={args.relay}  me={args.me}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
