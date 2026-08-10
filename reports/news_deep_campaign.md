# News under-reaction — deep campaign verdict

Date: 2026-08-10. Script: scripts/news_deep_campaign.py (CSV: news_deep_campaign.csv).

## A. EIA Natural Gas Stocks Change surprise -> NG price — DEAD

The archive carries 581 storage reports with numeric forecast+actual (2015-2026).
Clean single-title test: per-title z on the storage surprise, short NG on positive
surprise (more supply -> price down), 1-pip-equivalent cost (0.15% RT baseline).

- 200 triggers (105 IS / 95 OOS)
- IS t=+0.51, OOS t=+0.56, OOS win 49.5%, walk-forward p=0.37, bootstrap P(<=0)=0.38
- **Verdict: FAIL all gates.** The storage forced-flow mechanism produces no
  tradeable next-day drift on NG. (This isolates the single title that was pooled
  into the earlier US->NG unit, which also died.)

## B. USDJPY drift at longer holds — the effect is a 1-day phenomenon

Same universe/costs as the live strategy, holds extended to k=2/3/5 trading days,
overnight financing charged per night (long 0.0082%/night, short 0.0029%/night,
weekend nights x3 — operator's broker rates).

| Hold | n | IS t | OOS t | OOS NW | p_wf | boot P(<=0) | wf mean | Verdict |
|---|---|---|---|---|---|---|---|---|
| k=1 (baseline) | 2856 | +1.14 | +3.78 | 3.03 | 0.028 | 0.0014 | +0.00040 | 4/6 (known) |
| k=2 | 2855 | **−1.74** | +2.41 | 1.96 | 0.886 | 0.447 | +0.00001 | FAIL |
| k=3 | 2855 | −2.73 | +1.89 | 1.57 | 0.992 | 0.638 | **−0.00008** | FAIL |
| k=5 | 2852 | −2.68 | +2.38 | 1.99 | 0.833 | 0.395 | +0.00003 | FAIL |

The k=1 row reproduces the known result exactly (machinery sanity check).

Interpretation: the drift is concentrated in the FIRST day. By day 2-3 it is gone
or reversing (in-sample turns negative at k=2+, consistent with a day-2
overhang/mean-reversion), and every longer hold fails the walk-forward
permutation and bootstrap. Holding longer adds no edge — it only adds financing.

## Conclusion

- Storage surprises (nat gas): no edge.
- Longer USDJPY holds: no edge — the under-reaction is genuinely a 1-day effect,
  which also narrows what the live forward-test must confirm (the day-1 drift).
- The live strategy remains: USD High/Medium |z|>=0.5 -> USDJPY, 1-day hold.
