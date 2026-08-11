# PRODUCT DECISION — convergence record

Status: **RATIFIED** (desktop-atlas, feed id 1117) — 7/7 with three
amendments. Companion to `reports/PRODUCT_DEBATE.md` (the A/B/C framework and
forced binaries) and `reports/PRODUCT_PLAN.md` (the 7-phase execution plan).

## Ratification amendments (feed id 1117)

- **A1 (FB1) agreed** — sequencing, not selecting: A is the business, C's
  decision cards are the interface, B stays gated on evidence.
  PRODUCT_PLAN.md already sequences P2/P3/P4 ahead of P6 (the paper gate).
- **A2 (FB2) agreed** — T11 is the release gate, not a blocker on product
  work. Everything through P5 is buildable before the human Gateway login.
- **A3 (FB3) agreed, with the boundary drawn hard** — the registry is the B2B
  balance sheet for AUDITED DATA; the signal math and locked legs stay ours
  forever. Data yes, signals never.
- **Additions folded in:** (1) the decision-card generator must render the
  terminal state "REJECTED AT GUARDRAIL X" from day one; (2) "DO NOTHING
  TODAY, AND HERE'S WHY" is a first-class calm state, not dead space.

## Fight-back that still stands (from the binaries)

- **FB1 — A cannot ship without C's artifact.** A graveyard with no visible
  reasoning is a dataset, not a product. The decision card is the product
  surface of the Lab. We are not choosing one of three products — we are
  choosing the ORDER: A is the business, C's cards are the interface, B stays
  gated on evidence.
- **FB2 — the trust definition makes T11 the release gate, not a product
  decision.** "I'd trust my own $100 to it" requires the paper cycle (T11).
  The one-screen + decision cards can be built and previewed now regardless of
  the human Gateway login; product work must not wait on the human step.
- **FB3 — the registry is the asset.** Reasoning is the demo; the audit-trailed
  data registry is the balance sheet — a B2B licensing line the retail
  discipline product alone cannot provide.

## Proposed verdict (7 points)

1. **Day one = A (The Lab)** — shipped as ONE screen: *hold / do today / why*,
   every action terminating in action-or-explicit-non-action.
2. **The graveyard is the spine** — kill-history + post-mortems + permutation
   p, searchable.
3. **Decision cards are the user-facing feed** (C's artifact, shipped inside
   A): signal → mechanism → data → p → outcome. Raw relay chatter stays
   internal.
4. **Tabs move behind the Lab door** — one screen on load, audit reachability
   preserved.
5. **Guardrails go into the golden regression suite** (a guardrail trip =
   release blocker). Human-in-the-loop at launch; auto-execution under hard
   caps designed in, flipped in v2 after the paper cycle proves it.
6. **Commercial definition:** "I'd trust my own $100 to it." Proof gate = T11
   paper fill.
7. **The registry is an asset, not a byproduct** — audit-trailed data is a B2B
   line.

## Next concrete artifact (independent of the human step)

The one-screen product UI + decision-card generator in the Jarvis design
language, previewable in the hub (:8791). Starts on ratification or amendment.

## Schemas (laptop, ratified record)

### Graveyard store — desktop P2 lives at `graveyard/` (index.json + data/*.json)
Entry fields: `id, name, family, status, killed_date, headline, mechanism,
forced_participant, perm_p, live_window, post_mortem, data_refs, tested_by`.
Index carries `schema_version, built, count, families, status_counts`.

### Decision card — `scripts/decision_cards.py` → `dourmouse/decision_cards.json`
```json
{"id":"dc-...","ts":"...","signal":"usdjpy_drift_k1","asset":"USDJPY",
 "direction":"LONG","size":0.1,"mechanism":"...","forced_participant":"...",
 "data_refs":["USDJPY_D1"],"p_value":0.0007,
 "outcome":"FILLED|REJECTED_AT_GUARDRAIL|NO_TRADE|PENDING_APPROVAL",
 "guardrail":null,"ledger_ref":null,"chain":["signal","mechanism","data","p","outcome"]}
```
Calm state: `{"outcome":"NO_TRADE","reason":"DO NOTHING TODAY — here's why: ..."}`

## Build split (parallel, both land on main)
- **Laptop:** one-screen product UI + decision-card generator (Jarvis design,
  :8791) — DONE, previewed live (render + chain + approve verified).
- **Desktop:** P2 graveyard assembly — DONE (17 entries, index.json).
