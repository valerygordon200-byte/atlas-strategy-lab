# RELIABILITY LOG — Phase 1.3 (laptop side)

Daily reliability log for the Phase 1 gate: **ten features reliable for 2
continuous weeks; zero unrecovered failures.** Logged by LAP (laptop agent)
from real events; the daily 15-min use is YOU (human) per the scaling plan.
Failures are recorded honestly — an entry is data, not a reproach.

## How to log (each day)

Append a new `### Day N — YYYY-MM-DD` section: uptime, failures (what broke,
how it was recovered, time down), feature usage, notes. One entry per day;
keep it short. The gate needs 14 consecutive days.

## Template

```
### Day N — YYYY-MM-DD
- Uptime: (server + daemons, checked at ~09:00 local)
- Failures: (0 / list each: symptom, recovery, downtime)
- Feature usage: (what ran / what the human used)
- Notes:
```

---

### Day 0 — 2026-08-12 (benchmark + audit day)

- **Uptime:** dourmouse server 36973 up 1h05m+ at audit; bridge 39413 + feed 39414 up (detached new-session daemons).
- **Failures (environmental, all recovered):**
  1. exFAT volume flakiness: `launchctl bootstrap` failed reading a plist — `Bootstrap failed: 5: Input/output error`; later `launchd` spawn denied by macOS System Policy sandbox (`deny file-read-data relay_config.txt` / `deny file-write-data bridge.log`) → jobs exited 1/126/EX_CONFIG. Recovered by switching to detached new-session processes (no launchd). **Recovered, no data loss.**
  2. Git on the exFAT volume: interactive rebase bookkeeping corrupted mid-run (duplicate `pick` in todo; pick never applied). Recovered by abort + clean merge (`fa15e47`); pushed. **Recovered, no data loss.**
  3. Stale dourmouse server under system Python (no `openai`) — relaunched correctly; stale pid file fixed.
- **Feature usage:** relay link (bridge/feed) exercised all session; portfolio PDFs shared via repo push; auth gate live-tested; 2,757 memory facts queried; 97 tests green.
- **Notes:** Phase 1.2 benchmark ran the whole day (~3 models × 13 tasks; 3–223 s/turn). AUDIT.md (Phase 1.1) produced; **release blocker found: dist ships workspace data (memory DB + 130 sessions, 8.4 GB).** 14-day gate clock: not started (starts after benchmark + audit findings land — see plan Gate 1).
