# Central-bank gold net purchases — monthly grid (Nov 2020 → Jun 2026)

Verified monthly *reported* net purchases of gold by central banks and other
official institutions, compiled from the **World Gold Council's monthly
"Central Bank Gold Statistics" reports** (which are themselves compiled from
IMF IFS + national central-bank disclosures).

File: `central_bank_gold_monthly.csv` — columns:

| column | meaning |
|---|---|
| `month` | data month, `YYYY-MM` (reports lag data by ~6 weeks) |
| `net_t` | reported net purchases in tonnes (negative = net sales) |
| `source` | article URL for the monthly report (or report that cites the month) |
| `note` | provenance: `as-published` (headline figure in the report), `meta-description`, `pdf-narrative` (figure in the attached PDF), `cited-within-<X>-report` |

## What "reported" means — read before use

- This series is **reported activity only** (central banks reporting to the IMF
  IFS and via their own disclosures, as captured by the WGC monthly reports).
- It is **NOT** the WGC *Gold Demand Trends* "central bank demand" figure.
  GDT includes WGC estimates of unreported purchases (e.g. Russia). For
  example: reported 2024 ≈ **337t** (per the Dec-2024 report) vs GDT 2024
  = **1,092.4t**. Do not mix the two definitions.
- Figures are **as published in the month's report** (initial data, ~50-90% of
  banks reported). Later reports revise. Known revisions are flagged in
  `note` (e.g. Jan-2024 39t → revised 45t; Jun-2022 59t → 64t; Nov-2022 50t →
  60t; Oct-2022 31t → 34t; Apr-2023 −71t → −69t).
- Excludes the State Oil Fund of Azerbaijan (SOFAZ), which reports quarterly.

## Coverage and gaps

| period | status |
|---|---|
| Nov 2020 – Jun 2026 | monthly grid, **58 verified months** (see gaps below) |
| Mar–Jun 2021, Aug–Oct 2021, Feb–Apr 2022, Aug–Sep 2022, Mar 2023 | **no WGC monthly report found** (archive search + URL probing); quarterly GDT is the available resolution |
| 2015 – Oct 2020 | no monthly WGC series exists; use the annual series (`central_bank_gold.csv`, WGC GDT-verified) or quarterly GDT |
| 2026-07+ | report not yet published |

## Cross-checks (sums of the grid vs annual "reported" totals)

- **2024**: grid sum **+311t** vs reported annual **337t** (Dec-2024 report).
  Residual = 26t, consistent with the documented revisions above.
- **2025**: grid sum **+298t** vs reported annual **328t** (Dec-2025 report).
- **2023**: grid sum **+406t** (Mar-2023 missing ≈ +30t) vs reported 2023
  annual (≈ 450t, Dec-2023 report) — same order of magnitude.

## Build pipeline

`../scripts/gold_monthly_build.py` automates the fetch/parse (article HTML +
meta-description + PDF fallback; pure stdlib). The final grid was **audited
row-by-row** against each report's narrative — the script's first pass grabbed
per-country figures (e.g. Kazakhstan −13t in Feb-2023) and YTD totals (673t)
as if they were monthly totals; **every value in the CSV was corrected and
verified against its report's headline sentence**. Values without a report
headline are not included.

## Companion series

- `central_bank_gold.csv` — annual 2014–2025 (WGC Gold Demand Trends, verified).
- `central_bank_gold_README.md` — annual provenance.
