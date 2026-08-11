# Central-Bank Gold Net Purchases — provenance

Task T1 (owner laptop-dourmouse) · milestone 1 · 2026-08-11

**What this is:** the bookshelf's GOLD factor — central-bank net gold purchases —
currently marked as *data MISSING / belief*. This file starts replacing that
belief with sourced numbers.

## File

`data/central_bank_gold.csv` — columns:
- `granularity`: annual | quarterly | monthly
- `date`: period end (annual = 12-31 of year; monthly = month end)
- `total_net_purchases_tonnes`: global central-bank + other institutions NET
  purchases (purchases minus sales), tonnes
- per-country columns (`poland_tonnes`, `china_tonnes`, ...) where the source
  breaks out the month
- `source`: exact source series + access date

## Sources (verified this milestone)

| Rows | Source | Verified |
|---|---|---|
| annual 2014-2021 | World Gold Council Gold Demand Trends data, as tabulated in Visual Capitalist "Charted: A Decade of Central Bank Gold Purchases" (Oct 23 2025) | fetched 2026-08-11 |
| annual 2022-2023 | WGC GDT FY2023 central-banks page (1,081.9t / 1,037.4t) | fetched 2026-08-11 |
| annual 2024-2025 | WGC GDT FY2025 central-banks page (1,092.4t / 863.3t; 2025 Q4 230t) | fetched 2026-08-11 |
| monthly 2026-04, 2026-05 | WGC Central Bank Gold Statistics (gold-focus posts, Jun 12 + Jul 2 2026) | fetched 2026-08-11 |
| monthly 2025-03 | WGC Central Bank Gold Statistics Mar 2025 (17t) | secondary (Scribd) — treat as unverified |

## Gaps (honest)

1. **Monthly granularity 2015-2024 is NOT yet in this file.** The authoritative
   monthly series lives in WGC's monthly Central Bank Gold Statistics reports
   (2015-2021 in older report PDFs) and GDT quarterly tables. Annual-only for
   those years is a defensible first cut (the factor moves on annual/quarterly
   scales), but the task asked for monthly — this is the open work.
2. Monthly 2023, 2024, 2025 partial: only Q4-2023 (229t) and Mar-2025 (17t)
   sourced so far; H1-2025 headline buyers (Poland 67.2t, Azerbaijan 34.5t,
   Kazakhstan 22.1t, China 19t, Türkiye 17.2t) available but not yet a full
   monthly grid.
3. 2026 monthly: Mar 2026 was a net-SALES month (magnitude not yet sourced);
   Apr +17t, May +41t done; Jun 2026 onward pending the July/August reports.
4. Discrepancy note: WGC reports both gross buying (2022: 1,136t) and NET
   (2022: 1,081.9t) — this file uses NET consistently (matches the GDT table
   series and the bookshelf factor semantics "net purchases").

## Next steps (milestone 2)

- Extract the full monthly 2015-2024 grid from WGC monthly Central Bank Gold
  Statistics report PDFs + GDT quarterly XLSX tables (the FY2025 GDT page
  links the quarterly tables workbook). Target: `data/central_bank_gold.csv`
  complete at monthly granularity, 2015-01 through present.
- Add monthly per-country columns for the top ~8 accumulators.
- Cross-check with IMF IFS reserve-holding changes for the top reporters.

## Caveat

These are REPORTED figures (IMF IFS + national disclosures + WGC estimates);
central-bank data is published with lags and revisions. The series is
point-in-time as published; a revised series (e.g. WGC's later re-statements)
may differ slightly. For the bookshelf: treat as a *sourced* belief now, not
a confirmed measurement.
