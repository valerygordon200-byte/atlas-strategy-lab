# News under-reaction — extension campaign verdict

Date: 2026-08-10. Script: scripts/news_ext_campaign.py (results CSV: news_ext_campaign.csv).

## What was tested

The informed under-reaction family was extended beyond the one survivor
(USD releases -> USDJPY, D1 next-day, 4/6 strict gates) to 10 new units, using
the IDENTICAL per-title expanding z machinery and the same IS/OOS split
(IS <= 2021-12-31, OOS >= 2022-01-01):

| Unit | n (OOS) | IS t | OOS t | OOS win | Verdict |
|---|---|---|---|---|---|
| EUR events -> EURUSD | 224 | +0.26 | +0.08 | 48.2% | SCREEN-KILL |
| GBP events -> GBPUSD | 576 | +0.10 | +1.13 | 51.9% | SCREEN-KILL |
| JPY events -> USDJPY | 373 | −1.76 | −1.27 | 45.6% | SCREEN-KILL |
| AUD events -> AUDUSD | 175 | +1.39 | +0.87 | 56.0% | FULL BATTERY FAIL (6/6 gates) |
| CAD events -> USDCAD | 223 | −0.04 | +1.05 | 53.8% | FULL BATTERY FAIL (6/6 gates) |
| CHF events -> USDCHF | 125 | −0.82 | −0.38 | 48.0% | SCREEN-KILL |
| NZD events -> NZDUSD | 49 | +1.08 | +0.67 | 51.0% | SCREEN-KILL (thin n) |
| USD events -> Gold | 1370 | −2.83 | −0.95 | 46.7% | SCREEN-KILL |
| USD events -> Silver | 1370 | −2.32 | −0.06 | 47.7% | SCREEN-KILL |
| USD events -> Nat Gas | 1370 | −3.01 | −0.47 | 49.9% | SCREEN-KILL |

Screen rule: full battery only if OOS t > 1.8 OR (OOS mean > 2x cost AND win > 53%).
AUD and CAD passed the screen; both then failed all six strict gates
(in-sample perm p=0.04/0.39, holdout NW t=0.93/0.99, walk-forward p=0.23/0.49,
bootstrap P(<=0)=0.33/0.47).

## Interpretation

The under-reaction effect, to the extent it exists, is UNIQUE to:
- the release currency being USD, and
- the target being USDJPY (the most liquid dollar pair, largest carry asymmetry).

It does NOT generalize to:
- other currencies' releases on their own pairs (EUR->EURUSD, GBP->GBPUSD, ...),
- or dollar-priced commodities (gold, silver, natural gas) reacting to US macro.

Note on the metals: the hypothesis direction (USD strength -> gold down, conv=-1)
LOST in-sample (IS t=-2.83), i.e., gold did not fall on USD-positive surprises in
2016-2021. Flipping the sign post-hoc would only have produced OOS t≈+0.95 —
still far below significance. Neither direction survives; do not chase it.

## Conclusion

The USDJPY D1 news drift remains the single live candidate in the informed
under-reaction family. This campaign's negative result is itself informative:
it raises the prior that the USDJPY effect is pair-specific (a JPY-complex
liquidity/flow story in the 2022+ regime), not a general "markets under-react to
macro" law. The live forward-test (NewsDriftForward ledger) continues to decide
the USDJPY question.
