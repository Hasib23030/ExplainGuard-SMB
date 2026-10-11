"""Real-time screener: featurise -> score -> stability-gated reason -> audit record.

``Screener`` is the toolkit a small merchant, bookkeeper or small processor runs.
It processes one transaction at a time, exactly as a live checkout would.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import numpy as np

from .audit import AuditLog
from .explain import plain_language, top_k_reasons, topk_agreement
from .features import StreamingGraphFeaturizer
from .models import HybridDetector

RMF_TAGS = {  # NIST AI RMF 1.0 function each record field supports
    "model_version": "GOVERN",
    "features": "MAP",
    "score": "MEASURE",
    "stability": "MEASURE",
    "decision": "MANAGE",
}


class Screener:
    def __init__(self, model: HybridDetector, threshold: float, ensemble: list | None = None,
                 audit_path: str | None = None, stability_gate: float = 0.8, k: int = 3,
                 featurizer: StreamingGraphFeaturizer | None = None):
        self.model = model
        self.threshold = threshold
        self.ensemble = ensemble or []
        self.gate = stability_gate
        self.k = k
        self.fz = featurizer or StreamingGraphFeaturizer()
        self.log = AuditLog(audit_path) if audit_path else None
        self.version = model.version()

    def process(self, txn: dict) -> dict:
        """Screen one transaction dict with keys timestamp, merchant_id, card_id,
        device_id, ip_id, amount (and optionally txn_id, chargeback_time)."""
        t0 = time.perf_counter()
        f = self.fz.transform_one(txn["timestamp"], txn["merchant_id"], txn["card_id"],
                                  txn["device_id"], txn["ip_id"], txn["amount"])
        raw = np.array([f[c] for c in self.model.features], dtype=float)
        score, arm, attrib, anomaly = self.model.score_and_explain_vector(raw)
        alert = score >= self.threshold

        decision = {"txn_id": txn.get("txn_id"), "score": round(score, 6),
                    "decision": "REVIEW" if alert else "ALLOW", "arm": arm if alert else None,
                    "reason_codes": [], "reason_text": "", "stability": None}
        if alert:
            codes = top_k_reasons(attrib, self.model.features, self.k)
            stab = 1.0
            if self.ensemble:
                others = []
                for m in self.ensemble:
                    a = (m.logit.contrib_vector(raw) if arm == "supervised"
                         else m.deviation_vector(raw))
                    others.append(top_k_reasons(a, m.features, self.k))
                stab = float(np.mean([topk_agreement(codes, o, self.k) for o in others]))
            decision["stability"] = round(stab, 4)
            decision["reason_codes"] = codes
            vals = dict(f, amount=txn["amount"])
            lead = ("Flagged because " if arm == "supervised"
                    else "Flagged as unusual compared with normal customers because ")
            if stab >= self.gate and codes:
                decision["reason_text"] = lead + "; ".join(plain_language(c, vals) for c in codes) + "."
            else:
                decision["reason_text"] = ("Flagged for review; the automated reason did not pass "
                                           "the stability check and is withheld.")
        self.fz.update(txn["timestamp"], txn["merchant_id"], txn["card_id"], txn["device_id"],
                       txn["ip_id"], txn["amount"], txn.get("chargeback_time"))
        decision["latency_ms"] = (time.perf_counter() - t0) * 1000.0

        if self.log is not None:
            self.log.append({
                "logged_at": datetime.now(timezone.utc).isoformat(),
                "txn_id": decision["txn_id"],
                "inputs": {k: txn[k] for k in ("timestamp", "merchant_id", "card_id",
                                               "device_id", "ip_id", "amount")},
                "features": {k: round(v, 6) for k, v in f.items()},
                "model_version": self.version,
                "threshold": round(self.threshold, 6),
                "score": decision["score"],
                "decision": decision["decision"],
                "detector_arm": decision["arm"],
                "reason_codes": decision["reason_codes"],
                "reason_text": decision["reason_text"],
                "stability": decision["stability"],
                "rmf": RMF_TAGS,
            })
        return decision
