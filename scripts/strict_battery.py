#!/usr/bin/env python3
"""strict_battery.py — extremely strict battery for seasonal candidates.

For each candidate (commodity, window) the battery runs, in order:

  A. IN-SAMPLE EXCELLENCE (2000-2014, or first 15 years of data)
       mean, t, win rate, median, best/worst year, outlier-trimmed mean/t.
  B. IN-SAMPLE MONTE CARLO PERMUTATION (>=1000, gate p < 1%)
       Null: a random same-length calendar window in the same period.
       p = fraction of 1000 random-window means >= observed net mean.
  C. BLIND HOLDOUT (2015+) — same protocol as the campaign.
  D. WALK-FORWARD (rolling re-estimation, no fixed split, no lookahead)
       For each test year y: direction = sign(mean over trailing 10 years,
       >=8 obs) of the SAME window; realised year-y net return = dir*ret-cost.
       Series stats: mean, t, win, median, std, cumulative, halves.
  E. WALK-FORWARD PERMUTATION (1000)
       For each perm: pick a RANDOM start month (same length), run the full
       walk-forward machinery on that window, record its mean. p = fraction
       of random-window walk-forwards >= the actual window's.
  F. WALK-FORWARD MONTE CARLO (bootstrap, 5000)
       Resample the realised walk-forward yearly returns (with replacement);
       report mean/t 5th-50th-95th percentiles + P(mean <= 0).
  G. ROBUSTNESS: cost ladder 8/15/25%; trimmed walk-forward (drop best+worst
       year); in-sample halves both positive; walk-forward halves.

Verdict (all must pass):
  1. |t_is| > 2
  2. p_is < 0.01          (in-sample permutation, 1% gate)
  3. holdout t > 2 AND holdout p_mc < 0.05
  4. walk-forward mean > 0 AND p_wf < 0.05 (walk-forward permutation)
  5. bootstrap P(mean <= 0) < 0.05
  6. trimmed walk-forward mean > 0
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from seasonal_backtest import (SPREAD_PCT, load_all, monthly_log_returns)
from seasonal_batch import (FIN_LADDER, N_PERM, RNG, cost_roundtrip_pct,
                            month_end_close, window_return)

DATA = Path("E:/forex-data")
OUT = DATA / "reports"

SEL_START, SEL_END = 2000, 2014
HO_START = 2015
WF_TRAIL = 10          # trailing years for walk-forward re-estimation
WF_MIN_OBS = 8
N_BOOT = 5000

# Unique survivors (deduped grid/named) + top near-misses from the campaign.
CANDIDATES = [
    ("HE", 8, 8,  "Hogs August SHORT"),
    ("HE", 4, 4,  "Hogs April LONG"),
    ("NG", 12, 2, "NatGas Dec-Feb (winter)"),
    ("HE", 12, 12, "Hogs December LONG"),
    ("RB", 9, 9,  "Gasoline September"),
    ("ZC", 7, 7,  "Corn July"),
    ("NG", 12, 12, "NatGas December"),
    ("ZW", 9, 9,  "Wheat September"),
]


def net_series(rets: pd.Series, direction: int, spread: float, months: int,
               fin: float) -> pd.Series:
    cost = cost_roundtrip_pct(spread, months, fin) / 100.0
    return direction * rets - cost


def stats(s: pd.Series) -> dict:
    if len(s) < 2:
        return {"n": len(s), "mean": float(s.mean()) if len(s) else None,
                "t": None, "win": None, "median": None, "std": None}
    mu, sd = s.mean(), s.std(ddof=1)
    return {"n": len(s), "mean": float(mu),
            "t": float(mu / (sd / math.sqrt(len(s)))) if sd > 0 else 0.0,
            "win": float((s > 0).mean()), "median": float(s.median()),
            "std": float(sd)}


def perm_p_in_sample(observed: float, monthly: dict, years, L: int,
                     cost_L: float, n_perm: int = N_PERM) -> float:
    """Random-calendar null restricted to the given years (in-sample or
    holdout): for each year pick a random start month, L-month ring window,
    net of cost_L; p = fraction of random-calendar means >= observed."""
    cnt = 1
    for _ in range(n_perm):
        means = []
        for y in years:
            arr = monthly.get(y)
            if arr is None or len(arr) < 12:
                continue
            j = RNG.randrange(12)
            w = sum(arr[(j + k) % 12] for k in range(L))
            means.append(w - cost_L)
        if np.mean(means) >= observed:
            cnt += 1
    return cnt / (n_perm + 1)


def walk_forward(rets: pd.Series, months: int, spread: float, fin: float) -> pd.Series:
    """Year-by-year realised net returns; direction re-estimated each year on
    the trailing WF_TRAIL years (min WF_MIN_OBS obs), sign of trailing mean."""
    cost = cost_roundtrip_pct(spread, months, fin) / 100.0
    out = {}
    for y, r in rets.items():
        trail = [rr for yy, rr in rets.items() if y - WF_TRAIL <= yy < y]
        if len(trail) < WF_MIN_OBS:
            continue
        d = 1 if float(np.mean(trail)) > 0 else -1
        out[y] = d * r - cost
    return pd.Series(out, dtype=float)


def wf_perm_p(actual_mean: float, monthly: dict, years, L: int,
              spread: float, fin: float, n_perm: int = N_PERM) -> float:
    """Random-WINDOW walk-forward permutation: for each perm, choose a random
    start month (same length L), run the full walk-forward on that window's
    year-by-year returns, record the mean; p = fraction >= actual mean."""
    cost = cost_roundtrip_pct(spread, L, fin) / 100.0
    cnt = 1
    for _ in range(n_perm):
        j = RNG.randrange(12)
        rw = {}
        for y in years:
            arr = monthly.get(y)
            if arr is None or len(arr) < 12:
                continue
            w = sum(arr[(j + k) % 12] for k in range(L))
            rw[y] = w - cost
        rws = pd.Series(rw, dtype=float)
        wf = walk_forward(rws, L, spread, fin)
        if len(wf) and wf.mean() >= actual_mean:
            cnt += 1
    return cnt / (n_perm + 1)


def bootstrap_p(series: pd.Series, n: int = N_BOOT) -> dict:
    rng = random.Random(7)
    arr = series.to_numpy()
    means, ts = [], []
    for _ in range(n):
        b = rng.choices(list(arr), k=len(arr))
        m = float(np.mean(b))
        means.append(m)
        if len(b) > 1:
            sd = float(np.std(b, ddof=1))
            ts.append(m / (sd / math.sqrt(len(b))) if sd > 0 else 0.0)
    means = np.array(means)
    ts = np.array(ts)
    return {
        "mean_p5": float(np.percentile(means, 5)),
        "mean_p50": float(np.percentile(means, 50)),
        "mean_p95": float(np.percentile(means, 95)),
        "p_leq_0": float((means <= 0).mean()),
        "t_p5": float(np.percentile(ts, 5)),
        "t_p50": float(np.percentile(ts, 50)),
        "t_p95": float(np.percentile(ts, 95)),
    }


def fmt_pct(x, nd: int = 2) -> str:
    return "n/a" if x is None else f"{x*100:+.{nd}f}%"


def fmt_t(x) -> str:
    return "n/a" if x is None else f"{x:+.2f}"


def fmt_win(x) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def fmt3(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def main():
    frames = load_all()
    me = {c: month_end_close(f) for c, f in frames.items()}
    mret = {c: monthly_log_returns(f) for c, f in frames.items()}
    panels = {}
    for c in me:
        panel = {}
        for ts, v in mret[c].items():
            panel.setdefault(ts.year, {})[ts.month] = v
        panels[c] = {y: [panel[y].get(m, 0.0) for m in range(1, 13)]
                     for y in panel}

    rows = []
    lines = ["# STRICT BATTERY — seasonal candidates",
             "_data 2000-01..2026-08 · walk-forward: 10y trailing re-estimation, "
             f"min {WF_MIN_OBS} obs · 1000-permutation MC · 5000-bootstrap MC · "
             "costs at 8/15/25% financing ladder_", ""]

    for c, m1, m2, label in CANDIDATES:
        if c not in me:
            lines.append(f"## {label} — NO DATA\n")
            continue
        L = (m2 - m1) % 12 + 1
        spread = SPREAD_PCT[c]
        rets = window_return(me[c], m1, m2)
        years = sorted(rets.index)
        sel_years = [y for y in years if SEL_START <= y <= SEL_END]
        ho_years = [y for y in years if y >= HO_START]

        # ---- A. in-sample excellence (15% financing headline) ----
        d_lock = 1 if rets.loc[sel_years].mean() > 0 else -1
        is_net = net_series(rets.loc[sel_years], d_lock, spread, L, 15.0)
        is_s = stats(is_net)
        trimmed = is_net.sort_values()
        is_trim = stats(trimmed.iloc[1:-1]) if len(trimmed) >= 4 else None
        half = len(sel_years) // 2
        is_h1 = float(is_net.iloc[:half].mean()) if half else None
        is_h2 = float(is_net.iloc[half:].mean()) if half else None

        # ---- B. in-sample permutation (p<1% gate) ----
        cost15 = cost_roundtrip_pct(spread, L, 15.0) / 100.0
        p_is = perm_p_in_sample(is_s["mean"], panels[c], sel_years, L, cost15)

        # ---- C. blind holdout ----
        ho_net = net_series(rets.loc[ho_years], d_lock, spread, L, 15.0)
        ho_s = stats(ho_net)
        p_ho = perm_p_in_sample(ho_s["mean"], panels[c], ho_years, L, cost15)

        # ---- D. walk-forward ----
        wf = walk_forward(rets, L, spread, 15.0)
        wf_s = stats(wf)
        wf_trim = stats(wf.sort_values().iloc[1:-1]) if len(wf) >= 4 else None
        wf_half = len(wf) // 2
        wf_h1 = float(wf.iloc[:wf_half].mean()) if wf_half else None
        wf_h2 = float(wf.iloc[wf_half:].mean()) if wf_half else None

        # ---- E. walk-forward permutation ----
        p_wf = wf_perm_p(wf_s["mean"] if wf_s["mean"] is not None else -1e9,
                         panels[c], years, L, spread, 15.0)

        # ---- F. walk-forward bootstrap ----
        boot = bootstrap_p(wf) if wf_s["mean"] is not None else {}

        # ---- G. cost ladder ----
        ladder = {int(fin): float(walk_forward(rets, L, spread, fin).mean())
                  for fin in FIN_LADDER}

        # ---- verdict ----
        gates = {
            "|t_is|>2": is_s["t"] is not None and abs(is_s["t"]) > 2,
            "p_is<0.01": p_is < 0.01,
            "holdout t>2 & p<0.05": (ho_s["t"] is not None and ho_s["t"] > 2
                                     and p_ho < 0.05),
            "wf mean>0 & p_wf<0.05": (wf_s["mean"] is not None and wf_s["mean"] > 0
                                      and p_wf < 0.05),
            "bootstrap P(<=0)<0.05": bool(boot) and boot["p_leq_0"] < 0.05,
            "trimmed wf>0": wf_trim is not None and wf_trim["mean"] > 0,
        }
        passed = all(gates.values())
        rows.append({
            "key": f"{c}_{m1}-{m2}", "label": label,
            "is_mean": is_s["mean"], "is_t": is_s["t"], "is_win": is_s["win"],
            "is_trim_t": is_trim["t"] if is_trim else None,
            "p_is": p_is, "ho_mean": ho_s["mean"], "ho_t": ho_s["t"],
            "ho_win": ho_s["win"], "p_ho": p_ho,
            "wf_mean": wf_s["mean"], "wf_t": wf_s["t"], "wf_win": wf_s["win"],
            "wf_median": wf_s["median"], "wf_std": wf_s["std"],
            "wf_n": wf_s["n"], "p_wf": p_wf,
            "boot_p50": boot.get("mean_p50"), "boot_p5": boot.get("mean_p5"),
            "boot_p95": boot.get("mean_p95"), "p_leq_0": boot.get("p_leq_0"),
            "wf_trim_mean": wf_trim["mean"] if wf_trim else None,
            "wf_h1": wf_h1, "wf_h2": wf_h2, "ladder_8": ladder[8],
            "ladder_15": ladder[15], "ladder_25": ladder[25],
            "VERDICT": "PASS" if passed else "FAIL",
            "gates": "; ".join(k for k, v in gates.items() if not v) or "all pass",
        })

        lines.append(f"## {label} ({c} {m1:02d}-{m2:02d}) — "
                     f"{'PASS' if passed else 'FAIL'}\n")
        lines.append(f"- In-sample ({sel_years[0]}-{sel_years[-1]}): mean "
                     f"{fmt_pct(is_s['mean'])}, t {fmt_t(is_s['t'])}, win "
                     f"{fmt_win(is_s['win'])}, "
                     f"trimmed t {fmt_t(is_trim['t'] if is_trim else None)}")
        lines.append(f"  - In-sample permutation p = {p_is:.4f} "
                     f"({'<1% gate PASS' if p_is < 0.01 else 'FAIL'})")
        lines.append(f"  - In-sample halves: {fmt_pct(is_h1)} / {fmt_pct(is_h2)}")
        lines.append(f"- Holdout (2015+): mean {fmt_pct(ho_s['mean'])}, "
                     f"t {fmt_t(ho_s['t'])}, win "
                     f"{fmt_win(ho_s['win'])}, "
                     f"p {p_ho:.4f}")
        lines.append(f"- Walk-forward (n={wf_s['n']}): mean {fmt_pct(wf_s['mean'])}, "
                     f"t {fmt_t(wf_s['t'])}, win "
                     f"{fmt_win(wf_s['win'])}, "
                     f"median {fmt_pct(wf_s['median'])}, std {fmt_pct(wf_s['std'])}")
        lines.append(f"  - Walk-forward permutation p = {p_wf:.4f} "
                     f"({'PASS' if p_wf < 0.05 else 'FAIL'})")
        if boot:
            lines.append(f"  - Bootstrap (5000): mean 5-50-95% = "
                         f"{fmt_pct(boot['mean_p5'])} / {fmt_pct(boot['mean_p50'])} / "
                         f"{fmt_pct(boot['mean_p95'])}, P(mean<=0) = "
                         f"{boot['p_leq_0']:.3f} "
                         f"({'PASS' if boot['p_leq_0'] < 0.05 else 'FAIL'})")
        lines.append(f"  - Halves: {fmt_pct(wf_h1)} / {fmt_pct(wf_h2)}; "
                     f"trimmed wf mean {fmt_pct(wf_trim['mean'] if wf_trim else None)}")
        lines.append(f"  - Cost ladder (8/15/25%): {fmt_pct(ladder[8])} / "
                     f"{fmt_pct(ladder[15])} / {fmt_pct(ladder[25])}")
        lines.append(f"  - Gates: {'ALL PASS' if passed else 'FAILED: ' + '; '.join(k for k, v in gates.items() if not v)}\n")

    lines.append("## Summary\n")
    lines.append("| key | label | is_t | p_is | ho_t | p_ho | wf_mean | wf_t | "
                 "p_wf | boot P(<=0) | trimmed wf | ladder 8/15/25 | verdict |")
    lines.append("|-----|-------|------|------|------|------|---------|------|"
                 "------|-------------|------------|----------------|---------|")
    for r in rows:
        lines.append(
            f"| {r['key']} | {r['label']} | {fmt_t(r['is_t'])} | {r['p_is']:.4f} | "
            f"{fmt_t(r['ho_t'])} | {r['p_ho']:.4f} | {fmt_pct(r['wf_mean'])} | "
            f"{fmt_t(r['wf_t'])} | {r['p_wf']:.4f} | "
            f"{fmt3(r.get('p_leq_0'))} | "
            f"{fmt_pct(r['wf_trim_mean'])} | {fmt_pct(r['ladder_8'])}/"
            f"{fmt_pct(r['ladder_15'])}/{fmt_pct(r['ladder_25'])} | "
            f"{r['VERDICT']} |")
    lines.append("")
    lines.append("## What the numbers mean\n")
    lines.append("- **In-sample t**: signal strength in the 2000-2014 fit window "
                 "(|t|>2 required). High here alone is cheap — it is why the rest exists.")
    lines.append("- **p_is (in-sample permutation)**: 1000 random same-length calendar "
                 "windows; the chance a random month matches the observed fit-window "
                 "profit. p<0.01 means the fit is not luck-of-the-calendar.")
    lines.append("- **Holdout**: locked-direction 2015+ performance net of costs; t>2 "
                 "and p<0.05 mean the fit generalised forward.")
    lines.append("- **Walk-forward**: every year, direction is re-estimated on the "
                 "trailing 10 years only (no lookahead) and the NEXT year is traded. "
                 "This is the honest 'would I have traded it?' series.")
    lines.append("- **p_wf (walk-forward permutation)**: 1000 full walk-forwards on "
                 "random windows; the chance a random month matches the actual "
                 "walk-forward profit under identical machinery.")
    lines.append("- **Bootstrap P(mean<=0)**: 5000 resamples of the walk-forward "
                 "years; probability the true mean is non-positive. <0.05 is the "
                 "strict bar.")
    lines.append("- **Trimmed**: best and worst year removed — a real effect "
                 "survives; a one-year fluke dies.")
    lines.append("- **Ladder**: net at 8/15/25% annualised financing; a strategy "
                 "that dies at 25% is financing-dependent.")
    (OUT / "strict_battery.md").write_text("\n".join(lines), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT / "strict_battery.csv", index=False)
    print(f"battery done: {sum(1 for r in rows if r['VERDICT']=='PASS')}/{len(rows)} PASS")
    print("wrote reports/strict_battery.md + strict_battery.csv")


if __name__ == "__main__":
    main()
