# Paper-Trading Playbook — strategies worth forward-testing

Status: written after the full strict-testing programme (~1,300 strategies tested,
all kills documented in reports/). Exactly TWO strategies are worth paper trading.
Everything else in the programme is confirmed dead or below costs.

Inventory, one line each:
- Seasonal commodities (312-cell clean test): DEAD — below costs, 0/28 significant.
- Intraday news drift (1h-24h, all pairs): DEAD — overfit (0/24 strict battery).
- Cointegration pairs (FX/metals, 21 pairs): DEAD — 0/21 pass.
- Witching / LETF decay / window dressing / Russell / TIPS-gold: DEAD (Campaign-30).
- Dollar-basket under-reaction (Family E): DEAD at Stage 1 — surprise has no predictive power.
- D1 next-day news drift, basket pairs: DEAD (walk-forward permutation fails).
- **Dual momentum (Antonacci): the programme's ONE full PASS — paper trade.**
- **USDJPY D1 news drift: 4/6 strict gates, on probation — paper trade as a forward test.**

---

## Strategy 1 — Dual momentum (the one full PASS)

**Verdict:** only strategy in the programme to pass all six strict gates + the full
robustness battery (cost ladder 0x/2x/5x, both holdout halves, sub-periods). The
null-signal control (random ranking) FAILS, proving the momentum ranking itself is
the edge, not the machinery. Buy-and-hold SPY and IEF fail the same gates.

**Why it works (honest mechanism):**
- Momentum is the most robust documented anomaly in finance (Jegadeesh & Titman 1993;
  Asness, Moskowitz & Pedersen 2013). Markets under-react to good/bad news; the drift
  takes months to fully play out. Unlike most anomalies, it survived publication.
- The ABSOLUTE filter (only assets with positive 12m return are eligible) is the
  crash-protection engine: it holds cash through bear regimes (it was in cash through
  most of 2022 while SPY fell ~18%). This regime-switching is why it beat buy-and-hold
  on a risk-adjusted basis.
- No single forced participant — it is a behavioral/risk-premium effect, the
  programme's one exception to the forced-flow rule, and it earned the exception
  empirically. Persistence is a judgment call, not a law: assume finite life and keep
  re-evaluating annually.

**Tested parameters (from scripts/dual_momentum_test.py):**
- Universe: SPY, EFA, VNQ, GLD, DBC, IEF, SHY (7 ETFs)
- Lookback: 12-month total return; rebalance: monthly (1st trading day)
- Absolute filter: eligible iff own 12m return > 0
- Rank eligible by 12m return; hold TOP-1 (k=1), equal weight
- If nothing eligible: 100% SHY (cash)
- Cost model tested: 0.5 bps/trade + 0.5%/yr expense drag; passes at 2x and 5x too
- IS 2007-2017, blind holdout 2018-2026: +2.12%/mo, t=4.51, p=0.001; bootstrap
  P(mean<=0)=0.0000; positive in both holdout halves

**Execution steps (paper):**
1. Venue: IBKR paper (fractional ETF shares available; T212 cannot cleanly hold this
   ETF universe and has no fractional US stocks at $100 size).
2. On the 1st trading day of each month, pull monthly closes for the 7 ETFs
   (yfinance or IBKR; script scripts/dual_momentum_test.py already fetches them).
3. Compute each asset's 12m total return = close[t] / close[t-12] - 1.
4. Drop any asset with 12m return <= 0 (absolute filter).
5. Rank the survivors by 12m return; the target portfolio is 100% in the #1 asset.
6. If no asset survives, target = 100% SHY.
7. Rebalance to target weights, charging ~0.5 bps/trade in your ledger. Turnover is
   low (1-2 trades/month); most months the top asset is unchanged.
8. Record each month's decision in a paper ledger: date, per-asset 12m returns,
   target weights, actual fills, fees.
9. Evaluation gate after 12-18 months: compare vs SPY buy-and-hold on (a) total
   return, (b) max drawdown, (c) months-in-cash. It should beat BH on drawdown by
   construction; it must not trail meaningfully on return.

**Why it works here but not at every size:** the strategy needs whole-ETF sizing.
At $100, one share of SPY (~$560) is impossible without fractional shares — that is
why it is paper-traded on a fractional-capable venue, not live CFDs.

---

## Strategy 2 — USDJPY D1 news under-reaction drift (on probation)

**Verdict:** 4/6 strict gates. Passes every OUT-OF-SAMPLE gate: holdout t=+3.78
(p=0.001), walk-forward permutation p=0.012, bootstrap P(<=0)=0.002, outlier-trim
>0, positive 5/5 holdout years, vintage-audited clean (28/28 as-published prints).
Fails only the IN-SAMPLE gates (IS t=1.14) because the effect did not exist
2016-2021 — it is a 2022+ regime phenomenon. Not tradeable yet; the forward-test
decides. Paper trading this strategy IS the test.

**Why it might work (the hypothesis):**
- Informed under-reaction: a macro print (NFP, CPI, ISM...) is a genuine surprise to
  the whole market. The full information content takes time to propagate into every
  dollar instrument, and stop-losses / margin calls / hedger exits force
  counterparties to transact at the print regardless of price — they cannot wait for
  a better price. Those forced transactors are the other side of the drift.
- It uses information NOT derivable from price (survey consensus), which is why it
  survived where every price-only strategy died.
- Regime note: the effect is real in 2022+ only. Candidate explanation: thinner
  market-making liquidity in the JPY complex after the BoJ shift. Unproven — the
  live ledger decides.

**Tested parameters (ground truth: scripts/fx_strict_battery.py, news_USDJPY;**
**fully rebuilt and verified in USDJPY_news_drift_verification.xlsx):**
- Universe: every US (currency=USD) High/Medium release with numeric actual+forecast
  (9,709 releases, 131 titles in the archive)
- Surprise = actual - forecast (as printed)
- z per release title: (surprise - trailing mean of that title's prior surprises) /
  trailing std; min 20 prior events; std floored at 1e-12 (else no z); z clipped +/-8
- Trigger: |z| >= 0.5; direction = sign(z) (LONG USDJPY if z > 0, SHORT if z < 0)
- Entry: next trading day (code measures event-day close -> next-day close; the
  "next-day open" label is imprecise - includes the overnight gap)
- Exit: next day's close (~1 day hold, no stop)
- Cost: 1 pip round trip (~0.008% at current USDJPY levels)

**Execution steps (paper/forward-test):**
1. The daily task (NewsDriftForward, registered in Windows Task Scheduler) already
   does this automatically: it reads the live events archive, recomputes the
   expanding-window surprise z per title with zero lookahead, flags qualifying
   events, and records the next-day move on all 5 USD pairs into
   market-data/news_drift/forward_ledger.csv.
2. If trading it by hand: each US trading day, check the Forex Factory calendar for
   High/Medium US releases. When a print lands, compute surprise and z as above
   (the verification spreadsheet does this live - paste the row in, read the trigger).
3. On a trigger, log the paper fill: direction, entry (next-day open), exit
   (next-day close), 1-pip cost, and the realized net.
4. Do NOT size real money. The ledger is accumulating live-captured, vintage-proof
   evidence (actuals recorded as they print, not backfilled).
5. Evaluation gate: 30-60 more qualifying events across the basket. If the matched
   drift holds positive net (OOS mean > cost) across pairs, graduate to a tiny live
   test. If it is flat or negative, kill it with the clean data in hand.

**Why it is worth paper trading despite failing the battery:** a failing IN-SAMPLE
gate on a regime-dependent effect is a timing problem, not proof of absence; the
out-of-sample evidence is the strongest of anything in the programme, and the
forward-test costs nothing but a scheduled script. It is the only candidate that
uses information (survey consensus) that no price-only strategy can access.

---

## Standing rules for both

- Edge decays. Re-run the selection/battery annually with the window rolled forward.
- Paper ledger must include costs (spread + financing) or the test is meaningless.
- A correct kill is a success. Both strategies have pre-registered kill gates above;
  if they fail, say so plainly and stop.
