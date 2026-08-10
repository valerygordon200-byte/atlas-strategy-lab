# FX Carry Factor — Test Verdict: **FAIL**

**Date:** 2026-08-10 · **Campaign:** the first risk-premium family tested since dual momentum
**Script:** `scripts/carry_test.py` · **Data build:** `scripts/carry_data_build.py`

---

## What was tested

**The hypothesis (mechanism family D — risk premia).** Carry is the classic FX risk
premium: investors earn the interest-rate differential for bearing the risk that the
high-yielding currency depreciates. The forced-flow story: institutional carry books
and hedgers must roll and unwind on schedule regardless of price, and retail accounts
are the structural counterparty.

**The signal.** At each month-end, for each of 13 pairs (7 USD majors + 6 JPY crosses),
position by the sign of the policy-rate differential: long the pair if the base currency
pays more, short if it pays less. P&L per pair-month = price return + carry
(rate differential × days/365) − 1-pip cost. Portfolio = equal weight across pairs.

**The data.** Policy-rate histories for USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD,
reconstructed from the events archive's interest-rate-decision prints (actual = post-decision
level), 2015 → 2026, anchors verified against known history (Fed 0.5→5.5→cuts, BoJ −0.1→1.0,
SNB −0.75→1.75→0.0, etc.). ECB's MRO→deposit-rate conversion applied (the spread changed
over time: 25/40/50/15bp). Pre-2021 RBNZ levels filled from documented history.
Daily closes for all 13 pairs from the local store, month-end grid 2016-08 → 2026-07 (120 months).
**IS window: 2016-08 → 2021-12 (65 mo). OOS: 2022-01 → 2026-07 (54 mo).**

---

## Results (net of 1-pip cost)

| Unit | IS mean | IS t | IS Sharpe | IS win | OOS mean | OOS t | OOS Sharpe | OOS win |
|---|---|---|---|---|---|---|---|---|
| 7 USD pairs | +0.070%/mo | 0.39 | 0.05 | 57% | +0.095%/mo | 0.39 | 0.05 | 52% |
| 13 pairs (+JPY crosses) | +0.083%/mo | 0.81 | 0.10 | 55% | +0.337%/mo | 1.71 | 0.23 | 63% |

**The strict-battery gates:**

| Gate | Requirement | 13-pair result | Pass? |
|---|---|---|---|
| Stage 1 IS excellence | Sharpe ≥ 1.0, win ≥ 60%, t ≥ 2.5 | Sharpe 0.10, win 55%, t 0.81 | **FAIL** |
| IS permutation (randomise carry rank) | p < 0.01 | p = 0.030 | **FAIL** |
| Bootstrap P(mean ≤ 0) | p < 0.01 | p = 0.031 | **FAIL** |
| OOS t | ≥ 2.0 | 1.71 | **FAIL** |
| Sub-period stability (OOS halves) | both positive & t ≥ 2 | 2022-23: t=1.44 · 2024-26: t=1.02 | **FAIL** |
| Null-signal control (random rate ranking) | actual ≫ noise | actual +0.199 vs noise −0.030 %/mo | weak pass — the rank carries *some* signal, but far too small |

**Cost ladder (7-pair, net %/mo):** 0.0× +0.028 · 0.5× +0.023 · 1.0× +0.018 · 2.0× +0.007 · **5.0× −0.024** — dies entirely at 5× spread.

**Decomposition (13-pair):** price leg +0.086%/mo · carry leg +0.076%/mo · OOS price leg +0.165%/mo.
OOS annualised: **+4.0%/yr** gross of broker markup.

---

## Why it fails — the honest read

1. **The IS period (2016–21) had nothing to harvest.** Rates were pinned at zero across
   the G10 — average differentials were ~0.5–1pt, and the strategy returned +0.08%/mo
   (t=0.81). The "edge" only appears OOS (2022+), which is *mechanical*: when the Fed
   pushes differentials to 3–5pt, holding the high-yielder collects the differential by
   construction. That is not alpha; it is interest income wearing a strategy costume.

2. **Even that is marginal at the gates.** OOS t=1.71 (required 2.0), bootstrap p=0.031
   (required 0.01), and **2025 was negative (−0.05%/mo)** — the price leg eats the carry
   in a year when the high-yielder (USD) fell. Carry pays you a small, steady stipend and
   then takes it back in one regime month; the risk premium is real but tiny relative to
   its own volatility at this basket size.

3. **Retail markup makes it worse, not better.** The policy differential is the *gross*
   number. At retail the broker takes a markup on **both** sides of the swap — the USDJPY
   rates already on file (long 0.0082%/night, short 0.0029%/night, both effectively
   charges) show the collectible carry at a retail account is a fraction of the policy
   differential. We modeled policy rates, so the +4.0%/yr OOS **overstates** what a $100
   account would actually receive.

4. **The one genuine finding:** the 6 JPY crosses carry most of the OOS gain (13-pair
   +0.337 vs 7-pair +0.095 %/mo) — the *cross-sectional* spread between high-yielders
   and JPY is where the premium lives. But at t=1.71 with a failing bootstrap, it is
   not distinguishable from noise at the sample size we have.

---

## Verdict

**Carry, as tested (13-pair, policy-rate signal, monthly rebalance, $100 retail): FAIL.
Not tradeable.** It fails every strict-battery gate; the IS edge is absent by construction
(zero-rate era), the OOS gain is mostly mechanical interest income, and retail swap
markup would erode even that. The null-signal control says the *rank* is not pure noise,
so this family is not disproven for all time — a richer signal (carry **change**, not
level; G10 minus EM; longer holds with quarterly rebalance) could be retested later —
but nothing here earns a forward test.

**Added to the graveyard as tested** (notable: this was the first risk-premium family
tested; the programme's only surviving family remains **informed under-reaction**,
USD releases → USDJPY D1, on its live forward ledger).

---

## Files
- `scripts/carry_test.py` — the test (reusable)
- `scripts/carry_data_build.py` — rate-history assembler
- `market-data/rates/policy_rates.csv` — 8-currency policy rates, 2015→2026
- `reports/carry_test_monthly.csv` — 120 monthly portfolio net returns
- `market-data/raw/yahoo/{CADJPY,CHFJPY,NZDJPY}_d.csv` — the 3 newly fetched crosses

*Bug note: an initial run showed +14.8%/mo OOS (t=16.6) — that was a 100× scale bug
(policy rates in percent used as decimals). Fixed, rerun, and the honest result above
is the corrected one. The inflated number was not reported as real.*
