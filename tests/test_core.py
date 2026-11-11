import pandas as pd
import pytest

from sheetflow.core import (
    DataValidationError,
    append_frames,
    clean_dataframe,
    join_frames,
    normalize_columns,
    profile_dataframe,
)


def test_normalize_columns_avoids_name_collisions():
    frame = pd.DataFrame([[1, 2, 3]], columns=["Name", "Name", "Name_2"])
    assert list(normalize_columns(frame).columns) == ["name", "name_2", "name_2_2"]


def test_clean_trims_converts_and_deduplicates():
    frame = pd.DataFrame(
        {
            " Customer ID ": [" 001 ", "001", "002"],
            "Revenue": ["10.5", "10.5", "bad"],
            "Signup Date": ["2025-01-01", "2025-01-01", "bad"],
            "Name": [" Alice ", " Alice ", "  "],
        }
    )
    cleaned, metrics = clean_dataframe(
        frame,
        {
            "numeric_columns": ["revenue"],
            "date_columns": ["signup_date"],
            "deduplicate_on": ["customer_id"],
            "required_columns": ["customer_id", "name"],
        },
    )
    assert len(cleaned) == 2
    assert cleaned.loc[0, "customer_id"] == "001"
    assert cleaned.loc[0, "name"] == "Alice"
    assert pd.isna(cleaned.loc[1, "name"])
    assert metrics["duplicates_removed"] == 1
    assert metrics["coerced_values"]["revenue"] == 1
    assert metrics["coerced_values"]["signup_date"] == 1


def test_required_columns_fail_fast():
    with pytest.raises(DataValidationError, match="required_columns"):
        clean_dataframe(
            pd.DataFrame({"name": ["A"]}),
            {"required_columns": ["email"]},
        )


def test_append_aligns_schemas_and_tracks_source():
    left = pd.DataFrame({"id": [1], "name": ["A"]})
    right = pd.DataFrame({"id": [2], "email": ["b@example.test"]})
    result = append_frames([left, right], ["a.csv", "b.csv"], "source_file")
    assert result.loc[1, "source_file"] == "b.csv"
    assert pd.isna(result.loc[1, "name"])


def test_join_checks_cardinality():
    customers = pd.DataFrame({"customer_id": [1, 2], "name": ["A", "B"]})
    orders = pd.DataFrame({"customer_id": [1, 1, 3], "total": [10, 20, 30]})
    result = join_frames(
        [customers, orders], "customer_id", how="left", validate="one_to_many"
    )
    assert len(result) == 3
    with pytest.raises(pd.errors.MergeError):
        join_frames(
            [customers, orders], "customer_id", how="left", validate="one_to_one"
        )


def test_profile_reports_missing_values():
    report = profile_dataframe(
        pd.DataFrame({"id": [1, 2], "email": ["a@example.test", None]})
    )
    assert report["row_count"] == 2
    assert report["missing_values"] == 1
    assert report["columns"]["email"]["missing_count"] == 1
