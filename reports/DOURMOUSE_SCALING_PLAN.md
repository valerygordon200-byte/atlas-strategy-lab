# DOURMOUSE — COMMERCIAL SCALING PLAN (v1)
Execution plan built on top of `DOURMOUSE_COMMERCIAL_PLAN.md` (the authoritative strategy doc).
Status: pre-revenue, pre-validation. Every gate below is evidence-gated; a failed gate is a successful outcome, not a failure.

---

## 0. The three decisions this plan makes

1. **Product = small-business workflow automation.** The Atlas trading engine is parked (not sold, not productized at this stage). The Tailscale two-machine feed stays as *internal dev tooling only* — it is how we build, not what we sell.
2. **The repo holds ONE commercial direction.** `COMMERCIAL_REQUIREMENTS.md` / `COMMERCIAL_CHECKLIST.md` were built for the Atlas-led sell plan. They are now **superseded** for commercial purposes; their reusable items (token rotation, secrets audit, Windows test port, compliance kit, installers) are folded into this plan. They stay in the repo as archived record, marked superseded — not deleted.
3. **Nothing is sold until Phase 3's evidence exists.** No pricing, no landing page, no outreach beyond the Phase 2 cohort until a real user reports measurable value.

---

## 1. Verified starting point (2026-08-12, checked against code)

| Fact | Verified |
|---|---|
| Stack: Python (webui.py stdlib HTTP server + SSE) + static HTML UI; **not Next.js** | ✅ |
| Agent cluster admin_ops / atlas / jarvis with tool-calling, file ops, web search | ✅ |
| Memory/fact store: SQLite + FTS5 + semantic recall | ✅ (566 count = live runtime number, Mac-side) |
| Approval gates: run_privileged_command → INTERVENTIONS, RBAC, guardrails.py | ✅ |
| Live status + SSE wiring; daily reporter daemon; kill switch (stop.command) | ✅ |
| Gmail read/search/send + read-only Calendar | ✅ |
| **Google Drive, Google Sheets** | ❌ not in code |
| **PDF/receipt/invoice extraction** | ❌ not confirmed in code |
| **User-defined recurring workflows** ("every Monday") | ⚠️ partial — fixed internal poll tables only |
| **Turnkey onboarding** (no API keys/config) | ❌ requires Ollama + .env + venv today |
| Test suite | 991/1035 pass (95.7%); 44 failures = Windows-port issues only |
| Live stack on this machine | hub :8791 ✅, engine :8790 ✅, relay :8788 ✅, 7 supervised services ✅ |
| Laptop agent (Mac) | ⬇ down since 2026-08-11 (Freebuff crash + pen-drive I/O); relay keeps its inbox |
| External users / demand signal | none — correctly untested |

**Consequence:** the commercial plan's Phase 1 gate ("10 core features work reliably for 2 weeks") **cannot be attempted until the three ❌ feature gaps are closed**. Phase 0 below exists to close them.

---

## 2. Phases, gates, owners, timeline

Owner shorthand: **ME** = this desktop agent, **LAP** = laptop agent, **YOU** = human.

### PHASE 0 — FOUNDATION (make the evidence honest) — ~2–3 weeks, mostly ME
The goal: a system that is secure, tests green on the platform buyers use, and actually possesses the ten v1 features.

| # | Work item | Owner | Gate / done-when |
|---|---|---|---|
| 0.1 | Commit the commercial plan + this plan to the repo (authoritative docs live in `reports/`) | ME | pushed; laptop can pull |
| 0.2 | Mark `COMMERCIAL_REQUIREMENTS.md` / `COMMERCIAL_CHECKLIST.md` superseded with a pointer to this plan | ME | archived, not deleted |
| 0.3 | Token rotation + secrets audit (old token is in git history) | ME | old token 401 everywhere; audit doc exists; zero live secrets committed |
| 0.4 | Windows test port: fix the 44 failures (POSIX .sh fixtures → .py shims; platform-aware path assertions; UTF-8 opens) | ME | suite 1,035/1,035 green on Windows |
| 0.5 | CI: matrix (ubuntu / macos / windows) running the suite + ATLAS golden regressions | ME+LAP | green check on every PR, all OSes |
| 0.6 | **Close feature gap: Google Drive + Sheets** (auth via existing Google path; list/read/write on Drive, read/update on Sheets) | ME | working tools + tests; honest NOT-CONFIGURED states |
| 0.7 | **Close feature gap: user-defined recurring workflows** ("do X every Monday") — extend live_runtime schedule table to persist user-defined entries | ME+LAP | schedule editor works end-to-end; restart survives |
| 0.8 | **Close feature gap: PDF/receipt/invoice extraction** (pypdf/pdfplumber route; fields → structured output) | ME | extraction tool + tests |
| 0.9 | **Turnkey onboarding v1**: one-command setup (detect/install Ollama, create venv, generate .env from defaults, first-run wizard) — packaged installer deferred to Phase 4 | ME+LAP | works on a clean machine, zero manual config |
| 0.10 | Kill stale research processes (lockup_test ×4, lockup_refetch_adj ×2); commit uncommitted dourmouse files; clean supervisor restart | ME | stack healthy, tree clean |

**Gate 0 (pass to Phase 1):** suite green on Windows + CI green; secrets clean; Drive/Sheets/recurring/extraction shipped with tests; onboarding one-command works on a clean machine.

### PHASE 1 — PROVE IT FOR ONE USER (the plan's Phase 1) — ~3–4 weeks
| # | Work item | Owner | Gate / done-when |
|---|---|---|---|
| 1.1 | Full system audit (frontend, backend, performance under sustained load, end-to-end) → `AUDIT.md` with per-area pass/fail | ME (harness) + LAP (runs on the Mac, owns the live system) | audit doc complete; every area marked |
| 1.2 | Model upgrade + before/after benchmark: qwen3:8b vs gemma4:e4b vs gpt-oss:20b on the multi-step orchestration task set; pick the model that closes the reliability gap on this hardware | LAP (Mac) with ME harness | benchmark numbers; reliability gap closed or explicit residual list |
| 1.3 | Two continuous weeks of real personal use, no supervision; daily reliability log (failures, recoveries, feature usage) | YOU (use) + LAP (log) | log exists for all 14 days |

**Gate 1:** ten features reliable for 2 continuous weeks; zero unrecovered failures; benchmark confirms the gap closed. **This gate is the plan's own; if it fails, debug — never lower the bar.**

### PHASE 2 — PROVE IT FOR A HANDFUL (the plan's Phase 2) — ~6–10 weeks
| # | Work item | Owner | Gate / done-when |
|---|---|---|---|
| 2.1 | Recruit 3–7 real users (contractors, small professional firms, small hospitality, regional suppliers) with a specific repetitive workflow; not friends humoring a demo | YOU (outreach) + ME (sourcing, scripts) | cohort list with named workflows |
| 2.2 | White-glove onboarding per user; log every failure, confusion point, and trust-moment (approval gate hesitation) | YOU + LAP + ME (log tooling) | per-user session logs |
| 2.3 | Weekly review of the failure log; fix the top recurring issue each week | ME+LAP | weekly review notes committed |
| 2.4 | No payment collected. Objective is signal. | — | stated and held |

**Gate 2:** ≥1 real user reports a measurable time saving AND would be upset if the tool were taken away. **If no user reports value after honest sustained use → stop onboarding, rescope. That is a successful negative.**

### PHASE 3 — INTRODUCE MONETIZATION — only after Gate 2
| # | Work item | Owner | Gate / done-when |
|---|---|---|---|
| 3.1 | Pricing decision from Phase 2 evidence (Option A flat sub / B setup+sub / C early-access lifetime — test, don't commit) | YOU (decision) + ME (analysis of what users valued) | one model chosen with reasoning |
| 3.2 | Minimal licensing/entitlement (who is entitled, expiry, seat) — token-gating exists; licensing doesn't | ME | paid pilot can be issued/revoked |
| 3.3 | Small paying pilot cohort (single digits) | YOU + ME | ≥1 pilot stays past 30 days; churn reason understood |

**Gate 3:** ≥1 paying pilot past 30 days with a fixable-or-understood churn reason. **Pilot churn without a fixable cause → stop selling, return to Phase 2.**

### PHASE 4 — SCALE — only if Phase 3 shows real demand
| # | Work item | Owner | Gate / done-when |
|---|---|---|---|
| 4.1 | Signed installers + update mechanism (replace git-pull + .bat for customers) | ME+LAP | clean install + update on a stranger's machine |
| 4.2 | Opt-in, honest telemetry (feature usage, task failures, approval-gate trips) + failure reports that reach us | ME | consent-first; dashboard |
| 4.3 | Backup/recovery for user business data (survives a dead laptop) | ME+LAP | restore tested from scratch |
| 4.4 | Stranger-proof docs: README, privacy policy, terms, compliance kit (no return promises ever; CAN-SPAM block; license DATA never SIGNALS) | ME | reviewable by a stranger |
| 4.5 | GTM: direct outreach with working demos of the prospect's own workflow; waitlist/landing for inbound; no paid ads until a public success story exists | YOU + ME | first repeatable acquisition from cold outreach |

**Gate 4:** repeatable acquisition + positive unit economics. **If not reached, a boutique single-owner tool is a valid outcome — never force scaling.**

---

## 3. What stays parked (explicit exclusion list — do not re-enter scope)
- **Atlas trading engine / Lab product** — parked. The live USDJPY drift forward ledger keeps accumulating (already running) but is not a v1 product feature. T11 (IBKR paper login) stays paused for this track.
- **Tailscale mesh / two-machine feed** — internal dev tooling only. It is how ME+LAP build, not what we sell.
- **Multi-provider BYOK routing, OS-level control, hosted multi-tenant version** — Phase 4+ questions, each its own scoping pass.

---

## 4. Division of labor
- **ME (desktop):** Phase 0 entirely (0.1–0.10), audit + benchmark harnesses (1.1, 1.2), Phase 2 log tooling (2.2), licensing (3.2), telemetry + backup + docs (4.1–4.4). Everything verifiable on this machine.
- **LAP (laptop/Mac, once recovered):** runs the live system the audit is about (1.1), model benchmarks on the actual hardware (1.2), daily reliability log (1.3), onboarding sessions (2.2), UI polish. Coordinate via the relay feed; relay keeps messages until it reconnects.
- **YOU:** Phase 1's two-week real use (1.3 — the only way the gate passes), Phase 2 recruiting + white-glove onboarding (2.1, 2.2), pricing decision (3.1). Everything else ME/LAP can execute.

## 5. Timeline (best case, not a promise)
- Phase 0: **now → ~3 weeks** (parallelizable, mostly ME — can start immediately)
- Phase 1: ~3–4 weeks after Gate 0 (audit 1 wk + 2-wk gate)
- Phase 2: ~6–10 weeks after Gate 1
- Phase 3: starts ~month 4; Phase 4: month 6+ only if gates pass
- **Honest milestone: paying pilots ≈ 4 months away; scaling ≈ 6+ months, evidence-gated.**

## 6. Risk register additions (beyond the commercial plan's own)
| Risk | Why it matters | Mitigation |
|---|---|---|
| Laptop side stays down | All Mac-side work (audit, benchmarks, real-use log) blocks | Phase 0 is 100% desktop-executable; laptop work only gates Phase 1.2+ |
| Two-week gate needs sustained human use | The plan's own kill criterion depends on YOU | Schedule the 14 days explicitly; a daily 15-min log is the only ask |
| Google API credentials for Drive/Sheets | Turnkey onboarding says "no API keys" — OAuth flow must be first-run wizard, not config | 0.9 builds the wizard; test on a clean machine |
| Reliability under load on fanless Mac | Known thermal ceiling | Audit 1.1 tests sustained load explicitly; if it fails, batch-processing design is the fallback, not silence |

## 7. Immediate next steps (this week)
1. **ME:** commit both plan docs + supersede markers (0.1, 0.2).
2. **ME:** token rotation + secrets audit (0.3) — 15 min, closes the live leak.
3. **ME:** start the 44-failure Windows port (0.4).
4. **ME:** scope the Drive/Sheets integration against the existing Google auth path (0.6) — the biggest feature gap.
5. **ME:** draft the one-command onboarding script (0.9).
6. **YOU:** decide whether the Mac pen drive is recoverable (laptop must come back for Phase 1). Everything else runs without it.
7. **YOU:** block the 14-day Phase 1 window once Gate 0 passes.
