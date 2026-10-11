# Results — scenario `novel_attack`

Transactions: 33,286 · fraud rate 2.92% · test window 6,933 txns (457 fraud)

## Operating point A — fixed alert budget (validation FPR ≤ 1%)

| Detector | Recall | Precision | FPR | Alerts | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| rules | 0.103 | 0.635 | 0.0042 | 74 | 0.659 | 0.962 |
| isolation_forest | 0.803 | 0.834 | 0.0113 | 440 | 0.892 | 0.985 |
| logit_transaction_only | 0.162 | 0.860 | 0.0019 | 86 | 0.262 | 0.457 |
| logit_graph | 0.160 | 0.948 | 0.0006 | 77 | 0.262 | 0.293 |
| hybrid_graph_anomaly | 0.755 | 0.901 | 0.0059 | 383 | 0.897 | 0.986 |

### Recall by fraud pattern (alert budget)

| Detector | card_testing | ring | takeover |
|---|---|---|---|
| rules | 0.000 | 0.329 | 0.392 |
| isolation_forest | 0.963 | 0.659 | 0.020 |
| logit_transaction_only | 0.000 | 0.659 | 0.392 |
| logit_graph | 0.000 | 0.805 | 0.137 |
| hybrid_graph_anomaly | 0.907 | 0.610 | 0.020 |

## Operating point B — false positives at the rule baseline's test recall (0.103)

| Detector | Test recall | False positives | FP reduction vs rules |
|---|---|---|---|
| rules | 0.103 | 27 | +0.0% |
| isolation_forest | 0.103 | 0 | +100.0% |
| logit_transaction_only | 0.103 | 5 | +81.5% |
| logit_graph | 0.103 | 0 | +100.0% |
| hybrid_graph_anomaly | 0.103 | 0 | +100.0% |

### False positives needed to reach a given fraud recall (test window)

| Recall | rules | isolation_forest | logit_transaction_only | logit_graph | hybrid_graph_anomaly |
|---|---|---|---|---|---|
| 0.3 | 47 | 0 | 2257 | 5456 | 0 |
| 0.5 | 47 | 3 | 4213 | 6476 | 2 |
| 0.7 | 157 | 25 | 5173 | 6476 | 21 |

## Live replay (one transaction at a time)

- Screened 6,933 transactions, 383 alerts (35 supervised arm, 348 anomaly arm)
- Latency p50 / p95 / p99: 9.65 / 13.46 / 15.21 ms
- Mean top-3 reason agreement across re-estimated models: 0.974
- Alerts whose reason passed the 0.80 stability gate: 98.2%
- Audit records: 6,933 · chain valid: True · coverage 100%

## Endeavor targets

| Target | Goal | Observed | Met |
|---|---|---|---|
| fp_reduction_vs_rules | >= 20% fewer false positives than rules at recall 0.7 | 86.6% | yes |
| latency_ms_p99 | < 100 ms | 15.208 | yes |
| top3_stability_mean | >= 0.80 | 0.974 | yes |
| audit_coverage | 100% | 100.0% | yes |

## Example alerts

- `T0026522` (stability 1.00): Flagged as unusual compared with normal customers because this network address is linked to 2 card(s) that already had chargebacks; this network address has been used with 7 different cards; this device is linked to 1 card(s) that already had chargebacks.
- `T0026598` (stability 0.83): Flagged because the card was used from a device it has never used before; this device has been used with 8 different cards; the amount ($61.87) is high for this store.
- `T0026668` (stability 0.83): Flagged because the card was used from a device it has never used before; this network address has been used with 8 different cards; this device has been used with 7 different cards.
- `T0026713` (stability 1.00): Flagged as unusual compared with normal customers because this device has been used with 9 different cards; this network address has been used with 7 different cards; this device is linked to 1 card(s) that already had chargebacks.
- `T0026716` (stability 0.83): Flagged as unusual compared with normal customers because this device is linked to 2 card(s) that already had chargebacks; this network address is linked to 1 card(s) that already had chargebacks; it was placed between midnight and 6 in the morning.
