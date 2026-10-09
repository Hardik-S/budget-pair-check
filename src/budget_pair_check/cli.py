"""Offline command line interface for paired budget analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .engine import InputError, analyze


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite number is not valid JSON: {value}")


def _read_json(path: str) -> Any:
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            return json.load(
                stream,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_non_finite,
            )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise InputError(f"{path}: {exc}") from exc


def _as_mapping(result: Any) -> dict[str, Any]:
    """Normalize engine output while retaining the contract's field order."""
    conditions = result["conditions"]
    single = conditions["single"]
    team = conditions["team"]
    paired = result["paired"]
    condition_fields = (
        "count", "passed", "failed", "pass_rate", "input_tokens",
        "output_tokens", "total_tokens",
    )
    paired_fields = (
        "count", "both_pass", "both_fail", "single_only_pass", "team_only_pass",
    )
    return {
        "conditions": {
            "single": {field: single[field] for field in condition_fields},
            "team": {field: team[field] for field in condition_fields},
        },
        "paired": {field: paired[field] for field in paired_fields},
    }


def _format_text(summary: dict[str, Any]) -> str:
    rows: list[str] = []
    for name in ("single", "team"):
        values = summary["conditions"][name]
        rows.extend(
            (
                f"{name}:",
                f"  count: {values['count']}",
                f"  passed: {values['passed']}",
                f"  failed: {values['failed']}",
                f"  pass_rate: {values['pass_rate']}",
                f"  input_tokens: {values['input_tokens']}",
                f"  output_tokens: {values['output_tokens']}",
                f"  total_tokens: {values['total_tokens']}",
            )
        )
    paired = summary["paired"]
    rows.extend(
        (
            "paired:",
            f"  count: {paired['count']}",
            f"  both_pass: {paired['both_pass']}",
            f"  both_fail: {paired['both_fail']}",
            f"  single_only_pass: {paired['single_only_pass']}",
            f"  team_only_pass: {paired['team_only_pass']}",
        )
    )
    return "\n".join(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="budget-pair-check",
        description="Analyze paired budget runs from local JSON files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="analyze a manifest and runs file")
    analyze_parser.add_argument("manifest", metavar="MANIFEST.json")
    analyze_parser.add_argument("runs", metavar="RUNS.json")
    analyze_parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = _read_json(args.manifest)
        runs = _read_json(args.runs)
        summary = _as_mapping(analyze(manifest, runs))
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(_format_text(summary))
    return 0
