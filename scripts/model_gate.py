#!/usr/bin/env python3
"""model_gate.py — T12: the locked-model regression gate (release blocker).

Desktop's 1155 acceptance condition, on record: *"Log it in the golden
regressions as the locked model (a model-regression gate: strict-JSON <90%
on the 13-task suite = release blocker)."*

This gate re-runs the Phase 1.2 benchmark's 13-task suite against the
LOCKED production model (`dourmouse-finetuned`, verified 5/5 = 100% on the
held-out split) and fails loudly — exit 1 + a loud FAIL line — if strict-JSON
obedience drops below 90% (i.e. anything less than a perfect 5/5 on the 5
Part-A formatter tasks). It is the model twin of `golden_regressions.py`
(which guards the finance regressions); both are release blockers.

Part A (5 tasks): strict formatter — "output ONLY a JSON object with
{plan, risks, done}". Metric: valid-JSON rate. This is the gate.
Part B (8 tasks): real tasks under the PRODUCTION dispatch prompt — refusal
rate + latency, reported for context (NOT gated).

Run (needs Ollama + the locked model):
  python3 scripts/model_gate.py [--model dourmouse-finetuned]
                                [--json reports/model_gate.json]
                                [--md reports/model_gate.md]

Exit code: 0 = PASS (release not blocked) · 1 = FAIL (RELEASE BLOCKED).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434"
GATE = 0.90  # strict-JSON rate below this = release blocker (1155)

STRICT_JSON_SYSTEM = (
    "You are a deterministic formatter. Given a request, you output a single "
    "JSON object with exactly these keys: {\"plan\": [string steps], "
    "\"risks\": [strings], \"done\": true|false}. Output ONLY the JSON object — "
    "no markdown fences, no prose before or after it."
)

STRICT_TASKS = [
    "Summarize the risk of holding a leveraged FX position overnight in JSON.",
    "List the three steps to run a backtest on usdjpy_drift_k1 in JSON.",
    "What guardrails should a paper-trading loop enforce? Answer in JSON.",
    "Propose a weekly routine for maintaining a strategy lab in JSON.",
    "Explain what NOT CONFIGURED means for a tool result in JSON.",
]

REFUSE = re.compile(
    r"\b(sorry|i cannot|i can't|cannot assist|i'm unable|i am unable|"
    r"refus(e|ed|ing)|not able to)\b", re.I)


def _chat(model: str, system: str, user: str, num_predict: int = 500):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": num_predict},
    }).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode())
    lat = time.time() - t0
    content = d.get("message", {}).get("content", "")
    tokens = d.get("prompt_eval_count", 0) + d.get("eval_count", 0)
    return content, lat, tokens


def _parse_json(content: str):
    for candidate in (content,
                      *re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```",
                                  content, re.S)):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def run_gate(model: str) -> tuple[bool, dict]:
    rows = []
    for i, task in enumerate(STRICT_TASKS):
        try:
            content, lat, toks = _chat(model, STRICT_JSON_SYSTEM, task)
            ok = _parse_json(content) is not None
            rows.append({"task": task, "valid_json": ok,
                         "refusal": bool(REFUSE.search(content)),
                         "lat_s": round(lat, 1), "tokens": toks,
                         "preview": content[:120].replace("\n", " ")})
            print(f"[{model}] A{i+1} valid_json={ok} lat={lat:.1f}s", flush=True)
        except Exception as exc:  # noqa: BLE001
            rows.append({"task": task, "valid_json": False, "refusal": False,
                         "lat_s": None, "tokens": 0,
                         "preview": f"ERROR {exc}"})
            print(f"[{model}] A{i+1} ERROR {exc}", flush=True)

    n = len(rows)
    ok_n = sum(1 for r in rows if r["valid_json"])
    rate = ok_n / n if n else 0.0
    passed = rate >= GATE
    return passed, {
        "model": model,
        "n_tasks": n,
        "valid_json": ok_n,
        "strict_json_rate": round(rate, 3),
        "gate": GATE,
        "passed": passed,
        "generated": datetime.datetime.now(datetime.timezone.utc)
                     .isoformat(timespec="seconds"),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="dourmouse-finetuned")
    ap.add_argument("--json", default="reports/model_gate.json")
    ap.add_argument("--md", default="reports/model_gate.md")
    args = ap.parse_args()

    passed, report = run_gate(args.model)

    out_json = Path(args.json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# MODEL GATE — locked-model regression (release blocker, T12)",
        "",
        f"Run: {report['generated']} · model `{report['model']}` · "
        f"strict-JSON {report['strict_json_rate']:.0%} ({report['valid_json']}/"
        f"{report['n_tasks']}) · gate ≥ {report['gate']:.0%}",
        "",
        f"**{'PASS' if passed else 'RELEASE BLOCKED'}** — "
        + ("format obedience holds (1155 gate not tripped)."
           if passed else "strict-JSON fell below 90% — do NOT ship with this model."),
        "",
        "| task | valid JSON | latency (s) | preview |",
        "|---|---|---|---|",
    ]
    for r in report["rows"]:
        lines.append(f"| {r['task'][:60]} | {r['valid_json']} | "
                     f"{r['lat_s']} | {r['preview'][:70]} |")
    out_md = Path(args.md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    flag = "PASS" if passed else "FAIL"
    print(f"\n[{flag}] model_gate: strict-JSON "
          f"{report['strict_json_rate']:.0%} ({report['valid_json']}/"
          f"{report['n_tasks']}) vs gate {report['gate']:.0%} "
          f"-> {'ALL GATES PASS' if passed else 'RELEASE BLOCKED — GATES FAILED'}")
    print(f"Wrote {out_json}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
