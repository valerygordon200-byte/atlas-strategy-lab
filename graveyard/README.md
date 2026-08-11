# GRAVEYARD — the kill-history store

The spine of the product's honesty story (see reports/PRODUCT_DECISION.md,
point 2). Every strategy this project has tested and killed lives here, with
an honest post-mortem. **Nobody ships their dead — that is the point.**

## Structure

```
graveyard/
  build_index.py   # regenerates data/*.json + index.json from the entries in this script
  data/{id}.json   # one entry per dead strategy
  index.json       # the searchable index (families, status counts, summaries)
  README.md        # this file
```

## Entry schema (v1)

| field | meaning |
|---|---|
| id | stable slug, e.g. `seasonal-lean-hogs-aug` |
| name | human name of the strategy |
| family | mechanism family (calendar-forced hedging, momentum, breakout, …) |
| mechanism_claim | the hypothesis, in plain terms |
| forced_participant | the named forced participant — or explicit "none found" (the absence IS a kill reason) |
| data | instruments, frequency, range, source |
| tests_run | the actual tests: selection, holdout, roll checks, permutation, walk-forward |
| kill_criterion | the specific test that killed it |
| post_mortem | the honest lesson — including when the mechanism was real but untradeable |
| killed_date | ISO date of the kill |
| source | the report/script the entry is based on |
| headline | one-line verified numbers, e.g. `continuous -13.62% t-7.53 -> real -0.03% t-0.02` |
| status | `dead` (only status today; the store exists to keep it that way) |

## Rules for adding an entry

1. Only strategies actually tested in this project — never rumors or vendor claims.
2. Every number must come from a cited report/script. No estimates.
3. The post-mortem must state what actually killed it, including when the
   mechanism was real but the tradeability wasn't (COT, spreads).
4. Re-run `python graveyard/build_index.py` after adding; commit both the new
   entry and the regenerated index.

## Status: LIVE SURVIVORS are NOT graveyard entries

The graveyard only holds the dead. The live forward ledger (USDJPY news drift,
OOS t 3.711; Dual Momentum, holdout +2.12%/mo t 4.49) is the proof-of-life and
lives in the decision-card pipeline, not here. If a survivor dies later, it
gets a graveyard entry with its full record.
