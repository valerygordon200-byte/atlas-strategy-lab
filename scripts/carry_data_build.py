#!/usr/bin/env python3
"""carry_data_build.py — assemble the 8-currency policy-rate series.

Source: the events archive's interest-rate-decision events (actual = rate
level after the decision), 2015-01 -> present. Adjustments:
  - ECB: archive 'actual' is the MRO rate; carry uses the DEPOSIT rate.
    deposit = MRO - 50bp (before 2024-09-12), MRO - 15bp (after).
  - RBNZ: archive coverage starts 2021-11; pre-2021 OCR levels are filled from
    known history (well-documented official levels).
Output: market-data/rates/policy_rates.csv (date, USD, EUR, GBP, JPY, AUD,
CAD, CHF, NZD) + a per-currency change log.
"""
from pathlib import Path
import pandas as pd

BASE = Path("E:/forex-data")
OUT = BASE / "market-data/rates"
OUT.mkdir(parents=True, exist_ok=True)

NAMES = {"USD": "Fed Interest Rate Decision",
         "EUR": "ECB Interest Rate Decision",
         "GBP": "BoE Interest Rate Decision",
         "JPY": "BoJ Interest Rate Decision",
         "AUD": "RBA Interest Rate Decision",
         "CAD": "BoC Interest Rate Decision",
         "CHF": "SNB Interest Rate Decision",
         "NZD": "RBNZ Interest Rate Decision"}

ev = pd.read_parquet(BASE / "market-data/events/events.parquet")
ev["date_utc"] = pd.to_datetime(ev["date_utc"], utc=True)

# known RBNZ OCR levels before the archive's first decision (well documented)
RBNZ_FILL = [("2015-01-01", 3.5), ("2016-11-10", 2.0), ("2017-02-23", 1.75),
             ("2019-08-07", 1.0), ("2020-03-16", 0.25), ("2021-10-06", 0.5)]

series = {}
for ccy, title in NAMES.items():
    sub = ev[(ev["currency"] == ccy) & (ev["title"] == title)].sort_values("date_utc")
    a = pd.to_numeric(sub["actual"], errors="coerce")
    sub = sub[a.notna()].copy()
    sub["rate"] = a[a.notna()].values
    sub = sub[["date_utc", "rate"]].rename(columns={"date_utc": "date"})
    if ccy == "EUR":
        # MRO -> deposit: the MRO/deposit spread changed over time (known)
        def deposit_from_mro(d):
            d = pd.Timestamp(d)
            if d < pd.Timestamp("2016-03-10", tz="UTC"):
                return 0.25   # MRO 0.05, deposit -0.20
            if d < pd.Timestamp("2019-09-12", tz="UTC"):
                return 0.40   # MRO 0.00, deposit -0.40
            if d < pd.Timestamp("2024-09-12", tz="UTC"):
                return 0.50   # MRO 0.00, deposit -0.50 ... MRO 4.50, deposit 4.00
            return 0.15       # new framework: MRO = deposit + 15bp
        sub["rate"] = sub["rate"] - sub["date"].apply(deposit_from_mro)
    if ccy == "NZD":
        fill = pd.DataFrame(RBNZ_FILL, columns=["date", "rate"])
        fill["date"] = pd.to_datetime(fill["date"], utc=True)
        sub = pd.concat([fill, sub]).sort_values("date")
    series[ccy] = sub

# daily grid 2015-01-01 -> 2026-08-10, carry-forward last decision rate
grid = pd.date_range("2015-01-01", "2026-08-10", freq="D", tz="UTC")
out = pd.DataFrame(index=grid)
for ccy, sub in series.items():
    sub = sub.set_index("date")["rate"].sort_index()
    out[ccy] = sub.reindex(grid, method="ffill")

# sanity: level at a few anchor dates
for d in ["2016-06-01", "2019-06-01", "2022-06-01", "2024-06-01", "2026-08-01"]:
    row = out.loc[d]
    print(d, {c: round(float(v), 2) for c, v in row.items()})

out.to_csv(OUT / "policy_rates.csv", index_label="date")
print("\nsaved market-data/rates/policy_rates.csv  rows:", len(out))
# change log
log = []
for ccy, sub in series.items():
    ch = sub[sub["rate"].diff().abs() > 1e-9]
    log.append((ccy, len(ch), ch["date"].min(), ch["date"].max(), float(ch["rate"].iloc[-1])))
for ccy, n, d0, d1, last in log:
    print(f"{ccy}: {n} changes | {d0.date()} -> {d1.date()} | last level {last}")
