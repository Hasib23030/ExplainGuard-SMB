# Results — scenario `standard`

Transactions: 33,150 · fraud rate 2.78% · test window 6,599 txns (311 fraud)

## Operating point A — fixed alert budget (validation FPR ≤ 1%)

| Detector | Recall | Precision | FPR | Alerts | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| rules | 0.315 | 0.790 | 0.0041 | 124 | 0.672 | 0.963 |
| isolation_forest | 0.424 | 0.978 | 0.0005 | 135 | 0.726 | 0.962 |
| logit_transaction_only | 0.376 | 0.951 | 0.0010 | 123 | 0.798 | 0.982 |
| logit_graph | 0.547 | 1.000 | 0.0000 | 170 | 0.918 | 0.990 |
| hybrid_graph_anomaly | 0.508 | 1.000 | 0.0000 | 158 | 0.824 | 0.977 |

### Recall by fraud pattern (alert budget)

| Detector | card_testing | ring | takeover |
|---|---|---|---|
| rules | 0.000 | 0.367 | 0.655 |
| isolation_forest | 0.897 | 0.320 | 0.000 |
| logit_transaction_only | 0.977 | 0.136 | 0.164 |
| logit_graph | 0.770 | 0.574 | 0.109 |
| hybrid_graph_anomaly | 0.862 | 0.479 | 0.036 |

## Operating point B — false positives at the rule baseline's test recall (0.315)

| Detector | Test recall | False positives | FP reduction vs rules |
|---|---|---|---|
| rules | 0.315 | 24 | +0.0% |
| isolation_forest | 0.315 | 0 | +100.0% |
| logit_transaction_only | 0.315 | 1 | +95.8% |
| logit_graph | 0.315 | 0 | +100.0% |
| hybrid_graph_anomaly | 0.315 | 0 | +100.0% |

### False positives needed to reach a given fraud recall (test window)

| Recall | rules | isolation_forest | logit_transaction_only | logit_graph | hybrid_graph_anomaly |
|---|---|---|---|---|---|
| 0.3 | 21 | 0 | 0 | 0 | 0 |
| 0.5 | 34 | 12 | 30 | 0 | 0 |
| 0.7 | 149 | 249 | 98 | 13 | 47 |

## Live replay (one transaction at a time)

- Screened 6,599 transactions, 158 alerts (103 supervised arm, 55 anomaly arm)
- Latency p50 / p95 / p99: 9.67 / 13.57 / 15.87 ms
- Mean top-3 reason agreement across re-estimated models: 0.937
- Alerts whose reason passed the 0.80 stability gate: 89.2%
- Audit records: 6,599 · chain valid: True · coverage 100%

## Endeavor targets

| Target | Goal | Observed | Met |
|---|---|---|---|
| fp_reduction_vs_rules | >= 20% fewer false positives than rules at recall 0.7 | 68.5% | yes |
| latency_ms_p99 | < 100 ms | 15.866 | yes |
| top3_stability_mean | >= 0.80 | 0.937 | yes |
| audit_coverage | 100% | 100.0% | yes |

## Example alerts

- `T0026551` (stability 0.92): Flagged because the amount ($127.83) is high for this store; the card was used from a device it has never used before; it was placed between midnight and 6 in the morning.
- `T0026552` (stability 0.83): Flagged because this device has been used with 10 different cards; the card was used from a device it has never used before; the amount ($65.17) is high for this store.
- `T0026623` (stability 1.00): Flagged because this device has been used with 11 different cards; the amount ($108.51) is high for this store; the card was used from a device it has never used before.
- `T0026724` (stability 1.00): Flagged because this device has been used with 7 different cards; the amount ($147.54) is high for this store; the card was used from a device it has never used before.
- `T0026810` (stability 1.00): Flagged because this device has been used with 12 different cards; the amount ($160.54) is high for this store; this card was used 2 times in the last 24 hours.
