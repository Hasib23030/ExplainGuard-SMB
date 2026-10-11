---
title: "ExplainGuard-SMB: Joint Evaluation of Detection, Latency, Explanation Stability and Auditability for Real-Time Fraud Screening in Small Online Businesses"
author: "Hasibur Rahman"
date: "October 2026 — Technical Report v0.1 (draft)"
---

> **Draft notes for the author (delete before posting):** (1) Check every statistic in
> Section 1 against its original source and update the year if needed. (2) Fill in the full
> reference for your co-authored fraud-detection paper [12]. (3) Insert the Zenodo DOI and
> the GitHub URL. (4) Re-run `explainguard benchmark` and `scripts/multiseed.py` on your own
> machine and paste your numbers if they differ.

## Abstract

Small online businesses absorb much of the cost of payment fraud but rarely have tools that
detect coordinated fraud, explain each alert in plain language, and keep a verifiable record
of every decision. Published fraud-detection studies usually report accuracy alone. We
present ExplainGuard-SMB, an open benchmark and reference toolkit that evaluates detectors
jointly on (i) recall under a fixed alert budget and false positives at equal recall,
(ii) end-to-end per-transaction latency, (iii) the stability of top-3 explanation reasons
under model re-estimation, and (iv) coverage of a tamper-evident decision log aligned with
the NIST AI Risk Management Framework. Using a synthetic small-merchant generator with
delayed chargebacks and leakage-safe streaming graph features, we compare a rule baseline,
an Isolation Forest, transaction-only and graph-feature logistic models, and a hybrid
detector that combines a supervised graph arm with an unsupervised anomaly arm. Across three
seeds, graph features roughly doubled recall over rules at a ≤1% false-positive budget
(0.52 vs. 0.25). When a card-testing attack appeared only in the test window, the supervised
model alone detected none of it, while the hybrid detector recovered 97% (seed 7), raising
overall recall from 0.13 (rules) to 0.82 (mean of three seeds). All six runs met the latency
(p99 ≈ 15–16 ms), explanation-stability (0.90–0.97 mean top-3 agreement) and audit-coverage
targets. The false-alarm target (≥20% fewer false positives than rules at recall 0.70) was
met in five of six runs. Code, data generator, protocol and results are released under the
MIT licence.

## 1. Problem

Small businesses make up 99.9% of U.S. firms [1]. Reported internet-crime and consumer-fraud
losses in the United States run to tens of billions of dollars a year [2, 3], and merchants
bear costs well beyond the face value of a fraudulent order once chargebacks, fees and labour
are included [4]. AI adoption among small businesses remains low [5].

Three gaps limit the tools available to these firms:

1. **Detection.** Fraud rings reuse devices and network addresses across many stolen cards.
   The signal lies in relationships, but rule engines and per-transaction scores evaluate one
   payment at a time.
2. **Explanation.** Complex models return a score without a reason. Feature-attribution
   methods can also disagree with each other and change across re-trainings [6], so an
   explanation shown to a merchant may not be reliable.
3. **Audit.** Even when a reason exists, it is rarely recorded in a form that can later be
   verified by a bank, an insurer or an investigator. The NIST AI RMF names accountability,
   transparency and explainability as characteristics of trustworthy AI [7] but leaves
   implementation to practitioners.

## 2. Contributions

1. A **synthetic small-merchant transaction generator** with three fraud patterns
   (organized rings, card testing, account takeover) and delayed chargebacks. It needs no
   private data.
2. **Leakage-safe streaming graph features** over the card–device–IP–merchant network,
   where fraud labels become visible only after their chargeback time.
3. A **pre-registered evaluation protocol** that scores detectors jointly on detection,
   false alarms at equal recall, latency, explanation stability and audit coverage, including
   a novel-attack scenario.
4. A **reference screening toolkit** with stability-gated plain-language reasons and a
   SHA-256 hash-chained audit log mapped to NIST AI RMF functions.

## 3. Method

### 3.1 Data generator
Ninety days of activity for 40 merchants and 3,000 customers (≈33,000 transactions, 2.8%
fraud). Legitimate customers have one or two cards and devices and favor three merchants.
Fraud rings use 2–4 devices and 2–5 network addresses with 8–25 stolen cards. Card-testing
bursts send 6–20 sub-$3 charges from one device within minutes. Takeovers use one stolen card
on a new device for a high amount. Each fraud receives a chargeback 5–30 days later.

### 3.2 Features
Seven transaction features (amount, deviation from the card's median, night-time, card
velocity, new device, new IP, very small amount) and nine graph features (distinct cards per
device and per IP, device velocity and small-charge velocity in the last hour, number of
already-charged-back cards linked to the device and to the IP, two-hop charged-back cards
through the card's devices, distinct devices per card, and the merchant's 30-day chargeback
rate). All features are computed before the transaction is added to the graph.

### 3.3 Detectors
- **Rules:** weighted rules for high amount, new device, night-time, card velocity and amount spikes.
- **Isolation Forest** [8] trained on legitimate traffic.
- **Logistic models** on standardized features (transaction-only, and transaction + graph).
  Their per-feature contributions sum exactly to the log-odds, so explanations are faithful
  by construction.
- **Hybrid:** the graph logistic arm OR the anomaly arm. Each arm receives half of the
  alert budget on validation legitimate traffic. The combined score is the larger
  calibrated margin.

### 3.4 Protocol
Time split 60/20/20. Training uses only labels matured by the end of the training window.
Thresholds are set on validation (FPR ≤ 1%). Test metrics: recall, precision, FPR, PR-AUC,
per-pattern recall, and false positives needed to reach recall 0.3/0.5/0.7. The test window
is then replayed one transaction at a time through the screener to measure latency,
explanation stability and audit coverage.

**Explanation stability.** The supervised arm is re-estimated on four bootstrap resamples.
For each alert, stability is the mean share of top-3 reason codes shared between the deployed
model and each resample. Reasons with stability below 0.80 are withheld.

**Audit.** Each decision is serialized canonically with the previous record's hash and its
own SHA-256 hash. Verification recomputes the chain and reports the first altered, deleted or
reordered record.

## 4. Results

### 4.1 Seed 7, novel-attack scenario (test: 6,840 transactions, 552 fraud)

| Detector | Recall | Precision | Card testing | Ring | Takeover |
|---|---|---|---|---|---|
| Rules | 0.187 | 0.798 | 0.000 | 0.396 | 0.655 |
| Isolation Forest | 0.743 | 0.876 | 0.976 | 0.521 | 0.036 |
| Logistic, transaction only | 0.266 | 0.907 | 0.000 | 0.627 | 0.745 |
| Logistic, graph | 0.339 | 0.878 | 0.000 | 0.917 | 0.582 |
| Hybrid | **0.848** | **0.927** | 0.970 | 0.775 | 0.345 |

False positives needed for recall 0.70: rules 294, hybrid 8.

### 4.2 Seed 7, standard scenario (test: 6,599 transactions, 311 fraud)

| Detector | Recall | Precision | PR-AUC |
|---|---|---|---|
| Rules | 0.315 | 0.790 | 0.672 |
| Logistic, transaction only | 0.376 | 0.951 | 0.798 |
| Logistic, graph | 0.547 | 1.000 | 0.918 |
| Hybrid | 0.508 | 1.000 | 0.824 |

False positives needed for recall 0.70: rules 149, graph logistic 13, hybrid 47.

### 4.3 Robustness across seeds (7, 11, 23)

| Scenario | Hybrid recall | Rules recall | FP target met | Median p99 latency | Mean stability |
|---|---|---|---|---|---|
| Standard | 0.521 ± 0.059 | 0.248 ± 0.048 | 2/3 | 15.9 ms | 0.926 |
| Novel attack | 0.818 ± 0.045 | 0.127 ± 0.043 | 3/3 | 15.5 ms | 0.948 |

All six runs produced valid audit chains covering 100% of decisions. In the failed run
(standard, seed 11) the hybrid detector needed 121 false positives to reach recall 0.70
against 47 for rules. At recall 0.50 it needed 1 against 47.

## 5. Discussion

- **Relational features matter.** Adding graph features raised recall on organized rings
  from 0.14 to 0.57 at the same alert budget (seed 7, standard), consistent with the premise
  that coordinated fraud is visible in shared infrastructure.
- **A supervised model is not enough.** A model trained on past chargebacks missed every
  transaction of an attack it had never seen. A modest share of the alert budget given to an
  unsupervised arm recovered it. This trade-off is easy for a small business to understand
  and configure.
- **Trade-off at high recall.** In the standard scenario, giving half the budget to the anomaly
  arm sometimes costs precision at high recall, mainly on single-card takeovers that carry
  little relational signal. Operators who expect few novel attacks can shift the budget toward
  the supervised arm. Future versions will learn this split.
- **Stable, faithful reasons are achievable in real time.** Exact linear attributions and a
  bootstrap stability gate let 86–89% of alerts show a reason that passed the
  0.80 agreement gate (seed 7), within a ~15 ms budget in pure Python.

## 6. Limitations and next steps

Results come from synthetic data that encode the author's assumptions. They are evidence
that the protocol and toolkit work, not that the reported numbers will hold on real
merchant data. Next steps: (i) loaders and results for the public IEEE-CIS [9] and
PaySim [10] datasets; (ii) GNN baselines (GraphSAGE [11], GAT [13]) with GNNExplainer [14]
and SHAP [15] under the same protocol; (iii) concept-drift scenarios; (iv) consenting pilots
with small online businesses and the institutions that serve them; (v) a practitioner guide.

## 7. Availability

Code, generator, protocol, tests and results: GitHub `[URL]`, archived at Zenodo `[DOI]`,
MIT licence. All numbers in this report can be reproduced with
`explainguard benchmark` and `python scripts/multiseed.py 7 11 23`.

## References

[1] U.S. Small Business Administration, Office of Advocacy. *Frequently Asked Questions about Small Business* (latest edition). [verify figures]
[2] Federal Bureau of Investigation, Internet Crime Complaint Center. *Internet Crime Report* (latest edition). [verify figures]
[3] Federal Trade Commission. *Consumer Sentinel Network Data Book* (latest edition). [verify figures]
[4] LexisNexis Risk Solutions. *True Cost of Fraud Study: U.S. and Canada, Retail and E-commerce* (latest edition). [verify figures]
[5] U.S. Census Bureau, Business Trends and Outlook Survey; SBA Office of Advocacy analysis of AI use by small businesses. [verify figures]
[6] S. Krishna, T. Han, A. Gu, J. Pombra, S. Jabbari, S. Wu, H. Lakkaraju. "The Disagreement Problem in Explainable Machine Learning: A Practitioner's Perspective." arXiv:2202.01602, 2022.
[7] National Institute of Standards and Technology. *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, NIST AI 100-1, January 2023.
[8] F. T. Liu, K. M. Ting, Z.-H. Zhou. "Isolation Forest." *IEEE International Conference on Data Mining (ICDM)*, 2008.
[9] IEEE Computational Intelligence Society and Vesta Corporation. *IEEE-CIS Fraud Detection* dataset, Kaggle, 2019.
[10] E. A. Lopez-Rojas, A. Elmir, S. Axelsson. "PaySim: A Financial Mobile Money Simulator for Fraud Detection." *European Modeling and Simulation Symposium (EMSS)*, 2016.
[11] W. L. Hamilton, R. Ying, J. Leskovec. "Inductive Representation Learning on Large Graphs." *NeurIPS*, 2017.
[12] [Co-authors], H. Rahman, et al. "Detecting Financial Fraud in Real-Time Transactions Using Graph Neural Networks and Anomaly Detection Techniques." [Journal, year, DOI — fill in exactly as published.]
[13] P. Veličković, G. Cucurull, A. Casanova, A. Romero, P. Liò, Y. Bengio. "Graph Attention Networks." *ICLR*, 2018.
[14] R. Ying, D. Bourgeois, J. You, M. Zitnik, J. Leskovec. "GNNExplainer: Generating Explanations for Graph Neural Networks." *NeurIPS*, 2019.
[15] S. M. Lundberg, S.-I. Lee. "A Unified Approach to Interpreting Model Predictions." *NeurIPS*, 2017.
