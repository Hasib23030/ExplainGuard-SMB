"""Synthetic small-merchant transaction generator.

Produces a time-ordered table of card-not-present transactions for a set of
small online merchants, with three injected fraud patterns:

* ``ring``         - organised fraud rings that reuse a small pool of devices and
                     IP addresses across many stolen cards (relational signal).
* ``card_testing`` - bursts of very small authorisations from one device using
                     many cards in a short window (velocity + relational signal).
                     Can be held back until a later day to simulate a new attack
                     that a supervised model has never seen.
* ``takeover``     - a single stolen card used once or twice on a new device for
                     a high amount (weak relational signal; hard by design).

Fraudulent transactions receive a chargeback timestamp 5-30 days later. Graph
features downstream may only use chargebacks that are *already known* at the
moment of scoring, so the benchmark is free of label leakage.

No real customer data is used or required.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SCHEMA = [
    "txn_id", "timestamp", "merchant_id", "card_id", "device_id", "ip_id",
    "amount", "is_fraud", "fraud_type", "chargeback_time",
]


@dataclass
class GeneratorConfig:
    seed: int = 7
    days: int = 90
    n_merchants: int = 40
    n_customers: int = 3000
    legit_txn_per_customer_per_day: float = 0.12
    n_rings: int = 12
    ring_cards: tuple[int, int] = (8, 25)
    ring_devices: tuple[int, int] = (2, 4)
    ring_ips: tuple[int, int] = (2, 5)
    n_card_testing_bursts: int = 25
    card_testing_start_day: int = 0  # set > 0 to introduce the attack later
    n_takeovers: int = 150
    chargeback_delay_days: tuple[int, int] = (5, 30)


def _t(rng: np.random.Generator, day: float, night_bias: bool = False) -> float:
    """Seconds since start for a given day with a realistic hour-of-day profile."""
    if night_bias:
        hour = rng.choice([0, 1, 2, 3, 4, 5, 22, 23]) + rng.random()
    else:
        hour = np.clip(rng.normal(14, 4), 0, 23.99)
    return float(day * 86400 + hour * 3600)


def generate(config: GeneratorConfig | None = None) -> pd.DataFrame:
    """Generate a synthetic transaction table (sorted by time)."""
    c = config or GeneratorConfig()
    rng = np.random.default_rng(c.seed)
    rows: list[tuple] = []

    # --- merchants: each has a typical basket size --------------------------------
    merchant_mu = rng.normal(3.6, 0.5, c.n_merchants)  # log-dollars (~$37 median)

    # --- legitimate customers --------------------------------------------------------
    card_counter = device_counter = ip_counter = 0
    customers = []
    for _ in range(c.n_customers):
        n_cards = 1 + int(rng.random() < 0.25)
        n_dev = 1 + int(rng.random() < 0.35)
        cards = [f"C{card_counter + i:06d}" for i in range(n_cards)]
        devs = [f"D{device_counter + i:06d}" for i in range(n_dev)]
        ips = [f"I{ip_counter:06d}", f"I{ip_counter + 1:06d}"]
        card_counter += n_cards
        device_counter += n_dev
        ip_counter += 2
        fav = rng.choice(c.n_merchants, size=3, replace=False)
        customers.append((cards, devs, ips, fav))

    for cards, devs, ips, fav in customers:
        n = rng.poisson(c.legit_txn_per_customer_per_day * c.days)
        for _ in range(n):
            day = rng.integers(0, c.days)
            m = int(rng.choice(fav)) if rng.random() < 0.8 else int(rng.integers(c.n_merchants))
            amt = float(np.round(np.exp(rng.normal(merchant_mu[m], 0.7)), 2))
            rows.append((_t(rng, day), f"M{m:03d}", rng.choice(cards), rng.choice(devs),
                         rng.choice(ips), amt, 0, "legit"))

    all_cards = [card for cust in customers for card in cust[0]]

    # --- fraud ring pattern ----------------------------------------------------------
    for r in range(c.n_rings):
        r_devs = [f"RD{r:02d}_{i}" for i in range(rng.integers(*c.ring_devices, endpoint=True))]
        r_ips = [f"RI{r:02d}_{i}" for i in range(rng.integers(*c.ring_ips, endpoint=True))]
        stolen = rng.choice(all_cards, size=rng.integers(*c.ring_cards, endpoint=True), replace=False)
        start = rng.integers(0, max(1, c.days - 10))
        span = rng.integers(5, 20)
        targets = rng.choice(c.n_merchants, size=rng.integers(2, 6), replace=False)
        for card in stolen:
            for _ in range(rng.integers(1, 4)):
                day = min(c.days - 1, start + rng.integers(0, span))
                m = int(rng.choice(targets))
                amt = float(np.round(np.exp(rng.normal(merchant_mu[m] + 1.0, 0.6)), 2))
                rows.append((_t(rng, day, night_bias=rng.random() < 0.5), f"M{m:03d}", card,
                             rng.choice(r_devs), rng.choice(r_ips), amt, 1, "ring"))

    # --- card-testing bursts ---------------------------------------------------------
    for b in range(c.n_card_testing_bursts):
        dev, ip = f"TD{b:03d}", f"TI{b:03d}"
        m = int(rng.integers(c.n_merchants))
        day = rng.integers(c.card_testing_start_day, c.days)
        t0 = _t(rng, day, night_bias=True)
        cards = rng.choice(all_cards, size=rng.integers(6, 20), replace=False)
        for k, card in enumerate(cards):
            amt = float(np.round(rng.uniform(0.5, 3.0), 2))
            rows.append((t0 + k * rng.uniform(20, 240), f"M{m:03d}", card, dev, ip, amt, 1,
                         "card_testing"))

    # --- account takeover / single stolen card --------------------------------------
    for a in range(c.n_takeovers):
        card = rng.choice(all_cards)
        dev, ip = f"AD{a:04d}", f"AI{a:04d}"
        day = rng.integers(0, c.days)
        m = int(rng.integers(c.n_merchants))
        for _ in range(rng.integers(1, 3)):
            amt = float(np.round(np.exp(rng.normal(merchant_mu[m] + 1.6, 0.5)), 2))
            rows.append((_t(rng, day), f"M{m:03d}", card, dev, ip, amt, 1, "takeover"))

    df = pd.DataFrame(rows, columns=["timestamp", "merchant_id", "card_id", "device_id",
                                     "ip_id", "amount", "is_fraud", "fraud_type"])
    delay = rng.uniform(*c.chargeback_delay_days, size=len(df)) * 86400
    df["chargeback_time"] = np.where(df["is_fraud"] == 1, df["timestamp"] + delay, np.nan)
    df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    df.insert(0, "txn_id", [f"T{i:07d}" for i in range(len(df))])
    return df[SCHEMA]
