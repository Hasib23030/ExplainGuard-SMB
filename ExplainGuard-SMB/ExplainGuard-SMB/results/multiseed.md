# Multi-seed robustness (seeds 7, 11, 23)

Alert budget: validation FPR ≤ 1%. FP columns: false positives on the test window needed to reach the given recall.

| Scenario | Seed | Rules recall | Graph-logit recall | Hybrid recall | Hybrid precision | FP@0.5 rules | FP@0.5 hybrid | FP@0.7 rules | FP@0.7 hybrid | ≥20% FP target met | p99 ms | Top-3 stability | Audit valid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| novel_attack | 7 | 0.187 | 0.339 | 0.848 | 0.927 | 32 | 1 | 294 | 8 | yes | 15.5 | 0.939 | yes |
| novel_attack | 11 | 0.103 | 0.160 | 0.755 | 0.901 | 47 | 2 | 157 | 21 | yes | 15.2 | 0.974 | yes |
| novel_attack | 23 | 0.091 | 0.179 | 0.852 | 0.871 | 84 | 5 | 84 | 9 | yes | 15.6 | 0.930 | yes |
| standard | 7 | 0.315 | 0.547 | 0.508 | 1.000 | 34 | 0 | 149 | 47 | yes | 15.9 | 0.937 | yes |
| standard | 11 | 0.203 | 0.443 | 0.456 | 1.000 | 47 | 1 | 47 | 121 | no | 15.0 | 0.898 | yes |
| standard | 23 | 0.227 | 0.546 | 0.599 | 0.867 | 85 | 8 | 552 | 140 | yes | 15.9 | 0.944 | yes |

| Scenario | Hybrid recall (mean ± sd) | Rules recall (mean ± sd) | FP target met | Median p99 ms | Mean stability |
|---|---|---|---|---|---|
| standard | 0.521 ± 0.059 | 0.248 ± 0.048 | 2/3 | 15.9 | 0.926 |
| novel_attack | 0.818 ± 0.045 | 0.127 ± 0.043 | 3/3 | 15.5 | 0.948 |
