# C1 — Commercial Specification (dourmouse + atlas)

Date: 2026-08-11 · Owner: desktop-atlas · Status: DRAFT (laptop review pending)

## 1. What "commercial level" means here

Not "sell it tomorrow." It means: **the stack is dependable enough to trade real
money through, and complete enough that a fresh machine can run it without the
original authors.** Three components, per the user's directive:

1. **Atlas backtesting engine, loaded with all current data** — every dataset on
   the pen drive reachable through the unified registry, every backtest
   reproducible, no per-author scripts.
2. **The live chat feed** — the relay/dashboard is part of the product: agents
   coordinate through it, and it must survive unattended operation.
3. **Two-machine team** — desktop + laptop agents share one objective, one board,
   one feed, and never leave a message unanswered.

## 2. Acceptance criteria

### A. Engine & data (C2, C7, registry — largely built)
- [ ] Every dataset on `E:\forex-data` resolves through `data_registry.load(key)`
      (100 keys swept, 91 clean — the 9 gaps are documented availability limits).
- [ ] `data_registry` has a **programmatic API** (HTTP) callable from dourmouse's
      UI: `GET /api/keys`, `GET /api/data/{key}`, `POST /api/backtest`, results
      JSON-returned with the run parameters embedded (reproducibility).
- [ ] Golden regression suite (C7) runs the three confirmed results and **fails
      loudly** on any drift: hog roll-check (continuous ≈ −13.6%, t≈−7.5 vs real
      path ≈ 0), USDJPY drift (OOS t in 3.0–4.5 band, 4/6 gates), Dual Momentum
      (+2.12%/mo, t 4.51, wf p 0.001). A regression gate is a release blocker.
- [ ] Every backtest report states: data source + key, roll convention, cost
      model, split dates, permutation counts. No report without provenance.
- [ ] Time-to-load any single series ≤ 5s from cold; full battery ≤ 15 min.

### B. Chat feed / relay (C4)
- [ ] Dashboard **send is token-gated** (no anonymous messages into the feed).
- [ ] Message archive survives relay restarts; `relay/messages/` rotates (keep ≥
      90 days, archive older to `relay/archive/`).
- [ ] **Uptime heartbeat**: every 5 min the relay broadcasts a health line
      (participants, message count) — silence > 10 min = dead relay, alerted on
      the dashboard.
- [ ] Bridge auto-reconnect with backoff; watermark never skips or duplicates
      (persistent-id fix is the baseline).
- [ ] Feed renders on any browser; send box works from both machines.

### C. Two-machine team discipline (this protocol)
- [ ] **Immediate reply rule** (user-mandated): any message from the other device
      gets a reply within ~15s — from a session when one is open, from the worker
      auto-ack otherwise. This is enforced mechanically, not by intent.
- [ ] One board (`coordination/tasks.json`), claim-lock, push-after-every-action.
- [ ] Every task DONE carries a one-line result + artifact paths.
- [ ] No message sits unacknowledged across a session boundary.

### D. Reliability / operations (C5)
- [ ] Supervisor keeps alive: tick collector, event pipeline, forward ledger,
      worker, relay, chat feed — restart-on-crash, status endpoint.
- [ ] Start scripts are the single entry point on each machine
      (`start_relay.bat` / `start_client.bat`; laptop equivalents).
- [ ] Logs rotate; crashes are visible in the feed, not just in log files.

### E. Security
- [ ] Secrets only in env / git-ignored config (`relay_config.txt` pattern).
      No token in any committed file. (Audit on every release.)
- [ ] Worker executes only whitelisted board commands (already enforced).
- [ ] Dashboard send requires the shared token even on loopback.

### F. Risk guardrails (trading, when live)
- [ ] Pre-trade checklist enforced in code: position ≤ daily cap, ≤ margin,
      correct contract/expiry alignment (the hogs lesson), financing included.
- [ ] Paper-first: every strategy lives on the forward ledger / demo fills before
      any live capital. Live execution only via the audited connector (C3).
- [ ] Per-strategy kill gates from the research framework (OOS t, gates, ledger
      event counts) are wired to stop signals, not advisory.

### G. Packaging & docs (C6)
- [ ] One-command setup on a fresh machine: install deps + copy `.env`/config +
      smoke test (`scripts/health_check.py` prints all keys + 3 regressions).
- [ ] README covers: what the stack is, how to run it, how the two machines talk,
      how to add data, how to add a strategy.
- [ ] LICENSE chosen and applied.

## 3. Milestone order (board IDs)

| ID | Task | Owner | Blocked by |
|---|---|---|---|
| T4/C1 | Commercial spec (this doc) | desktop | — |
| T5/C2 | Engine as callable service | desktop | registry (done) |
| T6/C3 | Execution layer audit | laptop | — |
| T7/C4 | Chat/relay hardening | laptop | — |
| T8/C5 | Pipeline supervisor | desktop | C4 heartbeat design |
| T9/C6 | Packaging & docs | laptop | C2 API surface |
| T10/C7 | Golden regression suite | desktop | — |

Order note: C7 (T10) and C2 (T5) can start immediately; C5 (T8) after C4 (T7)
defines the heartbeat contract; C6 (T9) after the API surface exists.

## 4. Definition of DONE for the whole programme

All boxes in §2 ticked AND:
- the three regressions pass on a **fresh machine** with the packaged setup,
- one full paper-trade cycle (signal → entry → exit → ledger entry) completes
  through the audited connector with real demo fills,
- the feed shows ≥ 1 week of continuous uptime with heartbeats.

Reviewer: laptop-dourmouse — raise objections to any criterion before we commit
to it as a gate.
