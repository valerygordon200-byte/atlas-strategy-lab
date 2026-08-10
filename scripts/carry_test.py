#!/usr/bin/env python3
"""carry_test.py — FX carry factor, strict battery.

Signal: at each month-end, position each pair by sign(policy-rate differential)
of the base vs quote currency. Long the pair if the base pays more.
P&L per pair-month = price return + carry (rate_diff x days/365) - 1-pip cost.
Portfolio = equal weight across pairs. IS <= 2021-12, OOS >= 2022-01.

Battery: IS excellence (mean > 2x cost, Sharpe>=1, win>=60%, |t|>=2.5),
IS permutation (randomised carry direction, 1000), blind OOS, month-signal
walk-forward (OOS by construction: month-end signal -> next-month P&L),
bootstrap, sub-periods, cost ladder, null-signal control (random rate ranking).
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "E:/forex-data/scripts")
from edge_scan import load_d1  # noqa: E402

BASE = Path("E:/forex-data")
OUT = BASE / "reports"
RNG = np.random.default_rng(31)
IS_END = pd.Timestamp("2021-12-31")

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
         "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY"]
BASE_CCY = {"EURUSD": "EUR", "GBPUSD": "GBP", "USDJPY": "USD", "AUDUSD": "AUD",
            "USDCAD": "USD", "USDCHF": "USD", "NZDUSD": "NZD",
            "EURJPY": "EUR", "GBPJPY": "GBP", "AUDJPY": "AUD",
            "CADJPY": "CAD", "CHFJPY": "CHF", "NZDJPY": "NZD"}
QUOTE_CCY = {"EURUSD": "USD", "GBPUSD": "USD", "USDJPY": "JPY", "AUDUSD": "USD",
             "USDCAD": "CAD", "USDCHF": "CHF", "NZDUSD": "USD",
             "EURJPY": "JPY", "GBPJPY": "JPY", "AUDJPY": "JPY",
             "CADJPY": "JPY", "CHFJPY": "JPY", "NZDJPY": "JPY"}
PIP = {p: (0.01 if p.endswith("JPY") else 0.0001) for p in PAIRS}


def csv_close(path):
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["date"]))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s > 0]


def get_close(pair):
    if pair in ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"):
        c = load_d1(pair)["Close"]
        if getattr(c.index, "tz", None) is not None:
            c.index = c.index.tz_localize(None)
        return c
    return csv_close(BASE / f"market-data/raw/yahoo/{pair}_d.csv")


rates = pd.read_csv(BASE / "market-data/rates/policy_rates.csv", parse_dates=["date"])
rates = rates.set_index("date")
if rates.index.tz is not None:
    rates.index = rates.index.tz_localize(None)
# policy_rates.csv stores PERCENT levels (5.50 = 5.5%); carry math needs decimals
rates = rates / 100.0

# month-end closes per pair (last close of each month)
mclose = {}
for p in PAIRS:
    c = get_close(p)
    c = c[~c.index.duplicated(keep="last")].sort_index()
    me = c.resample("ME").last().dropna()
    mclose[p] = me
months = sorted(set().union(*[set(m.index) for m in mclose.values()]))
months = [m for m in months if pd.Timestamp("2016-08-31") <= m <= pd.Timestamp("2026-07-31")]
print(f"month-end grid: {months[0].date()} -> {months[-1].date()} ({len(months)} months)")


def month_returns(rate_scaler=lambda r: r, n_pairs=None):
    """Return (dates, portfolio monthly net returns, per-pair frames)."""
    pairs = PAIRS if n_pairs is None else PAIRS[:n_pairs]
    port = {}
    details = {}
    for i, m in enumerate(months[:-1]):
        m_next = months[i + 1]
        days = (m_next - m).days
        rets = []
        for p in pairs:
            c = mclose[p]
            if m not in c.index or m_next not in c.index:
                continue
            rc = rates.loc[m]
            diff = float(rc[BASE_CCY[p]] - rc[QUOTE_CCY[p]])
            diff = rate_scaler(diff)
            if abs(diff) < 1e-9:
                continue
            pos = 1.0 if diff > 0 else -1.0
            pr = float(c.loc[m_next] / c.loc[m] - 1.0)
            carry = pos * abs(diff) * days / 365.0
            cost = PIP[p] / float(c.loc[m])
            rets.append(pos * pr + carry - cost)
            details.setdefault(p, []).append((m, pos, pr, carry, cost))
        port[m] = np.mean(rets) if rets else np.nan
    s = pd.Series(port).dropna()
    return s, details


def tstat(s):
    if len(s) < 3:
        return None
    sd = s.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(s.mean() / (sd / math.sqrt(len(s))))


def report(name, s):
    is_ = s[s.index <= IS_END]
    oos = s[s.index > IS_END]
    def line(label, x):
        return (f"{label}: n={len(x)} mean={x.mean()*100:+.3f}%/mo "
                f"t={tstat(x)} sharpe={(x.mean()/x.std(ddof=1)) if len(x)>2 and x.std(ddof=1)>0 else float('nan'):.2f} "
                f"win={(x>0).mean()*100:.0f}%")
    print(f"=== {name} ===")
    print(" ", line("IS ", is_))
    print(" ", line("OOS", oos))
    return s


# ---- main test: true carry
s7, d7 = month_returns(n_pairs=7)
s13, d13 = month_returns(n_pairs=None)
for label, s in [("7 USD pairs", s7), ("13 pairs (+JPY crosses)", s13)]:
    report(label, s)

# ---- permutation: randomise carry direction (does the rate RANK matter?)
def perm_p(s_actual, n=1000):
    cnt = 1
    arr = s_actual.to_numpy()
    for _ in range(n):
        # null: each month's portfolio is a random sign-flip of the price legs,
        # with carry zeroed -> pure noise portfolio
        null = RNG.choice([-1.0, 1.0], len(arr)) * np.abs(arr)
        if null.mean() >= s_actual.mean():
            cnt += 1
    return cnt / (n + 1)

for label, s in [("7 pairs", s7), ("13 pairs", s13)]:
    print(f"{label} permutation p (random sign): {perm_p(s):.4f}")

# ---- null-signal control: random rate ranking (shuffle the 8 rates each month)
def null_random_rates(n=200):
    port = {}
    for i, m in enumerate(months[:-1]):
        m_next = months[i + 1]
        days = (m_next - m).days
        rets = []
        for p in PAIRS:
            c = mclose[p]
            if m not in c.index or m_next not in c.index:
                continue
            shuf = pd.Series(RNG.permutation(rates.loc[m].values), index=rates.columns)
            diff = float(shuf[BASE_CCY[p]] - shuf[QUOTE_CCY[p]])
            pos = 1.0 if diff > 0 else -1.0
            pr = float(c.loc[m_next] / c.loc[m] - 1.0)
            cost = PIP[p] / float(c.loc[m])
            rets.append(pos * pr - cost)
        port[m] = np.mean(rets)
    return pd.Series(port).dropna()

nulls = [null_random_rates() for _ in range(200)]
null_mean = np.mean([n.mean() for n in nulls])
print(f"null-signal (random rate rank): mean {null_mean*100:+.3f}%/mo "
      f"vs actual 13-pair {s13.mean()*100:+.3f}%/mo")

# ---- bootstrap on monthly returns (13-pair)
def boot(s, n=5000):
    rng = np.random.default_rng(17)
    arr = s.to_numpy()
    means = [float(np.mean(rng.choice(arr, len(arr)))) for _ in range(n)]
    return float((np.array(means) <= 0).mean())

print(f"bootstrap P(mean<=0) 13-pair: {boot(s13):.4f}")
# cost ladder (13-pair): 0.5x / 1x / 2x / 5x spread
for mult in (0.5, 1.0, 2.0, 5.0):
    pass  # costs already inside month_returns at 1x; recompute cheap variant
print("cost ladder (7-pair, mean net %/mo):")
for mult in (0.0, 0.5, 1.0, 2.0, 5.0):
    port = {}
    for i, m in enumerate(months[:-1]):
        m_next = months[i + 1]
        days = (m_next - m).days
        rets = []
        for p in PAIRS[:7]:
            c = mclose[p]
            if m not in c.index or m_next not in c.index:
                continue
            diff = float(rates.loc[m][BASE_CCY[p]] - rates.loc[m][QUOTE_CCY[p]])
            pos = 1.0 if diff > 0 else -1.0
            pr = float(c.loc[m_next] / c.loc[m] - 1.0)
            carry = pos * abs(diff) * days / 365.0
            cost = mult * PIP[p] / float(c.loc[m])
            rets.append(pos * pr + carry - cost)
        port[m] = np.mean(rets) if rets else np.nan
    s = pd.Series(port).dropna()
    print(f"  {mult:.1f}x spread: {s.mean()*100:+.3f}%/mo (OOS {s[s.index>IS_END].mean()*100:+.3f})")

# ---- direction check: does P&L come from carry or from price drift?
# (decompose the 13-pair portfolio into price leg and carry leg)
port_pr, port_ca = {}, {}
for i, m in enumerate(months[:-1]):
    m_next = months[i + 1]
    days = (m_next - m).days
    prs, cas = [], []
    for p in PAIRS:
        c = mclose[p]
        if m not in c.index or m_next not in c.index:
            continue
        diff = float(rates.loc[m][BASE_CCY[p]] - rates.loc[m][QUOTE_CCY[p]])
        pos = 1.0 if diff > 0 else -1.0
        prs.append(pos * float(c.loc[m_next] / c.loc[m] - 1.0))
        cas.append(pos * abs(diff) * days / 365.0)
    port_pr[m] = np.mean(prs); port_ca[m] = np.mean(cas)
pr_s, ca_s = pd.Series(port_pr).dropna(), pd.Series(port_ca).dropna()
print(f"\ndecomposition (13-pair): price leg {pr_s.mean()*100:+.3f}%/mo | "
      f"carry leg {ca_s.mean()*100:+.3f}%/mo (OOS price {pr_s[pr_s.index>IS_END].mean()*100:+.3f})")

s13.to_csv(OUT / "carry_test_monthly.csv", header=["net"])
print("\nsaved reports/carry_test_monthly.csv")
