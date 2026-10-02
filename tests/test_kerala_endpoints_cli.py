"""CLI saves immutable reports and keeps source/error contents private."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.cli import app

ROOT = Path(__file__).resolve().parents[1]


def test_offline_cli_saves_new_report(tmp_path):
    output = tmp_path / "report.json"
    result = CliRunner().invoke(app, ["evidence", "kerala-endpoints", "--output", str(output)])
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_bytes())
    assert report["source_audit_passed"] is True
    assert report["engine_activation_allowed"] is False
    before = output.read_bytes()
    again = CliRunner().invoke(app, ["evidence", "kerala-endpoints", "--output", str(output)])
    assert again.exit_code == 1
    assert output.read_bytes() == before


@pytest.mark.parametrize("folder", ["data", "src", "docs", "evidence"])
def test_cli_protects_new_files_in_evidence_folders(folder):
    output = ROOT / folder / "endpoint-test-must-not-create.json"
    result = CliRunner().invoke(app, ["evidence", "kerala-endpoints", "--output", str(output)])
    assert result.exit_code == 1
    assert not output.exists()


def test_cli_hides_private_error_text(monkeypatch):
    def fail(*_, **__):
        raise ValueError("PRIVATE_ROW_AND_PATH")

    monkeypatch.setattr("demeter.analysis.kerala_endpoints.audit_kerala_endpoints", fail)
    result = CliRunner().invoke(app, ["evidence", "kerala-endpoints"])
    assert result.exit_code == 1
    assert "PRIVATE_ROW_AND_PATH" not in result.output
    assert "invalid" in result.output
