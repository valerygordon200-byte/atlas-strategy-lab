# ATLAS ↔ DOURMOUSE — project status & system map

Last updated: 2026-08-11 (laptop-dourmouse session). This is the single
authoritative write-up of what the stack is, how it runs, what is done, and
what remains. Companion docs: `COMMERCIAL_SPEC.md` (contract), `DEPLOYMENT.md`
(runbook), `C3_EXECUTION_AUDIT.md`, `BOOKSHELF_AND_WEIGHTS.md`.

---

## 1. What this is

A two-machine quantitative research + agent-relay system:

- **ATLAS** — the research engine: 10 years of FX daily/hourly data, an
  84k-event economic calendar, 26 commodity futures, a strict six-gate
  backtest battery, and a live data registry + HTTP API. It is a research
  laboratory, not a trading system.
- **DOURMOUSE** — the commercial shell: a hub UI (ATLAS + TAILSCALE FEED tabs)
  and the local assistant.
- **TAILSCALE FEED** — a durable message relay that lets two autonomous agents
  (one per machine) coordinate, claim tasks, and stream a live chat.

Everything is stdlib Python (no pip installs) and token-gated where it faces a
network.

---

## 2. Architecture

```
DATA HOST (desktop, "desktop-atlas")            CLIENT (laptop, "laptop-dourmouse")
├─ relay_server.py   :8787  ◄───────────────────►├─ agent_bridge.py  --me laptop-dourmouse
├─ engine_api.py     :8790                       ├─ chat_feed.py     :8789  (dashboard)
├─ serve_hub.py      :8791  (hub.html)           ├─ autonomous_worker.py (inbox/board loop)
├─ pipeline_supervisor :8792 (keeps 6 alive)     └─ supervise_worker.py (restarts worker)
├─ data registry + market-data (E:/forex-data)
└─ desktop_worker.py (autonomous executor)
```

- **Relay** (one per tailnet, on the always-on desktop): durable per-recipient
  message queues. Bridges poll it; `/send` targets a recipient.
- **Engine** (data host): HTTP over the registry — `/api/health`, `/api/keys`,
  `/api/data/{key}`, `POST /api/backtest`. Token-gated (`X-Engine-Token`).
- **Hub** (any machine): three-tab shell (ATLAS / DOURMOUSE / FEED). Engine
  token injected server-side; FEED URL configurable via `HUB_FEED_URL`.
- **Workers**: watch the relay inbox + the shared task board, reply, claim and
  execute tasks. Fully autonomous — no human session required.

### Processes & ports (laptop side)
| process | port | how it stays up |
|---|---|---|
| `agent_bridge.py` | — (polls relay) | `start_bridge_detached.py` (double-fork) |
| `chat_feed.py` | 8789 | shell-detached |
| `autonomous_worker.py` | — | `supervise_worker.py` (crash-restart) |
| `supervise_worker.py` | — | shell-detached |

> macOS TCC blocks launchd-spawned processes from the `/Volumes` pen drive
> (`Operation not permitted`), so these run shell-detached and survive until
> reboot. True always-on needs Full Disk Access for Python + a LaunchAgent.

---

## 3. Task board (coordination/tasks.json)

| id | status | owner | summary |
|---|---|---|---|
| T1 | DONE (desktop wired it) | laptop→desktop | Central-bank gold net-purchase series; `weight_calibrator` GOLD factor live |
| T2 | DONE | desktop | Unified data-ingest registry |
| T3 | DONE | desktop-worker | Worker smoke test |
| T4 | DONE | desktop | C1 commercial spec |
| T5 | DONE | desktop | C2 engine HTTP service |
| T6 | TODO | laptop | C3 execution audit (report done; **paper connector NOT built**) |
| T7 | DONE | laptop | C4 chat/relay hardening (token gate + heartbeat) |
| T8 | DONE | desktop | C5 pipeline supervisor |
| T9 | DONE | laptop | C6 packaging (reviewed + 2 fixes shipped) |
| T10 | DONE | desktop | C7 golden regression suite |

### Definition of DONE for the whole programme (spec §4)
1. Three regressions pass on a **fresh machine** with the packaged setup.
2. One full paper-trade cycle (signal → entry → exit → ledger) completes
   through an audited connector with **real demo fills**.
3. Feed shows ≥ 1 week continuous uptime with heartbeats.

**Not yet met:** #2 (no live paper connector — see T6). #1 is now portable
(`health_check.py --base`). #3 is running toward it.

---

## 4. Data & provenance

### Central-bank gold (T1) — the flagship dataset
- `data/central_bank_gold.csv` — **annual** 2014–2025, WGC *Gold Demand Trends*
  (demand definition, includes estimates). Verified.
- `data/central_bank_gold_monthly.csv` — **monthly reported** Nov-2020 →
  Jun-2026, **55 verified months**, from WGC *Central Bank Gold Statistics*
  (reported-only, IMF IFS-based; **not** the GDT total). Row-by-row audited —
  the parser's first pass grabbed per-country/YTD figures; every value was
  corrected against its report's headline sentence.
- `data/fundamentals/central_bank_gold.csv` — canonical file in the exact
  `weight_calibrator.cb_gold_monthly()` schema (`date, total_net_purchases_tonnes`,
  month-end dates). Install: `cp` to `<BASE>/market-data/fundamentals/`.
- Build: `scripts/gold_monthly_build.py` (fetch/parse) + `gold_to_fundamentals.py`
  (schema emit).
- **Known limitation:** the WGC monthly series only exists from Nov-2020, so
  the GOLD factor's OOS sign-stability can't be validated against 2016–21 (the
  desktop flagged this). Gaps (no WGC report): Mar–Jun/Aug–Oct 2021,
  Feb–Apr/Aug–Sep 2022, Mar 2023 — fillable only via IMF IFS (needs a
  registration).

### Other data
- `data/registry.json` — the ingest registry: fx / events / commodity /
  fundamental / cpi / rate / ledger / gold sources with quality gates.
- `market-data/` is gitignored by design (lives on the desktop's E:/forex-data).

---

## 5. Golden regressions (C7 — the release gate)
`scripts/golden_regressions.py` recomputes the three locked results and fails
loudly on drift (`exit 1`):
- hog roll-check (raw path vs real path) — PASS
- USDJPY news-drift OOS t = 3.711 — PASS
- dual momentum +2.12%/mo, t = 4.49 — PASS

---

## 6. Execution layer — the open item (T6 / C8)
`reports/C3_EXECUTION_AUDIT.md` verdict: **LIVE connectors = 0**; Alpaca is
stubbed (keys only); MT5 / IBKR / T212 / TradingView were **absent**. The
intended venue was **IBKR paper** (`paper_trading_playbook.md`).

**C8 connector BUILT (desktop, pushed):** `scripts/ibkr_connector.py` does a
place → fill → ledger round trip via `ib_insync` (STK/FUT/CASH/CFD), reads
`IBKR_HOST/PORT/CLIENT_ID` from `dourmouse/.env`, appends to
`market-data/executions/executions.csv` in the forward-ledger style. Verified:
clean fail when the Gateway is down.

**Laptop side prepped:** `ib_insync` 0.9.86 installed in the dourmouse venv;
IBKR env added to `dourmouse/.env`; `--check` confirms the path works up to
port 7497. **Blocked on a human step:** an IBKR Gateway/TWS (paper account)
must be installed, logged in, API enabled on 7497, and reachable at
`192.168.1.95` / `100.84.156.49`. Exact steps: `docs/IBKR_PAPER_SETUP.md`.
This is the last unmet item toward spec §4 #2 (a full paper-trade cycle).

**The human step is now self-detecting:** `scripts/gateway_watch.py` (pushed
84e4487, running as a daemon on the Mac) polls 7497 on all three IPs every 5s;
the moment the Gateway comes up it runs `ibkr_connector.py --check` and
broadcasts "GATEWAY UP + PAPER CONNECTOR VERIFIED — ready for the first paper
fill" on the relay, so the desktop knows without anyone polling. Tested
end-to-end with a dummy listener (detection → check → re-arm on port close).

---

## 7. How the autonomous worker works
`relay/autonomous_worker.py` (stdlib): every ~10s it (a) `git pull`s the shared
repo, (b) watches the relay inbox, (c) watches the task board. New message →
composes a reply with the local model grounded in real repo state (git log,
reports, board). New task → claims + executes only if a registered executor
exists; otherwise it's honestly left for the desktop side. Flood-safe: ignores
auto-ack/heartbeat lines, replies once per substantive message, persists state
after every message, resets its watermark if the feed is cleared.

---

## 8. Known issues & next steps
1. **T6 / paper execution** — build + wire IBKR paper (or another venue) for a
   real demo-fill cycle. Biggest gap to commercial DONE.
2. **Gold monthly gaps** — IMF IFS registration to fill 2021–2023 gaps and
   extend the OOS window for the GOLD factor.
3. **Reboot survival** — laptop worker needs Full Disk Access + LaunchAgent for
   true always-on (currently survives until reboot).
4. **dourmouse GitHub repo** — the desktop's pushes to `adit2011238-glitch/dourmouse`
   403 (owner mismatch); hub files are mirrored in this repo under `dourmouse/`.
5. **Hub on laptop** — FEED pane now points at the laptop feed via `HUB_FEED_URL`.
6. **Laptop dashboard parity** — re-gated 2026-08-11 to the current C4 code
   (`--send-token`, 401/401/200 verified); orphaned supervisor removed so only
   one worker+supervisor pair runs.
7. **T11 board state** — set BLOCKED (owner joint) by the desktop; the only
   remaining action is the human Gateway login. The watcher above announces
   the moment that's done.

---

*Maintained by laptop-dourmouse. Update this file when the board or
architecture changes.*
