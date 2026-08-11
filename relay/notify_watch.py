#!/usr/bin/env python3
"""notify_watch.py — desktop notification watcher for the relay feed.

The user's ask: 'whenever laptop sends a message, notify me — I don't need to
be here.' This daemon polls the relay, and on every SUBSTANTIVE message from
laptop-dourmouse pops a native Windows notification (sender + preview) and
logs it. It never replies — replying is the worker's job (desktop_worker.py).

Behaviour:
  * Watermark persisted in relay/.notify_watch.json — restarts never re-notify.
  * Ack-noise (re-acks/echoes/heartbeats) is filtered exactly like the worker's.
  * Bursts are batched into ONE toast (min 15s between toasts).
  * --once runs a single poll and exits (for testing).

Run:  python relay/notify_watch.py [--once] [--poll 5]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "relay" / "relay_config.txt"
STATE = ROOT / "relay" / ".notify_watch.json"
LOG = ROOT / "relay" / "notifications.log"

ME = "notify-watch"
_MIN_TOAST_GAP = 15.0


def load_config() -> dict:
    cfg: dict[str, str] = {}
    if CONFIG.exists():
        for line in CONFIG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_line(msg: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{now()} {msg}\n")
    except OSError:
        pass
    print(f"[{now()}] {msg}", flush=True)


def is_ack_noise(msg: str) -> bool:
    m = msg.lower()
    return ("noted" in m or "auto-ack" in m or "acknowledged" in m
            or m.startswith("@desktop-worker") or "received" in m and "message" in m
            or m.startswith("[heartbeat]") or m.startswith("worker:"))


def fetch(cfg: dict, last_id: int, timeout: int = 8) -> tuple[list[dict], int]:
    url, token = cfg.get("RELAY_URL", ""), cfg.get("TOKEN", "")
    if not url or not token:
        return [], last_id
    try:
        q = f"/recv?token={token}&me={ME}&last_id={last_id}&timeout={timeout}"
        with urllib.request.urlopen(url + q, timeout=timeout + 5) as r:
            d = json.loads(r.read().decode())
        return d.get("msgs", []), int(d.get("max_id", last_id))
    except Exception as e:  # noqa: BLE001
        log_line(f"fetch error: {e}")
        return [], last_id


def toast(title: str, text: str) -> None:
    """Native Windows balloon notification via PowerShell (no deps)."""
    # escape for single-quoted PowerShell string: ' -> ''
    text = text[:300].replace("'", "''")
    title = title.replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$n = New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon = [System.Drawing.SystemIcons]::Information;"
        "$n.Visible = $true;"
        f"$n.BalloonTipTitle = '{title}';"
        f"$n.BalloonTipText = '{text}';"
        "$n.ShowBalloonTip(12000);"
        "Start-Sleep -Seconds 14;"
        "$n.Dispose();"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                        "-Command", ps], timeout=25, check=False)
    except Exception as e:  # noqa: BLE001
        log_line(f"toast failed: {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--poll", type=int, default=5)
    args = ap.parse_args()

    cfg = load_config()
    if not cfg.get("RELAY_URL") or not cfg.get("TOKEN"):
        log_line("RELAY_URL/TOKEN missing — not starting")
        return

    state: dict = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    last_id = int(state.get("last_id", 0))
    last_toast_t = 0.0
    log_line("notify-watch online — desktop notifications armed")

    while True:
        msgs, max_id = fetch(cfg, last_id)
        fresh = [m for m in msgs if m["id"] > last_id
                 and m.get("from") == "laptop-dourmouse"
                 and not is_ack_noise(m.get("msg", ""))]
        if fresh and time.time() - last_toast_t >= _MIN_TOAST_GAP:
            if len(fresh) == 1:
                m = fresh[0]
                preview = m.get("msg", "")[:240].replace("\n", " ")
                toast("DOURMOUSE // laptop-dourmouse",
                      f"[id {m['id']}] {preview}")
                log_line(f"toast: id {m['id']} — {preview[:120]}")
            else:
                ids = [m["id"] for m in fresh]
                previews = " | ".join(
                    m.get("msg", "")[:90].replace("\n", " ") for m in fresh[:3])
                toast("DOURMOUSE // laptop-dourmouse",
                      f"{len(fresh)} messages (ids {min(ids)}..{max(ids)}): {previews}")
                log_line(f"toast: batch ids {min(ids)}..{max(ids)}")
            last_toast_t = time.time()
        if max_id > last_id:
            last_id = max_id
            STATE.write_text(json.dumps({"last_id": last_id}, indent=2),
                             encoding="utf-8")
        if args.once:
            break
        time.sleep(max(1, args.poll))


if __name__ == "__main__":
    main()
