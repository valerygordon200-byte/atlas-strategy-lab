# STRICT BATTERY — seasonal candidates
_data 2000-01..2026-08 · walk-forward: 10y trailing re-estimation, min 8 obs · 1000-permutation MC · 5000-bootstrap MC · costs at 8/15/25% financing ladder_

## Hogs August SHORT (HE 08-08) — FAIL

- In-sample (2001-2014): mean +11.82%, t +3.51, win 86%, trimmed t +5.61
  - In-sample permutation p = 0.0010 (<1% gate PASS)
  - In-sample halves: +10.14% / +13.50%
- Holdout (2015+): mean +13.88%, t +5.62, win 92%, p 0.0010
- Walk-forward (n=18): mean +13.82%, t +8.08, win 94%, median +15.40%, std +7.25%
  - Walk-forward permutation p = 0.0759 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = +11.00% / +13.88% / +16.52%, P(mean<=0) = 0.000 (PASS)
  - Halves: +13.81% / +13.82%; trimmed wf mean +14.35%
  - Cost ladder (8/15/25%): +14.40% / +13.82% / +12.98%
  - Gates: FAILED: wf mean>0 & p_wf<0.05

## Hogs April LONG (HE 04-04) — FAIL

- In-sample (2001-2014): mean +4.71%, t +1.54, win 57%, trimmed t +1.82
  - In-sample permutation p = 0.0020 (<1% gate PASS)
  - In-sample halves: +5.31% / +4.11%
- Holdout (2015+): mean +5.70%, t +3.24, win 83%, p 0.0050
- Walk-forward (n=18): mean +4.13%, t +2.28, win 67%, median +4.26%, std +7.67%
  - Walk-forward permutation p = 0.1628 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = +1.30% / +4.13% / +7.10%, P(mean<=0) = 0.006 (PASS)
  - Halves: +3.74% / +4.52%; trimmed wf mean +4.11%
  - Cost ladder (8/15/25%): +4.71% / +4.13% / +3.30%
  - Gates: FAILED: |t_is|>2; wf mean>0 & p_wf<0.05

## NatGas Dec-Feb (winter) (NG 12-02) — FAIL

- In-sample (2001-2014): mean -3.26%, t -0.32, win 50%, trimmed t -0.27
  - In-sample permutation p = 0.1888 (FAIL)
  - In-sample halves: +2.74% / -9.25%
- Holdout (2015+): mean +22.65%, t +2.32, win 73%, p 0.0010
- Walk-forward (n=17): mean +5.47%, t +0.65, win 59%, median +5.85%, std +34.67%
  - Walk-forward permutation p = 0.2398 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = -7.80% / +5.88% / +18.56%, P(mean<=0) = 0.238 (FAIL)
  - Halves: -15.31% / +23.95%; trimmed wf mean +7.64%
  - Cost ladder (8/15/25%): +7.22% / +5.47% / +2.97%
  - Gates: FAILED: |t_is|>2; p_is<0.01; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## Hogs December LONG (HE 12-12) — FAIL

- In-sample (2001-2014): mean -0.24%, t -0.13, win 43%, trimmed t -0.09
  - In-sample permutation p = 0.2028 (FAIL)
  - In-sample halves: +0.19% / -0.68%
- Holdout (2015+): mean +4.70%, t +2.01, win 73%, p 0.0210
- Walk-forward (n=17): mean +2.79%, t +1.35, win 59%, median +2.47%, std +8.54%
  - Walk-forward permutation p = 0.1698 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = -0.43% / +2.74% / +6.00%, P(mean<=0) = 0.077 (FAIL)
  - Halves: +2.32% / +3.22%; trimmed wf mean +2.51%
  - Cost ladder (8/15/25%): +3.38% / +2.79% / +1.96%
  - Gates: FAILED: |t_is|>2; p_is<0.01; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## Gasoline September (RB 09-09) — FAIL

- In-sample (2001-2014): mean +5.24%, t +1.61, win 64%, trimmed t +2.12
  - In-sample permutation p = 0.0100 (<1% gate PASS)
  - In-sample halves: +5.51% / +4.97%
- Holdout (2015+): mean +5.56%, t +1.98, win 64%, p 0.0120
- Walk-forward (n=17): mean +4.67%, t +2.02, win 65%, median +4.67%, std +9.53%
  - Walk-forward permutation p = 0.0959 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = +0.88% / +4.73% / +8.43%, P(mean<=0) = 0.018 (PASS)
  - Halves: +3.05% / +6.11%; trimmed wf mean +4.26%
  - Cost ladder (8/15/25%): +5.26% / +4.67% / +3.84%
  - Gates: FAILED: |t_is|>2; holdout t>2 & p<0.05; wf mean>0 & p_wf<0.05

## Corn July (ZC 07-07) — FAIL

- In-sample (2001-2014): mean +0.56%, t +0.14, win 43%, trimmed t -0.02
  - In-sample permutation p = 0.1718 (FAIL)
  - In-sample halves: -2.16% / +3.28%
- Holdout (2015+): mean +4.86%, t +1.76, win 75%, p 0.0010
- Walk-forward (n=18): mean +3.46%, t +1.16, win 67%, median +3.63%, std +12.72%
  - Walk-forward permutation p = 0.0779 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = -1.26% / +3.39% / +8.38%, P(mean<=0) = 0.120 (FAIL)
  - Halves: +1.75% / +5.18%; trimmed wf mean +3.36%
  - Cost ladder (8/15/25%): +4.05% / +3.46% / +2.63%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## NatGas December (NG 12-12) — FAIL

- In-sample (2000-2014): mean -0.32%, t -0.06, win 53%, trimmed t +0.11
  - In-sample permutation p = 0.2318 (FAIL)
  - In-sample halves: -3.54% / +2.49%
- Holdout (2015+): mean +10.02%, t +1.72, win 64%, p 0.0050
- Walk-forward (n=18): mean +6.49%, t +1.47, win 61%, median +2.61%, std +18.75%
  - Walk-forward permutation p = 0.1738 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = -0.34% / +6.41% / +13.87%, P(mean<=0) = 0.061 (FAIL)
  - Halves: -1.61% / +14.59%; trimmed wf mean +5.78%
  - Cost ladder (8/15/25%): +7.07% / +6.49% / +5.65%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## Wheat September (ZW 09-09) — FAIL

- In-sample (2000-2014): mean -1.14%, t -0.41, win 53%, trimmed t -0.44
  - In-sample permutation p = 0.4086 (FAIL)
  - In-sample halves: +2.53% / -4.35%
- Holdout (2015+): mean +3.08%, t +1.69, win 73%, p 0.0120
- Walk-forward (n=18): mean -4.08%, t -1.89, win 44%, median -2.11%, std +9.18%
  - Walk-forward permutation p = 0.8452 (FAIL)
  - Bootstrap (5000): mean 5-50-95% = -7.57% / -4.02% / -0.60%, P(mean<=0) = 0.975 (FAIL)
  - Halves: -6.86% / -1.30%; trimmed wf mean -3.89%
  - Cost ladder (8/15/25%): -3.50% / -4.08% / -4.92%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05; trimmed wf>0

## Summary

| key | label | is_t | p_is | ho_t | p_ho | wf_mean | wf_t | p_wf | boot P(<=0) | trimmed wf | ladder 8/15/25 | verdict |
|-----|-------|------|------|------|------|---------|------|------|-------------|------------|----------------|---------|
| HE_8-8 | Hogs August SHORT | +3.51 | 0.0010 | +5.62 | 0.0010 | +13.82% | +8.08 | 0.0759 | 0.000 | +14.35% | +14.40%/+13.82%/+12.98% | FAIL |
| HE_4-4 | Hogs April LONG | +1.54 | 0.0020 | +3.24 | 0.0050 | +4.13% | +2.28 | 0.1628 | 0.006 | +4.11% | +4.71%/+4.13%/+3.30% | FAIL |
| NG_12-2 | NatGas Dec-Feb (winter) | -0.32 | 0.1888 | +2.32 | 0.0010 | +5.47% | +0.65 | 0.2398 | 0.238 | +7.64% | +7.22%/+5.47%/+2.97% | FAIL |
| HE_12-12 | Hogs December LONG | -0.13 | 0.2028 | +2.01 | 0.0210 | +2.79% | +1.35 | 0.1698 | 0.077 | +2.51% | +3.38%/+2.79%/+1.96% | FAIL |
| RB_9-9 | Gasoline September | +1.61 | 0.0100 | +1.98 | 0.0120 | +4.67% | +2.02 | 0.0959 | 0.018 | +4.26% | +5.26%/+4.67%/+3.84% | FAIL |
| ZC_7-7 | Corn July | +0.14 | 0.1718 | +1.76 | 0.0010 | +3.46% | +1.16 | 0.0779 | 0.120 | +3.36% | +4.05%/+3.46%/+2.63% | FAIL |
| NG_12-12 | NatGas December | -0.06 | 0.2318 | +1.72 | 0.0050 | +6.49% | +1.47 | 0.1738 | 0.061 | +5.78% | +7.07%/+6.49%/+5.65% | FAIL |
| ZW_9-9 | Wheat September | -0.41 | 0.4086 | +1.69 | 0.0120 | -4.08% | -1.89 | 0.8452 | 0.975 | -3.89% | -3.50%/-4.08%/-4.92% | FAIL |

## What the numbers mean

- **In-sample t**: signal strength in the 2000-2014 fit window (|t|>2 required). High here alone is cheap — it is why the rest exists.
- **p_is (in-sample permutation)**: 1000 random same-length calendar windows; the chance a random month matches the observed fit-window profit. p<0.01 means the fit is not luck-of-the-calendar.
- **Holdout**: locked-direction 2015+ performance net of costs; t>2 and p<0.05 mean the fit generalised forward.
- **Walk-forward**: every year, direction is re-estimated on the trailing 10 years only (no lookahead) and the NEXT year is traded. This is the honest 'would I have traded it?' series.
- **p_wf (walk-forward permutation)**: 1000 full walk-forwards on random windows; the chance a random month matches the actual walk-forward profit under identical machinery.
- **Bootstrap P(mean<=0)**: 5000 resamples of the walk-forward years; probability the true mean is non-positive. <0.05 is the strict bar.
- **Trimmed**: best and worst year removed — a real effect survives; a one-year fluke dies.
- **Ladder**: net at 8/15/25% annualised financing; a strategy that dies at 25% is financing-dependent.