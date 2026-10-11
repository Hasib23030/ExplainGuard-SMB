import numpy as np

from explainguard.generator import SCHEMA, GeneratorConfig, generate


def test_schema_and_order(small_df):
    assert list(small_df.columns) == SCHEMA
    assert small_df["timestamp"].is_monotonic_increasing
    assert small_df["txn_id"].is_unique


def test_deterministic_with_seed(small_cfg):
    a, b = generate(small_cfg), generate(small_cfg)
    assert a.equals(b)


def test_fraud_patterns_and_chargebacks(small_df):
    types = set(small_df["fraud_type"])
    assert {"legit", "ring", "card_testing", "takeover"} <= types
    fraud = small_df[small_df.is_fraud == 1]
    assert fraud["chargeback_time"].notna().all()
    assert (fraud["chargeback_time"] > fraud["timestamp"]).all()
    assert small_df.loc[small_df.is_fraud == 0, "chargeback_time"].isna().all()


def test_novel_attack_is_held_back():
    df = generate(GeneratorConfig(seed=1, days=40, n_customers=300, card_testing_start_day=30))
    ct = df[df.fraud_type == "card_testing"]
    assert (ct["timestamp"] >= 30 * 86400).all()


def test_amounts_positive(small_df):
    assert (small_df["amount"] > 0).all()
    assert np.isfinite(small_df["amount"]).all()
