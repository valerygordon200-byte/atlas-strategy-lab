"""
dual_momentum_test.py — Dual / absolute momentum asset allocation (Antonacci),
candidate #2 from the platform scan, tested through the strict battery.

Mechanism (Antonacci, Dual Momentum Investing — fully public logic):
  1. Universe: SPY (US eq), EFA (intl eq), VNQ (REITs), GLD (gold), DBC (commod),
     AGG/IEF (bonds), SHY (cash proxy).
  2. Monthly: 12-month total return per asset.
  3. Absolute filter: asset eligible iff its own 12m return > 0.
  4. Relative rank: among eligible, hold the top-k (k=1 or 2), equal weight.
  5. If none eligible: hold cash (SHY).
  6. Rebalance monthly, no leverage, no shorting.

Costs: 0.5 bps/trade + 0.5% annual drag (conservative for ETF execution),
charged on the traded fraction each month.

Outputs: reports/dual_momentum_strict.csv/.md
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(13)

UNIVERSE = ["SPY", "EFA", "VNQ", "GLD", "DBC", "IEF", "SHY"]
CASH = "SHY"
MOM = 12            # 12-month momentum lookback
K_TOP = 1           # hold top-k (variant 2 uses 2)
COST_BPS = 0.0005   # per-trade cost (spread+slippage), charged on traded fraction
DRAG = 0.005 / 12   # 0.5%/yr expense drag, monthly

N_PERM = 1000
N_BOOT = 5000
IS_END = "2017-12-31"   # 2007-2017 in-sample, 2018-2026 holdout


def load_close(name):
    df = pd.read_csv(BASE / "market-data/raw/yahoo" / f"ETF_{name}_d.csv",
                     index_col=0, parse_dates=True)
    return df["close"].sort_index()


def monthly_returns(closes):
    df = pd.concat(closes, axis=1).dropna()
    df.columns = UNIVERSE
    m = df.resample("ME").last()
    return m.pct_change().dropna()


def simulate(mret, k, cost_bps=COST_BPS, drag=DRAG, shuffle=False):
    """Monthly dual momentum. Returns (dates, monthly_net, turnover).
    shuffle=True replaces momentum ranking with random ranking (null-signal)."""
    mom = mret.rolling(MOM).apply(lambda x: (1 + x).prod() - 1, raw=True)
    dates = []
    nets = []
    turnover = 0.0
    prev_weights = pd.Series(0.0, index=UNIVERSE)
    rng = np.random.default_rng(1)
    for i in range(MOM, len(mret)):
        if shuffle:
            eligible = mom.iloc[i].drop(index=CASH, errors="ignore")
            if len(eligible) == 0:
                w = pd.Series(0.0, index=UNIVERSE)
                w[CASH] = 1.0
            else:
                top = eligible.sample(k, random_state=int(rng.integers(1e9))).index
                w = pd.Series(0.0, index=UNIVERSE)
                w[top] = 1.0 / len(top)
        else:
            eligible = mom.iloc[i][mom.iloc[i] > 0].drop(index=CASH, errors="ignore")
            if len(eligible) == 0:
                w = pd.Series(0.0, index=UNIVERSE)
                w[CASH] = 1.0
            else:
                top = eligible.nlargest(k)
                w = pd.Series(0.0, index=UNIVERSE)
                w[top.index] = 1.0 / len(top)
        traded = (w - prev_weights).abs().sum()
        turnover += traded
        net = float((w * mret.iloc[i]).sum()) - traded * cost_bps - drag
        dates.append(mret.index[i])
        nets.append(net)
        prev_weights = w
    return np.array(dates), np.array(nets), turnover


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


def wf_monthly(net, dates, trail_months=12, min_ev=18):
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
            if trail_cnt < 18 or lo >= i:
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


def battery(label, dates, net, is_cut):
    dates = pd.DatetimeIndex(pd.to_datetime(np.asarray(dates)))
    net = np.asarray(net, dtype=float)
    s = pd.Series(net, index=dates)
    is_ = s[s.index <= is_cut]
    oos = s[s.index > is_cut]
    is_s, oos_s = stats(is_), stats(oos)
    if is_s["mean"] is None or oos_s["mean"] is None:
        return dict(name=label, n=len(s), is_mean=None, is_t=None, p_is=None,
                    ho_mean=None, ho_t=None, p_ho=None, wf_mean=None, p_wf=None,
                    boot_p=None, trim=None, VERDICT="INSUFFICIENT", gates="empty slice")
    p_is = perm_signflip(is_s["mean"], is_.to_numpy())
    p_ho = perm_signflip(oos_s["mean"], oos.to_numpy())
    wf = wf_monthly(net, dates)
    wf_mean = float(wf.mean()) if len(wf) else None
    p_wf = wf_perm(wf_mean if wf_mean is not None else -1e9, dates, net)
    boot_p = bootstrap(wf.values) if wf_mean is not None else 1.0
    yrs = s.groupby(s.index.year).sum()
    trim = float(yrs.sort_values().iloc[1:-1].mean()) if len(yrs) >= 3 else None
    gates = {
        "|t_is|>2": is_s["t"] is not None and abs(is_s["t"]) > 2,
        "p_is<0.01": p_is < 0.01,
        "ho t>2&p<0.05": oos_s["t"] is not None and oos_s["t"] > 2 and p_ho < 0.05,
        "wf>0&p<0.05": wf_mean is not None and wf_mean > 0 and p_wf < 0.05,
        "boot<0.05": boot_p < 0.05,
        "trim>0": trim is not None and trim > 0,
    }
    return dict(name=label, n=len(s), is_mean=round(is_s["mean"] * 100, 3),
                is_t=round(is_s["t"], 2), p_is=round(p_is, 4),
                ho_mean=round(oos_s["mean"] * 100, 3), ho_t=round(oos_s["t"], 2),
                p_ho=round(p_ho, 4), wf_mean=round(wf_mean * 100, 3),
                p_wf=round(p_wf, 4), boot_p=round(boot_p, 4),
                trim=round(trim * 100, 3), VERDICT="PASS" if all(gates.values()) else "FAIL",
                gates="; ".join(k for k, v in gates.items() if not v) or "all pass")


def main():
    closes = {k: load_close(k) for k in UNIVERSE}
    mret = monthly_returns(closes)
    rows = []
    for k in (1, 2):
        dates, net, turn = simulate(mret, k)
        rows.append(battery(f"dual_mom_top{k}", dates, net, IS_END))
    # buy-and-hold references
    for ref in ("SPY", "IEF"):
        s = mret[ref].dropna()
        rows.append(battery(f"buyhold_{ref}", s.index.to_numpy(), s.to_numpy(), IS_END))
    # robustness battery on top-1
    dates, net, turn = simulate(mret, 1)
    for tag, cb, dr in (("cost0x", 0.0, 0.0), ("cost2x", 2 * COST_BPS, 2 * DRAG),
                        ("cost5x", 5 * COST_BPS, 5 * DRAG)):
        d2, n2, _ = simulate(mret, 1, cost_bps=cb, drag=dr)
        rows.append(battery(f"top1_{tag}", d2, n2, IS_END))
    d3, n3, _ = simulate(mret, 1, shuffle=True)
    rows.append(battery("top1_null_random_rank", d3, n3, IS_END))
    # sub-period stability: split holdout in half
    ho = pd.Series(net, index=pd.DatetimeIndex(pd.to_datetime(dates)))
    ho = ho[ho.index > IS_END]
    half = ho.index[len(ho) // 2]
    for tag, seg in (("ho_first_half", ho[ho.index <= half]),
                     ("ho_second_half", ho[ho.index > half])):
        ss = stats(seg.to_numpy())
        rows.append(dict(name=f"top1_{tag}", n=len(seg),
                         is_mean=None, is_t=None, p_is=None,
                         ho_mean=round(ss["mean"] * 100, 3) if ss["mean"] is not None else None,
                         ho_t=round(ss["t"], 2) if ss["t"] is not None else None,
                         p_ho=None, wf_mean=None, p_wf=None, boot_p=None, trim=None,
                         VERDICT="PASS" if (ss["t"] is not None and ss["t"] > 2 and ss["mean"] > 0) else "FAIL",
                         gates="t>2 & mean>0 (direct, no IS split)"))

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "dual_momentum_strict.csv", index=False)
    lines = ["# Dual momentum (Antonacci) — STRICT battery (candidate #2 from platform scan)", "",
             "Mechanism: 12m absolute filter -> rank -> top-k, cash if none eligible, monthly rebalance. "
             "Costs: 0.5bps/trade + 0.5%/yr drag. IS <= 2017-12, holdout 2018-2026.", "",
             "| variant | n | IS%/mo | IS t | p_is | HO%/mo | HO t | p_ho | WF%/mo | p_wf | boot | trim | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        lines.append(f"| {r['name']} | {r['n']} | {r['is_mean']:+.3f} | {r['is_t']:+.2f} | {r['p_is']:.3f} | "
                     f"{r['ho_mean']:+.3f} | {r['ho_t']:+.2f} | {r['p_ho']:.3f} | {r['wf_mean']:+.3f} | "
                     f"{r['p_wf']:.3f} | {r['boot_p']:.3f} | {r['trim']:+.3f} | **{r['VERDICT']}** |")
    lines += ["", "Failed gates:", ""]
    for _, r in res.iterrows():
        lines.append(f"- {r['name']}: {r['gates']}")
    (OUT / "dual_momentum_strict.md").write_text("\n".join(lines), encoding="utf-8")
    print(res.to_string(index=False))
    print("\n[saved]", OUT / "dual_momentum_strict.md")


if __name__ == "__main__":
    main()
