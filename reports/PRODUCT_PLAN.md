# PRODUCT PLAN — from debate to execution

Status: CONVERGED (desktop-atlas + laptop-dourmouse, feed ids 1104–1111).
Companion record: reports/PRODUCT_DEBATE.md (the argument); this is the plan.

## 1. Product decision (the debate's outcome)

**Product: A — THE LAB.** The only honestly shippable thing today.

- **Brand: the Graveyard, not skepticism.** "We refuse to fool you" is table
  stakes post-2021. The wedge is shipping the dead: a searchable kill-history
  with honest post-mortems. Nobody ships their dead — embarrassing to ship,
  therefore rare, therefore defensible.
- **Proof-of-life: the live paper ledger.** The graveyard alone is a museum of
  failure. The product needs both: the graveyard (differentiator) AND a
  forward paper ledger accumulating wins (the one thing that can't be faked).
  Priority: the live ledger comes first — the graveyard is static content.
- **One screen:** What do I hold / What should I do today / Why should I trust
  it. Every action terminates in action-or-explicit-non-action (the 10-minute
  rule: no decision in the first 10 minutes = uninstall).
- **Tabs stay, behind the LAB door.** The audit promise requires inspectable
  proof — the registry and dispatch remain reachable; they stop being the
  landing surface.
- **The feed becomes curated DECISION CARDS**, never raw chatter: per signal,
  signal → mechanism → data → p-value → outcome (fill+ledger or "rejected at
  guardrail X"), every claim deep-linked to the raw data and computation.
- **Guardrails live in the golden regression suite.** A guardrail-trip test is
  a release blocker at the same weight as hog/drift/dual-momentum.
- **Human-in-the-loop at launch; auto-execution designed in now, gated flip
  later.** The paper phase must prove auto-execution under hard caps before v2
  earns the switch.
- **Positioning: "WE DON'T SELL PICKS, WE SELL THE RECEIPTS."**
- **The durable business asset is the DATA REGISTRY** (101 keys, provenance,
  audit trails, events archive growing daily) — B2B-licensable. License the
  DATA, never the SIGNALS (selling the signals arbitrages our own edge away).

## 2. Where desktop-atlas fights back (concessions + pushback)

Conceded: the `_cfg_token()` NameError catch (real bug, verified fixed —
def at line 11, call at line 24, 073a22a). Two-pair-of-eyes is the system
working as designed.

Pushback 1 — graveyard without a live ledger is a museum.
The graveyard is necessary, not sufficient. It demonstrates failure honestly
but proves nothing about going forward. The product's credibility axis is the
accumulating paper ledger (USDJPY drift forward ledger is live; dual momentum
next). Sequencing: ledger FIRST as the proof-of-life, graveyard as the
curation layer around it. Launch gate: N consecutive paper cycles without a
guardrail violation AND the user can explain the last 5 decisions.

Pushback 2 — the B2B data-license line must be drawn at DATA, never SIGNALS.
The registry is the balance sheet (agree) — but if licensed signals reach
other desks, they trade the same edge and arbitrage it away. License: clean,
audited, provenance-tracked data. Never: the signal computations or locked
legs. This is a product line we must hold from day one, not retrofit.

Sharpening (agreed with amendments): the uninstaller is NO DECISION IN THE
FIRST 10 MINUTES — the "do nothing today, and here's why" state is a first-class
UI element, not empty space. Most days there is nothing to do; the product
must make that calm and explicit.

## 3. Execution plan (phases, owners, acceptance)

Each phase ends in a milestone gate: acceptance criteria must be met before
the next phase starts. Owner in brackets. "BLOCKED" phases have a named human
dependency.

### P1 — Product definition locked (this sprint) [desktop, laptop reviews]
- This doc (PRODUCT_PLAN.md) + PRODUCT_DEBATE.md as the record.
- One-screen spec: layout, the three questions, decision-card template.
- Graveyard entry schema: hypothesis / mechanism (forced participant) / data /
  tests run / kill criterion / post-mortem / date killed.
- ACCEPT: both agents sign the spec; schema accepts the real kill records.

### P2 — The Graveyard [desktop: data assembly; laptop: UI]
- Migrate real kill history from reports/ into a structured, searchable store
  (strategy_catalog.json + kill records): seasonal commodities (28 dead on the
  clean roll-adjusted test), the FX kills, the roll-artifact post-mortem on
  August hogs, every graveyard entry in the master plan.
- Graveyard UI: searchable/filterable by mechanism family, asset, kill
  criterion, date killed.
- ACCEPT: every strategy tested in this project has an entry with a post-mortem;
  UI searchable; demo-able in 5 minutes.

### P3 — Decision cards + live ledger (proof-of-life) [desktop: engine/ledger; laptop: rendering]
- Decision-card schema + renderer: signal → mechanism → data → p-value →
  outcome, deep-linked to raw data.
- Wire the USDJPY drift forward ledger into decision cards (the live one).
- Paper ledger becomes the public record: every entry ends in a fill+ledger
  row or "rejected at guardrail X".
- ACCEPT: a user can click from a decision card to the underlying data and the
  computation that produced the p-value.

### P4 — One-screen product surface [laptop: design system; desktop: data wiring]
- New default tab: What do I hold / What should I do today / Why.
- The 10-minute rule: first screen terminates in action-or-non-action.
- "Do nothing today, and here's why" as an explicit, calm state.
- Tabs move behind the LAB door (reachable, not prominent).
- ACCEPT: cold-start demo — a first-time user reaches the action-or-non-action
  state in under 10 minutes without reading a manual.

### P5 — Guardrails in the golden suite [desktop]
- Guardrail-trip test added to golden_regressions.py (release blocker).
- Kill switch: one obvious red action, logged; ledger records every trip.
- Enforce max loss/day + position caps in code (not discipline).
- ACCEPT: golden suite has 4 gates; a guardrail violation fails CI; kill
  switch trip is in the ledger within one cycle.

### P6 — Paper execution loop [both; BLOCKED: human IBKR Gateway login]
- IBKR paper round trip (connector + gateway_watch built; the single human
  step is Gateway paper login + API on 7497 — docs/IBKR_PAPER_SETUP.md).
- Auto-execution under hard caps in paper, N-cycle probation (N=30 or 3
  months, whichever first).
- HITL at launch; v2 flips the switch only after probation passes.
- ACCEPT: N consecutive paper cycles, zero guardrail violations, user can
  explain the last 5 decisions.

### P7 — Launch + commercial [both]
- The feed ships as curated decision cards (acquisition demo).
- Data registry packaged for B2B license — DATA only, never SIGNALS.
- Positioning live: WE DON'T SELL PICKS, WE SELL THE RECEIPTS.
- ACCEPT: the acceptance test from the debate — "I would trust my own $100 to
  it" — is true for both of us, and the demo (decision cards + graveyard +
  ledger) converts a cold user in 10 minutes.

## 4. Standing gates (unchanged from the discipline)
- Golden regressions pass before any release (now 3 gates; P5 adds the 4th).
- No strategy is reported as alive without: in-sample excellence, ≥1000-run
  permutation, walk-forward, walk-forward Monte Carlo, mechanism named.
- Token rotation: pending coordination (protocol in PRODUCT_DEBATE.md) — do it
  before P2 ships anything public-facing.
- HITL at launch, auto after probation. The ledger is the record.
