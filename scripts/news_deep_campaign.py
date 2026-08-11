#!/usr/bin/env python3
"""news_deep_campaign.py — two deeper tests of the informed under-reaction family.

A. EIA Natural Gas Stocks Change surprise -> NG price (clean storage test).
   Hypothesis: positive storage surprise (more supply) -> NG down (conv=-1).
B. USDJPY drift at longer holds: k=2/3/5 trading days, with overnight
   financing charged per calendar night (weekend nights x3) using the
   operator's broker rates (long 0.0082%/night, short 0.0029%/night).
   k=1 baseline included as a machinery sanity check (should reproduce the
   known USDJPY 4/6 result).
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "E:/forex-data/scripts")
from fx_strict_battery import (  # noqa: E402
    IS_END, OOS_START, Z_THR,
    stats_series, trimmed_mean_by_year, perm_p_signflip,
    wf_news, wf_perm_p_news, bootstrap_p,
)

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
LONG_RATE = 0.000082   # per night, longs (T212)
SHORT_RATE = 0.000029  # per night, shorts (T212)


def load_events_all(currency: str = "USD", impact=("High", "Medium")) -> pd.DataFrame:
    """All events with per-title expanding z (no trigger filter — callers apply).

    Canonical implementation now lives in data_registry.py (T2 unified
    ingest); z_thr=None preserves this function's unfiltered semantics.
    """
    from data_registry import load as _reg_load
    return _reg_load("events", currency=currency, impact=impact, z_thr=None)


def close_from_csv(path: str) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["date"]))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s > 0]


def nights_held(entry_date, exit_date):
    """Calendar nights between two dates; Sat+Sun nights count 3x (broker rule)."""
    d0, d1 = pd.Timestamp(entry_date), pd.Timestamp(exit_date)
    n = (d1 - d0).days
    if n <= 0:
        return 0.0
    days = pd.date_range(d0, d1, freq="D")
    wd = [d for d in days if d.dayofweek >= 5]
    return float(n + 2 * len(wd))


def unit_frame(events, close, conv, k=1, fin=False, cost_frac=0.0):
    r = close.pct_change(k).shift(-k).dropna()
    r.index = r.index.date
    idx = close.index
    ev = events.copy()
    ev["r"] = ev["date"].map(r)
    ev = ev.dropna(subset=["r"])
    if fin:
        # exit date = date of the bar k rows ahead of the event bar
        dates = idx
        date_of = {d.date(): i for i, d in enumerate(dates)}
        def exit_date(ed):
            i = date_of.get(ed)
            return dates[i + k].date() if i is not None and i + k < len(dates) else None
        ev["exit_d"] = ev["date"].map(exit_date)
        ev = ev.dropna(subset=["exit_d"])
        ev["nights"] = [nights_held(a, b) for a, b in zip(ev["date"], ev["exit_d"])]
        ev["fin"] = np.where(np.sign(ev["z"]) * conv > 0,
                             ev["nights"] * LONG_RATE, ev["nights"] * SHORT_RATE)
        ev["net"] = conv * np.sign(ev["z"]) * ev["r"] - cost_frac - ev["fin"]
    else:
        ev["net"] = conv * np.sign(ev["z"]) * ev["r"] - cost_frac
    ev = ev[ev["z"].abs() >= Z_THR]
    out = ev[["date", "z", "r", "net"]].copy()
    out["fin"] = ev["fin"] if "fin" in ev.columns else 0.0
    return out


def full_battery(ev, close, conv, cost_frac, key, label, fin=False):
    ret_full = close.pct_change().dropna()
    is_ev = ev[ev["date"] <= pd.Timestamp(IS_END).date()]
    oos_ev = ev[ev["date"] >= pd.Timestamp(OOS_START).date()]
    is_s = stats_series(is_ev["net"])
    ho_s = stats_series(oos_ev["net"])
    p_is = perm_p_signflip(is_s["mean"], is_ev["r"].to_numpy(),
                           conv * np.sign(is_ev["z"].to_numpy()), 0.0)
    p_ho = perm_p_signflip(ho_s["mean"], oos_ev["r"].to_numpy(),
                           conv * np.sign(oos_ev["z"].to_numpy()), 0.0)
    wf = wf_news(ev)
    wf_s = stats_series(wf)
    wf_trim = trimmed_mean_by_year(wf) if len(wf) >= 3 else None
    p_wf = wf_perm_p_news(wf_s["mean"] if wf_s["mean"] is not None else -1e9,
                          ev, ret_full)
    boot = bootstrap_p(wf) if wf_s["mean"] is not None else {}
    ladder = {}
    for mult in (0.5, 1.0, 2.0):
        ev2 = ev.copy()
        ev2["net"] = conv * np.sign(ev2["z"]) * ev2["r"] - mult * cost_frac
        if fin:
            ev2["net"] -= ev2["fin"]
        ladder[mult] = float(wf_news(ev2).mean())
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
    return {"key": key, "label": label, "n": len(ev),
            "is_t": is_s["t"], "is_nw": is_s["nw"], "is_win": is_s["win"],
            "p_is": p_is, "ho_t": ho_s["t"], "ho_nw": ho_s["nw"],
            "ho_win": ho_s["win"], "ho_mean": ho_s["mean"], "p_ho": p_ho,
            "wf_mean": wf_s["mean"], "wf_n": wf_s["n"], "p_wf": p_wf,
            "p_leq_0": boot.get("p_leq_0"), "wf_trim": wf_trim,
            "ladder_05": ladder[0.5], "ladder_1": ladder[1.0],
            "ladder_2": ladder[2.0],
            "VERDICT": "PASS" if all(gates.values()) else "FAIL",
            "gates": "; ".join(k for k, v in gates.items() if not v) or "all pass"}


NG = close_from_csv(str(BASE / "market-data/raw/yahoo/COMM_NG_d.csv"))
UJ = pd.read_parquet(BASE / "market-data/normalized/USDJPY/USDJPY_d1.parquet")["Close"]
results = []

# ---- A. NG storage surprise -> NG (clean single-title test)
# storage reports are not High/Medium tier in the archive -> load ALL tiers for this title
ev_us = load_events_all("USD")
ng_ev = load_events_all("USD", impact=None)
ng_ev = ng_ev[ng_ev["title"] == "EIA Natural Gas Stocks Change"].copy()
print(f"A. EIA Natural Gas Stocks Change: {len(ng_ev)} events "
      f"({ng_ev['date_utc'].min().date()} -> {ng_ev['date_utc'].max().date()})")
if len(ng_ev) >= 40:
    fr = unit_frame(ng_ev, NG, conv=-1.0, k=1, fin=False, cost_frac=0.0015)
    print(f"   triggers: {len(fr)} | IS n={(fr['date'] <= pd.Timestamp(IS_END).date()).sum()} "
          f"| OOS n={(fr['date'] >= pd.Timestamp(OOS_START).date()).sum()}")
    res = full_battery(fr, NG, -1.0, 0.0015, "NG_STORAGE",
                       "EIA Nat Gas storage surprise -> NG (short on +surprise)")
    results.append(res)
    print(f"   -> {res['VERDICT']} | gates: {res['gates']}")

# ---- B. USDJPY drift at k = 1/2/3/5 (k=1 = machinery sanity check)
for k in (1, 2, 3, 5):
    fr = unit_frame(ev_us, UJ, conv=+1.0, k=k, fin=(k > 1), cost_frac=0.01 / float(UJ.mean()))
    label = f"USDJPY news drift k={k}-day hold" + (" (+financing)" if k > 1 else "")
    print(f"B. {label}: n={len(fr)}")
    res = full_battery(fr, UJ, +1.0, 0.01 / float(UJ.mean()), f"UJ_k{k}", label, fin=(k > 1))
    results.append(res)
    print(f"   -> {res['VERDICT']} | OOS t={res['ho_t']:.2f} | gates: {res['gates']}")

df = pd.DataFrame(results)
df.to_csv(OUT / "news_deep_campaign.csv", index=False)
pd.set_option("display.width", 260)
print("\nsaved reports/news_deep_campaign.csv")
print(df.to_string())
