"""
pairs_coint_test.py — Cointegration pairs trading (stat-arb), candidate #1 from
the platform scan, tested through the strict six-gate battery.

Mechanism (QuantConnect research/15347, George J. Miao method, daily-frequency
adaptation on our local FX + metals universe):
  1. Universe: EURUSD, GBPUSD, AUDUSD, USDJPY, USDCAD, GOLD, SILVER (21 pairs).
  2. Every REEST days: OLS hedge ratio y = a + b*x + e on a TRAIN-day window.
     Engle-Granger ADF on the residual; pair is tradeable iff ADF t < CRIT.
  3. Trade only when cointegrated: z = (spread - mean)/std from the training
     window.  Enter long spread (long y, short b*x) when z < -ENTRY,
     short spread when z > +ENTRY.  Exit when |z| < EXIT.  Stop at STOP*std.
  4. Dollar-neutral, one unit of y vs b units of x.
  5. Costs: 1 pip per leg per side (entry+exit = 2 pips/leg, 2 legs).

Outputs: reports/pairs_coint_strict.csv/.md
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(11)

INSTR = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCAD", "GOLD", "SILVER"]
PIP = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "AUDUSD": 0.0001,
       "USDJPY": 0.01, "USDCAD": 0.0001, "GOLD": 0.1, "SILVER": 0.001}
# per-leg per-side cost in pips (conservative: spread + slippage)
LEG_COST_PIPS = 1.0

TRAIN = 126        # ~6 months of trading days
REEST = 21         # monthly re-estimation
CRIT = -3.37       # Engle-Granger 5% critical value (constant, no trend, T~130)
ENTRY = 2.33       # 99% confidence z
EXIT = 0.5
STOP = 4.0
MIN_TRADE_DAYS = 5

N_PERM = 1000
N_BOOT = 5000
IS_END = "2022-12-31"   # 2018-2022 in-sample, 2023-2026 holdout


def load_close(name):
    f = BASE / "market-data/raw/yahoo"
    cand = [f / (name + "_d.csv"), f / ("COMM_" + name + "_d.csv")]
    path = next((c for c in cand if c.exists()), None)
    if path is None:
        raise FileNotFoundError(f"no data for {name}")
    df = pd.read_csv(path)
    datecol = "Date" if "Date" in df.columns else "date"
    closecol = "Close" if "Close" in df.columns else "close"
    df = df.drop_duplicates(datecol, keep="last")
    df = df.set_index(pd.to_datetime(df[datecol]))[[closecol]].sort_index()
    df.columns = ["Close"]
    return df["Close"]


def adf_t(resid):
    """ADF(1) t-stat on the residual (constant, no trend)."""
    r = np.asarray(resid, dtype=float)
    y = np.diff(r)
    x1 = r[:-1]
    x2 = np.diff(r, prepend=r[0])[:-1]
    X = np.column_stack([np.ones(len(y)), x1, x2])
    X = X[~np.isnan(X).any(axis=1) & ~np.isnan(y)]
    y = y[~np.isnan(y)]
    if len(y) < 10:
        return 0.0
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid2 = y - X @ beta
    s2 = resid2 @ resid2 / (len(y) - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    se = math.sqrt(max(cov[1, 1], 1e-18))
    return beta[1] / se


def simulate_pair(close_a, close_b, names):
    """Return (dates, daily_net_returns, n_trades)."""
    df = pd.concat([close_a, close_b], axis=1).dropna()
    df.columns = ["A", "B"]
    dates = df.index
    n = len(df)
    pos = 0.0          # +1 long spread (long A, short b*B), -1 short spread
    beta = 0.0
    mean_z = 0.0
    std_z = 1.0
    tradeable = False
    pnl = np.zeros(n)
    trade_days = 0
    cooldown = 0
    n_trades = 0
    cost_pct = (LEG_COST_PIPS * PIP[names[0]] / float(close_a.mean())
                + LEG_COST_PIPS * PIP[names[1]] / float(close_b.mean()))
    for i in range(TRAIN, n):
        if i % REEST == 0 or i == TRAIN:
            w = df.iloc[i - TRAIN:i]
            y = np.log(w["A"].to_numpy())
            x = np.log(w["B"].to_numpy())
            X = np.column_stack([np.ones(len(y)), x])
            beta_, *_ = np.linalg.lstsq(X, y, rcond=None)
            resid = y - X @ beta_
            t = adf_t(resid)
            tradeable = t < CRIT
            beta = beta_[1]
            mean_z = float(resid.mean())
            std_z = float(resid.std())
        if not tradeable or std_z < 1e-12:
            # force flat if no longer tradeable (no new entries, close open)
            if pos != 0.0:
                pnl[i] -= cost_pct * abs(pos)
                pos = 0.0
                cooldown = 5
            continue
        # daily spread move in log terms
        ra = df["A"].iloc[i] / df["A"].iloc[i - 1] - 1
        rb = df["B"].iloc[i] / df["B"].iloc[i - 1] - 1
        spread_move = ra - beta * rb
        pnl[i] = pos * spread_move
        if pos != 0.0:
            trade_days += 1
        # z of current spread
        yt = math.log(df["A"].iloc[i]); xt = math.log(df["B"].iloc[i])
        z = (yt - beta * xt - mean_z) / std_z
        if pos == 0.0:
            if cooldown > 0:
                cooldown -= 1
            elif z < -ENTRY:
                pos = 1.0; n_trades += 1; pnl[i] -= cost_pct
            elif z > ENTRY:
                pos = -1.0; n_trades += 1; pnl[i] -= cost_pct
        else:
            if abs(z) < EXIT or abs(z) > STOP or trade_days > 60:
                pos = 0.0; pnl[i] -= cost_pct; trade_days = 0; cooldown = 5
    return dates, pnl, n_trades


def stats(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 5 or x.std() == 0:
        return dict(mean=None, t=None)
    mu = x.mean()
    return dict(mean=float(mu), t=float(mu / x.std() * math.sqrt(n)))


def perm_signflip(actual, raw, n=N_PERM):
    raw = np.asarray(raw, dtype=float)
    flips = RNG.choice([-1.0, 1.0], size=(n, len(raw)))
    means = (flips * raw).mean(axis=1)
    return float((means >= actual).sum() + 1) / (n + 1)


def wf_monthly(net, dates, trail_months=12, min_ev=20):
    df = pd.DataFrame({"d": pd.to_datetime(dates), "net": np.asarray(net, dtype=float)})
    df["m"] = df["d"].dt.to_period("M")
    out = {}
    for m in sorted(df["m"].unique()):
        trail = df[df["m"] < m].tail(trail_months * 31)
        if len(trail) < min_ev:
            continue
        trade = trail["net"].mean() > 0
        this = df[df["m"] == m]
        out[m] = float(this["net"].mean()) if (trade and len(this)) else 0.0
    return pd.Series(out, dtype=float)


def wf_perm(actual, dates, pool, n=N_PERM):
    r = np.asarray(pool, dtype=float)
    dates = np.asarray(pd.to_datetime(dates))
    df = pd.DataFrame({"d": dates, "net": np.zeros(len(dates))})
    df["u"] = df["d"].dt.to_period("M").astype("int64")
    unit_codes = df.sort_values("d")["u"].to_numpy()
    starts = np.searchsorted(unit_codes, np.unique(unit_codes))
    ends = np.append(starts[1:], len(unit_codes))
    counts_u = (ends - starts).astype(float)
    cum = np.cumsum(counts_u)
    cnt = 1
    for _ in range(n):
        net = RNG.choice(r, len(dates), replace=True)
        sums = np.add.reduceat(net, starts)
        means = sums / counts_u
        out = np.zeros(len(means))
        for i in range(len(means)):
            lo = max(0, i - 12)
            trail_cnt = cum[i - 1] if i > 0 else 0
            if lo > 0:
                trail_cnt -= cum[lo - 1]
            if trail_cnt < 20 or lo >= i:
                continue
            if means[lo:i].mean() > 0:
                out[i] = means[i]
        if out.mean() >= actual:
            cnt += 1
    return cnt / (n + 1)


def bootstrap(wf, n=N_BOOT):
    wf = np.asarray(wf, dtype=float)
    if len(wf) < 3:
        return 1.0
    means = np.array([np.mean(RNG.choice(wf, len(wf), replace=True)) for _ in range(n)])
    return float(np.mean(means <= 0))


def main():
    closes = {k: load_close(k) for k in INSTR}
    pairs = [(a, b) for i, a in enumerate(INSTR) for b in INSTR[i + 1:]]
    rows = []
    for a, b in pairs:
        dates, pnl, n_tr = simulate_pair(closes[a], closes[b], (a, b))
        net = pd.Series(pnl, index=dates)
        is_ = net[net.index <= IS_END]
        oos = net[net.index > IS_END]
        is_s = stats(is_)
        oos_s = stats(oos)
        if is_s["mean"] is None or oos_s["mean"] is None:
            rows.append(dict(pair=f"{a}-{b}", trades=n_tr, n=len(net),
                             is_mean=None, is_t=None, p_is=None, ho_mean=None, ho_t=None,
                             p_ho=None, wf_mean=None, p_wf=None, boot_p=None, trim=None,
                             VERDICT="INSUFFICIENT", gates="no trades in IS or OOS"))
            continue
        p_is = perm_signflip(is_s["mean"], is_.to_numpy())
        p_ho = perm_signflip(oos_s["mean"], oos.to_numpy())
        wf = wf_monthly(net.to_numpy(), dates)
        wf_mean = float(wf.mean()) if len(wf) else None
        pool = net.to_numpy()
        p_wf = wf_perm(wf_mean if wf_mean is not None else -1e9, dates, pool)
        boot_p = bootstrap(wf.values) if wf_mean is not None else 1.0
        yrs = net.groupby(net.index.year).sum()
        trim = float(yrs.sort_values().iloc[1:-1].mean()) if len(yrs) >= 3 else None
        gates = {
            "|t_is|>2": is_s["t"] is not None and abs(is_s["t"]) > 2,
            "p_is<0.01": p_is < 0.01,
            "ho t>2&p<0.05": oos_s["t"] is not None and oos_s["t"] > 2 and p_ho < 0.05,
            "wf>0&p<0.05": wf_mean is not None and wf_mean > 0 and p_wf < 0.05,
            "boot<0.05": boot_p < 0.05,
            "trim>0": trim is not None and trim > 0,
        }
        rows.append(dict(pair=f"{a}-{b}", trades=n_tr, n=len(net),
                         is_mean=round(is_s["mean"], 5), is_t=round(is_s["t"], 2),
                         p_is=round(p_is, 4), ho_mean=round(oos_s["mean"], 5),
                         ho_t=round(oos_s["t"], 2), p_ho=round(p_ho, 4),
                         wf_mean=round(wf_mean, 5) if wf_mean else 0.0,
                         p_wf=round(p_wf, 4), boot_p=round(boot_p, 4),
                         trim=round(trim, 5) if trim is not None else 0.0,
                         VERDICT="PASS" if all(gates.values()) else "FAIL",
                         gates="; ".join(k for k, v in gates.items() if not v) or "all pass"))
    res = pd.DataFrame(rows).sort_values("is_t", key=lambda s: s.abs(), ascending=False)
    res.to_csv(OUT / "pairs_coint_strict.csv", index=False)
    lines = ["# Cointegration pairs trading — STRICT battery (candidate #1 from platform scan)", "",
             "Mechanism: QC research/15347 (Miao).  Daily adaptation on local universe. "
             "Train 126d, re-estimate monthly, ADF < -3.37 required, z+-2.33 enter / 0.5 exit / 4 sigma stop. "
             "Costs: 1 pip/leg/side.", "",
             "| pair | trades | IS% | IS t | p_is | HO% | HO t | p_ho | WF% | p_wf | boot | trim | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        lines.append(f"| {r['pair']} | {r['trades']} | {r['is_mean']*100:+.3f} | {r['is_t']:+.2f} | {r['p_is']:.3f} | "
                     f"{r['ho_mean']*100:+.3f} | {r['ho_t']:+.2f} | {r['p_ho']:.3f} | {r['wf_mean']*100:+.3f} | "
                     f"{r['p_wf']:.3f} | {r['boot_p']:.3f} | {r['trim']*100:+.3f} | **{r['VERDICT']}** |")
    lines += ["", "Failed gates:", ""]
    for _, r in res.iterrows():
        lines.append(f"- {r['pair']}: {r['gates']}")
    (OUT / "pairs_coint_strict.md").write_text("\n".join(lines), encoding="utf-8")
    print(res[["pair", "trades", "is_mean", "is_t", "p_is", "ho_mean", "ho_t", "p_ho",
               "wf_mean", "p_wf", "boot_p", "trim", "VERDICT"]].to_string(index=False))
    print("\n[saved]", OUT / "pairs_coint_strict.md")


if __name__ == "__main__":
    main()
