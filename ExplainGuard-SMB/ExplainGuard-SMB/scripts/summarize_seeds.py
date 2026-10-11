"""Summarise per-seed results already produced by scripts/multiseed.py (no re-run)."""
import json
from pathlib import Path

import numpy as np

rows = []
for p in sorted(Path("results").glob("seed_*/results_*.json")):
    r = json.loads(p.read_text())
    b = r["operating_point_alert_budget"]["results"]
    c = r["operating_point_equal_recall"]["false_positives_at_recall"]
    rows.append((r["scenario"], r["config"]["seed"], b["rules"]["recall"], b["logit_graph"]["recall"],
                 b["hybrid_graph_anomaly"]["recall"], b["hybrid_graph_anomaly"]["precision"],
                 c["0.5"]["rules"], c["0.5"]["hybrid_graph_anomaly"], c["0.7"]["rules"],
                 c["0.7"]["hybrid_graph_anomaly"], r["targets"]["fp_reduction_vs_rules"]["met"],
                 r["live_replay"]["latency_ms_p99"], r["live_replay"]["top3_stability_mean"],
                 r["targets"]["audit_coverage"]["met"]))
L = ["# Multi-seed robustness (seeds 7, 11, 23)", "",
     "Alert budget: validation FPR ≤ 1%. FP columns: false positives on the test window needed to reach the given recall.", "",
     "| Scenario | Seed | Rules recall | Graph-logit recall | Hybrid recall | Hybrid precision | FP@0.5 rules | FP@0.5 hybrid | FP@0.7 rules | FP@0.7 hybrid | ≥20% FP target met | p99 ms | Top-3 stability | Audit valid |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for x in sorted(rows):
    L.append("| " + " | ".join([x[0], str(x[1])] + [f"{v:.3f}" for v in x[2:6]] + [str(v) for v in x[6:10]]
                              + ["yes" if x[10] else "no", f"{x[11]:.1f}", f"{x[12]:.3f}", "yes" if x[13] else "no"]) + " |")
L += ["", "| Scenario | Hybrid recall (mean ± sd) | Rules recall (mean ± sd) | FP target met | Median p99 ms | Mean stability |", "|---|---|---|---|---|---|"]
for s in ("standard", "novel_attack"):
    xs = [x for x in rows if x[0] == s]
    L.append(f"| {s} | {np.mean([x[4] for x in xs]):.3f} ± {np.std([x[4] for x in xs]):.3f} | "
             f"{np.mean([x[2] for x in xs]):.3f} ± {np.std([x[2] for x in xs]):.3f} | "
             f"{sum(x[10] for x in xs)}/{len(xs)} | {np.median([x[11] for x in xs]):.1f} | {np.mean([x[12] for x in xs]):.3f} |")
Path("results/multiseed.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
