import json
import sys
from pathlib import Path

from budget_pair_check.cli import main


ROOT = Path(__file__).resolve().parents[1]


def test_cli_json_success_and_exit_zero(capsys):
    code = main([
        "analyze", str(ROOT / "examples/manifest.json"), str(ROOT / "examples/runs.json"),
        "--format", "json",
    ])
    out = capsys.readouterr()
    assert code == 0
    assert out.err == ""
    parsed = json.loads(out.out)
    assert parsed["conditions"]["single"]["total_tokens"] == 570
    assert parsed["conditions"]["team"]["total_tokens"] == 810
    assert parsed["paired"]["count"] == 4


def test_cli_strict_json_rejects_duplicate_keys_and_nonfinite(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    runs = tmp_path / "runs.json"
    runs.write_text((ROOT / "examples/runs.json").read_text(encoding="utf-8"), encoding="utf-8")

    for content, expected in [
        ('{"version":1,"version":1}', "duplicate object key: 'version'"),
        ('{"version":NaN}', "non-finite number is not valid JSON: NaN"),
        ('{"version":Infinity}', "non-finite number is not valid JSON: Infinity"),
        ('{"version":-Infinity}', "non-finite number is not valid JSON: -Infinity"),
    ]:
        manifest.write_text(content, encoding="utf-8")
        code = main(["analyze", str(manifest), str(runs), "--format", "json"])
        out = capsys.readouterr()
        assert code == 2
        assert expected in out.err
        assert out.out == ""


def test_cli_invalid_matrix_exits_two(tmp_path, capsys):
    manifest = tmp_path / "manifest.json"
    runs = tmp_path / "runs.json"
    manifest.write_text((ROOT / "examples/manifest.json").read_text(encoding="utf-8"), encoding="utf-8")
    bad_runs = json.loads((ROOT / "examples/runs.json").read_text(encoding="utf-8"))
    bad_runs["runs"].pop()
    runs.write_text(json.dumps(bad_runs), encoding="utf-8")
    code = main(["analyze", str(manifest), str(runs)])
    out = capsys.readouterr()
    assert code == 2
    assert "incomplete matrix" in out.err
    assert out.out == ""
