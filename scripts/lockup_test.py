#!/usr/bin/env python3
"""lockup_test.py — IPO lockup expiry, strict battery.

Hypothesis (mechanism family B, forced flows): insiders are legally barred from
selling for the lockup period (standard 180 days in the US); when it lifts, a
price-insensitive supply overhang hits the market -> a short window around the
expiry should earn negative abnormal returns (Field & Hanka 2001 documented
~-1.5% at expiry).

Pre-registered spec:
  Universe:      non-SPAC US IPOs 2020-2025 with price data (844 names).
  Expiry proxy:  IPO date + 180 days (the documented standard for the
                 overwhelming majority of US IPOs; non-180 lockups and
                 early releases add noise, biasing AGAINST the effect).
  Trade:         SHORT close[D-1] -> close[D+2], D = first trading day >= expiry.
  Costs:         ladder 0 / 50 / 100 / 200 bps round trip.
  Controls:      SPY market adjustment; same-name random-window permutation;
                 long side as the sign-flip control.
  Split:         IS = expiry < 2024-01-01, OOS = expiry >= 2024-01-01 (no refit).
  Gates:         IS market-adj mean > 0, t >= 2.5; permutation p < 0.01;
                 OOS mean > 0, t >= 2.0; sub-period stability.
"""
import json
import math
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
IPODIR = BASE / "market-data/ipos"
PRICEDIR = IPODIR / "ipo_prices"
RNG = np.random.default_rng(41)
LOCKUP_DAYS = 180
IS_CUT = pd.Timestamp("2024-01-01")
# Windows device names: a file literally named CON.csv opens the console device
# and hangs on read. Exclude any ticker that collides with a reserved name.
WIN_RESERVED = {"con", "prn", "aux", "nul", "clock$"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}


# ---- load prices ----
# Adjusted closes: raw close is contaminated by splits (2020-25 IPO names split
# frequently; a raw series shows a fake -90% crash on split day).
def load_series(sym):
    df = pd.read_csv(PRICEDIR / f"{sym}.csv")
    col = "adjclose" if "adjclose" in df.columns else "close"
    s = pd.Series(df[col].values, index=pd.to_datetime(df["date"]))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s[s > 0]

# quality gates
PRICE_FLOOR = 2.0          # penny stocks have meaningless prints; require >= $2 at entry
WINZ = 0.25                # winsorize window returns at +/-25% (micro-cap 100%+ moves wreck the mean)

def is_spac(rec):
    return rec.get("ipo_price", "") in ("$10.00", "$10")

uniq = json.load(open(IPODIR / "ipo_list.json"))
names = [r for r in uniq if not is_spac(r) and r["symbol"].lower() not in WIN_RESERVED
        and (PRICEDIR / f"{r['symbol']}.csv").exists()]
print(f"non-SPAC IPOs with prices: {len(names)} (reserved-name files excluded)")

# SPY market control
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}
def spy_close():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1d&range=10y"
    req = urllib.request.Request(url, headers=HDR)
    import json as j, time
    d = j.loads(urllib.request.urlopen(req, timeout=30).read())
    r = d["chart"]["result"][0]
    return pd.Series(
        [c for c in r["indicators"]["quote"][0]["close"] if c and c > 0],
        index=pd.to_datetime([time.strftime("%Y-%m-%d", time.gmtime(t)) for t in r["timestamp"]])[
            [c is not None and c > 0 for c in r["indicators"]["quote"][0]["close"]]],
    )
try:
    spy = spy_close()
    spy = spy[~spy.index.duplicated(keep="last")].sort_index()
    print(f"SPY loaded: {len(spy)} bars")
except Exception as e:
    print("SPY fetch failed:", e)
    spy = None

# ---- build events ----
events = []
for rec in names:
    sym = rec["symbol"]
    s = load_series(sym)
    ipo = pd.Timestamp(rec["date"])
    expiry = ipo + pd.Timedelta(days=LOCKUP_DAYS)
    # D = first trading day on or after expiry
    after = s.index[s.index >= expiry]
    if len(after) == 0:
        continue
    d0 = after[0]
    idx = s.index
    i0 = idx.get_loc(d0)
    if i0 < 2 or i0 + 2 >= len(idx):
        continue
    d_minus1 = idx[i0 - 1]
    d_plus2 = idx[i0 + 2]
    p_in = float(s.loc[d_minus1])
    p_out = float(s.loc[d_plus2])
    if p_in < PRICE_FLOOR or p_out <= 0:
        continue
    short_ret = p_in / p_out - 1.0          # short: profit if price fell
    mkt = None
    if spy is not None:
        si = spy.index
        if d_minus1 in si and d_plus2 in si:
            mkt = float(spy.loc[d_plus2] / spy.loc[d_minus1] - 1.0)
    events.append({"symbol": sym, "ipo": ipo, "expiry": d0, "win_start": d_minus1,
                   "win_end": d_plus2, "short_ret": short_ret, "mkt": mkt})

ev = pd.DataFrame(events)
print(f"usable events: {len(ev)}  (expiries {ev['expiry'].min().date()} -> {ev['expiry'].max().date()})")
ev["adj"] = ev["short_ret"] - ev["mkt"].fillna(0.0)   # market-adjusted short return
ev.to_csv(BASE / "reports" / "lockup_events.csv", index=False)

# ---- split ----
is_ev = ev[ev["expiry"] < IS_CUT]
oos_ev = ev[ev["expiry"] >= IS_CUT]
print(f"IS: {len(is_ev)} events | OOS: {len(oos_ev)} events")

def tstat(x):
    if len(x) < 3:
        return None
    sd = x.std(ddof=1)
    return float(x.mean() / (sd / math.sqrt(len(x)))) if sd > 0 else 0.0

def winsor(s, w=WINZ):
    return s.clip(lower=-w, upper=w)

def report(name, s, label="short"):
    w = winsor(s)
    print(f"  {name}: n={len(s)} mean={w.mean()*100:+.3f}% (winz) median={s.median()*100:+.3f}% "
          f"t(winz)={tstat(w):.2f} win={(s<0).mean()*100:.0f}% (short wins when price falls)")
    return w

print("\n=== HEADLINE: SHORT close[D-1] -> close[D+2], market-adjusted ===")
report("IS ", is_ev["adj"])
report("OOS", oos_ev["adj"])

print("\n=== raw (unadjusted) ===")
report("IS raw ", is_ev["short_ret"])
report("OOS raw", oos_ev["short_ret"])

print("\n=== long side (sign-flip control) ===")
report("IS long ", -is_ev["short_ret"])
report("OOS long", -oos_ev["short_ret"])

# ---- permutation: same-name random windows ----
def perm_p(oos_adj, n=2000):
    cnt = 1
    for _ in range(n):
        null = RNG.choice([-1.0, 1.0], len(oos_adj)) * np.abs(oos_adj.to_numpy())
        if null.mean() >= oos_adj.mean():
            cnt += 1
    return cnt / (n + 1)

p_perm = perm_p(winsor(oos_ev["adj"]))
print(f"\npermutation p (random sign, OOS adjusted, winsorized): {p_perm:.4f}")

# random-window control: place each event at a random date in the stock's life
SERIES_CACHE = {}
def cached(sym):
    if sym not in SERIES_CACHE:
        SERIES_CACHE[sym] = load_series(sym)
    return SERIES_CACHE[sym]

def random_window_control(ev, n=1000):
    means = []
    rows = []
    for _, e in ev.iterrows():
        s = cached(e["symbol"])
        if len(s) < 30:
            continue
        rows.append(s)
    for _ in range(n):
        vals = []
        for s in rows:
            j = RNG.integers(5, len(s) - 5)
            if float(s.iloc[j]) < PRICE_FLOOR:
                continue
            r = float(s.iloc[j] / s.iloc[j + 3] - 1.0)
            vals.append(max(-WINZ, min(WINZ, r)))   # same winsor as the test
        means.append(np.mean(vals))
    return np.array(means)

for _, e in oos_ev.iterrows():
    cached(e["symbol"])
null_windows = random_window_control(oos_ev, n=500)
actual = winsor(oos_ev["short_ret"]).mean()
p_win = float((null_windows <= actual).mean())
print(f"random-window control (OOS): null mean {null_windows.mean()*100:+.3f}% "
      f"vs actual {actual*100:+.3f}%  p(<=actual)={p_win:.4f}")

# ---- bootstrap ----
def boot(s, n=5000):
    rng = np.random.default_rng(7)
    arr = s.to_numpy()
    means = np.array([np.mean(rng.choice(arr, len(arr))) for _ in range(n)])
    return float((means <= 0).mean())

print(f"bootstrap P(mean<=0) IS adj: {boot(winsor(is_ev['adj'])):.4f} | OOS adj: {boot(winsor(oos_ev['adj'])):.4f}")

# ---- cost ladder ----
print("\n=== cost ladder (OOS, market-adjusted short ret minus cost, winsorized) ===")
for cost in (0.0, 0.005, 0.01, 0.02):
    net = winsor(oos_ev["adj"]) - cost
    print(f"  {cost*100:.0f}bps: mean {net.mean()*100:+.3f}% t={tstat(net):.2f}")

# ---- sub-period stability (OOS) ----
print("\n=== OOS sub-periods ===")
for lo, hi in [(pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")),
               (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-08-01"))]:
    sub = oos_ev[(oos_ev["expiry"] >= lo) & (oos_ev["expiry"] < hi)]
    report(f"{lo.date()} -> {hi.date()}", sub["adj"])

# ---- SPAC subset (separate check) ----
spac_names = [r for r in uniq if is_spac(r) and (PRICEDIR / f"{r['symbol']}.csv").exists()]
spac_ev = []
for rec in spac_names:
    s = load_series(rec["symbol"])
    ipo = pd.Timestamp(rec["date"])
    after = s.index[s.index >= (ipo + pd.Timedelta(days=LOCKUP_DAYS))]
    if len(after) == 0:
        continue
    d0 = after[0]
    idx = s.index
    i0 = idx.get_loc(d0)
    if i0 < 2 or i0 + 2 >= len(idx):
        continue
    if float(s.iloc[i0 - 1]) < PRICE_FLOOR:
        continue
    spac_ev.append(float(s.iloc[i0 - 1] / s.iloc[i0 + 2] - 1.0))
spac_s = pd.Series(spac_ev)
print(f"\nSPAC subset: n={len(spac_s)} mean short {spac_s.mean()*100:+.3f}% t={tstat(spac_s):.2f}")
