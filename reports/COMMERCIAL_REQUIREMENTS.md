# COMMERCIAL REQUIREMENTS — dourmouse + ATLAS

Status: v1, 2026-08-11. The full requirement list for turning the system into
a product people can buy. Every requirement has: ID, priority, owner, effort,
and an acceptance gate. Priorities: **P0 = launch blocker**, P1 = launch-critical,
P2 = should-have, P3 = later stage.

Truth anchor: this list is useless unless the product keeps its honesty brand —
"we don't sell picks, we sell the receipts." Nothing below may weaken that.

---

## A. The OS product (dourmouse) — sellable to prosumers first

| ID | Req | Prio | Owner | Effort | Acceptance |
|---|---|---|---|---|---|
| A1 | **Windows port of the test suite (44 failures)** — UTF-8 opens, platform-aware path guards, .py fake-CLI shims | P0 | me | 1–2 days | `pytest` 100% green on this Windows machine |
| A2 | **Cross-platform CI** — GitHub Actions running the 1,035-test suite on macOS + Windows per push | P0 | me | 0.5 day | PRs fail loudly on any platform regression |
| A3 | **Signed installers** — dourmouse.app (macOS, exists) + Windows launcher/installer; no "unidentified developer" friction | P0 | me+laptop | 2–3 days | Fresh install on a clean machine in <5 min |
| A4 | **One-click first-run** — venv auto-create, model auto-download/verify (Ollama), key validation (exists), guided capability checklist (SETUP panel exists → make it the onboarding) | P0 | me | 1–2 days | Non-technical user reaches a working chat in <10 min |
| A5 | **LICENSE + EULA + privacy policy + terms** | P0 | human+me (draft) | 1 day | Legally reviewable; no secrets; clear data story ("nothing leaves your machine except calls you make") |
| A6 | **Stranger-proof README + docs** — user-facing, not builder-facing; quickstart, troubleshooting, FAQ | P0 | me | 1 day | A stranger can install without asking questions |
| A7 | **Version + update channel** — versioned releases, changelog, `dourmouse --update` or documented update path | P2 | me | 1–2 days | Update path verified on both OSes |
| A8 | **Hosted/cloud option** (deferred): the OS as a web service | P3 | both | weeks | TBD — only after local-first demand proves out |
| A9 | **Windows voice fallback** — piper works; macOS `say` fallback is Mac-only | P2 | me | 1 day | Voice buttons honest on Windows |

## B. The Lab product (ATLAS) — the trading receipts

| ID | Req | Prio | Owner | Effort | Acceptance |
|---|---|---|---|---|---|
| B1 | **P3: real decision cards** — engine→cards bridge (drift + dual momentum with real p, real ledger refs) | P0 | me | 1–2 days | Cards render live data, not demo |
| B2 | **T11: IBKR paper cycle** — Gateway login (human step) → real paper fills → public ledger | P0 | human+laptop | blocked | N clean paper cycles, zero guardrail violations |
| B3 | **P5: guardrails in the golden suite** — guardrail-trip test = release blocker (4th gate) | P0 | me | 1 day | Golden suite fails on a simulated guardrail trip |
| B4 | **Risk execution layer** — guardrails enforced in code on every trade decision (position caps, daily-loss trip, kill switch logged) | P0 | me | 2–3 days | A proposed trade that violates a cap is refused + logged, not warned |
| B5 | **Public live ledger** — every paper trade, its decision card, and outcome visible (the credibility asset) | P0 | me | 1–2 days | A stranger can audit the full chain |
| B6 | **Track-record window** — 6–8 months of clean forward paper data before the Lab is sold as a subscription | P1 | time | months | The ledger, not a promise |
| B7 | **Per-user accounts** for the Lab (when sold) | P3 | both | weeks | Login, per-user state, per-user risk limits |
| B8 | **Compliance kit** — risk warnings, "77% lose money" honesty, no-return-promise language, CFD disclosure | P0 | me (draft) | 1 day | Every public Lab asset carries the warning |

## C. Engineering & operations

| ID | Req | Prio | Owner | Effort | Acceptance |
|---|---|---|---|---|---|
| C1 | **Token rotation** — generate new relay token, flip both machines, kill the leaked token | P0 | both | 15 min | Old token 401 everywhere; both feeds live |
| C2 | **Secrets hygiene audit** — no tokens/keys in committed files or history (watch for new leaks) | P0 | me | 0.5 day | `git grep` clean + history scan documented |
| C3 | **Backups** — E:/ data + repos backed up; documented restore | P1 | me | 1 day | Restore drill works on a scratch machine |
| C4 | **Monitoring** — supervisor + notify exist; add: uptime history, alert on service crash >1/10 min, weekly health digest | P2 | me | 1–2 days | A crash is noticed without anyone watching |
| C5 | **Release discipline** — golden regressions + full test suite gate every release; versioned tags | P1 | me | 1 day | Releases are reproducible and auditable |
| C6 | **Pen-drive fragility** — dourmouse should not I/O-error when /Volumes/ATLAS is absent; internal-disk workspace with the drive for data only | P1 | both | 1–2 days | Mac runs with the drive unplugged |
| C7 | **Performance/scale** — measure webui + engine under load; document limits | P3 | me | — | Honest numbers in the README |

## D. Sales & commercial operations

| ID | Req | Prio | Owner | Effort | Acceptance |
|---|---|---|---|---|---|
| D1 | **Pricing model** — OS tiers (one-time vs subscription), Lab plans, B2B data license (DATA, never SIGNALS) | P0 | me+human | 1 day | A price exists; numbers defensible |
| D2 | **Landing page + waitlist** — Jarvis-language static page, privacy story, graveyard link, waitlist form (inbound = consented leads) | P0 | me | 1–2 days | A visitor can join the waitlist in <30 s |
| D3 | **Lead compiler** — public-directory business leads → leads.csv with source + consent flags | P1 | me | 1 day | 50–200 quality B2B leads with sources |
| D4 | **Mail-merge + follow-up tool** — per-lead personalization, day-0/5/30 scheduler, opt-out handling; user runs it | P1 | me | 1–2 days | CAN-SPAM/GDPR-clean sends from the user's domain |
| D5 | **Community presence plan** — contribution-first content calendar (graveyard post-mortems as content) | P1 | me | 1 day | 1 honest post/week per community |
| D6 | **Demo video** — 5-min screen share of the OS + Lab (the demo IS the sales pitch) | P2 | human | 1 day | A stranger understands the value in 5 min |
| D7 | **Referral program** — first 10 users → one intro each | P2 | me | 0.5 day | Tracked in the CRM |
| D8 | **CRM** — the leads.csv upgraded: stages, touch history, pipeline view | P2 | me | 1 day | The user sees the whole funnel at a glance |

## E. Legal & compliance (non-negotiable)

| ID | Req | Prio | Owner | Effort | Acceptance |
|---|---|---|---|---|---|
| E1 | **No return promises** on any trading material — ever | P0 | all | — | Constant; audited |
| E2 | **CAN-SPAM compliance** — physical address, honest subject, instant opt-out on every email | P0 | me | included in D4 | Templates carry all three |
| E3 | **GDPR posture** — lawful basis recorded per lead; opt-outs honored; no personal-data harvesting | P0 | me | included in D3/D4 | Consent flag + source recorded per lead |
| E4 | **Financial advice boundary** — the Lab is research tooling, not advice; disclosures in place | P0 | me | 1 day | Public copy reviewed |
| E5 | **Trade-secret vs open-source decision** — what stays public (repo), what stays private (signals, locked legs) | P1 | human | 1 day | A documented line, per the A3 amendment (DATA yes, SIGNALS never) |

---

## Priority order (the P0 path — what unblocks a launch)

1. **A1+A2** — Windows-green suite + CI (the test suite is the product's honesty engine; it must pass everywhere)
2. **A3–A6** — installers, onboarding, legal, docs (a stranger must be able to buy and run it)
3. **C1+C2** — token rotation + secrets audit (security before any public launch)
4. **B3+B4+B5** — guardrails in code + public ledger (the Lab's credibility chain)
5. **D1+D2** — pricing + landing page/waitlist (the first revenue surface)
6. **B1** — real decision cards (the demo must not be demo)
7. **B2** — human IBKR login → paper cycle starts (the clock on the track record; **the sooner the better — it's a months-long timer**)

## Standing rules (apply to everything)
- Golden regressions + full suite green before any release.
- No fabricated numbers, no fake social proof, no invented testimonials.
- The honesty brand is the product — any requirement that would weaken it is wrong by definition.
- Money-adjacent claims: no return promises, ever.
