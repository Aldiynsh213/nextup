import json

import pandas as pd

from sheetflow.cli import main
from sheetflow.io import read_table, write_table


def test_csv_round_trip_preserves_leading_zero_ids(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "output.csv"
    source.write_text("customer_id,name\n0007,Ada\n", encoding="utf-8")
    frame = read_table(source)
    assert frame.loc[0, "customer_id"] == "0007"
    write_table(frame, output)
    assert read_table(output).loc[0, "customer_id"] == "0007"


def test_excel_round_trip(tmp_path):
    source = tmp_path / "source.xlsx"
    frame = pd.DataFrame({"customer_id": ["0007"], "revenue": [12.5]})
    write_table(frame, source)
    restored = read_table(source)
    assert restored.loc[0, "customer_id"] == "0007"
    assert restored.loc[0, "revenue"] == 12.5


def test_json_pipeline_runs_end_to_end(tmp_path):
    source_a = tmp_path / "a.csv"
    source_b = tmp_path / "b.csv"
    source_a.write_text("customer_id,name\n0001,Ada\n", encoding="utf-8")
    source_b.write_text("customer_id,name\n0002,Grace\n", encoding="utf-8")
    config = {
        "inputs": [source_a.name, source_b.name],
        "cleaning": {"normalize_columns": True, "deduplicate": True},
        "combine": {"mode": "append", "source_column": "source_file"},
        "output": "result.xlsx",
        "report": "quality.json",
    }
    config_path = tmp_path / "pipeline.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert main(["run", "--config", str(config_path)]) == 0
    result = read_table(tmp_path / "result.xlsx")
    assert list(result["customer_id"]) == ["0001", "0002"]
    assert (tmp_path / "quality.json").exists()
