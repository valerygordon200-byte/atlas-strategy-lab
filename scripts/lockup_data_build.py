#!/usr/bin/env python3
"""lockup_data_build.py — assemble the IPO universe + prices for the lockup test.

Step 1: scrape per-year US IPO lists from stockanalysis.com (2020-2025):
        date, symbol, company, IPO price (parse the svelte-rendered table rows).
Step 2: fetch daily closes for every symbol from the Yahoo chart API
        (range=max so prices cover the full post-IPO life).
Output:
  market-data/ipos/ipo_list.json         (year, date, symbol, company, ipo_price)
  market-data/ipos/ipo_prices/          (one CSV per symbol: date, close)
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path("E:/forex-data")
IPODIR = BASE / "market-data/ipos"
PRICEDIR = IPODIR / "ipo_prices"
PRICEDIR.mkdir(parents=True, exist_ok=True)

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

def fetch(url):
    req = urllib.request.Request(url, headers=HDR)
    return urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "ignore")

def cells(row):
    out = []
    for td in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S):
        out.append(re.sub(r"<[^>]+>", "", td).strip())
    return out

out = []
for y in YEARS:
    try:
        html = fetch(f"https://stockanalysis.com/ipos/{y}/")
    except Exception as e:
        print(f"  {y}: fetch failed: {e}")
        continue
    rows = re.findall(r'<tr class="svelte-1rlg0my">(.*?)</tr>', html, re.S)
    n = 0
    for r in rows:
        c = cells(r)
        if len(c) < 4 or not re.match(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", c[0]):
            continue
        out.append({"year": y, "date": c[0], "symbol": c[1],
                    "company": c[2], "ipo_price": c[3]})
        n += 1
    print(f"  {y}: {n} rows parsed")

# dedupe by (date, symbol)
seen, uniq = set(), []
for rec in out:
    key = (rec["date"], rec["symbol"])
    if key in seen:
        continue
    seen.add(key)
    uniq.append(rec)

print(f"total unique IPOs: {len(uniq)}")
with open(IPODIR / "ipo_list.json", "w") as f:
    json.dump(uniq, f, indent=1)

# ---- step 2: prices ----
def yahoo_close(sym):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(sym)}?interval=1d&range=max")
    req = urllib.request.Request(url, headers=HDR)
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    r = d["chart"]["result"][0]
    ts = r["timestamp"]
    close = r["indicators"]["quote"][0]["close"]
    lines = []
    for t, c in zip(ts, close):
        if c is None or c <= 0:
            continue
        lines.append(f"{time.strftime('%Y-%m-%d', time.gmtime(t))},{c:.6f}")
    return lines

ok, fail = 0, 0
fails = []
for i, rec in enumerate(uniq):
    sym = rec["symbol"]
    p = PRICEDIR / f"{sym}.csv"
    if p.exists():
        ok += 1
        continue
    try:
        lines = yahoo_close(sym)
        if len(lines) < 30:
            fails.append((sym, f"<30 bars ({len(lines)})"))
            fail += 1
            continue
        p.write_text("date,close\n" + "\n".join(lines) + "\n")
        ok += 1
    except Exception as e:
        fails.append((sym, str(e)[:60]))
        fail += 1
    if (i + 1) % 100 == 0:
        print(f"  fetched {i+1}/{len(uniq)} (ok={ok} fail={fail})")
    time.sleep(0.12)

print(f"\ndone: ok={ok} fail={fail}")
print("failures sample:", fails[:25])
with open(IPODIR / "price_failures.json", "w") as f:
    json.dump(fails, f, indent=1)
