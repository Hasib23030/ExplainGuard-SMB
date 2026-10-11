# Results — scenario `novel_attack`

Transactions: 33,259 · fraud rate 2.87% · test window 7,047 txns (508 fraud)

## Operating point A — fixed alert budget (validation FPR ≤ 1%)

| Detector | Recall | Precision | FPR | Alerts | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| rules | 0.091 | 0.434 | 0.0092 | 106 | 0.621 | 0.956 |
| isolation_forest | 0.805 | 0.799 | 0.0158 | 512 | 0.892 | 0.980 |
| logit_transaction_only | 0.189 | 0.800 | 0.0037 | 120 | 0.294 | 0.480 |
| logit_graph | 0.179 | 0.827 | 0.0029 | 110 | 0.253 | 0.307 |
| hybrid_graph_anomaly | 0.852 | 0.871 | 0.0098 | 497 | 0.915 | 0.990 |

### Recall by fraud pattern (alert budget)

| Detector | card_testing | ring | takeover |
|---|---|---|---|
| rules | 0.000 | 0.240 | 0.362 |
| isolation_forest | 0.976 | 0.595 | 0.106 |
| logit_transaction_only | 0.003 | 0.537 | 0.638 |
| logit_graph | 0.000 | 0.579 | 0.447 |
| hybrid_graph_anomaly | 0.959 | 0.744 | 0.362 |

## Operating point B — false positives at the rule baseline's test recall (0.091)

| Detector | Test recall | False positives | FP reduction vs rules |
|---|---|---|---|
| rules | 0.091 | 60 | +0.0% |
| isolation_forest | 0.093 | 0 | +100.0% |
| logit_transaction_only | 0.091 | 2 | +96.7% |
| logit_graph | 0.091 | 5 | +91.7% |
| hybrid_graph_anomaly | 0.093 | 3 | +95.0% |

### False positives needed to reach a given fraud recall (test window)

| Recall | rules | isolation_forest | logit_transaction_only | logit_graph | hybrid_graph_anomaly |
|---|---|---|---|---|---|
| 0.3 | 84 | 0 | 280 | 2858 | 4 |
| 0.5 | 84 | 1 | 4540 | 6538 | 5 |
| 0.7 | 84 | 17 | 5356 | 6539 | 9 |

## Live replay (one transaction at a time)

- Screened 7,047 transactions, 497 alerts (77 supervised arm, 420 anomaly arm)
- Latency p50 / p95 / p99: 9.60 / 13.66 / 15.57 ms
- Mean top-3 reason agreement across re-estimated models: 0.930
- Alerts whose reason passed the 0.80 stability gate: 90.7%
- Audit records: 7,047 · chain valid: True · coverage 100%

## Endeavor targets

| Target | Goal | Observed | Met |
|---|---|---|---|
| fp_reduction_vs_rules | >= 20% fewer false positives than rules at recall 0.7 | 89.3% | yes |
| latency_ms_p99 | < 100 ms | 15.565 | yes |
| top3_stability_mean | >= 0.80 | 0.930 | yes |
| audit_coverage | 100% | 100.0% | yes |

## Example alerts

- `T0026218` (stability 1.00): Flagged as unusual compared with normal customers because this device made 1 tiny charges in the last hour; this device made 1 purchases in the last hour; it is a very small charge, typical of stolen-card testing.
- `T0026219` (stability 1.00): Flagged as unusual compared with normal customers because this device made 2 tiny charges in the last hour; this device made 2 purchases in the last hour; this network address is linked to 1 card(s) that already had chargebacks.
- `T0026220` (stability 1.00): Flagged as unusual compared with normal customers because this device made 3 tiny charges in the last hour; this device made 3 purchases in the last hour; this network address is linked to 1 card(s) that already had chargebacks.
- `T0026221` (stability 1.00): Flagged as unusual compared with normal customers because this device made 4 tiny charges in the last hour; this device made 4 purchases in the last hour; this network address is linked to 1 card(s) that already had chargebacks.
- `T0026222` (stability 1.00): Flagged as unusual compared with normal customers because this device made 5 tiny charges in the last hour; this device made 5 purchases in the last hour; this network address is linked to 1 card(s) that already had chargebacks.
