#!/usr/bin/env python3
"""news_ext_campaign.py — extend the informed under-reaction family.

Units tested (same per-title expanding z machinery, same gates as
fx_strict_battery.run_news_battery):
  EUR->EURUSD, GBP->GBPUSD, JPY->USDJPY, AUD->AUDUSD, CAD->USDCAD,
  CHF->USDCHF, NZD->NZDUSD        (non-USD releases on their own pair)
  USD->XAUUSD, USD->XAGUSD, USD->NG (USD releases on dollar-priced commodities)

Screen (fast, all units): IS t, OOS t/NW/win. Units with OOS t > 1.8 OR
(OOS mean > 2x cost AND OOS win > 0.53) get the FULL six-gate battery
(IS perm, holdout, walk-forward + perm, bootstrap, ladder, trim).
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "E:/forex-data/scripts")
from fx_strict_battery import (  # noqa: E402
    IS_END, OOS_START, Z_THR, N_PERM,
    stats_series, trimmed_mean_by_year, perm_p_signflip,
    wf_news, wf_perm_p_news, bootstrap_p,
)

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(31)


def load_events(currency: str) -> pd.DataFrame:
    ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)
    ev = ev[(ev["currency"] == currency) &
            (ev["impact"].isin(["High", "Medium"])) &
            ev["actual"].notna() & ev["forecast"].notna()].copy()
    ev["surprise"] = (pd.to_numeric(ev["actual"], errors="coerce") -
                      pd.to_numeric(ev["forecast"], errors="coerce"))
    ev = ev.dropna(subset=["surprise"]).sort_values("date_utc")
    ev["z"] = np.nan
    for _t, g in ev.groupby("title"):
        g = g.sort_values("date_utc")
        s = g["surprise"]
        mu = s.expanding(min_periods=20).mean().shift(1)
        sd = s.expanding(min_periods=20).std().shift(1)
        z = (s - mu) / sd.where(sd > 1e-12)
        ev.loc[g.index, "z"] = z.clip(-8, 8)
    ev["date"] = ev["date_utc"].dt.date
    return ev


def close_from_parquet(pair: str) -> pd.Series:
    return pd.read_parquet(BASE / f"market-data/normalized/{pair}/{pair}_d1.parquet")["Close"]


def close_from_csv(path: str) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["date"]))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s > 0]


def unit_frame(events: pd.DataFrame, close: pd.Series, conv: float,
               cost_frac: float) -> pd.DataFrame:
    r = close.pct_change().shift(-1).dropna()
    r.index = r.index.date
    ev = events.copy()
    ev["r"] = ev["date"].map(r)
    ev = ev.dropna(subset=["r"])
    ev["net"] = conv * np.sign(ev["z"]) * ev["r"] - cost_frac
    ev = ev[ev["z"].abs() >= Z_THR]
    return ev[["date", "z", "r", "net"]].copy()


def screen(ev: pd.DataFrame) -> dict:
    is_ev = ev[ev["date"] <= pd.Timestamp(IS_END).date()]
    oos_ev = ev[ev["date"] >= pd.Timestamp(OOS_START).date()]
    if len(ev) < 40 or len(is_ev) < 25 or len(oos_ev) < 15:
        return {"n": len(ev), "is_n": len(is_ev), "oos_n": len(oos_ev)}
    is_s = stats_series(is_ev["net"])
    ho_s = stats_series(oos_ev["net"])
    return {"n": len(ev), "is_n": len(is_ev), "oos_n": len(oos_ev),
            "is_t": is_s["t"], "ho_t": ho_s["t"], "ho_nw": ho_s["nw"],
            "ho_win": ho_s["win"], "ho_mean": ho_s["mean"]}


def full_battery(ev: pd.DataFrame, close: pd.Series, conv: float,
                 cost_frac: float, key: str, label: str) -> dict:
    ret_full = close.pct_change().dropna()
    is_ev = ev[ev["date"] <= pd.Timestamp(IS_END).date()]
    oos_ev = ev[ev["date"] >= pd.Timestamp(OOS_START).date()]
    is_s = stats_series(is_ev["net"])
    ho_s = stats_series(oos_ev["net"])
    p_is = perm_p_signflip(is_s["mean"], is_ev["r"].to_numpy(),
                           conv * np.sign(is_ev["z"].to_numpy()), cost_frac)
    p_ho = perm_p_signflip(ho_s["mean"], oos_ev["r"].to_numpy(),
                           conv * np.sign(oos_ev["z"].to_numpy()), cost_frac)
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
            "is_n": len(is_ev), "is_t": is_s["t"], "is_nw": is_s["nw"],
            "is_win": is_s["win"], "p_is": p_is,
            "ho_n": len(oos_ev), "ho_t": ho_s["t"], "ho_nw": ho_s["nw"],
            "ho_win": ho_s["win"], "ho_mean": ho_s["mean"], "p_ho": p_ho,
            "wf_mean": wf_s["mean"], "wf_n": wf_s["n"], "p_wf": p_wf,
            "p_leq_0": boot.get("p_leq_0"),
            "wf_trim": wf_trim, "ladder_05": ladder[0.5],
            "ladder_1": ladder[1.0], "ladder_2": ladder[2.0],
            "VERDICT": "PASS" if all(gates.values()) else "FAIL",
            "gates": "; ".join(k for k, v in gates.items() if not v) or "all pass"}


UNITS = [
    # (key, label, currency, close, conv, cost_frac)
    ("EUR", "EUR events -> EURUSD", "EUR", close_from_parquet("EURUSD"), +1.0, 0.0001 / 1.1),
    ("GBP", "GBP events -> GBPUSD", "GBP", close_from_parquet("GBPUSD"), +1.0, 0.0001 / 1.3),
    ("JPY", "JPY events -> USDJPY", "JPY", close_from_parquet("USDJPY"), -1.0, 0.01 / 155.0),
    ("AUD", "AUD events -> AUDUSD", "AUD", close_from_parquet("AUDUSD"), +1.0, 0.0001 / 0.66),
    ("CAD", "CAD events -> USDCAD", "CAD", close_from_parquet("USDCAD"), -1.0, 0.0001 / 1.37),
    ("CHF", "CHF events -> USDCHF", "CHF", close_from_parquet("USDCHF"), -1.0, 0.0001 / 0.88),
    ("NZD", "NZD events -> NZDUSD", "NZD", close_from_csv(str(BASE / "market-data/raw/yahoo/NZDUSD_d.csv")), +1.0, 0.0001 / 0.61),
    ("US->XAU", "USD events -> Gold (XAUUSD)", "USD", close_from_csv(str(BASE / "market-data/raw/yahoo/COMM_GC_d.csv")), -1.0, 0.0005),
    ("US->XAG", "USD events -> Silver (XAGUSD)", "USD", close_from_csv(str(BASE / "market-data/raw/yahoo/COMM_SI_d.csv")), -1.0, 0.0006),
    ("US->NG", "USD events -> Nat Gas", "USD", close_from_csv(str(BASE / "market-data/raw/yahoo/COMM_NG_d.csv")), -1.0, 0.0020),
]

results = []
for key, label, cur, close, conv, cost in UNITS:
    ev = unit_frame(load_events(cur), close, conv, cost)
    sc = screen(ev)
    print(f"[{key:<8}] n={sc.get('n',0):>5} IS n={sc.get('is_n',0):>5} "
          f"OOS n={sc.get('oos_n',0):>5} IS t={sc.get('is_t')} "
          f"OOS t={sc.get('ho_t')} OOS nw={sc.get('ho_nw')} "
          f"OOS win={sc.get('ho_win')} OOS mean={sc.get('ho_mean')}")
    need_full = (sc.get("ho_t") is not None and sc["ho_t"] > 1.8) or \
                (sc.get("ho_mean") is not None and sc.get("ho_win") is not None
                 and sc["ho_mean"] > 2 * cost and sc["ho_win"] > 0.53)
    if need_full:
        print(f"  -> passes screen, running FULL battery...")
        res = full_battery(ev, close, conv, cost, key, label)
        results.append(res)
        print(f"  -> VERDICT {res['VERDICT']} | gates: {res['gates']}")
    else:
        results.append({"key": key, "label": label, "n": sc.get("n", 0),
                        "VERDICT": "SCREEN-KILL", "gates": "",
                        "is_t": sc.get("is_t"), "ho_t": sc.get("ho_t"),
                        "ho_nw": sc.get("ho_nw"), "ho_win": sc.get("ho_win"),
                        "ho_mean": sc.get("ho_mean")})

df = pd.DataFrame(results)
df.to_csv(OUT / "news_ext_campaign.csv", index=False)
print("\nsaved reports/news_ext_campaign.csv")
pd.set_option("display.width", 250)
print(df.to_string())
