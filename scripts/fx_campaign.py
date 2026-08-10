#!/usr/bin/env python3
"""fx_campaign.py — massive FX strategy campaign (wider than edge_scan v1).

Universe: 12 FX pairs, D1 2016-08..2026-08 (~2,600 bars) + H1 2023-10..
Cross-asset signals: SP500, OIL, GOLD, BTCUSD d1.

Protocol (project standard):
  IS = 2016-08..2021-12, OOS = 2022-01..2026-08 (untouched).
  Cost = 1 pip round-trip (0.5/side) charged per position flip, in return
  units at the pair's mean close.
  t-stats: naive + Newey-West (lag 5).
  Null: 1000 permutations. For signal families, random ±1 signals with the
  true flip frequency; for calendar families, random same-count day subsets.
  p = (#null means >= actual OOS mean + 1)/1001.

Families (each x 12 pairs unless noted):
  momentum 9 (lookback x skip), vol-managed momentum 2, reversal 2,
  RSI 2, MA-bounce 1, Bollinger reversion control 1, post-shock drift 1,
  gap-fade 1, month-of-year 12, day-of-week 5, calendar-flow 4,
  cross-asset 3, cross-sectional baskets 3, news-surprise 6, H1 90.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from edge_scan import PAIRS, PIP, load_d1, load_h1, nw_t

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
IS_END = "2021-12-31"
OOS_START = "2022-01-01"
N_PERM = 1000
RNG = random.Random(11)
RT_PIPS = 1.0  # round-trip cost in pips (0.5/side)

SIGNAL_PAIRS = ["SP500", "OIL", "GOLD", "BTCUSD"]


def ret_series(close: pd.Series) -> pd.Series:
    return close.pct_change().dropna()


def pip_cost_units(pair: str, close: pd.Series) -> float:
    """Round-trip cost in return units at mean close."""
    return RT_PIPS * PIP[pair] / float(close.mean())


def backtest(pair, close, ret, signal, cost_units):
    """Position = sign(signal) entered next bar; cost per flip. Returns the
    net daily return series."""
    pos = np.sign(signal).shift(1).fillna(0.0)
    flips = (pos != pos.shift(1)).astype(float)
    return pos * ret - cost_units * flips


def stats_series(s: pd.Series, cost: float) -> dict:
    s = s.dropna()
    if len(s) < 20:
        return None
    mu, sd = s.mean(), s.std(ddof=1)
    if sd == 0:
        return None
    t = mu / (sd / math.sqrt(len(s)))
    sharpe = mu / sd * math.sqrt(252) if sd > 0 else 0.0
    return {"n": len(s), "mean": float(mu), "t": float(t),
            "nw_t": float(nw_t(s.to_numpy(), lag=5)),
            "sharpe": float(sharpe), "win": float((s > 0).mean()),
            "trades": int((s != 0).sum())}


def perm_p_signal(actual: float, ret: pd.Series, signal: pd.Series,
                  cost: float, n_perm: int = N_PERM) -> float:
    """Null: random +/-1 signals with the true flip frequency, same cost.
    Vectorised: each perm draws flips, cumulative product = sign path."""
    pos = np.sign(signal).shift(1).fillna(0.0)
    flips = (pos != pos.shift(1)).astype(float)
    p_flip = float(flips.mean())
    n = len(ret)
    r_arr = ret.to_numpy()
    rng = np.random.default_rng(11)
    cnt = 1
    for _ in range(n_perm):
        s = rng.choice([-1.0, 1.0])
        f = (rng.random(n) < p_flip).astype(float)
        pos_n = s * np.cumprod(1.0 - 2.0 * f)
        fl = np.abs(np.diff(pos_n, prepend=0.0)) > 0.0
        net = pos_n * r_arr - cost * fl
        if net.mean() >= actual:
            cnt += 1
    return cnt / (n_perm + 1)


def perm_p_calendar(actual: float, ret: pd.Series, mask: pd.Series,
                    n_perm: int = N_PERM) -> float:
    """Null: same-count RANDOM day subset (calendar structure removed)."""
    n = len(ret)
    k = int(mask.sum())
    r_arr = ret.to_numpy()
    rng = np.random.default_rng(12)
    cnt = 1
    for _ in range(n_perm):
        pick = rng.choice(n, k, replace=False)
        if r_arr[pick].mean() >= actual:
            cnt += 1
    return cnt / (n_perm + 1)


def eval_daily(pair, close, signal, direction_lock=None, calendar=False):
    """Full IS/OOS evaluation of one daily signal family."""
    ret = ret_series(close)
    signal = signal.reindex(ret.index).fillna(0.0)
    cost = pip_cost_units(pair, close)
    full = ret.copy()
    if direction_lock is not None:
        is_ret = ret.loc[:IS_END]
        sign = 1 if is_ret.mean() > 0 else -1
        signal = direction_lock * signal if direction_lock == 0 else signal
    # net series computed with sign(signal)
    net = backtest(pair, close, ret, signal, cost)
    is_net = net.loc[:IS_END]
    oos_net = net.loc[OOS_START:]
    is_s = stats_series(is_net, cost)
    oos_s = stats_series(oos_net, cost)
    if oos_s is None:
        return None
    if calendar:
        mask = (signal != 0).astype(bool)
        p = perm_p_calendar(oos_s["mean"], ret.loc[OOS_START:],
                            mask.loc[OOS_START:])
    else:
        p = perm_p_signal(oos_s["mean"], ret.loc[OOS_START:],
                          signal.loc[OOS_START:], cost)
    return {"is_t": is_s["t"] if is_s else None,
            "is_mean": is_s["mean"] if is_s else None,
            "oos_mean": oos_s["mean"], "oos_t": oos_s["t"],
            "oos_nw": oos_s["nw_t"], "oos_sharpe": oos_s["sharpe"],
            "win": oos_s["win"], "n": oos_s["n"], "p": p}


# ---------------------------------------------------------------------------
# D1 signal builders (return a pd.Series aligned to close.index)
# ---------------------------------------------------------------------------

def sig_momentum(close, lookback, skip=0):
    r = close.pct_change()
    if skip:
        sig = r.shift(skip).rolling(lookback).sum()
    else:
        sig = r.rolling(lookback).sum()
    return sig


def sig_vol_mom(close, lookback, vol_lb=21):
    r = close.pct_change()
    mom = r.rolling(lookback).sum()
    vol = r.rolling(vol_lb).std()
    return mom / vol.shift(1).replace(0, np.nan)


def sig_rev(close, k):
    return -close.pct_change().rolling(k).sum()


def sig_rsi(close, k, thr=30):
    r = close.pct_change()
    up = r.clip(lower=0).rolling(k).mean()
    dn = (-r.clip(upper=0)).rolling(k).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    sig = pd.Series(0.0, index=close.index)
    sig[rsi < thr] = 1.0
    sig[rsi > 100 - thr] = -1.0
    return sig


def sig_ma_bounce(close):
    ret = ret_series(close)
    ma = close.rolling(63).mean()
    z = (close - ma) / close.rolling(63).std()
    up = (ma > 0).astype(float)
    sig = pd.Series(0.0, index=close.index)
    sig[(z < -1.5) & (up == 1)] = 1.0   # pullback in uptrend
    return sig


def sig_bb_reentry(close):
    ma = close.rolling(20).mean()
    sd = close.rolling(20).std()
    low = ma - 2 * sd
    sig = (close < low).astype(float)   # long lower band (dead control)
    return sig


def sig_shock_drift(close, thr=2.5, hold=5):
    r = close.pct_change()
    z = r / r.rolling(21).std().shift(1).replace(0, np.nan)
    shock = (z.abs() > thr)
    dirs = np.sign(r).fillna(0.0)
    out = pd.Series(0.0, index=close.index)
    j = 0
    arr_dir = dirs.to_numpy()
    arr_shock = shock.to_numpy()
    res = np.zeros(len(close))
    for i in range(len(res)):
        if arr_shock[i]:
            j = hold
            d = arr_dir[i]
        if j > 0:
            res[i] = d
            j -= 1
    return pd.Series(res, index=close.index)


def sig_gap_fade(close):
    return -(close / close.shift(1) - 1).fillna(0.0)


def sig_month(close, m):
    sig = pd.Series(0.0, index=close.index)
    sig[close.index.month == m] = 1.0
    return sig


def sig_dow(close, wd):
    sig = pd.Series(0.0, index=close.index)
    sig[close.index.dayofweek == wd] = 1.0
    return sig


def sig_turn_of_month(close):
    sig = pd.Series(0.0, index=close.index)
    d = close.index.to_series()
    last2 = d.groupby(d.dt.to_period("M")).transform(lambda x: x >= x.nlargest(2).min())
    first2 = d.groupby(d.dt.to_period("M")).transform(lambda x: x <= x.nsmallest(2).max())
    sig[(last2 | first2).fillna(False)] = 1.0
    return sig


def sig_first_week(close):
    sig = pd.Series(0.0, index=close.index)
    sig[close.index.day <= 3] = 1.0
    return sig


def sig_last_week(close):
    sig = pd.Series(0.0, index=close.index)
    d = close.index.to_series()
    last3 = d.groupby(d.dt.to_period("M")).transform(lambda x: x >= x.nlargest(3).min())
    sig[last3.fillna(False)] = 1.0
    return sig


def sig_cross(close_x, k):
    return close_x.pct_change().rolling(k).sum()


def main():
    frames = {p: load_d1(p) for p in PAIRS}
    closes = {p: f["Close"] for p, f in frames.items() if len(f)}
    frames_x = {p: load_d1(p) for p in SIGNAL_PAIRS}
    closes_x = {p: f["Close"] for p, f in frames_x.items() if len(f)}
    print(f"d1 pairs loaded: {len(closes)}/{len(PAIRS)}")

    rows = []

    def add(fam, pair, signal, calendar=False):
        c = closes[pair]
        r = eval_daily(pair, c, signal, calendar=calendar)
        if r is None:
            return
        r.update({"family": fam, "pair": pair})
        rows.append(r)

    # ---- momentum + vol-managed ----
    for p in closes:
        c = closes[p]
        for lb in (5, 21, 63, 126, 252):
            add(f"mom{lb}", p, sig_momentum(c, lb))
        for lb in (21, 63, 126, 252):
            add(f"mom{lb}s5", p, sig_momentum(c, lb, skip=5))
        for lb in (63, 126):
            add(f"volmom{lb}", p, sig_vol_mom(c, lb))
    print(f"momentum block done: {len(rows)}", flush=True)

    # ---- reversal / RSI / structure ----
    for p in closes:
        c = closes[p]
        add("rev1", p, sig_rev(c, 1))
        add("rev5", p, sig_rev(c, 5))
        add("rsi2", p, sig_rsi(c, 2))
        add("rsi5", p, sig_rsi(c, 5))
        add("ma_bounce63", p, sig_ma_bounce(c))
        add("bb_lower20", p, sig_bb_reentry(c))
        add("shock_drift", p, sig_shock_drift(c))
        add("gap_fade", p, sig_gap_fade(c))
    print(f"reversal block done: {len(rows)}", flush=True)

    # ---- calendar ----
    for p in closes:
        c = closes[p]
        for m in range(1, 13):
            add(f"month{m:02d}", p, sig_month(c, m), calendar=True)
        for wd, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
            add(f"dow_{name}", p, sig_dow(c, wd), calendar=True)
        add("turn_of_month", p, sig_turn_of_month(c), calendar=True)
        add("first_week", p, sig_first_week(c), calendar=True)
        add("last_week", p, sig_last_week(c), calendar=True)
    print(f"calendar block done: {len(rows)}", flush=True)

    # ---- cross-asset (only the pairs with a mechanism) ----
    if "SP500" in closes_x:
        for p in closes:
            add("spx5", p, sig_cross(closes_x["SP500"], 5))
    if "OIL" in closes_x:
        if "USDCAD" in closes:
            add("oil_cad5", "USDCAD", -sig_cross(closes_x["OIL"], 5))
        if "AUDUSD" in closes:
            add("oil_aud5", "AUDUSD", sig_cross(closes_x["OIL"], 5))
    if "GOLD" in closes_x and "AUDUSD" in closes:
        add("gold_aud5", "AUDUSD", sig_cross(closes_x["GOLD"], 5))
    if "BTCUSD" in closes_x:
        for p in closes:
            add("btc5", p, sig_cross(closes_x["BTCUSD"], 5))
    print(f"cross-asset block done: {len(rows)}", flush=True)

    df = pd.DataFrame(rows).sort_values("oos_t", ascending=False)
    (OUT / "fx_campaign_leaderboard.csv").write_text(df.to_csv(index=False),
                                                     encoding="utf-8")
    print(f"total tested: {len(df)}")
    print("wrote reports/fx_campaign_leaderboard.csv (report next)")


if __name__ == "__main__":
    main()
