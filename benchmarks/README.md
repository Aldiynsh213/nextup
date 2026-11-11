# SheetFlow order benchmark

This folder contains a small generator for a repeatable test with two CSV files. It is useful for checking cross-file deduplication, mixed date parsing, currency parsing, and the effect of different column orders.

## Generate the data

From the repository root:

```bash
python benchmarks/generate_orders.py --output-dir benchmarks/generated
```

The generator uses a fixed seed by default. It creates 30,900 input rows with 30,000 distinct order IDs:

- Source A has 15,000 unique orders plus 449 repeated rows inside that file.
- Source B has 15,000 other unique orders plus 451 order IDs that also appear in Source A.
- The two files use different column orders.
- Dates use ISO, day-first numeric, and abbreviated month formats.
- Amounts include currency symbols, thousands separators, and a small number of invalid values.

The metadata file records the expected row counts. It is generated locally and is not committed.

## Run the pipeline

Install SheetFlow first, then run:

```bash
sheetflow run --config benchmarks/pipeline.json
```

The output workbook and JSON report are written to the repository's `output/` folder.

## What to check

- Input row count: 30,900.
- Distinct order IDs: 30,000.
- If each file is deduplicated separately and then appended, 30,451 rows remain.
- With `deduplicate_after_combine` enabled, the final output contains 30,000 rows.
- The report should show zero remaining duplicates for the `order_id` business key.
- Invalid amount values should be counted in `coerced_values`; valid currency strings should convert.
- The mixed date formats should parse with `dayfirst: true`.

To compare runtimes on your own machine, use a shell timer around the pipeline command. Record the machine, Python version, pandas version, and run conditions alongside the result. This repository does not publish a fixed performance claim because hardware and file storage affect the timings.
