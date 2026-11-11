"""Core dataframe transformations for SheetFlow."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from numbers import Number
from typing import Any

import pandas as pd


class DataValidationError(ValueError):
    """Raised when input data does not satisfy the requested schema."""


def normalize_column_name(value: object) -> str:
    """Convert a column label to a stable snake_case identifier."""
    name = str(value).strip().lower()
    name = re.sub(r"[^\w]+", "_", name, flags=re.UNICODE)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "column"


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize labels and keep every resulting column name unique."""
    used: set[str] = set()
    labels: list[str] = []
    for label in frame.columns:
        base = normalize_column_name(label)
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        used.add(candidate)
        labels.append(candidate)
    result = frame.copy()
    result.columns = labels
    return result


def _ensure_columns(frame: pd.DataFrame, columns: Sequence[str], option: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataValidationError(
            f"Unknown column(s) in {option}: {', '.join(missing)}. "
            f"Available: {', '.join(map(str, frame.columns))}"
        )


def _as_column_list(subset: str | Sequence[str] | None) -> list[str] | None:
    if subset is None:
        return None
    return [subset] if isinstance(subset, str) else list(subset)


def deduplicate_dataframe(
    frame: pd.DataFrame,
    subset: str | Sequence[str] | None = None,
    keep: str = "first",
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remove duplicate rows or duplicate business keys and report what changed.

    Rows with a missing value in any business-key column are retained. A missing
    identifier is not enough evidence to decide that two records are the same.
    """
    if keep not in {"first", "last"}:
        raise DataValidationError("keep must be either first or last.")

    keys = _as_column_list(subset)
    result = frame.copy()
    if keys:
        _ensure_columns(result, keys, "deduplicate_on")
        valid_keys = result[keys].notna().all(axis=1)
        duplicate_mask = pd.Series(False, index=result.index)
        duplicate_mask.loc[valid_keys] = result.loc[valid_keys].duplicated(
            subset=keys, keep=keep
        )
        duplicate_groups_mask = result.loc[valid_keys].duplicated(
            subset=keys, keep=False
        )
        duplicate_groups = int(
            result.loc[valid_keys].loc[duplicate_groups_mask, keys]
            .drop_duplicates()
            .shape[0]
        )
    else:
        duplicate_mask = result.duplicated(keep=keep)
        duplicate_groups_mask = result.duplicated(keep=False)
        duplicate_groups = int(
            result.loc[duplicate_groups_mask].drop_duplicates().shape[0]
        )

    removed = int(duplicate_mask.sum())
    cleaned = result.loc[~duplicate_mask].copy().reset_index(drop=True)
    return cleaned, {
        "duplicate_rows_found": removed,
        "duplicate_groups_found": duplicate_groups,
        "duplicates_removed": removed,
    }


def _parse_numeric_value(
    value: Any,
    decimal_separator: str = ".",
    thousands_separator: str = ",",
) -> float | Any:
    """Parse common currency strings without guessing the locale separators."""
    if value is None or value is pd.NA:
        return pd.NA
    if isinstance(value, Number) and not isinstance(value, bool):
        return value
    try:
        if pd.isna(value):
            return pd.NA
    except (TypeError, ValueError):
        pass

    text = str(value).strip()
    if not text:
        return pd.NA

    if len(decimal_separator) != 1:
        raise DataValidationError("decimal_separator must be one character.")
    if thousands_separator and len(thousands_separator) != 1:
        raise DataValidationError("thousands_separator must be empty or one character.")
    if decimal_separator == thousands_separator and thousands_separator:
        raise DataValidationError(
            "decimal_separator and thousands_separator must be different."
        )

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()

    # Remove common currency codes and Unicode currency symbols, but do not
    # silently discard arbitrary letters that could indicate malformed data.
    text = re.sub(r"(?i)^(?:USD|IDR|EUR|GBP|JPY|RP)\s*", "", text)
    text = re.sub(r"(?i)\s*(?:USD|IDR|EUR|GBP|JPY|RP)$", "", text)
    text = "".join(
        character
        for character in text
        if unicodedata.category(character) != "Sc"
    )
    text = re.sub(r"\s+", "", text)

    if thousands_separator:
        text = text.replace(thousands_separator, "")
    if decimal_separator != ".":
        text = text.replace(decimal_separator, ".")

    if not text or re.search(r"[^0-9.+-]", text):
        return pd.NA
    if text.count(".") > 1:
        return pd.NA
    if text.count("+") + text.count("-") > 1:
        return pd.NA
    if any(sign in text[1:] for sign in "+-"):
        return pd.NA
    if text in {".", "+", "-", "+.", "-."}:
        return pd.NA

    try:
        parsed = float(text)
    except ValueError:
        return pd.NA
    return -abs(parsed) if negative else parsed


def _parse_numeric_series(
    series: pd.Series,
    options: Mapping[str, Any] | None = None,
) -> pd.Series:
    config = dict(options or {})
    decimal_separator = config.get("decimal_separator", ".")
    thousands_separator = config.get("thousands_separator", ",")
    values = series.map(
        lambda value: _parse_numeric_value(
            value,
            decimal_separator=decimal_separator,
            thousands_separator=thousands_separator,
        )
    )
    return pd.to_numeric(values, errors="coerce")


def _parse_date_series(
    series: pd.Series,
    options: Mapping[str, Any] | None = None,
) -> pd.Series:
    """Parse mixed date formats with explicit locale and optional format hints."""
    config = dict(options or {})
    dayfirst = bool(config.get("dayfirst", False))
    formats = config.get("formats", [])
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    for date_format in formats:
        pending = parsed.isna() & series.notna()
        if not pending.any():
            break
        candidate = pd.to_datetime(
            series.loc[pending],
            format=date_format,
            errors="coerce",
            dayfirst=dayfirst,
        )
        parsed.loc[pending] = candidate

    pending = parsed.isna() & series.notna()
    if pending.any():
        parsed.loc[pending] = pd.to_datetime(
            series.loc[pending],
            format="mixed",
            errors="coerce",
            dayfirst=dayfirst,
        )
    return parsed


def clean_dataframe(
    frame: pd.DataFrame,
    config: Mapping[str, Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean data using explicit configuration and return auditable metrics."""
    options = dict(config or {})
    result = frame.copy()
    metrics: dict[str, Any] = {
        "rows_before": int(len(result)),
        "columns_before": int(len(result.columns)),
        "missing_values_before": int(result.isna().sum().sum()),
        "duplicates_removed": 0,
        "duplicate_groups_removed": 0,
        "empty_rows_removed": 0,
        "coerced_values": {},
        "conversion_details": {},
    }

    rename_map = options.get("rename_columns", {})
    if rename_map:
        if not isinstance(rename_map, Mapping):
            raise DataValidationError("rename_columns must be a JSON object.")
        result = result.rename(columns=dict(rename_map))

    if options.get("normalize_columns", True):
        result = normalize_columns(result)

    if options.get("trim_strings", True):
        for column in result.select_dtypes(include=["object", "string"]).columns:
            result[column] = result[column].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )
            result[column] = result[column].replace(r"^\s*$", pd.NA, regex=True)

    date_columns = list(options.get("date_columns", []))
    numeric_columns = list(options.get("numeric_columns", []))
    required_columns = list(options.get("required_columns", []))
    for option, columns in (
        ("date_columns", date_columns),
        ("numeric_columns", numeric_columns),
        ("required_columns", required_columns),
    ):
        _ensure_columns(result, columns, option)

    numeric_options = options.get("numeric_options", {})
    date_options = options.get("date_options", {})
    if not isinstance(numeric_options, Mapping) or not isinstance(date_options, Mapping):
        raise DataValidationError("numeric_options and date_options must be JSON objects.")

    for column in numeric_columns:
        original = int(result[column].notna().sum())
        column_options = numeric_options.get(column, {})
        converted = _parse_numeric_series(result[column], column_options)
        failed = max(0, original - int(converted.notna().sum()))
        metrics["coerced_values"][column] = failed
        metrics["conversion_details"][column] = {
            "kind": "numeric",
            "input_non_null": original,
            "converted_non_null": int(converted.notna().sum()),
            "invalid_values": failed,
            "decimal_separator": column_options.get("decimal_separator", "."),
            "thousands_separator": column_options.get("thousands_separator", ","),
        }
        result[column] = converted

    for column in date_columns:
        original = int(result[column].notna().sum())
        column_options = date_options.get(column, {})
        if not isinstance(column_options, Mapping):
            raise DataValidationError(f"date_options for {column} must be a JSON object.")
        converted = _parse_date_series(result[column], column_options)
        failed = max(0, original - int(converted.notna().sum()))
        metrics["coerced_values"][column] = failed
        metrics["conversion_details"][column] = {
            "kind": "date",
            "input_non_null": original,
            "converted_non_null": int(converted.notna().sum()),
            "invalid_values": failed,
            "dayfirst": bool(column_options.get("dayfirst", False)),
            "formats": list(column_options.get("formats", [])),
        }
        result[column] = converted

    if options.get("drop_empty_rows", True):
        empty_mask = result.isna().all(axis=1)
        metrics["empty_rows_removed"] = int(empty_mask.sum())
        result = result.loc[~empty_mask].copy()

    if options.get("deduplicate", True):
        subset = options.get("deduplicate_on")
        result, duplicate_metrics = deduplicate_dataframe(
            result,
            subset=subset,
            keep=options.get("keep", "first"),
        )
        metrics["duplicates_removed"] = duplicate_metrics["duplicates_removed"]
        metrics["duplicate_groups_removed"] = duplicate_metrics[
            "duplicate_groups_found"
        ]

    metrics.update(
        {
            "rows_after": int(len(result)),
            "columns_after": int(len(result.columns)),
            "missing_values_after": int(result.isna().sum().sum()),
            "required_columns": required_columns,
        }
    )
    return result.reset_index(drop=True), metrics


def profile_dataframe(
    frame: pd.DataFrame,
    key_columns: str | Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a column-level quality profile, including optional business-key duplicates."""
    columns: dict[str, Any] = {}
    for column in frame.columns:
        series = frame[column]
        columns[str(column)] = {
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_percent": (
                round(float(series.isna().mean() * 100), 2) if len(series) else 0.0
            ),
            "unique_count": int(series.nunique(dropna=True)),
            "sample_values": [str(value) for value in series.dropna().head(3).tolist()],
        }

    report: dict[str, Any] = {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_values": int(frame.isna().sum().sum()),
        "columns": columns,
    }

    keys = _as_column_list(key_columns)
    if keys:
        _ensure_columns(frame, keys, "key_columns")
        valid_keys = frame[keys].notna().all(axis=1)
        duplicate_rows = frame.loc[valid_keys].duplicated(subset=keys, keep="first")
        duplicate_groups_mask = frame.loc[valid_keys].duplicated(
            subset=keys, keep=False
        )
        duplicate_groups = int(
            frame.loc[valid_keys].loc[duplicate_groups_mask, keys]
            .drop_duplicates()
            .shape[0]
        )
        report["business_key"] = {
            "columns": keys,
            "duplicate_rows": int(duplicate_rows.sum()),
            "duplicate_groups": duplicate_groups,
            "unique_keys": int(
                frame.loc[valid_keys, keys].drop_duplicates().shape[0]
            ),
            "rows_with_missing_key": int((~valid_keys).sum()),
        }
    return report


def append_frames(
    frames: Sequence[pd.DataFrame],
    source_names: Sequence[str] | None = None,
    source_column: str | None = None,
) -> pd.DataFrame:
    """Append rows from multiple files, aligning columns and retaining lineage."""
    if not frames:
        raise DataValidationError("At least one input dataframe is required.")
    if source_column and any(source_column in frame.columns for frame in frames):
        raise DataValidationError(f"Source column {source_column} already exists.")
    if source_names is not None and len(source_names) != len(frames):
        raise DataValidationError("source_names must have one value per dataframe.")
    prepared = []
    for index, frame in enumerate(frames):
        item = frame.copy()
        if source_column:
            item[source_column] = (
                source_names[index] if source_names else f"source_{index + 1}"
            )
        prepared.append(item)
    return pd.concat(prepared, ignore_index=True, sort=False)


def join_frames(
    frames: Sequence[pd.DataFrame],
    on: str | Sequence[str],
    how: str = "outer",
    validate: str | None = None,
) -> pd.DataFrame:
    """Join two or more dataframes on explicit keys with optional cardinality checks."""
    if len(frames) < 2:
        raise DataValidationError("Join mode requires at least two dataframes.")
    keys = _as_column_list(on)
    if not keys:
        raise DataValidationError("At least one join key is required.")
    if how not in {"left", "right", "inner", "outer"}:
        raise DataValidationError("how must be left, right, inner, or outer.")
    result = frames[0].copy()
    _ensure_columns(result, keys, "join keys")
    for index, frame in enumerate(frames[1:], start=2):
        _ensure_columns(frame, keys, "join keys")
        result = result.merge(
            frame.copy(),
            on=keys,
            how=how,
            suffixes=("", f"_source{index}"),
            validate=validate,
            sort=False,
        )
    return result


def combine_frames(
    frames: Sequence[pd.DataFrame],
    mode: str = "append",
    on: str | Sequence[str] | None = None,
    how: str = "outer",
    source_names: Sequence[str] | None = None,
    source_column: str | None = None,
    validate: str | None = None,
) -> pd.DataFrame:
    """Combine dataframes by appending rows or joining on keys."""
    if mode == "append":
        return append_frames(frames, source_names, source_column)
    if mode == "join":
        if on is None:
            raise DataValidationError("Join mode requires explicit key columns.")
        return join_frames(frames, on, how, validate)
    raise DataValidationError("mode must be append or join.")
