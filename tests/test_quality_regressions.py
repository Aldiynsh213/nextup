import json

import pandas as pd
import pytest

from sheetflow.cli import main
from sheetflow.core import (
    DataValidationError,
    clean_dataframe,
    deduplicate_dataframe,
    profile_dataframe,
)
from sheetflow.io import read_table


def test_currency_parser_handles_usd_and_indonesian_formats():
    frame = pd.DataFrame(
        {
            "usd_amount": ["$1,234.50", "(1,234.50)", "bad"],
            "idr_amount": ["Rp1.234,50", "€ 2.000,00", "not available"],
        }
    )
    cleaned, metrics = clean_dataframe(
        frame,
        {
            "numeric_columns": ["usd_amount", "idr_amount"],
            "numeric_options": {
                "usd_amount": {"decimal_separator": ".", "thousands_separator": ","},
                "idr_amount": {"decimal_separator": ",", "thousands_separator": "."},
            },
            "drop_empty_rows": False,
        },
    )

    assert cleaned.loc[0, "usd_amount"] == 1234.50
    assert cleaned.loc[1, "usd_amount"] == -1234.50
    assert cleaned.loc[0, "idr_amount"] == 1234.50
    assert cleaned.loc[1, "idr_amount"] == 2000.00
    assert pd.isna(cleaned.loc[2, "usd_amount"])
    assert metrics["coerced_values"] == {"usd_amount": 1, "idr_amount": 1}


def test_mixed_date_parser_respects_dayfirst():
    frame = pd.DataFrame(
        {
            "order_date": [
                "2025-03-12",
                "12/03/2025",
                "12 Mar 2025",
                "not a date",
            ]
        }
    )
    cleaned, metrics = clean_dataframe(
        frame,
        {
            "date_columns": ["order_date"],
            "date_options": {"order_date": {"dayfirst": True}},
            "drop_empty_rows": False,
        },
    )

    expected = pd.Timestamp("2025-03-12")
    assert cleaned.loc[0, "order_date"] == expected
    assert cleaned.loc[1, "order_date"] == expected
    assert cleaned.loc[2, "order_date"] == expected
    assert pd.isna(cleaned.loc[3, "order_date"])
    assert metrics["coerced_values"]["order_date"] == 1


def test_duplicate_rows_across_sources_are_detected_by_business_key():
    frame = pd.DataFrame(
        {
            "order_id": ["A-100", "A-100", "A-101"],
            "amount": [100, 100, 200],
            "source_file": ["part_a.csv", "part_b.csv", "part_b.csv"],
        }
    )

    report = profile_dataframe(frame, key_columns=["order_id"])

    assert report["duplicate_rows"] == 0
    assert report["business_key"]["duplicate_rows"] == 1
    assert report["business_key"]["duplicate_groups"] == 1


def test_deduplication_keeps_rows_with_missing_business_keys():
    frame = pd.DataFrame(
        {
            "order_id": ["A-100", "A-100", None, None],
            "amount": [100, 100, 50, 50],
        }
    )
    cleaned, metrics = deduplicate_dataframe(frame, subset=["order_id"])

    assert len(cleaned) == 3
    assert metrics["duplicates_removed"] == 1
    assert cleaned["order_id"].isna().sum() == 2


def test_post_append_deduplication_removes_cross_file_duplicates(tmp_path):
    part_a = tmp_path / "part_a.csv"
    part_b = tmp_path / "part_b.csv"
    part_a.write_text(
        "order_id,amount\nA-100,100\nA-101,200\n", encoding="utf-8"
    )
    part_b.write_text(
        "amount,order_id\n100,A-100\n300,A-102\n", encoding="utf-8"
    )
    config = {
        "inputs": [part_a.name, part_b.name],
        "cleaning": {
            "normalize_columns": True,
            "deduplicate": False,
            "numeric_columns": ["amount"],
        },
        "combine": {
            "mode": "append",
            "source_column": "source_file",
            "deduplicate_after_combine": True,
            "deduplicate_on": ["order_id"],
            "keep": "first",
        },
        "output": "combined.xlsx",
        "report": "quality.json",
    }
    config_path = tmp_path / "pipeline.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    assert main(["run", "--config", str(config_path)]) == 0

    output = read_table(tmp_path / "combined.xlsx")
    report = json.loads((tmp_path / "quality.json").read_text(encoding="utf-8"))

    assert len(output) == 3
    assert output["order_id"].tolist() == ["A-100", "A-101", "A-102"]
    assert report["post_combine_deduplication"]["duplicates_removed"] == 1
    assert report["output_profile"]["business_key"]["duplicate_rows"] == 0


def test_numeric_options_must_be_objects():
    frame = pd.DataFrame({"amount": ["$10.00"]})
    with pytest.raises(DataValidationError, match="numeric_options"):
        clean_dataframe(
            frame,
            {
                "numeric_columns": ["amount"],
                "numeric_options": [],
            },
        )
