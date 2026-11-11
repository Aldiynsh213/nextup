"""Create repeatable order and customer datasets for SheetFlow benchmarks."""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path


def make_order(order_number: int) -> dict[str, str]:
    order_date = date(2025, 1, 1) + timedelta(days=(order_number * 7) % 365)
    if order_number % 3 == 0:
        date_value = order_date.isoformat()
    elif order_number % 3 == 1:
        date_value = order_date.strftime("%d/%m/%Y")
    else:
        date_value = order_date.strftime("%d %b %Y")

    amount = 125 + ((order_number * 7919) % 250000) / 100
    if order_number % 20 == 0:
        amount_value = "not-recorded"
    elif order_number % 3 == 0:
        amount_value = "$" + f"{amount:,.2f}"
    elif order_number % 3 == 1:
        amount_value = f"{amount:,.2f}"
    else:
        amount_value = "$" + f"{amount:.2f}"

    return {
        "Order ID": f"ORD-{order_number:06d}",
        "Customer ID": f"CUST-{(order_number % 5000) + 1:06d}",
        "Order Date": date_value,
        "Amount ($)": amount_value,
        "Status": ("paid", "pending", "refunded")[order_number % 3],
        "Channel": ("web", "store", "marketplace")[order_number % 3],
    }


def make_customer(customer_number: int) -> dict[str, str]:
    return {
        "Customer ID": f"CUST-{customer_number:06d}",
        "Customer Name": f"Customer {customer_number:06d}",
        "Segment": ("SMB", "Enterprise", "Consumer")[customer_number % 3],
    }


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def generate(output_dir: Path, seed: int = 20261112) -> dict[str, int]:
    rng = random.Random(seed)
    unique_orders = [make_order(number) for number in range(1, 30001)]
    source_a = unique_orders[:15000]
    source_b = unique_orders[15000:]

    # 449 repeats live inside source A. Another 451 order IDs appear in both
    # files, so a per-file dedup pass still leaves cross-file duplicates.
    source_a.extend(rng.sample(source_a, 449))
    source_b.extend(unique_orders[:451])
    rng.shuffle(source_a)
    rng.shuffle(source_b)

    columns_a = [
        "Order ID",
        "Customer ID",
        "Order Date",
        "Amount ($)",
        "Status",
        "Channel",
    ]
    columns_b = [
        "Channel",
        "Amount ($)",
        "Order Date",
        "Customer ID",
        "Order ID",
        "Status",
    ]

    write_csv(output_dir / "orders_a.csv", source_a, columns_a)
    write_csv(output_dir / "orders_b.csv", source_b, columns_b)
    write_csv(
        output_dir / "orders_unique.csv",
        unique_orders,
        columns_b,
    )
    write_csv(
        output_dir / "customers.csv",
        [make_customer(number) for number in range(1, 5001)],
        ["Customer ID", "Customer Name", "Segment"],
    )

    metadata = {
        "seed": seed,
        "source_a_rows": len(source_a),
        "source_b_rows": len(source_b),
        "input_rows": len(source_a) + len(source_b),
        "unique_order_ids": len(unique_orders),
        "customer_rows": 5000,
        "join_order_rows": len(unique_orders),
        "duplicates_inside_source_a": 449,
        "duplicates_across_sources": 451,
        "expected_rows_after_per_file_dedup_then_append": 30451,
        "expected_rows_after_global_dedup": 30000,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/generated"),
        help="Directory for the generated CSV files.",
    )
    parser.add_argument("--seed", type=int, default=20261112)
    args = parser.parse_args()
    metadata = generate(args.output_dir, args.seed)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
