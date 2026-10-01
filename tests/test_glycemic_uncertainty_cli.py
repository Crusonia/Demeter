import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded


def test_cli_writes_aggregate_report_and_preserves_existing_files(tmp_path, monkeypatch):
    from demeter.data import glycemic_uncertainty

    report = {
        "kind": "glycemic_joint_uncertainty",
        "model_role": "benchmark_only",
        "direct_initialization_allowed": False,
        "provenance": {"scope": "Synthetic CLI fixture; no clinical inference"},
    }
    monkeypatch.setattr(glycemic_uncertainty, "joint_report", lambda registry: report)
    output = tmp_path / "new-report.json"
    result = CliRunner().invoke(app, ["evidence", "glycemic-uncertainty", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert output.read_bytes() == encoded(report)
    summary = json.loads(result.output)
    assert summary["direct_initialization_allowed"] is False
    existing = tmp_path / "existing-source.json"
    existing.write_bytes(b"immutable source")
    alias = tmp_path / "source-alias.json"
    alias.hardlink_to(existing)
    refused = CliRunner().invoke(app, ["evidence", "glycemic-uncertainty", "--output", str(alias)])
    assert refused.exit_code != 0
    assert existing.read_bytes() == alias.read_bytes() == b"immutable source"


def test_offline_cli_reproduces_committed_report(tmp_path):
    output = tmp_path / "joint.json"
    result = CliRunner().invoke(app, ["evidence", "glycemic-uncertainty", "--output", str(output)])
    assert result.exit_code == 0, result.output
    actual = output.read_bytes()
    expected = Path("docs/validation/joint-glycemic-uncertainty.json").read_bytes()
    if actual != expected:
        pytest.fail(
            f"Report bytes differ: actual SHA {digest(actual)}, expected SHA {digest(expected)}"
        )
    report = json.loads(output.read_bytes())
    assert not report["scientific_release_ready"]
    assert not report["direct_initialization_allowed"]
