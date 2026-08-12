#!/usr/bin/env python3
"""model_benchmark.py — Phase 1.2 model benchmark harness (laptop side).

Runs a held-out sample of REAL dourmouse tasks (training_data/instruction_pairs.jsonl)
through each Ollama model with the PRODUCTION dispatch system prompt
(dourmouse.dispatch.system_message), measuring the "reliability gap" the
scaling plan's Phase 1.2 cares about:

  Part A — structured-output obedience: 5 tasks under a strict "output ONLY
           valid JSON" system prompt (the pattern atlas_lab uses). Metric:
           valid-JSON rate.
  Part B — open tasks under the real dispatch prompt: refusal rate, latency,
           token use, and keyword coverage of the reference assistant answer
           (deterministic overlap proxy for quality — documented as a proxy).

Honest limits (stated in the report): keyword coverage is a weak proxy for
quality; dourmouse-finetuned may be in-sample on these pairs (trained from
the same corpus) — treat its numbers as an upper bound.

Usage:
  python3 scripts/model_benchmark.py \
      --pairs /Volumes/ATLAS\ /Atlas/dourmouse-4.0.0/training_data/instruction_pairs.jsonl \
      --system-prompt /tmp/dourmouse_system_prompt.txt \
      --models dourmouse-finetuned --n 8 --out reports/MODEL_BENCHMARK.md
"""
import argparse
import json
import random
import re
import time
import urllib.request
import datetime

OLLAMA = "http://127.0.0.1:11434"

STRICT_JSON_SYSTEM = (
    "You are a deterministic formatter. Given a request, you output a single "
    "JSON object with exactly these keys: {\"plan\": [string steps], "
    "\"risks\": [strings], \"done\": true|false}. Output ONLY the JSON object — "
    "no markdown fences, no prose before or after it."
)

REFUSE = re.compile(
    r"\b(sorry|i cannot|i can't|cannot assist|i'm unable|i am unable|"
    r"refus(e|ed|ing)|not able to)\b", re.I)
STOPWORDS = set(
    "the a an and or but if then of to in on for with as is are was were be been "
    "it its this that these those you your i me my we our they them do does did "
    "have has had will would can could should may might not no yes ok okay "
    "please thank thanks just want need use make get go going like about from "
    "into out up down over under at by so also there here what which who whom "
    "when where how why all any each every both few more most other some such "
    "only own same very s t d ll m re ve don't can't won't".split())


def _chat(model: str, system: str, user: str, num_predict: int = 1200):
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
                      *re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", content, re.S)):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def _coverage(content: str, reference: str) -> float:
    """Fraction of significant reference words present in the output (proxy)."""
    ref_words = {w for w in re.findall(r"[a-z0-9']+", reference.lower())
                 if w not in STOPWORDS and len(w) > 2}
    out_words = set(re.findall(r"[a-z0-9']+", content.lower()))
    if not ref_words:
        return 0.0
    return round(len(ref_words & out_words) / len(ref_words), 3)


def run_model(model: str, system: str, strict_tasks: list, tasks: list) -> dict:
    rows = []
    # Part A: strict JSON
    for i, task in enumerate(strict_tasks):
        try:
            content, lat, toks = _chat(model, STRICT_JSON_SYSTEM, task, num_predict=500)
            ok = _parse_json(content) is not None
            rows.append({"part": "A", "i": i, "task": task[:70], "ok": ok,
                         "refusal": bool(REFUSE.search(content)),
                         "lat": round(lat, 1), "tokens": toks,
                         "preview": content[:100].replace("\n", " ")})
            print(f"[{model}] A{i+1} ok={ok} lat={lat:.1f}s", flush=True)
        except Exception as e:
            rows.append({"part": "A", "i": i, "task": task[:70], "ok": False,
                         "refusal": False, "lat": None, "tokens": 0,
                         "preview": f"ERROR {e}"})
            print(f"[{model}] A{i+1} ERROR {e}", flush=True)
    # Part B: real tasks, production prompt
    for i, rec in enumerate(tasks):
        try:
            content, lat, toks = _chat(model, system, rec["user"], num_predict=800)
            rows.append({"part": "B", "i": i, "task": rec["user"][:70],
                         "domain": rec.get("domain", "?"), "ok": None,
                         "refusal": bool(REFUSE.search(content)),
                         "cov": _coverage(content, rec.get("assistant", "")),
                         "lat": round(lat, 1), "tokens": toks,
                         "preview": content[:100].replace("\n", " ")})
            print(f"[{model}] B{i+1} ref={rows[-1]['refusal']} cov={rows[-1]['cov']} lat={lat:.1f}s", flush=True)
        except Exception as e:
            rows.append({"part": "B", "i": i, "task": rec["user"][:70],
                         "domain": rec.get("domain", "?"), "ok": None,
                         "refusal": False, "cov": 0.0, "lat": None, "tokens": 0,
                         "preview": f"ERROR {e}"})
            print(f"[{model}] B{i+1} ERROR {e}", flush=True)
    print(f"[DONE {model}] rows={len(rows)}", flush=True)
    return {"model": model, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--system-prompt", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="reports/MODEL_BENCHMARK.md")
    args = ap.parse_args()

    recs = [json.loads(l) for l in open(args.pairs, encoding="utf-8") if l.strip()]
    rng = random.Random(args.seed)
    sample = rng.sample(recs, min(args.n, len(recs)))
    system = open(args.system_prompt, encoding="utf-8").read()
    strict_tasks = [
        "Summarize the risk of holding a leveraged FX position overnight in JSON.",
        "List the three steps to run a backtest on usdjpy_drift_k1 in JSON.",
        "What guardrails should a paper-trading loop enforce? Answer in JSON.",
        "Propose a weekly routine for maintaining a strategy lab in JSON.",
        "Explain what NOT CONFIGURED means for a tool result in JSON.",
    ]
    results = [run_model(m, system, strict_tasks, sample) for m in
               [x.strip() for x in args.models.split(",")]]

    lines = [
        "# MODEL BENCHMARK — Phase 1.2 (laptop side)",
        "",
        f"Date: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M UTC}",
        f"Harness: `scripts/model_benchmark.py` · Part B tasks: {len(sample)} sampled "
        f"(seed {args.seed}) from `training_data/instruction_pairs.jsonl` (domain split: "
        + ", ".join(f"{d}={sum(1 for r in sample if r.get('domain') == d)}"
                    for d in sorted({r.get('domain', '?') for r in sample})) + ")",
        f"System prompt: production `dourmouse.dispatch.system_message(registry)` · Ollama {OLLAMA}",
        "Part A = strict-JSON obedience (5 fixed tasks); Part B = open answers on real tasks.",
        "",
        "> Honest limits: keyword coverage is a weak quality proxy; `dourmouse-finetuned` "
        "may be in-sample on these pairs (same corpus) — treat its numbers as an upper bound.",
        "",
        "## Summary",
        "",
        "| model | A valid-JSON | B refusal | B avg coverage | B avg latency (s) | B avg tokens |",
        "|---|---|---|---|---|---|",
    ]
    for res in results:
        a = [r for r in res["rows"] if r["part"] == "A"]
        b = [r for r in res["rows"] if r["part"] == "B"]
        a_ok = sum(1 for r in a if r["ok"]) / len(a) if a else 0
        b_ref = sum(1 for r in b if r["refusal"]) / len(b) if b else 0
        b_cov = sum(r["cov"] for r in b) / len(b) if b else 0
        b_lat = [r["lat"] for r in b if r["lat"]]
        b_tok = [r["tokens"] for r in b if r["tokens"]]
        lines.append(f"| {res['model']} | {a_ok:.0%} | {b_ref:.0%} | {b_cov:.2f} | "
                     f"{round(sum(b_lat)/len(b_lat),1) if b_lat else '-'} | "
                     f"{round(sum(b_tok)/len(b_tok)) if b_tok else '-'} |")
    lines += ["", "## Per-task detail"]
    for res in results:
        lines += [f"### {res['model']}", ""]
        for r in res["rows"]:
            extra = (f"ok={r['ok']}" if r["part"] == "A"
                     else f"ref={r['refusal']} cov={r['cov']}")
            lines.append(f"- **{r['part']}{r['i']}** [{r.get('domain','-')}] {extra} "
                         f"lat={r['lat']}s tok={r['tokens']} — {r['task']}")
            lines.append(f"  > {r['preview']}")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote {args.out}")

    for res in results:
        b = [r for r in res["rows"] if r["part"] == "B"]
        lat = [r["lat"] for r in b if r["lat"]]
        print(json.dumps({
            "model": res["model"],
            "A_json_ok": sum(1 for r in res["rows"] if r["part"] == "A" and r["ok"]),
            "B_refusals": sum(1 for r in b if r["refusal"]),
            "B_avg_cov": round(sum(r["cov"] for r in b) / len(b), 3),
            "B_avg_lat": round(sum(lat) / len(lat), 1) if lat else None,
        }))


if __name__ == "__main__":
    main()
