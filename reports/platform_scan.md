# Platform Strategy Discovery — CAN Brief

Date: 2026-08-10 · Scope: QuantConnect / TradingView / verifiedinvesting / myfxbook
Goal: a short, honest list of strategies eligible for backtesting. Zero is an acceptable outcome.

---

## Platform sweep results

### myfxbook.com — nothing eligible
Performance-tracking site for black-box EAs. No visible strategy logic anywhere; stats are
self-reported and survivorship-biased (losing EAs get deleted). Skipped discovery entirely,
per the brief. **Not eligible by definition.**

### verifiedinvesting.com — nothing eligible
Not a strategy library at all: a vendor selling courses, live trading rooms, and trade
alerts. Its headline "Verified Performance Leaderboard — WIN RATE: 85.29%" is self-reported
marketing with no code, no fill logic, and no independent audit; Reddit threads on their
swing-trade alerts are consistent with marketing-style performance claims. Nothing here can
be backtested without independently reconstructing logic from prose, which the site does not
disclose. **Not eligible.**

### tradingview.com — nothing eligible directly, but corroborates candidate #1
- `Engle-Granger Cointegration + ADF Z-Score (Pairs Trading Tool)` (fxmotif): **invite-only,
  paid** (Gumroad) → fails the eligibility filter (undisclosed/gated code). The *described*
  mechanism (rolling OLS hedge ratio, ADF on spread residuals, z-score ±2 entry, ±0.5 exit)
  is identical in spirit to the fully-open QuantConnect reference below, so it adds no
  independent candidate — it corroborates the pairs-trading mechanism.
- `Z-Score Stat Trading` (bratan2), `Z-Score Pairs Trading` (Fleisi): free and open-source
  Pine, but Pine backtests are repaint-prone and their community track records are not
  independently verifiable. Mechanism = same pairs z-score family.
- No other strategy found on TradingView passes all three filter criteria (mechanism
  disclosed AND codeable, data free, not in graveyard).

### quantconnect.com — 2 candidates pass the filter
The QuantConnect community leaderboard was NOT used as evidence (its rankings are
self-reported popularity). The candidates below come from the open Research/Strategy
Library, where the code is inspectable and the mechanisms are fully disclosed.

---

## Candidate 1 — Cointegration pairs trading (statistical arbitrage)

**SOURCE:** QuantConnect Research — "Intraday Dynamic Pairs Trading Using Correlation And
Cointegration Approach" (research/15347); George J. Miao method. Fully open, code published
in the research note.

**MECHANISM (exact, codeable):**
1. Universe: stocks from a single sector (bank sector in the reference; 20 names → 190 pairs).
2. Screen 1 — correlation: keep pairs with rolling correlation ≥ 0.9.
3. Screen 2 — cointegration: OLS hedge-ratio regression `A = α + β·B + ε`, then ADF unit-root
   test on the residual; keep pairs with cointegration p ≤ 0.05.
4. Trading signal: residual z-score. Enter when z < −2.33 (long spread: long A, short β·B)
   or z > +2.33 (short spread). Exit at z ≈ 0.5. Stop at ±4σ of the residual.
5. Rolling 3-month training / 3-month trading windows, re-selected each cycle.
6. Market-neutral: no directional market bet.

**DATA REQUIRED:** daily OHLC is sufficient for a first test (the reference uses 10-min data,
but the mechanism is frequency-agnostic). Instruments: our 5 FX pairs + gold/silver would be
the natural first universe — we already hold all of them locally (Yahoo D1, 2018+). Equities
pairs are also testable via free Yahoo data. **We already have everything needed to test the
FX version.**

**FORCED-PARTICIPANT STORY:** No (this is not a forced-flow strategy). But it is the right
kind of edge for this project: it profits from *spread reversion*, not directional prediction
— consistent with the programme's core finding that direction is unpredictable while
relative-price structure (volatility, spreads) is not.

**ELIGIBILITY:**
- Mechanism disclosed & codeable: **PASS** (full logic + code published).
- Data free & accessible: **PASS** (Yahoo D1; already local for FX/metals).
- Not in graveyard: **PASS** (stat-arb spread reversion was never tested here; the graveyard
  kills single-instrument Bollinger reversion, not cointegrated spread trading).

**VERIFICATION CHECKLIST (reference implementation):**
- Track record: the QC note's 26.9% CAGR / 3.01 Sharpe is a **backtest on one month of
  10-min data (Sept 2013)** — statistically thin, treat as illustration, not evidence.
- Max DD / trades: not disclosed per variant; flag as unverified.
- Costs: the note does not disclose spread/slippage treatment → numbers are **gross**.
- Backtest/live separation: none shown — this is a research illustration, not a track record.

**CONCERNS:** One-month backtest, unknown costs, single sector. Pairs trading is capacity- and
cost-sensitive; at $100 with FX spreads the z=2.33 threshold must clear round-trip costs
(≈1 pip on majors is fine). Cointegration breaks down — the rolling re-selection handles this
but must be tested honestly. Also note: FX majors pairs are the most-traded, most-arbitraged
corner of markets — the real question is whether a *daily* stat-arb on 5 majors survives at
all. The classic Gatev result is on equities, not spot FX.

**RECOMMENDED PRIORITY: HIGH.** Fully disclosed, immediately testable with local data, and
the only candidate family whose profit source (spread reversion, market-neutral) is
compatible with what this project has learned actually persists. The first decisive test:
run the exact z-score machinery on our 5 FX pairs + metals, 2018→2026, through the strict
battery, on **roll- and spread-adjusted** returns.

---

## Candidate 2 — Dual / absolute momentum asset allocation (Antonacci)

**SOURCE:** QuantConnect forum implementations ("Dual Momentum with Out Days" #10039,
"Accelerating Dual Momentum" #9703) + the published primary source: Antonacci, *Dual
Momentum Investing* (2012 paper / 2014 book), independently reviewed (Robot Wealth; quantpedia
replications). Logic is fully public and codeable.

**MECHANISM (exact, codeable):**
1. Universe: several asset classes (e.g. equities, bonds, gold, commodities via ETFs).
2. Each month: compute 12-month total return for each asset.
3. **Absolute momentum filter:** if an asset's own 12-month return < 0 (or < risk-free),
   it is excluded — the crash-protection half.
4. **Relative momentum ranking:** among survivors, hold the top-1 or top-2 by 12-month
   return; if nothing has positive absolute momentum, hold cash/short-term bonds.
5. Rebalance monthly. Low turnover (~12 trades/year).

**DATA REQUIRED:** monthly closes on ~6–10 ETFs (SPY, IEF/TLT, GLD, DBC, etc.) or the
equivalent index data. Free via Yahoo. **Not currently local** — needs a one-time fetch
(Yahoo D1 for ~10 tickers, 2008+). Cheap and free.

**FORCED-PARTICIPANT STORY:** No forced participant. The mechanism is trend + risk-off
filtering, not inelastic flow.

**ELIGIBILITY:**
- Mechanism disclosed & codeable: **PASS** (fully public).
- Data free & accessible: **PASS** (Yahoo ETFs).
- Not in graveyard: **PARTIAL — flag.** The graveyard kills *single-instrument time-series
  momentum* and *cross-sectional momentum on FX pairs*. Dual momentum is multi-asset
  cross-sectional momentum with an absolute-momentum cash filter — a different family
  (asset allocation, monthly, with documented crash protection) but it IS momentum, and
  momentum decay post-publication is a real prior. The brief explicitly lists it as a
  priority candidate, so it is reported — with the decay concern stated.

**VERIFICATION CHECKLIST (external):**
- Track record: Antonacci's paper/backtests span decades (1920s–2010s for some variants) and
  have been independently replicated (Robot Wealth, quantpedia) — this is the best-externally-
  tested candidate on the list.
- Max DD: documented as materially lower than buy-and-hold due to the cash filter (reported
  figures vary by variant; not re-stated here to avoid unverified precision).
- Trades: ~12/year → decades of monthly observations, adequate.
- Costs: published backtests are mostly gross; monthly turnover makes costs small but real.

**CONCERNS:** Post-publication decay (the same edge others now trade); our $100 account can
only buy whole ETF shares, which is fine for SPY/GLD-sized prices. The absolute-momentum
filter means long stretches in cash — low return but the point is drawdown control. Honest
expectation at $100: this is a portfolio-allocation strategy, not a high-turnover edge; its
value to this project is as the crash-protection half of a future allocation, not as a
week-to-week P&L driver.

**RECOMMENDED PRIORITY: MEDIUM.** Testable in an afternoon once ETF data is fetched; worth
one strict-battery pass because of its independent publication record, but its expected
contribution at $100 account size is modest and momentum decay is a live concern.

---

## Candidate 3 — Leveraged ETF rebalancing "decay" — EXCLUDED

**Investigated:** the brief asked to look for strategies exploiting the forced daily
rebalancing of 2x/3x ETFs.

**Finding:** the naive "capture the volatility drag" framing is largely **debunked** in the
current literature reviewed (Return Stacked "Rebalance Drag Myth"; arXiv 2504.20116 shows
the decay view is incomplete; Aptus "Hidden Costs of Volatility Drag" describes the drag as
a *cost borne by LETF holders*, not a free lunch for a counterparty). The real, structurally
forced phenomenon is the *predictable end-of-day rebalancing flow* (the fund must trade a
fixed dollar amount at the close regardless of price) — that is a genuine forced-participant
mechanism, but exploiting it requires shorting LETFs and/or trading the closing auction in
US equities with sub-minute precision — data we do not have, at a capital level where the
borrow/financing costs dominate. **Not eligible: no codeable strategy with accessible data
survives the filter.** Flagged as a mechanism to remember for a future equity-capable setup,
not a candidate now.

---

## Summary

| # | Strategy | Source | Priority | Testable now? |
|---|---|---|---|---|
| 1 | Cointegration pairs trading (stat-arb) | QuantConnect Research 15347 (open code) | **HIGH** | Yes — local FX/metals D1 |
| 2 | Dual/absolute momentum allocation | Antonacci + QC forum implementations | MEDIUM | After one Yahoo ETF fetch |
| 3 | LETF rebalancing decay | (investigated) | EXCLUDED | No — needs US equity close auction + borrow |

myfxbook: nothing eligible. verifiedinvesting: nothing eligible. TradingView: nothing eligible
(paid/invite-only or repaint-prone Pine); the open-source Pine z-score pairs scripts
corroborate candidate #1's mechanism but add no independent candidate.

**Bottom line:** one genuinely promising, immediately testable candidate (cointegration
pairs on our own data, strict battery, spread-adjusted) and one medium-priority, externally
well-tested allocation strategy (dual momentum). Everything else on the scanned platforms
fails the eligibility filter or is marketing.
