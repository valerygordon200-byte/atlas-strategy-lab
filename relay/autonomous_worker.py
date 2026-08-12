#!/usr/bin/env python3
"""Autonomous laptop executor for the ATLAS <-> DOURMOUSE relay.

Runs WITHOUT any Freebuff session so the laptop side of the relay is
self-sufficient: it watches the relay inbox and the coordination task board,
replies to messages (composing answers with the local Ollama model), claims
and executes tasks it can complete on this machine, pushes results, and
announces every action over the relay.

For every substantive message it also writes a DIGEST entry
(relay/AGENT_DIGEST.md, git-ignored) so the main laptop agent can catch up on
"What desktop said, what the worker replied, and what needs doing" without
reading the whole feed::

    ## 2026-08-12T17:30Z — desktop-atlas
    SAID: <the message>
    REPLIED: <what the worker sent back>
    ACTION ITEMS: <LLM-extracted to-dos for the main agent>

Design rules:
- stdlib-only (urllib), no pip installs.
- Never commits relay_config.txt / inbox_* / outbox_* / .worker_state /
  AGENT_DIGEST.md (all git-ignored). It only ever commits real artifacts
  (reports/, data/, scripts/) and coordination/ board changes.
- `git pull --ff-only` before every action; push after committed actions.
- Honest by default: claims a task ONLY when an executor is registered for
  it. Tasks that need resources this machine doesn't have (e.g. the
  desktop's E:/forex-data) are left for the desktop worker, with a log line.
- Every failure is logged and absorbed; the loop never dies.
"""
from __future__ import annotations

import argparse
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
DIGEST_FILE = RELAY_DIR / "AGENT_DIGEST.md"
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
OLLAMA_MODEL = CFG.get("WORKER_OLLAMA_MODEL", CFG.get("OLLAMA_MODEL", "dourmouse-finetuned"))
HOST_DESC = CFG.get("HOST_DESC", "the ATLAS/DOURMOUSE relay host")
WORKER_BOARD = CFG.get("WORKER_BOARD", "1") == "1"


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


def send(text: str, to: str | None = None) -> bool:
    """Targeted messages POST /send (proper `to` routing, like say.py);
    broadcasts append to the bridge outbox (the standing-behaviour channel).
    Both durable on the relay. Returns True on success."""
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
                return True
        except Exception as exc:  # noqa: BLE001
            log(f"direct send to {to} failed: {exc}")
    try:
        with OUTBOX.open("a", encoding="utf-8") as f:
            f.write(text.replace("\n", " ") + "\n")
        log(f"SENT broadcast via outbox: {text[:100]}")
        return True
    except OSError as exc:
        log(f"outbox append failed: {exc}")
        return False


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60
    ).stdout.strip()


# --------------------------------------------------------------------------- #
# digest — what desktop said + what we did + what the main agent must do
# --------------------------------------------------------------------------- #


def write_digest(sender: str, said: str, replied: str, actions: list[str]) -> None:
    """Append one digest entry so the main laptop agent can catch up fast."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"## {ts} — {sender}",
        f"SAID: {said.strip()[:800]}",
        f"REPLIED: {replied.strip()[:400]}",
    ]
    if actions:
        lines.append("ACTION ITEMS (for the main agent):")
        for a in actions:
            lines.append(f"- {a.strip()[:300]}")
    else:
        lines.append("ACTION ITEMS: none flagged by the worker.")
    lines.append("")
    try:
        with DIGEST_FILE.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log(f"DIGEST: entry appended for {sender}")
    except OSError as exc:
        log(f"digest write failed: {exc}")


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


def _ollama_generate(prompt: str, max_tokens: int = 400) -> str:
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
    with urllib.request.urlopen(req, timeout=180) as r:
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


_ACTION_RE = re.compile(r"^ACTION ITEMS?[:\-]\s*(.*)$", re.I | re.M)
_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*(.+)$")


def compose_answer(question: str) -> tuple[str, list[str]]:
    """Compose a reply AND extract action items with the local model.

    Returns (reply, action_items). Falls back to a template + empty actions
    if the model is unavailable — never crashes the loop."""
    facts = _repo_facts()
    prompt = (
        f"You are {ME}, the {ME.split(chr(45))[0]}-side autonomous relay agent on "
        "the ATLAS/DOURMOUSE team (a two-machine commercial product build: "
        "desktop-atlas has the Windows machine + E:/forex-data, laptop-dourmouse "
        "has the Mac with Ollama + the repo). A peer sent this message:\n\n"
        f"{question!r}\n\n"
        "COLLABORATION PROTOCOL (relay/COLLABORATION_PROTOCOL.md): before starting "
        "any task, discuss the goal, risks, and open questions first — never assume. "
        "If the peer is proposing work, reply with a brief discussion (goal + risk + "
        "open question) rather than just an ack. If the peer reports a phase done or "
        "asks for confirmation, confirm or raise a concern explicitly. Be transparent "
        "about errors and limitations. No silent assumptions.\n\n"
        "Facts about this host and the repo (use ONLY these, never invent):\n"
        f"{facts}\n\n"
        "Write a concise, warm reply to that peer (max 4 sentences). If the "
        "facts do not answer the question, say honestly what you know and offer "
        "to check with the main agent.\n"
        "Then on its own lines write ACTION ITEMS for the MAIN agent (things "
        "the main laptop session must actually do in response) as a numbered "
        "or bulleted list, or 'ACTION ITEMS: none' if nothing needs doing.\n"
        "No preamble, no emojis."
    )
    try:
        raw = _ollama_generate(prompt)
        if not raw:
            raise RuntimeError("empty model response")
    except Exception as exc:  # noqa: BLE001
        log(f"LLM unavailable ({exc}) — using template reply")
        repo_line = (git("log", "--oneline", "-3") or "none").replace("\n", " | ")
        return (
            f"{HOST_DESC} is up and monitoring the relay. Board + inbox are "
            "being watched continuously. Recent repo activity: " + repo_line,
            [],
        )
    # Split the reply (first block) from action items.
    m = _ACTION_RE.search(raw)
    if m:
        reply = raw[: m.start()].strip()
        actions = [
            _ITEM_RE.match(ln).group(1)
            for ln in raw[m.start():].splitlines()
            if (match := _ITEM_RE.match(ln))
        ]
        actions = [a for a in actions if a.lower() != "none"]
    else:
        reply = raw
        actions = []
    return (reply[:600] or "Acknowledged.", actions[:8])


# --------------------------------------------------------------------------- #
# message handling
# --------------------------------------------------------------------------- #

_MSG_RE = re.compile(r"^\[([^\]]+)\]\s*([^:]+):\s*(.*)$", re.S)

# Mechanical traffic that must NEVER get a reply — replying to an auto-ack or
# a "noted" creates an infinite ping-pong between the two workers' loops.
_SKIP_PREFIXES = ("auto-ack", "noted (", "received ", "received)", "auto-reply (")
_HEARTBEATS = ("online — autonomous executor standing by", "standing by",
               "worker online", "worker: online")
# Ack-template echoes from the other worker's auto-reply ("...worker is on
# it. (Full handling...)") — answering them creates infinite ping-pong.
_ACK_TEMPLATE = "worker is on it"


def _is_mechanical(body: str) -> bool:
    low = body.lower()
    if any(low.startswith(p) for p in _SKIP_PREFIXES):
        return True
    if any(h in low for h in _HEARTBEATS):
        return True
    # Ack-template echoes from the other side's auto-reply — replying feeds
    # an infinite ack ping-pong between the two workers.
    if _ACK_TEMPLATE in low and "full handling" in low:
        return True
    # supervisor restart notices are operational noise, not conversation.
    if low.startswith("supervisor:"):
        return True
    return False


def _is_our_own(body: str) -> bool:
    low = body.lower()
    # The worker's own broadcasts / ack template echoed back.
    return low.startswith(f"{ME}-worker") or "worker is on it" in low


def _split_messages(text: str) -> list[str]:
    """Split the inbox file into messages. Desktop's messages often contain
    embedded newlines, so a message runs from a '[ts] sender:' line until the
    next line that starts with '[' (a new timestamp header)."""
    lines = text.splitlines()
    msgs: list[str] = []
    current: list[str] = []
    for ln in lines:
        if ln.startswith("[") and "] " in ln:
            if current:
                msgs.append("\n".join(current))
            current = [ln]
        else:
            if current:
                current.append(ln)
            # A stray line before any header is dropped (rotated feed edge).
    if current:
        msgs.append("\n".join(current))
    return msgs


def handle_message(text: str, state: dict) -> None:
    m = _MSG_RE.match(text)
    if not m:
        log(f"unparsed inbox block: {text[:80]}")
        return
    sender = m.group(2).strip()
    body = m.group(3).strip()
    if sender == ME:
        return  # never reply to ourselves (broadcast echoes)
    if _is_our_own(body):
        log(f"own echo from {sender} — skipping")
        return
    h = hashlib.sha256(f"{sender}:{body}".encode()).hexdigest()[:16]
    if state["seen"].get(h):
        return
    state["seen"][h] = time.time()
    log(f"MSG from {sender}: {body[:140]}")
    if _is_mechanical(body):
        log(f"  (mechanical — no reply to break ack ping-pong)")
        write_digest(sender, body, "worker skipped (mechanical traffic)", [])
        return
    # Every substantive message gets an LLM-composed reply + action items.
    reply, actions = compose_answer(body)
    ok = send(f"@{sender} {reply}", to=sender)
    status = "sent" if ok else "QUEUED (relay send failed)"
    write_digest(sender, body, f"{status}: {reply}", actions)


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
        subprocess.run(
            [sys.executable, str(REPO / "scripts" / "coord.py"), "claim",
             "--me", ME, tid],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        git("add", "coordination")
        git("commit", "-m", f"{ME} claims {tid}", "--no-verify")
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
        git("commit", "-m", f"{ME} done {tid}", "--no-verify")
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
        except SystemError:
            # Windows: os.kill on a dead pid raises SystemError, not OSError
            alive = False
        age = time.time() - LOCK_FILE.stat().st_mtime
        if alive and age < 120:
            log(f"another worker running (pid {pid}) — exiting")
            sys.exit(0)
        log(f"reclaiming stale lock (pid {pid}, age {int(age)}s)")
    LOCK_FILE.write_text(str(os.getpid()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="process the current inbox once, then exit (testing)")
    ap.add_argument("--reset-watermark", action="store_true",
                    help="start from the current inbox tail (skip old backlog)")
    args = ap.parse_args()

    _acquire_lock()
    log(f"laptop worker up: me={ME} relay={RELAY} poll={POLL_SECONDS}s")
    send(f"{ME}-worker online — autonomous executor standing by")
    state = _load_state()

    if args.reset_watermark and INBOX.is_file():
        n = len(_split_messages(INBOX.read_text(encoding="utf-8", errors="replace")))
        log(f"reset watermark: {state.get('inbox_lines', 0)} -> {n} (skip backlog)")
        state["inbox_lines"] = n
        _save_state(state)

    while True:
        try:
            git("pull", "--ff-only")
            if INBOX.is_file():
                text = INBOX.read_text(encoding="utf-8", errors="replace")
                msgs = _split_messages(text)
                if len(msgs) < state["inbox_lines"]:
                    # The feed was cleared/rotated (e.g. the desktop wiping
                    # the chat) — the line-count watermark would otherwise
                    # blind us to new messages forever.
                    log(
                        f"inbox shrank ({state['inbox_lines']} -> {len(msgs)}) — "
                        "feed cleared; resetting watermark"
                    )
                    state["inbox_lines"] = 0
                    state["seen"] = {}
                    _save_state(state)
                if len(msgs) > state["inbox_lines"]:
                    for msg in msgs[state["inbox_lines"]:]:
                        handle_message(msg, state)
                        _save_state(state)  # crash-safe: never re-ack
                    state["inbox_lines"] = len(msgs)
                    _save_state(state)
            if WORKER_BOARD:
                handle_board(state)
            _save_state(state)
        except Exception as exc:  # noqa: BLE001
            # The loop never dies: log the error, sleep, retry.
            log(f"loop error (continuing): {exc}")
        if args.once:
            break
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
