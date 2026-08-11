# Track A — Structural Spreads: Verdict Report
Date: 2026-08-11 · Campaign: Multi-Track Edge Search

## 5.0 Timing test (mandatory)
Representative candidate (crush) through the **full Stage 0–4 pipeline, 1000 permutations
at both MC stages**: **9.9 s total** (stage 1: 0.0 s, stage 2: 6.4 s, stage 3: 0.1 s,
stage 4: 3.3 s). All four candidates run at full rigor with enormous time-budget headroom.
The 2.5–3 h allocation is not binding for Track A; ~40 s total for all four.

## 5.1 Results — all four spreads, full pipeline

| Spread | Coint IS (ADF) | Coint OOS (ADF) | Gross %/yr | Gross t | Gross Sharpe | Net %/yr OOS | Net t OOS | Stage 2 p | Stage 3 WF Sharpe/t | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| Crush (ZS vs 0.733ZM+0.183ZL) | −5.71 ✅ | −4.34 ✅ | +2.1% | 1.39 | 0.41 | −10.2% | −6.2 | 1.00 | −0.83 / −3.2 | FAIL |
| Hog-corn (HE vs ZC) | −3.85 ✅ | −5.11 ✅ | +1.4% | 0.31 | 0.09 | −10.8% | −2.4 | 1.00 | −0.88 / −3.4 | FAIL |
| Live/Feeder cattle (LE vs GF) | −4.34 ✅ | −3.68 ✅ | +2.0% | 1.20 | 0.35 | −11.0% | −6.3 | 1.00 | −1.67 / −6.4 | FAIL |
| 3:2:1 Crack (CL vs 2/3HO+1/3RB) | −4.34 ✅ | −4.84 ✅ | +2.6% | 0.62 | 0.18 | −8.6% | −2.0 | 1.00 | −0.48 / −1.8 | FAIL |

Stage 1 bar: mean > 2× round-trip cost, Sharpe ≥ 1.0, win ≥ 60%, t ≥ 2.5.
- Every spread fails Stage 1 **even before costs** (gross Sharpe 0.09–0.41, gross t 0.31–1.39 —
  not statistically distinguishable from zero). The pipeline never proceeds to Stage 2 as a pass;
  the permutation p ≈ 1.0 reflects a *negative* real result (the tests guard fake positives —
  there is nothing positive here to protect, and the negative result is robust).
- Win rates gross: 48–56%. Trades: ~18–21/yr per spread.

## 5.2 Roll-resistance check
Heuristic (no per-contract data on the drive; noted as a limitation): candidate roll-jump days
(|leg ret| > 5× its 90-day mean, unmirrored by other legs) numbered 52–146 per sample.
Excluding them changes the OOS edge by <1%/yr in all four (e.g. crush −22.2% → −22.8% net before
the cost-convention fix; lfcattle −23.6% → −22.9%). **The (tiny) gross edge is not concentrated
on roll days** — the mean-reversion is not a continuous-series construction artifact. The
cointegration itself survives out-of-sample for all four, which is the stronger test.

## 5.3 Mechanism audit
- Crush: crusher margin — real, stable cointegration ✅ but reversion magnitude far too small.
- Hog-corn: feed-cost margin — cointegrated but the 90-day z excursions are *trend* moves
  (fwd-20d return after z>2 is +2.1%, i.e. anti-reversion at this horizon); no tradeable signal.
- Live/Feeder: fattening margin — strongest reversion of the four (z<−2 followed by +3.9–7.3%
  over 20d in diagnostics) yet still sub-cost and gross-insignificant.
- Crack: refiner margin — weakest; also corr(P&L, crude) = 0.30, flagged: not fully
  direction-agnostic.

## 9.3 Failure classification
- **Classification: (b)-leaning — genuine absence of a tradeable signal.** Not an
  implementation/data bug: cointegration is stable OOS, P&L is direction-agnostic (except crack),
  and the edge is roll-clean. The effect is real in expectation but ~1/10th of round-trip cost
  and not statistically significant even gross. No salvage is honest: re-parameterising entry
  thresholds or holding periods cannot close a 10× cost gap, and per the standing instruction
  no parameter tuning was performed to manufacture a pass.
- The one structural escape (trading futures spreads directly instead of retail CFDs) is outside
  this campaign's account reality ($150, T212 CFDs) and the gross edge is insignificant anyway.

## Honest conclusion
**All four structural spreads are dead for a $150 retail CFD account.** The economic links are
genuinely cointegrated (a useful finding in itself — the relationships exist), but the reversion
payoff is one to two orders of magnitude below costs. The mechanism family is not viable at
retail cost levels; it would only be worth revisiting with direct futures execution and even then
the gross t-stats (0.3–1.4) give no confidence of a real edge.
