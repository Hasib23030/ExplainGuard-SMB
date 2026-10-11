import pandas as pd

from explainguard.cli import main


def test_generate_cli(tmp_path):
    out = tmp_path / "t.csv"
    assert main(["generate", "--out", str(out), "--days", "10"]) == 0
    assert len(pd.read_csv(out)) > 100
