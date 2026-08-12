# AUDIT — Phase 1.1 (laptop side, live Mac system)

**Date:** 2026-08-12 · **Owner:** laptop-dourmouse (ME harness = desktop, per scaling plan 1.1 — no harness delivered yet, so this is the laptop's v1 with real, verifiable checks) · **Scope:** the live dourmouse system running on this Mac (PID 36973, `dourmouse.webui` on 8765, Ollama backend `dourmouse-finetuned`).

**Method:** direct HTTP checks against the live server (loopback + Tailscale IP), file inspection, log review, and the test suite. Every claim below is backed by a command run on 2026-08-12.

---

## Summary

| Area | Verdict | Evidence |
|---|---|---|
| Backend | ✅ PASS | 7/7 endpoints 200, <10 ms (telemetry 108 ms) |
| Auth gate | ✅ PASS | non-loopback no-token → 302 (login); with-token → 200, verified via Tailscale IP |
| Memory store | ✅ PASS | 2,757 facts live via `/api/memory` (learn loop active) |
| Roster | ⚠️ PASS w/ drift | 23 subagents live; DESKTOP_DESIGN_PORTFOLIO.md claims 26 |
| Frontend | ✅ PASS | all pages served; zero external network refs; 5 responsive breakpoints |
| SSE | ✅ PASS | `/api/events` streams real events |
| Tests | ✅ PASS w/ caveat | 97/97 fast subset (webui/multi_device/guardrails) 25.5 s; full suite 991/1035 (95.7%) per plan — 44 Windows-only failures |
| Performance | ⚠️ CONFIRMED RISK | endpoint latency fine; LLM turns 3–223 s (thermal ceiling — see MODEL_BENCHMARK.md) |
| Reliability | ✅ PASS w/ notes | server up 1h05m at check; daemons (bridge 39413 / feed 39414) up; 2 log error lines (stale launch) |
| Security | ❌ **FAIL** | **dist/ ships the memory DB (contains secret-like strings) + 130+ session audit files; 8.4 GB artifact** |
| End-to-end | ✅ PASS (lite) | static → API → SSE handshake verified; full LLM turn covered by benchmark |

---

## 1. Backend — PASS

- Server: `ps -p 36973` → `python -m dourmouse.webui`, elapsed 01:05:01 at audit time.
- Endpoints (loopback, real): `/` 200 (3 ms) · `/api/backend` 200 (1 ms) · `/api/roster` 200 (2 ms) · `/api/telemetry` 200 (108 ms) · `/api/activity` 200 (2 ms) · `/api/palette` 200 (1 ms) · `/api/state` 200 (8 ms).
- Backend config: `{"backend":"ollama","model":"dourmouse-finetuned"}`.

## 2. Auth gate — PASS (live-verified)

- `DOURMOUSE_ACCESS_TOKEN` set; `DOURMOUSE_HOST=0.0.0.0`.
- Via Tailscale IP `100.84.156.49:8765`: **no token → 302** (login redirect); **bearer token → 200**. Loopback stays token-free by design.

## 3. Memory store — PASS

- `/api/memory` → **2,757 facts** (the scaling plan's verification table said 566 — the store has grown; learn loop is active and ingesting).

## 4. Roster — PASS with doc drift

- `/api/roster` → `subagents: 23`. The portfolio doc says 26 agents. **Action: reconcile the doc count** (agents may have been merged/renamed).

## 5. Frontend — PASS

- `ui/index.html` 175 KB, `ui/map.html` 44 KB, `ui/agent.html` 18 KB — all served.
- External-reference check: only `http://www.w3.org/2000/svg` (XML namespace declaration, not a network fetch). **Zero CDN/external resources** — the "no external references" rule holds.
- Responsive: 5 `@media` breakpoints in `index.html` (routed shell: sidebar / icon rail / bottom tabs).

## 6. SSE — PASS

- `/api/events` streams; first observed event: `{"type":"freebuff_watch","state":"offline","detail":"app unreachable"}` — an honest bridge status (Freebuff app not reachable from the server's perspective), not a fabrication.

## 7. Tests — PASS with caveat

- Ran: `pytest test_webui.py test_multi_device.py test_guardrails.py` → **97 passed in 25.5 s**.
- Full suite per scaling plan verification: 991/1035 (95.7%); the 44 failures are Windows-port issues (Phase 0.4 scope, desktop-owned).

## 8. Performance — confirmed risk, needs one more pass

- HTTP endpoints: all sub-10 ms. Good.
- **LLM turn latency on this hardware: 3–223 s** depending on model and thermals (full numbers in `MODEL_BENCHMARK.md`, Phase 1.2). The scaling plan's "thermal ceiling on fanless Mac" risk is **confirmed**.
- **Owed:** a clean sustained-load run (benchmark currently occupies the GPU; rerun endpoint-load timing after it completes).

## 9. Reliability — PASS with notes

- Server: clean 1h+ uptime; `.dourmouse-ui.log` has 2 error lines (a stale launch attempt with the wrong Python — `ModuleNotFoundError: openai` — since resolved; housekeeping fixed the stale `.dourmouse-ui.pid`).
- Relay daemons: bridge + chat feed up detached (PIDs 39413/39414), feed answering 200 on 8789.

## 10. Security — **FAIL: dist ships runtime data (and possible secrets)**

- `dist/dourmouse-dist/` is **8.4 GB** and contains:
  - `workspace/memory/atlas_memory.db` — **grep matches `nvapi-` / `DOURMOUSE_ACCESS_TOKEN=` secret patterns in the binary**
  - `workspace/sessions/session_*.jsonl` — **130+ full session audit files** (user conversations, tool calls)
  - An `atlas 2` directory (build-path artifact of the exFAT volume).
- The portfolio doc's do-not-ship contract says dist "never ships `.env` or `local_secrets.py`" — but runtime workspace data is being shipped. The memory DB + sessions must be **excluded from builds** (Phase 0.10 adjacent; flag to desktop as a release blocker for Phase 4.1 signed installers).
- `.env` permissions: `-rwx------` (owner-only) — PASS (exec bit on a dotfile is cosmetic).

## 11. End-to-end — PASS (lite)

- Chain verified: static page → REST API → SSE handshake, all on the live server. A full multi-turn LLM chat was not run during the audit (GPU is occupied by the benchmark); the benchmark exercises production-prompt turns directly (see Phase 1.2).

---

## Findings → actions

1. **[RELEASE BLOCKER, Phase 0.10/4.1]** `build_dist.sh` must exclude `workspace/` (memory DB + sessions) from the dist artifact; scrub the existing 8.4 GB build. Desktop: adjust the packaging script + regenerate.
2. **[LAP]** sustained-load endpoint timing to re-run after the benchmark completes.
3. **[LAP+DOC]** reconcile roster count (23 live vs 26 documented).
4. **[LAP]** full LLM end-to-end pass (one real chat turn) after the benchmark — scheduled with the 14-day gate (Phase 1.3 log).
