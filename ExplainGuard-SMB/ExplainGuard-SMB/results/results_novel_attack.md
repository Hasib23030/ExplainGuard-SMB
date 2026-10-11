# Results — scenario `novel_attack`

Transactions: 33,150 · fraud rate 2.78% · test window 6,840 txns (552 fraud)

## Operating point A — fixed alert budget (validation FPR ≤ 1%)

| Detector | Recall | Precision | FPR | Alerts | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| rules | 0.187 | 0.798 | 0.0041 | 129 | 0.728 | 0.963 |
| isolation_forest | 0.743 | 0.876 | 0.0092 | 468 | 0.898 | 0.986 |
| logit_transaction_only | 0.266 | 0.907 | 0.0024 | 162 | 0.399 | 0.612 |
| logit_graph | 0.339 | 0.878 | 0.0041 | 213 | 0.410 | 0.422 |
| hybrid_graph_anomaly | 0.848 | 0.927 | 0.0059 | 505 | 0.946 | 0.993 |

### Recall by fraud pattern (alert budget)

| Detector | card_testing | ring | takeover |
|---|---|---|---|
| rules | 0.000 | 0.396 | 0.655 |
| isolation_forest | 0.976 | 0.521 | 0.036 |
| logit_transaction_only | 0.000 | 0.627 | 0.745 |
| logit_graph | 0.000 | 0.917 | 0.582 |
| hybrid_graph_anomaly | 0.970 | 0.775 | 0.345 |

## Operating point B — false positives at the rule baseline's test recall (0.187)

| Detector | Test recall | False positives | FP reduction vs rules |
|---|---|---|---|
| rules | 0.187 | 26 | +0.0% |
| isolation_forest | 0.187 | 0 | +100.0% |
| logit_transaction_only | 0.187 | 3 | +88.5% |
| logit_graph | 0.187 | 1 | +96.2% |
| hybrid_graph_anomaly | 0.187 | 0 | +100.0% |

### False positives needed to reach a given fraud recall (test window)

| Recall | rules | isolation_forest | logit_transaction_only | logit_graph | hybrid_graph_anomaly |
|---|---|---|---|---|---|
| 0.3 | 32 | 0 | 37 | 8 | 1 |
| 0.5 | 32 | 0 | 2658 | 6158 | 1 |
| 0.7 | 294 | 23 | 4016 | 6288 | 8 |

## Live replay (one transaction at a time)

- Screened 6,840 transactions, 505 alerts (144 supervised arm, 361 anomaly arm)
- Latency p50 / p95 / p99: 9.71 / 13.58 / 15.50 ms
- Mean top-3 reason agreement across re-estimated models: 0.939
- Alerts whose reason passed the 0.80 stability gate: 86.3%
- Audit records: 6,840 · chain valid: True · coverage 100%

## Endeavor targets

| Target | Goal | Observed | Met |
|---|---|---|---|
| fp_reduction_vs_rules | >= 20% fewer false positives than rules at recall 0.7 | 97.3% | yes |
| latency_ms_p99 | < 100 ms | 15.502 | yes |
| top3_stability_mean | >= 0.80 | 0.939 | yes |
| audit_coverage | 100% | 100.0% | yes |

## Example alerts

- `T0026310` (stability 0.92): Flagged because the amount ($127.83) is high for this store; the card was used from a device it has never used before; it was placed between midnight and 6 in the morning.
- `T0026311` (stability 1.00): Flagged because this device has been used with 10 different cards; the card was used from a device it has never used before; the amount ($65.17) is high for this store.
- `T0026313` (stability 0.92): Flagged as unusual compared with normal customers because this network address is linked to 1 card(s) that already had chargebacks; this device is linked to 1 card(s) that already had chargebacks; this card shares devices with 11 card(s) that had chargebacks.
- `T0026314` (stability 0.92): Flagged because the card was used from a device it has never used before; this device has been used with 5 different cards; the amount ($63.82) is high for this store.
- `T0026382` (stability 1.00): Flagged because this device has been used with 11 different cards; the amount ($108.51) is high for this store; the card was used from a device it has never used before.
