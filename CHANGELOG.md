# Changelog

## 1.1.1 - 2026-11-12

- Validate decimal and thousands separator settings before parsing numeric values.
- Add regression coverage for currency codes, malformed thousands groups, and invalid separator settings.
- Extend the 30,900-row benchmark to check that valid amounts and dates remain intact after global deduplication.

## 1.1.0

- Added deduplication after append, using explicit business keys.
- Added business-key duplicate counts to quality profiles.
- Added currency parsing with configurable decimal and thousands separators.
- Added mixed-format date parsing and a configurable day-first setting.
- Added row-level conversion issue samples and configurable schema validation.
- Added regression tests for cross-file duplicates, currency values, and mixed dates.
- Expanded CI to test Python 3.10 through 3.13.
- Updated the sample pipeline and documentation.
