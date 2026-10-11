# Mapping to the NIST AI Risk Management Framework (AI RMF 1.0)

The NIST AI RMF (NIST AI 100-1, January 2023) names four functions: GOVERN, MAP,
MEASURE and MANAGE, and lists "accountable and transparent" and "explainable and
interpretable" among the characteristics of trustworthy AI. The table shows where
ExplainGuard-SMB implements each function. It is an engineering mapping, not a
certification or a compliance claim.

| AI RMF function | What it asks for (summary) | ExplainGuard-SMB implementation |
|---|---|---|
| **GOVERN** | Accountability, documented policies, traceability | Every decision is logged with a content-hashed `model_version` and threshold; the evaluation protocol is versioned ([PROTOCOL.md](PROTOCOL.md)); MIT licence and open code allow independent review |
| **MAP** | Context, intended use, known limitations | Intended users (small online merchants, bookkeepers, small processors) and limitations are documented in the README and technical report; inputs and features are recorded per decision |
| **MEASURE** | Test, evaluate and track trustworthiness | Benchmark measures detection at a fixed alert budget, false alarms at equal recall, latency, and explanation stability; robustness across seeds; novel-attack scenario |
| **MANAGE** | Prioritise and act on risks; respond and recover | Stability gate withholds unreliable reasons; the anomaly arm covers patterns absent from training; the tamper-evident log supports disputes, insurer requests and reports to the FBI IC3 |

Each audit record carries an `rmf` field linking record fields to these functions.
