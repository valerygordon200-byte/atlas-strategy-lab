#!/usr/bin/env python3
"""graveyard/gen_page.py — P2 tail: generate the searchable graveyard page.

Reads graveyard/index.json + graveyard/data/*.json and emits
dourmouse/ui/graveyard.html (Jarvis design language, same as product.html)
with the entries embedded — searchable by text, filterable by family and
status, every field visible, no server needed.

Run:  python graveyard/gen_page.py [--out <path>]
"""
from __future__ import annotations

import argparse
import html as H
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GY = os.path.join(ROOT, "graveyard")
DATA = os.path.join(GY, "data")
DEFAULT_OUT = os.path.join(ROOT, "dourmouse", "ui", "graveyard.html")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DOURMOUSE // GRAVEYARD</title>
<style>
  :root {
    --ground: #0B0E14; --surface: #12151E; --surface2: #161B27;
    --cyan: #4FC3F7; --cyan-rgb: 79,195,247;
    --amber: #F5A623; --red: #EF5350; --gold: #FFD232; --dead: #8A929E;
    --a06: 0.06; --a10: 0.10; --a16: 0.16; --a22: 0.22; --a45: 0.45; --a85: 0.85;
    --font-display: "Exo 2","Avenir Next","Helvetica Neue",Arial,sans-serif;
    --font-mono: "JetBrains Mono","SF Mono",Menlo,Consolas,monospace;
    --font-wordmark: "Orbitron","Exo 2","Avenir Next",sans-serif;
    --text: rgba(var(--cyan-rgb), var(--a85));
    --text-dim: rgba(var(--cyan-rgb), var(--a45));
    --line: rgba(var(--cyan-rgb), var(--a10));
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--ground); color: var(--text); font-family: var(--font-mono);
         min-height: 100vh; display: flex; flex-direction: column; }
  header { display: flex; align-items: center; gap: 16px; padding: 10px 18px;
           border-bottom: 1px solid var(--line); background: var(--surface); }
  .wordmark { font-family: var(--font-wordmark); font-size: 15px; letter-spacing: 3px; color: var(--gold); }
  .wordmark span { color: var(--cyan); }
  .tag { font-size: 10px; letter-spacing: 2px; color: var(--amber);
         border: 1px solid rgba(245,166,35,.4); padding: 2px 8px; }
  .spacer { flex: 1; }
  .count { font-size: 20px; color: var(--red); font-family: var(--font-display); }
  main { flex: 1; max-width: 1080px; width: 100%; margin: 0 auto; padding: 20px 18px 40px; }
  .controls { display: flex; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
  input, select { background: var(--surface2); color: var(--text); border: 1px solid var(--line);
                  font-family: var(--font-mono); font-size: 12px; padding: 8px 12px; }
  input { flex: 1; min-width: 240px; }
  select { min-width: 180px; }
  .hint { font-size: 10px; color: var(--text-dim); letter-spacing: 1px; margin-bottom: 16px; }
  .entry { background: var(--surface); border: 1px solid var(--line); margin-bottom: 14px; cursor: pointer; }
  .entry:hover { border-color: rgba(var(--cyan-rgb), var(--a45)); }
  .e-h { display: flex; align-items: center; gap: 12px; padding: 12px 14px; flex-wrap: wrap; }
  .e-name { font-family: var(--font-display); font-size: 13px; color: var(--text); }
  .e-fam { font-size: 9px; letter-spacing: 2px; color: var(--amber); border: 1px solid rgba(245,166,35,.3);
           padding: 2px 8px; white-space: nowrap; }
  .e-status { font-size: 9px; letter-spacing: 2px; color: var(--red); border: 1px solid rgba(239,83,80,.5);
              padding: 2px 8px; white-space: nowrap; }
  .e-date { font-size: 10px; color: var(--text-dim); margin-left: auto; white-space: nowrap; }
  .e-head { width: 100%; font-size: 11px; color: var(--dead); padding: 0 14px 10px; }
  .e-body { display: none; padding: 0 14px 14px; border-top: 1px solid var(--line); font-size: 11px; }
  .entry.open .e-body { display: block; }
  .e-body h4 { font-size: 9px; letter-spacing: 2px; color: var(--amber); margin: 12px 0 4px; }
  .e-body p { color: var(--text-dim); line-height: 1.55; }
  .e-body li { margin-left: 18px; color: var(--text-dim); }
  .e-src { font-size: 10px; color: var(--dead); margin-top: 10px; word-break: break-all; }
  .none { color: var(--dead); font-size: 12px; padding: 20px; text-align: center; }
  footer { padding: 14px 18px; border-top: 1px solid var(--line); font-size: 10px;
           color: var(--text-dim); letter-spacing: 1px; }
  a { color: var(--cyan); text-decoration: none; } a:hover { text-decoration: underline; }
</style>
</head>
<body>
<header>
  <div class="wordmark">DOURMOUSE<span>//</span>GRAVEYARD</div>
  <div class="tag">THE DEAD</div>
  <div class="spacer"></div>
  <span class="count" id="count">__COUNT__</span>
  <span style="font-size:10px;color:var(--text-dim)">killed strategies · every one with its post-mortem</span>
</header>
<main>
  <div class="controls">
    <input id="q" placeholder="search: name, family, mechanism, post-mortem, asset…" oninput="apply()">
    <select id="fam" onchange="apply()"><option value="">ALL FAMILIES</option>__FAMOPT__</select>
  </div>
  <div class="hint">__HINT__</div>
  <div id="list"></div>
</main>
<footer>VERDICT: A (THE LAB) · WE DON'T SELL PICKS, WE SELL THE RECEIPTS · <a href="product.html">back to the product</a></footer>
<script>
const DATA = __DATA__;
const famSel = document.getElementById("fam");
DATA.families.forEach(f => { const o = document.createElement("option"); o.value = f; o.textContent = f; famSel.appendChild(o); });

function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function rows(e){
  const body = e.tests_run && e.tests_run.length
    ? `<h4>TESTS RUN</h4><ul>${e.tests_run.map(t=>`<li>${esc(t)}</li>`).join("")}</ul>` : "";
  return `<div class="e-body">
    <h4>HYPOTHESIS</h4><p>${esc(e.mechanism_claim)}</p>
    <h4>FORCED PARTICIPANT</h4><p>${esc(e.forced_participant)}</p>
    <h4>DATA</h4><p>${esc(e.data)}</p>
    ${body}
    <h4>KILL CRITERION</h4><p style="color:var(--red)">${esc(e.kill_criterion)}</p>
    <h4>POST-MORTEM</h4><p>${esc(e.post_mortem)}</p>
    <div class="e-src">source: ${esc(e.source)}</div>
  </div>`;
}
function apply(){
  const q = document.getElementById("q").value.toLowerCase();
  const fam = document.getElementById("fam").value;
  const list = document.getElementById("list");
  const hits = DATA.entries.filter(e => {
    if (fam && e.family !== fam) return false;
    if (!q) return true;
    const hay = [e.name, e.family, e.mechanism_claim, e.forced_participant,
                 e.data, e.post_mortem, e.kill_criterion, e.headline].join(" ").toLowerCase();
    return hay.includes(q);
  });
  document.getElementById("count").textContent = hits.length;
  list.innerHTML = hits.length ? "" : '<div class="none">nothing here — that is the point. (try a different filter)</div>';
  hits.forEach(e => {
    const el = document.createElement("div");
    el.className = "entry";
    el.innerHTML = `<div class="e-h">
        <span class="e-name">${esc(e.name)}</span>
        <span class="e-fam">${esc(e.family)}</span>
        <span class="e-status">${esc(e.status)}</span>
        <span class="e-date">killed ${esc(e.killed_date)}</span>
        <div class="e-head">${esc(e.headline)}</div>
      </div>${rows(e)}`;
    el.addEventListener("click", () => el.classList.toggle("open"));
    list.appendChild(el);
  });
}
apply();
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    index = json.load(open(os.path.join(GY, "index.json"), encoding="utf-8"))
    entries = []
    for e in index["entries"]:
        with open(os.path.join(DATA, f"{e['id']}.json"), encoding="utf-8") as f:
            entries.append(json.load(f))
    data = {
        "count": len(entries),
        "families": index["families"],
        "entries": entries,
    }
    fam_opt = "".join(f'<option value="{H.escape(f)}">{H.escape(f)}</option>'
                      for f in index["families"])
    hint = (f"{len(entries)} killed strategies across {len(index['families'])} mechanism "
            f"families — every number sourced, every post-mortem honest. Click any entry "
            f"for the full record. Nothing here is 'fixed' — it's evidence.")
    out = (PAGE.replace("__COUNT__", str(len(entries)))
               .replace("__FAMOPT__", fam_opt)
               .replace("__HINT__", hint)
               .replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote {len(entries)} entries -> {args.out}")


if __name__ == "__main__":
    main()
