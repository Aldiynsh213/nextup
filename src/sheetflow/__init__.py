"""SheetFlow: practical data cleaning and integration for Excel and CSV files."""

from sheetflow.core import (
    DataValidationError,
    append_frames,
    clean_dataframe,
    combine_frames,
    deduplicate_dataframe,
    join_frames,
    profile_dataframe,
)

__version__ = "1.1.0"

__all__ = [
    "DataValidationError",
    "append_frames",
    "clean_dataframe",
    "combine_frames",
    "deduplicate_dataframe",
    "join_frames",
    "profile_dataframe",
]
