# Portfolio case study: multi-source customer data preparation

## Business problem

A team receives customer records from separate spreadsheet exports. Headers are inconsistent, text fields contain whitespace, some customer IDs are duplicated, and date or numeric fields may contain invalid values. Combining these files without controls can create unreliable reports.

## Solution

SheetFlow provides a repeatable local ETL workflow:

1. Read two source files while preserving IDs such as 0001.
2. Standardize column names and trim text.
3. Convert selected date and numeric fields.
4. Remove duplicate customer keys using an explicit rule.
5. Append records while retaining source-file lineage.
6. Export an Excel workbook and a JSON data-quality report.

## Demonstration

The bundled synthetic sample contains seven source rows across two files. The configured pipeline removes one duplicate customer key and retains six output rows. It records one invalid revenue conversion and one invalid date conversion rather than silently hiding those issues.

These figures describe only the bundled synthetic sample. They are not claims about a client engagement or production deployment.

## Skills demonstrated

Python, pandas, Excel and CSV automation, data cleaning, schema normalization, data validation, deduplication, append and keyed joins, reproducible ETL, automated testing, Git, and CI.
