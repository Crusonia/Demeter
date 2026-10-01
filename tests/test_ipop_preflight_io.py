"""Synthetic source-preservation and CLI disclosure checks; no participant files."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.analysis import ipop_preflight_io as intake
from demeter.cli import app


def test_failed_cached_acquisition_cannot_reach_selected_record_parser(monkeypatch, tmp_path):
    monkeypatch.setattr(
        intake,
        "load_sources",
        lambda *args: {
            "passed": False,
            "sources": None,
            "provenance": {"failure_stage": "source_identity"},
            "receipt_saved": True,
        },
    )

    def forbidden_parse(*args):
        pytest.fail("Invalid cache must not reach a participant parser")

    monkeypatch.setattr("demeter.analysis.ipop_preflight._records", forbidden_parse)
    report = intake.audit_preflight(tmp_path)
    assert not report["source_audit"]["passed"]
    assert report["source_audit"]["failure_stage"] == "acquisition_receipts_or_cached_bytes"
    for section in (
        "source_structure",
        "numeric_token_coverage",
        "linkage",
        "unambiguous_linked_coverage",
        "context_coverage",
        "provenance",
    ):
        assert report[section] is None
    assert report["clinical_fit_performed"] is False
    assert report["engine_activation_allowed"] is False


def test_report_creation_is_exclusive_and_preserves_existing_bytes(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "clinical_tests.txt"
    source.write_bytes(b"PRIVATE_SYNTHETIC_SOURCE")
    with pytest.raises(ValueError, match="protected_or_existing_report_path"):
        intake.write_fresh_report({"passed": True}, source, raw)
    assert source.read_bytes() == b"PRIVATE_SYNTHETIC_SOURCE"
    output = tmp_path / "reports/audit.json"
    intake.write_fresh_report({"passed": True}, output, raw)
    first = output.read_bytes()
    assert json.loads(first) == {"passed": True}
    with pytest.raises(ValueError, match="protected_or_existing_report_path"):
        intake.write_fresh_report({"passed": False}, output, raw)
    assert output.read_bytes() == first


@pytest.mark.parametrize("directory", ["evidence", "docs/validation", "data/sources", "src"])
def test_report_cannot_create_unregistered_evidence_bytes(monkeypatch, tmp_path, directory):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / directory / "new.json"
    with pytest.raises(ValueError, match="protected_or_existing_report_path"):
        intake.write_fresh_report({"passed": True}, output, tmp_path / "raw")
    assert not output.exists()


def test_acquisition_cli_never_serializes_in_memory_source_bytes(monkeypatch, tmp_path):
    from demeter.data import ipop

    monkeypatch.setattr(
        ipop,
        "fetch_sources",
        lambda *args: {
            "passed": False,
            "receipt_saved": True,
            "provenance": {"failure_stage": "source_identity"},
            "sources": {"clinical": b"PRIVATE_SYNTHETIC_RECORD_BYTES"},
        },
    )
    result = CliRunner().invoke(app, ["data", "fetch-ipop", "--destination", str(tmp_path)])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["passed"] is False
    assert "PRIVATE_SYNTHETIC" not in result.output


def test_cli_exceptions_cannot_echo_source_or_path_details(monkeypatch, tmp_path):
    def failed_audit(*args):
        raise ValueError("PRIVATE_SYNTHETIC_FAILURE_DETAILS")

    monkeypatch.setattr(intake, "audit_preflight", failed_audit)
    output = tmp_path / "report.json"
    result = CliRunner().invoke(
        app, ["evidence", "ipop-preflight", "--raw", str(tmp_path), "--output", str(output)]
    )
    assert result.exit_code == 1
    assert "PRIVATE_SYNTHETIC" not in result.output
    assert "source evidence preserved" in result.output
    assert not output.exists()


def test_resolution_loop_cannot_expose_exception_detail(monkeypatch, tmp_path):
    def private_resolution_failure(*args, **kwargs):
        raise RuntimeError("PRIVATE_SYNTHETIC_RESOLUTION_DETAILS")

    monkeypatch.setattr(Path, "resolve", private_resolution_failure)
    with pytest.raises(ValueError, match="^protected_or_existing_report_path$"):
        intake.write_fresh_report({}, tmp_path / "report.json", tmp_path / "raw")


def test_failed_cached_crosswalk_acquisition_cannot_reach_record_parser(monkeypatch, tmp_path):
    monkeypatch.setattr(
        intake,
        "load_sources",
        lambda *args: {
            "passed": False,
            "sources": None,
            "provenance": {"failure_stage": "source_identity"},
            "receipt_saved": True,
        },
    )

    def forbidden_parse(*args):
        pytest.fail("Invalid cache must not reach a participant parser")

    monkeypatch.setattr("demeter.analysis.ipop_preflight._records", forbidden_parse)
    report = intake.audit_crosswalk(tmp_path)
    assert not report["source_audit"]["passed"]
    assert report["source_audit"]["failure_stage"] == "acquisition_receipts_or_cached_bytes"
    assert report["v1_result"] is None
    assert report["namespace_consistency"] is None
    assert report["clinical_fit_performed"] is False
    assert report["engine_activation_allowed"] is False


def test_crosswalk_frozen_selection_is_checked_before_cache_access(monkeypatch, tmp_path):
    def invalid_freeze(*args):
        raise ValueError("PRIVATE_SYNTHETIC_PROTOCOL_DETAIL")

    def forbidden_cache(*args):
        pytest.fail("Invalid frozen hypothesis must not read the source cache")

    monkeypatch.setattr(
        "demeter.analysis.ipop_crosswalk.load_frozen_crosswalk_protocol", invalid_freeze
    )
    monkeypatch.setattr(intake, "load_sources", forbidden_cache)
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "ipop-crosswalk-preflight",
            "--raw",
            str(tmp_path),
            "--output",
            str(tmp_path / "new.json"),
        ],
    )
    assert result.exit_code == 1
    assert "PRIVATE_SYNTHETIC" not in result.output
    assert not (tmp_path / "new.json").exists()
