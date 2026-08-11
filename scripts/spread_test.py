#!/usr/bin/env python3
"""spread_test.py — structural spread backtest, four-stage validation framework.

Usage: python spread_test.py <key> [--quick]
  key: crush | hogcorn | lfcattle | crack

Pre-registered parameters (locked before results were seen):
  LOOKBACK=90 days rolling mean/std of the log-ratio
  ENTRY_Z=2.0, exit on z-crossing 0 or 20-day time stop
  IS window: 2000-09-15 -> 2014-12-31 ; OOS: 2015-01-01 -> present
  COST_PER_LEG=0.30% per side (T212 commodity CFD spread, measured earlier:
      corn 0.27%, gasoline 0.46%; 0.30% is the middle estimate)
  FIN_PER_DAY=0.01% per day per unit weight on held positions (assumption —
      T212 publishes no historical swap tables; flagged in every report)
  Block bootstrap block = 20 days (preserves autocorr + cross-leg correlation)
  Permutation count = 1000 at both MC stages

Stages:
  1  IS excellence: mean net > 2x round-trip cost, Sharpe>=1.0, win>=60%, t>=2.5
  2  IS permutation MC (>=1000), p<0.01
  3  Walk-forward, expanding window, re-optimize yearly, Sharpe>=0.5, t>=2.0
  4  Walk-forward MC (>=1000, full pipeline each), p<0.05  <- headline number

Roll-resistance probe (5.2, heuristic — no per-contract data on the drive):
  mark candidate roll-jump days per leg (|ret| > 5x its 90d mean, not mirrored
  by the other leg(s)); compare strategy P&L including vs excluding those days.

Direction-agnostic check: corr(P&L, each leg's daily return); flag |corr|>0.3.
"""
import json
import os
import sys
import time
import numpy as np
import pandas as pd

ROOT = "E:/forex-data"
RNG = np.random.default_rng(20260811)

LOOKBACK = 90
ENTRY_Z = 2.0
TIME_STOP = 20
IS_END = "2014-12-31"
COST_PER_LEG = 0.003
FIN_PER_DAY = 0.0001
BLOCK = 20
N_PERM = 1000
WF_FIRST = "2012-01-01"   # first walk-forward step (>=11y history at that point)
WF_STEP = 365

SPREADS = {
    "crush": {"legs": [("COMM_ZS_d.csv", 1.0), ("COMM_ZM_d.csv", -0.733), ("COMM_ZL_d.csv", -0.183)],
              "name": "Soybean crush (ZS - 0.733ZM - 0.183ZL)",
              "mech": "processor margin: crusher must buy beans and sell meal+oil on the crop calendar"},
    "hogcorn": {"legs": [("COMM_HE_d.csv", 1.0), ("COMM_ZC_d.csv", -1.0)],
                "name": "Hog-corn feed spread (HE - ZC)",
                "mech": "feeder must buy corn and sell hogs on the production calendar"},
    "lfcattle": {"legs": [("COMM_LE_d.csv", 1.0), ("COMM_GF_d.csv", -1.0)],
                 "name": "Live/feeder cattle spread (LE - GF)",
                 "mech": "feedlot fattening margin: buy feeder, sell fed cattle months later"},
    "crack": {"legs": [("COMM_CL_d.csv", 1.0), ("COMM_HO_d.csv", -0.667), ("COMM_RB_d.csv", -0.333)],
              "name": "3:2:1 crack spread (CL - 2/3HO - 1/3RB)",
              "mech": "refiner margin: refinery must run crude and sell products continuously"},
}


def adf_tstat(y, maxlag=12):
    """Augmented Dickey-Fuller t-stat (constant only). MacKinnon 5% crit ~ -2.86."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    n = y.size
    if n < 50:
        return np.nan
    dy = np.diff(y)
    best = None
    for p in range(0, maxlag + 1):
        T = n - 1 - p
        if T < 40:
            break
        yl = y[p:n - 1].reshape(-1, 1)
        X = np.hstack([np.ones((T, 1)), yl])
        if p > 0:
            cols = [dy[p - i:n - 1 - i].reshape(-1, 1) for i in range(1, p + 1)]
            X = np.hstack([X] + cols)
        Y = dy[p:n - 1].reshape(-1, 1)
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        resid = Y - X @ beta
        rss = float((resid ** 2).sum())
        k = 2 + p
        aic = n * np.log(rss / n) + 2 * k
        se = np.sqrt((rss / (T - k)) * np.linalg.inv(X.T @ X)[1, 1])
        tstat = float(beta[1, 0] / se)
        if best is None or aic < best[0]:
            best = (aic, tstat, p)
    return best[1]


def engle_granger(logs):
    """OLS of first leg on the others; returns residual series + ADF t.
    Returns (None, nan) when the design is degenerate (permuted series can collapse)."""
    try:
        y = logs.iloc[:, 0].values
        if not np.all(np.isfinite(y)) or np.std(y) < 1e-9:
            return None, np.nan
        X = np.column_stack([np.ones(len(y))] + [logs.iloc[:, i].values for i in range(1, logs.shape[1])])
        for j in range(1, X.shape[1]):
            if np.std(X[:, j]) < 1e-9:
                return None, np.nan
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        return pd.Series(resid, index=logs.index), adf_tstat(resid)
    except np.linalg.LinAlgError:
        return None, np.nan


def load_ratio(key):
    spec = SPREADS[key]
    idx = None
    legs = []
    for fname, w in spec["legs"]:
        df = pd.read_csv(os.path.join(ROOT, "market-data", "raw", "yahoo", fname),
                         parse_dates=["date"]).set_index("date")
        df = df[~df.index.duplicated(keep="first")].sort_index()
        c = df["close"].astype(float)
        c = c[c > 0]
        idx = c.index if idx is None else idx.intersection(c.index)
        legs.append((fname, w, c))
    common = pd.DataFrame({fname: c.reindex(idx) for fname, w, c in legs}).dropna()
    weights = np.array([w for _, w, _ in legs])
    logs = np.log(common)
    ratio = pd.Series(logs.values @ weights, index=common.index)
    ratio.wsum = float(np.abs(weights).sum())
    ret = ratio.diff()
    return common, ratio, ret, weights


def run_strategy(ratio, ret, wsum, lb=LOOKBACK, entry=ENTRY_Z, tstop=TIME_STOP):
    """Strategy engine. pos[t] decided on close t-1 (data<=t-2 rolling), pnl on day t."""
    n = len(ratio)
    m = ratio.rolling(lb).mean().shift(1)
    s = ratio.rolling(lb).std().shift(1)
    z = ((ratio - m) / s).values
    r = ret.values
    pos = np.zeros(n)
    pnl = np.zeros(n)
    cost_each = COST_PER_LEG * wsum  # 0.30% = 1x spread per leg round trip (0.5x spread + 0.5x slippage each way, project convention)
    cur = 0
    h = 0
    for t in range(1, n):
        zt = z[t - 1]
        if cur == 0:
            if zt >= entry:
                cur, h = -1, 1
            elif zt <= -entry:
                cur, h = 1, 1
        else:
            h += 1
            if (cur > 0 and zt <= 0) or (cur < 0 and zt >= 0) or h >= tstop:
                cur, h = 0, 0
        pos[t] = cur
        if cur != 0 and np.isfinite(r[t]):
            pnl[t] = cur * r[t] - FIN_PER_DAY * wsum
    for t in range(1, n):
        if pos[t] != 0 and pos[t - 1] == 0:
            pnl[t] -= cost_each
    trades = []
    t0 = None
    acc = 0.0
    for t in range(1, n):
        if pos[t] != 0 and pos[t - 1] == 0:
            t0 = t
            acc = 0.0
        if pos[t] != 0:
            acc += pnl[t]
        if pos[t] == 0 and pos[t - 1] != 0 and t0 is not None:
            trades.append(acc)
    out = pd.DataFrame({"pnl": pnl, "pos": pos}, index=ratio.index)
    out["z"] = z
    return out, trades


def stats_of(pnl, trades, label):
    d = pnl.dropna()
    n = len(d)
    if n < 50 or d.std(ddof=1) == 0:
        return dict(label=label, n=int(n), mean=0.0, sharpe=0.0, win=np.nan, t=0.0)
    mean_d = d.mean()
    sd_d = d.std(ddof=1)
    ann = mean_d * 252
    sharpe = mean_d / sd_d * np.sqrt(252)
    t = mean_d / sd_d * np.sqrt(n)
    win = np.mean([x > 0 for x in trades]) if trades else np.nan
    return dict(label=label, n=int(n), mean=round(ann * 100, 3), sharpe=round(sharpe, 2),
                win=round(win * 100, 1) if win == win else np.nan, t=round(t, 2))


def block_permute(logs, rng, block=BLOCK):
    """Block-bootstrap joint log-price paths (same block indices across legs)."""
    d = logs.diff().dropna()
    n = len(d)
    nblocks = int(np.ceil(n / block))
    order = rng.permutation(nblocks)
    idx = []
    for b in order:
        start = b * block
        idx.extend(range(start, min(start + block, n)))
        if len(idx) >= n:
            break
    idx = np.array(idx[:n])
    perm = d.iloc[idx].reset_index(drop=True)
    vals = np.log(logs.iloc[0].values.astype(float)) + perm.cumsum()
    return pd.DataFrame(vals, index=logs.index, columns=logs.columns)


def wf_pipeline(logs, ratio, ret, weights, wsum):
    """Walk-forward: expanding window, re-opt yearly (cointegration gate), trade 12 months."""
    idx = logs.index
    first = idx.searchsorted(pd.Timestamp(WF_FIRST))
    steps = list(range(first, len(idx), WF_STEP))
    seg = []
    for i, s in enumerate(steps):
        e = steps[i + 1] if i + 1 < len(steps) else len(idx)
        train = slice(0, s)
        test = slice(s, e)
        _, adf = engle_granger(logs.iloc[train])
        if np.isnan(adf) or adf > -2.86:
            continue  # cointegration not stable -> no trading that year (pre-registered)
        out, _ = run_strategy(ratio.iloc[test], ret.iloc[test], wsum)
        seg.append(out["pnl"])
    if not seg:
        return pd.Series(dtype=float)
    return pd.concat(seg)


def main():
    key = sys.argv[1]
    quick = "--quick" in sys.argv
    spec = SPREADS[key]
    t0 = time.time()
    common, ratio, ret, weights = load_ratio(key)
    wsum = ratio.wsum
    logs = np.log(common)
    t_load = time.time() - t0

    ism = ratio.index <= IS_END
    oosm = ratio.index > IS_END

    t0 = time.time()
    _, adf_is = engle_granger(logs.loc[ism])
    _, adf_oos = engle_granger(logs.loc[oosm])
    t_eg = time.time() - t0

    t0 = time.time()
    out_is, trades_is = run_strategy(ratio.loc[ism], ret.loc[ism], wsum)
    st1 = stats_of(out_is["pnl"], trades_is, "IS")
    roundtrip = 2.0 * COST_PER_LEG * wsum
    st1["mean_vs_cost_x"] = round(st1["mean"] / (roundtrip * 100), 2)
    t_s1 = time.time() - t0

    t0 = time.time()
    nperm = 100 if quick else N_PERM
    perm_means = []
    for _ in range(nperm):
        plogs = block_permute(logs.loc[ism], RNG)
        pratio = pd.Series(plogs.values @ weights, index=plogs.index)
        pret = pratio.diff()
        po, _ = run_strategy(pratio, pret, wsum)
        perm_means.append(po["pnl"].mean())
    p_stage2 = float(np.mean([m >= st1["mean"] / 252 for m in perm_means]))
    t_s2 = time.time() - t0

    t0 = time.time()
    wf_pnl = wf_pipeline(logs, ratio, ret, weights, wsum)
    st3 = stats_of(wf_pnl, [], "WF")
    t_s3 = time.time() - t0

    t0 = time.time()
    wf_means = []
    for _ in range(nperm):
        plogs = block_permute(logs, RNG)
        pratio = pd.Series(plogs.values @ weights, index=plogs.index)
        pret = pratio.diff()
        pp = wf_pipeline(plogs, pratio, pret, weights, wsum)
        wf_means.append(pp.mean() if len(pp) else np.nan)
    wf_means = np.array([m for m in wf_means if m == m])
    base_wf_daily = st3["mean"] / 252 if st3["mean"] == st3["mean"] else 0.0
    p_stage4 = float(np.mean(wf_means >= base_wf_daily)) if len(wf_means) else np.nan
    t_s4 = time.time() - t0

    out_oos, trades_oos = run_strategy(ratio.loc[oosm], ret.loc[oosm], wsum)
    st_oos = stats_of(out_oos["pnl"], trades_oos, "OOS")

    pnl_aligned = out_oos["pnl"]
    corrs = {}
    for fname, w, _ in [(f, w, c) for f, w, c in [] ] or [(f, w, None) for f, w in spec["legs"]]:
        lret = np.log(common[fname]).diff()
        corrs[fname] = round(float(pnl_aligned.corr(lret.reindex(pnl_aligned.index))), 3)

    roll_days = pd.Series(False, index=ratio.index)
    for fname, w, _ in [(f, w, None) for f, w in spec["legs"]]:
        lret = np.log(common[fname]).diff().abs()
        thresh = lret.rolling(90).mean() * 5
        hot = (lret > thresh) & thresh.notna()
        tot = ratio.diff().abs()
        unmirrored = hot & (tot < lret * 1.5)
        roll_days |= unmirrored.fillna(False)
    pnl_excl = out_oos["pnl"].copy()
    pnl_excl[roll_days.reindex(pnl_excl.index).fillna(False)] = 0.0
    edge_full = st_oos["mean"]
    edge_excl = float(pnl_excl.mean() * 252 * 100)
    roll_share = 1.0 - (edge_excl / edge_full) if edge_full > 0 else np.nan

    res = {
        "spread": key, "name": spec["name"], "mechanism": spec["mech"],
        "n_bars": int(len(ratio)), "is_bars": int(ism.sum()), "oos_bars": int(oosm.sum()),
        "adf_is": round(adf_is, 2), "adf_oos": round(adf_oos, 2),
        "coint_is": bool(adf_is < -2.86), "coint_oos": bool(adf_oos < -2.86),
        "stage1": st1, "stage2_p": round(p_stage2, 4), "stage3": st3,
        "stage4_p": round(float(p_stage4), 4) if p_stage4 == p_stage4 else None,
        "oos": st_oos, "corr_with_legs": corrs,
        "roll_probe": {"roll_days": int(roll_days.sum()), "edge_full_pct": round(edge_full, 3),
                       "edge_excl_pct": round(edge_excl, 3),
                       "roll_share_of_edge": round(roll_share, 3) if roll_share == roll_share else None},
        "params": {"lookback": LOOKBACK, "entry_z": ENTRY_Z, "tstop": TIME_STOP,
                   "cost_per_leg_pct": COST_PER_LEG * 100, "fin_per_day_pct": FIN_PER_DAY * 100,
                   "block": BLOCK, "n_perm": nperm, "quick": quick},
        "timing_s": {"load": round(t_load, 1), "eg": round(t_eg, 1), "stage1": round(t_s1, 1),
                     "stage2": round(t_s2, 1), "stage3": round(t_s3, 1), "stage4": round(t_s4, 1),
                     "total": round(sum([t_load, t_eg, t_s1, t_s2, t_s3, t_s4]), 1)},
    }
    print(json.dumps(res, indent=2, default=str))
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    with open(os.path.join(ROOT, "reports", f"spread_{key}_results.json"), "w") as f:
        json.dump(res, f, indent=2, default=str)
    print(f"\n=== {key}: stage4_p={res['stage4_p']} stage2_p={p_stage2:.4f} "
          f"stage3_sharpe={st3['sharpe']} stage3_t={st3['t']} "
          f"oos_mean={st_oos['mean']}% oos_t={st_oos['t']} adf_is={adf_is:.2f} adf_oos={adf_oos:.2f}")


if __name__ == "__main__":
    main()
