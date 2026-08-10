# Platform scan candidates — backtest results

Date: 2026-08-10 · Follows `reports/platform_scan.md` (the eligibility-filtered shortlist).
Both candidates from the scan were immediately tested through the project's strict battery.

---

## Candidate 1 — Cointegration pairs trading: DEAD (0/21)

**Test:** `scripts/pairs_coint_test.py`. The exact QC mechanism (research/15347, Miao):
rolling OLS hedge ratio on log prices, Engle-Granger ADF(1) on residuals (t < −3.37),
entry z ±2.33, exit |z| < 0.5, stop 4σ, 126-day training re-estimated monthly,
1-pip-per-leg-per-side costs. Universe: our local FX + metals (EURUSD, GBPUSD, AUDUSD,
USDJPY, USDCAD, GOLD, SILVER → 21 pairs). IS ≤ 2022-12, holdout 2023→2026.

**Result: 0/21 pairs pass. All FAIL or INSUFFICIENT.**
Best pair GBPUSD-USDCAD: IS t=+2.14 but holdout t=+0.05 (nothing). AUDUSD-USDJPY was
the only significant IS pair (t=−2.39) and it was *negative* — mean reversion firing in
the wrong direction. Mean daily net returns are ~±0.002–0.004% — statistically
indistinguishable from zero after costs.

**What this means:** daily-frequency stat-arb on the most-traded FX majors is arbitraged
to nothing — consistent with everything else this programme found about major FX.
The QC reference's impressive numbers were on 10-minute US bank-stock data with
undisclosed costs; our honest daily-FX version has no edge. Note the caveat: this test
covers the *daily FX/metals* version only. The equities intraday version needs minute
equity data we don't have, so it remains untested rather than proven dead — but at $100
with our data, the testable version is dead.

**Bug caught during testing:** an immediate re-entry after stop-out inflated early
results; fixed with a 5-day cooldown before the final run (results above are post-fix).

---

## Candidate 2 — Dual / absolute momentum (Antonacci): PASSES the strict battery

**Test:** `scripts/dual_momentum_test.py`. Exact published mechanism: monthly, 12-month
total return per asset, absolute filter (only assets with 12m return > 0 eligible),
relative rank → hold top-k (k=1 and k=2), cash (SHY) if nothing eligible. Universe:
SPY, EFA, VNQ, GLD, DBC, IEF, SHY (20y of daily closes fetched from Yahoo, 2006→2026,
stored as `market-data/raw/yahoo/ETF_*.csv`). Costs: 0.5 bps/trade + 0.5%/yr drag.
IS ≤ 2017-12, holdout 2018→2026.

### Strict battery — all six gates

| Variant | IS %/mo | IS t | p_is | HO %/mo | HO t | p_ho | WF %/mo | p_wf | boot | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **dual_mom_top1** | +1.612 | 3.83 | 0.001 | **+2.124** | **4.51** | 0.001 | +1.817 | 0.001 | 0.0000 | **PASS** |
| **dual_mom_top2** | +1.246 | 3.74 | 0.001 | +1.740 | 5.47 | 0.001 | +1.426 | 0.001 | 0.0000 | **PASS** |
| buyhold SPY (ref) | +0.614 | 1.73 | 0.043 | +1.141 | 2.45 | 0.009 | +0.826 | 0.001 | 0.0012 | FAIL |
| buyhold IEF (ref) | +0.199 | 1.26 | 0.084 | −0.101 | −0.53 | 0.708 | +0.030 | 0.001 | 0.4040 | FAIL |

Both buy-and-hold references FAIL — the strategy's pass is not just capturing the equity
premium. The absolute-momentum cash filter (the documented crash-protection mechanism)
is doing real work.

### Robustness battery

| Test | Result |
|---|---|
| Cost ladder 0x / 2x / 5x | **PASS at all three** (t 4.02 / 3.65 / 3.09) |
| Null-signal (random ranking) | **FAIL** (IS t=−0.73, holdout t=+1.11) — the momentum ranking itself produces the edge; the machinery contributes nothing |
| Holdout first half (2018–22) | PASS — t=+3.63, +2.20%/mo |
| Holdout second half (2022–26) | PASS — t=+2.82, +2.04%/mo |
| Outlier-trimmed WF | +20.4%/yr |

### Honest caveats

1. **This is a published, well-known strategy** (Antonacci 2014) — not a discovered
   edge. It has been widely traded since publication; post-publication decay is a real
   prior. What our test adds: it independently replicates on 2006–2026 data through our
   strict machinery, and the edge *strengthened* in the 2018–2026 holdout rather than
   decaying.
2. **Account-size reality at $100:** whole-share minimums bite — SPY ~$560, GLD ~$230,
   VNQ/IEF/EFA ~$80–95, DBC ~$20, SHY ~$84. With whole shares a $100 account can hold
   ~1 position (DBC or one IEF/EFA/VNQ). Fractional shares (T212-style) make it
   implementable; whole-share brokers do not. This is a monthly-rebalance allocation
   strategy, so it is a portfolio-construction layer, not a high-turnover week-to-week
   P&L driver.
3. Expectation: modest outperformance with materially lower drawdown than buy-and-hold
   (2022: strategy in cash/SHY while SPY fell ~18%). At $100 the absolute $ gain is
   small; its value scales with the account.

---

## Bottom line

- Candidate 1 (cointegration pairs on FX/metals, daily): **killed** — 0/21, arbitraged away.
- Candidate 2 (dual momentum): **first strategy in the ~1,300-tested programme to pass
  the full strict battery AND the robustness battery.** Replicates Antonacci's published
  result on 2006–2026 data. Not a secret — but a *confirmed*, independently-validated
  allocation edge with crash protection, and the strongest result the platform scan (or
  this programme) has produced.
- Next step if pursued: decide execution vehicle (fractional-share broker) and wire the
  monthly rebalance into the live pipeline; or hold as the risk-allocation layer while
  the USDJPY news-drift forward test continues.
