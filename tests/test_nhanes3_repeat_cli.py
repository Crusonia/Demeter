"""Public-only CLI behavior and write protection before admitted replay."""

import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data import nhanes3_repeat_admission as admission

runner = CliRunner()


@pytest.mark.parametrize(
    "target",
    [
        "docs/validation/missing-repeat.json",
        "data/new-repeat.json",
        "src/new-repeat.json",
        "evidence/new-repeat.json",
        "evidence/parameters.yaml",
    ],
)
def test_protected_output_refused_before_any_calculation(monkeypatch, target):
    def forbidden(*args, **kwargs):
        pytest.fail("Protected output reached admitted replay")

    monkeypatch.setattr(admission, "report", forbidden)
    result = runner.invoke(app, ["evidence", "nhanes3-repeat-fpg", "--output", target])
    assert result.exit_code == 1
    assert "Output must be new" in result.output


def test_existing_output_preserved_before_any_calculation(monkeypatch, tmp_path):
    target = tmp_path / "existing.json"
    target.write_bytes(b"preserved")
    monkeypatch.setattr(admission, "report", lambda *args: pytest.fail("Unexpected replay"))
    result = runner.invoke(app, ["evidence", "nhanes3-repeat-fpg", "--output", str(target)])
    assert result.exit_code == 1 and target.read_bytes() == b"preserved"


def test_only_public_projection_emitted_and_saved(monkeypatch, tmp_path):
    import json

    public = {"kind": "synthetic_coarse", "diagnostic_status": "withheld"}
    monkeypatch.setattr(admission, "report", lambda *args: public)
    target = tmp_path / "new" / "public.json"
    result = runner.invoke(app, ["evidence", "nhanes3-repeat-fpg", "--output", str(target)])
    assert result.exit_code == 0
    assert json.loads(result.output) == public
    assert json.loads(target.read_bytes()) == public


def test_failure_text_is_sanitized_and_does_not_create_output(monkeypatch, tmp_path):
    def failure(*args):
        raise ValueError("synthetic private value")

    monkeypatch.setattr(admission, "report", failure)
    target = tmp_path / "new" / "failed.json"
    result = runner.invoke(app, ["evidence", "nhanes3-repeat-fpg", "--output", str(target)])
    assert result.exit_code == 1
    assert "private value" not in result.output
    assert not target.parent.exists()


def test_source_destination_refused_before_replay(monkeypatch, tmp_path):
    source = tmp_path / "sources"
    monkeypatch.setattr(admission, "report", lambda *args: pytest.fail("Unexpected replay"))
    target = source / "new.json"
    result = runner.invoke(
        app, ["evidence", "nhanes3-repeat-fpg", "--source", str(source), "--output", str(target)]
    )
    assert result.exit_code == 1 and not source.exists()


def test_dangling_symlink_refused_before_replay(monkeypatch, tmp_path):
    target = tmp_path / "link.json"
    try:
        target.symlink_to(tmp_path / "missing.json")
    except OSError:
        pytest.skip("Platform cannot create symlinks")
    monkeypatch.setattr(admission, "report", lambda *args: pytest.fail("Unexpected replay"))
    result = runner.invoke(app, ["evidence", "nhanes3-repeat-fpg", "--output", str(target)])
    assert result.exit_code == 1 and target.is_symlink()
