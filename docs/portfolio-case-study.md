# Working with customer data from more than one spreadsheet

## The situation

Imagine receiving two customer exports from different teams. One file calls a field \`Customer ID\`, while the other uses \`Customer ID\` with slightly different spacing. Some rows are repeated. A date is entered in the wrong format, and one revenue value is not a number.

This is a small example, but it is the kind of cleanup that can take time when the same steps have to be repeated every week.

## What I did

I put together SheetFlow so the cleanup rules can be saved and run again instead of being applied by hand each time.

The sample workflow:

1. Reads both CSV files and keeps customer IDs such as \`0001\` as text.
2. Renames the headers to a consistent format and removes extra spaces from text.
3. Converts the configured signup date and revenue columns.
4. Removes repeated customer IDs using the rule in the configuration.
5. Adds the remaining rows together and records which file each row came from.
6. Saves an Excel workbook and a JSON report describing the cleanup.

## What happens to the sample

The two sample files contain seven rows in total. One repeated customer ID is removed, leaving six rows in the combined file. The invalid revenue value and invalid signup date are counted in the report and become missing values. They are not silently treated as valid data.

These numbers come from the sample files in this repository. They are not results from a paid client project or a production system.

## Why I made the rules configurable

Not every duplicate is an error, and not every column that contains digits should become a number. A customer ID, for example, may need its leading zeros. That is why the user chooses the deduplication key and the columns to convert.

The same idea applies when joining data. The join key and expected relationship should be clear before two files are merged. SheetFlow can check the relationship, but it cannot decide the business meaning of the data for you.

## Tools used

Python, pandas, Excel, CSV, JSON configuration, pytest, Ruff, Git, and GitHub Actions.
