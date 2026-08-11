# The Bookshelf — Data Digestion, Factor Weights, Central-Bank Flows, Illiquid Stocks, Timing
Date: 2026-08-11 · Artifacts: `market-data/bookshelf/bookshelf.json` + `weights.json`,
`scripts/bookshelf_build.py`, `scripts/weight_calibrator.py`

---

## 1. How do we digest data into the backtesting engine?

```
RAW SOURCES                                  NORMALIZED / FACTOR SIDE          ENGINE
────────────────────────────────────         ─────────────────────────────    ─────────────────────────
market-data/raw/yahoo/*.csv      ──┐
  COMM_ZS_d.csv … (26 commodities)  ├─►  market-data/normalized/<ASSET>/     load_d1() / load_ratio()
market-data/raw/ibkr, dukascopy     │      _d1/_h1/_m1...parquet             load_big_events()
market-data/raw/yahoo/USDJPY_d.csv ─┘                                        event_net_frame()
                                                                             spread_test.py
market-data/events/events.parquet  ──►  per-title EXPANDING surprise z        fx_strict_battery.py
  (84,498 events, 2015→present)         (min 20 prints, floor, clip ±8)      vol_module.py
market-data/fundamentals/*.csv     ──►  FRED: CPI, rates, yields (8 ccy)     weight_calibrator.py
  (FRED monthly)                        policy_rates.csv (8 ccy, daily)      ──► six-gate battery
market-data/rates/policy_rates.csv ─┘                                        (IS excellence, perm MC,
                                                                             blind holdout, WF, WF-MC)
```

**The honest gap:** today each strategy script has its *own* loader. There is no single
"ingest → validate → registry → engine" layer; the bookshelf is the map that makes that
gap visible, not the fix for it. Every price series passes quality gates on load
(dup dates, non-positive prices, reserved names like `CON`, adjusted closes — all
discovered the hard way in this project).

**Digestion rule we now follow:** *asset prices live in normalized/, factor data lives in
fundamentals/+events/+rates/, and the bookshelf JSON records for every asset which factors
it has and which it is missing.* If a factor says `data: MISSING`, the engine cannot use it
and no weight should be believed as calibrated.

---

## 2. The bookshelf (sorted into categories)

`market-data/bookshelf/bookshelf.json` — generated from actual disk contents, nothing
invented. Categories:

| Category | What's on the shelf |
|---|---|
| Physical & Commodities | GOLD, SILVER, OIL, GSR + 26 raw commodity futures series (grains, softs, livestock, metals, energy) |
| FX | 12 pairs (7 USD majors + 5 crosses) |
| Equities & Indices | SP500, NDX, IPO universe (844 names, 2020–25, adj-close quality-gated) |
| Digital | BTCUSD |
| Rates & Macro (factor side) | policy rates + yields + CPI (8 currencies), 84.5k-event calendar, WTI (FRED) |

Each asset card lists: price data (file, bar count, coverage), its **factors**, each
factor's mechanism participant, data availability, design weight, historical weight
(where calibratable), and final blended weight.

---

## 3. The weighting system — "weights from price charts"

**Method (reproducible, in `weight_calibrator.py`):** for each asset, regress monthly
returns on its available factors (standardised OLS, IS 2016–21 / OOS 2022–26):
- **historical weight** = |standardised beta| / Σ|betas| (the factor's share of price
  movement — literally read off the price charts);
- **design weight** = mechanism importance, pre-registered per factor (forced-participant
  strength);
- **final** = 0.4·design + 0.6·historical, renormalised.

| Asset | R² | Weights (final), largest first |
|---|---|---|
| GOLD | 0.27 | usd_basket .38 · **central_bank_net_buying .29 (NO DATA)** · real_yield .17 · policy_rate .10 · cpi_surprise .06 |
| SILVER | 0.25 | usd_basket .39 · GSR reversion .23 · industrial_demand .19 (NO DATA) · real_yield .10 |
| OIL | 0.09 | policy_rate .36 · OPEC regime .21 (NO DATA) · usd_basket .21 · inventory_surprise .13 · API .08 |
| USDJPY | 0.51 | usd_basket .42 · **news-drift .18 (the tested edge)** · risk_regime .17 · rate_diff .15 |
| EURUSD | 0.78 | usd_basket .48 · rate_diff .18 · risk_regime .14 · cpi surprises .10 |
| GBPUSD | 0.65 | usd_basket .51 · rate_diff .16 · risk_regime .14 |
| AUDUSD | 0.72 | usd_basket .40 · china_demand .20 (NO DATA) · commodity_link .16 · rate_diff .13 |

**What this honestly says:**
1. **The USD level is the dominant factor for everything** — and for the FX pairs this is
   partly circular (each pair *is* a member of the basket). The non-circular reading: the
   dollar is the system's single most important priced variable; a genuine "USD factor"
   trade would be DXY/currency-basket execution, which we have.
2. **Rate differentials and CPI surprises get small weights** — the monthly lens washes out
   the 1-day drift (the drift's whole edge is next-day). Not "unimportant" — *wrong
   frequency for monthly calibration*. The drift's own battery (OOS t 3.78) is the right
   evidence for it, and its design weight (0.40) keeps it prominent.
3. **OIL: US policy rate .36** is the biggest calibrated factor (t 3.07) — but its sign
   flips OOS; flag, don't trust blindly.
4. **The (NO DATA) factors carry pure design weight** — that's the honest way to say "we
   believe this matters but cannot yet prove it on our data."

---

## 4. Central banks: are they buying? Are they selling?

**The facts (well-documented, not from our data):** since 2022 central banks have been
massive **net buyers** of gold — 1,000+ tonnes/yr, the strongest buying streak on record,
led by China (PBoC), Poland, Turkey, India, and a long tail of EM central banks; gold is
now ~1/6 of EM reserves vs ~1/10 a decade ago. They are price-insensitive by design (reserve
diversification away from USD; sanctions-driven de-dollarisation), which is exactly the
"forced participant" pattern this project's whole thesis says matters.

**Where this sits in our system:** `central_bank_net_buying` is GOLD's single largest
design weight (0.35 → 0.29 final), and it is the **#1 data gap on the whole bookshelf** —
`data: MISSING`. We have nothing on the drive to measure it.

**Can we fix it?** Yes, with free sources: World Gold Council monthly central-bank gold
reserve changes (needs an account) or national CB disclosures + IMF IFS monthly series
(PBoC, RBI, NBP, TCMB all publish). Assembling a clean 2015→present monthly series is a
1–2 session data job, then the calibrator can give it a *real* weight instead of a design
one, and the forward ledger can watch for demand-rhythm shifts (buying tends to cluster
after price weakness — a useful timing input). **Recommendation: this is the single highest
value data addition available to us.**

---

## 5. Illiquid stocks — the nuances, and can we use them?

The IPO universe (844 names) is our laboratory; we already learned the hard lessons:

| Nuance | What it does | Evidence from our own work |
|---|---|---|
| Split/raw-price contamination | A raw close series shows fake −90% "crashes" on split days; a short "earns" +900% | Lockup test: fake OOS +19.8% (t 2.47) → honest −0.10% after adj-close refetch. **This is the #1 trap and it's now a standing data gate.** |
| Stale prices / no trades | Returns cluster at 0 then jump; vol & momentum estimates biased low | Must drop 0-volume days / winsorise before any stat |
| Bid-ask bounce | Negative autocorrelation at high frequency — fake mean-reversion | Flag in any intraday work on these names |
| Thin float / single-holder moves | Price shocks from one large order; index/lockup flows land mechanically | Lockup-expiry shorting was *real in-sample* (t 3.44), **dead OOS** (t −0.15): the mechanism was arbitraged away |
| Delisting/name quirks | `CON.csv` (Windows reserved name) hung our pipeline for hours | Reserved-name + dead-ticker filters are now in the loader |
| Earnings on thin coverage | PEAD-style under-reaction is *stronger* where coverage is thin (literature) | Requires coverage data we don't have; flagged as #23 in campaign-30, not yet testable |

**Can we use it?** Honest answer: the *nuances* are mostly **things that break backtests**
(data integrity), not tradeable edges. The one genuinely usable angle from our own data is
the vol/size result (squeeze → bigger next-day moves) which holds even on thin names — as a
**sizing input**, never direction. The lockup mechanism — the strongest forced-participant
story in equities — is dead OOS, and retail shorting of micro-cap IPOs is impractical
anyway (borrow, spreads). Conclusion: illiquid equities are a data-hygiene trap to manage,
not an edge to hunt, with our current data.

---

## 6. Is our timing good enough?

**For the one living strategy (USDJPY news drift): yes, deliberately.**
- Signal at print (08:30 ET) → entry at that day's close (~17:00) → exit next close.
  Tested exactly this way (close[D]→close[D+1]); ~8 hours of slack, no need to act at the
  second. Timing is conservative by construction and executable by hand or script.
- The faster versions (enter at print, 1h/2h/4h) were tested and **all died** (0/24
  passed). The drift is a *next-day continuation* phenomenon; faster timing never existed.
- The vol forecast (for sizing) is also known at close — no timing conflict.

**Where timing is NOT good enough (honest list):**
1. **k=1 only.** The effect is a one-day phenomenon; k=2/3/5 holds all failed. That means
   execution discipline is the whole game: enter that day's close, exit the next close,
   no drift, no "let it run."
2. **Weekend/financing edge.** Friday events hold over the weekend (3× financing on a live
   account); the backtest's 1-pip cost model excludes it. Small but real at $150.
3. **Dubai-clock reality.** Entry lands after midnight Dubai; a human must place it, or
   automation must exist. The forward ledger measures but does not execute.
4. **No per-contract/futures execution.** Anything roll-dependent (spreads' real economics,
   index-roll front-running) is untradeable on T212 CFDs regardless of timing.
5. **Monthly-factor timing.** The bookshelf's calibrated weights are monthly lens — fine for
   *what matters*, wrong for *when to act*; never trade on them directly.

**Verdict:** for the strategy we have, timing is good enough and was tested honestly. The
timing that *isn't* good enough belongs to strategies that are already dead or
data-blocked — not a fixable gap in the current system.

---

## Where this leaves us
The bookshelf + weights give every asset a real, reproducible importance ordering, and
make the data gaps explicit. The single biggest actionable item: **source central-bank
gold flow data** and give GOLD's top factor a real weight. Everything else in this
document is the map, not the territory — the territory still has exactly one living
strategy, and it's still accumulating its forward ledger.
