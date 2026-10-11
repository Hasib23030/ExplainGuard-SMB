import numpy as np

from explainguard.explain import explain_alert, plain_language, top_k_reasons, topk_agreement


def test_top_k_positive_only():
    feats = ["a", "b", "c", "d"]
    assert top_k_reasons(np.array([0.5, -2.0, 1.5, 0.1]), feats, 3) == ["c", "a", "d"]
    assert top_k_reasons(np.array([-1.0, -2.0, 0.0, -0.1]), feats, 3) == []


def test_agreement():
    assert topk_agreement(["a", "b", "c"], ["c", "b", "a"]) == 1.0
    assert topk_agreement(["a", "b", "c"], ["a", "x", "y"]) == 1 / 3


def test_plain_language_formats_values():
    s = plain_language("device_distinct_cards", {"device_distinct_cards": 7.0})
    assert "7 different cards" in s
    assert "$1,000.00" in plain_language("log_amount", {"amount": 1000.0})


def test_explain_alert_text():
    out = explain_alert(np.array([2.0, 1.0]), ["device_txn_1h", "is_night"],
                        {"device_txn_1h": 9.0, "is_night": 1.0})
    assert out["reason_codes"] == ["device_txn_1h", "is_night"]
    assert out["reason_text"].startswith("Flagged because this device made 9 purchases")
