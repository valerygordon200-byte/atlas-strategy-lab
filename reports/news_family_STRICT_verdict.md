# News drift family — STRICT verdict (final)

Date: 2026-08-10 · Script: `scripts/news_family_strict.py` · Outputs: `reports/news_family_strict.csv` / `.md`

## What was tested

The full news under-reaction family, through the pre-registered six-gate strict battery
(identical to `fx_strict_battery.py`):

- **D1 next-day drift** (2015/2016→2026, 2,856 events): all 5 pairs + basket; IS ≤ 2021-12.
- **Intraday H1 drift** (2023-10→2026-08, ~809 events): USDJPY at horizons 1/2/4/8/12/24h,
  basket-High at the same horizons; IS ≤ 2025-06, monthly walk-forward.
- All entries: US releases, High/Medium impact, expanding-window surprise |z| ≥ 0.5,
  direction = sign of z (USDJPY positive, others flipped), 1.0-pip round-trip cost.

Six gates: (A) IS |t|>2 · (B) IS 1000-perm p<0.01 · (C) holdout NW-t>2 & perm p<0.05 ·
(D) walk-forward mean>0 & wf-perm p<0.05 · (E) 5000-bootstrap P(mean≤0)<0.05 · (F) outlier-trimmed WF>0.

## Integrity fix (important)

The first run of this battery had a **silently broken walk-forward permutation** (`wf_perm`
passed all-zero dates into the null, so the null walk-forward was always empty and `p_wf`
printed the floor 0.001 for every variant). It was fixed to draw null returns from the pooled
pair-return distribution at the real event dates, through the same walk-forward machinery.
The earlier `fx_strict_battery.py` permutations were audited and are correct — the
historical "4/6 gates" USDJPY claim rests on sound tests.

## Result: 0 / 24 variants pass all six gates

| Group | Verdict |
|---|---|
| Intraday (USDJPY, all horizons; basket-High, all horizons) | **Dead.** In-sample significance (h12h t=2.99, p=0.002) does not survive holdout — every intraday holdout mean is ≤ 0 with negative t. Classic overfit signature. The lighter family screen's "13/84 pass" was a mirage. |
| D1 next-day, AUDUSD / USDCAD / GBPUSD / EURUSD / basket | **Dead.** Holdout positive (t 1.9–3.4) but walk-forward permutation fails (p_wf 0.07–0.53) and bootstrap P(≤0) is 0.04–0.36. The holdout numbers are within the null. |
| **D1 next-day USDJPY** | **4/6 gates — the only living candidate.** Fails ONLY the two in-sample gates (IS t=1.14, p_is=0.117) because the effect genuinely did not exist 2016–2021. Passes all four out-of-sample gates: holdout t=+3.78 (p=0.001), walk-forward p_wf=0.004, bootstrap P(≤0)=0.002, outlier-trimmed WF>0. |

## Why USDJPY D1 is "probation", not "edge"

The four passing gates are exactly the ones that matter for a *recent-regime* phenomenon:
blind holdout, walk-forward with re-estimation, bootstrap, robustness to outlier years. The
two failing gates say the effect is **not timeless** — it emerged in 2022 and has held every
year since (5/5 holdout years), consistent with the earlier campaign finding.

Prior work already cleared the historical contamination risks: vintage audit 28/28 as-published
prints (NFP −701K/−20.5M, CPI +8.6%), expanding-window z (no lookahead). The remaining
evidence gap is *forward* time: does the 2022+ drift persist in live, live-captured data?
That is exactly what the running `NewsDriftForward` task measures (daily 23:00, ledger in
`market-data/news_drift/forward_ledger.csv`).

## Bottom line

- **Nothing in the news family is tradeable today.** 0/24 strict passes.
- The intraday drift is dead — in-sample strength was overfitting.
- USDJPY D1 next-day drift remains the single best candidate in the whole programme
  (4/6 gates, vintage-clean, all OOS gates passing) and is being forward-tested live.
  It needs ~30–60 more clean live events (a few months) to confirm or kill.
