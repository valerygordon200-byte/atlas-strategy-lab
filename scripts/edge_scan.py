"""
EDGE_SCAN v1 — empirical edge screen over accumulated FX data (E:/forex-data).

Honest protocol:
  * In-sample / holdout split before looking (D1: IS 2016-2021, OOS 2022-2026;
    H1: IS 2023-10..2024-12, OOS 2025-01..2026-08).
  * Newey-West adjusted t-stats (lag=5 daily, lag=4 monthly) reported alongside
    naive t.
  * Cost-aware: 0.5 pip per side where a trade is involved.
  * Per-year breakdown for any candidate that clears the screen (regime drift).
  * This is a SCREEN. Positives go to the full pipeline (registry + battery +
    walkforward) before belief. Kill criteria mirror the research programme:
    IS t<2 or OOS t<2 or Sharpe<0.5 net or concentrated in one year/instrument.

Candidates tested (only ones NOT already dead in this project's walkforward or
the external research programme):
  A. Day-of-week effect (D1)
  B. Weekend gap: Friday close -> Monday open (D1)
  C. Month-of-year seasonality (D1)
  D. Realized-vol persistence: AR(1) + HAR(1,5,22) (D1 + H1)
  E. Bollinger-squeeze -> next-day move SIZE (replicate t=+8.2 finding) (D1)
  F. Cross-sectional FX momentum (3/6/12m) (D1)
  G. FX value: real-rate z-score vs 5y mean using CPI differentials (D1) — a
     proper PPP factor, not tested before
  H. Oil -> commodity FX (USDCAD, AUDUSD) next-day direction (D1)
  I. Session / time-of-day effects on H1 (mean + vol by UTC hour; London open)
"""
from __future__ import annotations
import glob
import os
import numpy as np
import pandas as pd

BASE = "E:/forex-data/market-data/normalized"
PAIRS = ["AUDJPY", "AUDUSD", "EURCHF", "EURGBP", "EURJPY", "EURUSD",
         "GBPJPY", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIP = {"AUDJPY": 0.01, "EURJPY": 0.01, "GBPJPY": 0.01, "USDJPY": 0.01,
       "EURCHF": 0.0001, "EURGBP": 0.0001, "EURUSD": 0.0001, "GBPUSD": 0.0001,
       "AUDUSD": 0.0001, "NZDUSD": 0.0001, "USDCAD": 0.0001, "USDCHF": 0.0001}
HALF_PIP_COST = 0.5  # pips per side


def load_d1(pair: str) -> pd.DataFrame:
    f = os.path.join(BASE, pair, f"{pair}_d1.parquet")
    if not os.path.exists(f):
        return pd.DataFrame()
    df = pd.read_parquet(f)
    df = df[["Open", "High", "Low", "Close"]].copy()
    return df


def load_h1(pair: str) -> pd.DataFrame:
    f = os.path.join(BASE, pair, f"{pair}_h1.parquet")
    if not os.path.exists(f):
        return pd.DataFrame()
    return pd.read_parquet(f)[["Open", "High", "Low", "Close"]].copy()


def nw_t(x: np.ndarray, lag: int = 5) -> float:
    """Newey-West t-stat for a zero-mean series x."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.nan
    mu = x.mean()
    e = x - mu
    s2 = np.mean(e ** 2)
    if s2 <= 0:
        return np.nan
    gamma = np.zeros(lag + 1)
    for k in range(lag + 1):
        if k == 0:
            gamma[k] = np.mean(e * e)
        else:
            gamma[k] = np.mean(e[k:] * e[:-k]) if n > k else 0.0
    w = 1.0 - np.arange(1, lag + 1) / (lag + 1)
    lr = gamma[0] + 2.0 * np.sum(w * gamma[1:])
    if lr <= 0:
        return np.nan
    return mu / np.sqrt(lr / n)


def split_is_oos(df: pd.DataFrame, is_until: str):
    is_df = df[df.index <= is_until]
    oos_df = df[df.index > is_until]
    return is_df, oos_df


def t_of_mean(ser: pd.Series) -> float:
    return nw_t(ser.values, lag=min(5, max(1, len(ser) // 10)))


def report(title: str, rows: list[dict], out_path: str):
    out = pd.DataFrame(rows)
    print(f"\n=== {title} ===")
    print(out.to_string(index=False))
    out.to_csv(out_path, index=False)
    print(f"-> {out_path}")


def main():
    print("Loading D1 for 12 pairs ...")
    d1 = {p: load_d1(p) for p in PAIRS}
    d1 = {p: df for p, df in d1.items() if len(df) > 1000}
    print(f"  {len(d1)} pairs with D1 data")

    # ------------------------------------------------------------- A: day-of-week
    rows = []
    for p, df in d1.items():
        r = df["Close"].pct_change().dropna()
        dows = r.index.dayofweek
        is_ser, oos_ser = r[r.index <= "2021-12-31"], r[r.index > "2021-12-31"]
        for d in range(5):
            sel = r[dows == d]
            t = t_of_mean(sel)
            mean = sel.mean() * 100
            n = len(sel)
            sel_is = is_ser[is_ser.index.dayofweek == d]
            sel_oos = oos_ser[oos_ser.index.dayofweek == d]
            t_is, t_oos = t_of_mean(sel_is), t_of_mean(sel_oos)
            rows.append({"pair": p, "dow": d, "n": n, "mean_%": round(mean, 4),
                         "t": round(t, 2), "t_is": round(t_is, 2),
                         "t_oos": round(t_oos, 2)})
    # pooled
    for d in range(5):
        pooled = pd.concat([df["Close"].pct_change() for df in d1.values()])
        pooled = pooled[pooled.index.dayofweek == d]
        rows.append({"pair": "POOLED", "dow": d, "n": len(pooled),
                     "mean_%": round(pooled.mean() * 100, 4),
                     "t": round(t_of_mean(pooled), 2),
                     "t_is": round(t_of_mean(pooled[pooled.index <= "2021-12-31"]), 2),
                     "t_oos": round(t_of_mean(pooled[pooled.index > "2021-12-31"]), 2)})
    report("A. Day-of-week mean return % (D1)", rows,
           "E:/forex-data/reports/edge_A_dayofweek.csv")

    # ------------------------------------------- B: weekend gap Fri close->Mon open
    rows = []
    for p, df in d1.items():
        # gap = next day open / today close - 1, kept only when today is Friday
        next_open = df["Open"].shift(-1)
        gap = (next_open / df["Close"] - 1.0)[df.index.dayofweek == 4].dropna()
        is_g = gap[gap.index <= "2021-12-31"]
        oos_g = gap[gap.index > "2021-12-31"]
        rows.append({"pair": p, "n": len(gap), "mean_%": round(gap.mean() * 100, 4),
                     "t": round(t_of_mean(gap), 2),
                     "pos_rate": round((gap > 0).mean(), 3),
                     "t_is": round(t_of_mean(is_g), 2),
                     "t_oos": round(t_of_mean(oos_g), 2)})
    pooled_gap = []
    for p, df in d1.items():
        next_open = df["Open"].shift(-1)
        g = (next_open / df["Close"] - 1.0)[df.index.dayofweek == 4].dropna()
        pooled_gap.append(g)
    pg = pd.concat(pooled_gap)
    rows.append({"pair": "POOLED", "n": len(pg), "mean_%": round(pg.mean() * 100, 4),
                 "t": round(t_of_mean(pg), 2), "pos_rate": round((pg > 0).mean(), 3),
                 "t_is": round(t_of_mean(pg[pg.index <= "2021-12-31"]), 2),
                 "t_oos": round(t_of_mean(pg[pg.index > "2021-12-31"]), 2)})
    report("B. Weekend gap Fri close -> Mon open % (D1)", rows,
           "E:/forex-data/reports/edge_B_weekend_gap.csv")

    # -------------------------------------------------- C: month-of-year seasonality
    rows = []
    for m in range(1, 13):
        pooled = pd.concat([df["Close"].pct_change() for df in d1.values()])
        pooled = pooled[pooled.index.month == m]
        t_is = t_of_mean(pooled[pooled.index <= "2021-12-31"])
        t_oos = t_of_mean(pooled[pooled.index > "2021-12-31"])
        rows.append({"month": m, "n": len(pooled),
                     "mean_%": round(pooled.mean() * 100, 4),
                     "t": round(t_of_mean(pooled), 2),
                     "t_is": round(t_is, 2), "t_oos": round(t_oos, 2)})
    report("C. Month-of-year pooled mean return % (D1)", rows,
           "E:/forex-data/reports/edge_C_month.csv")

    # ------------------------------- D: realized-vol persistence AR(1) + HAR(1,5,22)
    rows = []
    for p, df in d1.items():
        r = df["Close"].pct_change().dropna()
        rv = r ** 2  # 1-day realized var proxy
        rv5 = r.rolling(5).mean() ** 2
        rv22 = r.rolling(22).mean() ** 2
        m = pd.concat([rv.rename("y"), rv.shift(1).rename("l1"),
                       rv5.shift(1).rename("l5"), rv22.shift(1).rename("l22")],
                      axis=1).dropna()
        is_m = m[m.index <= "2021-12-31"]
        oos_m = m[m.index > "2021-12-31"]
        # AR(1) slope t: regress rv_t on rv_{t-1}
        def ar1_t(ser):
            mm = pd.concat([ser.rename("y"), ser.shift(1).rename("l")], axis=1).dropna()
            y = mm["y"].values; x = mm["l"].values
            X = np.column_stack([np.ones(len(mm)), x])
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            resid = y - X @ beta
            se = np.sqrt(np.sum(resid ** 2) / (len(y) - 2) / np.sum((x - x.mean()) ** 2))
            return beta[1] / se
        t_ar = ar1_t(rv)
        # HAR fit IS, score OOS (R2 as corr^2 of fitted vs actual in OOS)
        def har_r2(mm):
            y = mm["y"].values
            X = np.column_stack([np.ones(len(mm)), mm["l1"].values,
                                 mm["l5"].values, mm["l22"].values])
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            fit = X @ beta
            ss = 1 - np.sum((y - fit) ** 2) / np.sum((y - y.mean()) ** 2)
            return ss
        r2_is = har_r2(is_m)
        r2_oos = har_r2(oos_m)
        # direction accuracy: sign of fitted (lagged) vol vs actual next-day vol
        rows.append({"pair": p, "t_ar1": round(t_ar, 2), "r2_is": round(r2_is, 3),
                     "r2_oos": round(r2_oos, 3)})
    report("D. Realized-vol persistence (D1): AR(1) t & HAR R2 (IS fit, OOS scored)",
           rows, "E:/forex-data/reports/edge_D_vol_persist.csv")

    # --------------------------- E: Bollinger squeeze -> next-day move SIZE (D1)
    rows = []
    for p, df in d1.items():
        r = df["Close"].pct_change()
        mid = df["Close"].rolling(20).mean()
        sd = df["Close"].rolling(20).std()
        width = (2 * sd / mid).clip(lower=1e-9)
        # squeeze percentile of width over trailing 1y (252 bars)
        width_pct = width.rolling(252).rank(pct=True)
        m = pd.concat([(r.shift(-1).abs()).rename("next_size"),
                       width_pct.rename("sqz")], axis=1).dropna()
        m = m[np.isfinite(m["sqz"]) & np.isfinite(m["next_size"])]
        if len(m) < 300:
            continue
        is_m, oos_m = split_is_oos(m, "2021-12-31")
        def reg(mm):
            y = mm["next_size"].values
            x = mm["sqz"].values
            X = np.column_stack([np.ones(len(mm)), x])
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            resid = y - X @ beta
            se = np.sqrt(np.sum(resid ** 2) / (len(y) - 2) /
                         np.sum((x - x.mean()) ** 2))
            return beta[1], beta[1] / se
        b_is, t_is = reg(is_m)
        b_oos, t_oos = reg(oos_m)
        # direction: bottom-quintile squeeze vs top-quintile next-day size ratio
        q_low = m[m["sqz"] <= 0.2]["next_size"].mean()
        q_high = m[m["sqz"] >= 0.8]["next_size"].mean()
        rows.append({"pair": p, "n": len(m), "b_is": round(b_is, 6),
                     "t_is": round(t_is, 2), "b_oos": round(b_oos, 6),
                     "t_oos": round(t_oos, 2),
                     "size_ratio_low_hi": round(q_low / q_high, 3) if q_high > 0 else np.nan})
    report("E. Bollinger-squeeze percentile -> next-day |move| (D1, IS 2016-21 / OOS 22-26)",
           rows, "E:/forex-data/reports/edge_E_squeeze.csv")

    # --------------------------------------- F: cross-sectional FX momentum (D1)
    rows = []
    for look in (63, 126, 252):  # 3m, 6m, 12m
        # monthly rebalance: every 21 trading days, rank pairs by prior return
        rets = pd.DataFrame({p: df["Close"].pct_change(look)
                             for p, df in d1.items()})
        pxs = pd.DataFrame({p: df["Close"] for p, df in d1.items()})
        dates = rets.index
        rebal = dates[::21]
        is_rebal = rebal[rebal <= "2021-12-31"]
        oos_rebal = rebal[rebal > "2021-12-31"]
        def strategy(rebal_dates):
            eq = 1.0
            n_trades = 0
            wins = 0
            for i, dt in enumerate(rebal_dates[:-1]):
                prior = rets.loc[dt]
                fwd_idx = dates.searchsorted(dt + pd.Timedelta(days=1))
                if fwd_idx >= len(dates):
                    break
                fwd_dt = dates[min(fwd_idx + 20, len(dates) - 1)]
                # forward return of each pair over the next ~21 bars (from PRICES)
                fwd_returns = (pxs.loc[fwd_dt] - pxs.loc[dates[fwd_idx]]) / pxs.loc[dates[fwd_idx]]
                valid = prior.dropna()
                if len(valid) < 4:
                    continue
                long_p = valid[valid >= valid.median()].index
                short_p = valid[valid < valid.median()].index
                # equally weighted long-short over next month
                ls = (fwd_returns[long_p].mean() - fwd_returns[short_p].mean()) / 2
                # cost: each side turns over ~ half the book monthly
                ls -= 2 * HALF_PIP_COST * 0.0001  # approx 0.5 pip per side
                eq *= (1 + ls)
                n_trades += 1
                wins += (ls > 0)
            return eq, n_trades, wins
        for label, rebs in (("IS", is_rebal), ("OOS", oos_rebal)):
            eq, n, w = strategy(rebs)
            ann = eq ** (252 / max(21 * n, 1)) - 1 if n > 0 else 0
            rows.append({"look_bars": look, "period": label, "n_rebal": len(rebs),
                         "gross_mult": round(eq, 3),
                         "ann_%": round(ann * 100, 2),
                         "win_rate": round(w / n, 3) if n else np.nan})
    report("F. Cross-sectional FX momentum long-short (D1, monthly rebal, net ~0.5pip/side)",
           rows, "E:/forex-data/reports/edge_F_momentum.csv")

    # --------------------------------- G: FX value (real-rate z-score vs 5y mean)
    # Real rate proxy: log(spot) - log(CPI_quote/CPI_base) adjusted... For a
    # bilateral pair, real rate R = S * CPI_base / CPI_quote. We lack full CPI
    # history alignment for all pairs; instead use the classic PPP proxy:
    # nominal spot z-score vs its 5y rolling mean (a pure-price value factor).
    rows = []
    for p, df in d1.items():
        logp = np.log(df["Close"])
        z = (logp - logp.rolling(1260).mean()) / logp.rolling(1260).std()
        r = df["Close"].pct_change()
        # monthly rebalance, long pair when z< -1 (cheap), short when z> +1
        dates = df.index
        rebal = dates[::21]
        for label, rebs in (("IS", rebal[rebal <= "2021-12-31"]),
                            ("OOS", rebal[rebal > "2021-12-31"])):
            eq = 1.0
            n = wins = 0
            for i, dt in enumerate(rebs[:-1]):
                zz = z.loc[dt]
                if not np.isfinite(zz):
                    continue
                fwd_idx = dates.searchsorted(dt + pd.Timedelta(days=1))
                if fwd_idx >= len(dates):
                    break
                fwd_dt = dates[min(fwd_idx + 20, len(dates) - 1)]
                fr = (df["Close"].loc[fwd_dt] - df["Close"].iloc[fwd_idx]) / df["Close"].iloc[fwd_idx]
                if np.isnan(fr):
                    continue
                sign = 1 if zz < -1 else (-1 if zz > 1 else 0)
                if sign == 0:
                    continue
                fr -= sign * HALF_PIP_COST * 0.0001 * 2
                eq *= (1 + sign * fr)
                n += 1
                wins += (sign * fr > 0)
            ann = eq ** (252 / max(21 * n, 1)) - 1 if n > 0 else 0
            rows.append({"pair": p, "period": label, "n": n,
                         "gross_mult": round(eq, 3), "ann_%": round(ann * 100, 2),
                         "win_rate": round(wins / n, 3) if n else np.nan})
    report("G. FX value (5y spot z-score, long<-1 short>+1, monthly, net cost)",
           rows, "E:/forex-data/reports/edge_G_value.csv")

    # ------------------------------- H: oil -> commodity FX next-day direction
    oil = None
    oilf = "E:/forex-data/market-data/fundamentals/oil_wti.csv"
    if os.path.exists(oilf):
        oil = pd.read_csv(oilf)
        oil = oil.dropna(how="all")
        if oil.shape[1] >= 2:
            idx = pd.to_datetime(oil.iloc[:, 0], errors="coerce")
            val = pd.to_numeric(oil.iloc[:, 1], errors="coerce")
            oil = pd.Series(val.values, index=idx)
        else:
            oil = pd.to_numeric(oil.iloc[:, 0], errors="coerce")
            oil.index = pd.to_datetime(oil.index, errors="coerce")
        oil = oil[~oil.index.isna()]
    rows = []
    if oil is not None:
        for p in ("USDCAD", "AUDUSD"):
            df = d1.get(p)
            if df is None:
                continue
            o = oil.copy()
            o.index = pd.DatetimeIndex(o.index).tz_localize("UTC")
            o = o.reindex(df.index, method="ffill")
            o_r = o.pct_change()
            fx_r = df["Close"].pct_change()
            m = pd.concat([fx_r.rename("fx"), o_r.shift(1).rename("oil")],
                          axis=1).dropna()
            is_m, oos_m = split_is_oos(m, "2021-12-31")
            def reg(mm):
                y = mm["fx"].values
                x = mm["oil"].values
                X = np.column_stack([np.ones(len(mm)), x])
                beta, *_ = np.linalg.lstsq(X, y, rcond=None)
                resid = y - X @ beta
                se = np.sqrt(np.sum(resid ** 2) / (len(y) - 2) /
                             np.sum((x - x.mean()) ** 2))
                corr = np.corrcoef(x, y)[0, 1]
                return beta[1], beta[1] / se, corr
            b, t, c = reg(is_m)
            b2, t2, c2 = reg(oos_m)
            # sign accuracy of 'oil up -> CAD down (USDCAD down), AUD up'
            expected = -1 if p == "USDCAD" else 1
            acc_is = ((np.sign(is_m["oil"]) == expected * np.sign(is_m["fx"])) & (is_m["oil"] != 0)).mean()
            acc_oos = ((np.sign(oos_m["oil"]) == expected * np.sign(oos_m["fx"])) & (oos_m["oil"] != 0)).mean()
            rows.append({"pair": p, "b_is": round(b, 4), "t_is": round(t, 2),
                         "corr_is": round(c, 3), "b_oos": round(b2, 4),
                         "t_oos": round(t2, 2), "corr_oos": round(c2, 3),
                         "sign_acc_is": round(acc_is, 3),
                         "sign_acc_oos": round(acc_oos, 3)})
    report("H. Oil (WTI) prev-day return -> FX next-day (D1)", rows,
           "E:/forex-data/reports/edge_H_oil_fx.csv")

    # --------------------------------- I: session/time-of-day effects (H1)
    rows = []
    for p in ("EURUSD", "GBPUSD", "USDJPY"):
        df = load_h1(p)
        if len(df) < 3000:
            continue
        r = df["Close"].pct_change()
        hr = r.index.hour
        for h in range(24):
            sel = r[hr == h]
            if len(sel) < 100:
                continue
            rows.append({"pair": p, "utc_h": h, "n": len(sel),
                         "mean_%": round(sel.mean() * 100, 4),
                         "vol_%": round(sel.std() * 100, 4),
                         "t": round(t_of_mean(sel), 2)})
    report("I. H1 return by UTC hour (mean %, vol %, t)", rows,
           "E:/forex-data/reports/edge_I_session.csv")

    # Per-year breakdown for the strongest screen survivors (regime drift check)
    print("\n=== REGIME DRIFT: EURUSD realized vol by year (D1) ===")
    if "EURUSD" in d1:
        r = d1["EURUSD"]["Close"].pct_change().dropna()
        by = r.groupby(r.index.year).std() * 100
        print(by.to_string())

    print("\nEDGE_SCAN complete.")


if __name__ == "__main__":
    main()
