"""
campaign_30.py — 30-candidate campaign runner, Tier-1 free-data ideas.

Shared four-stage framework (edge-finding-master-plan.md §3):
  S1 IS excellence: mean > 2x cost, Sharpe >= 1, win >= 60%, t >= 2.5
  S2 IS 1000-run permutation MC (re-optimizing per perm where a parameter
     exists; otherwise label/date permutation), p < 0.01
  S3 walk-forward (expanding window), Sharpe >= 0.5, t >= 2.0
  S4 walk-forward MC 1000 runs, p < 0.05  -> the headline number

Ideas run here (forced participant stated in each function):
  #17 quadruple witching — derivatives books must roll/expire mechanically
  #19 leveraged-ETF pair decay — LETFs must rebalance daily by structure
  #15 quarter-end window dressing — fund reporting mandate, not price view
  #30 real-yield vs gold — DELIBERATE CONTROL (no forced participant)

Outputs: reports/campaign_30_*.csv/.md
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(31)

N_PERM = 1000
N_WFMC = 1000
RT_COST = 0.001          # 10 bps round trip (ETF/stock)
IS_END = "2022-12-31"    # IS 2007-2022, holdout 2023-2026


def load_series(name, folder="ETF", sym=None):
    p = BASE / "market-data/raw/yahoo"
    cands = []
    if folder == "ETF":
        cands += [p / f"ETF_{name}_d.csv", p / f"{name}_d.csv"]
    elif folder == "stocks":
        cands += [p / "stocks" / f"{name}_d.csv"]
    else:
        cands += [p / f"{name}_d.csv"]
    f = next((c for c in cands if c.exists()), None)
    if f is None:
        raise FileNotFoundError(f"no data for {name} in {cands}")
    df = pd.read_csv(f, index_col=0, parse_dates=True)
    col = "close" if "close" in df.columns else "Close"
    s = df[col].sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s


def stats(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 8 or x.std() == 0:
        return dict(mean=None, t=None, sharpe=None, win=None)
    mu = x.mean()
    return dict(mean=float(mu), t=float(mu / x.std() * math.sqrt(n)),
                sharpe=float(mu / x.std() * math.sqrt(252)),
                win=float((x > 0).mean()))


def signflip_p(actual, raw, n=N_PERM):
    raw = np.asarray(raw, dtype=float)
    flips = RNG.choice([-1.0, 1.0], size=(n, len(raw)))
    means = (flips * raw).mean(axis=1)
    return float((means >= actual).sum() + 1) / (n + 1)


def wf_expanding(net, dates, min_n=60, step=21):
    """Walk-forward: expanding IS, trade the next step OOS, concat. Returns
    (dates_oos, net_oos) — the concatenated OOS equity series. Vectorized:
    IS means via cumulative sums, numpy loop over steps."""
    net = np.asarray(net, dtype=float)
    dates = np.asarray(dates)
    n = len(net)
    if n < min_n + 5:
        return np.array([]), np.array([])
    cum = np.cumsum(net)
    out_d, out_n = [], []
    i = min_n
    while i < n:
        step_end = min(i + step, n)
        if step_end - i < 5:
            break
        is_mean = cum[i - 1] / i          # mean of net[0:i]
        d = 1.0 if is_mean > 0 else -1.0
        out_n.append(d * net[i:step_end])
        out_d.append(dates[i:step_end])
        i = step_end
    if not out_n:
        return np.array([]), np.array([])
    return np.concatenate(out_d), np.concatenate(out_n)


def wf_stats(oos_n):
    oos_n = np.asarray(oos_n, dtype=float)
    if len(oos_n) < 10 or oos_n.std() == 0:
        return 0.0, 0.0
    mu = oos_n.mean()
    t = mu / oos_n.std() * math.sqrt(len(oos_n))
    sh = mu / oos_n.std() * math.sqrt(252)
    return sh, t


def stage4(dates, net, pool, n=N_WFMC):
    """Walk-forward MC: permute the return pool, re-run the full walk-forward
    (including the IS-direction re-optimization) on each permutation. Returns
    p = P(permuted WF mean >= actual WF mean)."""
    r = np.asarray(pool, dtype=float)
    actual = wf_expanding(net, dates)
    actual_mean = float(np.mean(actual[1])) if len(actual[1]) else -1e9
    cnt = 1
    for _ in range(n):
        perm = RNG.choice(r, len(net), replace=True)
        _, oos = wf_expanding(perm, dates)
        if len(oos) and oos.mean() >= actual_mean:
            cnt += 1
    return cnt / (n + 1)


def battery(label, dates, net, pool, cost=RT_COST, wf_min=60):
    s = pd.Series(net, index=pd.DatetimeIndex(pd.to_datetime(dates)))
    is_ = s[s.index <= IS_END]
    oos = s[s.index > IS_END]
    is_s, oos_s = stats(is_), stats(oos)
    mean_net = float(s.mean())
    p_is = signflip_p(is_s["mean"], is_.to_numpy()) if is_s["mean"] is not None else None
    oos_d, oos_n = wf_expanding(net, dates, min_n=wf_min)
    wf_sh, wf_t = wf_stats(oos_n)
    p_wf = stage4(dates, net, pool)
    s1 = (mean_net > 2 * cost and (is_s["sharpe"] or 0) >= 1.0 and
          (is_s["win"] or 0) >= 0.60 and (is_s["t"] or 0) >= 2.5)
    s2 = p_is is not None and p_is < 0.01
    s3 = wf_sh >= 0.5 and wf_t >= 2.0
    s4 = p_wf < 0.05
    verdict = "PASS" if (s1 and s2 and s3 and s4) else "FAIL"
    return dict(name=label, n=len(s), mean_net=round(mean_net * 100, 4),
                is_t=round(is_s["t"], 2) if is_s["t"] else None,
                p_is=round(p_is, 4) if p_is is not None else None,
                oos_t=round(oos_s["t"], 2) if oos_s["t"] else None,
                wf_sh=round(wf_sh, 2), wf_t=round(wf_t, 2),
                p_wf=round(p_wf, 4), VERDICT=verdict,
                gates="; ".join(k for k, v in [("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4)] if not v) or "all pass")


# ---------------- Idea #17: quadruple witching ----------------
def witching_series():
    """Forced participant: institutional options/futures books MUST close or
    roll expiring positions on the 3rd Friday of Mar/Jun/Sep/Dec — mechanical
    flow, not a price view. Test: does SPY |daily return| on witching Fridays
    exceed the baseline (size, not direction)? Direction-agnostic by design."""
    spy = load_series("SPY")
    ret = spy.pct_change().dropna()
    dates = ret.index
    # 3rd Friday of Mar/Jun/Sep/Dec
    is_witch = []
    for d in dates:
        if d.dayofweek == 4 and d.day >= 15 and d.day <= 21 and d.month in (3, 6, 9, 12):
            is_witch.append(True)
        else:
            is_witch.append(False)
    is_witch = np.array(is_witch)
    # signal: |return| on witching day minus rolling 21d baseline |return|
    base = ret.abs().rolling(21).mean().shift(1)
    excess = pd.Series(np.where(is_witch, ret.abs().to_numpy() - base.to_numpy(), 0.0),
                       index=dates).dropna()
    # pool: raw |returns| for permutation
    pool = ret.abs().to_numpy()
    return excess.index, excess.to_numpy(), pool


# ---------------- Idea #19: leveraged-ETF pair decay ----------------
def letf_pair_series(pair_long, pair_short, label):
    """Forced participant: 2x/3x LETFs MUST rebalance to constant leverage
    daily — structural volatility drag, direction-agnostic by construction.
    Idea #19: short BOTH legs — both decay relative to the 1x underlying, so
    a short-both basket should profit whether the underlying rises or falls.
    Also report the correlation of basket P&L with underlying direction:
    near-zero = the mechanism is real (decay, not a directional bet)."""
    a = load_series(pair_long)
    b = load_series(pair_short)
    u = load_series("SPY")
    df = pd.concat([a, b, u], axis=1).dropna()
    df.columns = ["L", "S", "U"]
    rL = df["L"].pct_change()
    rS = df["S"].pct_change()
    rU = df["U"].pct_change()
    net = (-(rL + rS) / 2 - 2 * 0.0005).dropna()   # short both legs, 5bps/leg
    corr = float(np.corrcoef(net.to_numpy(), rU.reindex(net.index).to_numpy())[0, 1])
    print(f"  [letf {label}] corr(basket, underlying dir) = {corr:+.3f}")
    pool = net.to_numpy()
    return net.index, net.to_numpy(), pool


# ---------------- Idea #15: quarter-end window dressing ----------------
def window_dressing_series():
    """Forced participant: fund managers must disclose holdings at quarter-end;
    they buy recent winners / sell recent losers before reporting to look
    better — a reporting-calendar mandate, not a price view. Test: buy
    top-decile YTD winners, short bottom-decile losers over the last 5 trading
    days of each quarter; hold 5 days into the next quarter."""
    stocks = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","JPM","BAC","WMT","XOM","CVX",
              "PG","JNJ","PFE","KO","PEP","DIS","MCD","NKE","HD","T","VZ","CAT","GE"]
    closes = {s: load_series(s, folder="stocks") for s in stocks}
    df = pd.concat(closes, axis=1).dropna()
    df.columns = stocks
    # daily returns; drop any stock-day with >40% single-day move (spin-off
    # discontinuities like GE 2024 would otherwise contaminate the ranking)
    daily = df.pct_change()
    daily = daily.replace([np.inf, -np.inf], np.nan)
    daily[daily.abs() > 0.40] = np.nan
    qends = df.index.to_series().groupby([df.index.year, df.index.quarter]).max()
    rets, dates = [], []
    for i in range(1, len(qends)):
        q = qends.iloc[i]          # end of quarter i
        p = qends.iloc[i - 1]      # end of previous quarter
        cut = df.index[df.index <= q - pd.Timedelta(days=5)]
        if len(cut) == 0:
            continue
        ref = cut[-1]
        # YTD return from cumulative daily returns (split/dividend-safe)
        cum = (1 + daily.loc[p:ref]).prod() - 1
        cum = cum.dropna()
        if len(cum) < 8:
            continue
        win = cum.nlargest(4).index
        lose = cum.nsmallest(4).index
        # buy winners / short losers over the last 5 days of the quarter
        w5 = (1 + daily.loc[ref:q, win]).prod() - 1
        l5 = (1 + daily.loc[ref:q, lose]).prod() - 1
        if w5.isna().any() or l5.isna().any():
            continue
        r = w5.mean() - l5.mean() - 2 * RT_COST
        rets.append(r)
        dates.append(q)
    pool = np.asarray(rets, dtype=float)
    return np.array(dates), pool, pool


# ---------------- Idea #30: real-yield vs gold (control) ----------------
def realyield_gold_series():
    """DELIBERATE CONTROL — no forced participant. Gold's opportunity cost
    should track real yields. FRED (T10YIE/DFII10) is blocked on this network;
    proxy = nominal 10Y (^TNX) + TIP ETF move as the closest available.
    Signal: daily change in 10Y nominal yield -> next-day gold return
    (higher yields -> gold down). If this fundamentals-only link survives the
    battery as well as the forced-participant ideas, the core thesis is
    weakened — report that honestly."""
    gold = load_series("GOLD", folder="", sym="GOLD") if False else _load_gold()
    tnx = load_series("TNX")
    df = pd.concat([gold, tnx], axis=1).dropna()
    df.columns = ["gold", "tnx"]
    dy = df["tnx"].diff().shift(1)          # yesterday's yield change
    rg = df["gold"].pct_change()
    m = pd.concat([dy, rg], axis=1).dropna()
    # long gold when yields fell, short when they rose (beta signal)
    signal = -np.sign(m["tnx"].to_numpy())
    net = signal * m["gold"].to_numpy() - RT_COST
    pool = m["gold"].to_numpy()
    return m.index, net, pool


def _load_gold():
    df = pd.read_csv(BASE / "market-data/raw/yahoo/GOLD_d.csv", index_col=0, parse_dates=True)
    s = df["close"].sort_index() if "close" in df else df["Close"].sort_index()
    return s[~s.index.duplicated(keep="last")]


def main():
    rows = []
    # #17 witching
    d, n, pool = witching_series()
    rows.append(battery("witching_excess_abs", d, n, pool, cost=0.0))
    # #19 LETF pairs (long-short, direction-agnostic net)
    for pair, label in [(("TQQQ", "SQQQ"), "TQQQ_SQQQ"),
                        (("SPXL", "SPXS"), "SPXL_SPXS"),
                        (("UPRO", "SPXU"), "UPRO_SPXU")]:
        d, n, pool = letf_pair_series(*pair, label)
        rows.append(battery(f"letf_{label}_LS", d, n, pool, cost=0.0005))
    # #15 window dressing
    d, n, pool = window_dressing_series()
    rows.append(battery("window_dressing_w4_l4", d, n, pool, cost=RT_COST, wf_min=16))
    # #30 control
    d, n, pool = realyield_gold_series()
    rows.append(battery("realyield_gold_control", d, n, pool, cost=RT_COST))

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "campaign_30_tier1.csv", index=False)
    lines = ["# Campaign-30 Tier-1 results (four-stage framework)", "",
             "Forced participant stated per idea. S1 IS excellence; S2 IS 1000-perm p<0.01;",
             "S3 walk-forward Sharpe>=0.5 & t>=2; S4 walk-forward MC p<0.05 (headline).",
             f"IS <= {IS_END}; holdout after. Cost per round trip as noted.", "",
             "| idea | n | mean%/tr | IS t | p_is | OOS t | WF sh | WF t | p_wf | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    def fmt(v, pfx=""):
        return "-" if v is None else f"{pfx}{v:.2f}"
    for _, r in res.iterrows():
        lines.append(f"| {r['name']} | {r['n']} | {r['mean_net']:+.3f} | "
                     f"{fmt(r['is_t'], '+')} | {fmt(r['p_is'])} | "
                     f"{fmt(r['oos_t'], '+')} | {r['wf_sh']:+.2f} | {r['wf_t']:+.2f} | "
                     f"{r['p_wf']:.3f} | **{r['VERDICT']}** |")
    lines += ["", "Failed stages:", ""]
    for _, r in res.iterrows():
        lines.append(f"- {r['name']}: {r['gates']}")
    (OUT / "campaign_30_tier1.md").write_text("\n".join(lines), encoding="utf-8")
    print(res.to_string(index=False))
    print("\n[saved]", OUT / "campaign_30_tier1.md")


if __name__ == "__main__":
    main()
