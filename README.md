# ATLAS Strategy Lab — research + the dourmouse commercial stack

This repo is two things now:

1. **The research laboratory** (below): 900+ strategies through a strict
   six-gate battery, honest verdicts, zero survivor selection.
2. **The commercial stack**: dourmouse is the shell; **ATLAS** (backtest
   engine + full data registry) and the **TAILSCALE FEED** (live two-machine
   agent chat) live inside it as separate UIs.

## Commercial stack — quickstart

```
setup.bat                       # one-command: clone/pull, deps, config, SMOKE TEST
python scripts/pipeline_supervisor.py   # keeps relay/feed/worker/bridge/engine/hub alive (:8792)
open http://127.0.0.1:8791/hub.html     # the hub: ATLAS / DOURMOUSE / FEED tabs
```

- Engine API: `:8790` — `GET /api/keys`, `GET /api/data/{key}`,
  `POST /api/backtest` (`usdjpy_drift_k1`, `registry_gates`,
  `golden_regressions` — the release gate).
- Data: `E:orex-data` via `scripts/data_registry.py` (one loader, quality
  gates on every load). See `DEPLOY.md` for the full topology, lifecycle,
  laptop join, and security notes. Board + relay: `coordination/`, `relay/`.

---
# ATLAS Strategy Lab

Probabilistic research on FX and commodity trading strategies: **900+ strategies
tested with a strict six-gate backtest battery**, honest verdicts, zero survivor
selection. Built on the ATLAS research pipeline (10 years of FX daily + hourly
data, 84k-event economic calendar with forecast/actual, 26 commodity futures
2000→2026).

> This repo is a research laboratory, not a trading system. Nothing here is a
> recommendation to trade. Edges decay; every result is a claim to re-test, not
> a truth.

## The protocol (why the numbers are trustworthy)

Every strategy runs the same strict battery, in order:

1. **In-sample excellence** — mean, t-stat (naive + Newey-West lag-5), win rate,
   outlier-trimmed (best/worst year dropped).
2. **In-sample Monte Carlo permutation** (1000) — null = random calendar / random
   signals; gate **p < 1%**.
3. **Blind holdout** — direction locked in-sample, tested on untouched data,
   net of costs; t > 2 and p < 0.05.
4. **Walk-forward** — direction re-estimated on trailing data only (or a
   trailing-profitability gate), next period traded. Zero lookahead.
5. **Walk-forward permutation** (1000) — random-window null through the *same*
   machinery.
6. **Walk-forward Monte Carlo bootstrap** (5000) — mean 5/50/95%, P(mean ≤ 0).

Plus a **cost ladder** (financing 8/15/25% for commodities; 0.5/1/2-pip RT for
FX) — a strategy that dies at realistic costs is not a strategy.

Key honesty guards: expanding-window z-scores (standardisation never sees the
future), next-day-open entry (the pre-event move is never captured), vintage
audit requirement (stored news "actuals" must be proven as-published).

## Campaigns

| Campaign | Scope | Tests | Result |
|---|---|---|---|
| Seasonal grid | 26 commodities × 12 months + 39 named windows | 344 | 6 holdout survivors → 0/8 pass the full strict battery |
| FX massive campaign | 12 pairs × momentum/vol/reversal/calendar/cross-asset/news/intraday | 535 | 8 OOS survivors → news under-reaction drift on 5 USD pairs |
| FX strict battery | news drift ×5 pairs, reversal ×2 | 7 | **USDJPY news drift: 4/6 gates** (effect emerged post-2021) |
| FX round-2 | news-family depth + gold-silver ratio + per-title | ~420 | in progress → committed when complete |

## Headline findings

- **News under-reaction drift (USDJPY)** is the strongest FX candidate: holdout
  NW t = +3.14, walk-forward p = 0.003, bootstrap P(mean ≤ 0) = 0.000, positive
  in 5/5 out-of-sample years, robust across the cost ladder. It fails the two
  *in-sample* gates because the effect genuinely did not exist in 2016–2021 —
  it is a post-2021 phenomenon. **Vintage audit on the event store is still
  unresolved** — the drift is not tradeable until stored "actuals" are proven
  as-published.
- **Commodity seasonality**: the hog complex is the only family with real
  structure (Hogs Aug short: +13.9%/yr holdout, t=5.6, 92% win) — but it passes
  5/6 gates, missing only the strictest walk-forward permutation (p=0.076).
- **Everything else died** — momentum, calendar, day-of-week, carry, cross-asset,
  breakouts all fail net of costs, exactly as the pre-registered priors predicted.
- **Volatility predicts size, not direction** — four independent signals
  (Bollinger squeeze, bitcoin→FX, volume, event-day vol) all survive; usable for
  sizing, never for entry.

## Repo layout

```
scripts/
  edge_scan.py            data loader + Newey-West + pair constants
  fx_campaign.py          FX massive campaign (D1 core, 495 tests)
  fx_campaign_extra.py    FX campaign extras (baskets, news, H1 sessions)
  fx_campaign_round2.py   round-2 campaign, every test through the full battery
  fx_strict_battery.py    strict six-gate battery for FX candidates
  strict_battery.py       strict six-gate battery for seasonal candidates
  seasonal_backtest.py    seasonal data + monthly returns
  seasonal_batch.py       seasonal selection->lock->holdout pipeline
reports/
  fx_campaign_report.md / fx_campaign_leaderboard_full.csv   (535 tests)
  fx_strict_battery.md / fx_strict_battery.csv               (six-gate verdicts)
  strict_battery.md / strict_battery.csv                     (seasonal verdicts)
  seasonal_campaign_report.md / seasonal_leaderboard.csv     (344 tests)
  seasonal_locked.json / seasonal_holdout.csv                (locked directions)
  backtest_results.*.csv                                     (compound sims)
strategy_catalog.json     machine-readable locked candidates + verdicts
```

## How to run

```bash
pip install -r requirements.txt
# point BASE at a data store with market-data/ (see scripts/edge_scan.py)
python scripts/fx_strict_battery.py     # six-gate battery on FX candidates
python scripts/fx_campaign_round2.py    # round-2 scan + battery
python scripts/seasonal_batch.py        # seasonal selection pipeline
```

Data layout expected: `market-data/normalized/<PAIR>/<PAIR>_d1.parquet` (FX),
`market-data/events/events.parquet` (calendar: forecast + actual),
`market-data/raw/yahoo/COMM_*_d.csv` (commodities).

## Setup — relay + deployment (C1/C6)

The repo is also the relay hub for the laptop/desktop agent pair. Everything is
stdlib-only Python — no pip installs needed.

```bash
# 1. quick health check (5s): repo, relay ping, dashboard, worker, board
python3 scripts/health_check.py --relay http://<host>:8787 --token <TOKEN>

# 2. bridge (client side) — polls the relay's inbox/outbox for this machine
python3 relay/agent_bridge.py --relay http://<host>:8787 --token <TOKEN> --me <name>

# 3. chat dashboard (optional, any machine)
python3 relay/chat_feed.py --relay http://<host>:8787 --token <TOKEN> --me <name> --port 8789

# 4. autonomous worker (optional, client side) — watches inbox + task board,
#    replies and executes claimed tasks without a human session
python3 relay/autonomous_worker.py --relay http://<host>:8787 --token <TOKEN> --me <name>
python3 relay/supervise_worker.py        # crash-restart supervisor for the worker
```

Full runbook (roles, five processes, firewalls, tokens): **`docs/DEPLOYMENT.md`**.
The commercial spec with acceptance criteria: **`reports/COMMERCIAL_SPEC.md`**.

## Honesty policy

- Negative results are reported as loudly as positive ones — see
  `strict_battery.md`: **0/8** seasonal candidates pass all six gates.
- Every headline number is attacked: cost ladders, outlier trim, random-window
  permutations, roll-convention checks, vintage audits.
- The master question, applied to every result: *"What would this number look
  like if the signal contributed nothing?"* — computed explicitly, every time.

## 2026-08-10 correction — z-score sd-underflow bug (important)

A bug was found and fixed in the expanding per-title z-score used by the FX
campaigns (`fx_campaign_round2.py`, `fx_strict_battery.py`):

- **Bug**: `expanding().std()` on near-constant surprise series (e.g. titles
  that usually print exactly the forecast) underflows to ~1e-16, making
  `z = (surprise - mean)/sd` explode to ±1e15. The `|z| >= 0.5` "big surprise"
  filter then passed noise events, and the sign for those events was random.
- **Fix**: `min_periods=20`, sd floored at 1e-12 (near-constant series →
  NaN → excluded), and z winsorized at ±8.
- **Impact**: the previous full six-gate PASS (`streak_USDJPY_HM`, 6/6) was an
  artifact of this bug — **it no longer passes** (4/6). Corrected totals:
  **0/403 round-2 tests full-PASS, 0/7 battery candidates PASS.**
- **What survives**: the **USDJPY news under-reaction drift** remains the
  strongest candidate — 4/6 gates, failing only the two in-sample gates (the
  effect genuinely emerges post-2021): holdout NW t=+3.03, walk-forward p=0.012,
  bootstrap P(mean≤0)=0.001, robust across the cost ladder and outlier trim.
- All corrected numbers are in `reports/fx_round2_*.csv/md`,
  `reports/fx_strict_battery.*`, and `strategy_catalog.json`.

## 2026-08-10 further steps — vintage audit + roll check (read this)

Two decisive follow-ups were run on the two remaining candidates. Full detail:
`reports/FURTHER_STEPS.md` (reproducible: `scripts/vintage_audit.py`).

**1. Vintage audit — PASSES (USDJPY news drift).** 27 of 28 sampled events
match the documented as-published prints, including the four most
revision-prone releases in the store: NFP Mar-2020 (−701K, later −870K),
NFP Apr-2020 (−20.5M, later −22.1M), NFP Apr-2021 (+266K), CPI May-2022
(+8.6%), plus all 21 US GDP advance estimates and EIA crude April-2020 weeks
(store holds +8.99M/+4.59M vs today's revised +10.14M/+6.31M — proof it is
NOT the current vintage). The drift's actuals are as-published. The drift
remains 4/6 gates: a real 2022+ regime edge, absent 2016–21.

**2. Hogs August SHORT — KILLED (roll artifact).** The full seasonal program
collapsed under the roll-convention check. Raw continuous August: −13.9%
(t=−8.08). Excluding the contract-roll gap (not a tradeable move): +0.05%
(t=0.05). Mechanism confirmed: August is the most backwardated hog roll month
(mean −10% gap; spring-farrowed hogs reach slaughter weight Aug–Oct → cash
prices fall → deferred contracts discount the front). Same test kills Hogs
Apr/Dec, Gasoline Sep, Corn Jul, Live/Feeder Cattle May. **The seasonal
catalog is void — do not trade it.**
