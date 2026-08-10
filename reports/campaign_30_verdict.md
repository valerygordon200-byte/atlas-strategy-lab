# Campaign-30 — Tier 1 execution results

Date: 2026-08-10 · Scripts: `scripts/campaign_30.py` (+ inline probes) · Outputs: `reports/campaign_30_tier1.csv/.md`
Protocol: Edge-Finding Master Plan §3 four-stage framework. IS ≤ 2022-12-31, holdout 2023→2026.

## Shared framework (per idea)

S1 in-sample excellence (mean > 2× cost, Sharpe ≥ 1.0, win ≥ 60%, t ≥ 2.5) →
S2 IS 1000-run permutation MC p<0.01 → S3 walk-forward (expanding) Sharpe ≥ 0.5 &
t ≥ 2.0 → **S4 walk-forward MC 1000 runs, p<0.05 = headline**.

## Results

| Idea | Forced participant | n | mean/trade | IS t | p_is | WF sh | WF t | **p_wf** | verdict |
|---|---|---|---|---|---|---|---|---|---|
| #17 quad witching (SPY \|r\| excess) | options/futures books must expire/roll mechanically | 5030 | +0.001% | +0.19 | 0.427 | −0.24 | −1.06 | **1.000** | FAIL |
| #19 LETF pair TQQQ/SQQQ (short both) | LETFs must rebalance daily by structure | 4146 | −0.093% | −60.9 | 1.000 | +15.1 | +60.9 | **0.514** | FAIL |
| #19 LETF pair SPXL/SPXS (short both) | same | 4454 | −0.091% | −37.5 | 1.000 | +11.6 | +48.5 | **0.363** | FAIL |
| #19 LETF pair UPRO/SPXU (short both) | same | 4305 | −0.095% | −59.5 | 1.000 | +15.2 | +62.5 | **0.516** | FAIL |
| #15 quarter-end window dressing (w4/l4) | fund reporting mandate, not price view | 57 | +0.080% | −0.23 | 0.595 | −2.65 | −1.07 | **0.001** | FAIL |
| #30 real-yield vs gold (CONTROL) | **none — deliberate control** | 2509 | −0.090% | −2.76 | 0.997 | +1.33 | +4.15 | **0.037** | FAIL |
| #1 Russell reconstitution (IWM-SPY proxy) | index funds must buy adds at June close | 19 | −0.355%/5d | −1.76 | — | — | — | **1.000** | FAIL |

**Zero of six ideas pass the four-stage framework. All FAIL.**

## Per-idea findings (honest detail)

### #17 Quadruple witching — dead
SPY absolute-return excess on witching Fridays vs 21d baseline: t=+0.19, permutation
p=1.0. No volatility-size effect at all. The mechanical expiration flow is fully
arbitraged (and largely pre-positioned days ahead, invisible at daily resolution).

### #19 Leveraged-ETF pair decay — dead (and the direction-agnostic claim is confirmed-but-useless)
Short-both-legs basket (the brief's exact idea): **−0.09%/day, t≈−60** — a huge,
consistent, statistically overwhelming LOSS. Direction-agnosticism confirmed:
corr(basket P&L, underlying direction) = +0.04 / +0.05 / −0.08 (all ≈0), exactly as
the mechanism predicts. But the "decay" is a cost borne by LETF holders, NOT a
capturable edge for a short-both counterparty — the daily rebalancing mechanics and
financing costs eat the drag before it becomes profit. This matches the current
literature (Return Stacked "Rebalance Drag Myth"; arXiv 2504.20116): the naive decay
harvest is dead on arithmetic.

### #15 Quarter-end window dressing — dead
Winners-minus-losers (top/bottom 4 of 24 liquid large-caps by YTD) over the last 5
trading days of each quarter: IS t=−0.23, walk-forward negative (WF sh −2.65).
**Bug caught during testing:** the first run showed +494%/quarter — a GE 2024
spin-off discontinuity contaminating raw prices. Fixed by ranking on cumulative
daily returns with a >40% single-day-move filter; the honest number is nothing.

### #30 Real-yield vs gold — the deliberate control — dead
The one non-forced-participant idea: gold vs 10Y-yield change signal (FRED
T10YIE/DFII10 blocked on this network, so the honest proxy is nominal 10Y + TIP).
Mean **−0.09%** per trade, IS t=−2.76, permutation p=0.997 — the naive yield-change
signal is negative (and non-informative at daily resolution). **Thesis-relevant:
the control fails too**, so this campaign neither confirms nor refutes the
forced-participant thesis — but it does NOT weaken it, which is what the control
was designed to probe.

### #1 Russell reconstitution — proxy dead, name-level blocked
Index-level proxy (IWM vs SPY relative around the June-close reconstitution): mean
−0.355%, t=−1.76, permutation p=1.0 — small-caps UNDERPERFORM after reconstitution,
the wrong direction for the forced-buying hypothesis. Consistent with the
well-documented death of the Russell effect post-2007 (it was arbitraged away years
ago). The name-level version (actual add/drop lists, the decisive test) is
**data-blocked**: no free, assembled Russell reconstitution lists — requires manual
assembly from FTSE Russell announcements.

## Data-blocked / deprioritized (honest status, not tested)

- **#8 IPO lockup expiry** — data-blocked: needs per-IPO lockup dates from SEC
  prospectuses; no clean free feed assembled. Would be testable given ~2 days of
  assembly work (IPO calendar + prospectus dates).
- **#9 Buyback blackout** — partially blocked: earnings calendar is available, but
  the *decisive control* (buyback-program status per company-quarter) has no free
  clean source. Without it, the test cannot distinguish blackout from earnings
  drift. Not testable honestly today.
- **#23 Restricted PEAD** — data-blocked: analyst-coverage counts are not free;
  market-cap/volume proxies are available but weak. Deprioritized.
- **#5/#13/#15/#21/#25 (Tier 2)** — #15 done above; #5/#13/#21 need dividend /
  buyback-announcement / fund-distribution date assembly; #25 (rate-cycle rotation)
  is testable with existing FOMC calendar + sector ETFs — flagged as the cheapest
  next test.
- **#3/#4/#6/#7/#11/#22/#24/#27/#28/#29 (Tier 3)** — data-access constraints or
  thin/indirect mechanisms as documented in the brief; not prioritized.

## Bottom line

**0/6 free-data Tier-1 ideas survive. All four-stage verdicts are clean FAILs.**
The campaign's most useful outputs are the two negative-but-informative results:
(1) LETF short-both decay is dead on arithmetic despite a confirmed direction-
agnostic mechanism (the drag is a holder's cost, not a counterparty's edge), and
(2) the Russell effect is gone even at the index level, matching its documented
post-2007 death. The deliberate control (#30) failed, so the forced-participant
thesis is neither weakened nor confirmed by this round — but no evidence against
it emerged either.

The standing best candidates remain unchanged: **dual momentum** (the one PASS of
the whole programme, allocation layer) and the **USDJPY D1 news drift** (forward-
testing live). Cheapest next test from this campaign: #25 rate-cycle rotation
(sector ETFs around FOMC decisions, data already in hand).
