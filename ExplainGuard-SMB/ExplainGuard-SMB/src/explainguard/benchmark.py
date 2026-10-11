"""Benchmark protocol (pre-registered in docs/PROTOCOL.md).

1. Generate a synthetic dataset (or load a CSV with the same schema).
2. Compute leakage-safe streaming features.
3. Split by time: train 60% / validation 20% / test 20% of the day range.
4. Train on labels that had *matured* (chargeback received) by the end of the
   training window; tune thresholds on validation labels matured by its end.
5. Evaluate on the test window with final ground truth at two operating points:
   (a) a fixed alert budget (validation FPR <= 1%), and
   (b) equal recall with the rule baseline (to measure false-alarm reduction).
6. Replay the test window one transaction at a time through the Screener to
   measure end-to-end latency, explanation stability and audit-log coverage.
"""
from __future__ import annotations

import json
import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from . import __version__
from .audit import verify_log
from .features import ALL_FEATURES, GRAPH_FEATURES, TXN_FEATURES, StreamingGraphFeaturizer, build_features
from .generator import GeneratorConfig, generate
from .metrics import (confusion_at, ranking_metrics, recall_by_type, threshold_for_alert_rate,
                      threshold_for_recall)
from .models import ExplainableLogit, HybridDetector, IsolationForestDetector, RuleBaseline
from .toolkit import Screener

TARGET_RECALL = 0.7  # pre-registered recall level for the false-alarm comparison
TARGETS = {"fp_reduction_vs_rules": 0.20, "latency_ms_p99": 100.0,
           "top3_stability_mean": 0.80, "audit_coverage": 1.0}


def time_split(df: pd.DataFrame, train_frac=0.6, val_frac=0.2):
    t0, t1 = df["timestamp"].min(), df["timestamp"].max()
    a = t0 + (t1 - t0) * train_frac
    b = t0 + (t1 - t0) * (train_frac + val_frac)
    return df["timestamp"] < a, (df["timestamp"] >= a) & (df["timestamp"] < b), df["timestamp"] >= b, a, b


def matured_labels(df: pd.DataFrame, cutoff: float) -> np.ndarray:
    return ((df["is_fraud"] == 1) & (df["chargeback_time"] <= cutoff)).to_numpy(int)


def run_benchmark(config: GeneratorConfig | None = None, data: pd.DataFrame | None = None,
                  out_dir: str | Path = "results", max_fpr: float = 0.01, n_bootstrap: int = 5,
                  scenario: str = "standard", seed: int = 0) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    config = config or GeneratorConfig()
    df = data if data is not None else generate(config)
    X = build_features(df)
    tr, va, te, a, b = time_split(df)
    y_tr = matured_labels(df[tr], a)
    y_va = matured_labels(df[va], b)
    y_te = df.loc[te, "is_fraud"].to_numpy(int)
    types_te = df.loc[te, "fraud_type"].to_numpy()

    iforest = IsolationForestDetector(ALL_FEATURES, seed=seed).fit(X[tr], y_tr)
    detectors = {
        "rules": RuleBaseline().fit(X[tr]),
        "isolation_forest": iforest,
        "logit_transaction_only": ExplainableLogit(TXN_FEATURES, "logit_transaction_only", seed=seed).fit(X[tr], y_tr),
        "logit_graph": ExplainableLogit(ALL_FEATURES, "logit_graph", seed=seed).fit(X[tr], y_tr),
        "hybrid_graph_anomaly": HybridDetector(ALL_FEATURES, seed=seed, iforest=iforest).fit(X[tr], y_tr),
    }
    legit_va = X[va][y_va == 0]
    detectors["hybrid_graph_anomaly"].calibrate(legit_va, max_fpr)

    s_va = {k: d.score(X[va]) for k, d in detectors.items()}
    s_te = {k: d.score(X[te]) for k, d in detectors.items()}

    # (a) fixed alert budget
    budget = {}
    for k in detectors:
        thr = threshold_for_alert_rate(s_va[k][y_va == 0], max_fpr)
        budget[k] = {"threshold": thr, **confusion_at(s_te[k], y_te, thr),
                     **ranking_metrics(s_te[k], y_te),
                     "recall_by_type": recall_by_type(s_te[k], types_te, thr)}

    # (b) false positives needed to reach the same recall as the rule baseline on the
    #     test window (a ranking-quality comparison, reported separately from (a))
    rule_recall_te = budget["rules"]["recall"]
    equal = {}
    for k in detectors:
        thr = threshold_for_recall(s_te[k], y_te, rule_recall_te)
        equal[k] = {"threshold": thr, **confusion_at(s_te[k], y_te, thr)}
    rule_fp = equal["rules"]["fp"]
    for k in detectors:
        equal[k]["fp_reduction_vs_rules"] = 1.0 - equal[k]["fp"] / max(1, rule_fp)
    curve = {}
    for R in (0.3, 0.5, TARGET_RECALL):
        curve[str(R)] = {k: confusion_at(s_te[k], y_te, threshold_for_recall(s_te[k], y_te, R))["fp"]
                         for k in detectors}

    # explanation-stability ensemble (bootstrap re-estimation of the supervised arm)
    rng = np.random.default_rng(seed + 1)
    Xtr, idx = X[tr].reset_index(drop=True), np.arange(int(tr.sum()))
    ensemble = []
    for i in range(n_bootstrap - 1):
        bs = rng.choice(idx, size=len(idx), replace=True)
        ensemble.append(HybridDetector(ALL_FEATURES, seed=seed + 10 + i, iforest=iforest)
                        .fit(Xtr.iloc[bs], y_tr[bs]).calibrate(legit_va, max_fpr))

    # (c) live replay through the Screener
    main = detectors["hybrid_graph_anomaly"]
    fz = StreamingGraphFeaturizer()
    for r in df[~te].itertuples(index=False):
        fz.transform_one(r.timestamp, r.merchant_id, r.card_id, r.device_id, r.ip_id, r.amount)
        fz.update(r.timestamp, r.merchant_id, r.card_id, r.device_id, r.ip_id, r.amount, r.chargeback_time)
    log_path = out / f"audit_log_{scenario}.jsonl"
    if log_path.exists():
        log_path.unlink()
    screener = Screener(main, budget["hybrid_graph_anomaly"]["threshold"], ensemble=ensemble,
                        audit_path=str(log_path), featurizer=fz)
    decisions = [screener.process(r._asdict()) for r in df[te].itertuples(index=False)]
    lat = np.array([d["latency_ms"] for d in decisions])
    stab = np.array([d["stability"] for d in decisions if d["stability"] is not None])
    v = verify_log(log_path)
    examples = [d for d in decisions if d["decision"] == "REVIEW" and d["stability"] and d["stability"] >= 0.8][:5]

    live = {
        "transactions_screened": len(decisions),
        "alerts": int(sum(d["decision"] == "REVIEW" for d in decisions)),
        "latency_ms_p50": float(np.percentile(lat, 50)),
        "latency_ms_p95": float(np.percentile(lat, 95)),
        "latency_ms_p99": float(np.percentile(lat, 99)),
        "top3_stability_mean": float(stab.mean()) if len(stab) else float("nan"),
        "share_alerts_reason_shown": float((stab >= 0.8).mean()) if len(stab) else float("nan"),
        "audit_records": v["records"], "audit_chain_valid": v["valid"],
        "audit_coverage": v["records"] / max(1, len(decisions)), "audit_head": v["head"],
        "example_alerts": [{k: e[k] for k in ("txn_id", "score", "reason_text", "stability")} for e in examples],
    }

    targets = {
        "fp_reduction_vs_rules": {"target": f">= 20% fewer false positives than rules at recall {TARGET_RECALL}",
                                  "observed": 1.0 - curve[str(TARGET_RECALL)]["hybrid_graph_anomaly"]
                                  / max(1, curve[str(TARGET_RECALL)]["rules"])},
        "latency_ms_p99": {"target": "< 100 ms", "observed": live["latency_ms_p99"]},
        "top3_stability_mean": {"target": ">= 0.80", "observed": live["top3_stability_mean"]},
        "audit_coverage": {"target": "100%", "observed": live["audit_coverage"]},
    }
    targets["fp_reduction_vs_rules"]["met"] = targets["fp_reduction_vs_rules"]["observed"] >= TARGETS["fp_reduction_vs_rules"]
    targets["latency_ms_p99"]["met"] = targets["latency_ms_p99"]["observed"] < TARGETS["latency_ms_p99"]
    targets["top3_stability_mean"]["met"] = targets["top3_stability_mean"]["observed"] >= TARGETS["top3_stability_mean"]
    targets["audit_coverage"]["met"] = live["audit_chain_valid"] and live["audit_coverage"] >= 1.0

    result = {
        "explainguard_version": __version__, "scenario": scenario,
        "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                        "platform": platform.platform()},
        "config": asdict(config) if data is None else {"source": "external csv"},
        "data": {"transactions": len(df), "fraud_rate": float(df["is_fraud"].mean()),
                 "train": int(tr.sum()), "validation": int(va.sum()), "test": int(te.sum()),
                 "test_fraud": int(y_te.sum()),
                 "train_labels_matured": int(y_tr.sum()),
                 "train_fraud_true": int(df.loc[tr, "is_fraud"].sum())},
        "operating_point_alert_budget": {"max_validation_fpr": max_fpr, "results": budget},
        "operating_point_equal_recall": {"rule_test_recall": rule_recall_te, "results": equal,
                                         "false_positives_at_recall": curve},
        "live_replay": live, "targets": targets,
        "supervised_arm_coefficients": dict(zip(main.features, np.round(main.logit.model.coef_[0], 4).tolist())),
        "alerts_by_arm": {a: int(sum(d.get("arm") == a for d in decisions)) for a in ("supervised", "anomaly")},
    }
    (out / f"results_{scenario}.json").write_text(json.dumps(result, indent=2, default=float))
    (out / f"results_{scenario}.md").write_text(to_markdown(result))
    return result


def to_markdown(r: dict) -> str:
    L = [f"# Results — scenario `{r['scenario']}`", "",
         f"Transactions: {r['data']['transactions']:,} · fraud rate {r['data']['fraud_rate']:.2%} · "
         f"test window {r['data']['test']:,} txns ({r['data']['test_fraud']} fraud)", "",
         "## Operating point A — fixed alert budget (validation FPR ≤ 1%)", "",
         "| Detector | Recall | Precision | FPR | Alerts | PR-AUC | ROC-AUC |", "|---|---|---|---|---|---|---|"]
    for k, v in r["operating_point_alert_budget"]["results"].items():
        L.append(f"| {k} | {v['recall']:.3f} | {v['precision']:.3f} | {v['fpr']:.4f} | {v['alerts']} | "
                 f"{v['pr_auc']:.3f} | {v['roc_auc']:.3f} |")
    L += ["", "### Recall by fraud pattern (alert budget)", "",
          "| Detector | " + " | ".join(next(iter(r['operating_point_alert_budget']['results'].values()))['recall_by_type']) + " |",
          "|---|" + "---|" * len(next(iter(r['operating_point_alert_budget']['results'].values()))['recall_by_type'])]
    for k, v in r["operating_point_alert_budget"]["results"].items():
        L.append(f"| {k} | " + " | ".join(f"{x:.3f}" for x in v["recall_by_type"].values()) + " |")
    L += ["", f"## Operating point B — false positives at the rule baseline's test recall "
              f"({r['operating_point_equal_recall']['rule_test_recall']:.3f})", "",
          "| Detector | Test recall | False positives | FP reduction vs rules |", "|---|---|---|---|"]
    for k, v in r["operating_point_equal_recall"]["results"].items():
        L.append(f"| {k} | {v['recall']:.3f} | {v['fp']} | {v['fp_reduction_vs_rules']:+.1%} |")
    cv = r["operating_point_equal_recall"]["false_positives_at_recall"]
    names = list(next(iter(cv.values())))
    L += ["", "### False positives needed to reach a given fraud recall (test window)", "",
          "| Recall | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for R, row in cv.items():
        L.append(f"| {R} | " + " | ".join(str(row[n]) for n in names) + " |")
    lv = r["live_replay"]
    L += ["", "## Live replay (one transaction at a time)", "",
          f"- Screened {lv['transactions_screened']:,} transactions, {lv['alerts']} alerts "
          f"({r['alerts_by_arm']['supervised']} supervised arm, {r['alerts_by_arm']['anomaly']} anomaly arm)",
          f"- Latency p50 / p95 / p99: {lv['latency_ms_p50']:.2f} / {lv['latency_ms_p95']:.2f} / {lv['latency_ms_p99']:.2f} ms",
          f"- Mean top-3 reason agreement across re-estimated models: {lv['top3_stability_mean']:.3f}",
          f"- Alerts whose reason passed the 0.80 stability gate: {lv['share_alerts_reason_shown']:.1%}",
          f"- Audit records: {lv['audit_records']:,} · chain valid: {lv['audit_chain_valid']} · coverage {lv['audit_coverage']:.0%}",
          "", "## Endeavor targets", "", "| Target | Goal | Observed | Met |", "|---|---|---|---|"]
    for k, v in r["targets"].items():
        o = v["observed"]
        o = f"{o:.1%}" if k in ("fp_reduction_vs_rules", "audit_coverage") else f"{o:.3f}"
        L.append(f"| {k} | {v['target']} | {o} | {'yes' if v['met'] else 'no'} |")
    L += ["", "## Example alerts", ""]
    for e in lv["example_alerts"]:
        L.append(f"- `{e['txn_id']}` (stability {e['stability']:.2f}): {e['reason_text']}")
    return "\n".join(L) + "\n"
