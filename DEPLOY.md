# DEPLOY — the dourmouse + atlas commercial stack

The stack is one machine's worth of services plus a two-machine coordination
layer. This document covers a single-machine deployment (the desktop) and how
the laptop joins.

## Topology

```
                 dourmouse shell (hub.html :8791)
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
     ATLAS           DOURMOUSE      TAILSCALE FEED
   engine :8790    dispatch core    relay :8787 / feed :8788
   registry         (ui/index.html)  (chat dashboard)
   golden gates
        └──────────────┬───────────────┘
                 supervisor :8792
        (restart-on-crash for every service below)
```

## Services (all guarded by `scripts/pipeline_supervisor.py`)

| Service | Port | Command (cwd) | Health |
|---|---|---|---|
| relay | 8787 | `relay/relay_server.py --port 8787 --token T` | GET /ping |
| feed | 8788 | `relay/chat_feed.py --relay :8787 --token T --me X --port 8788` | GET /feed |
| worker | — | `relay/desktop_worker.py --poll 5` | process scan |
| bridge | — | `relay/agent_bridge.py --relay :8787 --token T --me X` | process scan |
| engine | 8790 | `scripts/engine_api.py --port 8790` | GET /api/health |
| hub | 8791 | `tools/serve_hub.py --port 8791` (dourmouse checkout) | GET /hub.html |
| supervisor | 8792 | `scripts/pipeline_supervisor.py --port 8792` | GET / (status JSON) |

Token: `relay/relay_config.txt` (git-ignored; copy from `relay_config.example.txt`).

## Fresh-machine setup

```
Windows:  setup.bat        (clone/pull, deps, config, smoke test)
macOS:    bash setup.sh    (same steps; also used by the laptop)
```

The smoke test (`E:\forex-data\scripts\health_check.py`) proves: registry
builds, core series load with quality gates, and all three golden regressions
PASS. Exit 0 only if the whole stack is healthy.

## Data

All data lives on the pen drive at `E:\forex-data`:
- `market-data/normalized/` — 12+ assets × d1/h1 OHLC parquet
- `market-data/raw/yahoo/` — continuous commodity futures CSVs
- `market-data/events/events.parquet` — 84k+ Forex Factory events (live-captured)
- `market-data/fundamentals/` + `market-data/rates/` — FRED + policy rates
- `market-data/bookshelf/` + `market-data/registry.json` — the catalogue
- `market-data/news_drift/forward_ledger.csv` — live USDJPY drift capture

`scripts/data_registry.py` is the ONLY loader: `load("fx:USDJPY:d1")`,
`load("events", currency="USD", ...)`, `load("commodity:ZS")`, ... Quality
gates (dedupe, non-positive guard, min obs, gap report) run on every load.

## Lifecycle

- **Start everything**: run the supervisor (it starts anything missing and
  keeps it alive). `python scripts/pipeline_supervisor.py --port 8792`.
- **Watch it**: the hub's PIPELINE row polls :8792 — live dots per service,
  ⚠N marks restarts. Restarts are also announced on the feed.
- **Release gate**: hub ATLAS tab → `run golden_regressions`, or
  `python scripts/golden_regressions.py`. ALL PASS or it's blocked.
- **Backtests**: `POST /api/backtest` with `{"id":"usdjpy_drift_k1"}`,
  `{"id":"registry_gates"}`, `{"id":"golden_regressions"}`.
- **Stop**: kill the supervisor first (it restarts everything else), then
  anything remaining.

## Laptop joins (second machine)

1. Tailscale on both machines, same tailnet (desktop `100.98.97.23`).
2. Laptop: `git clone` this repo; `bash setup.sh` (smoke test expects the
   data drive — on the laptop run the config-only path, the data stays on
   the desktop and is served via the engine API).
3. Laptop runs `relay/agent_bridge.py --relay http://100.98.97.23:8787
   --token T --me laptop-dourmouse` — joins the feed, gets its own inbox.
4. Coordination: `coordination/tasks.json` + `scripts/coord.py` (claim/done
   discipline), `relay/` for real-time chat, `reports/` for artifacts.

## Security notes

- `relay_config.txt` and any token: git-ignored, never commit.
- Engine API binds loopback by default; bind wider only behind the tailnet
  and set `ENGINE_TOKEN`.
- The worker executes ONLY board `cmd` fields (whitelisted
  `python <repo-relative script>`), never relay message text.
