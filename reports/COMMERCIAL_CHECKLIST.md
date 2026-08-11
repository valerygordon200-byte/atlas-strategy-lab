# COMMERCIAL EXECUTION CHECKLIST

Working document. Every box is a concrete, verifiable action. Tick as you go.
Order = dependency order. Source: reports/COMMERCIAL_REQUIREMENTS.md.
Owner shorthand: **ME** = desktop agent, **LAP** = laptop agent, **YOU** = human.

---

## PHASE 0 — FOUNDATION (security + a suite that passes everywhere)

### 0.1 Token rotation [ME+LAP, 15 min] — REQUIREMENT C1
- [ ] Generate a new token: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Update `relay/relay_config.txt` on desktop with the new TOKEN
- [ ] Restart the supervisor (kills + respawns all 7 services with the new token)
- [ ] Verify: old token gets 401 on `/recv` and `/send`; new token works
- [ ] Post on the relay: laptop pulls, updates ITS `relay_config.txt`, restarts bridge+feed+watcher
- [ ] Verify both directions deliver; delete the old token everywhere
- **DONE when:** old token is 401 everywhere; the feed flows both ways.

### 0.2 Secrets audit [ME, 0.5 day] — REQUIREMENT C2
- [ ] `git grep` the old relay token across ALL history (`git log -p` scan for `TOKEN=`, `nvapi-`, `ghp_`, `sk-`, `APCA_`)
- [ ] Grep the working tree for any key patterns in committed files
- [ ] Confirm `relay_config.txt`, `.env`, `local_secrets.py` are gitignored
- [ ] Document any historical leaks in `reports/SECRETS_AUDIT.md` (rotated = resolved)
- **DONE when:** zero live secrets in committed files or history; audit doc exists.

### 0.3 Windows test port [ME, 1–2 days] — REQUIREMENT A1 (44 failures)
- [ ] Fix class 1 (~25 fails, WinError 193): fake-CLI fixtures are POSIX `.sh` — swap to `.py` shims or `sys.executable` in: `test_atlas_cli`, `test_claude_code`, `test_codex_code`, `test_code_backends`, `test_agent_windows`
- [ ] Fix class 2 (~5 fails, POSIX paths): make path-guard assertions platform-aware (`/etc/hosts` etc.) in `test_system_access`, `test_map`, `test_v50_features`
- [ ] Fix class 3 (~14 fails, cp1252): open UI files with `encoding="utf-8"` in `test_learn`, `test_live_runtime`, `test_message_bus`, `test_repo_index`, `test_repo_panel`, `test_self_improve`, `test_general_roster`
- [ ] Re-run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest dourmouse/tests -q --tb=no`
- [ ] Confirm summary reads 1,035 collected, 0 failed
- **DONE when:** the suite is 100% green on Windows.

### 0.4 Cross-platform CI [ME, 0.5 day] — REQUIREMENT A2
- [ ] Add `.github/workflows/tests.yml`: matrix `os: [ubuntu, macos-latest, windows-latest]`
- [ ] Job: install Python 3.11+, `pip install -r requirements.txt -r requirements-dev.txt`, run the suite
- [ ] Add a second job for the ATLAS golden regressions (`E:`-independent, `--base` arg)
- [ ] Push and confirm all three OSes go green
- **DONE when:** a green check appears on every PR for all OSes.

---

## PHASE 1 — OS PRODUCT READINESS (a stranger can buy and run it)

### 1.1 Installers [ME+LAP, 2–3 days] — REQUIREMENT A3
- [ ] macOS: verify `build_app.command` produces a working `dourmouse.app`; fix any breakage
- [ ] Windows: create `start.bat` + `install.bat` (venv create, deps, model check, launch webui)
- [ ] Windows: verify launch via `python -m dourmouse.webui` opens `http://127.0.0.1:8765`
- [ ] Document: two supported install paths (macOS .app, Windows .bat) in a short INSTALL.md
- **DONE when:** a clean machine reaches a working dashboard in <5 min on each OS.

### 1.2 One-click first-run [ME, 1–2 days] — REQUIREMENT A4
- [ ] Launcher detects missing Ollama/model → prints exact fix (or auto-pulls if Ollama running)
- [ ] Route the SETUP panel checklist into the first-run flow (capabilities shown honestly: ●/○)
- [ ] Validate keys live on entry (key_check.py already does — ensure it's in the flow)
- [ ] After first chat, show the memory-facts line + 👍/👎 (learning on by default)
- **DONE when:** a non-technical user reaches a working chat in <10 min with no manual.

### 1.3 Legal docs [YOU + ME draft, 1 day] — REQUIREMENT A5
- [ ] ME drafts: LICENSE (pick MIT vs proprietary — decide with E5), EULA, privacy policy, terms
- [ ] YOU: review; state the trade-secret line (public repo vs private signals — E5)
- [ ] Put the three docs at repo root; link from README footer and landing page
- **DONE when:** a lawyer could review them; the data story is explicit and true.

### 1.4 Stranger docs [ME, 1 day] — REQUIREMENT A6
- [ ] Rewrite README quickstart for a non-builder (install → run → first ask → troubleshooting)
- [ ] Add FAQ (5–8 questions: privacy, models, hardware, updates, Windows support, limits)
- [ ] Add a "what it can't do" section (honest limits — on-brand)
- **DONE when:** a stranger installs and runs it without asking anyone.

---

## PHASE 2 — LAB CREDIBILITY CHAIN (the receipts)

### 2.1 Guardrails in the golden suite [ME, 1 day] — REQUIREMENT B3
- [ ] Add a 4th gate to `scripts/golden_regressions.py`: simulate a guardrail trip → suite must FAIL
- [ ] Gate: `trip detected` → release blocked with the guardrail named
- [ ] Verify all four gates run in <5 s; update the hub's golden button copy
- **DONE when:** the golden suite fails on a simulated trip and passes otherwise.

### 2.2 Risk execution layer [ME, 2–3 days] — REQUIREMENT B4
- [ ] Wire `dourmouse/guardrails.py` (AccountState, position caps, daily-loss trip) into the engine's trade-decision path
- [ ] A proposed trade violating a cap → REFUSED + logged with reason (not a warning)
- [ ] Kill switch: one red action in the hub, tripped → blocks all new trades, logged to ledger
- [ ] Add tests: cap violation, daily-loss trip, kill-switch trip
- **DONE when:** no code path can open a trade that violates a hard cap.

### 2.3 Public live ledger [ME, 1–2 days] — REQUIREMENT B5
- [ ] Schema: trade id → decision card id → direction → size → entry/exit → pnl → guardrail/approval trail
- [ ] Serve as `/ledger` in the hub + `reports/paper_log.csv` continues as the source of truth
- [ ] Every card ends in a terminal state (FILLED / REJECTED_AT_GUARDRAIL / NO_TRADE / user-rejected)
- **DONE when:** a stranger can audit the whole chain of any trade.

### 2.4 Real decision cards (P3) [ME, 1–2 days] — REQUIREMENT B1
- [ ] Bridge: engine's `usdjpy_drift_k1` output + forward ledger → real cards (real p, real ledger refs)
- [ ] Add a second real source (dual momentum) so the feed is not one-signal-dependent
- [ ] Replace demo ids with real ids; keep the schema-validating `--check`
- [ ] Update the UI banner: remove "DEMO DATA" once real
- **DONE when:** the hub's cards show live data with real p-values and ledger links.

### 2.5 Compliance kit [ME draft, 1 day] — REQUIREMENT B8
- [ ] Risk-warning block on every public Lab surface (hub, landing, emails): "CFDs are complex… 77% of retail lose money… not investment advice"
- [ ] A "what we are / what we are not" one-pager (research tooling, not advice; no return promises)
- **DONE when:** no public Lab surface lacks the warning.

### 2.6 IBKR paper cycle [YOU+LAP, blocked] — REQUIREMENT B2
- [ ] YOU: install TWS/IB Gateway, log in with the PAPER account, enable API on 7497 (docs/IBKR_PAPER_SETUP.md)
- [ ] gateway_watch on the laptop auto-runs `--check` the moment 7497 opens and pings the feed
- [ ] ME: drive the first real paper fill via `scripts/ibkr_connector.py --paper-order …`
- [ ] Every fill lands in the paper log → feeds the public ledger (2.3)
- **DONE when:** the first real paper fill is in the ledger with its decision card.
- **NOTE: starts the 6–8 month track-record clock. Do as early as possible.**

---

## PHASE 3 — SALES SURFACE (revenue)

### 3.1 Pricing [YOU+ME, 1 day] — REQUIREMENT D1
- [ ] Decide: OS one-time vs subscription (recommend: one-time for v1 + support tier)
- [ ] Decide: Lab — free research tier vs paid ledger/subscription (recommend: free graveyard+registry, paid live cards)
- [ ] Decide: B2B data license price point + the DATA-never-SIGNALS contract line
- [ ] Write it into `sales/PRICING.md` with compliance notes per tier
- **DONE when:** a price exists for both products and the doc is defensible.

### 3.2 Landing page + waitlist [ME, 1–2 days] — REQUIREMENT D2
- [ ] Static page in the Jarvis design language: headline, privacy story, 30-sec demo hook, graveyard link, waitlist form
- [ ] Waitlist writes to `sales/waitlist.csv` (consent captured) — served by `serve_hub.py` or a tiny endpoint
- [ ] Deploy on :8791 (and later a public URL)
- **DONE when:** a visitor joins the waitlist in <30 s with consent recorded.

### 3.3 Lead compiler [ME, 1 day] — REQUIREMENT D3
- [ ] Script: pull business contacts from public directories (source URL + consent flag per lead)
- [ ] Dedupe + append to `sales/leads.csv`; never harvest personal data
- [ ] Target: 50–200 quality B2B leads in the first pass
- **DONE when:** leads.csv has real, sourced, deduped business leads.

### 3.4 Mail-merge + follow-up [ME, 1–2 days] — REQUIREMENT D4
- [ ] Script: reads leads.csv, fills the template per lead, stages drafts (no auto-send)
- [ ] Day-0/5/30 scheduler with opt-out handling (unsubscribe link, honor instantly)
- [ ] CAN-SPAM block in every email (physical address, honest subject, opt-out)
- [ ] YOU: configure the sending account/domain; DKIM/SPF checked before first send
- **DONE when:** the user runs one command and gets drafted, personalized, compliant emails.

### 3.5 Community content calendar [ME, 1 day] — REQUIREMENT D5
- [ ] Pick 3–4 communities (r/selfhosted, r/LocalLLaMA, r/algotrading, HN)
- [ ] Calendar: 1 contribution/week each — value-first, product mention ≤10%
- [ ] First 4 posts drafted (graveyard post-mortems are the flagship content)
- **DONE when:** a month of content is drafted and scheduled for YOU to post.

### 3.6 Demo video [YOU, 1 day] — REQUIREMENT D6
- [ ] Script a 5-min walkthrough (OS: install→first ask→agent map; Lab: cards→graveyard→ledger)
- [ ] Record screen share; host where you choose
- **DONE when:** the demo link exists and a stranger understands the value in 5 min.

### 3.7 CRM [ME, 1 day] — REQUIREMENT D8
- [ ] Upgrade leads.csv → simple pipeline view (stages, touch history, next action)
- [ ] A tiny CLI/panel: "who's due today" — so the user spends 10 min/day, not hours
- **DONE when:** the funnel is visible at a glance and daily follow-ups are one command.

---

## PHASE 4 — OPS HARDENING

### 4.1 Backups [ME, 1 day] — REQUIREMENT C3
- [ ] Script: E:/ (data+scripts) and both repos → backup target (D:), nightly via Task Scheduler
- [ ] Document restore drill; run it once on a scratch dir
- **DONE when:** a restore drill succeeds.

### 4.2 Monitoring [ME, 1–2 days] — REQUIREMENT C4
- [ ] Supervisor: keep restart counts; add alert if any service restarts >4 in 10 min
- [ ] Weekly health digest posted to the relay (exists as the morning-report pattern — reuse it)
- **DONE when:** a crash is noticed without anyone watching.

### 4.3 Release discipline [ME, 1 day] — REQUIREMENT C5
- [ ] Release checklist: golden regressions → full suite → version tag → changelog entry
- [ ] Encode as a script (`release.sh`) so it can't be skipped
- **DONE when:** every release is reproducible and auditable.

### 4.4 Pen-drive resilience [ME+LAP, 1–2 days] — REQUIREMENT C6
- [ ] Laptop: workspace + venv on internal disk; `/Volumes/ATLAS` used only for data files
- [ ] Desktop: E: access is already data-only — confirm nothing else hardcodes E:
- **DONE when:** the Mac runs with the drive unplugged; the I/O-error failure mode is gone.

---

## PHASE 5 — LATER STAGE (post-launch)

- [ ] A8 hosted/cloud option (weeks, after local-first demand proves out)
- [ ] B7 per-user accounts for the Lab
- [ ] C7 performance/scale measurements documented
- [ ] D7 referral program (first 10 users → one intro each)

---

## DAILY EXECUTION RHYTHM (once live)

1. Check the relay for laptop messages (auto-reply + toast already handle the watch)
2. Run the golden regressions (one command) — any drift is a release blocker
3. Check the supervisor status row in the hub (7/7)
4. Feed the lead pipeline: compile leads → draft sends → user sends → log follow-ups
5. One community contribution drafted (graveyard post-mortems as content)
6. Commit + push; the laptop pulls and we stay in sync

## THE ONE HUMAN CLOCK
**IBKR paper login (2.6)** starts the 6–8 month track-record timer. Everything else
can be built in parallel. Do it this week if at all possible.
