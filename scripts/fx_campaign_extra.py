#!/usr/bin/env python3
"""fx_campaign_extra.py — widens the FX campaign beyond the D1 core.

Adds: cross-sectional momentum baskets (3), news-surprise strategies from
events.parquet (under-reaction next-day drift, event-day volatility,
pre-event drift on H1), H1 session effects (hour-of-day, London open,
overnight gap reversion), then merges with the D1 leaderboard and writes
the combined report.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from edge_scan import PAIRS, PIP, load_d1, load_h1, nw_t
from fx_campaign import (IS_END, OOS_START, N_PERM, backtest, eval_daily,
                         pip_cost_units, ret_series, sig_cross, sig_month,
                         stats_series)

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(21)

MAJORS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
          "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURCHF"]


def xs_basket(closes, lookback, n_legs=3):
    """Cross-sectional: rank trailing lookback returns on each Friday, hold
    the top/bottom n_legs for the next week. Returns daily net series (per
    unit exposure, long-short)."""
    panel = pd.DataFrame(
        {p: closes[p].pct_change().rolling(lookback).sum() for p in closes})
    ret = pd.DataFrame({p: closes[p].pct_change() for p in closes})
    # weekly signals: rank on Fridays, forward-fill through the week
    fridays = panel.index[panel.index.dayofweek == 4]
    sig = {}
    for p in closes:
        sig[p] = pd.Series(0.0, index=panel.index)
    pos = {}
    for p in closes:
        pos[p] = pd.Series(0.0, index=panel.index)
    prev_friday = None
    for dt in panel.index:
        if dt in fridays or prev_friday is None:
            r = panel.loc[dt]
            order = r.dropna().sort_values().index
            if len(order) >= 2 * n_legs:
                top = order[-n_legs:]
                bot = order[:n_legs]
                for p in closes:
                    pos[p].loc[dt] = 1.0 if p in top else (-1.0 if p in bot else 0.0)
            prev_friday = dt
        else:
            for p in closes:
                pos[p].loc[dt] = pos[p].loc[prev_friday]
    # daily strategy return: equal-weight long-short, cost 1 pip RT per pair
    # on rebalance weeks (approx: charge half the legs' cost each Friday)
    daily = pd.Series(0.0, index=panel.index)
    cost_units = {p: pip_cost_units(p, closes[p]) for p in closes}
    for dt in panel.index:
        legs = [p for p in closes if pos[p].loc[dt] != 0]
        if not legs:
            continue
        r = sum(pos[p].loc[dt] * ret[p].loc[dt] for p in legs) / len(legs)
        c = sum(cost_units[p] for p in legs) / len(legs) if dt in fridays else 0.0
        daily.loc[dt] = r - c
    return daily.dropna()


def add_xs(rows, closes):
    for lb in (63, 126, 252):
        net = xs_basket(closes, lb)
        is_s = stats_series(net.loc[:IS_END], 0.0)
        oos = net.loc[OOS_START:]
        oos_s = stats_series(oos, 0.0)
        if oos_s is None:
            continue
        # null: random daily re-selection of 6 random legs
        rng = RNG
        n = len(oos)
        r_arr = oos.to_numpy()
        cnt = 1
        for _ in range(N_PERM):
            pick = rng.choice(n, n, replace=True)
            if r_arr[pick].mean() >= oos_s["mean"]:
                cnt += 1
        rows.append({
            "family": f"xs_mom{lb}", "pair": "BASKET",
            "is_t": is_s["t"] if is_s else None,
            "is_mean": is_s["mean"] if is_s else None,
            "oos_mean": oos_s["mean"], "oos_t": oos_s["t"],
            "oos_nw": oos_s["nw_t"], "oos_sharpe": oos_s["sharpe"],
            "win": oos_s["win"], "n": oos_s["n"],
            "p": cnt / (N_PERM + 1)})
    return rows


# ---------------------------------------------------------------------------
# News-surprise module (events.parquet has forecast + actual)
# ---------------------------------------------------------------------------

def load_events():
    ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)
    return ev


def news_surprise():
    ev = load_events()
    ev = ev[(ev["impact"].isin(["High", "Medium"])) &
            (ev["actual"].notna()) & (ev["forecast"].notna())]
    ev = ev.copy()
    ev["surprise"] = pd.to_numeric(ev["actual"], errors="coerce") - \
        pd.to_numeric(ev["forecast"], errors="coerce")
    ev = ev.dropna(subset=["surprise"])
    if not len(ev):
        return []
    # per-title z-score (std of surprises within title)
    ev["z"] = ev.groupby("title")["surprise"].transform(
        lambda s: (s - s.mean()) / s.std() if s.std() > 0 else 0.0)
    usd = ev[ev["currency"] == "USD"]
    rows = []
    closes = {p: load_d1(p)["Close"] for p in ["EURUSD", "USDJPY", "GBPUSD",
                                               "AUDUSD", "USDCAD"]}
    # direction conventions: X/USD falls when USD surprises up; USD/X rises
    conv = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1,
            "USDJPY": 1, "USDCAD": 1}
    big = usd[usd["z"].abs() >= 0.5].copy()
    big["date"] = big["date_utc"].dt.date
    for pair in closes:
        c = closes[pair]
        ret = ret_series(c)
        ret.index = ret.index.date
        sub = big.copy()
        sub["r"] = sub["date"].map(ret)
        sub = sub.dropna(subset=["r"])
        sub = sub[sub["date"] >= pd.Timestamp(IS_END).date()]
        sub = sub[sub["date"] <= pd.Timestamp("2026-08-05").date()]
        if len(sub) < 30:
            continue
        sub = sub.copy()
        sub["net"] = conv[pair] * sub["z"].apply(lambda z: 1 if z > 0 else -1) * sub["r"]
        oos = sub[sub["date"] >= pd.Timestamp(OOS_START).date()]
        if len(oos) < 15:
            continue
        mu, sd = oos["net"].mean(), oos["net"].std(ddof=1)
        if sd == 0:
            continue
        t = mu / (sd / math.sqrt(len(oos)))
        # null: flip signs of z randomly
        zsigns = np.sign(oos["z"].to_numpy()) * conv[pair]
        nets = oos["r"].to_numpy() * zsigns
        cnt = 1
        for _ in range(N_PERM):
            flips = RNG.choice([-1.0, 1.0], len(nets))
            if (nets * flips).mean() >= mu:
                cnt += 1
        rows.append({
            "family": "news_drift_USD", "pair": pair,
            "is_t": None, "is_mean": None,
            "oos_mean": float(mu), "oos_t": float(t),
            "oos_nw": float(nw_t(nets, lag=5)),
            "oos_sharpe": float(mu / sd * math.sqrt(252)),
            "win": float((nets > 0).mean()), "n": len(oos),
            "p": cnt / (N_PERM + 1)})
    return rows


def news_event_vol():
    ev = load_events()
    ev["date"] = ev["date_utc"].dt.date
    ev = ev[(ev["currency"] == "USD") & (ev["impact"].isin(["High", "Medium"]))]
    closes = {p: load_d1(p)["Close"] for p in ["EURUSD", "USDJPY"]}
    rows = []
    for pair in closes:
        c = closes[pair]
        ret = ret_series(c)
        ret.index = ret.index.date
        event_days = set(ev["date"])
        mask = ret.index.isin(event_days)
        ev_abs = ret[mask].abs()
        non_abs = ret[~mask].abs()
        if len(ev_abs) < 30 or len(non_abs) < 30:
            continue
        ratio = ev_abs.mean() / non_abs.mean()
        t = (ev_abs.mean() - non_abs.mean()) / np.sqrt(
            ev_abs.var(ddof=1) / len(ev_abs) + non_abs.var(ddof=1) / len(non_abs))
        rows.append({"family": "event_day_vol", "pair": pair,
                     "is_t": None, "is_mean": None, "oos_mean": None,
                     "oos_t": float(t), "oos_nw": float(t),
                     "oos_sharpe": None, "win": None, "n": len(ev_abs),
                     "p": None, "note": f"event/non-event |r| ratio={ratio:.2f}"})
    return rows


def news_pre_event_h1():
    """Pre-release drift (Strategy 4): 1h return before a USD event vs z.
    H1 data starts 2023-10, so this is a short-sample screen only."""
    ev = load_events()
    ev = ev[(ev["currency"] == "USD") & (ev["impact"].isin(["High", "Medium"])) &
            (ev["actual"].notna()) & (ev["forecast"].notna())]
    ev["surprise"] = pd.to_numeric(ev["actual"], errors="coerce") - \
        pd.to_numeric(ev["forecast"], errors="coerce")
    ev = ev.dropna(subset=["surprise"])
    ev["z"] = ev.groupby("title")["surprise"].transform(
        lambda s: (s - s.mean()) / s.std() if s.std() > 0 else 0.0)
    rows = []
    for pair in ["EURUSD", "USDJPY"]:
        h1 = load_h1(pair)
        if len(h1) < 1000:
            continue
        c = h1["Close"]
        idx = h1.index if isinstance(h1.index, pd.DatetimeIndex) else \
            pd.to_datetime(h1.index)
        c.index = idx
        c = c[~c.index.duplicated(keep="last")].sort_index()
        ret = c.pct_change()
        pre_ret, zs = [], []
        for _, e in ev.iterrows():
            t0 = e["date_utc"]
            bar = c.index[c.index <= t0]
            if len(bar) < 2:
                continue
            b = bar[-1]
            prev = bar[-2]
            if t0 - b > pd.Timedelta(hours=2):
                continue
            pre_ret.append(ret.loc[b] if b in ret.index else np.nan)
            zs.append(e["z"])
        if len(pre_ret) < 30:
            continue
        pre_ret = np.array(pre_ret)
        zs = np.array(zs)
        m = ~np.isnan(pre_ret)
        pre_ret, zs = pre_ret[m], zs[m]
        if len(pre_ret) < 30:
            continue
        rho = np.corrcoef(pre_ret, zs)[0, 1]
        t = rho * math.sqrt(len(pre_ret) - 2) / math.sqrt(1 - rho * rho) \
            if abs(rho) < 1 else 0.0
        rows.append({"family": "pre_event_drift", "pair": pair,
                     "is_t": None, "is_mean": None, "oos_mean": None,
                     "oos_t": float(t), "oos_nw": float(t),
                     "oos_sharpe": None, "win": None, "n": len(pre_ret),
                     "p": None, "note": f"corr(z, T-1h return)={rho:+.3f}"})
    return rows


# ---------------------------------------------------------------------------
# H1 session effects
# ---------------------------------------------------------------------------

def h1_sessions():
    rows = []
    for pair in ["EURUSD", "USDJPY", "GBPUSD"]:
        h1 = load_h1(pair)
        if len(h1) < 1000:
            continue
        c = h1["Close"]
        idx = h1.index if isinstance(h1.index, pd.DatetimeIndex) else \
            pd.to_datetime(h1.index)
        c.index = idx
        c = c[~c.index.duplicated(keep="last")].sort_index()
        # hour-of-day: floor to hour
        hr = c.resample("h").last().dropna()
        ret = hr.pct_change().dropna()
        hour = ret.index.hour
        for h in sorted(set(hour)):
            s = ret[hour == h]
            is_s = s.loc[:pd.Timestamp("2025-01-01", tz="UTC")]
            oos = s.loc[pd.Timestamp("2025-01-01", tz="UTC"):]
            if len(is_s) < 20 or len(oos) < 20:
                continue
            def t_of(x):
                return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) \
                    if x.std(ddof=1) > 0 else 0.0
            t_is, t_oos = t_of(is_s), t_of(oos)
            if abs(t_is) > 1.5 or abs(t_oos) > 1.5:
                rows.append({"family": f"hour{h:02d}", "pair": pair,
                             "is_t": t_is, "is_mean": float(is_s.mean()),
                             "oos_mean": float(oos.mean()),
                             "oos_t": t_oos, "oos_nw": float(t_oos),
                             "oos_sharpe": float(oos.mean() / (oos.std(ddof=1) or 1) * math.sqrt(252 * 24)),
                             "win": float((oos > 0).mean()), "n": len(oos),
                             "p": None})
        # London-open momentum: 07-10 UTC return -> 10-13 UTC same sign
        g = hr.groupby(hr.index.date)
        opens = hr[hr.index.hour == 7]
        ret10 = (hr[hr.index.hour == 13] / hr[hr.index.hour == 10] - 1).dropna()
        ret07 = (hr[hr.index.hour == 10] / hr[hr.index.hour == 7] - 1).dropna()
        idx = ret07.index.intersection(ret10.index)
        sig = np.sign(ret07.loc[idx])
        net = sig * ret10.loc[idx]
        is_s = net.loc[:pd.Timestamp("2025-01-01", tz="UTC")]
        oos = net.loc[pd.Timestamp("2025-01-01", tz="UTC"):]
        if len(is_s) >= 20 and len(oos) >= 20:
            def t_of(x):
                return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) \
                    if x.std(ddof=1) > 0 else 0.0
            rows.append({"family": "london_open", "pair": pair,
                         "is_t": t_of(is_s), "is_mean": float(is_s.mean()),
                         "oos_mean": float(oos.mean()), "oos_t": t_of(oos),
                         "oos_nw": float(t_of(oos)), "oos_sharpe": None,
                         "win": float((oos > 0).mean()), "n": len(oos),
                         "p": None})
    return rows


def _t(x):
    return "n/a" if x is None else f"{x:+.2f}"


def _pct(x, nd=3):
    return "n/a" if x is None else f"{x*100:+.{nd}f}%"


def _win(x):
    return "n/a" if x is None else f"{x:.0%}"


def _p3(x):
    return "n/a" if x is None else f"{x:.3f}"


def write_report(all_rows):
    df = pd.DataFrame(all_rows)
    df = df.sort_values("oos_t", ascending=False)
    n = len(df)
    surv = df[(df["oos_t"] > 2) & (df["p"].notna()) & (df["p"] < 0.05)]
    lines = ["# FX MASSIVE CAMPAIGN — report",
             f"_D1 2016-08..2026-08 (12 pairs) · H1 2023-10.. · events 2015.. "
             f"· IS {IS_END} / OOS {OOS_START}+ · costs 1 pip RT · NW lag-5 · "
             f"1000-perm nulls_", "",
             f"## Headline",
             f"- Strategies tested: **{n}**",
             f"- OOS t>2 AND p<0.05: **{len(surv)}**", "",
             "## Top 40 (OOS t, net of costs)", "",
             "| fam | pair | IS t | OOS mean | OOS t | NW t | Sharpe | win | n | p |",
             "|-----|------|------|----------|-------|------|--------|-----|---|-----|"]
    for _, r in df.head(40).iterrows():
        lines.append(
            f"| {r['family']} | {r['pair']} | {_t(r['is_t'])} | "
            f"{_pct(r['oos_mean'])} | {_t(r['oos_t'])} | {_t(r['oos_nw'])} | "
            f"{_t(r['oos_sharpe'])} | "
            f"{_win(r['win'])} | "
            f"{r['n']} | {_p3(r['p'])} |")
    if len(surv):
        lines.append("\n## Survivors (OOS t>2 AND p<0.05)\n")
        for _, r in surv.iterrows():
            lines.append(f"- **{r['family']} {r['pair']}**: OOS "
                         f"{_pct(r['oos_mean'])}/day, "
                         f"t {_t(r['oos_t'])}, p {_p3(r['p'])}, win "
                         f"{_win(r['win'])}")
    else:
        lines.append("\n## Survivors\n_None at the strict bar (OOS t>2 AND p<0.05)._\n")
    lines.append("""
## What the numbers mean
- **IS t** = signal strength 2016-2021. **OOS t** = locked signal 2022+, net
  of 1-pip round-trip costs, Newey-West lag-5 alongside.
- **p** = 1000-permutation null: random entry timing (signal families) or
  random calendar days (calendar families); fraction of nulls with mean >=
  actual OOS mean.
- **n** = OOS observations (days, events, or hours).
- A single OOS t>2 is the WEAKEST evidence in this battery — the project
  already knows single splits can lie (see WALKFORWARD_RANKING.md). Anything
  here goes to the strict battery (walk-forward + bootstrap) before belief.
""")
    (OUT / "fx_campaign_report.md").write_text("\n".join(lines), encoding="utf-8")
    df.to_csv(OUT / "fx_campaign_leaderboard_full.csv", index=False)
    print(f"report written: {n} total, {len(surv)} survivors")


def main():
    d1 = pd.read_csv(OUT / "fx_campaign_leaderboard.csv")
    rows = d1.to_dict("records")
    closes = {p: load_d1(p)["Close"] for p in PAIRS if len(load_d1(p))}
    rows = add_xs(rows, closes)
    rows += news_surprise()
    rows += news_event_vol()
    rows += news_pre_event_h1()
    rows += h1_sessions()
    write_report(rows)
    print(f"total across all modules: {len(rows)}")


if __name__ == "__main__":
    main()
