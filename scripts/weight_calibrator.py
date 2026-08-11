#!/usr/bin/env python3
"""weight_calibrator.py — historical weight calibration ("weights from price charts").

For each asset, regress MONTHLY returns on its available fundamental factors
(standardised OLS): the standardised beta of each factor IS its historical
importance for that asset. Blended with the mechanism design weights from the
bookshelf: weight_final = 0.4*design + 0.6*historical (renormalised).

IS/OOS split 2016-08..2021-12 / 2022-01..2026-08 to check sign stability —
a factor whose sign flips out-of-sample is not trustworthy regardless of its
full-sample t.

Honest limits, stated up front:
  - factors we LACK data for (central-bank gold buying, OPEC decisions,
    China demand, earnings, ETF flows) are absent from the historical fit and
    keep only their design weight, flagged "hist=MISSING-DATA".
  - monthly frequency hides within-month relationships; these are long-horizon
    sensitivities, not trading signals.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
RNG = np.random.default_rng(20260811)
IS_END = "2021-12-31"
MIN_P = 20
Z_FLOOR = 1e-12
Z_CLIP = 8.0

CCY = {"GOLD": "USD", "SILVER": "USD", "OIL": "USD",
       "USDJPY": "JPY", "EURUSD": "EUR", "GBPUSD": "GBP", "AUDUSD": "AUD"}

FACTOR_SETS = {
    "GOLD":   ["real_yield_10y", "usd_basket", "usd_cpi_surprise_z", "policy_rate_us"],
    "SILVER": ["real_yield_10y", "usd_basket", "usd_cpi_surprise_z", "policy_rate_us"],
    "OIL":    ["inventory_surprise_z", "usd_basket", "policy_rate_us"],
    "USDJPY": ["rate_differential_us_jp", "usd_basket", "usd_cpi_surprise_z_drift"],
    "EURUSD": ["rate_differential_us_eur", "usd_basket", "usd_cpi_surprise_z", "eur_cpi_surprise_z"],
    "GBPUSD": ["rate_differential_us_gbp", "usd_basket", "usd_cpi_surprise_z", "gbp_cpi_surprise_z"],
    "AUDUSD": ["rate_differential_us_aud", "usd_basket", "usd_cpi_surprise_z", "aud_cpi_surprise_z"],
}
DIFF_MAP = {"USDJPY": "rate_differential_us_jp", "EURUSD": "rate_differential_us_eur",
            "GBPUSD": "rate_differential_us_gbp", "AUDUSD": "rate_differential_us_aud"}
CPI_MAP = {"USDJPY": "usd_cpi_surprise_z_drift"}


def monthly_asset_ret(asset):
    """Last-close-to-last-close monthly log return."""
    df = pd.read_parquet(BASE / f"market-data/normalized/{asset}/{asset}_d1.parquet")
    c = df["Close"]
    mc = c.resample("ME").last().dropna()
    mc.index = mc.index.tz_localize(None)
    r = np.log(mc).diff().dropna()
    return r.rename(asset)


def fr_monthly(fname):
    df = pd.read_csv(BASE / "market-data/fundamentals" / fname)
    dcol = "date" if "date" in df.columns else "observation_date"
    df[dcol] = pd.to_datetime(df[dcol])
    df = df.set_index(dcol).iloc[:, 0].astype(float)
    return df.resample("ME").last()


def cb_gold_monthly():
    """Central-bank net gold purchases (tonnes) — monthly mean of the daily/weekly
    CSV the laptop delivers (T1). Graceful: returns empty until the file lands."""
    p = BASE / "market-data/fundamentals" / "central_bank_gold.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(p)
    dcol = "date" if "date" in df.columns else "observation_date"
    vcol = "total_net_purchases_tonnes" if "total_net_purchases_tonnes" in df.columns         else (df.columns[1] if df.shape[1] > 1 else None)
    if vcol is None:
        return pd.Series(dtype=float)
    df[dcol] = pd.to_datetime(df[dcol])
    s = df.set_index(dcol)[vcol].astype(float)
    return s.resample("ME").mean().rename("central_bank_net_buying")


def policy_rates_monthly():
    df = pd.read_csv(BASE / "market-data/rates/policy_rates.csv", parse_dates=["date"])
    df = df.set_index("date")
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.resample("ME").last()


def surprise_z(currency, title_contains):
    """Per-title expanding z (min 20, floor, clip), no threshold; monthly mean z."""
    ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)
    ev = ev[(ev["currency"] == currency) &
            ev["title"].str.contains(title_contains, case=False, regex=False) &
            ev["actual"].notna() & ev["forecast"].notna()].copy()
    if ev.empty:
        return pd.Series(dtype=float)
    ev["surprise"] = pd.to_numeric(ev["actual"], errors="coerce") - pd.to_numeric(ev["forecast"], errors="coerce")
    ev = ev.dropna(subset=["surprise"]).sort_values("date_utc")
    z = []
    for _, g in ev.groupby("title"):
        s = g["surprise"]
        mu = s.expanding(min_periods=MIN_P).mean().shift(1)
        sd = s.expanding(min_periods=MIN_P).std().shift(1)
        gz = ((s - mu) / sd.where(sd > Z_FLOOR)).clip(-Z_CLIP, Z_CLIP)
        idx = pd.PeriodIndex(g["date_utc"].dt.tz_localize(None).dt.to_period("M"), freq="M").to_timestamp(how="end").normalize()
        z.append(pd.Series(gz.values, index=idx))
    if not z:
        return pd.Series(dtype=float)
    zs = pd.concat(z)
    return zs.groupby(level=0).mean()


def dxy_monthly(pairs):
    rets = []
    for p in pairs:
        r = monthly_asset_ret(p)
        rets.append(r)
    d = pd.concat(rets, axis=1)
    d.columns = pairs
    # USD rises when USD-base pairs fall and quote-base pairs rise
    usd = (-d[["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"]].mean(axis=1)
           + d[["USDJPY", "USDCAD", "USDCHF"]].mean(axis=1)) / 2.0
    return usd.rename("dxy")


def std_ols(y, X):
    yz = (y - y.mean()) / y.std(ddof=0)
    Xz = (X - X.mean()) / X.std(ddof=0)
    A = np.column_stack([np.ones(len(Xz))] + [Xz[c].values for c in X.columns])
    beta, *_ = np.linalg.lstsq(A, yz.values, rcond=None)
    resid = yz.values - A @ beta
    rss = float((resid ** 2).sum())
    tss = float(((yz.values - yz.values.mean()) ** 2).sum())
    r2 = 1.0 - rss / tss
    n, k = A.shape
    se = np.sqrt((rss / (n - k)) * np.linalg.inv(A.T @ A).diagonal())
    tstats = beta / se
    return {"beta": {c: float(b) for c, b in zip(["intercept"] + X.columns.tolist(), beta)},
            "t": {c: float(t) for c, t in zip(["intercept"] + X.columns.tolist(), tstats)},
            "r2": float(r2), "n": n}


def main():
    rates = policy_rates_monthly()
    yield_us = fr_monthly("yield_usd.csv").rename("y10")
    cpi_us = fr_monthly("cpi_usd.csv").rename("cpi")
    cpi_yoy_us = cpi_us.pct_change(12).rename("cpi_yoy")
    real_yield = (yield_us - cpi_yoy_us).dropna().rename("real_yield")
    d_real_yield = real_yield.diff().rename("d_real_yield")

    dxy = dxy_monthly(["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF"])

    us_cpi_z = surprise_z("USD", "Inflation")
    eur_cpi_z = surprise_z("EUR", "Inflation")
    gbp_cpi_z = surprise_z("GBP", "Inflation")
    aud_cpi_z = surprise_z("AUD", "Inflation")
    eia_crude_z = surprise_z("USD", "EIA Crude")

    zseries = {"us_cpi_z": us_cpi_z, "eur_cpi_z": eur_cpi_z, "gbp_cpi_z": gbp_cpi_z,
               "aud_cpi_z": aud_cpi_z, "eia_crude_z": eia_crude_z}

    shelf = json.load(open(BASE / "market-data/bookshelf/bookshelf.json"))
    design = {a: {f["name"]: f["weight_design"] for f in fs}
              for a, fs in shelf["mechanism_factors"].items()}

    out = {"generated": "2026-08-11", "method": "monthly std-OLS; 0.4*design + 0.6*hist; "
                                            "IS 2016-08..2021-12, OOS 2022-01..2026-08",
           "assets": {}}
    rows = []
    for asset in FACTOR_SETS:
        y = monthly_asset_ret(asset)
        cb_gold = cb_gold_monthly()
        if (not cb_gold.empty and asset == "GOLD"
                and "central_bank_net_buying" not in FACTOR_SETS[asset]):
            FACTOR_SETS[asset] = ["central_bank_net_buying"] + FACTOR_SETS[asset]
        fmap = {"real_yield_10y": d_real_yield, "usd_basket": dxy,
                "central_bank_net_buying": cb_gold,
                "policy_rate_us": rates["USD"].diff(),
                "usd_cpi_surprise_z": us_cpi_z, "eur_cpi_surprise_z": eur_cpi_z,
                "gbp_cpi_surprise_z": gbp_cpi_z, "aud_cpi_surprise_z": aud_cpi_z,
                "inventory_surprise_z": eia_crude_z}
        if asset in DIFF_MAP:
            fmap[DIFF_MAP[asset]] = (rates["USD"] - rates[CCY[asset]]).diff()
        if asset in CPI_MAP:
            fmap[CPI_MAP[asset]] = us_cpi_z
        X = pd.concat([fmap[f].rename(f) for f in FACTOR_SETS[asset]], axis=1)
        panel = pd.concat([y, X], axis=1, sort=False).dropna()

        ism = panel.index <= IS_END
        full = std_ols(panel[asset], panel[FACTOR_SETS[asset]])
        isfit = std_ols(panel.loc[ism, asset], panel.loc[ism, FACTOR_SETS[asset]]) if ism.sum() > 20 else None
        oosfit = std_ols(panel.loc[~ism, asset], panel.loc[~ism, FACTOR_SETS[asset]]) if (~ism).sum() > 12 else None

        betas = {f: full["beta"][f] for f in FACTOR_SETS[asset]}
        absb = np.array([abs(v) for v in betas.values()])
        hist = {f: float(absb[i] / absb.sum()) for i, f in enumerate(FACTOR_SETS[asset])}
        sign_stable = {}
        if isfit and oosfit:
            for f in FACTOR_SETS[asset]:
                b_is, b_oos = isfit["beta"][f], oosfit["beta"][f]
                sign_stable[f] = bool(np.sign(b_is) == np.sign(b_oos))
        # blend with design weights (match names; design-only factors get hist=0)
        des = design.get(asset, {})
        merged = {}
        for f in FACTOR_SETS[asset]:
            d_w = des.get(f, 0.0)
            merged[f] = {"design": d_w, "hist": hist[f],
                         "beta": round(betas[f], 3), "t": round(full["t"][f], 2),
                         "sign_stable_oos": sign_stable.get(f)}
        # design-only factors (no historical data)
        for f, d_w in des.items():
            if f not in merged:
                merged[f] = {"design": d_w, "hist": None, "beta": None, "t": None,
                             "sign_stable_oos": None, "hist_data": "MISSING"}
        # blend
        wfinal = {}
        for f, v in merged.items():
            if v["hist"] is None:
                wfinal[f] = v["design"]
            else:
                wfinal[f] = 0.4 * v["design"] + 0.6 * v["hist"]
        tot = sum(wfinal.values())
        wfinal = {f: round(w / tot, 3) for f, w in wfinal.items()}
        for f, v in merged.items():
            v["weight_final"] = wfinal.get(f)
        out["assets"][asset] = {"n_months": full["n"], "r2_full": round(full["r2"], 3),
                                "factors": merged}
        rows.append((asset, full["r2"], "; ".join(f"{f}={merged[f]['weight_final']}" for f in merged)))

    (BASE / "market-data/bookshelf").mkdir(exist_ok=True)
    with open(BASE / "market-data/bookshelf/weights.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"{'asset':8s} {'R2':>6s}  weights (final, per factor)")
    for a, r2, w in rows:
        print(f"{a:8s} {r2:6.3f}  {w}")
    print("\nweights.json written to market-data/bookshelf/")


if __name__ == "__main__":
    main()
