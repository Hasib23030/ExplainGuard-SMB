"""Plain-language reasons and explanation-stability testing.

A reason is only shown to a person when it is *stable*: models re-estimated on
resampled training data must agree on it. Unstable reasons are withheld and the
alert is marked "reason under review" instead of showing a misleading story.
"""
from __future__ import annotations

from itertools import combinations
from typing import Callable

import numpy as np
import pandas as pd

TEMPLATES = {
    "log_amount": "the amount (${amount:,.2f}) is high for this store",
    "amount_vs_card_median": "the amount is far above this card's usual spending",
    "is_night": "it was placed between midnight and 6 in the morning",
    "card_txn_24h": "this card was used {card_txn_24h:.0f} times in the last 24 hours",
    "card_new_device": "the card was used from a device it has never used before",
    "card_new_ip": "the card was used from a new network address",
    "small_amount": "it is a very small charge, typical of stolen-card testing",
    "device_distinct_cards": "this device has been used with {device_distinct_cards:.0f} different cards",
    "ip_distinct_cards": "this network address has been used with {ip_distinct_cards:.0f} different cards",
    "device_txn_1h": "this device made {device_txn_1h:.0f} purchases in the last hour",
    "device_small_txn_1h": "this device made {device_small_txn_1h:.0f} tiny charges in the last hour",
    "device_chargeback_cards": "this device is linked to {device_chargeback_cards:.0f} card(s) that already had chargebacks",
    "ip_chargeback_cards": "this network address is linked to {ip_chargeback_cards:.0f} card(s) that already had chargebacks",
    "card_2hop_chargeback_cards": "this card shares devices with {card_2hop_chargeback_cards:.0f} card(s) that had chargebacks",
    "card_distinct_devices": "this card has appeared on {card_distinct_devices:.0f} different devices",
    "merchant_chargeback_rate_30d": "this store has had elevated chargebacks in the last 30 days",
}


def top_k_reasons(contrib_row: np.ndarray, features: list[str], k: int = 3) -> list[str]:
    """Features with the largest *positive* contribution (pushing towards fraud)."""
    order = np.argsort(-contrib_row)
    return [features[i] for i in order[:k] if contrib_row[i] > 0]


def plain_language(feature: str, values: dict) -> str:
    v = dict(values)
    v.setdefault("amount", float(np.expm1(v.get("log_amount", 0.0))))
    try:
        return TEMPLATES[feature].format(**v)
    except (KeyError, ValueError):
        return feature.replace("_", " ")


def explain_alert(contrib_row: np.ndarray, features: list[str], values: dict, k: int = 3) -> dict:
    keys = top_k_reasons(contrib_row, features, k)
    text = "; ".join(plain_language(f, values) for f in keys)
    return {"reason_codes": keys, "reason_text": ("Flagged because " + text + ".") if keys else ""}


def topk_agreement(a: list[str], b: list[str], k: int = 3) -> float:
    """Share of the top-k reasons two explanations have in common (0..1)."""
    return len(set(a[:k]) & set(b[:k])) / float(k)


def stability_scores(models: list, X: pd.DataFrame, k: int = 3,
                     contrib_fn: Callable | None = None) -> np.ndarray:
    """Per-row mean pairwise top-k agreement across a set of re-estimated models."""
    if len(models) < 2:
        raise ValueError("need at least two models to measure stability")
    fn = contrib_fn or (lambda m, X: m.contributions(X))
    tops = []
    for m in models:
        C = fn(m, X)
        tops.append([top_k_reasons(C[i], m.features, k) for i in range(len(X))])
    pairs = list(combinations(range(len(models)), 2))
    out = np.zeros(len(X))
    for i in range(len(X)):
        out[i] = np.mean([topk_agreement(tops[a][i], tops[b][i], k) for a, b in pairs])
    return out
