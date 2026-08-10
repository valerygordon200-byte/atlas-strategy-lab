"""
news_family_strict.py — the STRICT six-gate battery on the surviving
news-drift variants (the ones that passed the lighter family screen).

Six gates, per the pre-registered protocol (same as strict_battery.py and
fx_strict_battery.py):
  A. in-sample excellence: |t| > 2
  B. in-sample 1000-perm sign-flip null: p < 0.01
  C. blind holdout: NW t > 2 AND perm p < 0.05
  D. walk-forward (profitability-gated, re-estimated): mean > 0 AND wf-perm p < 0.05
  E. 5000-bootstrap of the walk-forward: P(mean <= 0) < 0.05
  F. outlier-trimmed walk-forward mean > 0

Variants:
  D1 next-day (2015/2016-2026): the 5 pairs + basket; IS <= 2021-12-31.
  Intraday H1 (2023-10 -> 2026-08): USDJPY High-tier at horizons 1/2/4/8/12/24h,
    USDJPY all-tier 2h, basket-High 2h/4h; IS <= 2025-06-30.  Walk-forward is
    MONTHLY (trailing 12-month profitability gate) given the short window.

Outputs: reports/news_family_strict.csv + reports/news_family_strict.md
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

from edge_scan import PIP, load_d1, nw_t

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(7)

Z_THR = 0.5
RT_PIPS = 1.0
N_PERM = 1000
N_BOOT = 5000
CONV = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "USDJPY": 1, "USDCAD": 1}
PAIRS = ["USDJPY", "AUDUSD", "GBPUSD", "USDCAD", "EURUSD"]
H1_IS_END = "2025-06-30"
D1_IS_END = "2021-12-31"
HORIZONS = [1, 2, 4, 8, 12, 24]


def load_events():
    ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)
    ev = ev[(ev["currency"] == "USD") & (ev["impact"].isin(["High", "Medium"]))
            & ev["actual"].notna() & ev["forecast"].notna()].copy()
    ev["surprise"] = (pd.to_numeric(ev["actual"], errors="coerce") -
                      pd.to_numeric(ev["forecast"], errors="coerce"))
    ev = ev.dropna(subset=["surprise"]).sort_values("date_utc")
    ev["z"] = np.nan
    for title, g in ev.groupby("title"):
        g = g.sort_values("date_utc")
        s = g["surprise"]
        mu = s.expanding(min_periods=20).mean().shift(1)
        sd = s.expanding(min_periods=20).std().shift(1)
        z = (s - mu) / sd.where(sd > 1e-12)
        ev.loc[g.index, "z"] = z.clip(-8, 8)
    ev["date"] = pd.to_datetime(ev["date_utc"]).dt.date
    return ev[ev["z"].abs() >= Z_THR].reset_index(drop=True)


def load_h1(pair):
    df = pd.read_csv(BASE / "market-data/raw/yahoo" / f"{pair}_h1.csv", parse_dates=["Date"])
    df = df.drop_duplicates("Date", keep="last").sort_values("Date")
    return df.set_index("Date")[["Open", "Close"]]


def stats(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 5 or x.std() == 0:
        return dict(mean=None, t=None, nw=None, win=None)
    mu = x.mean()
    return dict(mean=float(mu), t=float(mu / x.std() * math.sqrt(n)),
                nw=float(nw_t(pd.Series(x), lag=5)), win=float((x > 0).mean()))


def trimmed_by_year(s, dates):
    df = pd.DataFrame({"d": pd.to_datetime(dates), "v": np.asarray(s, dtype=float)})
    ym = df.groupby(df["d"].dt.year)["v"].mean()
    if len(ym) < 3:
        return float(df["v"].mean())
    return float(ym.sort_values().iloc[1:-1].mean())


def perm_signflip(actual, raw, cost, n=N_PERM):
    raw = np.asarray(raw, dtype=float)
    cnt = 1
    for _ in range(n):
        flips = RNG.choice([-1.0, 1.0], len(raw))
        if (flips * raw - cost).mean() >= actual:
            cnt += 1
    return cnt / (n + 1)


def wf_yearly(net, dates, trail_years=3, min_ev=30):
    df = pd.DataFrame({"d": pd.to_datetime(dates), "net": np.asarray(net, dtype=float)})
    df["year"] = df["d"].dt.year
    out = {}
    for y in sorted(df["year"].unique()):
        trail = df[(df["year"] >= y - trail_years) & (df["year"] < y)]
        if len(trail) < min_ev:
            continue
        trade = trail["net"].mean() > 0
        this = df[df["year"] == y]
        out[y] = float(this["net"].mean()) if (trade and len(this)) else 0.0
    return pd.Series(out, dtype=float)


def wf_monthly(net, dates, trail_months=12, min_ev=30):
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


def wf_perm(actual, k_by_unit, ret_pool, wf_fn, n=N_PERM):
    r = np.asarray(ret_pool, dtype=float)
    cnt = 1
    for _ in range(n):
        frames = []
        for unit, k in k_by_unit.items():
            if k == 0:
                continue
            frames.append(pd.DataFrame({"net": RNG.choice(r, k, replace=True)}))
        null = pd.concat(frames)
        wf = wf_fn(null["net"].values, np.zeros(len(null)))
        if len(wf) and wf.mean() >= actual:
            cnt += 1
    return cnt / (n + 1)


def bootstrap(wf, n=N_BOOT):
    wf = np.asarray(wf, dtype=float)
    if len(wf) < 3:
        return {}
    means = np.array([np.mean(RNG.choice(wf, len(wf), replace=True)) for _ in range(n)])
    return dict(p50=float(np.percentile(means, 50)), p5=float(np.percentile(means, 5)),
                p95=float(np.percentile(means, 95)),
                p_leq_0=float(np.mean(means <= 0)))


def battery(label, net, dates, ret_pool, is_cut, wf_unit):
    net = np.asarray(net, dtype=float)
    dates = pd.DatetimeIndex(pd.to_datetime(np.asarray(dates)))
    df = pd.DataFrame({"d": dates, "net": net}).sort_values("d").dropna()
    is_ev = df[df["d"] <= pd.Timestamp(is_cut)]
    oos_ev = df[df["d"] > pd.Timestamp(is_cut)]
    if len(is_ev) < 20 or len(oos_ev) < 15:
        return dict(name=label, n=len(df), verdict="INSUFFICIENT", gates="")
    cost = 0.0   # net already includes cost

    is_s = stats(is_ev["net"])
    p_is = perm_signflip(is_s["mean"], is_ev["net"].to_numpy() + cost, cost)
    ho_s = stats(oos_ev["net"])
    p_ho = perm_signflip(ho_s["mean"], oos_ev["net"].to_numpy() + cost, cost)

    if wf_unit == "year":
        wf = wf_yearly(net, dates)
        trim = trimmed_by_year(wf.values, wf.index.astype(str)) if len(wf) >= 3 else None
        k_by = {u: int((pd.to_datetime(dates).year == u).sum()) for u in pd.to_datetime(dates).year.unique()}
    else:
        wf = wf_monthly(net, dates)
        trim = trimmed_by_year(wf.values, wf.index.astype(str)) if len(wf) >= 3 else None
        k_by = {u: int((pd.to_datetime(dates).to_period("M") == u).sum()) for u in pd.to_datetime(dates).to_period("M").unique()}

    wf_mean = float(wf.mean()) if len(wf) else None
    p_wf = wf_perm(wf_mean if wf_mean is not None else -1e9, k_by, ret_pool, wf_yearly if wf_unit == "year" else wf_monthly)
    boot = bootstrap(wf.values) if wf_mean is not None else {}

    gates = {
        "|t_is|>2": is_s["t"] is not None and abs(is_s["t"]) > 2,
        "p_is<0.01": p_is < 0.01,
        "ho t>2 & p<0.05": ho_s["t"] is not None and ho_s["t"] > 2 and p_ho < 0.05,
        "wf>0 & p_wf<0.05": wf_mean is not None and wf_mean > 0 and p_wf < 0.05,
        "boot P(<=0)<0.05": bool(boot) and boot["p_leq_0"] < 0.05,
        "trim>0": trim is not None and trim > 0,
    }
    return dict(name=label, n=len(df),
                is_mean=round(is_s["mean"], 4), is_t=round(is_s["t"], 2), p_is=round(p_is, 4),
                ho_mean=round(ho_s["mean"], 4), ho_t=round(ho_s["t"], 2), ho_nw=round(ho_s["nw"], 2),
                p_ho=round(p_ho, 4), wf_mean=round(wf_mean, 4), p_wf=round(p_wf, 4),
                boot_p=round(boot.get("p_leq_0", float("nan")), 4), trim=round(trim, 4),
                VERDICT="PASS" if all(gates.values()) else "FAIL",
                gates="; ".join(k for k, v in gates.items() if not v) or "all pass")


def main():
    ev = load_events()
    rows = []

    # ---------- D1 next-day variants ----------
    d1_ret = {}
    for p in PAIRS:
        d1_ret[p] = load_d1(p)["Close"].pct_change().dropna()
    ev_d1 = ev.copy()
    per = {}
    for p in PAIRS:
        c = load_d1(p)["Close"]
        r = c.pct_change(1)
        fwd = r.shift(-1)
        fwd.index = fwd.index.date
        lut = fwd[~fwd.index.duplicated(keep="last")]
        per[p] = pd.Series(ev_d1["date"].map(lut).to_numpy(), index=ev_d1.index)
        cost = RT_PIPS * PIP[p] / float(c.mean())
        ev_d1[f"net_{p}"] = CONV[p] * np.sign(ev_d1["z"]) * per[p] - cost
    ev_d1["net_basket"] = ev_d1[[f"net_{p}" for p in PAIRS]].mean(axis=1)
    for target in ["USDJPY", "GBPUSD", "EURUSD", "USDCAD", "AUDUSD", "basket"]:
        sub = ev_d1.dropna(subset=[f"net_{target}"])
        pool = d1_ret[target if target != "basket" else "USDJPY"]
        rows.append(battery(f"D1_nextday_{target}", sub[f"net_{target}"].to_numpy(),
                            sub["date"], pool.values, D1_IS_END, "year"))

    # ---------- intraday variants ----------
    h1 = {p: load_h1(p) for p in PAIRS}
    h1_ret = {p: h1[p]["Close"].pct_change().dropna() for p in PAIRS}
    for high_only in (True, False):
        evh = ev[ev["impact"] == "High"] if high_only else ev
        for h in HORIZONS:
            recs = []
            for _, r in evh.iterrows():
                ts = r["date_utc"]
                vals = {}
                ok = True
                for p in PAIRS:
                    bars = h1[p]
                    pos = bars.index.searchsorted(ts)
                    if pos >= len(bars) - h - 1 or (bars.index[pos] - ts) > pd.Timedelta(hours=2):
                        ok = False
                        break
                    vals[p] = (bars["Close"].iloc[pos + h] / bars["Open"].iloc[pos] - 1)
                if not ok:
                    continue
                recs.append(dict(date=r["date"], z=r["z"], **vals))
            if not recs:
                continue
            rec = pd.DataFrame(recs)
            cost = RT_PIPS * PIP["USDJPY"] / float(load_d1("USDJPY")["Close"].mean())
            for p in PAIRS:
                rec[f"net_{p}"] = CONV[p] * np.sign(rec["z"].to_numpy()) * rec[p].to_numpy() - cost
            rec["net_basket"] = rec[[f"net_{p}" for p in PAIRS]].mean(axis=1)
            for target in (["basket"] if high_only else ["USDJPY", "basket"]):
                sub = rec.dropna(subset=[f"net_{target}"])
                rows.append(battery(f"intraday_h{h}h_{target}{'_high' if high_only else ''}",
                                    sub[f"net_{target}"].to_numpy(), sub["date"],
                                    h1_ret[target if target != "basket" else "USDJPY"].values,
                                    H1_IS_END, "month"))

    res = pd.DataFrame(rows).sort_values("is_t", key=lambda s: s.abs(), ascending=False)
    res.to_csv(OUT / "news_family_strict.csv", index=False)
    lines = ["# News drift family — STRICT six-gate battery", ""]
    lines += ["Gates: IS |t|>2; IS 1000-perm p<1%; holdout t>2 & p<0.05; WF mean>0 & wf-perm p<0.05;",
              "bootstrap P(mean<=0)<0.05; outlier-trimmed WF>0.  D1: IS<=2021-12.  Intraday: IS<=2025-06, monthly WF.", ""]
    lines += ["| variant | n | IS% | IS t | p_is | HO% | HO t | p_ho | WF% | p_wf | boot P | trim | verdict |"]
    lines += ["|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        lines += [f"| {r['name']} | {r['n']} | {r['is_mean']:+.3f} | {r['is_t']:+.2f} | {r['p_is']:.3f} | "
                  f"{r['ho_mean']:+.3f} | {r['ho_t']:+.2f} | {r['p_ho']:.3f} | {r['wf_mean']:+.3f} | "
                  f"{r['p_wf']:.3f} | {r['boot_p']:.3f} | {r['trim']:+.3f} | **{r['VERDICT']}** |"]
    lines += ["", "Failed gates per variant:", ""]
    for _, r in res.iterrows():
        lines += [f"- {r['name']}: {r['gates']}"]
    (OUT / "news_family_strict.md").write_text("\n".join(lines), encoding="utf-8")
    print(res[["name", "n", "is_mean", "is_t", "p_is", "ho_mean", "ho_t", "p_ho", "wf_mean", "p_wf", "boot_p", "trim", "VERDICT"]].to_string(index=False))
    print("\n[saved]", OUT / "news_family_strict.md")


if __name__ == "__main__":
    main()
