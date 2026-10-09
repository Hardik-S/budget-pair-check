import copy
import json
from pathlib import Path

import pytest

from budget_pair_check.engine import InputError, analyze


ROOT = Path(__file__).resolve().parents[1]


def example_inputs():
    return (
        json.loads((ROOT / "examples/manifest.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "examples/runs.json").read_text(encoding="utf-8")),
    )


def test_complete_pairs_have_stable_descriptive_totals_and_frozen_shape():
    manifest, runs = example_inputs()
    expected = {
        "task_count": 2,
        "conditions": {
            "single": {"count": 4, "passed": 2, "failed": 2, "pass_rate": 0.5,
                       "input_tokens": 460, "output_tokens": 110, "total_tokens": 570},
            "team": {"count": 4, "passed": 2, "failed": 2, "pass_rate": 0.5,
                     "input_tokens": 660, "output_tokens": 150, "total_tokens": 810},
        },
        "paired": {"count": 4, "both_pass": 1, "both_fail": 1,
                   "single_only_pass": 1, "team_only_pass": 1},
    }
    result = analyze(manifest, runs)
    assert result == expected
    assert analyze(manifest, runs) == expected
    assert result["task_count"] == len(manifest["tasks"])
    assert set(result) == {"task_count", "conditions", "paired"}
    assert set(result["conditions"]["single"]) == {
        "count", "passed", "failed", "pass_rate", "input_tokens", "output_tokens", "total_tokens"
    }
    assert set(result["paired"]) == {
        "count", "both_pass", "both_fail", "single_only_pass", "team_only_pass"
    }


def test_version_and_count_types_are_exact():
    manifest, runs = example_inputs()
    for value in (True, 1.0, "1"):
        bad = copy.deepcopy(manifest)
        bad["version"] = value
        with pytest.raises(InputError, match="manifest.version must be integer 1"):
            analyze(bad, runs)
    for value in (True, 12.0, "12"):
        bad = copy.deepcopy(runs)
        bad["runs"][0]["input_tokens"] = value
        with pytest.raises(InputError, match=r"input_tokens must be a non-negative integer"):
            analyze(manifest, bad)
    bad = copy.deepcopy(runs)
    bad["runs"][0]["test_passed"] = 1
    with pytest.raises(InputError, match="test_passed must be a boolean"):
        analyze(manifest, bad)


@pytest.mark.parametrize("digest", ["", "a" * 63, "g" * 64])
def test_manifest_task_hash_must_be_sha256_hex(digest):
    manifest, runs = example_inputs()
    manifest["tasks"][0]["sha256"] = digest
    with pytest.raises(InputError, match=r"sha256 must be a 64-character SHA-256 hex digest"):
        analyze(manifest, runs)


@pytest.mark.parametrize("field", ["input_tokens", "output_tokens"])
def test_token_counts_reject_missing_negative_boolean_and_noninteger(field):
    manifest, runs = example_inputs()
    missing = copy.deepcopy(runs)
    del missing["runs"][0][field]
    with pytest.raises(InputError, match="invalid keys.*missing keys"):
        analyze(manifest, missing)
    for value in (-1, True, 1.5, "1"):
        bad = copy.deepcopy(runs)
        bad["runs"][0][field] = value
        with pytest.raises(InputError, match=field + r" must be a non-negative integer"):
            analyze(manifest, bad)


def test_matrix_rejects_missing_duplicate_and_unlisted_cells():
    manifest, runs = example_inputs()
    missing = copy.deepcopy(runs)
    missing["runs"].pop()
    with pytest.raises(InputError, match="incomplete matrix; missing cell: synthetic-task-b/rep-2/team"):
        analyze(manifest, missing)

    duplicate = copy.deepcopy(runs)
    duplicate["runs"].append(copy.deepcopy(duplicate["runs"][0]))
    duplicate["runs"][-1]["run_id"] = "new-run-id"
    with pytest.raises(InputError, match="duplicate task/replicate/setting cell"):
        analyze(manifest, duplicate)

    unknown_task = copy.deepcopy(runs)
    unknown_task["runs"][0]["task_id"] = "unlisted-task"
    with pytest.raises(InputError, match="references unknown task: unlisted-task"):
        analyze(manifest, unknown_task)

    unknown_replicate = copy.deepcopy(runs)
    unknown_replicate["runs"][0]["replicate"] = "unlisted-replicate"
    with pytest.raises(InputError, match="references unknown replicate: unlisted-replicate"):
        analyze(manifest, unknown_replicate)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("task_sha256", "0" * 64, "task_sha256 does not match manifest"),
        ("model", "other-synthetic-model", "paired model mismatch"),
        ("harness", "other-synthetic-harness", "paired harness mismatch"),
    ],
)
def test_pair_identity_mismatches_reject_complete_matrix(field, value, message):
    # Keep the full one-task/one-replicate pair so this reaches the intended check.
    manifest, runs = example_inputs()
    manifest["tasks"] = manifest["tasks"][:1]
    manifest["replicates"] = manifest["replicates"][:1]
    runs["runs"] = [row for row in runs["runs"] if row["task_id"] == "synthetic-task-a" and row["replicate"] == "rep-1"]
    runs["runs"][1][field] = value
    with pytest.raises(InputError, match=message):
        analyze(manifest, runs)


def test_over_cap_usage_is_rejected():
    manifest, runs = example_inputs()
    manifest["budget_cap_tokens"] = 100
    # The matrix remains complete; the first run alone exceeds the declared cap.
    with pytest.raises(InputError, match="run a-r1-single exceeds budget_cap_tokens"):
        analyze(manifest, runs)
