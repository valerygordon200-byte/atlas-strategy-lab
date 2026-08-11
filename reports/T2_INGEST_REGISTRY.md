# T2 — Unified Data-Ingest Registry (DONE)

Date: 2026-08-11 · Owner: desktop-atlas · Status: DONE

## What was built

**`scripts/data_registry.py`** — the single entry point for every dataset in the
programme, replacing the per-script loaders. Logical keys resolve to physical
sources via **`market-data/registry.json`** (regenerated from actual drive
contents — nothing invented):

| Key family | Kind | Example |
|---|---|---|
| `fx:SYM:TF` | normalized OHLC parquet | `fx:USDJPY:d1` |
| `events` | Forex Factory archive | `events` |
| `commodity:SYM` | Yahoo continuous futures CSV | `commodity:ZS` |
| `fundamental:FILE` | FRED CSV | `fundamental:cpi_usd`, `fundamental:oil_wti` |
| `rate:CCY` | policy_rates.csv | `rate:USD` |
| `ledger` | live news-drift forward ledger | `ledger` |

**Quality gates run on every load()** (results queryable via `gate_report()`,
persisted to `reports/registry_gates.csv`): duplicate-timestamp removal (count
reported), non-positive price removal (WTI-2020 guard), per-source minimum
observation floor, and a >5-trading-day gap report. 82 gate rows, all green.

## Migration proof (the point of the exercise)

The two duplicated event loaders were replaced with the registry's canonical
implementation — which now lives in exactly ONE place:

- `fx_strict_battery.load_big_events()` → `load("events")`
- `news_deep_campaign.load_events_all()` → `load("events", ..., z_thr=None)`

Full campaign re-run through the migrated loader:

| Metric | Before (inline dupes) | After (registry) |
|---|---|---|
| USDJPY drift k=1, n | 2,856 | 2,853 |
| OOS t | 3.775 | **3.711** |
| OOS win rate | 53.96% | 53.84% |
| wf p | 0.028 | 0.019 |
| Gates | 4/6 (IS pair fail) | 4/6 (IS pair fail) |

**Regression PASS** — the headline holds within tolerance after migration.

## Data-quality finding the registry caught

The registry's composite dedupe (date_utc, title, currency) dropped **3 pairs
of double-counted events** — the same release captured twice with DIFFERENT
`actual` values (revised-vs-original prints): Personal Income MoM 2019-03-01
(1.0 vs −0.1), Personal Spending MoM 2019-04-29 (0.1 vs 0.9), Initial Jobless
Claims 2025-11-20 (224 vs 235). The old loaders fed both rows into the z
statistics and trade count. The registry now keeps the first occurrence and
records the drop in the gate log. The drift result barely moved (t 3.775→3.711)
— good evidence the effect is not carried by those noisy rows.

## Coverage sweep (100 keys)

- **91 loaded clean, all gates green.**
- 9 failures, all honest data-availability findings, none bugs:
  - 8× missing h1 parquets: BTCUSD, GOLD, OIL, SILVER, NDX, SP500, GSR — the
    collector only builds h1 for the FX majors. h1 coverage is partial; d1 is
    complete.
  - `fx:GSR:d1` — GSR parquet has a different schema (ratio series, not OHLC);
    needs a dedicated ratio kind, not the fx loader.
  - `fundamental:manifest` — manifest.csv is a data manifest, not a series.
- Every missing key now fails LOUDLY with the exact path and a hint ("run the
  collector") instead of a silent empty frame.

## Adoption status

- `fx_strict_battery.py` and `news_deep_campaign.py` migrated (proven above).
- `vol_module.py`, `spread_test.py`, `edge_scan.py` still use their own loaders
  — flagged for follow-up migration, not required for correctness.

## Files

- `scripts/data_registry.py` — the registry module
- `market-data/registry.json` — generated catalogue (schema_version 1)
- `reports/registry_gates.csv` — 82-row gate report
- `reports/T2_INGEST_REGISTRY.md` — this report
