# Data quality controls

This note explains the choices SheetFlow makes when it changes spreadsheet data.

## Duplicate records

Exact duplicate rows and duplicate business keys are different checks. The duplicate_rows profile counts rows that match across every column. The business_key profile counts repeated values in the key columns supplied by the user.

For a multi-file append, set combine.deduplicate_after_combine to true and provide combine.deduplicate_on. This catches a record that appears in more than one source file.

Rows with a missing business key are kept. Two records without an ID should not be treated as the same record just because the key is blank.

## Numeric and currency values

Numeric conversion is opt-in. Configure the decimal and thousands separators for each numeric column. For example, use a dot and comma for 1,234.50, or a comma and dot for 1.234,50.

Common currency symbols and codes are removed before parsing. Parentheses around an amount are treated as a negative value. A value that still cannot be parsed is converted to a missing value and counted in coerced_values.

Do not mix locales in one column unless the input is normalized first. If a column contains both 1,234.50 and 1.234,50, decide on a locale or split the values into separate fields before conversion.

## Dates

SheetFlow tries explicitly configured formats first, then handles ISO dates and common locale formats before using a date parser for remaining values. Set dayfirst when the source uses dates such as 12/03/2025 to mean 12 March.

Some dates cannot be interpreted safely without a locale rule. For example, 03/04/2025 can mean 3 April or 4 March. Set dayfirst to match the source; do not rely on an automatic guess.

## Join validation

Use validate when the relationship between keys is known. For example, a customer table joined to an order table is often one_to_many. A validation failure stops the join rather than silently multiplying records.

## Review before publishing

Cleaning rules can remove rows or change values. Keep an untouched copy of the source files, review conversion failures, and compare row counts and business totals before using the output in a report.


## Row-level schema checks

Use the validation object to describe rules that apply to individual records:

- not_null_columns lists fields that must have a value.
- unique_columns lists fields that should not repeat.
- allowed_values maps a column to its accepted values.
- fail_on_error stops the cleaning step when any of those checks fail.

The report includes counts for each rule and a bounded sample of row numbers and issue types. By default, it does not include the raw invalid values. Set include_invalid_values to true only when you have a reason to include those values in the report.

max_issue_samples controls how many issue examples are kept. The default is 100. This limit applies to the examples in the report, not to the counts; all detected issues are still counted.
