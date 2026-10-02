"""CLI preflight and immutable aggregate output; no synthetic clinical claims."""

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner
from demeter.cli import app
from demeter.data import nhanes_current_store as store
from demeter.data.nhanes import encoded


@pytest.fixture
def summary_report(monkeypatch):
    report = {
        "kind": "nhanes_glycemic_2021_2023",
        "time_period": "August2021-August2023",
        "model_role": "benchmark_only",
        "scientific_release_ready": False,
        "direct_initialization_allowed": False,
        "source_audit_passed": True,
        "counts": {"eligible_n": 3},
        "joint": {
            "coordinates": [{"domain": "synthetic", "membership": "a"}],
            "covariance": [[0.125]],
            "estimates": [0.5],
        },
        "published_reconstruction": {"checks": [{"passed": True}], "passed": True},
        "provenance": {"protocol_sha256": "a" * 64, "source_manifest_sha256": "b" * 64},
    }
    monkeypatch.setattr(store, "report", lambda registry, source: report)
    return report


def test_cli_summary_does_not_print_large_covariance(summary_report):
    result = CliRunner().invoke(app, ["evidence", "glycemic-2021-2023"])
    assert result.exit_code == 0, result.output
    actual = json.loads(result.output)
    assert actual["joint_coordinates"] == 1
    assert actual["published_checks_passed"]
    assert actual["scientific_release_ready"] is False
    assert "covariance" not in result.output


def test_cli_exclusive_aggregate_output(summary_report, tmp_path):
    output = tmp_path / "aggregate.json"
    result = CliRunner().invoke(app, ["evidence", "glycemic-2021-2023", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert output.read_bytes() == encoded(summary_report)
    original = output.read_bytes()
    result = CliRunner().invoke(app, ["evidence", "glycemic-2021-2023", "--output", str(output)])
    assert result.exit_code != 0
    assert output.read_bytes() == original


@pytest.mark.parametrize("folder", ["data", "src", "docs", "evidence"])
def test_cli_refuses_even_missing_frozen_output_before_source_read(folder, monkeypatch):
    called = []
    monkeypatch.setattr(store, "report", lambda *args: called.append(True))
    output = Path(folder) / "DO_NOT_CREATE_NHANES_FIXTURE.json"
    assert not output.exists()
    result = CliRunner().invoke(app, ["evidence", "glycemic-2021-2023", "--output", str(output)])
    assert result.exit_code != 0 and "outside sources" in result.output
    assert not output.exists() and not called


def test_cli_refuses_hardlink_alias(summary_report, tmp_path):
    original = tmp_path / "source.bin"
    original.write_bytes(b"immutable")
    alias = tmp_path / "alias.bin"
    alias.hardlink_to(original)
    result = CliRunner().invoke(app, ["evidence", "glycemic-2021-2023", "--output", str(alias)])
    assert result.exit_code != 0
    assert original.read_bytes() == alias.read_bytes() == b"immutable"


def test_cli_refuses_new_output_in_custom_source_cache(monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    called = []
    monkeypatch.setattr(store, "report", lambda *args: called.append(True))
    output = cache / "new.json"
    result = CliRunner().invoke(
        app, ["evidence", "glycemic-2021-2023", "--source", str(cache), "--output", str(output)]
    )
    assert result.exit_code != 0 and not called and not output.exists()


def test_cli_source_failure_creates_no_output(monkeypatch, tmp_path):
    def fail(*args):
        raise ValueError("NHANES source checksum mismatch")

    monkeypatch.setattr(store, "report", fail)
    output = tmp_path / "new.json"
    result = CliRunner().invoke(app, ["evidence", "glycemic-2021-2023", "--output", str(output)])
    assert result.exit_code != 0
    assert "checksum mismatch" in result.output and not output.exists()
