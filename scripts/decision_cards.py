#!/usr/bin/env python3
"""decision_cards.py — the user-facing feed per PRODUCT_DECISION.md.

Emits DECISION CARDS (signal → mechanism → data → p → outcome) as
`dourmouse/decision_cards.json` for the one-screen product UI.

Terminal states are first-class from day one (amendment +1/+2):
  FILLED | REJECTED_AT_GUARDRAIL | NO_TRADE (calm state) | PENDING_APPROVAL

Stdlib only. Two modes:
  --demo            emit a representative sample so the UI is never empty
  --check           validate the current JSON against the schema (exit != 0 on bad)

Real mode (later): read the engine's signals + ledger and render each as a card.
The schema is fixed now so the desktop's graveyard records and the engine's
outcome fields can conform before the pipeline is wired.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "dourmouse", "decision_cards.json")
# Real graveyard store: desktop P2 assembly under graveyard/ (index.json + data/*.json)
GRAVEYARD_INDEX = os.path.join(REPO, "graveyard", "index.json")

OUTCOMES = {"FILLED", "REJECTED_AT_GUARDRAIL", "NO_TRADE", "PENDING_APPROVAL"}
GUARDRAILS = {"max_loss_day", "position_cap", "kill_switch", "correlation_cap"}
REQUIRED = {"id", "ts", "signal", "asset", "direction", "size", "mechanism",
            "forced_participant", "data_refs", "p_value", "outcome", "guardrail",
            "ledger_ref", "chain"}


def _demo_cards() -> list[dict]:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return [
        {
            "id": "dc-demo-001", "ts": now,
            "signal": "usdjpy_drift_k1", "asset": "USDJPY", "direction": "LONG",
            "size": 0.1,
            "mechanism": "News-driven drift persists for ~4 sessions; the forced "
                         "participant is the market itself — it under-reacts to a genuine surprise.",
            "forced_participant": "none forced — informed under-reaction to a genuine surprise",
            "data_refs": ["USDJPY_D1", "event_bank_news"], "p_value": 0.0007,
            "outcome": "PENDING_APPROVAL", "guardrail": None, "ledger_ref": None,
            "chain": [
                "signal: drift detected on USDJPY (k=1)",
                "mechanism: under-reaction to a genuine surprise — the move continues ~4 sessions",
                "data: USDJPY_D1 + event bank — 210 sessions",
                "p: 0.0007 (permutation)",
                "outcome: awaiting your approval — HITL (verdict #5)",
            ],
        },
        {
            "id": "dc-demo-002", "ts": now,
            "signal": "dual_momentum_k1", "asset": "GC_FUT", "direction": "LONG",
            "size": 0.05,
            "mechanism": "Trend-following leg; forced participant is the late "
                         "chaser entering on confirmation day.",
            "forced_participant": "late chaser entering on confirmation",
            "data_refs": ["GC_D1"], "p_value": 0.021,
            "outcome": "REJECTED_AT_GUARDRAIL", "guardrail": "position_cap",
            "ledger_ref": None,
            "chain": [
                "signal: dual momentum positive on GC",
                "mechanism: late chasers pay the spread on confirmation day",
                "data: GC_D1 — 1,400 sessions",
                "p: 0.021",
                "outcome: REJECTED AT GUARDRAIL position_cap (exposure already at cap)",
            ],
        },
        {
            "id": "dc-demo-003", "ts": now,
            "signal": "central_bank_net_buying", "asset": "GOLD", "direction": "HOLD",
            "size": 0.0,
            "mechanism": "Central-bank net buying is positive (beta +0.144) but "
                         "the OOS window is too short to trust a new entry today.",
            "forced_participant": "n/a — informational factor, not a trade trigger",
            "data_refs": ["central_bank_gold"], "p_value": 1.08,
            "outcome": "NO_TRADE", "guardrail": None, "ledger_ref": None,
            "chain": [
                "signal: CB net buying positive this month",
                "mechanism: CBs buying -> gold up (calibrated beta +0.144)",
                "data: WGC monthly series, 55 obs (Nov-2020..Jun-2026)",
                "p: 1.08 — NOT significant; OOS window too short",
                "outcome: DO NOTHING TODAY — here's why: the factor's sign is "
                "right but the evidence isn't strong enough for a trade yet.",
            ],
        },
    ]


def _check(cards: list[dict]) -> list[str]:
    errs: list[str] = []
    for c in cards:
        missing = [k for k in REQUIRED if k not in c]
        if missing:
            errs.append(f"{c.get('id', '?')}: missing {missing}")
        if c.get("outcome") not in OUTCOMES:
            errs.append(f"{c.get('id', '?')}: bad outcome {c.get('outcome')}")
        if c["outcome"] == "REJECTED_AT_GUARDRAIL" and c.get("guardrail") not in GUARDRAILS:
            errs.append(f"{c.get('id', '?')}: guardrail-rejected card without a "
                        f"valid guardrail name")
        if c["outcome"] == "NO_TRADE" and not any(
                s.startswith("outcome: DO NOTHING TODAY") for s in c.get("chain", [])):
            errs.append(f"{c.get('id', '?')}: NO_TRADE card must carry the calm-state line")
    return errs


def graveyard_count() -> int:
    """Real killed-strategy count from the P2 index (0 if not assembled yet)."""
    try:
        with open(GRAVEYARD_INDEX, encoding="utf-8") as f:
            return int(json.load(f).get("count", 0))
    except Exception:  # noqa: BLE001
        return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true", help="emit demo cards")
    ap.add_argument("--check", action="store_true", help="validate existing JSON")
    args = ap.parse_args()

    if args.check:
        with open(OUT, encoding="utf-8") as f:
            cards = json.load(f)["cards"]
        errs = _check(cards)
        if errs:
            print("\n".join(errs))
            sys.exit(1)
        print(f"[check] OK — {len(cards)} cards, schema conformant")
        return

    cards = _demo_cards() if args.demo else _demo_cards()  # real mode wires later
    errs = _check(cards)
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "mode": "demo" if args.demo else "default-demo",
                   "graveyard": {"count": graveyard_count()},
                   "cards": cards}, f, indent=2)
    print(f"[cards] {len(cards)} written to {OUT}")


if __name__ == "__main__":
    main()
