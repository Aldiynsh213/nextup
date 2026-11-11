"""Check the expected results of the 30,900-row synthetic benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from sheetflow.io import read_table


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    metadata = json.loads(
        (root / "benchmarks" / "generated" / "metadata.json").read_text(
            encoding="utf-8"
        )
    )
    report = json.loads(
        (root / "output" / "orders_quality.json").read_text(encoding="utf-8")
    )
    output = read_table(root / "output" / "orders_cleaned.xlsx")

    assert metadata["input_rows"] == 30_900
    assert metadata["unique_order_ids"] == 30_000
    assert len(output) == 30_000
    assert report["post_combine_deduplication"]["duplicates_removed"] == 900
    assert report["output_profile"]["business_key"]["duplicate_rows"] == 0
    assert report["output_profile"]["business_key"]["unique_keys"] == 30_000
    assert output["source_file"].nunique() == 2

    date_failures = sum(
        item["coerced_values"]["order_date"]
        for item in report["input_cleaning"]
    )
    assert date_failures == 0

    summary = {
        "input_rows": metadata["input_rows"],
        "unique_order_ids": metadata["unique_order_ids"],
        "output_rows": len(output),
        "duplicates_removed_after_append": report[
            "post_combine_deduplication"
        ]["duplicates_removed"],
        "remaining_business_key_duplicates": report["output_profile"][
            "business_key"
        ]["duplicate_rows"],
        "date_conversion_failures": date_failures,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
