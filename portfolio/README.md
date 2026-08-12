# dourmouse UI portfolio — two visual variants (debate in progress)

Source of truth for the mockups: `ui/DOURMOUSE_DESKTOP_MOCKUPS.html` in the
dourmouse repo (dark HUD language per DESKTOP_DESIGN_PORTFOLIO.md §13).

| File | Variant | Notes |
|---|---|---|
| `dourmouse-ui-portfolio.pdf` (444 KB) | **Standard dark HUD** | The shipped identity: `--bg #07090d`, cyan/amber/gold, bracket chrome, mono labels. 10 pages. |
| `dourmouse-ui-portfolio-pastel.pdf` (1.9 MB) | **Pastel** | Re-render of the same 10 pages in a pastel palette. Source HTML is NOT in the repo yet (exported standalone). |

## Verdict (2026-08-12, laptop + desktop agreement on the relay)

**Dark stays the default; pastel ships as a token-block theme toggle.**

Two conditions accepted and on record:
1. **One palette in every public artifact** — screenshots, PDFs, landing page,
   storefront all show dark until the 14-day-gate evidence says otherwise.
2. **Pastel ships as a BETA theme only** — it needs a WCAG AA contrast pass
   (4.5:1 body text on light backgrounds) before it leaves beta.

14-day gate: track which palette the pilot user actually keeps (evidence, not
preference) — logged daily in `reports/RELIABILITY_LOG.md`.

**Why this wins:** the app palette is CSS custom-property driven
(`--bg/--fg/--cyan/--amber/--gold/--red/--panel` + `-rgb` variants in
`ui/index.html`), so pastel is a token-set swap, not a rewrite — the decision
is about the default, and identity continuity + zero-rework win until
real usage evidence says otherwise.

Open laptop follow-up: pastel token block + contrast pass + beta label in
`ui/index.html` (queued with the UI work).
