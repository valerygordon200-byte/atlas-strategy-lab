# Commodity Seasonality Campaign — mass test report

_Generated 2026-08-09 · data 2000-01..2026-08 (Yahoo continuous front-month, back-adjusted) · protocol: selection 2000-2014 |t|>2 lock -> blind holdout 2015+ net of retail-CFD costs (spread+slippage+roll+financing) -> 1000-permutation MC p-value_

## Headline

- Strategies tested: **344** (305 single-month grid, 39 research-named windows)
- Passed selection |t|>2: **45** (expected by chance ~15.7)
- Survived blind holdout net-of-costs (ho_t>2 and p_mc<0.05): **6**
- Positive in BOTH holdout halves: **37**

## Top 50 (ranked by holdout t, 15% financing)

| # | key | label | dir | sel_t | ho_mean | ho_t | win | p_mc | h1 | h2 | T212 |
|---|-----|-------|-----|-------|---------|------|-----|------|----|----|------|
| 229 | HE_8-8 | HE 08 | S | -4.33 | +13.88% | +5.62 | 92% | 0.001 | +12.1% | +15.7% | Y |
| 324 | HE_8-8 | Hogs Aug | S | -4.33 | +13.88% | +5.62 | 92% | 0.001 | +12.1% | +15.7% | Y |
| 323 | HE_4-4 | Hogs Apr | L | 2.44 | +5.70% | +3.24 | 83% | 0.004 | +9.2% | +2.2% | Y |
| 225 | HE_4-4 | HE 04 | L | 2.44 | +5.70% | +3.24 | 83% | 0.006 | +9.2% | +2.2% | Y |
| 306 | NG_12-2 | NatGas winter premium | S | -0.34 | +22.65% | +2.32 | 73% | 0.001 | +11.2% | +32.2% | ? |
| 233 | HE_12-12 | HE 12 | L | 1.30 | +4.70% | +2.01 | 73% | 0.024 | +9.0% | +1.1% | Y |
| 50 | RB_9-9 | RB 09 | S | -2.42 | +5.56% | +1.98 | 64% | 0.011 | +5.9% | +5.3% | Y |
| 60 | ZC_7-7 | ZC 07 | S | -0.68 | +4.86% | +1.76 | 75% | 0.002 | +1.9% | +7.9% | Y |
| 29 | NG_12-12 | NG 12 | S | -0.51 | +10.02% | +1.72 | 64% | 0.002 | +4.3% | +14.8% | ? |
| 74 | ZW_9-9 | ZW 09 | L | 0.33 | +3.08% | +1.69 | 73% | 0.023 | +4.6% | +1.8% | Y |
| 65 | ZC_12-12 | ZC 12 | L | 3.15 | +1.97% | +1.57 | 73% | 0.031 | +0.3% | +3.3% | Y |
| 317 | ZC_12-12 | Corn post-harvest low | L | 3.15 | +1.97% | +1.57 | 73% | 0.028 | +0.3% | +3.3% | Y |
| 226 | HE_5-5 | HE 05 | L | 0.75 | +2.97% | +1.48 | 67% | 0.048 | +3.8% | +2.1% | Y |
| 223 | HE_2-2 | HE 02 | L | 2.79 | +3.54% | +1.38 | 58% | 0.025 | -2.2% | +9.3% | Y |
| 322 | HE_2-2 | Hogs Feb | L | 2.79 | +3.54% | +1.38 | 58% | 0.034 | -2.2% | +9.3% | Y |
| 340 | GC_1-1 | Gold January fade | L | 1.48 | +1.35% | +1.28 | 75% | 0.011 | +2.3% | +0.4% | ? |
| 234 | GC_1-1 | GC 01 | L | 1.48 | +1.35% | +1.28 | 75% | 0.013 | +2.3% | +0.4% | ? |
| 312 | RB_9-10 | Gasoline winter-blend switch | S | -2.36 | +4.30% | +1.25 | 64% | 0.069 | +5.6% | +3.2% | Y |
| 207 | LE_10-10 | LE 10 | L | 1.20 | +1.43% | +1.17 | 55% | 0.007 | +4.0% | -0.7% | Y |
| 325 | HE_10-10 | Hogs Oct | S | -2.29 | +3.85% | +1.05 | 64% | 0.039 | -1.0% | +7.9% | Y |
| 231 | HE_10-10 | HE 10 | S | -2.29 | +3.85% | +1.05 | 64% | 0.040 | -1.0% | +7.9% | Y |
| 152 | SB_3-3 | SB 03 | S | -2.35 | +3.50% | +0.99 | 50% | 0.006 | +8.8% | -1.8% | Y |
| 158 | SB_9-9 | SB 09 | L | 0.24 | +1.94% | +0.94 | 64% | 0.040 | +2.2% | +1.7% | Y |
| 85 | ZS_8-8 | ZS 08 | S | -0.66 | +1.45% | +0.88 | 67% | 0.011 | +1.9% | +1.0% | Y |
| 45 | RB_4-4 | RB 04 | L | 1.17 | +2.45% | +0.87 | 67% | 0.096 | +6.0% | -1.1% | Y |
| 202 | LE_5-5 | LE 05 | S | -2.45 | +1.74% | +0.86 | 58% | 0.002 | +3.2% | +0.3% | Y |
| 327 | LE_5-5 | Cattle May | S | -2.45 | +1.74% | +0.86 | 58% | 0.003 | +3.2% | +0.3% | Y |
| 286 | PA_5-5 | PA 05 | S | -0.84 | +1.50% | +0.82 | 58% | 0.034 | -0.9% | +3.9% | ? |
| 165 | CC_4-4 | CC 04 | L | 0.40 | +1.62% | +0.79 | 75% | 0.078 | +1.4% | +1.9% | ? |
| 18 | NG_1-1 | NG 01 | S | -1.26 | +4.39% | +0.77 | 58% | 0.040 | +4.8% | +4.0% | ? |
| 304 | LB_11-11 | LB 11 | L | 3.04 | +3.84% | +0.73 | 62% | 0.107 | -2.7% | +10.4% | ? |
| 148 | KC_11-11 | KC 11 | L | 0.72 | +2.65% | +0.72 | 55% | 0.029 | -4.4% | +8.5% | ? |
| 77 | ZW_12-12 | ZW 12 | L | 0.89 | +1.00% | +0.72 | 64% | 0.078 | +0.5% | +1.4% | Y |
| 257 | SI_12-12 | SI 12 | L | 0.00 | +1.92% | +0.72 | 55% | 0.059 | -0.1% | +3.6% | ? |
| 99 | ZM_10-10 | ZM 10 | L | 2.06 | +1.84% | +0.70 | 55% | 0.031 | -0.7% | +4.0% | N |
| 52 | RB_11-11 | RB 11 | S | -1.18 | +2.32% | +0.70 | 64% | 0.095 | +2.6% | +2.1% | Y |
| 21 | NG_4-4 | NG 04 | L | 0.56 | +2.29% | +0.67 | 58% | 0.124 | +2.4% | +2.2% | ? |
| 27 | NG_10-10 | NG 10 | L | 1.61 | +2.49% | +0.61 | 55% | 0.136 | -0.6% | +5.1% | ? |
| 190 | OJ_5-5 | OJ 05 | L | 0.12 | +1.68% | +0.59 | 75% | 0.040 | +2.6% | +0.7% | ? |
| 159 | SB_10-10 | SB 10 | L | 1.56 | +1.77% | +0.58 | 55% | 0.031 | +7.5% | -3.0% | Y |
| 246 | SI_1-1 | SI 01 | L | 1.64 | +0.88% | +0.57 | 50% | 0.122 | +1.9% | -0.1% | ? |
| 305 | LB_12-12 | LB 12 | L | 0.11 | +3.33% | +0.56 | 50% | 0.134 | -1.7% | +8.4% | ? |
| 76 | ZW_11-11 | ZW 11 | S | -0.10 | +1.11% | +0.56 | 55% | 0.091 | +0.6% | +1.5% | Y |
| 43 | RB_2-2 | RB 02 | L | 1.48 | +1.69% | +0.55 | 50% | 0.154 | +0.6% | +2.7% | Y |
| 44 | RB_3-3 | RB 03 | L | 4.03 | +4.87% | +0.52 | 83% | 0.027 | -5.5% | +15.2% | Y |
| 40 | HO_11-11 | HO 11 | S | -0.42 | +2.01% | +0.51 | 55% | 0.073 | +2.2% | +1.8% | ? |
| 328 | GF_5-5 | Feeder Cattle May | L | 2.68 | +0.90% | +0.48 | 58% | 0.001 | +0.1% | +1.7% | N |
| 214 | GF_5-5 | GF 05 | L | 2.68 | +0.90% | +0.48 | 58% | 0.001 | +0.1% | +1.7% | N |
| 123 | ZO_10-10 | ZO 10 | L | 0.12 | +1.39% | +0.46 | 55% | 0.044 | +4.7% | -1.3% | ? |
| 84 | ZS_7-7 | ZS 07 | S | -1.23 | +0.80% | +0.44 | 58% | 0.033 | -0.2% | +1.8% | Y |

## Survivors (holdout t>2 AND p<0.05, 15% financing)

- **HE_8-8** HE 08 — dir S, sel_t -4.33, holdout +13.88%/yr (t +5.62), win 92%, p_mc 0.001, halves +12.1%/+15.7%, T212 Y
- **HE_8-8** Hogs Aug — dir S, sel_t -4.33, holdout +13.88%/yr (t +5.62), win 92%, p_mc 0.001, halves +12.1%/+15.7%, T212 Y
- **HE_4-4** Hogs Apr — dir L, sel_t +2.44, holdout +5.70%/yr (t +3.24), win 83%, p_mc 0.004, halves +9.2%/+2.2%, T212 Y
- **HE_4-4** HE 04 — dir L, sel_t +2.44, holdout +5.70%/yr (t +3.24), win 83%, p_mc 0.006, halves +9.2%/+2.2%, T212 Y
- **NG_12-2** NatGas winter premium — dir S, sel_t -0.34, holdout +22.65%/yr (t +2.32), win 73%, p_mc 0.001, halves +11.2%/+32.2%, T212 ?
- **HE_12-12** HE 12 — dir L, sel_t +1.30, holdout +4.70%/yr (t +2.01), win 73%, p_mc 0.024, halves +9.0%/+1.1%, T212 Y

## Sector notes (research-named windows)

### Energy

- NatGas winter premium (NG_12-2): holdout +22.65%/yr, t +2.32, p 0.001 — EIA 2013; CME
- Gasoline winter-blend switch (RB_9-10): holdout +4.30%/yr, t +1.25, p 0.069 — AAA winter-blend
- NatGas shoulder collapse (NG_3-4): holdout +1.97%/yr, t +0.38, p 0.111 — EIA 2013

### Grains

- Corn post-harvest low (ZC_12-12): holdout +1.97%/yr, t +1.57, p 0.028 — CME grains course
- Corn harvest pressure (ZC_7-9): holdout +0.39%/yr, t +0.12, p 0.050 — CME grains course
- Corn planting premium (ZC_5-6): holdout -0.59%/yr, t -0.19, p 0.141 — CME grains course

### Livestock

- Hogs Aug (HE_8-8): holdout +13.88%/yr, t +5.62, p 0.001 — ATLAS prior study
- Hogs Apr (HE_4-4): holdout +5.70%/yr, t +3.24, p 0.004 — ATLAS prior study
- Hogs Feb (HE_2-2): holdout +3.54%/yr, t +1.38, p 0.034 — ATLAS prior study

### Softs

- Sugar harvest (SB_2-3): holdout +1.50%/yr, t +0.37, p 0.030 — ag seasonality study
- Cocoa post-holiday (CC_12-1): holdout +1.89%/yr, t +0.17, p 0.088 — softs seasonality
- Cotton planting (CT_5-5): holdout -0.26%/yr, t -0.15, p 0.139 — ag seasonality study

### Metals

- Gold January fade (GC_1-1): holdout +1.35%/yr, t +1.28, p 0.011 — SSRN 2598514
- Silver autumn (SI_9-9): holdout -1.15%/yr, t -0.40, p 0.424 — SSRN 2598514
- Copper January restock (HG_1-1): holdout -1.81%/yr, t -0.88, p 0.483 — SSRN 2598514


## Honest verdict

Multiple-testing reality: with ~350 strategies tested, ~16 would pass |t|>2 by chance alone in selection, and several will clear the holdout bar by luck. The survivors above are candidates for the FULL strict battery (seasonal_backtest.py: outlier trim, roll-convention check, cost ladder, mechanism audit, $100 compound sim) before any paper capital. Seasonality in financialised commodities is known to decay — treat every line as a hypothesis with evidence attached, not a promise.
