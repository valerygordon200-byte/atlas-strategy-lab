# Dual momentum (Antonacci) — STRICT battery (candidate #2 from platform scan)

Mechanism: 12m absolute filter -> rank -> top-k, cash if none eligible, monthly rebalance. Costs: 0.5bps/trade + 0.5%/yr drag. IS <= 2017-12, holdout 2018-2026.

| variant | n | IS%/mo | IS t | p_is | HO%/mo | HO t | p_ho | WF%/mo | p_wf | boot | trim | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dual_mom_top1 | 228 | +1.612 | +3.83 | 0.001 | +2.124 | +4.51 | 0.001 | +1.817 | 0.001 | 0.000 | +20.358 | **PASS** |
| dual_mom_top2 | 228 | +1.246 | +3.74 | 0.001 | +1.740 | +5.47 | 0.001 | +1.426 | 0.001 | 0.000 | +16.797 | **PASS** |
| buyhold_SPY | 240 | +0.614 | +1.73 | 0.043 | +1.141 | +2.45 | 0.009 | +0.826 | 0.001 | 0.001 | +11.620 | **FAIL** |
| buyhold_IEF | 240 | +0.199 | +1.26 | 0.084 | -0.101 | -0.53 | 0.708 | +0.030 | 0.001 | 0.404 | +1.121 | **FAIL** |
| top1_cost0x | 228 | +1.690 | +4.02 | 0.001 | +2.189 | +4.64 | 0.001 | +1.891 | 0.001 | 0.000 | +21.183 | **PASS** |
| top1_cost2x | 228 | +1.534 | +3.65 | 0.002 | +2.058 | +4.38 | 0.001 | +1.743 | 0.001 | 0.000 | +19.533 | **PASS** |
| top1_cost5x | 228 | +1.298 | +3.09 | 0.003 | +1.861 | +3.98 | 0.001 | +1.521 | 0.001 | 0.000 | +17.058 | **PASS** |
| top1_null_random_rank | 228 | -0.331 | -0.73 | 0.793 | +0.463 | +1.11 | 0.121 | +0.025 | 0.001 | 0.344 | +2.259 | **FAIL** |
| top1_ho_first_half | 53 | +nan | +nan | nan | +2.201 | +3.63 | nan | +nan | nan | nan | +nan | **PASS** |
| top1_ho_second_half | 51 | +nan | +nan | nan | +2.044 | +2.82 | nan | +nan | nan | nan | +nan | **PASS** |

Failed gates:

- dual_mom_top1: all pass
- dual_mom_top2: all pass
- buyhold_SPY: |t_is|>2; p_is<0.01
- buyhold_IEF: |t_is|>2; p_is<0.01; ho t>2&p<0.05; boot<0.05
- top1_cost0x: all pass
- top1_cost2x: all pass
- top1_cost5x: all pass
- top1_null_random_rank: |t_is|>2; p_is<0.01; ho t>2&p<0.05; boot<0.05
- top1_ho_first_half: t>2 & mean>0 (direct, no IS split)
- top1_ho_second_half: t>2 & mean>0 (direct, no IS split)