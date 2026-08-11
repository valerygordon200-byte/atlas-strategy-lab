# Part 9.2 — Volatility Prediction Module: Report
Date: 2026-08-11 · Campaign: Multi-Track Edge Search

## What was built
Composite HAR-RV-style OLS forecast of next-day |USDJPY return| from four signals:
realised-vol persistence (1/5/22-day components), Bollinger(20,2) width percentile
(trailing 252d), and |BTCUSD daily return| (cross-asset). Fit in-sample
(2016-08 → 2021-12), evaluated out-of-sample (2022 → 2026-08) untouched.
Volume signal: **unusable** — Yahoo FX volume is all zeros for USDJPY; excluded and
flagged (the graveyard already says volume predicts size, but there is no data here).

## Validation (Stage 1 redefined for a forecast) — PASS

| Metric | IS | OOS |
|---|---|---|
| Quintile means of actual next-day \|r\| (low→high forecast) | .25/.26/.28/.31/.44% | .31/.44/.48/.52/.57% |
| Monotonic across 5 quintiles | ✅ | ✅ |
| Q5/Q1 ratio | 1.77 | 1.86 |
| Spearman(forecast, actual) | 0.204 | 0.221 |
| OOS R² (composite) | — | **0.0161** |
| OOS R² (naive: yesterday's \|r\|) | — | **−0.808** |
| OOS R² (naive: 20-day avg vol) | — | 0.0136 |

Permutation (1000 runs, target shuffled, both statistics): **p_rho = 0.000, p_qspread = 0.000**
— the predictive relationship is overwhelmingly not noise. R² of 1.6% is small in
absolute terms but is the normal magnitude for daily vol forecasting, and it beats
both naive benchmarks (yesterday's vol alone is an *anti*-predictor OOS, R² −0.81;
the multi-horizon HAR structure is what carries the signal).

## Application to the USDJPY news drift (1,201 OOS events) — does NOT help

| Forecast-vol tercile | n | Mean net/event | t | Win |
|---|---|---|---|---|
| Low | 401 | +0.056% | 2.21 | 55.9% |
| Mid | 400 | +0.011% | 0.33 | 49.2% |
| High | 400 | **+0.160%** | **3.77** | 56.8% |

| Sizing | Ann. return | Sharpe |
|---|---|---|
| Flat (1 unit/event) | +19.1% | 1.73 |
| Vol-scaled (∝ 1/forecast-vol) | +15.9% | **1.56** |

## Honest conclusion — the two answers differ (as the brief predicted they might)
1. **The forecast validates.** Next-day move size is genuinely predictable, monotonically
   calibrated out-of-sample, with permutation p < 0.001 — consistent with the project's
   prior "size is predictable, direction is not" finding (EDGE_SCAN_REPORT: 9/12 pairs
   hold OOS).
2. **It does not help the drift strategy.** The drift's edge is *concentrated in
   high-vol states* (t 3.77 vs 0.33 mid), so conventional inverse-vol sizing (1/fvol)
   shrinks exactly the best trades: Sharpe 1.73 → 1.56. The module's correct use is
   risk management only — sizing caps, worst-case estimates, and stop placement —
   never as a directional signal, and not as a position shrinker on this strategy.
   For any *future* strategy whose edge is not vol-state-dependent, vol-scaling
   should be re-tested rather than assumed.
