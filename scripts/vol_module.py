#!/usr/bin/env python3
"""vol_module.py — Part 9.2 volatility prediction module (risk-sizing ONLY).

Composite HAR-RV-style forecast of next-day |USDJPY return| from four signals:
  rv1, rv5, rv22  realised-vol persistence (HAR components)
  sqz             Bollinger(20,2) width percentile (trailing 252d)
  btc             |BTCUSD daily log-return| (cross-asset)

Validation (Stage 1 redefined for a forecast):
  - OOS R^2 > naive benchmarks (yesterday's vol, 20d average)
  - monotonic calibration across forecast quintiles
  - Spearman rho forecast vs actual, OOS
Permutation (Stage 2/4): 1000 shuffles of the OOS target -> p-value on rho
  and on the Q5-Q1 quintile spread.

Application: USDJPY news-drift events (load_big_events + event_net_frame from
fx_strict_battery). Split OOS events by forecast-vol tercile; compare flat vs
vol-scaled sizing (position proportional to 1/forecast_vol, mean size = 1).
Forecast for the holding day uses only data <= event-day close -> no lookahead.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")
from fx_strict_battery import load_big_events, event_net_frame, load_d1

BASE = Path("E:/forex-data")
RNG = np.random.default_rng(20260811)
IS_END = "2021-12-31"
N_PERM = 1000


def build_features():
    j = load_d1("USDJPY")
    c = j["Close"]
    r = np.log(c).diff()
    ar = r.abs()
    tgt = ar.shift(-1)  # next-day |return|
    f = pd.DataFrame(index=j.index)
    f["rv1"] = ar
    f["rv5"] = ar.rolling(5).mean()
    f["rv22"] = ar.rolling(22).mean()
    w = c.rolling(20).std() * 4.0  # Bollinger width
    f["sqz"] = w.rolling(252).apply(lambda a: float((a[-1] >= a).mean()), raw=True)
    b = load_d1("BTCUSD")["Close"]
    bret = np.log(b).diff().abs()
    f["btc"] = bret.reindex(j.index, method="ffill")
    f["tgt"] = tgt
    return f.dropna()


def quintile_stats(pred, actual):
    df = pd.DataFrame({"pred": pred, "actual": actual}).dropna()
    if len(df) < 100:
        return None
    q = pd.qcut(df["pred"], 5, labels=False, duplicates="drop")
    means = df.groupby(q)["actual"].mean()
    if len(means) < 4:
        return None
    mono = all(means.iloc[i] <= means.iloc[i + 1] for i in range(len(means) - 1))
    rho = df["pred"].corr(df["actual"], method="spearman")
    return {"q_means": [round(x, 5) for x in means.tolist()],
            "monotonic": bool(mono),
            "q5_q1_ratio": round(float(means.iloc[-1] / means.iloc[0]), 2) if means.iloc[0] > 0 else None,
            "spearman": round(float(rho), 4),
            "n": int(len(df))}


def oos_r2(pred, actual):
    df = pd.DataFrame({"pred": pred, "actual": actual}).dropna()
    return 1.0 - float(((df["actual"] - df["pred"]) ** 2).sum() /
                       ((df["actual"] - df["actual"].mean()) ** 2).sum())


def main():
    f = build_features()
    ism = f.index <= IS_END
    oosm = f.index > IS_END

    # --- OLS composite fit on IS, predict OOS ---
    feats = ["rv1", "rv5", "rv22", "sqz", "btc"]
    Xis = np.column_stack([np.ones(ism.sum())] + [f.loc[ism, k].values for k in feats])
    yis = f.loc[ism, "tgt"].values
    beta, *_ = np.linalg.lstsq(Xis, yis, rcond=None)
    Xoos = np.column_stack([np.ones(oosm.sum())] + [f.loc[oosm, k].values for k in feats])
    yoos = f.loc[oosm, "tgt"].values
    pred_oos = Xoos @ beta
    pred_is = Xis @ beta

    # --- naive benchmarks (fit-free) ---
    r2_comp = oos_r2(pred_oos, yoos)
    r2_rv1 = oos_r2(f.loc[oosm, "rv1"].values, yoos)
    r2_20 = oos_r2(f.loc[oosm, "rv22"].values, yoos)

    # --- permutation: shuffle OOS target 1000x ---
    def rho_stat(a, b):
        return pd.Series(a).corr(pd.Series(b), method="spearman")

    def qspread_stat(a, b):
        df = pd.DataFrame({"p": a, "a": b}).dropna()
        q = pd.qcut(df["p"], 5, labels=False, duplicates="drop")
        m = df.groupby(q)["a"].mean()
        return float(m.iloc[-1] - m.iloc[0]) if len(m) >= 4 else 0.0

    real_rho = rho_stat(pred_oos, yoos)
    real_qs = qspread_stat(pred_oos, yoos)
    perm_rho, perm_qs = [], []
    for _ in range(N_PERM):
        yp = RNG.permutation(yoos)
        perm_rho.append(rho_stat(pred_oos, yp))
        perm_qs.append(qspread_stat(pred_oos, yp))
    p_rho = float(np.mean(np.array(perm_rho) >= real_rho))
    p_qs = float(np.mean(np.array(perm_qs) >= real_qs))

    # --- calibration ---
    cal_is = quintile_stats(pred_is, f.loc[ism, "tgt"].values)
    cal_oos = quintile_stats(pred_oos, yoos)

    # --- application: USDJPY news drift, OOS events ---
    ev = load_big_events()
    net = event_net_frame("USDJPY", ev)
    oos_net = net[net["date"].astype(str) >= "2022-01-01"].copy()
    oos_net["date"] = pd.to_datetime(oos_net["date"]).dt.tz_localize(None)
    oos_net = oos_net.set_index("date").sort_index()
    # forecast of holding-day vol, known at event close (data <= event day)
    fc = pd.DataFrame({"fvol": pred_oos}, index=f.loc[oosm].index.tz_localize(None))
    oos_net["fvol"] = fc["fvol"].reindex(oos_net.index, method="ffill")
    oos_net = oos_net.dropna(subset=["fvol"])

    terc = pd.qcut(oos_net["fvol"], 3, labels=["low", "mid", "high"], duplicates="drop")
    app = {}
    for tname in ["low", "mid", "high"]:
        s = oos_net.loc[terc == tname, "net"]
        app[tname] = {"n": int(len(s)),
                      "mean_net_pct": round(float(s.mean() * 100), 4),
                      "t": round(float(s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))), 2) if len(s) > 1 and s.std(ddof=1) > 0 else None,
                      "win": round(float((s > 0).mean()), 3)}
    # vol-scaled: position proportional to 1/fvol (mean size = 1)
    oos_net["size"] = (1.0 / oos_net["fvol"]) / (1.0 / oos_net["fvol"]).mean()
    flat_sharpe = oos_net["net"].mean() / oos_net["net"].std(ddof=1) * np.sqrt(252) if oos_net["net"].std(ddof=1) > 0 else 0
    scaled = oos_net["net"] * oos_net["size"]
    scaled_sharpe = scaled.mean() / scaled.std(ddof=1) * np.sqrt(252) if scaled.std(ddof=1) > 0 else 0
    flat_ann = oos_net["net"].mean() * 252 * 100
    scaled_ann = scaled.mean() * 252 * 100

    res = {
        "n_is": int(ism.sum()), "n_oos": int(oosm.sum()),
        "oos_r2_composite": round(r2_comp, 4),
        "oos_r2_bench_rv1": round(r2_rv1, 4),
        "oos_r2_bench_rv22": round(r2_20, 4),
        "calibration_is": cal_is,
        "calibration_oos": cal_oos,
        "perm": {"p_rho": round(p_rho, 4), "p_qspread": round(p_qs, 4), "n_perm": N_PERM},
        "application_drift": {"n_events": int(len(oos_net)), "by_tercile": app,
                              "flat": {"ann_pct": round(flat_ann, 3), "sharpe": round(flat_sharpe, 3)},
                              "vol_scaled": {"ann_pct": round(scaled_ann, 3), "sharpe": round(scaled_sharpe, 3)}},
    }
    print(json.dumps(res, indent=2))
    with open(BASE / "reports/vol_module_results.json", "w") as fh:
        json.dump(res, fh, indent=2)
    print("\n=== VOL MODULE: oos R2 comp={} vs rv1={} vs rv22={} | p_rho={} p_qspread={} | "
          "drift flat sharpe={} scaled sharpe={}".format(
              r2_comp, r2_rv1, r2_20, p_rho, p_qs, flat_sharpe, scaled_sharpe))


if __name__ == "__main__":
    main()
