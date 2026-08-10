# News drift family — STRICT six-gate battery

Gates: IS |t|>2; IS 1000-perm p<1%; holdout t>2 & p<0.05; WF mean>0 & wf-perm p<0.05;
bootstrap P(mean<=0)<0.05; outlier-trimmed WF>0.  D1: IS<=2021-12.  Intraday: IS<=2025-06, monthly WF.

| variant | n | IS% | IS t | p_is | HO% | HO t | p_ho | WF% | p_wf | boot P | trim | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| intraday_h12h_USDJPY | 809 | +0.001 | +2.99 | 0.002 | -0.000 | -0.42 | 0.656 | +0.000 | 0.001 | 0.048 | +0.000 | **FAIL** |
| intraday_h2h_USDJPY | 809 | +0.000 | +2.74 | 0.003 | -0.000 | -0.15 | 0.547 | +0.000 | 0.001 | 0.024 | +0.000 | **FAIL** |
| intraday_h8h_USDJPY | 809 | +0.000 | +2.61 | 0.006 | -0.000 | -0.71 | 0.756 | +0.000 | 0.001 | 0.057 | +0.000 | **FAIL** |
| intraday_h24h_USDJPY | 807 | +0.001 | +2.46 | 0.005 | -0.000 | -0.59 | 0.707 | +0.000 | 0.001 | 0.065 | +0.000 | **FAIL** |
| intraday_h12h_basket_high | 254 | +0.001 | +2.39 | 0.007 | -0.000 | -0.30 | 0.609 | +0.001 | 0.001 | 0.063 | +0.000 | **FAIL** |
| D1_nextday_AUDUSD | 2856 | -0.000 | -2.29 | 0.980 | +0.001 | +2.36 | 0.011 | +0.000 | 0.273 | 0.360 | +0.000 | **FAIL** |
| intraday_h2h_basket_high | 254 | +0.000 | +2.15 | 0.023 | -0.000 | -0.68 | 0.759 | +0.000 | 0.066 | 0.306 | -0.000 | **FAIL** |
| intraday_h1h_USDJPY | 809 | +0.000 | +2.00 | 0.020 | -0.000 | -0.44 | 0.658 | +0.000 | 0.015 | 0.088 | +0.000 | **FAIL** |
| intraday_h8h_basket_high | 254 | +0.000 | +1.94 | 0.038 | -0.000 | -1.06 | 0.862 | +0.000 | 0.042 | 0.318 | +0.000 | **FAIL** |
| intraday_h4h_basket_high | 254 | +0.000 | +1.88 | 0.033 | -0.000 | -0.34 | 0.618 | +0.000 | 0.058 | 0.336 | +0.000 | **FAIL** |
| intraday_h1h_basket_high | 254 | +0.000 | +1.69 | 0.044 | -0.000 | -1.22 | 0.882 | +0.000 | 0.261 | 0.413 | -0.000 | **FAIL** |
| intraday_h24h_basket_high | 254 | +0.001 | +1.68 | 0.047 | -0.000 | -0.12 | 0.537 | +0.000 | 0.001 | 0.174 | +0.000 | **FAIL** |
| intraday_h4h_USDJPY | 809 | +0.000 | +1.60 | 0.065 | -0.000 | -0.22 | 0.584 | +0.000 | 0.003 | 0.109 | +0.000 | **FAIL** |
| intraday_h12h_basket | 809 | +0.000 | +1.34 | 0.091 | -0.000 | -0.20 | 0.576 | +0.000 | 0.010 | 0.174 | +0.000 | **FAIL** |
| D1_nextday_USDCAD | 2856 | -0.000 | -1.29 | 0.910 | +0.000 | +2.58 | 0.010 | +0.000 | 0.431 | 0.265 | +0.000 | **FAIL** |
| D1_nextday_USDJPY | 2856 | +0.000 | +1.14 | 0.117 | +0.001 | +3.78 | 0.001 | +0.000 | 0.004 | 0.002 | +0.000 | **FAIL** |
| intraday_h2h_basket | 809 | +0.000 | +1.05 | 0.140 | -0.000 | -1.88 | 0.973 | -0.000 | 0.543 | 0.535 | +0.000 | **FAIL** |
| intraday_h24h_basket | 807 | +0.000 | +0.91 | 0.171 | +0.000 | +0.75 | 0.239 | +0.000 | 0.003 | 0.102 | +0.000 | **FAIL** |
| intraday_h8h_basket | 809 | +0.000 | +0.78 | 0.228 | -0.000 | -0.88 | 0.795 | -0.000 | 0.603 | 0.546 | +0.000 | **FAIL** |
| intraday_h4h_basket | 809 | +0.000 | +0.71 | 0.246 | -0.000 | -1.02 | 0.843 | -0.000 | 0.954 | 0.702 | +0.000 | **FAIL** |
| D1_nextday_basket | 2856 | -0.000 | -0.68 | 0.728 | +0.001 | +3.35 | 0.001 | +0.000 | 0.531 | 0.041 | +0.000 | **FAIL** |
| intraday_h1h_basket | 809 | +0.000 | +0.64 | 0.260 | -0.000 | -2.75 | 0.998 | -0.000 | 0.626 | 0.569 | +0.000 | **FAIL** |
| D1_nextday_GBPUSD | 2856 | +0.000 | +0.12 | 0.449 | +0.001 | +2.90 | 0.004 | +0.000 | 0.070 | 0.079 | +0.000 | **FAIL** |
| D1_nextday_EURUSD | 2856 | +0.000 | +0.00 | 0.471 | +0.000 | +1.92 | 0.031 | +0.000 | 0.088 | 0.063 | +0.000 | **FAIL** |

Failed gates per variant:

- intraday_h12h_USDJPY: ho t>2 & p<0.05
- intraday_h2h_USDJPY: ho t>2 & p<0.05
- intraday_h8h_USDJPY: ho t>2 & p<0.05; boot P(<=0)<0.05
- intraday_h24h_USDJPY: ho t>2 & p<0.05; boot P(<=0)<0.05
- intraday_h12h_basket_high: ho t>2 & p<0.05; boot P(<=0)<0.05
- D1_nextday_AUDUSD: p_is<0.01; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- intraday_h2h_basket_high: p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05; trim>0
- intraday_h1h_USDJPY: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; boot P(<=0)<0.05
- intraday_h8h_basket_high: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; boot P(<=0)<0.05
- intraday_h4h_basket_high: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- intraday_h1h_basket_high: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05; trim>0
- intraday_h24h_basket_high: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; boot P(<=0)<0.05
- intraday_h4h_USDJPY: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; boot P(<=0)<0.05
- intraday_h12h_basket: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; boot P(<=0)<0.05
- D1_nextday_USDCAD: |t_is|>2; p_is<0.01; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- D1_nextday_USDJPY: |t_is|>2; p_is<0.01
- intraday_h2h_basket: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- intraday_h24h_basket: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; boot P(<=0)<0.05
- intraday_h8h_basket: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- intraday_h4h_basket: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- D1_nextday_basket: |t_is|>2; p_is<0.01; wf>0 & p_wf<0.05
- intraday_h1h_basket: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- D1_nextday_GBPUSD: |t_is|>2; p_is<0.01; wf>0 & p_wf<0.05; boot P(<=0)<0.05
- D1_nextday_EURUSD: |t_is|>2; p_is<0.01; ho t>2 & p<0.05; wf>0 & p_wf<0.05; boot P(<=0)<0.05