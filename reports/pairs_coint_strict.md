# Cointegration pairs trading — STRICT battery (candidate #1 from platform scan)

Mechanism: QC research/15347 (Miao).  Daily adaptation on local universe. Train 126d, re-estimate monthly, ADF < -3.37 required, z+-2.33 enter / 0.5 exit / 4 sigma stop. Costs: 1 pip/leg/side.

| pair | trades | IS% | IS t | p_is | HO% | HO t | p_ho | WF% | p_wf | boot | trim | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AUDUSD-USDJPY | 18 | -0.002 | -2.39 | 0.998 | -0.001 | -0.43 | 0.640 | +0.000 | 0.167 | 1.000 | -0.309 | **FAIL** |
| EURUSD-AUDUSD | 12 | -0.001 | -1.58 | 0.923 | -0.000 | -0.30 | 0.614 | +0.000 | 0.167 | 1.000 | -0.051 | **FAIL** |
| GBPUSD-GOLD | 9 | +0.001 | +1.16 | 0.238 | +0.000 | +0.06 | 0.439 | +0.000 | 0.402 | 0.355 | +0.019 | **FAIL** |
| AUDUSD-GOLD | 9 | +0.000 | +1.15 | 0.224 | +0.001 | +0.78 | 0.187 | -0.000 | 0.898 | 0.814 | +0.044 | **FAIL** |
| AUDUSD-USDCAD | 25 | +0.003 | +1.05 | 0.174 | +0.003 | +0.66 | 0.385 | +0.001 | 0.439 | 0.200 | +0.462 | **FAIL** |
| GBPUSD-USDJPY | 21 | -0.002 | -1.04 | 0.816 | -0.001 | -1.38 | 0.904 | -0.000 | 0.302 | 0.868 | -0.297 | **FAIL** |
| USDCAD-SILVER | 18 | -0.001 | -0.96 | 0.801 | +0.002 | +1.39 | 0.120 | +0.001 | 0.163 | 0.367 | -0.074 | **FAIL** |
| EURUSD-USDJPY | 9 | +0.000 | +0.76 | 0.368 | +0.000 | +0.61 | 0.264 | +0.000 | 0.468 | 0.134 | +0.045 | **FAIL** |
| EURUSD-GOLD | 21 | -0.001 | -0.72 | 0.697 | +0.001 | +0.51 | 0.312 | -0.001 | 0.904 | 1.000 | -0.030 | **FAIL** |
| USDCAD-GOLD | 14 | -0.001 | -0.54 | 0.686 | -0.002 | -0.96 | 0.809 | -0.000 | 0.545 | 0.754 | -0.054 | **FAIL** |
| USDJPY-USDCAD | 18 | -0.001 | -0.51 | 0.670 | +0.002 | +0.72 | 0.344 | -0.000 | 0.808 | 0.821 | -0.104 | **FAIL** |
| GBPUSD-USDCAD | 15 | +0.000 | +0.39 | 0.335 | +0.001 | +0.83 | 0.354 | +0.000 | 0.544 | 0.421 | +0.078 | **FAIL** |
| USDJPY-SILVER | 18 | +0.000 | +0.32 | 0.406 | +0.004 | +1.13 | 0.157 | +0.001 | 0.428 | 0.236 | +0.041 | **FAIL** |
| EURUSD-USDCAD | 27 | -0.000 | -0.32 | 0.620 | +0.001 | +0.54 | 0.324 | +0.000 | 0.252 | 0.283 | +0.027 | **FAIL** |
| EURUSD-GBPUSD | 9 | -0.000 | -0.30 | 0.603 | +0.000 | +0.62 | 0.385 | -0.000 | 0.671 | 1.000 | -0.009 | **FAIL** |
| GBPUSD-AUDUSD | 6 | -0.000 | -0.25 | 0.651 | -0.000 | -0.00 | 0.491 | -0.000 | 0.828 | 1.000 | -0.000 | **FAIL** |
| GBPUSD-SILVER | 15 | +0.000 | +0.23 | 0.412 | -0.000 | -0.31 | 0.752 | -0.000 | 0.434 | 0.532 | -0.029 | **FAIL** |
| USDJPY-GOLD | 33 | +0.000 | +0.02 | 0.477 | -0.002 | -0.98 | 0.825 | -0.001 | 0.666 | 0.834 | -0.260 | **FAIL** |
| EURUSD-SILVER | 6 | +nan | +nan | nan | +nan | +nan | nan | +nan | nan | nan | +nan | **INSUFFICIENT** |
| AUDUSD-SILVER | 15 | +nan | +nan | nan | +nan | +nan | nan | +nan | nan | nan | +nan | **INSUFFICIENT** |
| GOLD-SILVER | 9 | +nan | +nan | nan | +nan | +nan | nan | +nan | nan | nan | +nan | **INSUFFICIENT** |

Failed gates:

- AUDUSD-USDJPY: p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- EURUSD-AUDUSD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- GBPUSD-GOLD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05
- AUDUSD-GOLD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05
- AUDUSD-USDCAD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05
- GBPUSD-USDJPY: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- USDCAD-SILVER: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- EURUSD-USDJPY: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05
- EURUSD-GOLD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- USDCAD-GOLD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- USDJPY-USDCAD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- GBPUSD-USDCAD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05
- USDJPY-SILVER: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05
- EURUSD-USDCAD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05
- EURUSD-GBPUSD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- GBPUSD-AUDUSD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- GBPUSD-SILVER: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- USDJPY-GOLD: |t_is|>2; p_is<0.01; ho t>2&p<0.05; wf>0&p<0.05; boot<0.05; trim>0
- EURUSD-SILVER: no trades in IS or OOS
- AUDUSD-SILVER: no trades in IS or OOS
- GOLD-SILVER: no trades in IS or OOS