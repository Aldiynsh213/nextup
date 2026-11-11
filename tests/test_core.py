import pandas as pd
import pytest

from sheetflow.core import (
    DataValidationError,
    append_frames,
    clean_dataframe,
    deduplicate_dataframe,
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


def test_currency_parser_handles_usd_and_indonesian_formats():
    frame = pd.DataFrame(
        {
            "usd_amount": ["$1,234.50", "(USD 25.00)", "not money", "US$1,000.00", "$12,34.50"],
            "idr_amount": ["Rp1.234,50", "IDR 2.000,00", "Rp 500,00"],
        }
    )
    cleaned, metrics = clean_dataframe(
        frame,
        {
            "numeric_columns": ["usd_amount", "idr_amount"],
            "numeric_options": {
                "usd_amount": {
                    "decimal_separator": ".",
                    "thousands_separator": ",",
                },
                "idr_amount": {
                    "decimal_separator": ",",
                    "thousands_separator": ".",
                },
            },
            "deduplicate": False,
        },
    )
    assert cleaned["usd_amount"].iloc[0] == pytest.approx(1234.50)
    assert cleaned["usd_amount"].iloc[1] == pytest.approx(-25.00)
    assert pd.isna(cleaned["usd_amount"].iloc[2])
    assert cleaned["idr_amount"].tolist() == pytest.approx([1234.50, 2000.00, 500.00])
    assert cleaned["usd_amount"].iloc[3] == pytest.approx(1000.00)
    assert pd.isna(cleaned["usd_amount"].iloc[4])
    assert metrics["coerced_values"]["usd_amount"] == 2
    assert metrics["coerced_values"]["idr_amount"] == 0


def test_mixed_date_formats_respect_dayfirst():
    frame = pd.DataFrame(
        {
            "order_date": [
                "2025-03-12",
                "12/03/2025",
                "12 Mar 2025",
                "invalid-date",
            ]
        }
    )
    cleaned, metrics = clean_dataframe(
        frame,
        {
            "date_columns": ["order_date"],
            "date_options": {"order_date": {"dayfirst": True}},
            "deduplicate": False,
        },
    )
    expected = pd.Timestamp("2025-03-12")
    assert cleaned["order_date"].iloc[:3].tolist() == [expected, expected, expected]
    assert pd.isna(cleaned["order_date"].iloc[3])
    assert metrics["coerced_values"]["order_date"] == 1


def test_ambiguous_dates_follow_explicit_dayfirst_setting():
    frame = pd.DataFrame({"date": ["03/04/2025"]})
    us_style, _ = clean_dataframe(
        frame,
        {
            "date_columns": ["date"],
            "date_options": {"date": {"dayfirst": False}},
            "deduplicate": False,
        },
    )
    id_style, _ = clean_dataframe(
        frame,
        {
            "date_columns": ["date"],
            "date_options": {"date": {"dayfirst": True}},
            "deduplicate": False,
        },
    )
    assert us_style.loc[0, "date"] == pd.Timestamp("2025-03-04")
    assert id_style.loc[0, "date"] == pd.Timestamp("2025-04-03")


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


def test_global_deduplication_removes_cross_file_business_key_duplicates():
    left = pd.DataFrame({"order_id": ["001", "002"], "source_file": ["a.csv", "a.csv"]})
    right = pd.DataFrame({"order_id": ["002", "003"], "source_file": ["b.csv", "b.csv"]})
    combined = append_frames([left, right])
    cleaned, metrics = deduplicate_dataframe(combined, subset="order_id")
    assert cleaned["order_id"].tolist() == ["001", "002", "003"]
    assert metrics["duplicates_removed"] == 1
    assert metrics["duplicate_groups_found"] == 1


def test_missing_business_keys_are_retained():
    frame = pd.DataFrame({"order_id": ["001", None, None], "amount": [10, 20, 30]})
    cleaned, metrics = deduplicate_dataframe(frame, subset="order_id")
    assert len(cleaned) == 3
    assert metrics["duplicates_removed"] == 0


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


def test_profile_reports_business_key_duplicates_even_with_source_column():
    frame = pd.DataFrame(
        {
            "order_id": ["001", "001", "002"],
            "source_file": ["a.csv", "b.csv", "a.csv"],
        }
    )
    report = profile_dataframe(frame, key_columns="order_id")
    assert report["duplicate_rows"] == 0
    assert report["business_key"]["duplicate_rows"] == 1
    assert report["business_key"]["duplicate_groups"] == 1
    assert report["business_key"]["unique_keys"] == 2


def test_profile_reports_missing_values():
    report = profile_dataframe(
        pd.DataFrame({"id": [1, 2], "email": ["a@example.test", None]})
    )
    assert report["row_count"] == 2
    assert report["missing_values"] == 1
    assert report["columns"]["email"]["missing_count"] == 1
