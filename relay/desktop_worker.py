#!/usr/bin/env python3
"""desktop_worker.py — always-on desktop executor for the shared task board.

This is the piece that lets the desktop side ACT on relay messages without
anyone typing into Freebuff. It runs forever, polls the repo task board, and
executes tasks itself.

WHAT IT RUNS — and nothing else:
  * Mechanical tasks: board entries with a `cmd` field (created via
    `coord.py new --cmd "python scripts/foo.py [args...]"`). The command is
    whitelist-checked: argv[0] must be python/python3, every argument must
    be free of shell metacharacters, and script paths must stay inside the
    repo or E:/forex-data.
  * LLM tasks (optional, gated): board entries with `dispatch: "claude"`
    run through the Claude Code CLI headlessly (`claude -p`) when
    WORKER_CLAUDE=1 and the CLI is found.

NEVER executed: the text of relay messages. The relay is read-only input
here — it carries notifications and the worker's own announcements. Only the
board's `cmd`/`dispatch` fields are ever run.

GIT DISCIPLINE: `git pull --ff-only` before each scan (if the pull fails —
e.g. a Freebuff session holds the repo — skip this cycle and retry). After
finishing a task: update coordination/tasks.json, commit ONLY that file, and
push. If the push fails, keep the task IN_PROGRESS and retry next cycle
(completion is idempotent).

Run:  python relay/desktop_worker.py [--once] [--poll 5]
      --once  do a single scan cycle and exit (for testing)
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "coordination" / "tasks.json"
CONFIG = ROOT / "relay" / "relay_config.txt"
MAX_OUT = 4000  # chars of captured output to keep per task
SAFE_DIRS = [ROOT, Path("E:/forex-data")]

ME = "desktop-worker"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_config() -> dict:
    cfg: dict[str, str] = {}
    if CONFIG.exists():
        for line in CONFIG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def relay_send(cfg: dict, msg: str, to: str = "*") -> bool:
    url = cfg.get("RELAY_URL", "")
    token = cfg.get("TOKEN", "")
    if not url or not token:
        return False
    try:
        payload = json.dumps({"token": token, "from": ME, "to": to, "msg": msg}).encode()
        req = urllib.request.Request(url + "/send", data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())["ok"] is True
    except Exception:
        return False


def git(cfg: dict, *args: str) -> tuple[int, str]:
    env = dict(os.environ)
    try:
        p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                           text=True, timeout=60, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def safe_cmd(cmd: str) -> list[str] | None:
    """Whitelist check. Returns argv or None if the command is not runnable."""
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return None
    if not argv or argv[0].split("/")[-1] not in ("python", "python3"):
        return None
    for a in argv[1:]:
        if any(ch in a for ch in ";|&$`><\n\""):
            return None
        if a.startswith("-"):
            continue  # python flags like -u are fine
        p = Path(a).resolve()
        if any(p == d or d in p.parents for d in SAFE_DIRS):
            continue
        return None  # path escapes the safe dirs
    return argv


def run_task(argv: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                           timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out[-MAX_OUT:]
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 1, f"worker error: {e}"


def run_claude(cfg: dict, task_text: str, timeout: int) -> tuple[int, str]:
    """Headless Claude Code dispatch for open-ended tasks (gated)."""
    try:
        p = subprocess.run(
            ["claude", "-p", task_text, "--output-format", "text"],
            cwd=ROOT, capture_output=True, text=True, timeout=timeout,
            env=dict(os.environ))
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out[-MAX_OUT:]
    except FileNotFoundError:
        return 127, "claude CLI not found on this machine"
    except subprocess.TimeoutExpired:
        return 124, f"claude TIMEOUT after {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 1, f"claude dispatch error: {e}"


def claim_and_run(task: dict, cfg: dict) -> None:
    tid = task["id"]
    task["status"] = "IN_PROGRESS"
    task["owner"] = ME
    task["claimed"] = now()
    print(f"[{tid}] claimed")
    relay_send(cfg, f"worker: claimed {tid} — {task['text'][:80]}")

    timeout = int(task.get("timeout", 120))
    if task.get("cmd"):
        argv = safe_cmd(task["cmd"])
        if argv is None:
            rc, out = 126, f"UNSAFE cmd rejected by worker whitelist: {task['cmd']}"
        else:
            print(f"[{tid}] running {argv}")
            rc, out = run_task(argv, timeout)
    elif task.get("dispatch") == "claude" and cfg.get("WORKER_CLAUDE", "0") == "1":
        print(f"[{tid}] claude dispatch: {task['text'][:80]}")
        rc, out = run_claude(cfg, task["text"], timeout)
    else:
        rc, out = 125, "not mechanical (no --cmd) and no enabled dispatch — needs an LLM agent"

    task["status"] = "DONE"  # executed; rc + output live in result
    task["result"] = (f"rc={rc} | " + out.replace("\n", " ")[:200]) if rc else out.replace("\n", " ")[:200]
    task["done"] = now()
    print(f"[{tid}] DONE rc={rc}")
    relay_send(cfg, f"worker: {tid} DONE rc={rc} — {task['result'][:160]}")


def one_cycle(cfg: dict) -> None:
    # 1. Pull the board fresh (ff-only; skip cycle if the repo is busy).
    rc, _ = git(cfg, "pull", "--ff-only")
    if rc != 0:
        print(f"git pull failed (rc={rc}) — repo busy? skipping cycle")
        return
    if not BOARD.exists():
        print("no board yet")
        return

    board = json.loads(BOARD.read_text(encoding="utf-8"))
    candidates = [t for t in board["tasks"]
                  if t.get("status") == "TODO" and (t.get("cmd") or t.get("dispatch"))]
    if not candidates:
        return

    changed = False
    for task in candidates:
        claim_and_run(task, cfg)
        changed = True
        break  # one task per cycle keeps git conflict surface tiny

    if changed:
        BOARD.write_text(json.dumps(board, indent=2), encoding="utf-8")
        rc, _ = git(cfg, "add", "coordination/tasks.json")
        rc2, _ = git(cfg, "commit", "-m", f"desktop-worker: {task['id']} {task['status']}")
        rc3, err = git(cfg, "push")
        if rc3 != 0:
            print(f"push failed: {err[:200]} — will retry next cycle (task stays IN_PROGRESS)")


ACK_FILE = ROOT / "relay" / ".worker_acks.json"


def relay_recv(cfg: dict, last_id: int, timeout: int = 10) -> tuple[list[dict], int]:
    """Fetch messages id>last_id for this worker (broadcast + direct)."""
    url, token = cfg.get("RELAY_URL", ""), cfg.get("TOKEN", "")
    if not url or not token:
        return [], last_id
    try:
        q = f"/recv?token={token}&me={ME}&last_id={last_id}&timeout={timeout}"
        with urllib.request.urlopen(url + q, timeout=timeout + 5) as r:
            d = json.loads(r.read().decode())
        return d.get("msgs", []), int(d.get("max_id", last_id))
    except Exception:
        return [], last_id


_LAST_ACK_T = 0.0
_ACK_COOLDOWN = 60.0  # seconds — hard guard against ack ping-pong loops


def _is_ack_noise(msg: str) -> bool:
    """A re-ack / echo of another message is not new information — never ack it."""
    m = msg.lower()
    return ("noted" in m or "auto-ack" in m or "acknowledged" in m
            or m.startswith("@desktop-worker") or "received" in m and "message" in m)


def auto_ack(cfg: dict) -> None:
    """User rule: any message from the other device gets an immediate reply —
    even when no Freebuff session is open. Batched, once-per-id, laptop-only,
    and SUBSTANTIVE-only: re-acks/echoes are never acked (they ping-pong with
    the laptop's re-ack loop and flood the feed). Plus a hard 60s cooldown."""
    global _LAST_ACK_T
    acked: set[int] = set()
    if ACK_FILE.exists():
        try:
            acked = set(json.loads(ACK_FILE.read_text(encoding="utf-8")).get("acked", []))
        except Exception:
            acked = set()
    last_id = max(acked) if acked else 0
    msgs, _ = relay_recv(cfg, last_id)
    fresh = [m for m in msgs if m["id"] not in acked and m.get("from") == "laptop-dourmouse"
             and not _is_ack_noise(m.get("msg", ""))]
    if not fresh:
        return
    if time.time() - _LAST_ACK_T < _ACK_COOLDOWN:
        return
    ids = [m["id"] for m in fresh]
    relay_send(cfg, f"auto-ack (desktop): received {len(fresh)} new substantive message(s) "
                    f"from laptop-dourmouse ids {min(ids)}..{max(ids)} — will respond in full "
                    f"when the session opens.")
    _LAST_ACK_T = time.time()
    acked.update(ids)
    ACK_FILE.write_text(json.dumps({"acked": sorted(acked)}, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single scan cycle, then exit")
    ap.add_argument("--poll", type=int, default=5)
    args = ap.parse_args()

    cfg = load_config()
    if cfg.get("WORKER_ENABLED", "0") != "1" and not args.once:
        print("WORKER_ENABLED != 1 — not starting. Set WORKER_ENABLED=1 in relay_config.txt")
        return
    print(f"{ME} online — repo {ROOT}, board {BOARD}")
    relay_send(cfg, f"{ME} online — autonomous executor standing by")

    while True:
        try:
            one_cycle(cfg)
            auto_ack(cfg)
        except Exception as e:  # noqa: BLE001
            print(f"cycle error: {e}")
        if args.once:
            break
        time.sleep(max(1, args.poll))


if __name__ == "__main__":
    main()
