"""Validation and deterministic summaries for paired token budget receipts."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


class InputError(ValueError):
    """Raised when a manifest or run receipt violates the input contract."""


_MANIFEST_KEYS = {"version", "settings", "budget_cap_tokens", "tasks", "replicates"}
_TASK_KEYS = {"id", "sha256"}
_RUNS_KEYS = {"version", "runs"}
_RUN_KEYS = {
    "run_id", "task_id", "task_sha256", "setting", "replicate", "model",
    "harness", "input_tokens", "output_tokens", "test_passed", "evidence",
}
_SETTINGS = ("single", "team")
_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")


def _object(value: Any, name: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{name} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        details = []
        if missing:
            details.append(f"missing keys: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected keys: {', '.join(extra)}")
        raise InputError(f"{name} has invalid keys ({'; '.join(details)})")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{name} must be a non-empty string")
    return value


def _count(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise InputError(f"{name} must be a non-negative integer")
    return value


def analyze(manifest: Any, runs: Any) -> dict[str, Any]:
    """Validate the complete paired matrix and return aggregate token/pass counts."""
    manifest = _object(manifest, "manifest", _MANIFEST_KEYS)
    if type(manifest["version"]) is not int or manifest["version"] != 1:
        raise InputError("manifest.version must be integer 1")
    if manifest["settings"] != list(_SETTINGS) or type(manifest["settings"]) is not list:
        raise InputError('manifest.settings must be exactly ["single", "team"]')
    cap = manifest["budget_cap_tokens"]
    if type(cap) is not int or cap <= 0:
        raise InputError("manifest.budget_cap_tokens must be a positive integer")

    tasks_raw = manifest["tasks"]
    if type(tasks_raw) is not list or not tasks_raw:
        raise InputError("manifest.tasks must be a non-empty list")
    tasks: dict[str, str] = {}
    for i, raw in enumerate(tasks_raw):
        task = _object(raw, f"manifest.tasks[{i}]", _TASK_KEYS)
        task_id = _string(task["id"], f"manifest.tasks[{i}].id")
        digest = task["sha256"]
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise InputError(f"manifest.tasks[{i}].sha256 must be a 64-character SHA-256 hex digest")
        if task_id in tasks:
            raise InputError(f"duplicate task id: {task_id}")
        tasks[task_id] = digest

    reps_raw = manifest["replicates"]
    if type(reps_raw) is not list or not reps_raw:
        raise InputError("manifest.replicates must be a non-empty list")
    replicates = []
    for i, raw in enumerate(reps_raw):
        rep = _string(raw, f"manifest.replicates[{i}]")
        if rep in replicates:
            raise InputError(f"duplicate replicate id: {rep}")
        replicates.append(rep)

    runs = _object(runs, "runs document", _RUNS_KEYS)
    if type(runs["version"]) is not int or runs["version"] != 1:
        raise InputError("runs.version must be integer 1")
    records = runs["runs"]
    if type(records) is not list:
        raise InputError("runs.runs must be a list")

    by_cell: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    run_ids: set[str] = set()
    for i, raw in enumerate(records):
        run = _object(raw, f"runs.runs[{i}]", _RUN_KEYS)
        run_id = _string(run["run_id"], f"runs.runs[{i}].run_id")
        task_id = _string(run["task_id"], f"runs.runs[{i}].task_id")
        digest = _string(run["task_sha256"], f"runs.runs[{i}].task_sha256")
        setting = _string(run["setting"], f"runs.runs[{i}].setting")
        rep = _string(run["replicate"], f"runs.runs[{i}].replicate")
        model = _string(run["model"], f"runs.runs[{i}].model")
        harness = _string(run["harness"], f"runs.runs[{i}].harness")
        input_tokens = _count(run["input_tokens"], f"runs.runs[{i}].input_tokens")
        output_tokens = _count(run["output_tokens"], f"runs.runs[{i}].output_tokens")
        if type(run["test_passed"]) is not bool:
            raise InputError(f"runs.runs[{i}].test_passed must be a boolean")
        _string(run["evidence"], f"runs.runs[{i}].evidence")
        if run_id in run_ids:
            raise InputError(f"duplicate run_id: {run_id}")
        run_ids.add(run_id)
        if task_id not in tasks:
            raise InputError(f"run {run_id} references unknown task: {task_id}")
        if digest != tasks[task_id]:
            raise InputError(f"run {run_id} task_sha256 does not match manifest")
        if rep not in replicates:
            raise InputError(f"run {run_id} references unknown replicate: {rep}")
        if setting not in _SETTINGS:
            raise InputError(f"run {run_id} has invalid setting: {setting}")
        if input_tokens + output_tokens > cap:
            raise InputError(f"run {run_id} exceeds budget_cap_tokens")
        cell = (task_id, rep, setting)
        if cell in by_cell:
            raise InputError(f"duplicate task/replicate/setting cell: {cell}")
        by_cell[cell] = run

    expected = {
        (task_id, rep, setting)
        for task_id in tasks
        for rep in replicates
        for setting in _SETTINGS
    }
    missing = expected - by_cell.keys()
    if missing:
        task_id, rep, setting = sorted(missing)[0]
        raise InputError(f"incomplete matrix; missing cell: {task_id}/{rep}/{setting}")

    for task_id in tasks:
        for rep in replicates:
            single = by_cell[(task_id, rep, "single")]
            team = by_cell[(task_id, rep, "team")]
            if single["model"] != team["model"]:
                raise InputError(f"paired model mismatch for {task_id}/{rep}")
            if single["harness"] != team["harness"]:
                raise InputError(f"paired harness mismatch for {task_id}/{rep}")

    conditions: dict[str, dict[str, Any]] = {}
    for setting in _SETTINGS:
        selected = [by_cell[cell] for cell in sorted(expected) if cell[2] == setting]
        passed = sum(run["test_passed"] for run in selected)
        input_total = sum(run["input_tokens"] for run in selected)
        output_total = sum(run["output_tokens"] for run in selected)
        count = len(selected)
        conditions[setting] = {
            "count": count,
            "passed": passed,
            "failed": count - passed,
            "pass_rate": passed / count,
            "input_tokens": input_total,
            "output_tokens": output_total,
            "total_tokens": input_total + output_total,
        }

    both_pass = both_fail = single_only_pass = team_only_pass = 0
    for task_id, rep in sorted({(task_id, rep) for task_id, rep, _ in expected}):
        single_pass = by_cell[(task_id, rep, "single")]["test_passed"]
        team_pass = by_cell[(task_id, rep, "team")]["test_passed"]
        if single_pass and team_pass:
            both_pass += 1
        elif not single_pass and not team_pass:
            both_fail += 1
        elif single_pass:
            single_only_pass += 1
        else:
            team_only_pass += 1

    return {
        "task_count": len(tasks),
        "conditions": conditions,
        "paired": {
            "count": len(tasks) * len(replicates),
            "both_pass": both_pass,
            "both_fail": both_fail,
            "single_only_pass": single_only_pass,
            "team_only_pass": team_only_pass,
        },
    }
