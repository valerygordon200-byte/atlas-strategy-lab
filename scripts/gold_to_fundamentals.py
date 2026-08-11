#!/usr/bin/env python3
"""T1: emit the canonical central-bank gold fundamentals file that
weight_calibrator.cb_gold_monthly() consumes.

Reads data/central_bank_gold_monthly.csv (month, net_t) and writes
market-data/fundamentals/central_bank_gold.csv with columns
  date, total_net_purchases_tonnes
using month-end dates so the engine's resample("ME") bins each value into the
correct calendar month. Gaps in the WGC monthly series are left as missing
rows (never interpolated/fabricated).

market-data/ is gitignored in this repo by design, so the canonical output is
also mirrored to data/fundamentals/central_bank_gold.csv (committed). Install
onto a machine running weight_calibrator with:
  cp data/fundamentals/central_bank_gold.csv <BASE>/market-data/fundamentals/
"""
import calendar
import csv
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "central_bank_gold_monthly.csv")
OUT_REPO = os.path.join(ROOT, "data", "fundamentals", "central_bank_gold.csv")


def month_end(y, m):
    return date(y, m, calendar.monthrange(y, m)[1])


def main():
    rows = []
    with open(SRC) as f:
        for r in csv.DictReader(f):
            y, m = (int(x) for x in r["month"].split("-"))
            rows.append((month_end(y, m), float(r["net_t"])))
    rows.sort()
    os.makedirs(os.path.dirname(OUT_REPO), exist_ok=True)
    with open(OUT_REPO, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "total_net_purchases_tonnes"])
        for d, v in rows:
            w.writerow([d.isoformat(), f"{v:g}"])
    print(f"wrote {len(rows)} rows -> {OUT_REPO}")
    print(f"date range: {rows[0][0]} .. {rows[-1][0]}")
    # also write into the local market-data tree if it exists
    md = os.path.join(ROOT, "market-data", "fundamentals")
    if os.path.isdir(os.path.join(ROOT, "market-data")):
        os.makedirs(md, exist_ok=True)
        import shutil
        shutil.copy(OUT_REPO, os.path.join(md, "central_bank_gold.csv"))
        print(f"installed -> {os.path.join(md, 'central_bank_gold.csv')}")


if __name__ == "__main__":
    main()
