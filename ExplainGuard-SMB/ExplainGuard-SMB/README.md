# ExplainGuard-SMB

**An explainable, auditable, graph-aware fraud-screening benchmark and toolkit for small U.S. online businesses.**

[![CI](https://github.com/YOUR-GITHUB-USERNAME/ExplainGuard-SMB/actions/workflows/ci.yml/badge.svg)](../../actions)
License: MIT · Python ≥ 3.10 · Version 0.1.0

ExplainGuard-SMB tests fraud detectors on four things at once, instead of on accuracy alone:

1. **Detection** of coordinated fraud under a fixed alert budget, with fewer false alarms than rules.
2. **Speed**: end-to-end decision time per transaction, measured one transaction at a time.
3. **Explanation stability**: whether the plain-language reason for an alert stays the same when the model is re-estimated. Unstable reasons are withheld.
4. **Auditability**: every decision is written to a tamper-evident (SHA-256 hash-chained) log.

It is the first public release of *Project 1 (Explainable Graph Fraud-Detection Benchmark)* and the core of *Project 2 (Auditable Fraud-Screening Toolkit)* in the author's research plan.

---

## Why this exists

Fraud rings share devices, rotate stolen cards and spread activity across many accounts. The warning sign is in the **connections** between cards, devices, network addresses and merchants. Per-transaction rules and risk scores usually miss it.

Large banks and payment platforms build their own systems for this. Small online sellers, their bookkeepers, and the small processors that serve them usually have two options: rigid rules, or opaque third-party scores they cannot check. Those scores give no reason a person can act on and leave no record they can show a bank, an insurer or an investigator.

Three gaps, and how this repository addresses each one:

| Gap | What ExplainGuard-SMB does |
|---|---|
| **Detection**: one-payment-at-a-time rules miss organized fraud | Streaming graph features over the card–device–IP–merchant network (shared devices, linked chargebacks, two-hop links, velocity), plus an unsupervised arm for attacks never seen before |
| **Explanation**: models return a bare score, and explanation methods can be unstable | Exact additive attributions turned into plain-language reasons, shown only when they pass a re-estimation stability test |
| **Audit**: reasons are rarely recorded in a verifiable form | Append-only, hash-chained decision log with inputs, model version, reason and outcome, mapped to the NIST AI RMF functions |

## Results (v0.1, synthetic data, pre-registered protocol)

All numbers below are produced by `explainguard benchmark` on the synthetic small-merchant data in this repository. They come from an **experimental setting** and are not results from real merchants. See [Limitations](#limitations).

**Seed 7, `novel_attack` scenario** (a card-testing attack appears only in the test window, so the supervised models have never seen a labeled example of it):

| Detector | Recall at ≤1% FPR budget | Precision | Card-testing recall | Ring recall | Takeover recall |
|---|---|---|---|---|---|
| Rules baseline | 0.187 | 0.798 | 0.000 | 0.396 | 0.655 |
| Graph model only (supervised) | 0.339 | 0.878 | 0.000 | 0.917 | 0.582 |
| **Hybrid: graph + anomaly** | **0.848** | **0.927** | **0.970** | 0.775 | 0.345 |

**Across 3 independent seeds × 2 scenarios** ([results/multiseed.md](results/multiseed.md)):

| Pre-registered target | Result |
|---|---|
| ≥ 20% fewer false positives than rules at recall 0.70 | Met in **5 of 6** runs (3/3 novel-attack, 2/3 standard; failed on standard seed 11) |
| p99 decision time < 100 ms | Met in 6/6 (≈15–16 ms, single CPU core, pure Python) |
| Mean top-3 reason agreement ≥ 0.80 | Met in 6/6 (0.898–0.974) |
| 100% of decisions in a verifiable log | Met in 6/6 |

Main findings:
- **Graph features roughly double recall over rules** at the same alert budget (standard scenario: 0.52 vs 0.25, mean of 3 seeds).
- **A supervised model alone is blind to a new attack** (card-testing recall 0.000). The anomaly arm recovers it (0.97), which is why the toolkit uses both.
- **Account takeover with a single stolen card** carries little relational signal and stays the hardest pattern. At high recall it drives the one failed run. This is reported, not hidden.

Example alert reason, generated automatically and stability-checked:

> *Flagged because this device has been used with 11 different cards; the amount ($108.51) is high for this store; the card was used from a device it has never used before.*

## Install and run

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/ExplainGuard-SMB.git
cd ExplainGuard-SMB
pip install -e ".[dev]"
pytest -q                                   # 24 tests
explainguard benchmark --out results        # full protocol, both scenarios (~5 min)
explainguard verify-log results/audit_log_sample.jsonl
python examples/quickstart.py               # train, then screen live with reasons
```

Use your own data, for example a transaction export with tokenized card, device and IP identifiers (schema: [docs/DATA_SCHEMA.md](docs/DATA_SCHEMA.md)):

```bash
explainguard benchmark --data my_transactions.csv --out my_results
```

## How it works

```
transaction ─▶ StreamingGraphFeaturizer ─▶ HybridDetector ─────────────▶ Screener ─▶ AuditLog
               (state before this txn;     supervised graph arm   OR     reason +       (hash chain,
                chargebacks visible only   anomaly arm, each with        stability      verify_log)
                after they arrive)         half the alert budget         gate
```

| Module | Purpose |
|---|---|
| `generator.py` | Synthetic small-merchant data with fraud rings, card testing and account takeover; delayed chargebacks |
| `features.py` | Leakage-safe streaming features: 7 transaction features and 9 graph-neighborhood features |
| `models.py` | Rule baseline, Isolation Forest, explainable logistic model, hybrid two-arm detector |
| `explain.py` | Plain-language templates, top-k reasons, top-k agreement and stability scoring |
| `audit.py` | Append-only SHA-256 hash-chained log with tamper detection and localization |
| `toolkit.py` | `Screener`: one-transaction-at-a-time screening with stability-gated reasons |
| `benchmark.py` | The evaluation protocol ([docs/PROTOCOL.md](docs/PROTOCOL.md)) |

Design choices:
- **No label leakage.** Features are computed before each transaction is added. A fraud label reaches the graph only after its chargeback date, and models train only on labels that had arrived by the end of the training window.
- **Faithful explanations.** The supervised arm is a standardized logistic model, so each reason is an exact share of the score, not a post-hoc approximation.
- **Honest operating points.** Thresholds are tuned on validation data only and evaluated once on a later test window.

## Governance: NIST AI RMF

Each record in the audit log links its fields to the four NIST AI RMF 1.0 functions: GOVERN (model version), MAP (inputs and features), MEASURE (score and stability) and MANAGE (decision). See [docs/NIST_AI_RMF_MAPPING.md](docs/NIST_AI_RMF_MAPPING.md). This is an engineering mapping, not a compliance certification.

## Limitations

- **Synthetic data.** The generator encodes the author's assumptions about fraud patterns. Real-world performance must be confirmed on public datasets (for example IEEE-CIS, PaySim) and in consenting pilots. That work is planned for v0.2 and later.
- The supervised arm is linear on engineered graph features, not a graph neural network. GNN baselines (GraphSAGE, GAT) with GNNExplainer are on the roadmap and will be evaluated under the same protocol.
- Stability is measured by bootstrap re-estimation of the supervised arm with a shared anomaly model.
- The hash chain gives tamper evidence, not prevention. Operators should publish or escrow the latest head hash.
- This is research software, not a certified fraud-prevention product.

## Roadmap

| Version | Planned work |
|---|---|
| 0.2 | IEEE-CIS and PaySim loaders; concept-drift scenario; GraphSAGE/GAT baselines (optional PyTorch extra) |
| 0.3 | Simple web interface for CSV exports; printable alert and audit report for chargeback disputes |
| 1.0 | Validation on multiple public datasets and consenting pilots; practitioner guide for small businesses |

## Citation

See [CITATION.cff](CITATION.cff). A DOI will be added after the first Zenodo release.

```
Rahman, H. (2026). ExplainGuard-SMB: An Explainable, Auditable, Graph-Aware Fraud-Screening
Benchmark and Toolkit for Small Online Businesses (Version 0.1.0) [Computer software].
```

## License

MIT. Free for any use, including commercial use.
