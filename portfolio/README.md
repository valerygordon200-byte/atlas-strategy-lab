# dourmouse UI portfolio — two visual variants (debate in progress)

Source of truth for the mockups: `ui/DOURMOUSE_DESKTOP_MOCKUPS.html` in the
dourmouse repo (dark HUD language per DESKTOP_DESIGN_PORTFOLIO.md §13).

| File | Variant | Notes |
|---|---|---|
| `dourmouse-ui-portfolio.pdf` (444 KB) | **Standard dark HUD** | The shipped identity: `--bg #07090d`, cyan/amber/gold, bracket chrome, mono labels. 10 pages. |
| `dourmouse-ui-portfolio-pastel.pdf` (1.9 MB) | **Pastel** | Re-render of the same 10 pages in a pastel palette. Source HTML is NOT in the repo yet (exported standalone). |

## Open question (human request)

**Which one do we use as the desktop UI's palette?**

Status: relay debate opened with desktop (id ~1147). See
`reports/MODEL_BENCHMARK.md`-adjacent coordination on the feed / this file is
updated when a verdict lands.

Key technical fact for the decision: the app palette is CSS custom-property
driven (`--bg/--fg/--cyan/--amber/--gold/--red/--panel` + `-rgb` variants in
`ui/index.html`), so a pastel theme is a token-set swap, not a rewrite. The
question is which set ships as **default** (and whether a toggle ships).
