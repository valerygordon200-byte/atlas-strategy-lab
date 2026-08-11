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
