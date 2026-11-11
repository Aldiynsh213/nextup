# Data quality controls

SheetFlow keeps the rules that can change or remove data visible in configuration and in the run report.

## Business-key deduplication

A full-row duplicate check compares every column. That is not the same as checking whether an order ID or customer ID appears more than once. A source filename column, for example, makes two otherwise identical orders look like different rows.

Use \`deduplicate_on\` to name the business key. For append workflows, use \`deduplicate_after_combine\` so the check runs after every source has been appended. Rows with a missing key are retained; a blank ID is not enough evidence to merge two records.

## Numeric and currency conversion

Numeric conversion is opt-in. Configure separators for each column:

- US-style: decimal \`.\`, thousands \`,\`.
- Indonesian or European-style: decimal \`,\`, thousands \`.\`.

Common currency symbols and codes are removed before parsing. Malformed grouping such as \`12,34.50\` is rejected rather than silently converted. Failed values are counted in \`coerced_values\` and described in \`conversion_details\`.

## Date conversion

Date conversion is also opt-in. Set \`dayfirst\` for sources that use day/month/year. Optional explicit formats can be supplied in a \`formats\` array before the parser tries common formats.

Dates such as \`03/04/2025\` are ambiguous. The parser follows the configured locale; it cannot infer the intended date from that string alone.

## What the report means

- \`duplicate_rows\`: exact repeated rows across all output columns.
- \`business_key.duplicate_rows\`: extra rows sharing a non-empty business key.
- \`business_key.duplicate_groups\`: number of distinct keys that appear more than once.
- \`coerced_values\`: non-empty input values that could not be converted to the requested type.
- \`conversion_details\`: input, converted, and invalid counts plus the parsing settings used.

A successful run means the configured workflow completed. It does not mean every source value was valid. Review the report and the business rules before using the output for financial or operational decisions.
