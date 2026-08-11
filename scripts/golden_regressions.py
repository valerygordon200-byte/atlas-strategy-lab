#!/usr/bin/env python3
"""golden_regressions.py — T10: the golden regression suite.

The release blocker. Recomputed from the drive data every run:

  1. HOG AUGUST SHORT  (seasonal catalog)
       raw continuous  ~ -13.6%  (t ~ -7.5)   -> the phantom roll gap
       real capturable path (A+B) ~ 0.0% (|t| < 2)  -> NOT capturable
     Gate: raw mean < -5 (edge lived in the gap) AND |t_AplusB| < 2 (void).

  2. USDJPY NEWS DRIFT k=1  (the live strategy)
       holdout OOS t in [3.0, 4.5], OOS mean net > 0.
     Gate: 3.0 <= oos_t <= 4.5 AND oos_mean > 0.

  3. DUAL MOMENTUM  (Antonacci-style, 7-ETF universe)
       holdout (2018+) ~ +2.12%/mo, t ~ 4.51.
     Gate: ho_mean > +1.5 AND ho_t > 3.5.

Any gate failing => exit code 1 + a loud FAIL line. Runs in seconds
(no heavy permutations — those live in the full batteries).

Run:  python golden_regressions.py [--json reports/golden_regressions.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("E:/forex-data")
OUT = BASE / "reports"

LOCKED = {
    "hog_raw_mean": -13.6,     # % (phantom roll gap)
    "hog_raw_t": -7.5,
    "hog_real_t": -0.02,       # capturable path
    "drift_oos_t": 3.711,
    "dm_ho_mean": 2.12,        # %/mo
    "dm_ho_t": 4.51,
}


# --------------------------------------------------------------------------
# 1. Hog August — real capturable path vs phantom gap
# --------------------------------------------------------------------------

def check_hog() -> dict:
    sys.path.insert(0, str(BASE / "scripts"))
    import hog_august_check as hog

    hist, _hog_stats = hog.part1_history()
    rows = []
    for col, label in [("legA", "legA"), ("legB", "legB"),
                       ("AplusB", "real"), ("gap", "gap"), ("raw", "raw")]:
        s = hist[col]
        n = len(s)
        m = s.mean()
        t = m / s.std() * math.sqrt(n) if s.std() > 0 else np.nan
        rows.append({"series": label, "mean_pct": round(float(m), 2),
                     "t": round(float(t), 2), "n": n})
    real = next(r for r in rows if r["series"] == "real")
    raw = next(r for r in rows if r["series"] == "raw")
    ok = (raw["mean_pct"] < -5.0) and (abs(real["t"]) < 2.0)
    return {"name": "hog_august_short", "ok": ok, "detail": rows,
            "locked": {"raw_mean": LOCKED["hog_raw_mean"], "real_t": LOCKED["hog_real_t"]},
            "gate": "raw mean < -5 AND |real path t| < 2 (seasonal void, edge was the gap)"}


# --------------------------------------------------------------------------
# 2. USDJPY news drift k=1 (registry-based, identical to the engine service)
# --------------------------------------------------------------------------

def check_drift() -> dict:
    sys.path.insert(0, str(BASE / "scripts"))
    import data_registry as reg

    ev = reg.load("events", currency="USD", impact=("High", "Medium"), z_thr=0.5)
    px = reg.load("fx:USDJPY:d1")["Close"]
    r = px.pct_change()
    next_r = r.shift(-1).dropna()
    next_r.index = next_r.index.date
    ev["r"] = ev["date"].map(next_r)
    ev = ev.dropna(subset=["r"])
    cost = 1.0 * 0.01 / float(px.mean())
    net = 1.0 * ev["z"].apply(lambda z: 1 if z > 0 else -1) * ev["r"] - cost
    ism = ev["date"].astype(str) < "2022-01-01"
    is_n, oos_n = int(ism.sum()), int((~ism).sum())
    is_t = float(net[ism].mean() / (net[ism].std(ddof=1) / math.sqrt(is_n))) if is_n > 2 else np.nan
    oos_t = float(net[~ism].mean() / (net[~ism].std(ddof=1) / math.sqrt(oos_n))) if oos_n > 2 else np.nan
    oos_mean = float(net[~ism].mean())
    ok = (3.0 <= oos_t <= 4.5) and (oos_mean > 0)
    return {"name": "usdjpy_drift_k1", "ok": ok,
            "detail": {"n_is": is_n, "n_oos": oos_n, "is_t": round(is_t, 3),
                       "oos_t": round(oos_t, 3), "oos_mean_net": round(oos_mean, 6)},
            "locked": {"oos_t": LOCKED["drift_oos_t"]},
            "gate": "OOS t in [3.0, 4.5] AND OOS mean net > 0"}


# --------------------------------------------------------------------------
# 3. Dual momentum — holdout (2018+) stats
# --------------------------------------------------------------------------

def check_dual_momentum() -> dict:
    sys.path.insert(0, str(BASE / "scripts"))
    import dual_momentum_test as dm

    closes = {n: dm.load_close(n) for n in dm.UNIVERSE}
    mret = dm.monthly_returns(closes)
    dates, nets, turnover = dm.simulate(mret, dm.K_TOP)
    s = pd.Series(nets, index=pd.to_datetime(dates))
    oos = s[s.index > pd.Timestamp(dm.IS_END)]
    n = len(oos)
    mu = float(oos.mean())
    t = float(mu / oos.std() * math.sqrt(n)) if oos.std() > 0 and n > 2 else np.nan
    ok = (mu * 100 > 1.5) and (t > 3.5)
    return {"name": "dual_momentum", "ok": ok,
            "detail": {"n_holdout_months": n, "ho_mean_pct_mo": round(mu * 100, 2),
                       "ho_t": round(t, 2), "turnover_total": round(float(turnover), 2)},
            "locked": {"ho_mean": LOCKED["dm_ho_mean"], "ho_t": LOCKED["dm_ho_t"]},
            "gate": "holdout mean > +1.5%/mo AND t > 3.5"}


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(OUT / "golden_regressions.json"))
    ap.add_argument("--md", default=str(OUT / "golden_regressions.md"))
    args = ap.parse_args()

    t0 = time.time()
    checks = [check_hog(), check_drift(), check_dual_momentum()]
    dt = time.time() - t0
    all_ok = all(c["ok"] for c in checks)

    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "all_pass": all_ok, "runtime_s": round(dt, 1),
        "checks": checks,
    }
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = ["# Golden regression suite", "",
             f"Run: {report['generated']} · {dt:.1f}s · ALL PASS: {all_ok}", ""]
    for c in checks:
        flag = "PASS" if c["ok"] else "FAIL"
        lines.append(f"## [{flag}] {c['name']}")
        lines.append(f"- gate: {c['gate']}")
        lines.append(f"- detail: {json.dumps(c['detail'])}")
        lines.append(f"- locked reference: {json.dumps(c['locked'])}")
        lines.append("")
    Path(args.md).write_text("\n".join(lines), encoding="utf-8")

    for c in checks:
        flag = "PASS" if c["ok"] else "FAIL"
        print(f"[{flag}] {c['name']}: {c['detail']}")
    print(f"\n{'ALL GATES PASS' if all_ok else 'RELEASE BLOCKED — GATES FAILED'} "
          f"({dt:.1f}s) -> {args.json}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
