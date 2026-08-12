# DOURMOUSE
# COMMERCIAL PLAN
Validation-first path to a small-business workflow automation product
Draft — August 2026
Status: pre-revenue, pre-validation. This document is a plan, not a claim of traction.

## 1. Executive summary
Dourmouse is a private, local-first AI agent system currently used as a personal workflow and research tool. This document lays out a deliberately narrow, evidence-gated path to a commercial version — not a launch plan, a validation plan.
The product being planned is workflow automation for small businesses: an agent that takes a plain-language instruction, executes it across the tools a small business already uses (email, files, spreadsheets, calendar), asks for approval before anything risky, and reports what it did. Nothing more, for version one.
Two things are deliberately not part of this plan yet:
- The Atlas trading/backtesting engine — not being productized or sold at this stage.
- The full multi-device mesh, multi-provider model routing, and OS-level control vision from earlier product notes — real ideas, wrong stage. Each is its own project and none is required to prove the core value.

Governing principle for this whole document: no claim in here is asserted as fact unless it has been tested. Where something is a hypothesis (pricing, demand, positioning), it is labeled as one, with the test that would confirm or kill it.

## 2. Current state — an honest assessment
Before any commercial plan can be credible, it has to start from what is actually true today, not what the product is meant to become.

### 2.1 What exists
- A working multi-agent orchestration system (Dourmouse), built in Next.js, using SSE streaming and recursive sub-agent delegation.
- Running locally on a single MacBook Air (Apple M3, 24GB unified memory, fanless) via Ollama.
- A functioning agent cluster (admin_ops, atlas, jarvis) with tool-calling, file operations, and web search.
- A persistent memory/fact store (566 recorded facts at last check).

### 2.2 What has been tested, and what it found

| Area | Finding | Status |
|---|---|---|
| Model reliability | The original backend (qwen3:8b) under-performs specifically on multi-step orchestration and tool-routing, confirmed by direct side-by-side testing. | Confirmed gap |
| Model upgrade path | gemma4:e4b and gpt-oss:20b identified as viable local upgrades on existing hardware; qwen3.6:27b flagged as too large for this machine. | Identified, untested live |
| Hardware ceiling | Fanless design creates a real thermal-throttling risk under sustained load; 24GB unified memory caps which models are viable at all. | Known constraint |
| System audit | A full frontend/backend/performance/end-to-end audit has been scoped but not yet executed to completion. | Scoped, pending |
| Demand for a paid product | No external users, no paid pilots, no validated demand signal exists yet. | Not yet tested |

This table is the actual starting line for the roadmap in Section 5. A commercial plan that skips past these gaps is planning around a product that doesn't exist yet.

## 3. Product definition — version one scope
Version one is scoped deliberately small: reliable, trustworthy automation of repeatable small-business workflows. Not a platform, not an ecosystem — a tool that does a defined set of things well.

### 3.1 Core features — must have
1. Natural-language task input — state a goal, the agent breaks it into steps.
2. Google Workspace integration (Gmail, Drive, Sheets, Calendar) — the primary surface small-business repeatable work happens on.
3. Document and file handling — read, sort, and extract data from PDFs, receipts, and invoices.
4. Approval gates before any risky action — sending mail, deleting files, or anything else consequential requires explicit confirmation.
5. A plain-language action/audit log — a visible history of what the agent did and why.
6. A live status window — running, completed, waiting-on-approval, and failed tasks, with a real reason shown for failures.
7. A kill switch — stop all in-progress automation immediately.
8. Recurring and scheduled workflows — "do this every Monday," not only one-off requests.
9. Turnkey onboarding — no API keys, no config files, no technical setup required from the customer.
10. Clear failure reporting with retry — a failed step states what broke rather than stalling silently.

### 3.2 Explicitly out of scope for version one
Each item below is a real idea from earlier product notes. Each is excluded here on the same basis: it is not required to prove the core value, and attempting it now would risk the reliability of what does need to work.
- Multi-provider BYOK model routing across several paid AI services.
- Embedded cross-device mesh networking (Tailscale/WireGuard-style, behind a single join token).
- OS-level device control beyond the local automation sandbox.
- Productized access to the Atlas trading/backtesting engine.

Reintroduce any of these only after version one is proven reliable with real users. Each is a project in its own right and deserves its own scoping pass, not a line item on this roadmap.

## 4. Target market and positioning

### 4.1 Primary target
Small-business owners and operators with repetitive digital administration — sorting files, extracting data, drafting routine replies, updating spreadsheets — and no dedicated IT or automation staff. Candidate segments: contractors, small professional service firms, small hospitality operators, regional suppliers.

### 4.2 Positioning
The pitch is outcomes, not architecture. "An assistant that does your paperwork" beats "multi-agent orchestration" for this audience. Technical language belongs in documentation, not the pitch.

### 4.3 What is not being sold, and why that is stated up front
Dourmouse is not positioned as a trading tool, an investment product, or a general-purpose chatbot. Mixing an automation product with anything finance-adjacent invites regulatory and trust complications that a pre-revenue product does not need to take on.

## 5. Validation-first roadmap
Three phases, in strict order. Each phase has an explicit gate. The next phase does not start until the current one's gate is met — this mirrors the same evidence-before-action discipline used throughout this project's trading research.

**Phase 1 — Prove it works for one user (you)**
- Complete the full Dourmouse system audit (frontend, backend, performance, end-to-end).
- Complete the model upgrade and confirm the reliability gap is actually closed, not just theoretically better.
- Run the ten core features (Section 2.1) against real personal workflows for a sustained period, not a single demo session.
- Gate to Phase 2: the ten core features work reliably, without supervision, across real use for at least two continuous weeks.

**Phase 2 — Prove it works for a handful of real outside users**
- Recruit a small number of real early users (single digits, not the earlier blueprint's twenty) from people with a genuine, specific repetitive workflow — not friends humoring a demo.
- White-glove onboarding — set it up for them personally, watch what actually happens.
- Track every failure, every point of confusion, every moment they didn't trust the agent enough to approve an action.
- No payment collected in this phase. The objective is signal, not revenue.
- Gate to Phase 3: at least one real user reports a measurable time saving and would be upset if the tool were taken away.

**Phase 3 — Introduce monetization**
- Only after Phase 2's gate is met. Pricing and packaging are informed by what real users in Phase 2 actually valued, not by a plan written before anyone used the product.
- Start narrow: a small number of paying pilot customers before any broader go-to-market motion.

## 6. Business model — hypotheses, not decisions
Nothing in this section is a commitment. Each option is a hypothesis to test against real Phase 2 users, not a pricing page to publish.
- **Option A — Simple monthly subscription:** A flat monthly fee for the core automation product. Simplest to explain to a non-technical buyer; easiest to test.
- **Option B — Done-for-you setup plus subscription:** A higher-priced onboarding/configuration fee for customers who want it installed and configured for them, plus an ongoing subscription. Matches the "no technical setup" positioning directly.
- **Option C — Early-access lifetime license:** Referenced in earlier product notes as a way to reward first real users. Worth testing only as a Phase 2 relationship-building tool, not as the actual long-term pricing model — a lifetime license does not fund ongoing development.

Do not select a final model until Phase 2 produces real evidence about what a customer actually values and what they would pay for it.

## 7. Go-to-market — first motion only
This section covers the first handful of customers, not a scaled acquisition channel. A full GTM machine is premature before Phase 2's gate is met.
- Direct, personal outreach to a small, specific list of small businesses with an identifiable repetitive workflow — not a broad cold campaign.
- Lead with a working demonstration of their own workflow, not a pitch deck — the same "show, don't tell" principle already validated as effective for the earlier AI-agency business idea discussion.
- No paid advertising, no broad content marketing, no scaled anything until Phase 2 produces a real success story to point to.

## 8. Risk register

| Risk | Why it matters | Mitigation |
|---|---|---|
| Single point of hardware failure | The whole system currently runs on one fanless laptop with a known thermal ceiling. | Phase 1 gate explicitly requires sustained-load testing before anything customer-facing. |
| Automating access to real business data | A small-business customer's email, files, and calendar are sensitive. A mistake here damages trust immediately and possibly irreversibly. | Approval gates on every risky action are a hard requirement, not optional, in Section 2.1. |
| Solo builder, limited hours | Development, support, and onboarding all fall on one person alongside schoolwork. | Deliberately small Phase 2 cohort (single digits) so support load stays manageable. |
| Unvalidated demand | No external evidence yet that small businesses will pay for this, at any price. | Phase 2 exists specifically to generate this evidence before money or scaled effort is spent. |
| Scope creep back toward the original blueprint | Mesh networking, multi-provider routing, and OS control are compelling ideas that could quietly re-enter scope before they're needed. | Section 2.2 exists as an explicit, standing exclusion list. |

## 9. Success metrics and kill criteria
Applying the same standard used throughout this project's other research: a negative result, honestly reached, is a successful outcome of a phase — not a failure of the plan.

### 9.1 Phase 1 success metrics
- Ten core features function without supervision across two continuous weeks of real personal use.
- No unrecovered failure in the audit's performance testing under realistic sustained load.

### 9.2 Phase 2 success metrics
- At least one real outside user reports a measurable time saving.
- At least one real outside user would object to losing access to the tool.

### 9.3 Kill criteria — when to stop or rescope, not push through
- If Phase 1's reliability gate is not met after the model upgrade, the correct response is further debugging, not lowering the bar to move on anyway.
- If no Phase 2 user reports genuine value after honest, sustained use, that is evidence the product is not solving a real problem yet — not evidence to onboard more users hoping the next one reacts differently.

## 10. Immediate next steps
1. Complete the full Dourmouse system audit (already scoped in the separate audit document).
2. Complete and verify the model upgrade against the audit's own before/after benchmark.
3. Run Phase 1 for a real two-week period before any conversation about outside users begins.
4. Revisit this document after Phase 1's gate is met — do not draft Phase 2 recruitment materials before that point.

---

*End of document. This plan is intentionally conservative in scope. Ambition belongs in the excluded-features list waiting for its turn — not in this quarter's roadmap.*

---

## ADDENDUM — Desktop verification pass (2026-08-12)
Saved verbatim from the user. One factual correction verified against the shared repo on this machine:
- **"Built in Next.js" is incorrect.** The engine is Python (`dourmouse/webui.py`, stdlib HTTP server) with static HTML UI (`ui/index.html`, `product.html`). SSE streaming is real (webui.py delivers API + SSE + RBAC + SQLite). No `package.json`/`next.config` exists anywhere in the checkout. `UPGRADE_PLAN.md` explicitly rejected a framework rewrite. If a Next.js build exists elsewhere it has never been mirrored to the shared repo.
- Feature-gap verification: Gmail + read-only Calendar exist in `google_services.py`; **Drive and Sheets are not implemented**. Turnkey onboarding (feature 9) is a build target, not current reality (requires Ollama + `.env` + venv today). Recurring workflows (feature 8) are partial — fixed internal poll tables, not user-defined schedules. PDF/receipt extraction (feature 3) unconfirmed in code.
- See `reports/DOURMOUSE_SCALING_PLAN.md` for the execution plan built on this document.
