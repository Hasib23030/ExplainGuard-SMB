"""Detectors compared in the benchmark.

All detectors expose ``fit(X, y)`` and ``score(X) -> np.ndarray`` (higher = riskier).

* ``RuleBaseline``      - a transparent rule engine of the kind small merchants use.
* ``IsolationForestDetector`` - unsupervised anomaly detection (catches new patterns).
* ``ExplainableLogit``  - standardised logistic regression; its per-feature
                          contributions are exact, so explanations are faithful.
* ``HybridDetector``    - supervised explainable graph arm OR unsupervised anomaly
                          arm, each with half of the alert budget.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression


class RuleBaseline:
    """Weighted rule score. Rules reflect common small-merchant fraud filters."""

    name = "rules"
    RULES = {
        "high amount (> $300)": (lambda X: np.expm1(X["log_amount"]) > 300, 1.0),
        "new device on known card": (lambda X: X["card_new_device"] > 0, 1.0),
        "night-time purchase": (lambda X: X["is_night"] > 0, 0.5),
        "card used 4+ times in 24h": (lambda X: X["card_txn_24h"] >= 4, 1.0),
        "amount 3x above card's usual": (lambda X: X["amount_vs_card_median"] > np.log(3), 1.0),
    }

    def fit(self, X: pd.DataFrame, y=None) -> "RuleBaseline":
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        s = np.zeros(len(X))
        for fn, w in self.RULES.values():
            s += w * fn(X).to_numpy(dtype=float)
        # tiny tie-breaker so thresholds can be tuned continuously
        return s + 1e-3 * X["log_amount"].to_numpy()


class IsolationForestDetector:
    name = "isolation_forest"

    def __init__(self, features: list[str], seed: int = 0, n_estimators: int = 200):
        self.features = features
        self.model = IsolationForest(n_estimators=n_estimators, random_state=seed, n_jobs=1)

    def fit(self, X: pd.DataFrame, y=None) -> "IsolationForestDetector":
        mask = np.ones(len(X), bool) if y is None else (np.asarray(y) == 0)
        self.model.fit(X.loc[mask, self.features].to_numpy())
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        return -self.model.score_samples(X[self.features].to_numpy())


class ExplainableLogit:
    """Logistic regression on standardised features with exact additive attributions."""

    def __init__(self, features: list[str], name: str = "logit", C: float = 1.0,
                 seed: int = 0):
        self.features = list(features)
        self.name = name
        self.C = C
        self.seed = seed

    def fit(self, X: pd.DataFrame, y) -> "ExplainableLogit":
        A = X[self.features].to_numpy(dtype=float)
        self.mu_ = A.mean(0)
        self.sd_ = A.std(0) + 1e-9
        self.model = LogisticRegression(C=self.C, max_iter=2000, class_weight="balanced",
                                        random_state=self.seed)
        self.model.fit((A - self.mu_) / self.sd_, np.asarray(y))
        return self

    def _z(self, X: pd.DataFrame) -> np.ndarray:
        return (X[self.features].to_numpy(dtype=float) - self.mu_) / self.sd_

    def score(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.decision_function(self._z(X))

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        """Per-feature contribution to the log-odds (sums to score - intercept)."""
        return self._z(X) * self.model.coef_[0]

    # fast single-transaction path (raw feature vector in ``self.features`` order)
    def contrib_vector(self, raw: np.ndarray) -> np.ndarray:
        return (raw - self.mu_) / self.sd_ * self.model.coef_[0]

    def score_vector(self, raw: np.ndarray) -> float:
        return float(self.contrib_vector(raw).sum() + self.model.intercept_[0])

    def version(self) -> str:
        payload = json.dumps({"f": self.features, "coef": np.round(self.model.coef_[0], 8).tolist(),
                              "b": round(float(self.model.intercept_[0]), 8),
                              "mu": np.round(self.mu_, 8).tolist(),
                              "sd": np.round(self.sd_, 8).tolist()}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


class HybridDetector:
    """Two-arm detector: a supervised explainable graph model OR an unsupervised anomaly arm.

    Each arm receives half of the alert budget (calibrated on validation legit traffic).
    The supervised arm catches known patterns with faithful reasons; the anomaly arm
    catches patterns never seen in training labels (e.g. a new card-testing attack).
    The combined score is the larger of the two calibrated margins, so 0 is the
    decision boundary and the score stays comparable across arms.
    """

    name = "hybrid_graph_anomaly"

    def __init__(self, features: list[str], seed: int = 0,
                 iforest: IsolationForestDetector | None = None, C: float = 1.0):
        self.features = list(features)
        self.seed = seed
        self.logit = ExplainableLogit(features, "supervised_arm", C=C, seed=seed)
        self._prefit = iforest is not None
        self.iforest = iforest or IsolationForestDetector(features, seed=seed)

    def fit(self, X: pd.DataFrame, y) -> "HybridDetector":
        y = np.asarray(y)
        self.logit.fit(X, y)
        if not self._prefit:
            self.iforest.fit(X, y)
        A = X.loc[y == 0, self.features].to_numpy(dtype=float)
        self.legit_mu_, self.legit_sd_ = A.mean(0), A.std(0) + 1e-9
        return self

    def calibrate(self, X_legit: pd.DataFrame, max_fpr: float = 0.01) -> "HybridDetector":
        ls, an = self.logit.score(X_legit), self.iforest.score(X_legit)
        q = 1.0 - max_fpr / 2.0
        self.t_sup_, self.t_anom_ = float(np.quantile(ls, q)), float(np.quantile(an, q))
        self.s_sup_, self.s_anom_ = float(ls.std() + 1e-9), float(an.std() + 1e-9)
        return self

    def _margins(self, ls, an):
        return (np.asarray(ls) - self.t_sup_) / self.s_sup_, (np.asarray(an) - self.t_anom_) / self.s_anom_

    def score(self, X: pd.DataFrame) -> np.ndarray:
        m_s, m_a = self._margins(self.logit.score(X), self.iforest.score(X))
        return np.maximum(m_s, m_a)

    def score_and_explain_vector(self, raw: np.ndarray) -> tuple[float, str, np.ndarray, float]:
        """Fast single-transaction path. Returns (score, arm, attribution, anomaly)."""
        contrib = self.logit.contrib_vector(raw)
        ls = float(contrib.sum() + self.logit.model.intercept_[0])
        an = float(-self.iforest.model.score_samples(raw[None, :])[0])
        m_s, m_a = self._margins(ls, an)
        if m_s >= m_a:
            return float(m_s), "supervised", contrib, an
        return float(m_a), "anomaly", self.deviation_vector(raw), an

    def deviation_vector(self, raw: np.ndarray) -> np.ndarray:
        """How unusual each feature is versus normal (legit) customers, in std units."""
        return (raw - self.legit_mu_) / self.legit_sd_

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        return self.logit.contributions(X)

    def version(self) -> str:
        payload = json.dumps({"logit": self.logit.version(),
                              "iforest": self.iforest.model.get_params()["random_state"],
                              "t": [round(self.t_sup_, 8), round(self.t_anom_, 8)]}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
