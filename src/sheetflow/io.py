"""CSV and Excel input/output helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from sheetflow.core import DataValidationError


def read_table(path: str | Path, sheet_name: str | int = 0) -> pd.DataFrame:
    """Read CSV or Excel data, keeping CSV identifiers as strings."""
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Input file not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(
            source,
            dtype="string",
            encoding="utf-8-sig",
            keep_default_na=False,
            na_values=[""],
        )
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(
            source, sheet_name=sheet_name, engine="openpyxl", dtype=object
        )
    raise DataValidationError(f"Unsupported input format: {suffix}")


def write_table(frame: pd.DataFrame, path: str | Path) -> Path:
    """Write a dataframe to CSV or XLSX."""
    destination = Path(path)
    suffix = destination.suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise DataValidationError(f"Unsupported output format: {suffix}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".csv":
        frame.to_csv(destination, index=False, encoding="utf-8-sig")
    else:
        frame.to_excel(destination, index=False, engine="openpyxl")
    return destination


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    """Write a JSON report."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return destination


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON configuration object."""
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise DataValidationError("Configuration root must be a JSON object.")
    return data
