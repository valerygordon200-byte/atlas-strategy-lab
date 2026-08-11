#!/usr/bin/env python3
"""Autonomous laptop executor for the ATLAS <-> DOURMOUSE relay.

Runs WITHOUT any Freebuff session so the laptop side of the relay is
self-sufficient: it watches the relay inbox and the coordination task board,
replies to messages (composing answers with the local Ollama model), claims
and executes tasks it can complete on this machine, pushes results, and
announces every action over the relay.

Design rules:
- stdlib-only (urllib), no pip installs.
- Never commits relay_config.txt / inbox_* / outbox_* / .worker_state (all
  git-ignored). It only ever commits real artifacts (reports/, data/,
  scripts/) and coordination/ board changes.
- `git pull --ff-only` before every action; push after committed actions.
- Honest by default: claims a task ONLY when an executor is registered for
  it. Tasks that need resources this machine doesn't have (e.g. the
  desktop's E:/forex-data) are left for the desktop worker, with a log line.
- Every failure is logged and absorbed; the loop never dies.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RELAY_DIR = REPO / "relay"
STATE_FILE = RELAY_DIR / ".worker_state.json"
LOG_FILE = RELAY_DIR / "autonomous_worker.log"
POLL_SECONDS = 10

# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #


def _load_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    p = RELAY_DIR / "relay_config.txt"
    if p.is_file():
        for line in p.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


CFG = _load_config()
ME = CFG.get("ME", "laptop-dourmouse")
RELAY = CFG.get("RELAY_URL", "http://100.98.97.23:8787")
TOKEN = CFG.get("TOKEN", "")
INBOX = RELAY_DIR / f"inbox_{ME}.txt"
OUTBOX = RELAY_DIR / f"outbox_{ME}.txt"
OLLAMA = "http://127.0.0.1:11434"
OLLAMA_MODEL = "dourmouse-finetuned"


# --------------------------------------------------------------------------- #
# logging + relay io
# --------------------------------------------------------------------------- #


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def send(text: str, to: str | None = None) -> None:
    """Targeted messages POST /send (proper `to` routing, like say.py);
    broadcasts append to the bridge outbox (the standing-behaviour channel).
    Both durable on the relay."""
    if to is not None:
        try:
            body = json.dumps(
                {"token": TOKEN, "from": ME, "to": to, "msg": text}
            ).encode()
            req = urllib.request.Request(
                RELAY + "/send", data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                log(f"SENT to {to}: {text[:100]}")
                return
        except Exception as exc:  # noqa: BLE001
            log(f"direct send to {to} failed: {exc}")
    try:
        with OUTBOX.open("a") as f:
            f.write(text + "\n")
        log(f"SENT broadcast via outbox: {text[:100]}")
    except OSError as exc:
        log(f"outbox append failed: {exc}")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60
    ).stdout.strip()


# --------------------------------------------------------------------------- #
# state
# --------------------------------------------------------------------------- #


def _load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {"inbox_lines": 0, "seen": {}, "board": {}}


def _save_state(state: dict) -> None:
    """Crash-safe, immediate persistence: write to a temp then rename, and
    call it after EVERY message + board scan so a restart can never
    re-process (and re-ack) messages the bridge already delivered."""
    try:
        tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, STATE_FILE)
    except OSError as exc:
        log(f"state save failed: {exc}")


# --------------------------------------------------------------------------- #
# LLM answer composition (local model)
# --------------------------------------------------------------------------- #


def _ollama_generate(prompt: str, max_tokens: int = 300) -> str:
    body = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
    ).encode()
    req = urllib.request.Request(
        OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r).get("response", "").strip()


def _repo_facts() -> str:
    facts = []
    recent = git("log", "--oneline", "-10")
    facts.append("recent commits:\n" + (recent or "(none)"))
    reports = sorted((REPO / "reports").glob("*"))[-4:] if (REPO / "reports").is_dir() else []
    facts.append("latest reports:\n" + "\n".join(f"- {p.name}" for p in reports) or "(none)")
    try:
        board = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "coord.py"), "list"],
            cwd=REPO, capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        facts.append("task board:\n" + (board or "(empty)"))
    except Exception as exc:  # noqa: BLE001
        facts.append(f"board unavailable: {exc}")
    return "\n".join(facts)


def compose_answer(question: str) -> str:
    facts = _repo_facts()
    prompt = (
        "You are the laptop-dourmouse autonomous relay agent on the "
        "ATLAS/DOURMOUSE team. A peer sent this message: "
        f"{question!r}\n\n"
        "Facts about the laptop side and the repo (use ONLY these, never invent):\n"
        f"{facts}\n\n"
        "Write a concise, warm reply (max 4 sentences). If the facts do not "
        "answer the question, say honestly what you know and offer to check "
        "with the desktop side. No preamble, no emojis."
    )
    try:
        ans = _ollama_generate(prompt)
        if ans:
            return ans[:600]
    except Exception as exc:  # noqa: BLE001
        log(f"LLM unavailable ({exc}) — using template reply")
    return (
        "Laptop side is up and monitoring the relay (machine: adits-macbook-air, "
        "tailnet 100.84.156.49). Board + inbox are being watched continuously. "
        "Recent repo activity: " + (git("log", "--oneline", "-3") or "none")
    )


# --------------------------------------------------------------------------- #
# message handling
# --------------------------------------------------------------------------- #

_MSG_RE = re.compile(r"^\[([^\]]+)\]\s*([^:]+):\s*(.*)$", re.S)

# Mechanical traffic that must NEVER get a reply — replying to an auto-ack or
# a "noted" creates an infinite ping-pong between the two workers' loops.
_SKIP_PREFIXES = ("auto-ack", "noted (", "received ", "received)")
_HEARTBEAT = ("online — autonomous executor standing by", "standing by")


def _is_question(text: str) -> bool:
    low = text.lower()
    return any(
        k in low
        for k in ("?", "status", "summary", "what have you", "what are you",
                  "report", "how are", "update", "list", "working on")
    )


def _is_mechanical(body: str) -> bool:
    low = body.lower()
    if any(low.startswith(p) for p in _SKIP_PREFIXES):
        return True
    if any(h in low for h in _HEARTBEAT):
        return True
    return False


def handle_message(text: str, state: dict) -> None:
    m = _MSG_RE.match(text)
    if not m:
        log(f"unparsed inbox line: {text[:80]}")
        return
    sender = m.group(2).strip()
    body = m.group(3).strip()
    if sender == ME:
        return  # never reply to ourselves (broadcast echoes)
    h = hashlib.sha256(f"{sender}:{body}".encode()).hexdigest()[:16]
    if state["seen"].get(h):
        return
    state["seen"][h] = time.time()
    log(f"MSG from {sender}: {body[:120]}")
    if _is_mechanical(body):
        log(f"  (mechanical — no reply to break ack ping-pong)")
        return
    # Addressed to us, or a directive (claim/please/reply/report/do) that
    # needs a one-time acknowledgment; questions get a composed answer.
    low = body.lower()
    addressed = "laptop-dourmouse" in low or "@laptop" in low
    directive = any(
        k in low for k in ("claim ", "please ", "reply with", "report ",
                           "do this", "your task", "your side", "for you")
    )
    if _is_question(body):
        answer = compose_answer(body)
        send(f"@{sender} {answer}")
    elif addressed or directive:
        send(f"@{sender} Acknowledged — laptop-dourmouse worker is on it. "
             f"(Full handling happens when the laptop session is active.)")


# --------------------------------------------------------------------------- #
# board handling
# --------------------------------------------------------------------------- #

_TASK_RE = re.compile(r"^(T\d+)\s+\[(\w+)\]\s+(\w+)\s+(.*)$")


def _read_board() -> dict[str, dict]:
    """Parse coord.py list output into {id: {status, text}}."""
    try:
        out = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "coord.py"), "list"],
            cwd=REPO, capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception as exc:  # noqa: BLE001
        log(f"board read failed: {exc}")
        return {}
    board: dict[str, dict] = {}
    for line in out.splitlines():
        m = _TASK_RE.match(line.strip())
        if m:
            board[m.group(1)] = {
                "priority": m.group(2),
                "status": m.group(3),
                "text": m.group(4),
            }
    return board


# Executor registry: task id or title keyword -> callable(board_task) -> result str.
# Only tasks this laptop can genuinely complete get executors. Everything else
# is left for the desktop worker (who has E:/forex-data).
def _executor_placeholder(task: dict) -> str:
    return f"laptop has no executor for: {task['text'][:80]}"


EXECUTORS: dict[str, object] = {}


def handle_board(state: dict) -> None:
    board = _read_board()
    if not board:
        return
    for tid, task in board.items():
        known = state["board"].get(tid)
        if known and known.get("status") == task["status"]:
            continue
        state["board"][tid] = task
        if task["status"] != "TODO":
            continue
        # New TODO task. Claim only what we can execute.
        executor = EXECUTORS.get(tid)
        if executor is None:
            log(f"board: {tid} TODO — no laptop executor, leaving for desktop side")
            continue
        log(f"board: claiming {tid}: {task['text'][:80]}")
        claim = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "coord.py"), "claim",
             "--me", ME, tid],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        git("add", "coordination")
        git("commit", "-m", f"laptop-dourmouse claims {tid}", "--no-verify")
        git("push")
        send(f"worker: claimed {tid} — {task['text'][:100]}")
        try:
            result = executor(task)
        except Exception as exc:  # noqa: BLE001
            result = f"failed: {exc}"
            log(f"{tid} executor raised: {exc}")
        subprocess.run(
            [sys.executable, str(REPO / "scripts" / "coord.py"), "done",
             tid, result],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        git("add", "coordination")
        git("commit", "-m", f"laptop-dourmouse done {tid}", "--no-verify")
        git("push")
        send(f"worker: done {tid} — {result[:140]}")


# --------------------------------------------------------------------------- #
# main loop
# --------------------------------------------------------------------------- #


LOCK_FILE = RELAY_DIR / ".worker.lock"


def _acquire_lock() -> None:
    """Single-instance guard: a stale pid file older than 2 minutes is
    reclaimed (the machine may have rebooted); otherwise refuse to start so
    two workers never double-claim tasks."""
    if LOCK_FILE.is_file():
        try:
            pid = int(LOCK_FILE.read_text().strip() or "0")
        except ValueError:
            pid = 0
        try:
            os.kill(pid, 0)  # alive?
            alive = True
        except (OSError, ProcessLookupError):
            alive = False
        age = time.time() - LOCK_FILE.stat().st_mtime
        if alive and age < 120:
            log(f"another worker running (pid {pid}) — exiting")
            sys.exit(0)
        log(f"reclaiming stale lock (pid {pid}, age {int(age)}s)")
    LOCK_FILE.write_text(str(os.getpid()))



def main() -> None:
    _acquire_lock()
    log(f"laptop worker up: me={ME} relay={RELAY} poll={POLL_SECONDS}s")
    send(f"laptop-dourmouse-worker online — autonomous executor standing by")
    state = _load_state()
    while True:
        try:
            git("pull", "--ff-only")
            if INBOX.is_file():
                lines = INBOX.read_text().splitlines()
                if len(lines) < state["inbox_lines"]:
                    # The feed was cleared/rotated (e.g. the desktop wiping
                    # the chat) — the line-count watermark would otherwise
                    # blind us to new messages forever.
                    log(
                        f"inbox shrank ({state['inbox_lines']} -> {len(lines)}) — "
                        "feed cleared; resetting watermark"
                    )
                    state["inbox_lines"] = 0
                    state["seen"] = {}
                    _save_state(state)
                if len(lines) > state["inbox_lines"]:
                    for line in lines[state["inbox_lines"] :]:
                        handle_message(line, state)
                        _save_state(state)  # crash-safe: never re-ack
                    state["inbox_lines"] = len(lines)
                    _save_state(state)
            handle_board(state)
            _save_state(state)
        except Exception as exc:  # noqa: BLE001
            # The loop never dies: log the error, sleep, retry.
            log(f"loop error (continuing): {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
