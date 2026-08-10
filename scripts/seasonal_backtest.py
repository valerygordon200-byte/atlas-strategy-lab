#!/usr/bin/env python3
"""seasonal_backtest.py — commodity seasonal strategy, full protocol.

Brief-compliant execution:
  Step 1-2: data gates done (seasonal_fetch.py); split 2000-2014 / 2015+.
  Step 3: select (commodity, month) with |t|>2 on the SELECTION window only;
          directions locked to a JSON file. Never refit.
  Step 4: blind holdout, full costs.
  Step 5: $100 compound sim, daily cap, $100 min notional, ENB scaling.
  Step 6: robustness battery (7 tests).
  Step 7: verdict vs pre-registered kill criteria.

Costs (fraction of notional, round trip):
  spread per instrument (retail CFD; anchors: corn 0.27%, gasoline 0.46% —
  measured in the prior study; others estimated by category).
  slippage = 0.5 x spread each way (worst plausible fill).
  roll     = 1 x spread if a month-long position crosses a contract roll
             (continuous front-month series rolls roughly monthly).
  financing: annual/12 per month held; run the ladder 8 / 15 / 25%.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("E:/forex-data")
RAW = DATA / "market-data/raw/yahoo"
OUT = DATA / "reports"

SEL_START, SEL_END = "2000-01-01", "2014-12-31"
HO_START = "2015-01-01"

COMMODITIES = ["CL", "BZ", "NG", "HO", "RB", "ZC", "ZW", "ZS", "ZM", "ZL",
               "ZO", "ZR", "KC", "SB", "CC", "CT", "OJ", "LE", "GF", "HE",
               "GC", "SI", "HG", "PL", "PA", "LB"]
# retail CFD round-trip spread, % of notional (estimated; two measured anchors)
SPREAD_PCT = {
    "CL": 0.46, "BZ": 0.50, "NG": 0.60, "HO": 0.60, "RB": 0.46,
    "ZC": 0.27, "ZW": 0.27, "ZS": 0.35, "ZM": 0.35, "ZL": 0.50, "ZO": 0.60,
    "ZR": 0.80, "KC": 0.60, "SB": 0.40, "CC": 0.60, "CT": 0.50, "OJ": 0.80,
    "LE": 0.50, "GF": 0.70, "HE": 0.50,
    "GC": 0.35, "SI": 0.50, "HG": 0.40, "PL": 0.80, "PA": 0.80, "LB": 0.80,
}
# T212 availability (from the brief): NOT available -> flag trades untradeable
T212_UNAVAILABLE = {"GF": "Feeder Cattle not offered", "ZM": "Soybean Meal not offered"}
T212_CONFIRMED = {"RB", "SB", "ZW", "CT", "ZC", "LE", "ZL", "HE", "ZS", "ZR"}
MIN_NOTIONAL = 100.0
DAILY_CAP = 5.0
CAP_PCT = 0.085


def load_all():
    frames = {}
    for c in COMMODITIES:
        f = RAW / f"COMM_{c}_d.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, parse_dates=["date"]).set_index("date").sort_index()
        df = df[~df.index.duplicated(keep="last")]
        frames[c] = df[["open", "high", "low", "close"]].astype(float)
    return frames


def monthly_log_returns(df):
    """log(close[last trading day of m] / close[last trading day of m-1])."""
    last = df["close"].resample("ME").last().dropna()
    return np.log(last / last.shift(1)).dropna()


def sel_stats(ret, months_of_year):
    """Selection-window stats for a (commodity, month) seasonal."""
    sub = ret[ret.index.month == months_of_year]
    if len(sub) < 8:
        return None
    mu = sub.mean()
    sd = sub.std(ddof=1)
    t = mu / (sd / math.sqrt(len(sub))) if sd > 0 else 0.0
    return {"n": len(sub), "mean": mu, "t": t}


def net_return(gross_dir_ret, spread_pct, fin_pct):
    """gross_dir_ret = signalled-direction log return (fraction).
    Costs in fraction of notional: spread + 2x0.5xspread slippage + roll + fin."""
    cost = spread_pct / 100.0 + 2 * (0.5 * spread_pct / 100.0) + spread_pct / 100.0 + fin_pct / 100.0
    return gross_dir_ret - cost


def main():
    frames = load_all()
    print(f"loaded {len(frames)}/26 instruments")

    # ============ STEP 3: SELECTION (2000-2014) ============
    sel_rets = {c: monthly_log_returns(f.loc[SEL_START:SEL_END]) for c, f in frames.items()}
    locked = {}
    n_tests = 0
    for c in COMMODITIES:
        if c not in frames:
            continue
        for m in range(1, 13):
            st = sel_stats(sel_rets[c], m)
            if st is None:
                continue
            n_tests += 1
            if abs(st["t"]) > 2.0:
                locked[f"{c}_{m}"] = {
                    "commodity": c, "month": m,
                    "direction": 1 if st["mean"] > 0 else -1,
                    "is_mean": float(st["mean"]), "is_t": float(st["t"]),
                    "is_n": st["n"],
                }
    # expected hits by chance under null: 2-sided |t|>2 ~ p=0.0455
    exp_chance = n_tests * 0.0455
    (OUT / "seasonal_locked.json").write_text(
        json.dumps(locked, indent=2), encoding="utf-8")
    print(f"selection: {n_tests} tests, {len(locked)} selected |t|>2, "
          f"expected by chance ~{exp_chance:.1f}")
    for k, v in sorted(locked.items()):
        print(f"  {k:6s} dir={'L' if v['direction']>0 else 'S'} "
              f"IS mean={v['is_mean']*100:+.2f}% t={v['is_t']:+.2f} n={v['is_n']}")

    # ============ STEP 4: BLIND HOLDOUT (2015+) ============
    ho_rets = {c: monthly_log_returns(f.loc[HO_START:]) for c, f in frames.items()}
    fin_ladder = (8, 15, 25)  # ints so column keys match selectors
    rows = []
    for k, spec in sorted(locked.items()):
        c, m = spec["commodity"], spec["month"]
        r = ho_rets[c]
        sub = r[r.index.month == m]
        gross = sub * spec["direction"]  # profit to signalled direction
        n = len(sub)
        res = {"key": k, "commodity": c, "month": m,
               "dir": "L" if spec["direction"] > 0 else "S",
               "is_mean%": round(spec["is_mean"] * 100, 2),
               "is_t": round(spec["is_t"], 2),
               "oos_n": n, "oos_win%": round((gross > 0).mean() * 100, 1)
               if n else np.nan,
               "t212": "NO" if c in T212_UNAVAILABLE else "yes"}
        for fin in fin_ladder:
            fin_pct = fin / 12.0
            net = gross.apply(lambda g: net_return(g, SPREAD_PCT[c], fin_pct))
            mu = net.mean()
            sd = net.std(ddof=1) if len(net) > 1 else 1e-9
            t = mu / (sd / math.sqrt(len(net))) if sd > 0 else 0.0
            res[f"oos_net_mean{fin}%"] = round(mu * 100, 3)
            res[f"oos_t{fin}"] = round(t, 2)
        rows.append(res)

    ho_df = pd.DataFrame(rows)
    ho_df.to_csv(OUT / "seasonal_holdout.csv", index=False)
    pd.set_option("display.width", 220)
    print("\n=== BLIND HOLDOUT (net of costs; mean % per trade, signalled direction) ===")
    show = ho_df[["key", "dir", "is_mean%", "is_t", "oos_n", "oos_win%",
                  "oos_net_mean8%", "oos_t8", "oos_net_mean15%", "oos_t15",
                  "oos_net_mean25%", "oos_t25", "t212"]]
    print(show.to_string(index=False))

    # binomial: how many of the selected seasonals are net-positive OOS at 8%
    pos8 = (ho_df["oos_net_mean8%"] > 0).sum()
    tot = len(ho_df)
    from scipy import stats as _s
    binom_p = _s.binomtest(pos8, tot, 0.5).pvalue if tot else float("nan")
    print(f"\nnet-positive OOS at 8% fin: {pos8}/{tot} (binomial p vs 50%: {binom_p:.3f})")

    # ============ STEP 5: PORTFOLIO COMPOUND SIM ============
    # one pass at 8% financing (full ladder summary in robustness)
    fin_pct = 8.0 / 12.0
    eq = 100.0
    eq_curve = [100.0]
    years = {}
    forced_min = 0
    cap_bound = 0
    n_trades = 0
    monthly_port = []
    # monthly net returns per (key) across the full holdout
    netmap = {}
    for k, spec in locked.items():
        c, m = spec["commodity"], spec["month"]
        r = ho_rets[c]
        sub = (r * spec["direction"]).copy()
        netmap[k] = sub.apply(lambda g: net_return(g, SPREAD_PCT[c], fin_pct))
    # correlation of annual leg returns for ENB — computed on the SELECTION
    # window only (reviewer: holdout-derived scale is lookahead)
    leg_annual = {}
    for k, spec in locked.items():
        c, m = spec["commodity"], spec["month"]
        r = sel_rets[c]
        s = (r * spec["direction"])
        leg_annual[k] = s.groupby(s.index.year).mean()
    la = pd.DataFrame(leg_annual).dropna()
    if len(la) >= 2 and la.shape[1] >= 2:
        corr = la.corr().values
        eig = np.linalg.eigvalsh(corr)
        enb = eig.sum() ** 2 / (eig ** 2).sum() if (eig ** 2).sum() > 0 else 1.0
        scale = 1.0
        if enb < 0.6 * la.shape[1]:
            scale = enb / la.shape[1]
    else:
        enb, scale = 1.0, 1.0
    print(f"\nENB on annual leg returns: {enb:.2f} of {len(la.columns) if len(la) else 0} "
          f"legs; exposure scale {scale:.2f}")

    monthly_idx = sorted(set().union(*[set(netmap[k].index) for k in netmap]))
    for ym in monthly_idx:
        cap = min(DAILY_CAP, CAP_PCT * eq)
        active = [k for k in netmap if ym in netmap[k].index]
        if not active:
            eq_curve.append(eq)
            continue
        n_trades += len(active)
        port_ret = 0.0
        for j, k in enumerate(active):
            c = locked[k]["commodity"]
            df = frames[c]
            # trailing 60d daily vol at month start (no lookahead)
            prior = df.loc[:ym - pd.Timedelta(days=1), "close"].tail(60)
            if len(prior) < 20:
                continue
            dv = prior.pct_change().std()
            if not np.isfinite(dv) or dv <= 0:
                continue
            notional = (cap / len(active)) / (1.5 * dv)
            if notional < MIN_NOTIONAL:
                notional = MIN_NOTIONAL
                forced_min += 1
            if cap < DAILY_CAP - 1e-9:
                cap_bound += 1
            port_ret += notional / eq * netmap[k][ym] * scale
        eq *= (1.0 + port_ret)
        eq_curve.append(eq)
        monthly_port.append((ym, port_ret))
        years[ym.year] = years.get(ym.year, 1.0) * (1.0 + port_ret)
        if eq <= 15.0:
            print(f"  [full-35 sim] ACCOUNT BLOWN at {ym:%Y-%m} "
                  f"(equity ${eq:.2f} < margin floor) — sim halted", flush=True)
            break

    eqs = pd.Series(eq_curve)
    mdd = ((eqs - eqs.cummax()) / eqs.cummax()).min() * 100
    yr_ret = {y: (v - 1) * 100 for y, v in sorted(years.items())}
    mrets = pd.Series([r for _, r in monthly_port])
    sharpe = mrets.mean() / mrets.std(ddof=1) * math.sqrt(12) if len(mrets) > 1 and mrets.std(ddof=1) > 0 else 0.0
    print("\n=== PORTFOLIO ($100 COMPOUNDED, 8% financing) ===")
    print(f"terminal equity: ${eq:.2f}  (CAGR {((eq/100)**(12/len(monthly_port))-1)*100 if monthly_port else 0:.1f}%/yr)")
    print(f"max drawdown: {mdd:.1f}%  | worst year: {min(yr_ret.values()):.2f}% "
          f"({min(yr_ret, key=yr_ret.get)}) | best year: {max(yr_ret.values()):.2f}%")
    print(f"monthly Sharpe (net): {sharpe:.2f} | trades/mo: {n_trades/max(len(monthly_idx),1):.1f}")
    print(f"forced $100 minimum oversizing: {forced_min} months | daily-cap pct-half bound: {cap_bound} months")
    print("yearly returns:", {y: round(v, 1) for y, v in yr_ret.items()})

    # ============ STEP 6: ROBUSTNESS BATTERY ============
    print("\n=== ROBUSTNESS ===")
    # 1. outlier trim (drop best and worst year per seasonal, holdout, at 8%)
    worse = 0
    for k, spec in locked.items():
        c, m = spec["commodity"], spec["month"]
        r = ho_rets[c]
        sub = (r * spec["direction"]).copy()
        net = sub.apply(lambda g: net_return(g, SPREAD_PCT[c], fin_pct))
        if len(net) >= 3:
            trimmed = net.drop(net.idxmax()).drop(net.idxmin())
            if trimmed.mean() < net.mean():
                worse += 1
    print(f"1. outlier trim: {worse}/{len(locked)} seasonals WEAKEN after dropping best+worst year")
    # 2. BH at FDR 10% on selection p-values
    pvals = []
    for c in COMMODITIES:
        if c not in frames:
            continue
        for m in range(1, 13):
            st = sel_stats(sel_rets[c], m)
            if st:
                pvals.append(2 * (1 - _s.norm.cdf(abs(st["t"]))))
    pvals = np.sort(pvals)
    bh_k = 0
    for i, p in enumerate(pvals):
        if p <= (i + 1) / len(pvals) * 0.10:
            bh_k = i + 1
        else:
            break
    print(f"2. BH @10% FDR: {bh_k}/{len(pvals)} tests survive (vs {len(locked)} selected raw)")
    # 3. sub-period stability: holdout halves
    for k, spec in locked.items():
        c, m = spec["commodity"], spec["month"]
        r = ho_rets[c]
        sub = (r[r.index.month == m] * spec["direction"])
        h1 = sub[sub.index < "2020-01-01"]
        h2 = sub[sub.index >= "2020-01-01"]
        s1 = h1.mean() if len(h1) else 0
        s2 = h2.mean() if len(h2) else 0
        if abs(s1) > 0 or abs(s2) > 0:
            same = (s1 > 0) == (s2 > 0)
            if len(h1) >= 3 and len(h2) >= 3 and not same:
                print(f"3. sub-period FLIP: {k} 2015-19={s1*100:+.2f}% 2020+={s2*100:+.2f}%")
    # 4. roll convention: CL =F vs specific contract CLZ26 overlap
    try:
        import urllib.request, json as _j
        HDR = {"User-Agent": "Mozilla/5.0 Chrome/126.0"}
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/CLZ26"
               "?interval=1d&range=5y")
        d = _j.loads(urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=40).read())
        ts = d["chart"]["result"][0]["timestamp"]
        q = d["chart"]["result"][0]["indicators"]["quote"][0]
        cont = frames["CL"]["close"]
        spec_c = pd.Series([q["close"][i] for i in range(len(ts)) if q["close"][i]],
                           index=[pd.Timestamp(x, unit="s", tz="UTC").normalize()
                                  for i, x in enumerate(ts) if q["close"][i]])
        overlap = pd.concat([cont, spec_c], axis=1, join="inner").dropna()
        corr = overlap[0].corr(overlap[1])
        print(f"4. roll check: CL=F vs unadjusted CLZ26 contract, {len(overlap)} overlapping "
              f"bars, price corr {corr:.4f} (adjusted basis gap = roll method; "
              f"correlation near 1 = series tracks the real contract)")
    except Exception as e:
        print(f"4. roll check: skipped ({type(e).__name__})")
    # 5. cost ladder: portfolio avg monthly net at 0/50/100/200% costs
    for mult, label in ((0, "0%"), (0.5, "50%"), (1.0, "100%"), (2.0, "200%")):
        cost_tot = 0.0
        n = 0
        for k, spec in locked.items():
            c, m = spec["commodity"], spec["month"]
            r = ho_rets[c]
            sub = (r * spec["direction"])
            base_cost = (SPREAD_PCT[c] * 2.5) / 100.0 + fin_pct / 100.0
            net = sub - base_cost * mult
            cost_tot += net.mean()
            n += 1
        print(f"5. cost ladder {label:>5s}: mean net monthly across seasonals "
              f"{cost_tot/n*100:+.3f}%")
    # 6. mechanism audit — print survivors with mechanisms
    print("6. mechanism audit (survivors at 8%: OOS t>1):")
    for _, rw in ho_df.iterrows():
        if rw["oos_t8"] > 1 and rw["oos_n"] >= 8:
            print(f"   {rw['key']}: OOS t={rw['oos_t8']:+.2f} — see verdict table for mechanism")
    # 7. null-signal test: random directions on the same (comm, month) pairs
    rng = np.random.default_rng(7)
    null_ts = []
    for trial in range(200):
        tot_t = 0.0
        for k, spec in locked.items():
            c, m = spec["commodity"], spec["month"]
            r = ho_rets[c]
            sub = r[r.index.month == m]
            if len(sub) < 2:
                continue
            direction = rng.choice([-1, 1])
            net = sub * direction - (SPREAD_PCT[c] * 2.5) / 100.0 - fin_pct / 100.0
            tot_t += net.mean() / (net.std(ddof=1) / math.sqrt(len(net)) if net.std(ddof=1) > 0 else 1e-9)
        null_ts.append(tot_t)
    null_ts = np.array(null_ts)
    real_sum_t = sum(rw["oos_t8"] for _, rw in ho_df.iterrows() if np.isfinite(rw["oos_t8"]))
    print(f"7. null-signal: sum-of-OOS-t across random directions "
          f"mean {null_ts.mean():+.2f} (95% CI {np.percentile(null_ts,2.5):+.2f}.."
          f"{np.percentile(null_ts,97.5):+.2f}) vs real {real_sum_t:+.2f}")

    # ============ CORE-CLUSTER PORTFOLIO ($100, forced-flow family) ======
    # The full-35 sim showed the $100 min-notional + 9 concurrent positions
    # forces ~9x leverage (worst year -111%). The brief says at $100 you run
    # 6-8 trades/yr, not 35. The forced-flow cluster (hogs cycle, driving
    # season, harvest) is the mechanism-backed subset — the honest tradeable
    # test at this account size.
    # PRE-REGISTERED: the brief's 8 named trades, minus GF_5 (not offered on
    # T212). Locked BEFORE the holdout. SB_3 (post-hoc) deliberately excluded.
    CORE = ["HE_8", "HE_4", "HE_10", "HE_2", "RB_9", "ZC_12", "LE_5"]
    core_locked = {k: locked[k] for k in CORE if k in locked}
    # ENB scale for the CORE legs from the SELECTION window (not the full-35
    # scale: applying the 35-leg scale to a 7-leg portfolio understates risk)
    cla = {}
    for k, spec in core_locked.items():
        c, m = spec["commodity"], spec["month"]
        s = sel_rets[c] * spec["direction"]
        sub = s[s.index.month == m]
        cla[k] = sub.groupby(sub.index.year).mean()
    clf = pd.DataFrame(cla).dropna()
    if len(clf) >= 2 and clf.shape[1] >= 2:
        ceig = np.linalg.eigvalsh(clf.corr().values)
        cenb = ceig.sum() ** 2 / (ceig ** 2).sum() if (ceig ** 2).sum() > 0 else 1.0
        cscale = cenb / clf.shape[1] if cenb < 0.6 * clf.shape[1] else 1.0
    else:
        cenb, cscale = 1.0, 1.0
    print(f"core ENB (selection window): {cenb:.2f} of {len(clf.columns)} legs; "
          f"scale {cscale:.2f}")
    eq2, eqc2 = 100.0, [100.0]
    monthly2 = []
    core_netmap = {}
    for k, spec in core_locked.items():
        c, m = spec["commodity"], spec["month"]
        sub = (ho_rets[c][ho_rets[c].index.month == m] * spec["direction"])
        core_netmap[k] = sub.apply(lambda g: net_return(g, SPREAD_PCT[c], fin_pct))
    idx2 = sorted(set().union(*[set(v.index) for v in core_netmap.values()]))
    for ym in idx2:
        cap = min(DAILY_CAP, CAP_PCT * eq2)
        active = [k for k in core_netmap if ym in core_netmap[k].index]
        if not active:
            eqc2.append(eq2)
            continue
        pr = 0.0
        for k in active:
            c = locked[k]["commodity"]
            df = frames[c]
            prior = df.loc[: ym - pd.Timedelta(days=1), "close"].tail(60)
            if len(prior) < 20:
                continue
            dv = prior.pct_change().std()
            if not np.isfinite(dv) or dv <= 0:
                continue
            notional = (cap / len(active)) / (1.5 * dv)
            if notional < MIN_NOTIONAL:
                notional = MIN_NOTIONAL
            pr += notional / eq2 * core_netmap[k][ym] * cscale
        eq2 *= (1.0 + pr)
        eqc2.append(eq2)
        monthly2.append(pr)
    eq2s = pd.Series(eqc2)
    mdd2 = ((eq2s - eq2s.cummax()) / eq2s.cummax()).min() * 100
    m2 = pd.Series(monthly2)
    sh2 = m2.mean() / m2.std(ddof=1) * math.sqrt(12) if len(m2) > 1 and m2.std(ddof=1) > 0 else 0.0
    # ---- stops-vs-no-stops on the pre-registered core legs (brief §4.2) ----
    print("\n=== STOPS TEST (pre-registered core legs, 8% fin) ===")
    for k in CORE:
        spec = locked[k]
        c, m = spec["commodity"], spec["month"]
        df = frames[c]
        yr = df["close"].resample("ME").last().dropna()
        sub = (ho_rets[c][ho_rets[c].index.month == m] * spec["direction"])
        # no-stop version = base result
        base = sub.mean() if len(sub) else 0.0
        # with 2.5x monthly-ATR stop: count months where the signalled move
        # exceeded a 2.5-ATR adverse excursion (approx via monthly range)
        months = sub.index
        hits = 0
        for ym in months:
            # month-end may fall on a non-trading day; slice the calendar month
            m_start = ym - pd.offsets.MonthBegin(1)
            win = df[(df.index >= m_start) & (df.index <= ym)]
            if len(win) < 2:
                continue
            a = (win["high"] - win["low"]).mean()
            if not np.isfinite(a) or a <= 0:
                continue
            adverse = (win["low"].min() if spec["direction"] > 0 else -win["high"].max())
            move = (win["close"].iloc[-1] - win["close"].iloc[0]) * spec["direction"]
            if move < -2.5 * a:
                hits += 1
        print(f"  {k}: no-stop mean {base*100:+.2f}% | months breaching 2.5xATR "
              f"adverse: {hits}/{len(months)} (stop would cap ~{hits} losses)")

    # core yearly returns (brief §9 requires per-year)
    yrs = {}
    for ym in idx2:
        cap = min(DAILY_CAP, CAP_PCT * eq2)
        active = [k for k in core_netmap if ym in core_netmap[k].index]
        if not active:
            yrs[ym.year] = yrs.get(ym.year, 1.0)
            continue
        pr = 0.0
        for k in active:
            c = locked[k]["commodity"]
            df = frames[c]
            prior = df.loc[: ym - pd.Timedelta(days=1), "close"].tail(60)
            if len(prior) < 20:
                continue
            dv = prior.pct_change().std()
            if not np.isfinite(dv) or dv <= 0:
                continue
            notional = (cap / len(active)) / (1.5 * dv)
            if notional < MIN_NOTIONAL:
                notional = MIN_NOTIONAL
            pr += notional / eq2 * core_netmap[k][ym] * scale
        yrs[ym.year] = yrs.get(ym.year, 1.0) * (1.0 + pr)
    pos_yrs = sum(1 for v in yrs.values() if v > 1.0)
    print(f"core yearly: { {y: round((v-1)*100,1) for y,v in sorted(yrs.items())} } "
          f"| positive {pos_yrs}/{len(yrs)} years")

    print("\n=== CORE-CLUSTER PORTFOLIO ($100, PRE-REGISTERED legs, 8% financing) ===")
    print(f"terminal ${eq2:.2f} | monthly Sharpe {sh2:.2f} | max DD {mdd2:.1f}% | "
          f"trades/mo {sum(1 for v in monthly2 if v != 0)/max(len(idx2),1):.1f}")
    print(f"core legs: {CORE}")

    print("\n=== VERDICT ===")
    print(f"selected {len(locked)} (expected by chance ~{exp_chance:.1f})")
    print(f"net-positive OOS at 8%: {pos8}/{tot} (chance ~{tot/2:.1f})")
    print(f"portfolio monthly Sharpe net (8% fin): {sharpe:.2f} (kill if < 0.5)")
    print(f"terminal $100 -> ${eq:.2f}; worst year {min(yr_ret.values()):.1f}%")
    print(f"BH survivors: {bh_k}/{len(pvals)}")
    print(f"null-signal real sum-t {real_sum_t:+.2f} vs null {null_ts.mean():+.2f}")


if __name__ == "__main__":
    main()
