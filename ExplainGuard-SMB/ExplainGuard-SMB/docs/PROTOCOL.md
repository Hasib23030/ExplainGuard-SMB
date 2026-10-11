# Evaluation protocol (v0.1, fixed before results were produced)

This protocol is fixed in advance and versioned with the code, so that results cannot
be tuned after the fact. Any change requires a new protocol version.

## 1. Data
- **Primary:** synthetic small-merchant data from `explainguard.generator` (90 days,
  40 merchants, 3,000 customers, three fraud patterns: `ring`, `card_testing`, `takeover`).
- **External:** any CSV with the schema in [DATA_SCHEMA.md](DATA_SCHEMA.md) can be
  passed with `explainguard benchmark --data file.csv`.
- No private or personal data is used or required.

## 2. Scenarios
| Scenario | Description |
|---|---|
| `standard` | All fraud patterns appear throughout the 90 days. |
| `novel_attack` | Card-testing starts on day 72, i.e. only in the test window. Supervised models never see a labelled example of it. |

## 3. Features (leakage control)
Transactions are processed strictly in time order. Features use only information
available *before* the transaction, and a fraud label becomes visible to the graph
features only after its chargeback timestamp (5–30 days after the fraud).

## 4. Splits and labels
- Time-based split: train 60% / validation 20% / test 20% of the time range.
- Training labels: only frauds whose chargeback arrived by the end of the training window
  ("matured" labels). Late chargebacks are treated as unknown, as in real operations.
- Thresholds are tuned on validation traffic only.
- Test metrics use final ground truth.

## 5. Detectors
`rules` (transparent rule engine), `isolation_forest` (unsupervised), `logit_transaction_only`
(no relational features), `logit_graph` (transaction + graph features), and
`hybrid_graph_anomaly` (supervised graph arm OR anomaly arm, each with half the alert budget).

## 6. Operating points and metrics
- **A. Fixed alert budget.** Threshold such that validation false-positive rate ≤ 1%.
  Report test recall, precision, FPR, alert count, PR-AUC, ROC-AUC and recall per pattern.
- **B. Equal recall.** False positives each detector needs to reach the same test recall
  (0.3, 0.5, 0.7, and the rule baseline's own recall). This compares ranking quality.
- **C. Live replay.** The test window is replayed one transaction at a time through
  `Screener` (feature update + scoring + explanation + audit write), measuring end-to-end
  latency, explanation stability and audit coverage.

## 7. Explanation stability
The supervised arm is re-estimated on 4 bootstrap resamples of the training data (5 models
in total). For each alert, stability = mean overlap of the top-3 reason codes between the
deployed model and each re-estimated model (0 to 1). A reason is shown to the user only if
stability ≥ 0.80; otherwise it is withheld and the alert is marked for manual review.
For anomaly-arm alerts, reasons are the features most unusual versus normal customers and
stability is computed the same way using each resample's legit-traffic statistics.

## 8. Pre-registered targets
| Target | Measure |
|---|---|
| Fewer false alarms | ≥ 20% fewer false positives than rules at recall 0.70 |
| Real-time speed | p99 end-to-end decision time < 100 ms per transaction |
| Stable explanations | mean top-3 agreement ≥ 0.80 |
| Full auditability | 100% of decisions in a hash chain that verifies |

## 9. Robustness
The full protocol is repeated on independent seeds (`scripts/multiseed.py`); mean ± sd are reported.
