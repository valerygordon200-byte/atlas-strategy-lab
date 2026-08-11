#!/usr/bin/env python3
"""lockup_refetch_adj.py — re-fetch IPO prices with Yahoo adjusted closes.

The first build saved raw `close`, which is contaminated by stock splits
(2020-25 IPO names split frequently; a raw series shows a fake -90% crash on
split day). This refetches every symbol that already has a CSV and overwrites
it with date,close,adjclose. Resumable: files that already contain an
adjclose column are skipped, so rerunning just continues where it left off.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path("E:/forex-data")
IPODIR = BASE / "market-data/ipos"
PRICEDIR = IPODIR / "ipo_prices"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}
# Windows device names (CON.csv opens the console device and hangs on read)
WIN_RESERVED = {"con", "prn", "aux", "nul", "clock$"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}


def fetch_adjclose(sym):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(sym)}?interval=1d&range=max")
    req = urllib.request.Request(url, headers=HDR)
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    r = d["chart"]["result"][0]
    ts = r["timestamp"]
    q = r["indicators"]["quote"][0]["close"]
    adj = r["indicators"]["adjclose"][0]["adjclose"]
    lines = []
    for t, c, a in zip(ts, q, adj):
        if c is None or c <= 0 or a is None or a <= 0:
            continue
        lines.append(f"{time.strftime('%Y-%m-%d', time.gmtime(t))},{c:.6f},{a:.6f}")
    return lines


uniq = json.load(open(IPODIR / "ipo_list.json"))
todo = [r["symbol"] for r in uniq if r["symbol"].lower() not in WIN_RESERVED
        and (PRICEDIR / f"{r['symbol']}.csv").exists()]
print(f"candidates with CSVs: {len(todo)}")

ok, skip, fail = 0, 0, 0
fails = []
for i, sym in enumerate(todo):
    p = PRICEDIR / f"{sym}.csv"
    # resumable: skip files that already have adjclose
    try:
        head = p.read_text(encoding="utf-8", errors="ignore")[:200]
    except Exception:
        head = ""
    if "adjclose" in head:
        skip += 1
        continue
    try:
        lines = fetch_adjclose(sym)
        if len(lines) < 30:
            fails.append((sym, f"<30 bars ({len(lines)})"))
            fail += 1
            continue
        p.write_text("date,close,adjclose\n" + "\n".join(lines) + "\n")
        ok += 1
    except Exception as e:
        fails.append((sym, str(e)[:60]))
        fail += 1
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(todo)} (ok={ok} skip={skip} fail={fail})")
    time.sleep(0.12)

print(f"\ndone: ok={ok} skip={skip} fail={fail}")
print("failures sample:", fails[:15])
