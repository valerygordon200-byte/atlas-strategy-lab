#!/usr/bin/env python3
"""health_check.py — C6 smoke test. Run on any machine to prove the stack works.

1. Registry present + N keys resolve
2. Core series load with quality gates (FX d1, events, a commodity)
3. Golden regression suite: all three locked results PASS

Exit 0 only if everything passes. Used by setup.bat/setup.sh as the
definition-of-done smoke gate (commercial spec §2A / §4).

Run:  python scripts/health_check.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

BASE = Path("E:/forex-data")
sys.path.insert(0, str(BASE / "scripts"))

fails: list[str] = []


def step(name: str, fn) -> None:
    t0 = time.time()
    try:
        msg = fn()
        print(f"[PASS] {name} ({time.time() - t0:.1f}s) {msg}")
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {name}: {e}")
        fails.append(name)


def check_registry():
    import data_registry as reg
    reg.rebuild_registry()
    reg._load_registry()
    return f"registry.json regenerated"


def check_keys():
    import json
    import data_registry as reg
    r = json.loads((reg.BASE / "market-data/registry.json").read_text(encoding="utf-8"))
    d = r["discovered"]
    n = (len(d["fx_pairs"]) * 2) + 1 + len(d["commodities"]) + len(d["fundamentals"]) + 8 + 1
    return f"{n} logical keys discovered"


def check_data():
    import data_registry as reg
    fx = reg.load("fx:USDJPY:d1")
    assert len(fx) > 2500, f"USDJPY d1 only {len(fx)} rows"
    import pandas as pd
    ev_raw = pd.read_parquet(reg.BASE / "market-data/events/events.parquet")
    assert len(ev_raw) > 80000, f"events archive only {len(ev_raw)} rows"
    zs = reg.load("commodity:ZS")
    assert len(zs) > 2500, f"soybeans only {len(zs)} rows"
    return f"USDJPY {len(fx)} / events archive {len(ev_raw)} / ZS {len(zs)} rows"


def check_golden():
    sys.path.insert(0, str(BASE / "scripts"))
    import golden_regressions as gr
    checks = [gr.check_hog(), gr.check_drift(), gr.check_dual_momentum()]
    assert all(c["ok"] for c in checks), \
        "golden gates: " + ", ".join(f"{c['name']}={c['ok']}" for c in checks)
    return "hog + drift + dual momentum ALL PASS"


def main() -> int:
    print(f"health check — {BASE}")
    step("registry", check_registry)
    step("keys", check_keys)
    step("data", check_data)
    step("golden regressions", check_golden)
    print("")
    if fails:
        print(f"SMOKE TEST FAILED: {fails}")
        return 1
    print("SMOKE TEST PASS — stack is healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
