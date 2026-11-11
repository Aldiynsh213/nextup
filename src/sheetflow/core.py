"""Core dataframe transformations for SheetFlow."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
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
        "empty_rows_removed": 0,
        "coerced_values": {},
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

    for column in numeric_columns:
        original = int(result[column].notna().sum())
        converted = pd.to_numeric(result[column], errors="coerce")
        metrics["coerced_values"][column] = max(
            0, original - int(converted.notna().sum())
        )
        result[column] = converted

    for column in date_columns:
        original = int(result[column].notna().sum())
        converted = pd.to_datetime(result[column], errors="coerce")
        metrics["coerced_values"][column] = max(
            0, original - int(converted.notna().sum())
        )
        result[column] = converted

    if options.get("drop_empty_rows", True):
        empty_mask = result.isna().all(axis=1)
        metrics["empty_rows_removed"] = int(empty_mask.sum())
        result = result.loc[~empty_mask].copy()

    if options.get("deduplicate", True):
        subset = options.get("deduplicate_on")
        if subset:
            subset = list(subset)
            _ensure_columns(result, subset, "deduplicate_on")
        keep = options.get("keep", "first")
        if keep not in {"first", "last"}:
            raise DataValidationError("keep must be either first or last.")
        duplicate_mask = result.duplicated(subset=subset, keep=keep)
        metrics["duplicates_removed"] = int(duplicate_mask.sum())
        result = result.loc[~duplicate_mask].copy()

    metrics.update(
        {
            "rows_after": int(len(result)),
            "columns_after": int(len(result.columns)),
            "missing_values_after": int(result.isna().sum().sum()),
            "required_columns": required_columns,
        }
    )
    return result.reset_index(drop=True), metrics


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    """Build a JSON-serializable column-level data-quality profile."""
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
    return {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_values": int(frame.isna().sum().sum()),
        "columns": columns,
    }


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
    keys = [on] if isinstance(on, str) else list(on)
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
