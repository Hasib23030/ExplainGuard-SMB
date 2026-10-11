import math

from explainguard.features import ALL_FEATURES, StreamingGraphFeaturizer, build_features


def test_feature_columns(small_df):
    X = build_features(small_df.head(500))
    assert list(X.columns) == ALL_FEATURES
    assert X.notna().all().all()


def test_no_chargeback_leakage():
    """A chargeback must not be visible before its chargeback time."""
    fz = StreamingGraphFeaturizer()
    fz.transform_one(0, "M1", "C1", "D1", "I1", 50)
    fz.update(0, "M1", "C1", "D1", "I1", 50, chargeback_time=10 * 86400)
    before = fz.transform_one(5 * 86400, "M1", "C2", "D1", "I2", 20)
    assert before["device_chargeback_cards"] == 0
    fz.update(5 * 86400, "M1", "C2", "D1", "I2", 20)
    after = fz.transform_one(11 * 86400, "M1", "C3", "D1", "I3", 20)
    assert after["device_chargeback_cards"] == 1


def test_features_computed_before_update():
    fz = StreamingGraphFeaturizer()
    f = fz.transform_one(0, "M1", "C1", "D1", "I1", 10)
    assert f["device_distinct_cards"] == 0 and f["card_txn_24h"] == 0


def test_shared_device_and_two_hop():
    fz = StreamingGraphFeaturizer()
    for i, card in enumerate(["A", "B", "C"]):
        fz.transform_one(i, "M", card, "DEV", "IP", 30)
        fz.update(i, "M", card, "DEV", "IP", 30, chargeback_time=100 if card == "A" else math.nan)
    f = fz.transform_one(200, "M", "B", "DEV", "IP", 30)
    assert f["device_distinct_cards"] == 3
    assert f["device_chargeback_cards"] == 1
    assert f["card_2hop_chargeback_cards"] == 1


def test_velocity_windows():
    fz = StreamingGraphFeaturizer()
    for i in range(5):
        fz.transform_one(i * 60, "M", f"C{i}", "D", "I", 1.0)
        fz.update(i * 60, "M", f"C{i}", "D", "I", 1.0)
    f = fz.transform_one(300, "M", "C9", "D", "I", 1.0)
    assert f["device_txn_1h"] == 5 and f["device_small_txn_1h"] == 5
    g = fz.transform_one(300 + 7200, "M", "C9", "D", "I", 1.0)
    assert g["device_txn_1h"] == 0
