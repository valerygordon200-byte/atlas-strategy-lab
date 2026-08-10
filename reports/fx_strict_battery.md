# FX STRICT BATTERY — news drift + reversal survivors
_data D1 2016-08..2026-08 · events 2015.. · expanding per-title z · next-day-open entry · 1-pip RT cost · 1000-perm MC · 5000-bootstrap MC · walk-forward: news=3y profitability gate / reversal=504d direction_

## Candidates: 7

## News drift EURUSD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean +0.000%, t +0.00, NW +0.00, win 50%, trimmed +0.001%
  - In-sample permutation p = 0.1978 (FAIL)
- Holdout (2022+): mean +0.028%, t +1.92, NW +1.49, win 50%, p 0.0040
- Walk-forward (n=10): mean +0.010%, t +1.45, win 50%
  - Walk-forward permutation p = 0.1109 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.001% / +0.010% / +0.021%, P(mean<=0) = 0.065 (FAIL)
  - Halves: -0.007% / +0.028%; trimmed wf +0.009%
  - Cost ladder (0.5/1/2 pips): +0.015% / +0.010% / +0.004%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout NW t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## News drift USDJPY (z>=|0.5|, next-day open) — FAIL

- In-sample: mean +0.014%, t +1.14, NW +1.12, win 51%, trimmed +0.019%
  - In-sample permutation p = 0.0320 (FAIL)
- Holdout (2022+): mean +0.076%, t +3.78, NW +3.03, win 54%, p 0.0010
- Walk-forward (n=10): mean +0.040%, t +2.99, win 80%
  - Walk-forward permutation p = 0.0120 (PASS)
  - Bootstrap: mean 5-50-95% = +0.019% / +0.040% / +0.061%, P(mean<=0) = 0.001 (PASS)
  - Halves: +0.006% / +0.074%; trimmed wf +0.041%
  - Cost ladder (0.5/1/2 pips): +0.045% / +0.040% / +0.031%
  - Gates: FAILED: |t_is|>2; p_is<0.01

## News drift GBPUSD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean +0.002%, t +0.12, NW +0.11, win 50%, trimmed +0.007%
  - In-sample permutation p = 0.2657 (FAIL)
- Holdout (2022+): mean +0.048%, t +2.90, NW +2.27, win 53%, p 0.0020
- Walk-forward (n=10): mean +0.015%, t +1.38, win 50%
  - Walk-forward permutation p = 0.0699 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.002% / +0.014% / +0.031%, P(mean<=0) = 0.076 (FAIL)
  - Halves: -0.004% / +0.033%; trimmed wf +0.014%
  - Cost ladder (0.5/1/2 pips): +0.024% / +0.015% / +0.011%
  - Gates: FAILED: |t_is|>2; p_is<0.01; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## News drift AUDUSD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean -0.035%, t -2.29, NW -2.17, win 49%, trimmed -0.032%
  - In-sample permutation p = 0.9171 (FAIL)
- Holdout (2022+): mean +0.048%, t +2.36, NW +1.88, win 52%, p 0.0010
- Walk-forward (n=10): mean +0.003%, t +0.35, win 30%
  - Walk-forward permutation p = 0.2827 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.010% / +0.003% / +0.015%, P(mean<=0) = 0.364 (FAIL)
  - Halves: -0.010% / +0.015%; trimmed wf +0.005%
  - Cost ladder (0.5/1/2 pips): +0.005% / +0.003% / -0.003%
  - Gates: FAILED: p_is<0.01; holdout NW t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## News drift USDCAD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean -0.015%, t -1.29, NW -1.24, win 50%, trimmed -0.012%
  - In-sample permutation p = 0.7333 (FAIL)
- Holdout (2022+): mean +0.029%, t +2.58, NW +2.21, win 53%, p 0.0020
- Walk-forward (n=10): mean +0.002%, t +0.59, win 40%
  - Walk-forward permutation p = 0.4356 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.004% / +0.002% / +0.008%, P(mean<=0) = 0.270 (FAIL)
  - Halves: -0.006% / +0.011%; trimmed wf +0.003%
  - Cost ladder (0.5/1/2 pips): +0.005% / +0.002% / -0.000%
  - Gates: FAILED: |t_is|>2; p_is<0.01; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## 1-day reversal AUDUSD — FAIL

- In-sample: mean -0.012%, t -0.81, NW -0.71, win 49%, trimmed +0.003%
  - In-sample permutation p = 0.4326 (FAIL)
- Holdout (2022+): mean -0.062%, t -3.25, NW -3.29, win 46%, p 0.9950
- Walk-forward (n=9): mean -0.005%, t n/a, win n/a
  - Walk-forward permutation p = 0.6903 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.033% / -0.005% / +0.021%, P(mean<=0) = 0.618 (FAIL)
  - Halves: -0.035% / +0.018%; trimmed wf -0.003%
  - Cost ladder (0.5/1/2 pips): -0.005% / -0.005% / -0.005%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout NW t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05; trimmed wf>0

## 5-day reversal EURGBP — FAIL

- In-sample: mean -0.002%, t -0.16, NW -0.15, win 49%, trimmed +0.014%
  - In-sample permutation p = 0.2048 (FAIL)
- Holdout (2022+): mean +0.025%, t +1.52, NW +1.23, win 51%, p 0.0080
- Walk-forward (n=9): mean -0.014%, t n/a, win n/a
  - Walk-forward permutation p = 0.9091 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.042% / -0.012% / +0.009%, P(mean<=0) = 0.800 (FAIL)
  - Halves: -0.007% / -0.020%; trimmed wf -0.003%
  - Cost ladder (0.5/1/2 pips): -0.014% / -0.014% / -0.014%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout NW t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05; trimmed wf>0

## Summary

| key | label | is_t | p_is | ho_nw | p_ho | wf_mean | p_wf | boot P(<=0) | trimmed | ladder 0.5/1/2 | verdict |
|-----|-------|------|------|-------|------|---------|------|------------|---------|----------------|---------|
| news_EURUSD | News drift EURUSD (z>=|0.5|, next-day open) | +0.00 | 0.1978 | +1.49 | 0.0040 | +0.010% | 0.1109 | 0.065 | +0.009% | +0.015%/+0.010%/+0.004% | FAIL |
| news_USDJPY | News drift USDJPY (z>=|0.5|, next-day open) | +1.14 | 0.0320 | +3.03 | 0.0010 | +0.040% | 0.0120 | 0.001 | +0.041% | +0.045%/+0.040%/+0.031% | FAIL |
| news_GBPUSD | News drift GBPUSD (z>=|0.5|, next-day open) | +0.12 | 0.2657 | +2.27 | 0.0020 | +0.015% | 0.0699 | 0.076 | +0.014% | +0.024%/+0.015%/+0.011% | FAIL |
| news_AUDUSD | News drift AUDUSD (z>=|0.5|, next-day open) | -2.29 | 0.9171 | +1.88 | 0.0010 | +0.003% | 0.2827 | 0.364 | +0.005% | +0.005%/+0.003%/-0.003% | FAIL |
| news_USDCAD | News drift USDCAD (z>=|0.5|, next-day open) | -1.29 | 0.7333 | +2.21 | 0.0020 | +0.002% | 0.4356 | 0.270 | +0.003% | +0.005%/+0.002%/-0.000% | FAIL |
| rev1_AUDUSD | 1-day reversal AUDUSD | -0.81 | 0.4326 | -3.29 | 0.9950 | -0.005% | 0.6903 | 0.618 | -0.003% | -0.005%/-0.005%/-0.005% | FAIL |
| rev5_EURGBP | 5-day reversal EURGBP | -0.16 | 0.2048 | +1.23 | 0.0080 | -0.014% | 0.9091 | 0.800 | -0.003% | -0.014%/-0.014%/-0.014% | FAIL |

## What the numbers mean
- **In-sample t / NW**: signal strength 2016-2021 (Newey-West lag-5). High alone is cheap; that is why the rest exists.
- **p_is**: 1000 sign-flip permutations — the chance that random position signs reproduce the fit-window profit. p<0.01 is the gate.
- **Holdout**: locked-direction 2022+ net of costs; NW t>2 and p<0.05 mean the fit generalised forward.
- **Walk-forward**: news — a year is traded only if the trailing-3y event book was profitable (min 30 events), direction always the surprise direction; reversal — direction re-estimated on trailing 504 days. No lookahead in either.
- **p_wf**: 1000 random-day walk-forwards under identical machinery; the chance a random calendar matches the actual walk-forward profit.
- **Bootstrap P(mean<=0)**: 5000 resamples of the walk-forward years; probability the true mean is non-positive. <0.05 is the strict bar.
- **Trimmed**: best and worst year removed — a real effect survives.
- **Ladder**: net at 0.5/1/2-pip round-trip costs; dying at 2 pips means the edge is cost-dependent.