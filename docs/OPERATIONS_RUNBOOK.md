# Operations Runbook — ATLAS ↔ DOURMOUSE relay (laptop side)

Live operational knowledge for the Mac side of the two-machine agent relay.
Pair with `docs/DEPLOYMENT.md` (fresh-machine setup), `docs/PROJECT_STATUS.md`
(state), and `relay/LAPTOP_SETUP.md` (first-time join). This file is about
**running and recovering the stack day-to-day**.

All paths are relative to the repo root (`/Volumes/ATLAS /dourmouse-4.0.0/atlas-strategy-lab`).

---

## 1. The laptop process inventory

| Process | Script | Port/role | Log |
|---|---|---|---|
| bridge | `relay/agent_bridge.py` | connects laptop → desktop relay (100.98.97.23:8787) | `relay/bridge_laptop.log` |
| autonomous worker | `relay/autonomous_worker.py` | reads inbox/board every ~10s, replies/executes; **supervised** | `relay/autonomous_worker.log` |
| supervisor | `relay/supervise_worker.py` | restarts the worker on crash (TCC blocks launchd) | same log |
| chat dashboard | `relay/chat_feed.py --port 8789` | laptop feed UI; `/send` is token-gated | `relay/chat_laptop.log` |
| gateway watcher | `scripts/gateway_watch.py` | polls IBKR Gateway 7497, announces readiness | `relay/gateway_watch.log` |

Expected state (healthy):

```bash
ps aux | grep -E 'agent_bridge|autonomous_worker|supervise_worker|chat_feed|gateway_watch' | grep -v grep
# exactly: 1 bridge, 1 worker, 1 supervisor, 1 chat_feed, 1 gateway_watch
```

`gateway_watch` is a single long-running poller, not a supervisor loop — the
other four should be **exactly one each**. A duplicate supervisor or worker is
a bug to fix (see §4), not a feature.

Quick health sweep:

```bash
curl -s http://100.98.97.23:8787/ping          # relay alive -> {"ok": true, participants: {...}}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8789/   # 200 = laptop dashboard up
nc -z -w 2 127.0.0.1 7497 && echo GATEWAY_UP || echo gateway-down
git -C . pull origin main                       # in sync with the desktop's work
```

---

## 2. The relay contract (quick reference)

- **Send**: `python3 relay/say.py --relay http://100.98.97.23:8787 --token <TOKEN> --from laptop-dourmouse "msg"` → `{'ok': True, 'id': N}`.
- **Receive**: `tail -f relay/inbox_laptop-dourmouse.txt`. The bridge appends.
- **Token**: `relay/relay_config.txt` (git-ignored). `X-Engine-Token` header
  gates the chat dashboard `/send` (C4). Laptop dash token: `laptop-dash-2026`.
- **Board**: `python3 scripts/coord.py list`, `claim --me laptop-dourmouse <id>`,
  `done --me laptop-dourmouse <id>`.
- **Feed format**: inbox lines `[ISO8601] from: text`. The worker ignores
  `[heartbeat]`, `auto-ack`, and its own replies to stay flood-safe.
- Never commit: `relay_config.txt`, `.worker_state.json`, `inbox_*`, `outbox_*`.

---

## 3. Restarting a laptop process

The wrapper's backgrounded children are killed when the calling shell dies, so
a plain `nohup ... &` does **not** survive. Use the double-fork daemonizer:

```bash
# example: chat dashboard
cat > /tmp/start_x.py <<'EOF'
import os, sys
REPO = "/Volumes/ATLAS /dourmouse-4.0.0/atlas-strategy-lab"
LOG = REPO + "/relay/chat_laptop.log"
pid = os.fork()
if pid > 0: os._exit(0)
os.setsid()
pid = os.fork()
if pid > 0: os._exit(0)
os.chdir(REPO)
dn = os.open(os.devnull, os.O_RDWR); lf = os.open(LOG, os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o644)
os.dup2(dn,0); os.dup2(lf,1); os.dup2(lf,2)
os.execvp("python3", ["python3","relay/chat_feed.py","--relay","http://100.98.97.23:8787",
  "--token","<TOKEN>","--me","laptop-dourmouse","--port","8789","--send-token","laptop-dash-2026"])
EOF
python3 /tmp/start_x.py   # returns instantly; child is reparented to launchd
```

The gateway watcher has its own launcher (`/tmp/start_gw.py`, venv python at
`/Volumes/ATLAS /dourmouse-4.0.0/.venv/bin/python` — it must run in the venv,
`ib_insync` lives there).

---

## 4. Recovery procedures (all hit in production, all now handled)

1. **Runaway ack ping-pong** (auto-ack → "noted" → auto-ack → …): the worker
   now treats `auto-ack`/`heartbeat` lines as mechanical and never replies.
   Fix if it regresses: `relay/autonomous_worker.py`, the
   `_is_mechanical()` predicate.
2. **Cleared feed blinds the worker**: the worker tracks progress by line
   count. If the desktop clears the feed, delete/reset
   `relay/.worker_state.json` (`inbox_lines: 0`) so it re-reads from the top.
3. **Duplicate supervisor/worker** (happens after manual restarts): `ps` for
   the pair, keep the newest `supervise_worker.py`, kill the older one and its
   children. Duplicate workers double-reply to every message.
4. **exFAT rebase corruption**: the pen drive tangles `git rebase` todo lists
   (duplicated picks, done/todo overlaps). Deterministic path:
   - `git rebase --abort` (or clear `.git/rebase-*` if sticky)
   - reset working tree to `origin/main`
   - replay local commits with `git am` from `git format-patch` of your commits
   - verify with `git log origin/main..HEAD` and a `git status` clean tree
5. **Relay send failures**: transient (the desktop's supervisor restarts its
   services). Retry in 5s; `gateway_watch.say()` already retries 4×/5s.
6. **Dashboard running stale code**: the running `chat_feed` used the retired
   `--dash-token` flag while the file on disk moved to `--send-token`. Always
   restart the dashboard from the current file after pulling, and re-test:
   no token → 401, wrong token → 401, right token → 200 (C4 contract).

---

## 5. The gold data pipeline (T1)

- `scripts/gold_monthly_build.py` — discovers WGC monthly report URLs from the
  sitemap + archives, downloads article/PDF, extracts the headline net-purchase
  figure, and merges with a vetted table.
- `data/central_bank_gold_monthly.csv` — 58 verified months (Nov-2020 →
  Jun-2026). **Every row was audited against its report's headline**; the first
  parser pass grabbed per-country/YTD numbers as monthly totals and was
  corrected (e.g. Dec-2024 is −3t, not −11t; Nov-2022 is +50t, not +673t).
- `scripts/gold_to_fundamentals.py` — normalizes to the `weight_calibrator`
  schema: `date, total_net_purchases_tonnes` (month-end dates).
  `data/fundamentals/central_bank_gold.csv` is the canonical input.
- **Known gaps**: Mar–Jun + Aug–Oct 2021, Feb–Apr + Aug–Sep 2022, Mar 2023 —
  no WGC monthly report was published for those months; the only clean source
  is IMF IFS (registration-gated). The GOLD factor's OOS window can't be
  extended until that's filled.

---

## 6. Remaining path to commercial DONE (spec §4)

1. **Human step — IBKR Gateway (paper) login** (`docs/IBKR_PAPER_SETUP.md`):
   install Gateway, log into the paper account, API on 7497, Trusted IPs
   `192.168.1.95`/`100.84.156.49`. **The gateway watcher detects this
   automatically** and broadcasts "GATEWAY UP + PAPER CONNECTOR VERIFIED" —
   no polling needed.
2. **First paper fill** — run `scripts/ibkr_connector.py --check`, then the
   desktop drives a real place→fill→ledger round trip (T11 acceptance).
3. **1-week uptime** — all six services under the desktop's supervisor; laptop
   processes survive until reboot. True always-on needs Full Disk Access +
   LaunchAgent for the laptop worker (macOS TCC blocks launchd-spawned
   processes on the pen drive).

---

## 7. Process history log (why things are the way they are)

- 2026-08-11: ack ping-pong fixed; worker made flood-safe + crash-safe state.
- 2026-08-11: worker's clear-feed fix (watermark reset).
- 2026-08-11: chat dashboard re-gated to current C4 code (`--send-token`);
  orphaned supervisor removed; single worker+supervisor pair confirmed.
- 2026-08-11: `gateway_watch.py` deployed — auto-detect 7497, verify, announce
  (tested end-to-end with a dummy listener; retry 4×/5s added after one
  transient relay hiccup).
