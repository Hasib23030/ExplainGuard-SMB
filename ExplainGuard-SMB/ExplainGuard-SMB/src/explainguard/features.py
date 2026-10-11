"""Leakage-safe streaming features over the card-device-IP-merchant graph.

Transactions are processed strictly in time order. For each transaction the
features are computed from the state *before* the transaction is added, and
chargeback (fraud) labels are only visible after their chargeback timestamp.
This mirrors what a real-time screening system can actually know.

Two feature groups are produced:

* ``TXN_FEATURES``   - per-transaction/per-card behaviour (no relational data).
* ``GRAPH_FEATURES`` - neighbourhood aggregates over the entity graph
                       (one- and two-hop links through shared devices and IPs).
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict, deque

import numpy as np
import pandas as pd

TXN_FEATURES = [
    "log_amount",
    "amount_vs_card_median",
    "is_night",
    "card_txn_24h",
    "card_new_device",
    "card_new_ip",
    "small_amount",
]

GRAPH_FEATURES = [
    "device_distinct_cards",
    "ip_distinct_cards",
    "device_txn_1h",
    "device_small_txn_1h",
    "device_chargeback_cards",
    "ip_chargeback_cards",
    "card_2hop_chargeback_cards",
    "card_distinct_devices",
    "merchant_chargeback_rate_30d",
]

ALL_FEATURES = TXN_FEATURES + GRAPH_FEATURES

HOUR, DAY = 3600.0, 86400.0


class StreamingGraphFeaturizer:
    """Incrementally maintains entity-graph state and emits features per transaction."""

    def __init__(self) -> None:
        self.card_devices: dict[str, set] = defaultdict(set)
        self.card_ips: dict[str, set] = defaultdict(set)
        self.device_cards: dict[str, set] = defaultdict(set)
        self.ip_cards: dict[str, set] = defaultdict(set)
        self.card_amounts: dict[str, list] = defaultdict(list)
        self.card_times: dict[str, deque] = defaultdict(deque)
        self.device_times: dict[str, deque] = defaultdict(deque)
        self.device_small_times: dict[str, deque] = defaultdict(deque)
        self.merchant_times: dict[str, deque] = defaultdict(deque)
        self.merchant_cb_times: dict[str, deque] = defaultdict(deque)
        self.cb_cards: set = set()
        self.device_cb: dict[str, int] = defaultdict(int)
        self.ip_cb: dict[str, int] = defaultdict(int)
        self._pending: list = []  # heap of (chargeback_time, card_id, merchant_id)

    # ------------------------------------------------------------------ internals
    @staticmethod
    def _trim(q: deque, now: float, window: float) -> None:
        while q and q[0] < now - window:
            q.popleft()

    def _release_chargebacks(self, now: float) -> None:
        while self._pending and self._pending[0][0] <= now:
            cb_t, card, merchant = heapq.heappop(self._pending)
            self.merchant_cb_times[merchant].append(cb_t)
            if card in self.cb_cards:
                continue
            self.cb_cards.add(card)
            for d in self.card_devices[card]:
                self.device_cb[d] += 1
            for i in self.card_ips[card]:
                self.ip_cb[i] += 1

    # ------------------------------------------------------------------ public API
    def transform_one(self, t: float, merchant: str, card: str, device: str, ip: str,
                      amount: float) -> dict:
        """Return the feature dict for one transaction, computed before updating state."""
        self._release_chargebacks(t)
        for q, w in ((self.card_times[card], DAY), (self.device_times[device], HOUR),
                     (self.device_small_times[device], HOUR),
                     (self.merchant_times[merchant], 30 * DAY),
                     (self.merchant_cb_times[merchant], 30 * DAY)):
            self._trim(q, t, w)

        hist = self.card_amounts[card]
        med = float(np.median(hist[-20:])) if hist else amount
        two_hop = sum(self.device_cb[d] for d in self.card_devices[card])
        m_n = len(self.merchant_times[merchant])
        feats = {
            "log_amount": math.log1p(amount),
            "amount_vs_card_median": math.log1p(amount) - math.log1p(med),
            "is_night": float(((t % DAY) / HOUR) < 6),
            "card_txn_24h": float(len(self.card_times[card])),
            "card_new_device": float(bool(hist) and device not in self.card_devices[card]),
            "card_new_ip": float(bool(hist) and ip not in self.card_ips[card]),
            "small_amount": float(amount < 5.0),
            "device_distinct_cards": float(len(self.device_cards[device])),
            "ip_distinct_cards": float(len(self.ip_cards[ip])),
            "device_txn_1h": float(len(self.device_times[device])),
            "device_small_txn_1h": float(len(self.device_small_times[device])),
            "device_chargeback_cards": float(self.device_cb[device]),
            "ip_chargeback_cards": float(self.ip_cb[ip]),
            "card_2hop_chargeback_cards": float(two_hop),
            "card_distinct_devices": float(len(self.card_devices[card])),
            "merchant_chargeback_rate_30d": len(self.merchant_cb_times[merchant]) / (m_n + 20.0),
        }
        return feats

    def update(self, t: float, merchant: str, card: str, device: str, ip: str, amount: float,
               chargeback_time: float | None = None) -> None:
        """Add the transaction to graph state (call after ``transform_one``)."""
        if device not in self.card_devices[card]:
            self.card_devices[card].add(device)
            self.device_cards[device].add(card)
            if card in self.cb_cards:
                self.device_cb[device] += 1
        if ip not in self.card_ips[card]:
            self.card_ips[card].add(ip)
            self.ip_cards[ip].add(card)
            if card in self.cb_cards:
                self.ip_cb[ip] += 1
        self.card_amounts[card].append(amount)
        self.card_times[card].append(t)
        self.device_times[device].append(t)
        if amount < 5.0:
            self.device_small_times[device].append(t)
        self.merchant_times[merchant].append(t)
        if chargeback_time is not None and not (isinstance(chargeback_time, float)
                                                and math.isnan(chargeback_time)):
            heapq.heappush(self._pending, (float(chargeback_time), card, merchant))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute features for a whole (time-sorted) transaction table."""
    fz = StreamingGraphFeaturizer()
    out = []
    for r in df.itertuples(index=False):
        out.append(fz.transform_one(r.timestamp, r.merchant_id, r.card_id, r.device_id,
                                    r.ip_id, r.amount))
        fz.update(r.timestamp, r.merchant_id, r.card_id, r.device_id, r.ip_id, r.amount,
                  r.chargeback_time)
    return pd.DataFrame(out, columns=ALL_FEATURES, index=df.index)
