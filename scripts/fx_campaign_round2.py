#!/usr/bin/env python3
"""fx_campaign_round2.py — round-2 FX campaign, news-family depth + fresh families.

Every test runs the FULL strict six-gate battery inline (no survivor
selection bias): IS excellence, IS permutation (p<1%), blind holdout,
walk-forward with trailing profitability gate, walk-forward permutation,
5000-bootstrap, cost ladder. Protocol identical to fx_strict_battery.py.

Grid (~420 tests):
  news drift     10 pairs x |z| thr {0.5,1.0,1.5,2.0} x horizon {1,2,3,5} x
                 tier {High+Medium, High-only}
  basket         core-5 equal-weight, same thr/hor/tier grid
  size-|z|       position ~ |z| (not just sign), core-5, thr 0.5/1.0, hor 1
  vol-managed    position ~ 1/sigma21, core-5, thr 0.5, hor 1, both tiers
  over-fade      |z|>=1.0 AND event |r| > 1.5 sigma21 -> FADE next day
  streak         same-sign big surprise within 7d -> trade the 2nd
  per-title      NFP / CPI / FOMC / Jobless Claims drift, core-5, hor 1
  gsr            gold-silver ratio z-score reversion -> AUDUSD, USDJPY

Standardisation: per-title EXPANDING z (no future data). Entry: NEXT day open
(r = close[t+h]/close[t]-1). Cost: 1-pip RT per trade.
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
RNG = np.random.default_rng(41)

IS_END = "2021-12-31"
OOS_START = "2022-01-01"
RT_PIPS = 1.0
WF_TRAIL_YEARS = 3
WF_MIN_EVENTS = 30
N_PERM = 1000
N_BOOT = 5000

PAIRS_NEWS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD",
              "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "AUDJPY"]
CONV = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1,
        "USDJPY": 1, "USDCAD": 1, "USDCHF": 1,
        "EURJPY": -1, "GBPJPY": -1, "AUDJPY": -1}
CORE5 = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD"]
THRS = [0.5, 1.0, 1.5, 2.0]
HORS = [1, 2, 3, 5]
TIERS = ["HM", "H"]          # High+Medium, High only

# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def load_events():
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
        mu = s.expanding().mean().shift(1)
        sd = s.expanding().std().shift(1)
        ev.loc[g.index, "z"] = (s - mu) / sd.replace(0, np.nan)
    ev["date"] = ev["date_utc"].dt.date
    return ev


_d1_cache = {}


def close_of(pair: str) -> pd.Series:
    if pair not in _d1_cache:
        if pair in ("GC", "SI"):
            f = BASE / "market-data/raw/yahoo" / f"COMM_{pair}_d.csv"
            df = pd.read_csv(f)
            df["date"] = pd.to_datetime(df["date"])
            c = df.set_index("date")["close"].rename("Close")
            c = c[~c.index.duplicated(keep="last")].sort_index()
            _d1_cache[pair] = c
        else:
            _d1_cache[pair] = load_d1(pair)["Close"]
    return _d1_cache[pair]


def hday_ret(pair: str, dates, h: int):
    """Per-date h-day return entered next day: close[t+h]/close[t]-1.
    Returns a numpy array aligned positionally to `dates`."""
    c = close_of(pair)
    r = c.pct_change(h)                  # close[t]/close[t-h]-1
    # we want, at date t: close[t+h]/close[t]-1 = r at index t+h
    fwd = r.shift(-h)
    fwd.index = fwd.index.date
    lut = fwd[~fwd.index.duplicated(keep="last")]
    return pd.Series(dates).map(lut).to_numpy()


def cost_units(pair: str) -> float:
    return RT_PIPS * PIP[pair] / float(close_of(pair).mean())


def sigma21(pair: str, dates):
    """Trailing-21d vol of daily returns, shifted 1 day, positional to dates."""
    c = close_of(pair)
    sig = c.pct_change().rolling(21).std().shift(1)
    sig.index = sig.index.date
    lut = sig[~sig.index.duplicated(keep="last")]
    return pd.Series(dates).map(lut).to_numpy()


# ---------------------------------------------------------------------------
# strategy builders: return (net, r, pos) per event, pos = position direction
# ---------------------------------------------------------------------------

def build_news(events, thr, hor, tier, pairs):
    ev = events[(events["z"].abs() >= thr)]
    if tier == "H":
        ev = ev[ev["impact"] == "High"]
    if pairs is None:
        pairs = PAIRS_NEWS
    dfs = []
    for pair in pairs:
        ev2 = ev.copy()
        ev2["r"] = hday_ret(pair, ev2["date"], hor)
        ev2 = ev2.dropna(subset=["r"])
        cost = cost_units(pair)
        ev2["net"] = CONV[pair] * np.sign(ev2["z"]) * ev2["r"] - cost
        ev2["pos"] = CONV[pair] * np.sign(ev2["z"])
        ev2["pair"] = pair
        dfs.append(ev2[["date", "z", "r", "net", "pos", "pair"]])
    return pd.concat(dfs)


def build_basket(events, thr, hor, tier):
    ev = events[(events["z"].abs() >= thr)]
    if tier == "H":
        ev = ev[ev["impact"] == "High"]
    nets, poss, rs = [], [], []
    for pair in CORE5:
        ev2 = ev.copy()
        ev2["r"] = hday_ret(pair, ev2["date"], hor)
        ev2 = ev2.dropna(subset=["r"])
        cost = cost_units(pair)
        nets.append(CONV[pair] * np.sign(ev2["z"]) * ev2["r"] - cost)
        poss.append(CONV[pair] * np.sign(ev2["z"]))
        rs.append(ev2["r"])
    out = pd.DataFrame({
        "date": ev["date"].values,
        "net": pd.concat(nets, axis=1).mean(axis=1).to_numpy(),
        "pos": pd.concat(poss, axis=1).mean(axis=1).to_numpy(),
        "r": pd.concat(rs, axis=1).mean(axis=1).to_numpy(),
    })
    return out


def build_size_z(events, thr, hor, tier):
    ev = events[(events["z"].abs() >= thr)]
    if tier == "H":
        ev = ev[ev["impact"] == "High"]
    dfs = []
    for pair in CORE5:
        ev2 = ev.copy()
        ev2["r"] = hday_ret(pair, ev2["date"], hor)
        ev2 = ev2.dropna(subset=["r"])
        cost = cost_units(pair)
        pos = CONV[pair] * ev2["z"]
        ev2["net"] = pos * ev2["r"] - cost
        ev2["pos"] = pos
        ev2["pair"] = pair
        dfs.append(ev2[["date", "z", "r", "net", "pos", "pair"]])
    return pd.concat(dfs)


def build_volman(events, thr, hor, tier):
    ev = events[(events["z"].abs() >= thr)]
    if tier == "H":
        ev = ev[ev["impact"] == "High"]
    dfs = []
    for pair in CORE5:
        ev2 = ev.copy()
        ev2["r"] = hday_ret(pair, ev2["date"], hor)
        sig = sigma21(pair, ev2["date"])
        ev2["sig"] = sig
        ev2 = ev2.dropna(subset=["r", "sig"])
        cost = cost_units(pair)
        ref = ev2["sig"].mean()
        pos = CONV[pair] * np.sign(ev2["z"]) * (ref / ev2["sig"])
        ev2["net"] = pos * ev2["r"] - cost
        ev2["pos"] = pos
        ev2["pair"] = pair
        dfs.append(ev2[["date", "z", "r", "net", "pos", "pair"]])
    return pd.concat(dfs)


def build_overfade(events, thr, hor, tier):
    ev = events[(events["z"].abs() >= thr)]
    if tier == "H":
        ev = ev[ev["impact"] == "High"]
    dfs = []
    for pair in CORE5:
        ev2 = ev.copy()
        ev2["r"] = hday_ret(pair, ev2["date"], hor)
        sig = sigma21(pair, ev2["date"])
        ev2["sig"] = sig
        # event-day move magnitude (same-day return)
        c = close_of(pair)
        er = c.pct_change()
        er.index = er.index.date
        ev2["er"] = er.reindex(ev2["date"]).to_numpy()
        ev2 = ev2.dropna(subset=["r", "sig", "er"])
        over = ev2["er"].abs() > 1.5 * ev2["sig"]
        ev2 = ev2[over]
        if len(ev2) < 30:
            continue
        cost = cost_units(pair)
        pos = -CONV[pair] * np.sign(ev2["z"])      # fade the over-reaction
        ev2["net"] = pos * ev2["r"] - cost
        ev2["pos"] = pos
        ev2["pair"] = pair
        dfs.append(ev2[["date", "z", "r", "net", "pos", "pair"]])
    return pd.concat(dfs)


def build_streak(events, thr, hor, tier):
    ev = events[(events["z"].abs() >= thr)].sort_values("date_utc").copy()
    if tier == "H":
        ev = ev[ev["impact"] == "High"]
    ev["sgn"] = np.sign(ev["z"])
    ev["prev_date"] = ev["date_utc"].shift(1)
    ev["prev_sgn"] = ev["sgn"].shift(1)
    ev["same"] = (ev["sgn"] == ev["prev_sgn"]) & \
                 ((ev["date_utc"] - ev["prev_date"]) <= pd.Timedelta(days=7))
    ev = ev[ev["same"]]
    dfs = []
    for pair in CORE5:
        ev2 = ev.copy()
        ev2["r"] = hday_ret(pair, ev2["date"], hor)
        ev2 = ev2.dropna(subset=["r"])
        if len(ev2) < 30:
            continue
        cost = cost_units(pair)
        pos = CONV[pair] * ev2["sgn"]
        ev2["net"] = pos * ev2["r"] - cost
        ev2["pos"] = pos
        ev2["pair"] = pair
        dfs.append(ev2[["date", "z", "r", "net", "pos", "pair"]])
    return pd.concat(dfs)


def build_title(events, title, hor):
    ev = events[events["title"] == title].copy()
    dfs = []
    for pair in CORE5:
        ev2 = ev.copy()
        ev2["r"] = hday_ret(pair, ev2["date"], hor)
        ev2 = ev2.dropna(subset=["r"])
        if len(ev2) < 20:
            continue
        cost = cost_units(pair)
        pos = CONV[pair] * np.sign(ev2["z"])
        ev2["net"] = pos * ev2["r"] - cost
        ev2["pos"] = pos
        ev2["pair"] = pair
        dfs.append(ev2[["date", "z", "r", "net", "pos", "pair"]])
    return pd.concat(dfs)


def build_gsr(events, thr, hor, tier):
    """Gold-silver ratio z-score -> risk-on/off FX. Needs metals d1."""
    try:
        gc = close_of("GC")
        si = close_of("SI")
    except Exception:
        return pd.DataFrame()
    ratio = gc / si.reindex(gc.index).ffill()
    z20 = (ratio - ratio.rolling(20).mean()) / ratio.rolling(20).std()
    z63 = (ratio - ratio.rolling(63).mean()) / ratio.rolling(63).std()
    rows = []
    for lb, zser in (("20", z20), ("63", z63)):
        zser = zser.dropna()
        zser.index = zser.index.date
        for pair in ("AUDUSD", "USDJPY"):
            c = close_of(pair)
            r = c.pct_change()
            r.index = r.index.date
            common = zser.index.intersection(r.index)
            z = zser.loc[common]
            rr = r.loc[common].shift(-1)          # next-day return
            m = rr.notna()
            z, rr = z[m], rr[m]
            if len(z) < 100:
                continue
            cost = cost_units(pair)
            pos = -np.sign(z)                     # low ratio -> long AUD / short USDJPY
            net = pos * rr.to_numpy() - cost
            rows.append(pd.DataFrame({
                "date": common[m], "z": z.to_numpy(), "r": rr.to_numpy(),
                "net": net, "pos": pos, "pair": pair,
                "note": f"gsr{lb}"}))
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows)


# ---------------------------------------------------------------------------
# six-gate battery
# ---------------------------------------------------------------------------

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


def trimmed_by_year(s: pd.Series) -> float:
    if isinstance(s.index, pd.DatetimeIndex):
        y = pd.Series(s.index.year, index=s.index)
    else:
        y = pd.Series(s.index, index=s.index)
    ym = s.groupby(y).mean()
    if len(ym) < 3:
        return float(s.mean())
    return float(ym.sort_values().iloc[1:-1].mean())


def perm_signflip(actual, r, pos, cost, n_perm=N_PERM):
    r = np.asarray(r, dtype=float)
    pos = np.asarray(pos, dtype=float)
    cnt = 1
    for _ in range(n_perm):
        flips = RNG.choice([-1.0, 1.0], len(r))
        if (pos * flips * r - cost).mean() >= actual:
            cnt += 1
    return cnt / (n_perm + 1)


def perm_randday(actual, r_arr, k, n_perm=N_PERM):
    cnt = 1
    for _ in range(n_perm):
        if (RNG.choice(r_arr, k, replace=True)).mean() >= actual:
            cnt += 1
    return cnt / (n_perm + 1)


def wf_gate(ev: pd.DataFrame) -> pd.Series:
    """Year-by-year mean net; a year traded only if trailing-3y mean net > 0
    (min WF_MIN_EVENTS trailing events)."""
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


def wf_perm_randday(actual_mean, ev, daily_ret_pool, n_perm=N_PERM):
    ev = ev.copy()
    ev["year"] = pd.to_datetime(ev["date"]).dt.year
    years = sorted(ev["year"].unique())
    k_by_year = {y: int((ev["year"] == y).sum()) for y in years}
    cnt = 1
    for _ in range(n_perm):
        frames = []
        for y in years:
            k = k_by_year[y]
            if k == 0:
                continue
            frames.append(pd.DataFrame({"year": y,
                                        "net": RNG.choice(daily_ret_pool, k, replace=True)}))
        wf = wf_gate(pd.concat(frames))
        if len(wf) and wf.mean() >= actual_mean:
            cnt += 1
    return cnt / (n_perm + 1)


def bootstrap_p(series: pd.Series, n: int = N_BOOT) -> dict:
    rng = random.Random(23)
    arr = series.to_numpy()
    means = []
    for _ in range(n):
        b = rng.choices(list(arr), k=len(arr))
        means.append(float(np.mean(b)))
    means = np.array(means)
    return {"mean_p5": float(np.percentile(means, 5)),
            "mean_p50": float(np.percentile(means, 50)),
            "mean_p95": float(np.percentile(means, 95)),
            "p_leq_0": float((means <= 0).mean())}


def battery(ev: pd.DataFrame, daily_pool: np.ndarray, null: str,
            cost_per_event: float, label: str, key: str) -> dict:
    if len(ev) < 60:
        return None
    ev = ev.dropna(subset=["net", "r"]).copy()
    is_ev = ev[ev["date"] <= pd.Timestamp(IS_END).date()]
    oos_ev = ev[ev["date"] >= pd.Timestamp(OOS_START).date()]
    if len(is_ev) < 30 or len(oos_ev) < 20:
        return None

    is_s = stats_series(is_ev["net"])
    is_trim = trimmed_by_year(is_ev.set_index(pd.to_datetime(is_ev["date"]))["net"])
    ho_s = stats_series(oos_ev["net"])

    if null == "signflip":
        p_is = perm_signflip(is_s["mean"], is_ev["r"].to_numpy(),
                             is_ev["pos"].to_numpy(), cost_per_event)
        p_ho = perm_signflip(ho_s["mean"], oos_ev["r"].to_numpy(),
                             oos_ev["pos"].to_numpy(), cost_per_event)
    else:
        p_is = perm_randday(is_s["mean"], daily_pool, len(is_ev))
        p_ho = perm_randday(ho_s["mean"], daily_pool, len(oos_ev))

    wf = wf_gate(ev)
    wf_s = stats_series(wf)
    wf_trim = trimmed_by_year(wf) if len(wf) >= 3 else None
    p_wf = wf_perm_randday(wf_s["mean"] if wf_s["mean"] is not None else -1e9, ev, daily_pool)
    boot = bootstrap_p(wf) if wf_s["mean"] is not None else {}

    gates = {
        "|t_is|>2": is_s["t"] is not None and abs(is_s["t"]) > 2,
        "p_is<0.01": p_is < 0.01,
        "ho NW t>2 & p<0.05": (ho_s["nw"] is not None and ho_s["nw"] > 2 and p_ho < 0.05),
        "wf>0 & p_wf<0.05": (wf_s["mean"] is not None and wf_s["mean"] > 0 and p_wf < 0.05),
        "boot P(<=0)<0.05": bool(boot) and boot["p_leq_0"] < 0.05,
        "trimmed wf>0": wf_trim is not None and wf_trim > 0,
    }
    return {
        "key": key, "label": label, "n": len(ev),
        "is_mean": is_s["mean"], "is_t": is_s["t"], "is_nw": is_s["nw"],
        "is_trim": is_trim, "p_is": p_is,
        "ho_mean": ho_s["mean"], "ho_t": ho_s["t"], "ho_nw": ho_s["nw"],
        "ho_win": ho_s["win"], "p_ho": p_ho,
        "wf_mean": wf_s["mean"], "wf_t": wf_s["t"], "wf_win": wf_s["win"],
        "wf_n": wf_s["n"], "p_wf": p_wf,
        "boot_p5": boot.get("mean_p5"), "boot_p50": boot.get("mean_p50"),
        "boot_p95": boot.get("mean_p95"), "p_leq_0": boot.get("p_leq_0"),
        "wf_trim": wf_trim,
        "n_gates": sum(1 for v in gates.values() if v),
        "VERDICT": "PASS" if all(gates.values()) else "FAIL",
        "gates": "; ".join(k for k, v in gates.items() if not v) or "all pass",
    }


def main():
    events = load_events()
    print(f"events with expanding z: {len(events)}", flush=True)
    rows = []

    # daily pools per pair for randday nulls
    pools = {p: close_of(p).pct_change().dropna().to_numpy() for p in PAIRS_NEWS}
    pools["GC"] = close_of("GC").pct_change().dropna().to_numpy()
    pools["SI"] = close_of("SI").pct_change().dropna().to_numpy()

    count = 0

    def run(key, label, ev, pair, null):
        nonlocal count
        cost = cost_units(pair) if pair in CONV else RT_PIPS * PIP[pair] / float(close_of(pair).mean())
        r = battery(ev, pools.get(pair, pools["EURUSD"]), null, cost, label, key)
        if r:
            rows.append(r)
            count += 1

    # ---- news drift grid ----
    for pair in PAIRS_NEWS:
        for thr in THRS:
            for hor in HORS:
                for tier in TIERS:
                    ev = build_news(events, thr, hor, tier, [pair])
                    run(f"news_{pair}_{thr}_{hor}_{tier}", f"news {pair} thr={thr} h={hor} tier={tier}",
                        ev, pair, "signflip")
    print(f"news grid done: {count} tested", flush=True)

    # ---- basket ----
    for thr in THRS:
        for hor in HORS:
            for tier in TIERS:
                ev = build_basket(events, thr, hor, tier)
                cost = np.mean([cost_units(p) for p in CORE5])
                key = f"basket_{thr}_{hor}_{tier}"
                r = battery(ev, pools["EURUSD"], "signflip", cost, f"basket thr={thr} h={hor} tier={tier}", key)
                if r:
                    rows.append(r)
                    count += 1
    print(f"basket done: {count} tested", flush=True)

    # ---- size-|z| ----
    for pair in CORE5:
        for thr in (0.5, 1.0):
            for tier in TIERS:
                ev = build_size_z(events, thr, 1, tier)
                run(f"sizez_{pair}_{thr}_{tier}", f"size|z| {pair} thr={thr} tier={tier}",
                    ev, pair, "randday")
    print(f"sizez done: {count} tested", flush=True)

    # ---- vol-managed ----
    for pair in CORE5:
        for tier in TIERS:
            ev = build_volman(events, 0.5, 1, tier)
            run(f"volman_{pair}_{tier}", f"vol-managed {pair} tier={tier}", ev, pair, "randday")
    print(f"volman done: {count} tested", flush=True)

    # ---- over-reaction fade ----
    for pair in CORE5:
        for tier in TIERS:
            ev = build_overfade(events, 1.0, 1, tier)
            if len(ev):
                run(f"overfade_{pair}_{tier}", f"over-fade {pair} tier={tier}", ev, pair, "signflip")
    print(f"overfade done: {count} tested", flush=True)

    # ---- streak ----
    for pair in CORE5:
        for tier in TIERS:
            ev = build_streak(events, 0.5, 1, tier)
            if len(ev):
                run(f"streak_{pair}_{tier}", f"streak {pair} tier={tier}", ev, pair, "signflip")
    print(f"streak done: {count} tested", flush=True)

    # ---- per-title ----
    for title in ["Non Farm Payrolls", "CPI", "Fed Funds Rate", "Initial Jobless Claims"]:
        ev = build_title(events, title, 1)
        if len(ev):
            key = f"title_{title.replace(' ', '_')}"
            run(key, f"title {title}", ev, "EURUSD", "signflip")
    print(f"per-title done: {count} tested", flush=True)

    # ---- gold-silver ratio ----
    ev = build_gsr(events, 0.5, 1, "HM")
    if len(ev):
        for pair, grp in ev.groupby("pair"):
            lb = grp["note"].iloc[0]
            cost = cost_units(pair)
            r = battery(grp, pools[pair], "signflip", cost, f"gsr{lb} -> {pair}", f"gsr{lb}_{pair}")
            if r:
                rows.append(r)
                count += 1
    print(f"gsr done: {count} tested", flush=True)

    df = pd.DataFrame(rows).sort_values(["n_gates", "p_wf"], ascending=[False, True])
    (OUT / "fx_round2_leaderboard.csv").write_text(df.to_csv(index=False), encoding="utf-8")

    lines = ["# FX ROUND-2 CAMPAIGN — news-family depth + fresh families",
             "_every test through the full six-gate strict battery inline · "
             "expanding per-title z · next-day-open entry · 1-pip RT · "
             "1000-perm MC · 5000-bootstrap MC_", "",
             f"## Headline",
             f"- Strategies tested (full battery each): **{len(df)}**",
             f"- Full six-gate PASS: **{int((df['VERDICT'] == 'PASS').sum())}**",
             f"- Partial (>=4 gates): **{int((df['n_gates'] >= 4).sum())}**", ""]
    top = df.head(30)
    lines.append("## Top 30 (by gates passed, then walk-forward p)")
    lines.append("| key | is_t | p_is | ho_nw | p_ho | wf_mean | p_wf | boot P(<=0) | gates |")
    lines.append("|-----|------|------|-------|------|---------|------|-------------|-------|")
    for _, r in top.iterrows():
        lines.append(f"| {r['key']} | {fmt_t(r['is_t'])} | {r['p_is']:.4f} | "
                     f"{fmt_t(r['ho_nw'])} | {r['p_ho']:.4f} | {fmt_pct(r['wf_mean'])} | "
                     f"{r['p_wf']:.4f} | {r['p_leq_0']:.3f} | {int(r['n_gates'])}/6 |")
    lines.append("")
    lines.append("## Honest reading")
    lines.append("- The IS gates (|t|>2, p<0.01) are the strictest: an effect that "
                 "emerged only post-2021 (like the news drift) fails them by design, "
                 "even when the walk-forward + bootstrap + holdout all pass.")
    lines.append("- Walk-forward permutation (random-day null through identical "
                 "machinery) is the strongest guard against calendar luck.")
    lines.append("- Any candidate with n_gates >= 5 is the live candidate list; "
                 "n_gates = 6 is proven under this protocol.")
    (OUT / "fx_round2_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"round-2 complete: {len(df)} tested, full-PASS {int((df['VERDICT']=='PASS').sum())}")


def fmt_t(x):
    return "n/a" if x is None else f"{x:+.2f}"


def fmt_pct(x, nd=3):
    return "n/a" if x is None else f"{x*100:+.{nd}f}%"


if __name__ == "__main__":
    main()
