# FX STRICT BATTERY — news drift + reversal survivors
_data D1 2016-08..2026-08 · events 2015.. · expanding per-title z · next-day-open entry · 1-pip RT cost · 1000-perm MC · 5000-bootstrap MC · walk-forward: news=3y profitability gate / reversal=504d direction_

## Candidates: 7

## News drift EURUSD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean -0.002%, t -0.22, NW -0.20, win 50%, trimmed -0.003%
  - In-sample permutation p = 0.2807 (FAIL)
- Holdout (2022+): mean +0.026%, t +1.84, NW +1.42, win 51%, p 0.0100
- Walk-forward (n=10): mean +0.010%, t +1.50, win 50%
  - Walk-forward permutation p = 0.1099 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.000% / +0.010% / +0.020%, P(mean<=0) = 0.057 (FAIL)
  - Halves: -0.007% / +0.027%; trimmed wf +0.010%
  - Cost ladder (0.5/1/2 pips): +0.014% / +0.010% / +0.004%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout NW t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## News drift USDJPY (z>=|0.5|, next-day open) — FAIL

- In-sample: mean +0.019%, t +1.60, NW +1.53, win 50%, trimmed +0.020%
  - In-sample permutation p = 0.0120 (FAIL)
- Holdout (2022+): mean +0.076%, t +3.91, NW +3.14, win 54%, p 0.0010
- Walk-forward (n=10): mean +0.043%, t +3.55, win 90%
  - Walk-forward permutation p = 0.0030 (PASS)
  - Bootstrap: mean 5-50-95% = +0.024% / +0.043% / +0.062%, P(mean<=0) = 0.000 (PASS)
  - Halves: +0.012% / +0.075%; trimmed wf +0.043%
  - Cost ladder (0.5/1/2 pips): +0.047% / +0.043% / +0.034%
  - Gates: FAILED: |t_is|>2; p_is<0.01

## News drift GBPUSD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean -0.009%, t -0.67, NW -0.61, win 49%, trimmed -0.008%
  - In-sample permutation p = 0.5035 (FAIL)
- Holdout (2022+): mean +0.049%, t +3.03, NW +2.35, win 53%, p 0.0010
- Walk-forward (n=10): mean +0.015%, t +1.28, win 50%
  - Walk-forward permutation p = 0.0679 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.003% / +0.014% / +0.033%, P(mean<=0) = 0.073 (FAIL)
  - Halves: -0.008% / +0.038%; trimmed wf +0.012%
  - Cost ladder (0.5/1/2 pips): +0.017% / +0.015% / +0.010%
  - Gates: FAILED: |t_is|>2; p_is<0.01; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## News drift AUDUSD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean -0.027%, t -1.97, NW -1.86, win 49%, trimmed -0.026%
  - In-sample permutation p = 0.8002 (FAIL)
- Holdout (2022+): mean +0.051%, t +2.59, NW +2.06, win 53%, p 0.0030
- Walk-forward (n=10): mean +0.003%, t +0.46, win 30%
  - Walk-forward permutation p = 0.2537 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.009% / +0.003% / +0.015%, P(mean<=0) = 0.364 (FAIL)
  - Halves: -0.009% / +0.015%; trimmed wf +0.005%
  - Cost ladder (0.5/1/2 pips): +0.006% / +0.003% / -0.002%
  - Gates: FAILED: |t_is|>2; p_is<0.01; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## News drift USDCAD (z>=|0.5|, next-day open) — FAIL

- In-sample: mean -0.011%, t -1.02, NW -0.95, win 50%, trimmed -0.009%
  - In-sample permutation p = 0.6364 (FAIL)
- Holdout (2022+): mean +0.031%, t +2.79, NW +2.36, win 54%, p 0.0010
- Walk-forward (n=10): mean +0.004%, t +0.83, win 40%
  - Walk-forward permutation p = 0.3636 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.004% / +0.004% / +0.011%, P(mean<=0) = 0.187 (FAIL)
  - Halves: -0.006% / +0.013%; trimmed wf +0.005%
  - Cost ladder (0.5/1/2 pips): +0.006% / +0.004% / -0.002%
  - Gates: FAILED: |t_is|>2; p_is<0.01; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05

## 1-day reversal AUDUSD — FAIL

- In-sample: mean -0.012%, t -0.81, NW -0.71, win 49%, trimmed +0.003%
  - In-sample permutation p = 0.4755 (FAIL)
- Holdout (2022+): mean -0.062%, t -3.25, NW -3.29, win 46%, p 0.9930
- Walk-forward (n=9): mean -0.005%, t n/a, win n/a
  - Walk-forward permutation p = 0.6603 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.033% / -0.005% / +0.021%, P(mean<=0) = 0.618 (FAIL)
  - Halves: -0.035% / +0.018%; trimmed wf -0.003%
  - Cost ladder (0.5/1/2 pips): -0.005% / -0.005% / -0.005%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout NW t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05; trimmed wf>0

## 5-day reversal EURGBP — FAIL

- In-sample: mean -0.002%, t -0.16, NW -0.15, win 49%, trimmed +0.014%
  - In-sample permutation p = 0.2018 (FAIL)
- Holdout (2022+): mean +0.025%, t +1.52, NW +1.23, win 51%, p 0.0110
- Walk-forward (n=9): mean -0.014%, t n/a, win n/a
  - Walk-forward permutation p = 0.8811 (FAIL)
  - Bootstrap: mean 5-50-95% = -0.042% / -0.012% / +0.009%, P(mean<=0) = 0.800 (FAIL)
  - Halves: -0.007% / -0.020%; trimmed wf -0.003%
  - Cost ladder (0.5/1/2 pips): -0.014% / -0.014% / -0.014%
  - Gates: FAILED: |t_is|>2; p_is<0.01; holdout NW t>2 & p<0.05; wf mean>0 & p_wf<0.05; bootstrap P(<=0)<0.05; trimmed wf>0

## Summary

| key | label | is_t | p_is | ho_nw | p_ho | wf_mean | p_wf | boot P(<=0) | trimmed | ladder 0.5/1/2 | verdict |
|-----|-------|------|------|-------|------|---------|------|------------|---------|----------------|---------|
| news_EURUSD | News drift EURUSD (z>=|0.5|, next-day open) | -0.22 | 0.2807 | +1.42 | 0.0100 | +0.010% | 0.1099 | 0.057 | +0.010% | +0.014%/+0.010%/+0.004% | FAIL |
| news_USDJPY | News drift USDJPY (z>=|0.5|, next-day open) | +1.60 | 0.0120 | +3.14 | 0.0010 | +0.043% | 0.0030 | 0.000 | +0.043% | +0.047%/+0.043%/+0.034% | FAIL |
| news_GBPUSD | News drift GBPUSD (z>=|0.5|, next-day open) | -0.67 | 0.5035 | +2.35 | 0.0010 | +0.015% | 0.0679 | 0.073 | +0.012% | +0.017%/+0.015%/+0.010% | FAIL |
| news_AUDUSD | News drift AUDUSD (z>=|0.5|, next-day open) | -1.97 | 0.8002 | +2.06 | 0.0030 | +0.003% | 0.2537 | 0.364 | +0.005% | +0.006%/+0.003%/-0.002% | FAIL |
| news_USDCAD | News drift USDCAD (z>=|0.5|, next-day open) | -1.02 | 0.6364 | +2.36 | 0.0010 | +0.004% | 0.3636 | 0.187 | +0.005% | +0.006%/+0.004%/-0.002% | FAIL |
| rev1_AUDUSD | 1-day reversal AUDUSD | -0.81 | 0.4755 | -3.29 | 0.9930 | -0.005% | 0.6603 | 0.618 | -0.003% | -0.005%/-0.005%/-0.005% | FAIL |
| rev5_EURGBP | 5-day reversal EURGBP | -0.16 | 0.2018 | +1.23 | 0.0110 | -0.014% | 0.8811 | 0.800 | -0.003% | -0.014%/-0.014%/-0.014% | FAIL |

## What the numbers mean
- **In-sample t / NW**: signal strength 2016-2021 (Newey-West lag-5). High alone is cheap; that is why the rest exists.
- **p_is**: 1000 sign-flip permutations — the chance that random position signs reproduce the fit-window profit. p<0.01 is the gate.
- **Holdout**: locked-direction 2022+ net of costs; NW t>2 and p<0.05 mean the fit generalised forward.
- **Walk-forward**: news — a year is traded only if the trailing-3y event book was profitable (min 30 events), direction always the surprise direction; reversal — direction re-estimated on trailing 504 days. No lookahead in either.
- **p_wf**: 1000 random-day walk-forwards under identical machinery; the chance a random calendar matches the actual walk-forward profit.
- **Bootstrap P(mean<=0)**: 5000 resamples of the walk-forward years; probability the true mean is non-positive. <0.05 is the strict bar.
- **Trimmed**: best and worst year removed — a real effect survives.
- **Ladder**: net at 0.5/1/2-pip round-trip costs; dying at 2 pips means the edge is cost-dependent.