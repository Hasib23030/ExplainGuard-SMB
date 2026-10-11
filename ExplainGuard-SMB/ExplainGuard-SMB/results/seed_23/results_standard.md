# Results — scenario `standard`

Transactions: 33,259 · fraud rate 2.87% · test window 6,746 txns (207 fraud)

## Operating point A — fixed alert budget (validation FPR ≤ 1%)

| Detector | Recall | Precision | FPR | Alerts | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| rules | 0.227 | 0.439 | 0.0092 | 107 | 0.471 | 0.938 |
| isolation_forest | 0.517 | 0.829 | 0.0034 | 129 | 0.654 | 0.950 |
| logit_transaction_only | 0.488 | 0.815 | 0.0035 | 124 | 0.703 | 0.972 |
| logit_graph | 0.546 | 0.869 | 0.0026 | 130 | 0.805 | 0.972 |
| hybrid_graph_anomaly | 0.599 | 0.867 | 0.0029 | 143 | 0.717 | 0.960 |

### Recall by fraud pattern (alert budget)

| Detector | card_testing | ring | takeover |
|---|---|---|---|
| rules | 0.000 | 0.248 | 0.362 |
| isolation_forest | 0.949 | 0.545 | 0.085 |
| logit_transaction_only | 1.000 | 0.380 | 0.340 |
| logit_graph | 0.974 | 0.521 | 0.255 |
| hybrid_graph_anomaly | 0.949 | 0.653 | 0.170 |

## Operating point B — false positives at the rule baseline's test recall (0.227)

| Detector | Test recall | False positives | FP reduction vs rules |
|---|---|---|---|
| rules | 0.227 | 60 | +0.0% |
| isolation_forest | 0.227 | 0 | +100.0% |
| logit_transaction_only | 0.227 | 3 | +95.0% |
| logit_graph | 0.227 | 0 | +100.0% |
| hybrid_graph_anomaly | 0.227 | 0 | +100.0% |

### False positives needed to reach a given fraud recall (test window)

| Recall | rules | isolation_forest | logit_transaction_only | logit_graph | hybrid_graph_anomaly |
|---|---|---|---|---|---|
| 0.3 | 62 | 1 | 3 | 0 | 0 |
| 0.5 | 85 | 15 | 23 | 5 | 8 |
| 0.7 | 552 | 277 | 109 | 52 | 140 |

## Live replay (one transaction at a time)

- Screened 6,746 transactions, 143 alerts (76 supervised arm, 67 anomaly arm)
- Latency p50 / p95 / p99: 9.65 / 13.42 / 15.89 ms
- Mean top-3 reason agreement across re-estimated models: 0.944
- Alerts whose reason passed the 0.80 stability gate: 90.9%
- Audit records: 6,746 · chain valid: True · coverage 100%

## Endeavor targets

| Target | Goal | Observed | Met |
|---|---|---|---|
| fp_reduction_vs_rules | >= 20% fewer false positives than rules at recall 0.7 | 74.6% | yes |
| latency_ms_p99 | < 100 ms | 15.889 | yes |
| top3_stability_mean | >= 0.80 | 0.944 | yes |
| audit_coverage | 100% | 100.0% | yes |

## Example alerts

- `T0026832` (stability 1.00): Flagged as unusual compared with normal customers because this card shares devices with 16 card(s) that had chargebacks; this network address is linked to 1 card(s) that already had chargebacks; this device is linked to 1 card(s) that already had chargebacks.
- `T0026896` (stability 1.00): Flagged as unusual compared with normal customers because it was placed between midnight and 6 in the morning; this network address is linked to 1 card(s) that already had chargebacks; this network address has been used with 4 different cards.
- `T0027086` (stability 1.00): Flagged as unusual compared with normal customers because this device is linked to 2 card(s) that already had chargebacks; this card shares devices with 23 card(s) that had chargebacks; this network address is linked to 1 card(s) that already had chargebacks.
- `T0027257` (stability 1.00): Flagged because the card was used from a device it has never used before; the amount ($137.82) is high for this store; it was placed between midnight and 6 in the morning.
- `T0027497` (stability 1.00): Flagged because the amount ($591.03) is high for this store; the card was used from a device it has never used before; this card was used 1 times in the last 24 hours.
