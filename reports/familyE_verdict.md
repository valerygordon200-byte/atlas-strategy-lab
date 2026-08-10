# Family E — dollar-basket under-reaction — VERDICT: not supported on H1 data

Date: 2026-08-10 · Script: `scripts/familyE_basket_test.py` · Outputs: `reports/familyE_basket_strict.csv/.md`
Protocol: Edge-Finding Master Plan §1E + §3 (four-stage framework).

## The premise, tested honestly

**Forced participant (named before code):** after a macro print, stop-losses,
margin calls and hedger exits force counterparties to transact at the print
regardless of price — they cannot wait for a better price — while the full
information content of the surprise propagates slowly across dollar
instruments. If the market under-reacts, forced transactors supply the other
side of the drift. This test exists to confirm or kill that story.

**Construction:** surprise z = (actual − consensus)/σ(trailing, per title) using
the REAL consensus column of the live-captured Forex Factory archive (not a
statistical proxy); 7-pair vol-normalized dollar basket (EURUSD GBPUSD AUDUSD
NZDUSD +1, USDJPY USDCAD USDCHF −1); r30~z regression fitted IN-SAMPLE only
and locked; under-reaction gap filter (|r30| < |predicted|, same sign,
|gap| > 0.5σ); entry |z| > 0.5, Tier 1/2, no second Tier1/2 USD release in the
48h window; EURUSD execution; time exits 4h/8h/24h/48h. H1 data 2023-10 →
2026-08. IS ≤ 2025-06-30. Costs 1pip + 0.5pip slippage ≈ 0.014% round trip.

## Result: the signal cannot be built — Stage 1 premise failure

### 1. The surprise does not predict the 30-min basket move

Full deduplicated in-sample regression (n=717 events with z):

| Statistic | Value |
|---|---|
| Slope b1 | −0.0096 |
| t-stat | **−0.36** |
| R² | **0.0002** |

The surprise z-score explains 0.02% of the 30-minute basket move. The
under-reaction gap filter therefore produces **zero trades** at every horizon.
There is nothing to under-react to: the surprise does not move the basket in a
predictable way at H1 frequency in this sample.

### 2. The apparent CPI "effect" was a duplicate-release artifact (data-integrity catch)

Before deduplication, per-title CPI regressions looked significant
(Inflation titles: n=107, t=−3.03, R²=8%). **This was an artifact:** the CPI
family is ~5 sub-titles (Inflation MoM/YoY, Core MoM/YoY, index level) firing at
the SAME timestamp — the same release counted 4–5×. Deduplicated by timestamp,
the honest CPI sample is **32 unique releases** in the whole H1 window
(monthly cadence × 2.9y) — far too few for any of the four stages to mean
anything, and the leftover per-release signal is statistically unevaluable.

**The plan's data-integrity discipline caught an inflation artifact before it
became another "confirmed" finding.** Exactly the failure mode §2 exists for.

### 3. The momentum control arm — the plan's decisive test — FAILS

| Variant | IS t | OOS t | p_is | p_wf | boot | verdict |
|---|---|---|---|---|---|---|
| h4h momentum | +2.36 | +0.27 | 0.016 | 0.567 | 0.088 | FAIL |
| h8h momentum | +0.64 | −0.52 | 0.272 | 0.673 | 0.583 | FAIL |
| h24h momentum | +1.70 | +0.02 | 0.049 | 0.552 | 0.197 | FAIL |
| h48h momentum | +1.23 | −1.02 | 0.108 | 0.453 | 0.421 | FAIL |

In-sample strength (t=2.36) collapses to nothing out-of-sample (t=0.27) — the
graveyard signature for post-news momentum. The control arm did its job: the
little intraday signal that exists after releases is ordinary momentum, which
is already in the graveyard. (No signal-arm trades existed to compare, so the
discriminator is moot — but the control failing independently is consistent.)

## What this means

- **Family E as specified (intraday under-reaction on the dollar basket) is NOT
  supported on the available H1 window.** The central premise — that real
  consensus surprises predict short-horizon dollar moves — fails at Stage 1
  (R²≈0.0002). No further stages were reachable because the signal produces no
  trades.
- The earlier "CPI moves the dollar" hint was a counting artifact, now
  documented so it does not resurface.
- The surviving thread in this family remains the **D1 next-day USDJPY drift**
  (4/6 strict gates from prior work, vintage-audited clean, a 2022+ regime
  phenomenon) — a *daily* horizon, being forward-tested live by the
  `NewsDriftForward` task. That is a different horizon and a different
  construction; it is not affected by this H1 result.
- Honest caveat: the H1 sample (2.9y, 32 unique CPI releases) is thin for this
  family even if the premise had held. A proper intraday under-reaction test
  needs either more H1 history (2–3 more years → ~100 CPI releases) or
  minute-level data for exact T+30min fills. Neither is available today.

## Next steps (if this family is revisited)

1. Do not re-test intraday under-reaction until ≥3 more years of H1 history
   accumulate (or minute data is acquired) — the sample is the binding
   constraint, not the method.
2. The D1 USDJPY drift forward-test continues on its own clock; it is the only
   live candidate in the family.
3. Per plan §6, move to the next mechanism family (B: structurally forced fund
   flows — index reconstitution / LETF rebalancing / month-end flows), which is
   untested and has free yfinance data.
