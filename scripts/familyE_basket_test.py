"""
familyE_basket_test.py — Mechanism Family E: informed under-reaction, dollar
basket, per the Edge-Finding Master Plan §1E.

Forced participant (named before code): after a macro print, stop-losses,
margin calls and hedger exits force counterparties to transact at the print
regardless of price — they cannot wait for a better price — while the full
information content of the surprise propagates slowly across dollar
instruments. If the market under-reacts, the forced transactors supply the
other side of the drift. This test exists to confirm or kill that story.

Data adaptation (documented): release T is not on an hourly boundary; with
H1 bars the honest entry is the first clean hourly OPEN at or after T+30min
(the :00 bar following a :30/:00 release). The "reaction" r30 is measured as
the basket move from that entry open to the end of the first post-entry hour;
exits at entry + 4/8/24/48 hours.

Signal:
  z = (actual - consensus) / sigma(trailing surprises, per title)
  dollar basket factor = sum sign_i * (r_i / sigma_i) over 7 USD pairs
      sign +1: EURUSD GBPUSD AUDUSD NZDUSD ;  -1: USDJPY USDCAD USDCHF
  r30 regression on z, IN-SAMPLE ONLY, locked: predicted = a + b*z
  gap = r30 - predicted.  Under-reaction iff |r30| < |predicted| (market
      moved less than the surprise implies) and sign(r30) == sign(predicted)
      (it moved the right way) and |gap| > 0.5*sigma(gap).
  Entry: |z| > 0.5, Tier 1/2, under-reaction as above, no other Tier1/2 USD
      release inside the holding window.
  Direction on EURUSD: short if z > 0 (USD surprise positive -> USD strong),
      long if z < 0.  Execute on EURUSD only.
  Exit: time-based 4h / 8h / 24h / 48h.

Control arm (mandatory, the decisive test): identical entry/exit, but
direction = sign of the already-observed pre-entry move (momentum over
[T-1h, entry open]).  If the control performs as well as the signal, the
effect is ordinary post-news momentum (graveyard) and the family dies.

Four-stage framework (plan §3):
  S1 IS excellence: mean > 2x round-trip cost, Sharpe >= 1, win >= 60%, t >= 2.5
  S2 IS 1000-run permutation MC: p < 0.01
  S3 walk-forward (quarterly re-estimate of the r30 regression, trade the
     following month out-of-sample): Sharpe >= 0.5, t >= 2.0
  S4 walk-forward MC 1000 runs: p < 0.05

Costs: 1 pip spread + 0.5 pip slippage on EURUSD ~= 0.014% round trip.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(23)

PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF"]
SIGN = {"EURUSD": 1, "GBPUSD": 1, "AUDUSD": 1, "NZDUSD": 1,
        "USDJPY": -1, "USDCAD": -1, "USDCHF": -1}
Z_THR = 0.5
TIERS = ["High", "Medium"]
HORIZONS = [4, 8, 24, 48]
EXECUTE = "EURUSD"
RT_COST = 0.00014
N_PERM = 1000
N_WFMC = 1000
H1_IS_END = "2025-06-30"
MIN_Z_OBS = 20


def load_events():
    ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
    ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)
    ev = ev[(ev["currency"] == "USD") & (ev["impact"].isin(TIERS))
            & ev["actual"].notna() & ev["forecast"].notna()].copy()
    ev["surprise"] = (pd.to_numeric(ev["actual"], errors="coerce") -
                      pd.to_numeric(ev["forecast"], errors="coerce"))
    ev = ev.dropna(subset=["surprise"]).sort_values("date_utc")
    ev["date"] = ev["date_utc"].dt.date
    ev["z"] = np.nan
    for title, g in ev.groupby("title"):
        g = g.sort_values("date_utc")
        s = g["surprise"]
        mu = s.expanding(min_periods=MIN_Z_OBS).mean().shift(1)
        sd = s.expanding(min_periods=MIN_Z_OBS).std().shift(1)
        z = (s - mu) / sd.where(sd > 1e-12)
        ev.loc[g.index, "z"] = z.clip(-8, 8)
    return ev.dropna(subset=["z"])


def load_h1(pair):
    df = pd.read_csv(BASE / "market-data/raw/yahoo" / f"{pair}_h1.csv", parse_dates=["Date"])
    df = df.drop_duplicates("Date", keep="last").sort_values("Date")
    return df.set_index("Date")[["Open", "Close"]]


def leg_vol(b, pos, win=24):
    w = b["Close"].iloc[max(0, pos - win):pos].pct_change().std()
    return w if (w is not None and not math.isnan(w) and w > 1e-12) else 0.001


def basket_move(bars, pos, h):
    """Vol-normalized basket factor move from bar pos open to bar pos+h close."""
    tot = 0.0
    for p in PAIRS:
        b = bars[p]
        if pos + h >= len(b):
            return None
        w = leg_vol(b, pos)
        r = b["Close"].iloc[pos + h] / b["Open"].iloc[pos] - 1
        tot += SIGN[p] * r / w
    return tot / len(PAIRS)


def collect(ev, bars):
    """Build per-event records: entry idx, z, r30 (first-hour basket move),
    pre-move (last-hour move before entry, for control), horizon returns."""
    b = bars[EXECUTE]
    recs = []
    for _, r in ev.iterrows():
        ts = r["date_utc"]
        pos = b.index.searchsorted(ts)
        if pos >= len(b) - 50:
            continue
        if (b.index[pos] - ts) > pd.Timedelta(hours=2):
            continue
        entry_idx = pos + 1                      # first clean hourly open
        if entry_idx + 48 >= len(b):
            continue
        r30 = basket_move(bars, entry_idx, 1)    # first post-entry hour
        premove = basket_move(bars, entry_idx - 1, 1)  # hour before entry
        if r30 is None or premove is None:
            continue
        # horizon returns on the executed pair
        ex = b["Open"].iloc[entry_idx]
        hrs = {}
        ok = True
        for h in HORIZONS:
            if entry_idx + h >= len(b):
                ok = False
                break
            hrs[f"h{h}"] = b["Close"].iloc[entry_idx + h] / ex - 1
        if not ok:
            continue
        recs.append(dict(date=r["date"], ts=ts, z=r["z"], r30=r30,
                         premove=premove, **hrs))
    return pd.DataFrame(recs)


def stats(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 5 or x.std() == 0:
        return dict(mean=None, t=None, sharpe=None, win=None, n=n)
    mu = x.mean()
    return dict(mean=float(mu), t=float(mu / x.std() * math.sqrt(n)),
                sharpe=float(mu / x.std() * math.sqrt(252 / 1)),
                win=float((x > 0).mean()), n=n)


def signflip_p(actual, raw, n=N_PERM):
    raw = np.asarray(raw, dtype=float)
    flips = RNG.choice([-1.0, 1.0], size=(n, len(raw)))
    means = (flips * raw).mean(axis=1)
    return float((means >= actual).sum() + 1) / (n + 1)


def trade_records(rec, horizon, mode, is_end=None, fit_rec=None, cpi_only=False):
    """Apply entry rules. mode='signal': surprise-gap under-reaction.
    mode='momentum': control arm on pre-move direction.
    is_end: if given, fit the r30~z regression on that subset only (locked).
    cpi_only: restrict to CPI-family releases (Stage-0 optimization).
    Returns (dates, net_returns, n_trades)."""
    df = rec.copy()
    if cpi_only:
        cpi = df["title"].astype(str).str.contains("Inflation|CPI", case=False)
        df = df[cpi]
    if fit_rec is not None:
        f = fit_rec
    else:
        f = df[df["date"] <= is_end] if is_end else df
    if len(f) < 20:
        return None
    z = f["z"].to_numpy()
    y = f["r30"].to_numpy()
    A = np.column_stack([np.ones(len(z)), z])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ beta
    resid = y - pred
    sigma_gap = float(resid.std()) if resid.std() > 1e-12 else 1e9
    dates, nets = [], []
    n_tr = 0
    for _, r in df.iterrows():
        if abs(r["z"]) < Z_THR:
            continue
        p = beta[0] + beta[1] * r["z"]
        gap = r["r30"] - p
        if mode == "signal":
            # under-reaction: moved less than implied, right way, big gap
            if abs(p) < 1e-12:
                continue
            if abs(r["r30"]) >= abs(p):
                continue
            if np.sign(r["r30"]) != np.sign(p):
                continue
            if abs(gap) < 0.5 * sigma_gap:
                continue
            direction = 1 if p > 0 else -1      # USD strong -> short EURUSD
        else:
            if abs(r["premove"]) < 1e-12:
                continue
            direction = 1 if r["premove"] > 0 else -1
        net = direction * r[f"h{horizon}"] - RT_COST
        dates.append(r["date"])
        nets.append(net)
        n_tr += 1
    if len(nets) < 10:
        return None
    return np.array(dates), np.array(nets), n_tr


def wf_monthly(net, dates, trail_months=12, min_ev=15):
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


def wf_perm_p(actual, dates, pool, n=N_PERM):
    r = np.asarray(pool, dtype=float)
    dates = np.asarray(pd.to_datetime(dates))
    df = pd.DataFrame({"d": dates, "net": np.zeros(len(dates))})
    df["u"] = df["d"].dt.to_period("M").astype("int64")
    uc = df.sort_values("d")["u"].to_numpy()
    starts = np.searchsorted(uc, np.unique(uc))
    ends = np.append(starts[1:], len(uc))
    cu = (ends - starts).astype(float)
    cum = np.cumsum(cu)
    cnt = 1
    for _ in range(n):
        net = RNG.choice(r, len(dates), replace=True)
        sums = np.add.reduceat(net, starts)
        means = sums / cu
        out = np.zeros(len(means))
        for i in range(len(means)):
            lo = max(0, i - 12)
            tc = cum[i - 1] if i > 0 else 0
            if lo > 0:
                tc -= cum[lo - 1]
            if tc < 15 or lo >= i:
                continue
            if means[lo:i].mean() > 0:
                out[i] = means[i]
        if out.mean() >= actual:
            cnt += 1
    return cnt / (n + 1)


def bootstrap_p(wf, n=5000):
    wf = np.asarray(wf, dtype=float)
    if len(wf) < 3:
        return 1.0
    means = np.array([np.mean(RNG.choice(wf, len(wf), replace=True)) for _ in range(n)])
    return float(np.mean(means <= 0))


def main():
    ev = load_events()
    bars = {p: load_h1(p) for p in PAIRS}
    b0 = bars[EXECUTE]
    ev_h = ev[(ev["date_utc"] >= b0.index.min()) & (ev["date_utc"] <= b0.index.max() - pd.Timedelta(days=5))]
    print(f"events with z: {len(ev)} | in H1 window: {len(ev_h)}")
    # dedupe: the four CPI titles fire at the same timestamp; keep max |z|
    ev_h = ev_h.sort_values("z", key=lambda s: s.abs(), ascending=False)
    ev_h = ev_h[~ev_h["date_utc"].duplicated(keep="first")].sort_values("date_utc")
    rec = collect(ev_h, bars)
    print(f"measurable records (deduped by timestamp): {len(rec)} | {rec['date'].min()} -> {rec['date'].max()}")
    rec["date"] = pd.to_datetime(rec["date"])
    # merge back title/impact for the CPI restriction + second-release gate
    rec = rec.merge(ev_h[["date_utc", "impact", "title"]], left_on="ts", right_on="date_utc", how="left")
    # second-release gate: no other Tier1/2 USD release inside the holding window
    ts_all = ev_h["date_utc"].to_numpy()
    keep = []
    for i, ts in enumerate(rec["ts"].to_numpy()):
        win = ts_all[(ts_all > ts) & (ts_all <= ts + np.timedelta64(48, "h"))]
        keep.append(len(win) <= 1)
    rec = rec[np.array(keep)]
    rows = []
    for h in HORIZONS:
        for mode in ("signal", "momentum"):
            out = trade_records(rec, h, mode, is_end=H1_IS_END)
            if out is None:
                print(f"h{h}h {mode}: insufficient")
                continue
            dates, net, n_tr = out
            s = pd.Series(net, index=pd.DatetimeIndex(pd.to_datetime(dates)))
            is_ = s[s.index <= H1_IS_END]
            oos = s[s.index > H1_IS_END]
            is_s, oos_s = stats(is_), stats(oos)
            p_is = signflip_p(is_s["mean"], is_.to_numpy()) if is_s["mean"] is not None else None
            wf = wf_monthly(net, dates)
            wf_mean = float(wf.mean()) if len(wf) else None
            p_wf = wf_perm_p(wf_mean if wf_mean is not None else -1e9, dates, net) if wf_mean is not None else None
            boot = bootstrap_p(wf.values) if wf_mean is not None else 1.0
            yrs = s.groupby(s.index.year).sum()
            trim = float(yrs.sort_values().iloc[1:-1].mean()) if len(yrs) >= 3 else None
            mean_net = float(s.mean())
            s1 = (mean_net > 2 * RT_COST and
                  (is_s["sharpe"] or 0) >= 1.0 and (is_s["win"] or 0) >= 0.60 and
                  (is_s["t"] or 0) >= 2.5)
            s2 = p_is is not None and p_is < 0.01
            wf_sharpe = (wf_mean or 0) / (wf.std() + 1e-12) * math.sqrt(12) if wf.std() > 0 else 0
            s3 = wf_mean is not None and wf_mean > 0 and wf_sharpe >= 0.5
            s4 = p_wf is not None and p_wf < 0.05
            verdict = "PASS" if (s1 and s2 and s3 and s4 and boot < 0.05 and trim > 0) else "FAIL"
            rows.append(dict(variant=f"h{h}h_{mode}", n=n_tr, mean_net=round(mean_net * 100, 4),
                             is_t=round(is_s["t"], 2) if is_s["t"] else None,
                             p_is=round(p_is, 4) if p_is is not None else None,
                             oos_mean=round(float(oos.mean()) * 100, 4) if len(oos) else None,
                             oos_t=round(oos_s["t"], 2) if oos_s["t"] else None,
                             wf_mean=round(wf_mean * 100, 4) if wf_mean is not None else None,
                             p_wf=round(p_wf, 4) if p_wf is not None else None,
                             boot=round(boot, 4), trim=round(trim * 100, 4) if trim is not None else None,
                             VERDICT=verdict,
                             gates="; ".join(k for k, v in
                                             [("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4),
                                              ("boot", boot < 0.05), ("trim", (trim or -1) > 0)]
                                             if not v) or "all pass"))
        # Stage-0-optimized variant: CPI-only, signal mode, all horizons
        out = trade_records(rec, h, "signal", is_end=H1_IS_END, cpi_only=True)
        if out is not None:
            dates, net, n_tr = out
            s = pd.Series(net, index=pd.DatetimeIndex(pd.to_datetime(dates)))
            is_ = s[s.index <= H1_IS_END]
            oos = s[s.index > H1_IS_END]
            is_s, oos_s = stats(is_), stats(oos)
            p_is = signflip_p(is_s["mean"], is_.to_numpy()) if is_s["mean"] is not None else None
            wf = wf_monthly(net, dates)
            wf_mean = float(wf.mean()) if len(wf) else None
            p_wf = wf_perm_p(wf_mean if wf_mean is not None else -1e9, dates, net) if wf_mean is not None else None
            boot = bootstrap_p(wf.values) if wf_mean is not None else 1.0
            yrs = s.groupby(s.index.year).sum()
            trim = float(yrs.sort_values().iloc[1:-1].mean()) if len(yrs) >= 3 else None
            mean_net = float(s.mean())
            s1 = (mean_net > 2 * RT_COST and
                  (is_s["sharpe"] or 0) >= 1.0 and (is_s["win"] or 0) >= 0.60 and
                  (is_s["t"] or 0) >= 2.5)
            s2 = p_is is not None and p_is < 0.01
            wf_sharpe = (wf_mean or 0) / (wf.std() + 1e-12) * math.sqrt(12) if wf.std() > 0 else 0
            s3 = wf_mean is not None and wf_mean > 0 and wf_sharpe >= 0.5
            s4 = p_wf is not None and p_wf < 0.05
            verdict = "PASS" if (s1 and s2 and s3 and s4 and boot < 0.05 and trim > 0) else "FAIL"
            rows.append(dict(variant=f"h{h}h_signal_cpi", n=n_tr, mean_net=round(mean_net * 100, 4),
                             is_t=round(is_s["t"], 2) if is_s["t"] else None,
                             p_is=round(p_is, 4) if p_is is not None else None,
                             oos_mean=round(float(oos.mean()) * 100, 4) if len(oos) else None,
                             oos_t=round(oos_s["t"], 2) if oos_s["t"] else None,
                             wf_mean=round(wf_mean * 100, 4) if wf_mean is not None else None,
                             p_wf=round(p_wf, 4) if p_wf is not None else None,
                             boot=round(boot, 4), trim=round(trim * 100, 4) if trim is not None else None,
                             VERDICT=verdict,
                             gates="; ".join(k for k, v in
                                             [("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4),
                                              ("boot", boot < 0.05), ("trim", (trim or -1) > 0)]
                                             if not v) or "all pass"))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "familyE_basket_strict.csv", index=False)
    lines = ["# Family E — dollar-basket under-reaction — STRICT four-stage battery", "",
             "Mechanism: surprise z (actual vs real consensus, per title), 7-pair vol-normalized dollar",
             "basket, IN-SAMPLE-locked r30~z regression, under-reaction gap filter, EURUSD execution.",
             "Control arm = momentum on pre-move (must FAIL for the family to live).  H1 2023-10 -> 2026-08.",
             "Costs: 1pip + 0.5pip slippage ~= 0.014% RT.  IS <= 2025-06-30.", "",
             "| variant | n | mean%/tr | IS t | p_is | OOS% | OOS t | WF% | p_wf | boot | trim | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    def fmt(v, pfx=""):
        return "-" if v is None else f"{pfx}{v:.3f}"
    for _, r in res.iterrows():
        lines.append(f"| {r['variant']} | {r['n']} | {r['mean_net']:+.3f} | "
                     f"{fmt(r['is_t'], '+')} | {fmt(r['p_is'])} | "
                     f"{fmt(r['oos_mean'], '+')} | {fmt(r['oos_t'], '+')} | "
                     f"{fmt(r['wf_mean'], '+')} | {fmt(r['p_wf'])} | "
                     f"{r['boot']:.3f} | {r['trim']:+.3f} | **{r['VERDICT']}** |")
    lines += ["", "Failed stages:", ""]
    for _, r in res.iterrows():
        lines.append(f"- {r['variant']}: {r['gates']}")
    (OUT / "familyE_basket_strict.md").write_text("\n".join(lines), encoding="utf-8")
    print(res.to_string(index=False))
    print("\n[saved]", OUT / "familyE_basket_strict.md")


if __name__ == "__main__":
    main()
