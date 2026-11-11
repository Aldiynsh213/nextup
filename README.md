# SheetFlow

I built SheetFlow for a familiar spreadsheet problem: data arrives in several files, the columns do not quite match, some rows are repeated, and a few values need fixing before anyone can use the data with confidence.

SheetFlow brings those steps into one repeatable workflow. It reads Excel and CSV files, cleans the columns you specify, combines the results, and writes an output workbook together with a data-quality report.

The project is written in Python and uses pandas for the data work. It is a portfolio project, with synthetic sample data and tests that show how the main parts behave.

## What it can do

- Read CSV, XLSX, and XLSM files. Write the result as CSV or XLSX.
- Keep CSV identifiers such as \`0007\` as text instead of turning them into the number \`7\`.
- Standardize column names, trim extra spaces, and treat blank cells as missing values.
- Convert selected columns to dates or numbers. Values that cannot be converted are counted in the cleaning report.
- Remove duplicate rows, or remove duplicates using a key such as \`customer_id\`.
- Append files when they contain the same kind of records, even if their columns are not in the same order.
- Join files when they describe related records, using one or more key columns.
- Check join relationships, for example when one customer can have many orders.
- Create a column-by-column profile showing missing values, unique values, data types, and sample values.
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

Create a quick profile before changing a file:

\`\`\`bash
sheetflow profile customers.csv --output customer_profile.json
\`\`\`

Clean one file using the rules in a JSON file:

\`\`\`bash
sheetflow clean customers.csv \
  --config examples/cleaning.json \
  --output customers_clean.xlsx \
  --report cleaning_report.json
\`\`\`

Append files that contain the same type of records:

\`\`\`bash
sheetflow combine january.csv february.csv \
  --mode append \
  --source-column source_file \
  --output all_customers.xlsx
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

These two operations solve different problems.

Use **append** when each file contains more rows of the same kind. For example, January and February customer exports can be stacked into one table. If the files have different columns, SheetFlow keeps the columns and leaves missing values where a source did not provide them.

Use **join** when the files contain different details about related records. For example, a customer table can be joined to an orders table through \`customer_id\`. Choose the join type and, when possible, the expected relationship between the keys. The validation option helps catch an unexpected duplicate-key relationship instead of quietly multiplying rows.

## Change the cleaning rules

The examples in \`examples/\` are meant to be edited. In \`examples/cleaning.json\`, you can choose which columns should be treated as dates or numbers, which columns must exist, and which key should be used for deduplication.

Date and number conversion is opt-in. That is deliberate: an account number, postal code, or product code should not be changed just because it looks numeric.

A required-column rule checks that the named columns are present. It does not decide whether every row has a valid value in those columns; that kind of business rule needs to be defined for the dataset.

## Run the tests

\`\`\`bash
ruff check .
pytest
\`\`\`

GitHub Actions runs the same lint and test checks when code is pushed to \`main\` or a pull request is opened.

## Sample data and limits

The files in \`examples/data/\` are made-up records. They include inconsistent headers, extra spaces, a repeated customer ID, and a few invalid values so the cleaning steps can be seen in the output. They do not contain real customer information.

SheetFlow uses pandas in memory, so it is intended for small and medium spreadsheet jobs rather than very large data warehouses. It does not read legacy \`.xls\` files. It can read an \`.xlsm\` worksheet, but it does not carry macros, formulas, or workbook formatting into the output file.

Before using the result for reporting, check the cleaning report and make sure the deduplication key and join rules match the way the business actually treats its records.

## Project layout

- \`src/sheetflow/\` — data cleaning, file handling, and command-line code.
- \`examples/\` — sample input files and JSON configurations.
- \`tests/\` — unit tests and an end-to-end pipeline test.
- \`docs/\` — notes about the sample scenario and data-quality checks.

## License

MIT. See [LICENSE](LICENSE).
