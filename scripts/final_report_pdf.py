#!/usr/bin/env python3
"""final_report_pdf.py — Part 9.4 final deliverable: full campaign PDF report."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)
import json
from pathlib import Path

BASE = Path("E:/forex-data")
OUT = BASE / "reports/EDGE_CAMPAIGN_FINAL_2026-08-11.pdf"

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=styles["Heading1"], fontSize=16, spaceAfter=10)
H2 = ParagraphStyle("H2x", parent=styles["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("Bodyx", parent=styles["BodyText"], fontSize=9.5, leading=13)
SMALL = ParagraphStyle("Smallx", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#333333"))


def tbl(data, widths=None):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
    ]))
    return t


story = []

# ============ TITLE ============
story.append(Paragraph("ATLAS EDGE-SEARCH CAMPAIGN — FINAL REPORT", H1))
story.append(Paragraph("Pen-drive migration verification + multi-track edge search · 2026-08-11 · "
                       "E:\\forex-data (drive) · Account: $150 T212 CFD", BODY))
story.append(Spacer(1, 6))

# ============ EXEC SUMMARY ============
story.append(Paragraph("Executive summary", H2))
story.append(Paragraph(
    "<b>Total candidates tested this session: 4 spreads (full four-stage pipeline, 1000-perm MC) "
    "+ 2 validation modules (vol forecast). Tracks B (literature) and C (platforms) yielded "
    "<b>zero</b> testable candidates after the eligibility filter — an honest, expected outcome "
    "given the project's graveyard and the drive's data constraints.</b> "
    "All four structural spreads failed: the cointegration is real and stable out-of-sample for "
    "every spread, but the reversion payoff is 6–12× below retail CFD costs and not significant "
    "even gross (t 0.3–1.4). The volatility module <b>validates</b> (monotonic calibration OOS, "
    "permutation p&lt;0.001) but <b>does not help</b> the one surviving strategy (the USDJPY news "
    "drift) — its edge is concentrated in high-vol states, so inverse-vol sizing hurts "
    "(Sharpe 1.73 → 1.56). Salvage attempts: 0 attempted — classified as structural, see "
    "per-candidate records.", BODY))
story.append(Spacer(1, 4))

# ============ TIME BUDGET ============
story.append(Paragraph("Time budget — actual vs planned", H2))
story.append(tbl([
    ["Phase", "Planned", "Actual (approx.)", "Note"],
    ["Part 1 migration verification", "15–30 min", "~45 min", "Engine missing from drive; archive workaround (drive writes ~50 KB/s)"],
    ["Part 5.0 timing test + Track A", "2.5–3 h", "~25 min", "Crush timing test: 9.9 s/candidate → all 4 spread at full rigor (~45 s total)"],
    ["Tracks B + C (search)", "within budget", "~30 min", "Zero eligible candidates, documented"],
    ["Part 9.2 vol module", "within budget", "~25 min", "Validates; does not help the drift"],
    ["Part 9.4 PDF", "20–30 min", "~15 min", "This document"],
], widths=[5.2 * cm, 2.6 * cm, 2.6 * cm, 6.4 * cm]))

# ============ PART 1 ============
story.append(PageBreak())
story.append(Paragraph("Part 1 — Migration verification (all passed)", H2))
story.append(Paragraph(
    "<b>Structure:</b> all required trees present on E:\\forex-data except atlas-engine "
    "(found only on local disk). <b>Completeness:</b> events.parquet 84k+ rows 2015→present; "
    "strategies registry 26 = 26 JSONs; normalized store + manifest present. "
    "<b>Regressions (all three reproduce exactly):</b> "
    "① hog August roll-check — continuous −13.6% (t −7.5) vs real path −0.03% (t −0.02) ✅; "
    "② Dual Momentum — holdout +2.12%/mo, t 4.51, wf p 0.001, 6/6 gates ✅; "
    "③ USDJPY news drift — IS t 1.139, OOS t 3.775, boot P(≤0) 0.0014, 4/6 gates ✅. "
    "<b>Live:</b> forward ledger live (4 events, 3/4 hits); task scripts location-relative. "
    "<b>Issues found &amp; fixed:</b> atlas-engine absent → shipped as sha256-verified archive "
    "(atlas-engine.tar.gz, 1.8 MB, byte-identical both sides); partial copy renamed "
    "atlas-engine.partial (do not use). Drive write throughput measured ~50 KB/s — the reason "
    "for archive-instead-of-per-file migration. Stray cp/tar processes were holding the drive; "
    "killed. No data loss.", BODY))

# ============ PART 3 CONSTRAINTS ============
story.append(Paragraph("Part 3 — Account constraints as used", H2))
story.append(tbl([
    ["Constraint", "Value used", "Where applied"],
    ["Capital", "$150 total; free CFD margin not programmatically confirmable — flagged", "sizing discussion"],
    ["Leverage caps", "FX majors 30:1, commodities 10:1 (T212)", "margin capacity"],
    ["Spread", "0.30%/leg round trip (corn 0.27%, gasoline 0.46% measured earlier)", "Track A costs"],
    ["Financing", "0.01%/day/leg assumption (T212 publishes no historical swap tables) — flagged", "Track A costs"],
    ["Cross-currency fee", "0.5% on P&L for non-USD-base pairs — none of Track A legs affected (all USD-priced)", "n/a"],
], widths=[4.2 * cm, 7.2 * cm, 5.4 * cm]))

# ============ TRACK A ============
story.append(PageBreak())
story.append(Paragraph("Track A — Structural spreads: 4 candidates, full records", H2))
story.append(Paragraph(
    "Method: log-ratio spread, 90-day rolling z-score, enter |z|≥2, exit z=0 or 20-day stop, "
    "IS 2000-09→2014-12 / OOS 2015→2026-08. Engle-Granger cointegration (ADF, MacKinnon 5% "
    "crit −2.86) tested IS and re-tested OOS separately. Permutation blocks: 20-day joint "
    "block bootstrap (preserves cross-leg correlation). 1000 permutations at both MC stages "
    "(timing test: 9.9 s/candidate).", SMALL))
story.append(Spacer(1, 4))

tracka = json.load(open(BASE / "reports/spread_crush_results.json"))
rows = [["Spread", "Coint IS (ADF)", "Coint OOS (ADF)", "Gross %/yr", "Gross t", "Net %/yr OOS", "Net t OOS", "WF Sharpe/t", "Verdict"]]
data = {
    "crush": ("Soybean crush", -5.71, -4.34, 2.12, 1.39, -10.24, -6.23, "-0.83 / -3.2"),
    "hogcorn": ("Hog-corn", -3.85, -5.11, 1.36, 0.31, -10.83, -2.44, "-0.88 / -3.4"),
    "lfcattle": ("Live/Feeder cattle", -4.34, -3.68, 1.95, 1.20, -11.04, -6.29, "-1.67 / -6.4"),
    "crack": ("3:2:1 Crack", -4.34, -4.84, 2.60, 0.62, -8.62, -2.03, "-0.48 / -1.8"),
}
for k, (name, ai, ao, g, gt, n, nt, wf) in data.items():
    rows.append([name, f"{ai} ✅", f"{ao} ✅", f"+{g}%", gt, f"{n}%", nt, wf, "FAIL — Stage 1 gross"])
story.append(tbl(rows, widths=[2.9 * cm, 2.1 * cm, 2.1 * cm, 1.8 * cm, 1.3 * cm, 1.9 * cm, 1.5 * cm, 2.2 * cm, 3.0 * cm]))
story.append(Spacer(1, 6))

story.append(Paragraph("Per-candidate detail", H2))
for k, (name, ai, ao, g, gt, n, nt, wf) in data.items():
    j = json.load(open(BASE / f"reports/spread_{k}_results.json"))
    story.append(Paragraph(f"<b>{name}</b> — {j['mechanism']}", BODY))
    story.append(Paragraph(
        f"IS (2015-09→2014): mean {j['stage1']['mean']}%/yr, Sharpe {j['stage1']['sharpe']}, "
        f"win {j['stage1']['win']}%, t {j['stage1']['t']} — <b>fails Stage 1 even gross</b> "
        f"(gross OOS Sharpe 0.09–0.41, gross t 0.31–1.39, not significant). "
        f"Permutation p (S2) = {j['stage2_p']} (expected: real IS result is negative). "
        f"Walk-forward (S3): Sharpe {j['stage3']['sharpe']}, t {j['stage3']['t']}. "
        f"Roll probe: {j['roll_probe']['roll_days']} candidate roll days; excluding them changes "
        f"the edge by &lt;1%/yr — the reversion is <b>not</b> a continuous-series roll artifact. "
        f"Direction-agnostic corr: {j['corr_with_legs']} "
        f"({'FLAG crack CL 0.30' if k == 'crack' else 'clean'}). "
        f"<b>Kill criterion: mean net &lt; 2× round-trip cost and Stage-1 gross failure.</b> "
        f"Classification per 9.3: structural (b) — the edge is 6–12× below cost and gross "
        f"insignificant; no honest salvage exists (re-parameterising cannot close a 10× gap).", BODY))
    story.append(Spacer(1, 4))

# ============ TRACK B / C ============
story.append(PageBreak())
story.append(Paragraph("Track B — Literature search: zero eligible candidates", H2))
story.append(Paragraph(
    "Searched: SSRN, general web, CME publications. Queries: hedging pressure / normal "
    "backwardation; commodity index (Goldman) roll; first-notice-day/delivery effects; "
    "pre-hedging; news under-reaction in commodities. 10 papers extracted per 6.3 — every one "
    "either overlaps the graveyard (hedging pressure = COT positioning, already dead), "
    "requires per-contract / term-structure / intraday data not on the drive (roll "
    "front-running, basis reversal, overreaction), or is documented-decayed (Goldman roll "
    "order-flow costs down &gt;80% since 2010, Irwin-Sanders-Yan 2022). "
    "<b>No candidate promoted to testing. This is a legitimate, complete result.</b>", BODY))
story.append(Paragraph("Track C — Platform scan: zero eligible candidates", H2))
story.append(Paragraph(
    "myfxbook/verifiedinvesting skipped (black-box by definition). QuantConnect supplemental "
    "check surfaced no new visible-logic strategy distinct from already-tested families; "
    "prior campaign-30 already executed the QC-derived mechanism ideas (witching, LETF decay, "
    "window dressing, Russell reconstitution) — all failed the four-stage framework. "
    "TradingView/YouTube: no rule set demonstrable to code precision that wasn't a repackaged "
    "graveyard family. <b>Zero promoted.</b>", BODY))

# ============ VOL MODULE ============
story.append(PageBreak())
story.append(Paragraph("Part 9.2 — Volatility prediction module", H2))
story.append(Paragraph(
    "Composite HAR-RV forecast of next-day |USDJPY return| (rv1/rv5/rv22 + Bollinger-width "
    "percentile + |BTC|), IS fit 2016-21, OOS 2022-26 untouched. "
    "<b>Validates:</b> quintile calibration monotonic in-sample AND out-of-sample "
    "(Q5/Q1 = 1.77 / 1.86), Spearman 0.20 / 0.22, OOS R² 0.016 vs naive rv1 −0.81 and "
    "rv22 0.014; permutation p &lt; 0.001 on both rho and quintile-spread (1000 runs). "
    "<b>Does not help the drift:</b> the drift edge is strongest in the high-vol tercile "
    "(+0.160%/event, t 3.77 vs 0.33 mid), so inverse-vol sizing throws away the best trades: "
    "Sharpe 1.73 → 1.56, ann +19.1% → +15.9%. Correct use: risk management (caps, stops), "
    "never a directional signal; re-test per-strategy rather than assume.", BODY))

# ============ PORTFOLIO ============
story.append(Paragraph("Portfolio-level check (survivors at $150)", H2))
story.append(Paragraph(
    "Only one active candidate survives everything: the <b>USDJPY D1 news drift</b> "
    "(forward ledger live, 4 events; backtest OOS 1,201 events, flat Sharpe 1.73, ann +19% on "
    "event-return units). No cross-candidate correlation matrix is computable — no second "
    "survivor. Dual Momentum remains formally validated (holdout t 4.51, wf p 0.001) but is "
    "<b>retired by your decision</b> and excluded. "
    "Trade frequency: drift triggers ≈ 22/month (well above the 3/month target; the binding "
    "constraint is the $100 platform minimum order and margin — at 30:1, $150 supports "
    "≈ $4,500 notional, i.e. roughly 3–4 concurrent minimum-size positions, so the ~22 "
    "monthly triggers must be filtered, not all taken). Risk cap: min($5, 8.5% equity) per "
    "day shared across concurrent positions.", BODY))

# ============ FINAL VERDICT ============
story.append(Paragraph("Final verdict and ranked recommendations", H2))
story.append(tbl([
    ["Rank", "Candidate", "Status", "Recommendation / caveat"],
    ["1", "USDJPY news drift (D1, next-day continuation)", "Only survivor — forward ledger live (4 ev, 3/4 hits)", "Let the ledger run to its 30–60 event kill gate before committing capital. Entry at event-day close, exit next close, 1-pip cost model; weekend holds pay 3× financing. Size cap per event; do NOT vol-scale (edge is high-vol-state concentrated)."],
    ["2", "Volatility forecast (HAR-RV composite)", "Validated (p<0.001) but no strategy use found yet", "Use for risk management and as a candidate filter for future strategies; re-test vol-scaling per-strategy."],
    ["—", "All four structural spreads", "Dead at retail costs", "Mechanism real (cointegration stable OOS) but edge 6–12× below costs. Only worth revisiting with direct futures execution — and gross t 0.3–1.4 gives no confidence even then."],
    ["—", "Tracks B & C (literature/platforms)", "Zero eligible candidates", "The literature's best mechanism (index-roll front-running) is documented-arbitraged and untestable on this data."],
], widths=[1.2 * cm, 5.6 * cm, 4.4 * cm, 5.6 * cm]))

story.append(Spacer(1, 6))
story.append(Paragraph(
    "<b>Honest cross-track comparison:</b> of four tracks, only the previously-existing "
    "candidate survived; the new tracks produced zero tradeable strategies. This is consistent "
    "with the project's base rate (~1,300 strategies tested, one survivor). For next time: "
    "the highest-value untested ground is (a) per-contract futures data to unlock the roll/term-"
    "structure family, and (b) completing the drift's forward kill gate — not more daily-bar "
    "backtests on the current data.", BODY))
story.append(Paragraph(
    "<b>Caveats:</b> financing rates assumed (0.01%/day/leg; T212 publishes no history); "
    "broker spread 0.30%/leg estimated from earlier measurements (corn 0.27%, gasoline 0.46%); "
    "roll-resistance probe is a heuristic (no per-contract data on the drive); free CFD margin "
    "for the $150 account not programmatically confirmable.", SMALL))

doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                        title="Atlas Edge-Search Campaign Final Report")
doc.build(story)
print("PDF written:", OUT, "size:", OUT.stat().st_size)
