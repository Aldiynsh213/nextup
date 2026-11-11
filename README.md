# SheetFlow

**Automated Excel and CSV data cleaning, validation, profiling, and integration with Python.**

SheetFlow is a reproducible, local-first ETL toolkit for teams working with multiple spreadsheet sources. It standardizes headers, trims messy text, preserves identifier values, converts selected date and numeric columns, removes duplicates, validates required fields, combines datasets, and produces data-quality reports.

This portfolio project demonstrates Python, pandas, Excel automation, data cleaning, data integration, repeatable ETL, automated testing, Git, and CI.

## Features

- Reads CSV, XLSX, and XLSM files; writes CSV and XLSX outputs.
- Preserves identifiers such as 0007 as text when reading CSV files.
- Normalizes headers to unique snake_case names.
- Trims text and converts blank strings to missing values.
- Converts explicitly configured date and numeric columns and counts invalid values.
- Removes empty rows and duplicates using full-row matching or declared business keys.
- Appends datasets with different schemas and preserves source-file lineage.
- Joins datasets using left, right, inner, or outer joins.
- Supports join-cardinality validation to catch unexpected one-to-many relationships.
- Generates column-level data-quality profiles and JSON pipeline reports.
- Processes files locally; no datasets are uploaded to a remote service.

## Quick start

Requires Python 3.10 or newer.

1. Create a virtual environment: python -m venv .venv
2. Activate it: source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. Install: pip install -e ".[dev]"
4. Run the example: sheetflow run --config examples/pipeline.json
5. Run tests: pytest
6. Run lint: ruff check .

## CLI examples

- Profile a file: sheetflow profile input.csv --output profile.json
- Clean a file: sheetflow clean input.csv --config examples/cleaning.json --output cleaned.xlsx
- Append files: sheetflow combine source_a.csv source_b.csv --mode append --source-column source_file --output combined.xlsx
- Join files: sheetflow combine customers.xlsx orders.xlsx --mode join --on customer_id --how left --validate one_to_many --output joined.xlsx
- Run a configured workflow: sheetflow run --config examples/pipeline.json

## Pipeline configuration

A JSON pipeline defines input paths, cleaning rules, combine behavior, output path, and optional report path. Relative paths are resolved from the JSON file location.

Supported cleaning options include normalize_columns, rename_columns, trim_strings, drop_empty_rows, deduplicate, deduplicate_on, keep, date_columns, numeric_columns, and required_columns.

Numeric and date conversion is opt-in so identifiers and codes are not accidentally coerced. Review conversion failures and quality reports before using transformed data in production.

## Architecture

CSV or Excel files -> ingestion -> header normalization -> cleaning and validation -> append or keyed join -> Excel/CSV output plus JSON quality report.

## Scope and limitations

- Uses in-memory pandas processing and is intended for small-to-medium spreadsheet workflows.
- Legacy XLS workbooks are not supported; use XLSX or XLSM.
- Joins require explicit keys. Select a cardinality validation rule when the expected relationship is known.
- Keep original source files and never commit client datasets or personally identifiable information to a public repository.

## Example data

All files in examples/data are synthetic. The examples intentionally include inconsistent headers, whitespace, duplicate IDs, blank fields, and invalid date or numeric values so the cleaning behavior can be inspected.

## License

MIT. See LICENSE.
