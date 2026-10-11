"""Append-only, tamper-evident decision log (SHA-256 hash chain).

Every screening decision is written as one JSON line containing its inputs,
model version, explanation and outcome, plus the hash of the previous record.
Changing, deleting or reordering any record breaks the chain, which
``verify_log`` detects and locates.

This provides tamper *evidence*, not tamper *prevention*: an operator should
periodically publish or escrow the latest hash (the "head") so that the whole
log can be checked against it later.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

GENESIS = "0" * 64


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def record_hash(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.head = GENESIS
        self.count = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.head = json.loads(line)["hash"]
                    self.count += 1

    def append(self, entry: dict) -> str:
        record = {"seq": self.count, "prev_hash": self.head, **entry}
        record["hash"] = record_hash(record)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(_canonical(record) + "\n")
        self.head = record["hash"]
        self.count += 1
        return self.head


def verify_log(path: str | Path) -> dict:
    """Return {'valid': bool, 'records': n, 'first_bad_seq': int|None, 'head': str}."""
    prev = GENESIS
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    for n, line in enumerate(lines):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            return {"valid": False, "records": len(lines), "first_bad_seq": n, "head": prev}
        if rec.get("seq") != n or rec.get("prev_hash") != prev or record_hash(rec) != rec.get("hash"):
            return {"valid": False, "records": len(lines), "first_bad_seq": n, "head": prev}
        prev = rec["hash"]
    return {"valid": True, "records": len(lines), "first_bad_seq": None, "head": prev}
