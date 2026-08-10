# Family E — dollar-basket under-reaction — STRICT four-stage battery

Mechanism: surprise z (actual vs real consensus, per title), 7-pair vol-normalized dollar
basket, IN-SAMPLE-locked r30~z regression, under-reaction gap filter, EURUSD execution.
Control arm = momentum on pre-move (must FAIL for the family to live).  H1 2023-10 -> 2026-08.
Costs: 1pip + 0.5pip slippage ~= 0.014% RT.  IS <= 2025-06-30.

| variant | n | mean%/tr | IS t | p_is | OOS% | OOS t | WF% | p_wf | boot | trim | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| h4h_momentum | 178 | +0.032 | +2.360 | 0.016 | +0.006 | +0.270 | +0.022 | 0.567 | 0.088 | +0.895 | **FAIL** |
| h8h_momentum | 178 | +0.005 | +0.640 | 0.272 | +-0.015 | +-0.520 | +-0.005 | 0.673 | 0.583 | +0.030 | **FAIL** |
| h24h_momentum | 178 | +0.045 | +1.700 | 0.049 | +0.001 | +0.020 | +0.024 | 0.552 | 0.197 | +1.022 | **FAIL** |
| h48h_momentum | 178 | +0.014 | +1.230 | 0.108 | +-0.085 | +-1.020 | +0.007 | 0.453 | 0.421 | -1.621 | **FAIL** |

Failed stages:

- h4h_momentum: S1; S2; S4; boot
- h8h_momentum: S1; S2; S3; S4; boot
- h24h_momentum: S1; S2; S4; boot
- h48h_momentum: S1; S2; S3; S4; boot; trim