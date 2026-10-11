"""Operational metrics: what a fraud team actually works with."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def threshold_for_alert_rate(scores_legit: np.ndarray, max_fpr: float) -> float:
    """Smallest threshold whose false-positive rate on legit traffic is <= max_fpr."""
    return float(np.quantile(scores_legit, 1.0 - max_fpr))


def threshold_for_recall(scores: np.ndarray, y: np.ndarray, recall: float) -> float:
    """Highest threshold that still reaches the requested fraud recall."""
    fraud = np.sort(scores[y == 1])[::-1]
    if len(fraud) == 0:
        return float("inf")
    k = max(1, int(np.ceil(recall * len(fraud))))
    return float(fraud[k - 1])


def confusion_at(scores: np.ndarray, y: np.ndarray, thr: float) -> dict:
    flag = scores >= thr
    tp = int((flag & (y == 1)).sum())
    fp = int((flag & (y == 0)).sum())
    fn = int((~flag & (y == 1)).sum())
    tn = int((~flag & (y == 0)).sum())
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "recall": tp / max(1, tp + fn),
        "precision": tp / max(1, tp + fp),
        "fpr": fp / max(1, fp + tn),
        "alerts": tp + fp,
    }


def ranking_metrics(scores: np.ndarray, y: np.ndarray) -> dict:
    if len(np.unique(y)) < 2:
        return {"pr_auc": float("nan"), "roc_auc": float("nan")}
    return {"pr_auc": float(average_precision_score(y, scores)),
            "roc_auc": float(roc_auc_score(y, scores))}


def recall_by_type(scores: np.ndarray, types: np.ndarray, thr: float) -> dict:
    out = {}
    for t in sorted(set(types) - {"legit"}):
        m = types == t
        out[t] = float((scores[m] >= thr).mean()) if m.any() else float("nan")
    return out
