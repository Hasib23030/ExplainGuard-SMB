import json

from explainguard.audit import AuditLog, verify_log


def _write(path, n=5):
    log = AuditLog(path)
    for i in range(n):
        log.append({"txn_id": f"T{i}", "decision": "ALLOW", "score": i / 10})
    return log


def test_valid_chain(tmp_path):
    p = tmp_path / "log.jsonl"
    log = _write(p)
    r = verify_log(p)
    assert r == {"valid": True, "records": 5, "first_bad_seq": None, "head": log.head}


def test_tamper_detected_and_located(tmp_path):
    p = tmp_path / "log.jsonl"
    _write(p)
    lines = p.read_text().splitlines()
    rec = json.loads(lines[2]); rec["decision"] = "REVIEW"
    lines[2] = json.dumps(rec)
    p.write_text("\n".join(lines) + "\n")
    r = verify_log(p)
    assert not r["valid"] and r["first_bad_seq"] == 2


def test_deletion_detected(tmp_path):
    p = tmp_path / "log.jsonl"
    _write(p)
    lines = p.read_text().splitlines()
    del lines[1]
    p.write_text("\n".join(lines) + "\n")
    assert verify_log(p)["first_bad_seq"] == 1


def test_reopen_continues_chain(tmp_path):
    p = tmp_path / "log.jsonl"
    _write(p, 3)
    log = AuditLog(p)
    log.append({"txn_id": "T3"})
    assert verify_log(p)["valid"] and verify_log(p)["records"] == 4
