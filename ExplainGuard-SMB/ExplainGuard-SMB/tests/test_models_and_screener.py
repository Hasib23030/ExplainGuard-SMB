import numpy as np

from explainguard.audit import verify_log
from explainguard.benchmark import matured_labels, time_split
from explainguard.features import ALL_FEATURES, build_features
from explainguard.metrics import confusion_at, threshold_for_alert_rate, threshold_for_recall
from explainguard.models import ExplainableLogit, HybridDetector, RuleBaseline
from explainguard.toolkit import Screener


def _prep(df):
    X = build_features(df)
    tr, va, te, a, b = time_split(df)
    return X, tr, va, te, matured_labels(df[tr], a), matured_labels(df[va], b)


def test_contributions_are_exact(small_df):
    X, tr, *_ , y_tr, _ = _prep(small_df)
    m = ExplainableLogit(ALL_FEATURES).fit(X[tr], y_tr)
    c = m.contributions(X[tr])
    assert np.allclose(c.sum(1) + m.model.intercept_[0], m.score(X[tr]))


def test_label_maturity_hides_late_chargebacks(small_df):
    tr, va, te, a, b = time_split(small_df)
    assert matured_labels(small_df[tr], a).sum() <= small_df.loc[tr, "is_fraud"].sum()


def test_metrics_thresholds():
    s = np.array([0.1, 0.2, 0.3, 0.9, 0.8, 0.7])
    y = np.array([0, 0, 0, 1, 1, 1])
    assert confusion_at(s, y, threshold_for_recall(s, y, 1.0))["recall"] == 1.0
    assert confusion_at(s, y, threshold_for_alert_rate(s[y == 0], 0.0))["fp"] <= 1


def test_hybrid_and_screener_end_to_end(small_df, tmp_path):
    X, tr, va, te, y_tr, y_va = _prep(small_df)
    h = HybridDetector(ALL_FEATURES, seed=0).fit(X[tr], y_tr).calibrate(X[va][y_va == 0], 0.01)
    ens = [HybridDetector(ALL_FEATURES, seed=s, iforest=h.iforest).fit(X[tr], y_tr)
           .calibrate(X[va][y_va == 0], 0.01) for s in (1, 2)]
    # vector path must agree with the batch path
    raw = X[te].iloc[0][ALL_FEATURES].to_numpy(float)
    assert np.isclose(h.score_and_explain_vector(raw)[0], h.score(X[te].iloc[[0]])[0])

    log = tmp_path / "audit.jsonl"
    sc = Screener(h, 0.0, ensemble=ens, audit_path=str(log))
    out = [sc.process(r._asdict()) for r in small_df.itertuples(index=False)]
    assert len(out) == len(small_df)
    assert any(d["decision"] == "REVIEW" for d in out)
    for d in out:
        if d["decision"] == "REVIEW":
            assert d["reason_text"] and 0.0 <= d["stability"] <= 1.0
    v = verify_log(log)
    assert v["valid"] and v["records"] == len(small_df)


def test_rules_score_shape(small_df):
    X = build_features(small_df.head(200))
    assert RuleBaseline().score(X).shape == (200,)
