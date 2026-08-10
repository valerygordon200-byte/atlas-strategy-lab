# FURTHER STEPS — Vintage Audit + Hogs Roll Check

_2026-08-10 · the two remaining candidates, taken to a verdict_

---

## 1. Vintage audit (USDJPY news drift) — PASSES

**Question:** do the stored event `actual`s match the as-published prints, or are
they revisions traders never saw?

**Method:** sample the most revision-prone releases in the store and compare
against independent as-published sources. BLS/FRED/ALFRED are unreachable from
this network (timeouts/403); BEA and EIA are reachable; famous prints verified
against documented press releases.

**Results — 27 of 28 checks match the as-published print:**

| Release | Store actual | As-published | Revised later to | Verdict |
|---|---|---|---|---|
| GDP Q1 2020 adv (2020-04-29) | −4.8% | −4.8% | −5.0% | MATCH |
| GDP Q2 2020 adv (2020-07-30) | −32.9% | −32.9% | −31.4% | MATCH |
| GDP Q3 2020 adv (2020-10-29) | +33.1% | +33.1% | +33.4% | MATCH |
| GDP Q1 2025 adv (2025-04-30) | −0.3% | **−0.3%** (BEA) | −0.5% | MATCH |
| … 17 more GDP advance estimates (2020–2025) | | | | all MATCH (21/21) |
| NFP Mar 2020 (2020-04-03) | −701K | −701K | −870K→−1.4M | MATCH |
| NFP Apr 2020 (2020-05-08) | −20,500K | −20.5M | −22.1M | MATCH |
| NFP Apr 2021 (2021-05-07) | +266K | +266K | revised up | MATCH |
| CPI May 2022 (2022-06-10) | +8.6% | +8.6% | n/a | MATCH |
| EIA crude week end 4/17/2020 | +15.02M | +15.02M | +15.02M | MATCH |
| EIA crude week end 4/24/2020 | +8.99M | +8.99M | **+10.14M** | MATCH (holds print, not revision) |
| EIA crude week end 5/1/2020 | +4.59M | +4.59M | **+6.31M** | MATCH (holds print, not revision) |

**Verdict: the drift's actuals are as-published, not revision-contaminated.**
The four NFP/CPI checks are the strongest possible test — each was revised
substantially after publication and the store holds the ORIGINAL number. The
EIA April-2020 weeks prove the store is not the current vintage.

**Known data-quality warts (documented, not fatal to the drift):**
- One ADP release (2022-08-31) appears 3× with different actuals (380/268/132)
  — duplicate rows, 0.1% of the drift set. `load_events` should dedupe.
- The `previous` column disagrees with the prior release's `actual` ~70% of the
  time on payroll titles — irrelevant to the drift, which never uses `previous`.

**Status of the USDJPY news drift after this audit:**
- Holdout (2022+): NW t = +3.03, p = 0.001 · walk-forward p = 0.012 ·
  bootstrap P(mean ≤ 0) = 0.001 · survives cost ladder and outlier trim ·
  **vintage audit now CLEARS** (Step 0 of the protocol).
- Still fails the two in-sample gates (t = 1.14, p_is = 0.032): the effect is
  genuinely a 2022+ phenomenon, absent 2016–2021.
- Honest framing: a real, replicable recent-regime edge — not a proven timeless
  one. Tradeable *if* the regime persists; that is the strongest statement the
  data supports. NOT a 6/6 PASS under the pre-registered protocol.

---

## 2. Hogs August SHORT — KILLED by the roll-convention check

**Question:** is the August short a real seasonal or an artifact of the
continuous front-month series?

**Method:** detect the contract roll (large splice gap, ~10th business day of
each month) and recompute the monthly return using only prices BEFORE the roll
— what a trader holding the front contract actually captures.

**Result — the entire effect is the roll gap:**

| Measure | RAW continuous | PRE-ROLL (real) |
|---|---|---|
| Aug return | −13.9% (t = −8.08, 92% yrs down) | **+0.05% (t = 0.05, 38%)** |
| Roll-gap contribution | | −14.0% of the −13.9% |

**Mechanism (confirmed in data):** August is the most backwardated roll month
in hogs — mean roll gap **−10.0%** (next closest: October −3.8%). The
biological calendar: pigs farrowed Feb–Apr reach slaughter weight Aug–Oct;
supply swells into autumn while grilling-season demand fades after July 4th →
cash hogs fall → deferred contracts trade at a deep discount to the front
August contract → the Aug→Sep splice drops ~10% every August. The continuous
series books that basis as a phantom return; a short CFD position does not
capture it (the broker rolls at market with a basis adjustment).

**Same test, all other seasonal survivors — every one is a roll artifact:**

| Seasonal | RAW | PRE-ROLL | Verdict |
|---|---|---|---|
| Hogs Apr LONG | +8.7% (t=4.5) | −1.5% (t=−1.4) | artifact |
| Hogs Dec LONG | +5.1% (t=3.1) | −0.8% (t=−0.7) | artifact |
| Gasoline Sep SHORT | −7.2% (t=−3.5) | +0.5% (t=0.5) | artifact |
| LiveCattle May SHORT | −3.8% (t=−3.2) | +0.1% (t=0.5) | artifact |
| FeederCattle May LONG | +4.1% (t=3.6) | +0.2% (t=0.3) | artifact |
| Corn Jul SHORT | −3.8% (t=−1.7) | +1.4% (t=1.0) | artifact |
| NatGas Dec SHORT | −5.0% (t=−1.3) | −1.6% (t=−0.5) | dead either way |

**Verdict: the entire commodity-seasonal program — including the prior study's
headline trades — is a roll artifact of the unadjusted continuous series.**
This is exactly the protocol's roll-artifact trap: "if seasonality only appears
in one construction, the roll method is generating it." The strict battery's
walk-forward permutation gate (p = 0.076 for hogs Aug) was already signalling
the weakness; the mechanism check finished the job.

**Correction for the record:** the earlier "5/6 gates" for hogs Aug was testing
an artifact. The seasonal catalog in `strategy_catalog.json` is void and should
not be traded.

---

## Bottom line

- **USDJPY news drift:** vintage audit clears (27/28 as-published). Remains
  4/6 gates — a real 2022+ regime edge, the best candidate in the entire
  research programme, but not a proven timeless one.
- **Hogs Aug (and all seasonals):** dead — roll artifacts, mechanism confirmed.
- **Nothing is tradeable yet.** The news drift is the only candidate with a
  path forward: forward-test it on a demo account and treat it as a
  regime-contingent edge, not a law.
