# IPO Lockup Expiry — Campaign-30 #8, tested: **DEAD out-of-sample**

**Strategy tested:** SHORT the stock over the window close[D-1] → close[D+2] where
D = the first trading day at/after lockup expiry (IPO date + 180 days, the
documented standard for the overwhelming majority of US IPOs — Field & Hanka 2001
documented ~−1.5% abnormal return at expiry).

**Mechanism (forced participant):** Insiders are legally barred from selling for
the lockup period. When the bar lifts, price-insensitive supply hits the market —
they cannot wait for a better price, they can finally sell at all. This is one of
the most-documented forced-selling mechanisms in finance.

**Bottom line:** The effect was genuinely present in-sample (2020–2023, t=3.44)
but is **flat to negative out-of-sample (2024–2026, t=−0.15)**. The edge has
decayed — the same pattern seen everywhere else in this project: a real, documented
effect that has been arbitraged away since publication. Not tradeable.

---

## Data build (with two real bugs caught and fixed)

| Step | Result |
|---|---|
| IPO lists | stockanalysis.com per-year pages 2020–2025 → 1,886 unique (date, symbol, ipo_price) |
| Universe | 844 non-SPAC IPOs with price history (SPACs excluded; identified by $10 IPO price) |
| Expiry proxy | IPO date + 180 days (biases AGAINST the effect: non-180 lockups + early releases add noise) |
| Prices | Yahoo v8 chart API, daily |

**Bug 1 — raw closes are split-contaminated.** The first fetch saved Yahoo's raw
`close`. 2020–25 IPO names split frequently (SPAC-era + tech), and a raw series
shows a fake −90% "crash" on split day. A short "captures" that phantom crash as
+900%. Scan found **3,967 single-day |move| > 40%** in the corpus. Re-fetched all
symbols with `adjclose` (split/dividend-corrected) — 1,064 files refetched, 12
dead tickers dropped. After the fix the OOS mean fell from a fake +19.8% (t=2.47)
to a real −0.10% (t=−0.15).

**Bug 2 — a file literally named `CON.csv` hangs the whole run.** `CON` is a
Windows reserved device name (the console); opening `CON.csv` opens the console
device and blocks forever. `CON` is a real 2023 IPO ticker. Excluded reserved
names (CON/PRN/AUX/NUL/COM1-9/LPT1-9) from the loader — cost ~2 hours of
wall-clock debugging across two scripts.

**Quality gates applied:** adjusted closes; price floor ≥ $2 at entry (penny
stocks have meaningless prints); window returns winsorized at ±25% (micro-cap
100%+ moves wreck the mean — the median is reported alongside).

## Results — SHORT D-1 → D+2, market-adjusted (SPY), winsorized

| Metric | IS (2020–2023) | OOS (2024–2026) |
|---|---|---|
| n | 406 | 349 |
| Mean (winz) | **+2.68%** | **−0.10%** |
| Median | +1.53% | −0.57% |
| t (winz) | **3.44** | **−0.15** |
| Win rate (short) | 47% | 55% |

Raw (no market adjustment): IS +3.23% (t=4.31) / OOS +0.41% (t=0.59).
Long-side sign-flip control: IS −3.23% (t=−4.31) / OOS −0.41% (t=−0.59) — the
IS short signal is a genuine short effect, not a construction artifact.

## Gate battery (pre-registered)

| Gate | Result | Verdict |
|---|---|---|
| IS mean > 0, t ≥ 2.5 | t = 3.44 | PASS (effect was real 2020–23) |
| OOS t ≥ 2.0 | t = −0.15 | **FAIL** |
| Permutation p < 0.01 (random sign, OOS) | p = 0.566 | **FAIL** |
| Bootstrap P(mean ≤ 0) OOS < 0.01 | p = 0.551 | **FAIL** |
| Random-window control (OOS) | null +1.65% vs actual +0.41%, p=0.026 | weak/ambiguous |
| Cost ladder (OOS): 0/50/100/200 bps | −0.10 / −0.60 / −1.10 / −2.10% | negative at every cost |
| Sub-periods (2024 / 2025–26) | −0.39% t=−0.25 / +0.04% t=0.05 | no stability |
| SPAC subset | +0.10%, t=0.23 | flat |

## Verdict

**The lockup-expiry short is dead out-of-sample.** The 2020–2023 IS sample shows
the residual of the Field-Hanka effect (+2.7% per 4-day window, t=3.44 — it really
was still there), and 2024–2026 shows it gone (t=−0.15, permutation p=0.57, loses
at any cost). This is the cleanest edge-decay pattern in the project: a mechanism
that was real and documented in 2001, competed away by 2024. The window also fails
the practical test — shorting micro-cap IPO stocks at retail (hard to borrow, wide
spreads, no borrow guarantee on a CFD platform) would pay more in friction than the
historical signal ever returned net.

**Kill criteria triggered:** OOS t < 2.0; permutation p > 0.01; bootstrap p > 0.01;
mean net < 2× round-trip cost at any realistic cost.

**Campaign-30 status:** #8 now closed (previously data-blocked; executed with the
documented 180-day standard proxy, which biases against the effect). Tier-1
remaining: #9 (buyback blackout — earnings-calendar assembly needed), #23
(restricted PEAD — coverage data not free), #25 (rate-cycle rotation — cheapest
remaining test).
