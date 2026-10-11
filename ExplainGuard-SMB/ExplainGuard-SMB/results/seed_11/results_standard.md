# Results — scenario `standard`

Transactions: 33,286 · fraud rate 2.92% · test window 6,713 txns (237 fraud)

## Operating point A — fixed alert budget (validation FPR ≤ 1%)

| Detector | Recall | Precision | FPR | Alerts | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| rules | 0.203 | 0.640 | 0.0042 | 75 | 0.610 | 0.965 |
| isolation_forest | 0.511 | 0.968 | 0.0006 | 125 | 0.734 | 0.962 |
| logit_transaction_only | 0.498 | 0.983 | 0.0003 | 120 | 0.856 | 0.990 |
| logit_graph | 0.443 | 1.000 | 0.0000 | 105 | 0.895 | 0.986 |
| hybrid_graph_anomaly | 0.456 | 1.000 | 0.0000 | 108 | 0.736 | 0.962 |

### Recall by fraud pattern (alert budget)

| Detector | card_testing | ring | takeover |
|---|---|---|---|
| rules | 0.000 | 0.329 | 0.412 |
| isolation_forest | 0.904 | 0.329 | 0.000 |
| logit_transaction_only | 0.971 | 0.207 | 0.000 |
| logit_graph | 0.769 | 0.305 | 0.000 |
| hybrid_graph_anomaly | 0.817 | 0.280 | 0.000 |

## Operating point B — false positives at the rule baseline's test recall (0.203)

| Detector | Test recall | False positives | FP reduction vs rules |
|---|---|---|---|
| rules | 0.203 | 27 | +0.0% |
| isolation_forest | 0.211 | 0 | +100.0% |
| logit_transaction_only | 0.203 | 0 | +100.0% |
| logit_graph | 0.203 | 0 | +100.0% |
| hybrid_graph_anomaly | 0.203 | 0 | +100.0% |

### False positives needed to reach a given fraud recall (test window)

| Recall | rules | isolation_forest | logit_transaction_only | logit_graph | hybrid_graph_anomaly |
|---|---|---|---|---|---|
| 0.3 | 46 | 0 | 0 | 0 | 0 |
| 0.5 | 47 | 3 | 2 | 0 | 1 |
| 0.7 | 47 | 121 | 59 | 2 | 121 |

## Live replay (one transaction at a time)

- Screened 6,713 transactions, 108 alerts (78 supervised arm, 30 anomaly arm)
- Latency p50 / p95 / p99: 9.50 / 13.04 / 14.95 ms
- Mean top-3 reason agreement across re-estimated models: 0.898
- Alerts whose reason passed the 0.80 stability gate: 83.3%
- Audit records: 6,713 · chain valid: True · coverage 100%

## Endeavor targets

| Target | Goal | Observed | Met |
|---|---|---|---|
| fp_reduction_vs_rules | >= 20% fewer false positives than rules at recall 0.7 | -157.4% | no |
| latency_ms_p99 | < 100 ms | 14.954 | yes |
| top3_stability_mean | >= 0.80 | 0.898 | yes |
| audit_coverage | 100% | 100.0% | yes |

## Example alerts

- `T0026936` (stability 1.00): Flagged as unusual compared with normal customers because this device is linked to 2 card(s) that already had chargebacks; this network address is linked to 1 card(s) that already had chargebacks; it was placed between midnight and 6 in the morning.
- `T0027288` (stability 1.00): Flagged as unusual compared with normal customers because this device has been used with 10 different cards; this network address is linked to 1 card(s) that already had chargebacks; this device is linked to 1 card(s) that already had chargebacks.
- `T0027679` (stability 0.92): Flagged because this device has been used with 11 different cards; this network address has been used with 10 different cards; the amount ($136.16) is high for this store.
- `T0027688` (stability 1.00): Flagged because it is a very small charge, typical of stolen-card testing; this device made 4 purchases in the last hour; the card was used from a device it has never used before.
- `T0027689` (stability 0.92): Flagged because this device made 5 purchases in the last hour; it is a very small charge, typical of stolen-card testing; the card was used from a device it has never used before.
