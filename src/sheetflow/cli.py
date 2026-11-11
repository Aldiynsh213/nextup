"""Command-line interface for SheetFlow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sheetflow.core import (
    DataValidationError,
    clean_dataframe,
    combine_frames,
    profile_dataframe,
)
from sheetflow.io import load_json, read_table, write_json, write_table


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sheetflow",
        description="Clean, validate, profile, and combine Excel/CSV datasets.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    profile = sub.add_parser("profile", help="Generate a data-quality profile.")
    profile.add_argument("input")
    profile.add_argument("--output")

    clean = sub.add_parser("clean", help="Clean one CSV or Excel file.")
    clean.add_argument("input")
    clean.add_argument("--output", "-o", required=True)
    clean.add_argument("--config")
    clean.add_argument("--report")

    combine = sub.add_parser("combine", help="Append or join multiple files.")
    combine.add_argument("inputs", nargs="+")
    combine.add_argument("--mode", choices=["append", "join"], default="append")
    combine.add_argument("--on", nargs="+")
    combine.add_argument("--how", choices=["left", "right", "inner", "outer"], default="outer")
    combine.add_argument(
        "--validate",
        choices=["one_to_one", "one_to_many", "many_to_one", "many_to_many"],
    )
    combine.add_argument("--source-column")
    combine.add_argument("--cleaning-config")
    combine.add_argument("--output", "-o", required=True)
    combine.add_argument("--report")

    run = sub.add_parser("run", help="Execute a repeatable JSON pipeline.")
    run.add_argument("--config", required=True)
    return parser


def _clean_options(path: str | None) -> dict[str, Any]:
    return load_json(path) if path else {}


def _run_pipeline(config_path: str) -> dict[str, Any]:
    config_file = Path(config_path).resolve()
    config = load_json(config_file)
    inputs = config.get("inputs", [])
    if not isinstance(inputs, list) or not inputs:
        raise DataValidationError("Pipeline config must contain a non-empty inputs array.")

    def resolve(value: str) -> Path:
        candidate = Path(value)
        return candidate if candidate.is_absolute() else config_file.parent / candidate

    cleaning = config.get("cleaning", {})
    combine = config.get("combine", {})
    frames = []
    metrics = []
    for input_path in inputs:
        cleaned, item_metrics = clean_dataframe(
            read_table(resolve(input_path)), cleaning
        )
        frames.append(cleaned)
        metrics.append({"input": input_path, **item_metrics})

    mode = combine.get("mode", "append")
    combined = combine_frames(
        frames,
        mode=mode,
        on=combine.get("on"),
        how=combine.get("how", "outer"),
        source_names=[Path(value).name for value in inputs],
        source_column=combine.get("source_column"),
        validate=combine.get("validate"),
    )
    output = config.get("output", "output/combined.xlsx")
    write_table(combined, resolve(output))
    report = {
        "pipeline": config_file.name,
        "input_count": len(inputs),
        "mode": mode,
        "input_cleaning": metrics,
        "output": output,
        "output_profile": profile_dataframe(combined),
    }
    if config.get("report"):
        write_json(report, resolve(config["report"]))
    return report


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "profile":
            report = profile_dataframe(read_table(args.input))
            if args.output:
                write_json(report, args.output)
            print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
            return 0

        if args.command == "clean":
            cleaned, metrics = clean_dataframe(
                read_table(args.input), _clean_options(args.config)
            )
            write_table(cleaned, args.output)
            report = {
                "cleaning": metrics,
                "output_profile": profile_dataframe(cleaned),
            }
            if args.report:
                write_json(report, args.report)
            print(json.dumps({"output": args.output, **metrics}, indent=2, default=str))
            return 0

        if args.command == "combine":
            cleaning = _clean_options(args.cleaning_config)
            frames = []
            metrics = []
            for path in args.inputs:
                cleaned, item_metrics = clean_dataframe(read_table(path), cleaning)
                frames.append(cleaned)
                metrics.append({"input": path, **item_metrics})
            combined = combine_frames(
                frames,
                mode=args.mode,
                on=args.on,
                how=args.how,
                source_names=[Path(value).name for value in args.inputs],
                source_column=args.source_column,
                validate=args.validate,
            )
            write_table(combined, args.output)
            report = {
                "input_cleaning": metrics,
                "output": args.output,
                "output_profile": profile_dataframe(combined),
            }
            if args.report:
                write_json(report, args.report)
            print(json.dumps(report, indent=2, default=str))
            return 0

        if args.command == "run":
            report = _run_pipeline(args.config)
            print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
            return 0

    except (DataValidationError, FileNotFoundError, ValueError) as exc:
        print(f"sheetflow: error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
