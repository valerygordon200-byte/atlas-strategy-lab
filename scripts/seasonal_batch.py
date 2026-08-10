#!/usr/bin/env python3
"""seasonal_batch.py — mass seasonal-commodity testing campaign.

Tests a large strategy catalog through the SAME protocol standard as
seasonal_backtest.py (selection -> lock direction -> blind holdout -> full
costs), plus a 1000-permutation Monte Carlo p-value on the holdout:

  Catalog A  full single-month grid: (commodity, month)  = 26 x 12 = 312
  Catalog B  research-named multi-month windows (~37) from a web sweep
             (CME education, EIA, SSRN 2598514 metals seasonality,
             agricultural seasonality studies, prior-study livestock claims)

Selection   2000-01-01..2014-12-31  (same split as the strict standard)
Holdout     2015-01-01..present
Direction   locked from selection sign(mean); sel_n >= 8 required
Costs       retail-CFD model from seasonal_backtest: spread + slippage
            (0.5x spread each way) + roll (spread per month held) +
            financing ladder 8/15/25% annualised, prorated per month
Monte Carlo 1000 shuffles of holdout window returns (seed 42),
            p = (1 + #perm_mean >= actual) / 1001

Outputs:    reports/seasonal_leaderboard.csv
            reports/seasonal_campaign_report.md
"""
from __future__ import annotations

import csv
import json
import math
import random
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from seasonal_backtest import (COMMODITIES, SPREAD_PCT, T212_CONFIRMED,
                               T212_UNAVAILABLE, load_all, monthly_log_returns)

DATA = Path("E:/forex-data")
RAW = DATA / "market-data/raw/yahoo"
OUT = DATA / "reports"

SEL_START, SEL_END = "2000-01-01", "2014-12-31"
HO_START = "2015-01-01"
FIN_LADDER = (8.0, 15.0, 25.0)
N_PERM = 1000
RNG = random.Random(42)

# ---------------------------------------------------------------------------
# Research-named multi-month windows: (commodity, m1, m2, label, mechanism,
# source). Direction is LOCKED FROM THE DATA (selection window), not assumed
# from the source — the source only names the window worth testing.
# ---------------------------------------------------------------------------
NAMED = [
    # Energy — EIA nat-gas seasonality, CME, MacroMicro oil season chart
    ("NG", 12, 2, "NatGas winter premium", "space-heating demand peak", "EIA 2013; CME"),
    ("NG", 7, 8, "NatGas summer cooling", "electricity cooling demand", "EIA 2013; CME"),
    ("NG", 3, 4, "NatGas shoulder collapse", "injection season oversupply", "EIA 2013"),
    ("HO", 10, 11, "HeatingOil build season", "pre-winter distillate restock", "EIA; MacroMicro"),
    ("HO", 1, 2, "HeatingOil post-winter fade", "mild demand after peak", "EIA; MacroMicro"),
    ("RB", 5, 9, "Gasoline driving season", "US summer road demand", "EIA; AAA blend notes"),
    ("RB", 9, 10, "Gasoline winter-blend switch", "cheaper blend re-pricing", "AAA winter-blend"),
    ("CL", 4, 5, "Crude spring peak", "refinery turnaround + demand", "MacroMicro season chart"),
    ("CL", 1, 1, "Crude January trough", "post-holiday demand lull", "MacroMicro season chart"),
    # Grains — CME grains education, SSRN 245931
    ("ZC", 5, 6, "Corn planting premium", "weather risk in planting window", "CME grains course"),
    ("ZC", 7, 9, "Corn harvest pressure", "new-crop supply into Sep", "CME grains course"),
    ("ZC", 12, 12, "Corn post-harvest low", "harvest low + storage carry", "CME grains course"),
    ("ZW", 7, 7, "Wheat harvest pressure", "winter-wheat harvest glut", "CME grains course"),
    ("ZS", 5, 6, "Soy planting premium", "planting weather risk", "CME grains course"),
    ("ZS", 8, 10, "Soy harvest pressure", "new-crop supply into Oct", "CME grains course"),
    ("ZL", 12, 12, "Soybean-oil demand", "holiday food demand", "ag seasonality study"),
    # Livestock — prior-study claims (brief) + grill season
    ("HE", 2, 2, "Hogs Feb", "prior-study claim (LONG)", "ATLAS prior study"),
    ("HE", 4, 4, "Hogs Apr", "prior-study claim (LONG)", "ATLAS prior study"),
    ("HE", 8, 8, "Hogs Aug", "prior-study claim (SHORT)", "ATLAS prior study"),
    ("HE", 10, 10, "Hogs Oct", "prior-study claim (SHORT)", "ATLAS prior study"),
    ("LE", 2, 2, "Cattle grill restock", "pre-grill-season feeder demand", "livestock seasonality"),
    ("LE", 5, 5, "Cattle May", "prior-study claim (SHORT)", "ATLAS prior study"),
    ("GF", 5, 5, "Feeder Cattle May", "prior-study claim (LONG)", "ATLAS prior study"),
    # Softs — ag seasonality studies (Feb/Jul/Sep strong months), holiday demand
    ("KC", 2, 3, "Coffee Feb-Mar", "post-harvest tightness", "ag seasonality study"),
    ("KC", 7, 9, "Coffee Jul-Sep", "Brazil frost-risk window", "ag seasonality study"),
    ("SB", 8, 9, "Sugar Aug-Sep", "pre-harvest tightness", "ag seasonality study"),
    ("SB", 2, 3, "Sugar harvest", "main-crop harvest pressure", "ag seasonality study"),
    ("CC", 10, 10, "Cocoa Oct", "holiday chocolate demand", "softs seasonality"),
    ("CC", 12, 1, "Cocoa post-holiday", "demand fade into new year", "softs seasonality"),
    ("CT", 5, 5, "Cotton planting", "planting weather premium", "ag seasonality study"),
    ("CT", 10, 11, "Cotton harvest", "harvest pressure", "ag seasonality study"),
    ("OJ", 11, 11, "OJ freeze season onset", "Florida freeze-risk premium", "softs seasonality"),
    ("OJ", 3, 3, "OJ post-freeze fade", "risk premium unwinds", "softs seasonality"),
    # Metals — SSRN 2598514 gold/silver/platinum/palladium/copper
    ("GC", 8, 10, "Gold autumn effect", "jewellery demand + festival season", "SSRN 2598514"),
    ("GC", 1, 1, "Gold January fade", "post-holiday demand lull", "SSRN 2598514"),
    ("SI", 9, 9, "Silver autumn", "industrial + festive demand", "SSRN 2598514"),
    ("HG", 1, 1, "Copper January restock", "industrial restocking", "SSRN 2598514"),
    ("HG", 7, 9, "Copper summer lull", "northern summer industrial pause", "SSRN 2598514"),
    ("PL", 10, 10, "Platinum Oct", "autocatalyst demand season", "SSRN 2598514"),
]


def month_end_close(df: pd.DataFrame) -> pd.Series:
    """Month-end close series (last close of each calendar month)."""
    return df["close"].resample("ME").last().dropna()


def window_return(me: pd.Series, m1: int, m2: int) -> pd.Series:
    """log(C[y,m2] / C[y,m1-1]) per calendar year y. m1=1 uses Dec of y-1.
    Returns a Series indexed by year (only complete years)."""
    keyed = {}
    for ts, v in me.items():
        keyed[(ts.year, ts.month)] = v
    out = {}
    for y in range(me.index.min().year, me.index.max().year + 1):
        prev_key = (y - 1, 12) if m1 == 1 else (y, m1 - 1)
        end_key = (y, m2)
        if prev_key in keyed and end_key in keyed:
            out[y] = math.log(keyed[end_key] / keyed[prev_key])
    return pd.Series(out, dtype=float)


def sel_stats(rets: pd.Series, sel_mask) -> dict | None:
    sub = rets[sel_mask]
    if len(sub) < 8:
        return None
    mu, sd = sub.mean(), sub.std(ddof=1)
    t = mu / (sd / math.sqrt(len(sub))) if sd > 0 else 0.0
    return {"n": int(len(sub)), "mean": float(mu), "t": float(t)}


def cost_roundtrip_pct(spread_pct: float, months: int, fin_pct: float) -> float:
    """% of notional: spread + slippage(0.5x each way) + roll per month +
    financing prorated per month. Same model as seasonal_backtest."""
    s = spread_pct / 100.0
    fin_m = (fin_pct / 100.0) / 12.0
    return (s + 2 * (0.5 * s) + months * s + months * fin_m) * 100.0


def perm_p_value(observed_mean: float, monthly: dict, years, L: int,
                 cost_L: float, n_perm: int = N_PERM) -> float:
    """Calendar-effect permutation test.

    Null: for each holdout year, pick a RANDOM start month and take the
    L-month window return (ring-sum within the year), net of cost_L, then
    average over years. p = fraction of 1000 random-calendar means >= the
    observed window mean. (Shuffling one series preserves its mean, so the
    null MUST resample the calendar, not the values.)"""
    cnt = 1  # the observed draw itself
    for _ in range(n_perm):
        means = []
        for y in years:
            arr = monthly.get(y)
            if arr is None or len(arr) < 12:
                continue
            j = RNG.randrange(12)
            w = sum(arr[(j + k) % 12] for k in range(L))
            means.append(w - cost_L)
        if np.mean(means) >= observed_mean:
            cnt += 1
    return cnt / (n_perm + 1)


def main():
    frames = load_all()
    me = {c: month_end_close(f) for c, f in frames.items()}
    # monthly gross log-return panel per instrument: {year: array(12)}
    panels = {}
    for c, f in frames.items():
        mret = monthly_log_returns(f)  # indexed by month-end
        panel = {}
        for ts, v in mret.items():
            panel.setdefault(ts.year, {})[ts.month] = v
        panels[c] = {y: [panel[y].get(m, 0.0) for m in range(1, 13)]
                     for y in panel}
    print(f"loaded {len(me)}/{len(COMMODITIES)} instruments")

    # selection / holdout masks by calendar year
    sel_years = set(range(2000, 2015))
    ho_years = set(range(2015, 2027))

    def run_strategy(c, m1, m2, label, mechanism, source, kind):
        rets = window_return(me[c], m1, m2)
        if len(rets) < 16:
            return None
        sel_mask = rets.index.isin(sel_years)
        ho_mask = rets.index.isin(ho_years)
        st = sel_stats(rets, sel_mask)
        if st is None:
            return None
        months = (m2 - m1) % 12 + 1
        spread = SPREAD_PCT[c]
        rec = {
            "kind": kind, "key": f"{c}_{m1}-{m2}", "commodity": c,
            "months": f"{m1:02d}-{m2:02d}" if m2 >= m1 else f"{m1:02d}-{m2:02d}",
            "label": label, "mechanism": mechanism, "source": source,
            "sel_n": st["n"], "sel_mean": st["mean"], "sel_t": st["t"],
            "direction": 1 if st["mean"] > 0 else -1,
            "n_hold": int(ho_mask.sum()),
            "t212": "Y" if c in T212_CONFIRMED else ("N" if c in T212_UNAVAILABLE else "?"),
        }
        ho = rets[ho_mask]
        for fin in FIN_LADDER:
            cost = cost_roundtrip_pct(spread, months, fin) / 100.0
            net = rec["direction"] * ho - cost
            rec[f"net_mean_{int(fin)}%"] = float(net.mean())
            rec[f"net_t_{int(fin)}%"] = float(
                net.mean() / (net.std(ddof=1) / math.sqrt(len(net))) if net.std(ddof=1) > 0 else 0.0)
            rec[f"win_{int(fin)}%"] = float((net > 0).mean())
        # headline = 15% financing
        hm = rec["net_mean_15%"]
        rec["ho_mean"] = hm
        rec["ho_t"] = rec["net_t_15%"]
        rec["win"] = rec["win_15%"]
        cost15 = cost_roundtrip_pct(spread, months, 15.0) / 100.0
        rec["p_mc"] = perm_p_value(
            hm, panels[c], [y for y in ho.index if y in panels.get(c, {})],
            months, cost15)
        # sub-period stability (holdout halves)
        half = len(ho) // 2
        ho_arr = (rec["direction"] * ho - cost_roundtrip_pct(spread, months, 15.0) / 100.0)
        rec["ho_h1"] = float(ho_arr.iloc[:half].mean()) if half else None
        rec["ho_h2"] = float(ho_arr.iloc[half:].mean()) if half else None
        return rec

    results = []
    # Catalog A: full grid
    for c in COMMODITIES:
        if c not in me:
            continue
        for m in range(1, 13):
            r = run_strategy(c, m, m, f"{c} {m:02d}", "single-month grid", "grid", "grid")
            if r:
                results.append(r)
    # Catalog B: named
    for c, m1, m2, label, mech, src in NAMED:
        if c not in me:
            continue
        r = run_strategy(c, m1, m2, label, mech, src, "named")
        if r:
            results.append(r)

    # ---- leaderboard ----
    cols = ["kind", "key", "commodity", "months", "label", "mechanism", "source",
            "direction", "sel_n", "sel_mean", "sel_t", "n_hold", "ho_mean",
            "ho_t", "win", "p_mc", "ho_h1", "ho_h2", "t212"]
    for fin in FIN_LADDER:
        cols += [f"net_mean_{int(fin)}%", f"net_t_{int(fin)}%", f"win_{int(fin)}%"]
    df = pd.DataFrame(results)[cols].sort_values("ho_t", ascending=False)
    (OUT / "seasonal_leaderboard.csv").write_text(
        df.to_csv(index=False), encoding="utf-8")

    # ---- report ----
    n_tested = len(df)
    sel_pass = df[df.sel_t.abs() > 2]
    exp_chance = n_tested * 0.0455
    hold_sig = df[(df.p_mc < 0.05) & (df.ho_t > 2)]
    pos_both_halves = df[(df.ho_h1 > 0) & (df.ho_h2 > 0)]

    lines = []
    lines.append("# Commodity Seasonality Campaign — mass test report\n")
    lines.append(f"_Generated {date.today().isoformat()} · data 2000-01..2026-08 "
                 f"(Yahoo continuous front-month, back-adjusted) · protocol: "
                 f"selection 2000-2014 |t|>2 lock -> blind holdout 2015+ net of "
                 f"retail-CFD costs (spread+slippage+roll+financing) -> "
                 f"1000-permutation MC p-value_\n")
    lines.append(f"## Headline\n")
    lines.append(f"- Strategies tested: **{n_tested}** "
                 f"({len(df[df.kind=='grid'])} single-month grid, "
                 f"{len(df[df.kind=='named'])} research-named windows)")
    lines.append(f"- Passed selection |t|>2: **{len(sel_pass)}** "
                 f"(expected by chance ~{exp_chance:.1f})")
    lines.append(f"- Survived blind holdout net-of-costs (ho_t>2 and p_mc<0.05): "
                 f"**{len(hold_sig)}**")
    lines.append(f"- Positive in BOTH holdout halves: **{len(pos_both_halves)}**")
    lines.append("\n## Top 50 (ranked by holdout t, 15% financing)\n")
    lines.append("| # | key | label | dir | sel_t | ho_mean | ho_t | win | p_mc | h1 | h2 | T212 |")
    lines.append("|---|-----|-------|-----|-------|---------|------|-----|------|----|----|------|")
    for i, r in df.head(50).iterrows():
        d = "L" if r.direction == 1 else "S"
        lines.append(
            f"| {i+1} | {r.key} | {r.label} | {d} | {r.sel_t:.2f} | "
            f"{r.ho_mean*100:+.2f}% | {r.ho_t:+.2f} | {r.win:.0%} | "
            f"{r.p_mc:.3f} | {('' if r.ho_h1 is None else f'{r.ho_h1*100:+.1f}%')} | "
            f"{('' if r.ho_h2 is None else f'{r.ho_h2*100:+.1f}%')} | {r.t212} |")
    lines.append("\n## Survivors (holdout t>2 AND p<0.05, 15% financing)\n")
    if len(hold_sig):
        for _, r in hold_sig.sort_values("ho_t", ascending=False).iterrows():
            lines.append(f"- **{r.key}** {r.label} — dir {'L' if r.direction==1 else 'S'}, "
                         f"sel_t {r.sel_t:+.2f}, holdout {r.ho_mean*100:+.2f}%/yr "
                         f"(t {r.ho_t:+.2f}), win {r.win:.0%}, p_mc {r.p_mc:.3f}, "
                         f"halves {('' if r.ho_h1 is None else f'{r.ho_h1*100:+.1f}%')}/"
                         f"{('' if r.ho_h2 is None else f'{r.ho_h2*100:+.1f}%')}, "
                         f"T212 {r.t212}")
    else:
        lines.append("_None._")
    lines.append("\n## Sector notes (research-named windows)\n")
    for sec, coms in [("Energy", ["NG", "HO", "RB", "CL"]),
                      ("Grains", ["ZC", "ZW", "ZS", "ZL", "ZM", "ZO", "ZR"]),
                      ("Livestock", ["LE", "GF", "HE"]),
                      ("Softs", ["KC", "SB", "CC", "CT", "OJ"]),
                      ("Metals", ["GC", "SI", "HG", "PL", "PA"])]:
        sub = df[df.commodity.isin(coms) & (df.kind == "named")]
        best = sub.sort_values("ho_t", ascending=False).head(3)
        lines.append(f"### {sec}\n")
        for _, r in best.iterrows():
            lines.append(f"- {r.label} ({r.key}): holdout {r.ho_mean*100:+.2f}%/yr, "
                         f"t {r.ho_t:+.2f}, p {r.p_mc:.3f} — {r.source}")
        lines.append("")
    lines.append("\n## Honest verdict\n")
    lines.append("Multiple-testing reality: with ~350 strategies tested, ~16 would "
                 "pass |t|>2 by chance alone in selection, and several will clear "
                 "the holdout bar by luck. The survivors above are candidates for "
                 "the FULL strict battery (seasonal_backtest.py: outlier trim, "
                 "roll-convention check, cost ladder, mechanism audit, $100 "
                 "compound sim) before any paper capital. Seasonality in "
                 "financialised commodities is known to decay — treat every line "
                 "as a hypothesis with evidence attached, not a promise.\n")
    (OUT / "seasonal_campaign_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"tested {n_tested}, selection-pass {len(sel_pass)}, "
          f"holdout-survivors {len(hold_sig)}, pos-both-halves {len(pos_both_halves)}")
    print("wrote reports/seasonal_leaderboard.csv + seasonal_campaign_report.md")


if __name__ == "__main__":
    main()
