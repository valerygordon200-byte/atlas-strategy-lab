# Agent Coordination Protocol

How two Freebuff agents (this account, your laptop account, dourmouse, etc.) coordinate
through this repo. There is no direct agent-to-agent chat feature in Freebuff — this
file-based protocol is the channel. It works across accounts, machines, and devices,
because it only needs git + this repo.

## The rules (both sides must follow)

1. **One task board, one source of truth.** `tasks.json` is the board. `TASKS.md` is a
   human-readable view of it. Never edit both — always via `scripts/coord.py`.
2. **Pull before you look, push after you act.**
   - `git pull` → `python scripts/coord.py list` → find a TODO task
   - `python scripts/coord.py claim <id>` → commit+push IMMEDIATELY (claims must land
     fast so the other side sees the lock)
   - do the work, commit+push results to the normal folders (reports/, scripts/, data/)
   - `python scripts/coord.py done <id> "<one-line result>"` → commit+push
3. **Never edit a task someone else has claimed** (status IN_PROGRESS, owner = them).
   If it looks stale (claimed >24h with no log entry), comment on it, don't take it.
4. **Keep tasks small and outcome-shaped.** "Run X and report" not "investigate X".
   One push per task minimum so the other side always sees progress.
5. **Everything material lands in the repo** (reports/, scripts/, data/), not just the
   task line. The board is the pointer; the repo is the content.
6. **Same-machine bonus:** if both accounts run on the same PC, they also share
   `E:\forex-data` and `C:\Users\ankit\Documents\forex-engine` directly — use the repo
   board for *who does what*, and the drive for *shared data*.

## Workflow example

```bash
# Agent A (this account)
git pull && python scripts/coord.py new "Source central-bank gold flow data 2015-present" --priority high
git add coordination scripts && git commit -m "Add task" && git push

# Agent B (laptop account, later)
git pull && python scripts/coord.py list --status TODO
python scripts/coord.py claim T3
git add coordination && git commit -m "Claim T3" && git push
# ... does the work, pushes data + report ...
python scripts/coord.py done T3 "WGC monthly series assembled; weights.json updated"
git add -A && git commit -m "T3 done" && git push

# Agent A (this account, next pull) sees T3 DONE and can pick up the result.
```

## The orchestrator pattern (main objective -> delegated execution)

When you give this account's agent a MAIN OBJECTIVE, it acts as coordinator:

1. **Decompose** the objective into small outcome-shaped tasks and add them to the
   board (`coord.py new`), each with a priority.
2. **Broadcast the plan** over the relay: `objective: <one line>; tasks: T1..Tn;
   I'm taking T<x>, T<y> is open` — the other agent sees it in ~1-2 s.
3. **Delegate by leaving open TODOs.** Any agent may claim one
   (`coord.py claim`, push immediately). One owner per task (claim lock).
4. **Both sides execute autonomously** and push artifacts to the repo; when done:
   `coord.py done <id> "<one-line result>"` + a relay message.
5. **Integrate:** the coordinator reviews every DONE task, runs any final
   validation, writes the objective summary to `reports/`, and reports to the user.
6. **Standing behaviour of every agent:** check `relay/inbox_<me>.txt` and the task
   board at the start of every turn; reply over the relay before ending a turn.
7. **Escalation:** a task stuck IN_PROGRESS >24h with no log entries is stale —
   comment on it (never silently take it); after 48h the coordinator may reclaim it.

The board is the plan, the relay is the conversation, the repo is the work product.

## Real-time option (instead of polling)

The task board is async (minutes). For **real-time talk**, use `relay/` (README there):
run `relay/relay_server.py` on the laptop, run `relay/agent_bridge.py` on each side,
and read `relay/inbox_<me>.txt` / write `relay/outbox_<me>.txt`. Messages arrive in
~1-2 s and are durable (offline sides catch up on reconnect). Use the board for tasks
that outlive a conversation; use the relay for live back-and-forth.

## The autonomous executor (desktop-worker) — tasks run WITHOUT a session

`relay/desktop_worker.py` runs 24/7 on the desktop (started by `start_client.bat`
when `WORKER_ENABLED=1` in `relay_config.txt`). It polls the board and executes
tasks itself, so work happens even when no Freebuff session is open:

- **Mechanical tasks** — post with `--cmd`, the worker runs it and commits the
  result. Command must be `python <repo-relative script> [args...]`; anything
  else is rejected by its whitelist.
  ```bash
  python scripts/coord.py new "Rebuild USDJPY drift report" --cmd "python scripts/regen_report.py" --me laptop-dourmouse
  ```
- **LLM tasks** — post with `--dispatch claude`; runs through Claude Code CLI
  headlessly, but only when the desktop config has `WORKER_CLAUDE=1` (off by
  default — it costs API credits).
- Every lifecycle step (claim, run, done + output) is announced on the relay, so
  it appears in the chat feed in real time. Relay message text is NEVER executed
  — only board `cmd`/`dispatch` fields, and only whitelisted ones.
- Test locally any time: `python relay/desktop_worker.py --once`.

## Optional: watcher (notify on new pushes)

`scripts/coord_watch.py` polls the repo (default every 60s) and prints new tasks /
status changes / pushes it has not seen. Run it in a terminal on either side:

```bash
python scripts/coord_watch.py            # one-shot: show anything newer than last seen
python scripts/coord_watch.py --watch    # keep polling
```

## Identities

`coord.py` identifies you via `--me NAME`, or the `AGENT_ID` env var, or falls back to
hostname. Use distinct names ("desktop-atlas", "laptop-dourmouse") so the board shows
clearly who owns what.
