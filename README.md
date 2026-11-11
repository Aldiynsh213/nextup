# SheetFlow

I built SheetFlow for a familiar spreadsheet problem: data arrives in several files, the columns do not quite match, some rows are repeated, and a few values need fixing before anyone can use the data with confidence.

SheetFlow brings those steps into one repeatable workflow. It reads Excel and CSV files, applies cleaning rules, combines the results, and writes an output workbook with a data-quality report.

The project uses Python and pandas. The examples contain synthetic records, and the test suite covers the main cleaning and integration paths.

## What it can do

- Read CSV, XLSX, and XLSM files. Write the result as CSV or XLSX.
- Keep identifiers such as \`0007\` as text when reading CSV files.
- Standardize column names, trim extra spaces, and treat blank cells as missing values.
- Parse currency and numeric values with an explicit decimal and thousands separator.
- Parse mixed date formats, with an optional \`dayfirst\` setting for dates such as \`12/03/2025\`.
- Remove duplicate rows or duplicate business keys.
- Deduplicate again after files are appended, so repeated records from different sources are not missed.
- Append files with different column orders and keep the source filename for each row.
- Join related tables using one or more keys, with optional relationship checks.
- Report both exact duplicate rows and duplicates based on business keys.
- Run the same steps again from a JSON configuration file.

Files are processed on the machine where SheetFlow runs. The tool does not send datasets to an external service.

## Set it up

Python 3.10 or newer is required.

\`\`\`bash
python -m venv .venv
source .venv/bin/activate
# On Windows: .venv\Scripts\activate

python -m pip install -e ".[dev]"
\`\`\`

Run the sample workflow:

\`\`\`bash
sheetflow run --config examples/pipeline.json
\`\`\`

The cleaned workbook and its JSON report are written to the \`output/\` folder.

## A few commands

Create a profile and check duplicate order IDs:

\`\`\`bash
sheetflow profile orders.csv --key-columns order_id --output profile.json
\`\`\`

Clean one file:

\`\`\`bash
sheetflow clean orders.csv \
  --config examples/cleaning.json \
  --output orders_clean.xlsx \
  --report cleaning_report.json
\`\`\`

Append files and remove repeated order IDs after the append:

\`\`\`bash
sheetflow combine january.csv february.csv \
  --mode append \
  --source-column source_file \
  --deduplicate-after-combine \
  --deduplicate-on order_id \
  --output all_orders.xlsx \
  --report all_orders_quality.json
\`\`\`

Join customer records to their orders:

\`\`\`bash
sheetflow combine customers.xlsx orders.xlsx \
  --mode join \
  --on customer_id \
  --how left \
  --validate one_to_many \
  --output customer_orders.xlsx
\`\`\`

## Append or join?

Use **append** when each file contains more rows of the same kind. For example, January and February order exports can be stacked into one table. If the files have different columns, SheetFlow keeps the columns and leaves missing values where a source did not provide them.

Use **join** when the files contain different details about related records. For example, a customer table can be joined to an orders table through \`customer_id\`. Choose the join type and, when possible, the expected relationship between the keys. The validation option helps catch an unexpected duplicate-key relationship instead of quietly multiplying rows.

## Currency and date formats

Number conversion is opt-in. The separator settings are explicit because \`1,234.50\` and \`1.234,50\` mean different things in different locales.

For example:

\`\`\`json
{
  "numeric_columns": ["amount"],
  "numeric_options": {
    "amount": {
      "decimal_separator": ",",
      "thousands_separator": "."
    }
  },
  "date_columns": ["order_date"],
  "date_options": {
    "order_date": {
      "dayfirst": true
    }
  }
}
\`\`\`

The date parser can read common mixed formats. A date such as \`03/04/2025\` is still ambiguous without a locale rule, so set \`dayfirst\` to match the source. Values that cannot be parsed are counted in the report.

## Duplicate handling

There are two separate checks:

- \`duplicate_rows\` counts rows that match across every column.
- \`business_key\` counts repeated values for the key columns you choose, even when a source column makes the full rows different.

For an append workflow, set \`combine.deduplicate_after_combine\` to \`true\` and provide \`combine.deduplicate_on\`. This is useful when the same order appears in more than one export.

Rows with missing business keys are kept during key-based deduplication. SheetFlow cannot safely decide whether two records without an ID are the same record.

## Run the tests

\`\`\`bash
ruff check .
pytest
\`\`\`

GitHub Actions runs lint and tests on pushes and pull requests.

## Sample data and limits

The files in \`examples/data/\` are made-up records. They include inconsistent headers, extra spaces, a repeated customer ID, and a few invalid values so the cleaning steps can be seen in the output. They do not contain real customer information.

SheetFlow uses pandas in memory, so it is intended for small and medium spreadsheet jobs rather than very large data warehouses. It does not read legacy \`.xls\` files. It can read an \`.xlsm\` worksheet, but it does not carry macros, formulas, or workbook formatting into the output file.

Before using the result for reporting, check the cleaning report and make sure the deduplication key, number locale, date locale, and join rules match the source data.

## Project layout

- \`src/sheetflow/\` — data cleaning, file handling, and command-line code.
- \`examples/\` — sample input files and JSON configurations.
- \`tests/\` — unit tests and regression tests.
- \`docs/\` — notes about the sample scenario and data-quality checks.

## License

MIT. See [LICENSE](LICENSE).
