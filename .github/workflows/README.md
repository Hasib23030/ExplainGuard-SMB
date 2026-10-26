[README.md](https://github.com/user-attachments/files/33980591/README.md)
# ExplainGuard-SMB

[![CI](https://github.com/Hasib23030/ExplainGuard-SMB/actions/workflows/ci.yml/badge.svg)](https://github.com/Hasib23030/ExplainGuard-SMB/actions/workflows/ci.yml)

**Explainable, auditable, graph-aware fraud screening benchmark and toolkit for small U.S. online businesses.**

ExplainGuard-SMB tests fraud detectors on four things at once, instead of accuracy alone:

| Criterion | What is measured |
|---|---|
| Detection | Graph features across shared cards, devices, IP addresses and merchants, plus an unsupervised anomaly arm for unseen attacks, under a fixed alert budget |
| Latency | Decision time per transaction |
| Explanation stability | A plain-language reason is shown only if it stays the same when the model is re-estimated |
| Auditability | Every decision is written to a SHA-256 hash-chained log, mapped to the NIST AI RMF functions |

## Where the code is

All source code, tests, results and documentation are in
[`ExplainGuard-SMB/ExplainGuard-SMB/`](ExplainGuard-SMB/ExplainGuard-SMB/).
The full project README is
[here](ExplainGuard-SMB/ExplainGuard-SMB/README.md).

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/Hasib23030/ExplainGuard-SMB.git
cd ExplainGuard-SMB/ExplainGuard-SMB/ExplainGuard-SMB
pip install -e ".[dev]"

# run the tests
pytest -q

# generate a synthetic small-merchant transaction file
explainguard generate --out transactions.csv --days 90

# run the full benchmark (standard + novel-attack scenarios)
explainguard benchmark --out results --scenario both

# verify a tamper-evident audit log
explainguard verify-log results/audit_log_sample.jsonl
```

## Results

Results on synthetic data are in
[`results/`](ExplainGuard-SMB/ExplainGuard-SMB/results/),
including three random seeds (7, 11, 23) and two scenarios (standard and novel attack).
The technical report is in
[`docs/`](ExplainGuard-SMB/ExplainGuard-SMB/docs/).

## Limitations

- Results use **synthetic data only**; real-world performance is not yet confirmed.
- The supervised arm is a linear model, not a graph neural network (planned for v0.2).
- The hash chain **detects** tampering; it does not prevent it.
- This is research software, not a certified fraud-prevention product.

## Roadmap

- **v0.2** — IEEE-CIS and PaySim data loaders, concept-drift tests, GNN baselines
- **v0.3** — web interface and printable dispute reports
- **v1.0** — validation on several public datasets and consenting pilot deployments

## Citation

See [`CITATION.cff`](ExplainGuard-SMB/ExplainGuard-SMB/CITATION.cff).

## License

MIT — see [`LICENSE`](ExplainGuard-SMB/ExplainGuard-SMB/LICENSE).

**Author:** Hasibur Rahman
