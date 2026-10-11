"""Minimal end-to-end example: train on history, then screen new transactions live.

Run:  python examples/quickstart.py
"""
from explainguard.benchmark import matured_labels, time_split
from explainguard.features import ALL_FEATURES, StreamingGraphFeaturizer, build_features
from explainguard.generator import GeneratorConfig, generate
from explainguard.models import HybridDetector
from explainguard.toolkit import Screener
from explainguard.audit import verify_log

df = generate(GeneratorConfig(seed=42, days=60, n_customers=1500))
X = build_features(df)
train, val, test, t_train, t_val = time_split(df)
y_train = matured_labels(df[train], t_train)
y_val = matured_labels(df[val], t_val)

model = HybridDetector(ALL_FEATURES).fit(X[train], y_train).calibrate(X[val][y_val == 0], max_fpr=0.01)

# Warm the graph state with history, then screen the newest transactions one by one.
fz = StreamingGraphFeaturizer()
for r in df[~test].itertuples(index=False):
    fz.transform_one(r.timestamp, r.merchant_id, r.card_id, r.device_id, r.ip_id, r.amount)
    fz.update(r.timestamp, r.merchant_id, r.card_id, r.device_id, r.ip_id, r.amount, r.chargeback_time)

screener = Screener(model, threshold=0.0, audit_path="quickstart_audit.jsonl", featurizer=fz)
for r in df[test].itertuples(index=False):
    d = screener.process(r._asdict())
    if d["decision"] == "REVIEW":
        print(f"{d['txn_id']}  score={d['score']:.2f}  {d['reason_text']}")

print(verify_log("quickstart_audit.jsonl"))
