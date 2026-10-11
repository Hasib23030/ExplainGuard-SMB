"""Robustness check: rerun the full protocol on several independent random seeds."""
import json
import sys
from pathlib import Path

import numpy as np

from explainguard.benchmark import TARGET_RECALL, run_benchmark
from explainguard.generator import GeneratorConfig

seeds = [int(s) for s in sys.argv[1:]] or [7, 11, 23]
rows = []
for scen in ("standard", "novel_attack"):
    for sd in seeds:
        cfg = GeneratorConfig(seed=sd, card_testing_start_day=72 if scen == "novel_attack" else 0)
        r = run_benchmark(cfg, out_dir=f"results/seed_{sd}", scenario=scen)
        b = r["operating_point_alert_budget"]["results"]
        rows.append({"scenario": scen, "seed": sd,
                     "rules_recall": b["rules"]["recall"], "hybrid_recall": b["hybrid_graph_anomaly"]["recall"],
                     "logit_graph_recall": b["logit_graph"]["recall"],
                     "hybrid_precision": b["hybrid_graph_anomaly"]["precision"],
                     "fp_reduction": r["targets"]["fp_reduction_vs_rules"]["observed"],
                     "p99_ms": r["live_replay"]["latency_ms_p99"],
                     "stability": r["live_replay"]["top3_stability_mean"],
                     "audit_ok": r["targets"]["audit_coverage"]["met"]})
Path("results/multiseed.json").write_text(json.dumps(rows, indent=2))
L = ["# Multi-seed robustness", "", f"Seeds: {seeds}. Alert budget: validation FPR <= 1%. "
     f"FP reduction measured at recall {TARGET_RECALL}.", "",
     "| Scenario | Rules recall | Graph-logit recall | Hybrid recall | Hybrid precision | FP reduction vs rules | p99 latency (ms) | Top-3 stability | Audit valid |",
     "|---|---|---|---|---|---|---|---|---|"]
for scen in ("standard", "novel_attack"):
    rs = [r for r in rows if r["scenario"] == scen]
    f = lambda k: f"{np.mean([r[k] for r in rs]):.3f} ± {np.std([r[k] for r in rs]):.3f}"
    L.append(f"| {scen} | {f('rules_recall')} | {f('logit_graph_recall')} | {f('hybrid_recall')} | "
             f"{f('hybrid_precision')} | {f('fp_reduction')} | {f('p99_ms')} | {f('stability')} | "
             f"{all(r['audit_ok'] for r in rs)} |")
Path("results/multiseed.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
