"""Command-line interface: ``explainguard generate | benchmark | verify-log``."""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from .audit import verify_log
from .generator import SCHEMA, GeneratorConfig, generate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="explainguard", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="write a synthetic small-merchant transaction CSV")
    g.add_argument("--out", default="transactions.csv")
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--days", type=int, default=90)

    b = sub.add_parser("benchmark", help="run the full benchmark protocol")
    b.add_argument("--out", default="results")
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--scenario", choices=["standard", "novel_attack", "both"], default="both")
    b.add_argument("--data", help="optional CSV with the generator schema instead of synthetic data")

    v = sub.add_parser("verify-log", help="verify a tamper-evident audit log")
    v.add_argument("path")

    a = p.parse_args(argv)
    if a.cmd == "generate":
        generate(GeneratorConfig(seed=a.seed, days=a.days)).to_csv(a.out, index=False)
        print(f"wrote {a.out}")
    elif a.cmd == "benchmark":
        from .benchmark import run_benchmark
        if a.data:
            df = pd.read_csv(a.data)
            missing = set(SCHEMA) - set(df.columns) - {"txn_id", "fraud_type"}
            if missing:
                sys.exit(f"CSV is missing columns: {sorted(missing)}")
            df = df.sort_values("timestamp").reset_index(drop=True)
            df["fraud_type"] = df.get("fraud_type", df["is_fraud"].map({0: "legit", 1: "fraud"}))
            if "txn_id" not in df:
                df["txn_id"] = [f"T{i:07d}" for i in range(len(df))]
            r = run_benchmark(data=df, out_dir=a.out, scenario="external")
            print(json.dumps(r["targets"], indent=2, default=float))
            return 0
        scen = ["standard", "novel_attack"] if a.scenario == "both" else [a.scenario]
        for s in scen:
            cfg = GeneratorConfig(seed=a.seed, card_testing_start_day=72 if s == "novel_attack" else 0)
            r = run_benchmark(cfg, out_dir=a.out, scenario=s)
            print(f"[{s}]", json.dumps({k: v["met"] for k, v in r["targets"].items()}))
    elif a.cmd == "verify-log":
        r = verify_log(a.path)
        print(json.dumps(r, indent=2))
        return 0 if r["valid"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
