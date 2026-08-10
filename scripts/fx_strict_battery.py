#!/usr/bin/env python3
"""fx_strict_battery.py — extremely strict battery for FX candidates.

Same six-gate protocol as strict_battery.py (seasonal), adapted to daily and
event-driven strategies:

  A. IN-SAMPLE EXCELLENCE (2016-08..2021-12): mean, Newey-West t, win, trimmed
  B. IN-SAMPLE MONTE CARLO PERMUTATION (1000, gate p < 1%)
       news:     sign-flip null (mechanism test: does surprise direction matter?)
       reversal: random-signal null
  C. BLIND HOLDOUT (2022-01..2026-08): NW t > 2 AND p < 0.05
  D. WALK-FORWARD (no lookahead)
       news:     trade a year only if trailing-3y mean net > 0 (min 30 events);
                 direction = surprise direction (mechanism, never re-estimated)
       reversal: direction = sign(trailing 2y raw-signal mean), trade next year
  E. WALK-FORWARD PERMUTATION (1000): random-day null through the SAME machinery
  F. WALK-FORWARD MONTE CARLO (5000 bootstrap): mean 5/50/95%, P(mean <= 0)
  G. ROBUSTNESS: cost ladder 0.5/1/2 pips, trimmed wf, first/second-half

Strictness upgrades over the campaign (both remove lookahead):
  - surprise z-scores use EXPANDING per-title mean/std (trailing only), so the
    standardization never sees future surprises;
  - entry is at the NEXT day's open (return = event-day close -> next-day
    close), so the pre-event move is never captured.

Verdict (all must pass):
  1. |t_is| > 2 (Newey-West lag-5)
  2. p_is < 0.01
  3. holdout NW t > 2 AND p_ho < 0.05
  4. wf mean > 0 AND p_wf < 0.05
  5. bootstrap P(mean <= 0) < 0.05
  6. trimmed wf mean > 0
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from edge_scan import PIP, load_d1, nw_t

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(31)

IS_END = "2021-12-31"
OOS_START = "2022-01-01"
Z_THR = 0.5
RT_PIPS = 1.0          # baseline round-trip cost in pips
WF_TRAIL_YEARS = 3     # trailing years for the news walk-forward profitability gate
WF_MIN_EVENTS = 30     # min trailing events before a year may be traded
REV_TRAIL_DAYS = 504   # trailing days for reversal direction re-estimation
REV_MIN_OBS = 200
N_PERM = 1000
N_BOOT = 5000

CORE_PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD"]
CONV = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "USDJPY": 1, "USDCAD": 1}


def load_big_events() -> pd.DataFrame:
    """USD High+Medium events with actual+forecast; per-title EXPANDING z."""
    ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)
    ev = ev[(ev["currency"] == "USD") &
            (ev["impact"].isin(["High", "Medium"])) &
            ev["actual"].notna() & ev["forecast"].notna()].copy()
    ev["surprise"] = (pd.to_numeric(ev["actual"], errors="coerce") -
                      pd.to_numeric(ev["forecast"], errors="coerce"))
    ev = ev.dropna(subset=["surprise"]).sort_values("date_utc")
    ev["z"] = np.nan
    for title, g in ev.groupby("title"):
        g = g.sort_values("date_utc")
        s = g["surprise"]
        mu = s.expanding(min_periods=20).mean().shift(1)
        sd = s.expanding(min_periods=20).std().shift(1)
        z = (s - mu) / sd.where(sd > 1e-12)
        ev.loc[g.index, "z"] = z.clip(-8, 8)
    ev = ev[ev["z"].abs() >= Z_THR].copy()
    ev["date"] = ev["date_utc"].dt.date
    return ev


def event_net_frame(pair: str, events: pd.DataFrame) -> pd.DataFrame:
    """Per-event net return: next-day-open entry, 1-pip RT cost."""
    c = load_d1(pair)["Close"]
    r = c.pct_change()
    next_r = r.shift(-1).dropna()          # return of the bar AFTER the event day
    next_r.index = next_r.index.date
    ev = events.copy()
    ev["r"] = ev["date"].map(next_r)
    ev = ev.dropna(subset=["r"])
    cost = RT_PIPS * PIP[pair] / float(c.mean())
    ev["net"] = CONV[pair] * np.sign(ev["z"]) * ev["r"] - cost
    return ev[["date", "z", "r", "net"]].copy()


def stats_series(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) < 10:
        return {"n": len(s), "mean": float(s.mean()) if len(s) else None,
                "t": None, "nw": None, "win": None}
    mu, sd = s.mean(), s.std(ddof=1)
    if sd == 0:
        return {"n": len(s), "mean": float(mu), "t": 0.0, "nw": 0.0,
                "win": float((s > 0).mean())}
    return {"n": len(s), "mean": float(mu),
            "t": float(mu / (sd / math.sqrt(len(s)))),
            "nw": float(nw_t(s.to_numpy(), lag=5)),
            "win": float((s > 0).mean())}


def trimmed_mean_by_year(s: pd.Series) -> float:
    """Mean after dropping the best and worst YEAR (grouped by index year)."""
    if isinstance(s.index, pd.DatetimeIndex):
        y = pd.Series(s.index.year, index=s.index)
    else:
        y = pd.Series(s.index, index=s.index)
    ym = s.groupby(y).mean()
    if len(ym) < 3:
        return float(s.mean())
    return float(ym.sort_values().iloc[1:-1].mean())


def perm_p_signflip(actual: float, r: np.ndarray, signs: np.ndarray,
                    cost: float, n_perm: int = N_PERM) -> float:
    """Null: position sign flipped randomly per event (mechanism test)."""
    cnt = 1
    for _ in range(n_perm):
        flips = RNG.choice([-1.0, 1.0], len(r))
        if (signs * flips * r - cost).mean() >= actual:
            cnt += 1
    return cnt / (n_perm + 1)


def wf_news(ev: pd.DataFrame) -> pd.Series:
    """Year-by-year mean net return; a year is traded only if the trailing
    WF_TRAIL_YEARS of events (min WF_MIN_EVENTS) have positive mean net.
    Direction is ALWAYS the surprise direction (mechanism)."""
    ev = ev.copy()
    if "date" in ev.columns:
        ev["year"] = pd.to_datetime(ev["date"]).dt.year
    out = {}
    for y in sorted(ev["year"].unique()):
        trail = ev[(ev["year"] >= y - WF_TRAIL_YEARS) & (ev["year"] < y)]
        if len(trail) < WF_MIN_EVENTS:
            continue
        trade = trail["net"].mean() > 0
        this = ev[ev["year"] == y]
        out[y] = float(this["net"].mean()) if (trade and len(this)) else 0.0
    return pd.Series(out, dtype=float)


def wf_perm_p_news(actual_mean: float, ev: pd.DataFrame, pair_ret: pd.Series,
                   n_perm: int = N_PERM) -> float:
    """Random-day null through the SAME walk-forward machinery: each year's
    events are replaced by the same count of random daily returns."""
    ev = ev.copy()
    ev["year"] = pd.to_datetime(ev["date"]).dt.year
    years = sorted(ev["year"].unique())
    k_by_year = {y: int((ev["year"] == y).sum()) for y in years}
    r_arr = pair_ret.to_numpy()
    cnt = 1
    for _ in range(n_perm):
        frames = []
        for y in years:
            k = k_by_year[y]
            if k == 0:
                continue
            frames.append(pd.DataFrame({"year": y,
                                        "net": RNG.choice(r_arr, k, replace=True)}))
        null_ev = pd.concat(frames)
        wf = wf_news(null_ev)
        if len(wf) and wf.mean() >= actual_mean:
            cnt += 1
    return cnt / (n_perm + 1)


def wf_reversal(s: pd.Series, cost: float) -> pd.Series:
    """Year-by-year mean net return; direction re-estimated each year on the
    trailing REV_TRAIL_DAYS of raw signal returns (min REV_MIN_OBS)."""
    out = {}
    prev_d = None
    for y, grp in s.groupby(s.index.year):
        trail = s[s.index < grp.index[0]].iloc[-REV_TRAIL_DAYS:]
        if len(trail) < REV_MIN_OBS:
            continue
        d = 1 if trail.mean() > 0 else -1
        m = float(grp.mean())
        flip_cost = cost / len(grp) if (prev_d is not None and d != prev_d) else 0.0
        out[y] = d * m - flip_cost
        prev_d = d
    return pd.Series(out, dtype=float)


def wf_perm_p_reversal(actual_mean: float, s: pd.Series, pair_ret: pd.Series,
                       cost: float, n_perm: int = N_PERM) -> float:
    """Random-day null through the SAME reversal walk-forward machinery."""
    years = sorted(s.index.year.unique())
    k_by_year = {y: int((s.index.year == y).sum()) for y in years}
    r_arr = pair_ret.to_numpy()
    cnt = 1
    for _ in range(n_perm):
        frames = []
        for y in years:
            k = k_by_year[y]
            if k == 0:
                continue
            frames.append(pd.Series(RNG.choice(r_arr, k, replace=True),
                                    index=pd.date_range(f"{y}-01-01", periods=k)))
        null_s = pd.concat(frames)
        wf = wf_reversal(null_s, cost)
        if len(wf) and wf.mean() >= actual_mean:
            cnt += 1
    return cnt / (n_perm + 1)


def bootstrap_p(series: pd.Series, n: int = N_BOOT) -> dict:
    rng = random.Random(17)
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
    return {"mean_p5": float(np.percentile(means, 5)),
            "mean_p50": float(np.percentile(means, 50)),
            "mean_p95": float(np.percentile(means, 95)),
            "p_leq_0": float((means <= 0).mean()),
            "t_p5": float(np.percentile(ts, 5)),
            "t_p95": float(np.percentile(ts, 95))}


def fmt_pct(x, nd=3):
    return "n/a" if x is None else f"{x*100:+.{nd}f}%"


def fmt_t(x):
    return "n/a" if x is None else f"{x:+.2f}"


def fmt_win(x):
    return "n/a" if x is None else f"{x:.0%}"


def run_news_battery(pair: str, events: pd.DataFrame) -> dict:
    ev = event_net_frame(pair, events)
    if len(ev) < 60:
        return None
    ret_full = load_d1(pair)["Close"].pct_change().dropna()
    is_ev = ev[ev["date"] <= pd.Timestamp(IS_END).date()]
    oos_ev = ev[ev["date"] >= pd.Timestamp(OOS_START).date()]
    if len(is_ev) < 30 or len(oos_ev) < 20:
        return None

    # A. in-sample excellence
    is_s = stats_series(is_ev["net"])
    is_trim = trimmed_mean_by_year(is_ev.set_index(pd.to_datetime(is_ev["date"]))["net"])
    # B. in-sample permutation (sign-flip mechanism null)
    p_is = perm_p_signflip(is_s["mean"], is_ev["r"].to_numpy(),
                           CONV[pair] * np.sign(is_ev["z"].to_numpy()),
                           RT_PIPS * PIP[pair] / float(load_d1(pair)["Close"].mean()))
    # C. blind holdout
    ho_s = stats_series(oos_ev["net"])
    p_ho = perm_p_signflip(ho_s["mean"], oos_ev["r"].to_numpy(),
                           CONV[pair] * np.sign(oos_ev["z"].to_numpy()),
                           RT_PIPS * PIP[pair] / float(load_d1(pair)["Close"].mean()))
    # D. walk-forward
    wf = wf_news(ev)
    wf_s = stats_series(wf)
    wf_trim = trimmed_mean_by_year(wf) if len(wf) >= 3 else None
    # E. walk-forward permutation
    p_wf = wf_perm_p_news(wf_s["mean"] if wf_s["mean"] is not None else -1e9,
                          ev, ret_full)
    # F. bootstrap
    boot = bootstrap_p(wf) if wf_s["mean"] is not None else {}
    # G. cost ladder
    ladder = {}
    for pips in (0.5, 1.0, 2.0):
        ev2 = ev.copy()
        cost = pips * PIP[pair] / float(load_d1(pair)["Close"].mean())
        ev2["net"] = CONV[pair] * np.sign(ev2["z"]) * ev2["r"] - cost
        ladder[pips] = float(wf_news(ev2).mean())
    wf_half = len(wf) // 2
    wf_h1 = float(wf.iloc[:wf_half].mean()) if wf_half else None
    wf_h2 = float(wf.iloc[wf_half:].mean()) if wf_half else None

    gates = {
        "|t_is|>2": is_s["t"] is not None and abs(is_s["t"]) > 2,
        "p_is<0.01": p_is < 0.01,
        "holdout NW t>2 & p<0.05": (ho_s["nw"] is not None and ho_s["nw"] > 2
                                    and p_ho < 0.05),
        "wf mean>0 & p_wf<0.05": (wf_s["mean"] is not None and wf_s["mean"] > 0
                                  and p_wf < 0.05),
        "bootstrap P(<=0)<0.05": bool(boot) and boot["p_leq_0"] < 0.05,
        "trimmed wf>0": wf_trim is not None and wf_trim > 0,
    }
    return {
        "key": f"news_{pair}", "label": f"News drift {pair} (z>=|{Z_THR}|, next-day open)",
        "is_mean": is_s["mean"], "is_t": is_s["t"], "is_nw": is_s["nw"],
        "is_win": is_s["win"], "is_trim": is_trim, "p_is": p_is,
        "ho_mean": ho_s["mean"], "ho_t": ho_s["t"], "ho_nw": ho_s["nw"],
        "ho_win": ho_s["win"], "p_ho": p_ho,
        "wf_mean": wf_s["mean"], "wf_t": wf_s["t"], "wf_win": wf_s["win"],
        "wf_n": wf_s["n"], "p_wf": p_wf,
        "boot_p50": boot.get("mean_p50"), "boot_p5": boot.get("mean_p5"),
        "boot_p95": boot.get("mean_p95"), "p_leq_0": boot.get("p_leq_0"),
        "wf_trim": wf_trim, "wf_h1": wf_h1, "wf_h2": wf_h2,
        "ladder_05": ladder[0.5], "ladder_1": ladder[1.0], "ladder_2": ladder[2.0],
        "VERDICT": "PASS" if all(gates.values()) else "FAIL",
        "gates": "; ".join(k for k, v in gates.items() if not v) or "all pass",
    }


def run_reversal_battery(pair: str, k: int) -> dict:
    c = load_d1(pair)["Close"]
    ret = c.pct_change().dropna()
    sig = -ret.rolling(k).sum()          # reversal signal
    pos = np.sign(sig).shift(1).fillna(0.0)   # entered NEXT bar (no lookahead)
    s = (pos * ret).dropna()
    cost = RT_PIPS * PIP[pair] / float(c.mean())
    is_s_raw = s.loc[:IS_END]
    if len(is_s_raw) < 200:
        return None
    d_is = 1 if is_s_raw.mean() > 0 else -1
    is_net = d_is * is_s_raw - cost
    is_stats = stats_series(is_net)
    is_trim = trimmed_mean_by_year(is_s_raw * d_is) if is_s_raw.index.year.nunique() >= 3 else float((is_s_raw * d_is).mean())
    oos_raw = s.loc[OOS_START:]
    oos_net = d_is * oos_raw - cost
    ho_stats = stats_series(oos_net)

    # permutations: random-signal null (flip sign randomly per day)
    p_is = perm_p_signflip(is_stats["mean"], is_s_raw.to_numpy(),
                           np.full(len(is_s_raw), d_is), cost)
    p_ho = perm_p_signflip(ho_stats["mean"], oos_raw.to_numpy(),
                           np.full(len(oos_raw), d_is), cost)

    wf = wf_reversal(s, cost)
    wf_s = stats_series(wf)
    wf_trim = trimmed_mean_by_year(wf) if len(wf) >= 3 else None
    p_wf = wf_perm_p_reversal(wf_s["mean"] if wf_s["mean"] is not None else -1e9,
                              s, ret, cost)
    boot = bootstrap_p(wf) if wf_s["mean"] is not None else {}
    ladder = {}
    for pips in (0.5, 1.0, 2.0):
        cst = pips * PIP[pair] / float(c.mean())
        ladder[pips] = float(wf_reversal(s, cst).mean())
    wf_half = len(wf) // 2
    wf_h1 = float(wf.iloc[:wf_half].mean()) if wf_half else None
    wf_h2 = float(wf.iloc[wf_half:].mean()) if wf_half else None

    gates = {
        "|t_is|>2": is_stats["t"] is not None and abs(is_stats["t"]) > 2,
        "p_is<0.01": p_is < 0.01,
        "holdout NW t>2 & p<0.05": (ho_stats["nw"] is not None and ho_stats["nw"] > 2
                                    and p_ho < 0.05),
        "wf mean>0 & p_wf<0.05": (wf_s["mean"] is not None and wf_s["mean"] > 0
                                  and p_wf < 0.05),
        "bootstrap P(<=0)<0.05": bool(boot) and boot["p_leq_0"] < 0.05,
        "trimmed wf>0": wf_trim is not None and wf_trim > 0,
    }
    return {
        "key": f"rev{k}_{pair}", "label": f"{k}-day reversal {pair}",
        "is_mean": is_stats["mean"], "is_t": is_stats["t"], "is_nw": is_stats["nw"],
        "is_win": is_stats["win"], "is_trim": is_trim,
        "p_is": p_is, "ho_mean": ho_stats["mean"], "ho_t": ho_stats["t"],
        "ho_nw": ho_stats["nw"], "ho_win": ho_stats["win"], "p_ho": p_ho,
        "wf_mean": wf_s["mean"], "wf_t": wf_s["t"], "wf_win": wf_s["win"],
        "wf_n": wf_s["n"], "p_wf": p_wf,
        "boot_p50": boot.get("mean_p50"), "boot_p5": boot.get("mean_p5"),
        "boot_p95": boot.get("mean_p95"), "p_leq_0": boot.get("p_leq_0"),
        "wf_trim": wf_trim, "wf_h1": wf_h1, "wf_h2": wf_h2,
        "ladder_05": ladder[0.5], "ladder_1": ladder[1.0], "ladder_2": ladder[2.0],
        "VERDICT": "PASS" if all(gates.values()) else "FAIL",
        "gates": "; ".join(k for k, v in gates.items() if not v) or "all pass",
    }


def main():
    events = load_big_events()
    print(f"big USD events (|z|>=0.5, expanding z): {len(events)}")
    rows = []
    for pair in CORE_PAIRS:
        r = run_news_battery(pair, events)
        if r:
            rows.append(r)
        print(f"  news {pair}: done", flush=True)
    for pair, k in (("AUDUSD", 1), ("EURGBP", 5)):
        r = run_reversal_battery(pair, k)
        if r:
            rows.append(r)
        print(f"  rev{k} {pair}: done", flush=True)

    lines = ["# FX STRICT BATTERY — news drift + reversal survivors",
             "_data D1 2016-08..2026-08 · events 2015.. · expanding per-title z · "
             "next-day-open entry · 1-pip RT cost · 1000-perm MC · 5000-bootstrap MC · "
             "walk-forward: news=3y profitability gate / reversal=504d direction_",
             "",
             f"## Candidates: {len(rows)}", ""]
    for r in rows:
        lines.append(f"## {r['label']} — {r['VERDICT']}\n")
        lines.append(f"- In-sample: mean {fmt_pct(r['is_mean'])}, t {fmt_t(r['is_t'])}, "
                     f"NW {fmt_t(r['is_nw'])}, win {fmt_win(r['is_win'])}, "
                     f"trimmed {fmt_pct(r['is_trim'])}")
        lines.append(f"  - In-sample permutation p = {r['p_is']:.4f} "
                     f"({'PASS' if r['p_is'] < 0.01 else 'FAIL'})")
        lines.append(f"- Holdout (2022+): mean {fmt_pct(r['ho_mean'])}, t {fmt_t(r['ho_t'])}, "
                     f"NW {fmt_t(r['ho_nw'])}, win {fmt_win(r['ho_win'])}, p {r['p_ho']:.4f}")
        lines.append(f"- Walk-forward (n={r['wf_n']}): mean {fmt_pct(r['wf_mean'])}, "
                     f"t {fmt_t(r['wf_t'])}, win {fmt_win(r['wf_win'])}")
        lines.append(f"  - Walk-forward permutation p = {r['p_wf']:.4f} "
                     f"({'PASS' if r['p_wf'] < 0.05 else 'FAIL'})")
        lines.append(f"  - Bootstrap: mean 5-50-95% = {fmt_pct(r['boot_p5'])} / "
                     f"{fmt_pct(r['boot_p50'])} / {fmt_pct(r['boot_p95'])}, "
                     f"P(mean<=0) = {r['p_leq_0']:.3f} "
                     f"({'PASS' if r['p_leq_0'] < 0.05 else 'FAIL'})")
        lines.append(f"  - Halves: {fmt_pct(r['wf_h1'])} / {fmt_pct(r['wf_h2'])}; "
                     f"trimmed wf {fmt_pct(r['wf_trim'])}")
        lines.append(f"  - Cost ladder (0.5/1/2 pips): {fmt_pct(r['ladder_05'])} / "
                     f"{fmt_pct(r['ladder_1'])} / {fmt_pct(r['ladder_2'])}")
        lines.append(f"  - Gates: {'ALL PASS' if r['VERDICT'] == 'PASS' else 'FAILED: ' + r['gates']}\n")

    lines.append("## Summary\n")
    lines.append("| key | label | is_t | p_is | ho_nw | p_ho | wf_mean | p_wf | "
                 "boot P(<=0) | trimmed | ladder 0.5/1/2 | verdict |")
    lines.append("|-----|-------|------|------|-------|------|---------|------|"
                 "------------|---------|----------------|---------|")
    for r in rows:
        lines.append(f"| {r['key']} | {r['label']} | {fmt_t(r['is_t'])} | {r['p_is']:.4f} | "
                     f"{fmt_t(r['ho_nw'])} | {r['p_ho']:.4f} | {fmt_pct(r['wf_mean'])} | "
                     f"{r['p_wf']:.4f} | {r['p_leq_0']:.3f} | {fmt_pct(r['wf_trim'])} | "
                     f"{fmt_pct(r['ladder_05'])}/{fmt_pct(r['ladder_1'])}/"
                     f"{fmt_pct(r['ladder_2'])} | {r['VERDICT']} |")
    lines.append("")
    lines.append("## What the numbers mean")
    lines.append("- **In-sample t / NW**: signal strength 2016-2021 (Newey-West lag-5). "
                 "High alone is cheap; that is why the rest exists.")
    lines.append("- **p_is**: 1000 sign-flip permutations — the chance that random "
                 "position signs reproduce the fit-window profit. p<0.01 is the gate.")
    lines.append("- **Holdout**: locked-direction 2022+ net of costs; NW t>2 and p<0.05 "
                 "mean the fit generalised forward.")
    lines.append("- **Walk-forward**: news — a year is traded only if the trailing-3y "
                 "event book was profitable (min 30 events), direction always the "
                 "surprise direction; reversal — direction re-estimated on trailing "
                 "504 days. No lookahead in either.")
    lines.append("- **p_wf**: 1000 random-day walk-forwards under identical machinery; "
                 "the chance a random calendar matches the actual walk-forward profit.")
    lines.append("- **Bootstrap P(mean<=0)**: 5000 resamples of the walk-forward years; "
                 "probability the true mean is non-positive. <0.05 is the strict bar.")
    lines.append("- **Trimmed**: best and worst year removed — a real effect survives.")
    lines.append("- **Ladder**: net at 0.5/1/2-pip round-trip costs; dying at 2 pips "
                 "means the edge is cost-dependent.")
    (OUT / "fx_strict_battery.md").write_text("\n".join(lines), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT / "fx_strict_battery.csv", index=False)
    print(f"battery done: {sum(1 for r in rows if r['VERDICT']=='PASS')}/{len(rows)} PASS")
    print("wrote reports/fx_strict_battery.md + fx_strict_battery.csv")


if __name__ == "__main__":
    main()
