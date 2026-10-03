"""CLI refusal and aggregate replay; no clinical state inference or row export."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data import nhanes_assay_mapping as mapping
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

COMMAND = ["evidence", "assay-mapping"]
FROZEN = Path("docs/validation/nhanes-assay-mapping-report-v1.json")
FROZEN_SHA256 = "0cb7e82cbfc108c8cd0dc5bb77053ce84c902a8206fc57a7a99d8ebec04b0bc3"


@pytest.fixture
def summary_report(monkeypatch):
    report = {
        "kind": mapping.DATASET,
        "time_period": "Synthetic source labels",
        "model_role": "benchmark_only",
        "validation_only": True,
        **{name: False for name in mapping.GATES},
        "source_audit_passed": True,
        "counts": {"eligible_n": 4, "paired_no_n": 2, "discordant_paired_no_n": 1},
        "joint": {
            "coordinates": [{"domain": "synthetic", "membership": "synthetic"}],
            "estimates": [0.5],
            "covariance": [[0.125]],
        },
        "equivalence": [
            {
                "domain": "paired_no:20_plus:all",
                "n": 2,
                "discordant_n": 1,
                "status": "contradicted_in_observed_sample",
                "scalar": {"estimate": 0.5, "interval": None},
            }
        ],
        "provenance": {"protocol_sha256": "a" * 64, "source_manifest_sha256": "b" * 64},
    }
    monkeypatch.setattr(mapping, "report", lambda registry, source: report)
    return report


def test_compact_summary_preserves_interpretation_and_inactive_gates(summary_report):
    result = CliRunner().invoke(app, COMMAND)
    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    assert summary["kind"] == mapping.DATASET
    assert summary["joint_coordinates"] == 1
    assert summary["equivalence"] == summary_report["equivalence"]
    assert summary["model_role"] == "benchmark_only"
    assert summary["validation_only"] is True
    assert summary["scientific_release_ready"] is False
    assert summary["direct_initialization_allowed"] is False
    assert "literal No" in summary["interpretation"]
    assert "does not identify true clinical states" in summary["interpretation"]
    assert "covariance" not in result.output
    assert "joint" not in summary and "provenance" not in summary


def test_full_output_is_exclusive_and_retains_all_inactive_gates(summary_report, tmp_path):
    output = tmp_path / "aggregate.json"
    result = CliRunner().invoke(app, COMMAND + ["--output", str(output)])
    assert result.exit_code == 0, result.output
    before = output.read_bytes()
    assert before == encoded(summary_report)
    assert all(json.loads(before)[gate] is False for gate in mapping.GATES)
    result = CliRunner().invoke(app, COMMAND + ["--output", str(output)])
    assert result.exit_code != 0
    assert output.read_bytes() == before


@pytest.mark.parametrize("folder", ["data", "src", "docs", "evidence"])
def test_new_protected_output_refused_before_source_processing(monkeypatch, folder):
    monkeypatch.setattr(mapping, "report", lambda *args: pytest.fail("source processing started"))
    output = Path(folder) / "DO_NOT_CREATE_ASSAY_CLI_TEST.json"
    assert not output.exists()
    result = CliRunner().invoke(app, COMMAND + ["--output", str(output)])
    assert result.exit_code != 0 and "outside sources" in result.output
    assert not output.exists()


def test_existing_hardlink_output_refused_before_source_processing(monkeypatch, tmp_path):
    original = tmp_path / "immutable.json"
    original.write_bytes(b"immutable evidence bytes")
    alias = tmp_path / "alias.json"
    alias.hardlink_to(original)
    monkeypatch.setattr(mapping, "report", lambda *args: pytest.fail("source processing started"))
    result = CliRunner().invoke(app, COMMAND + ["--output", str(alias)])
    assert result.exit_code != 0
    assert original.read_bytes() == alias.read_bytes() == b"immutable evidence bytes"


def test_custom_source_output_refused_before_source_processing(monkeypatch, tmp_path):
    source = tmp_path / "custom-cache"
    source.mkdir()
    output = source / "new-aggregate.json"
    monkeypatch.setattr(mapping, "report", lambda *args: pytest.fail("source processing started"))
    result = CliRunner().invoke(app, COMMAND + ["--source", str(source), "--output", str(output)])
    assert result.exit_code != 0 and "outside sources" in result.output
    assert not output.exists()


def test_source_refusal_creates_no_output_or_output_directory(monkeypatch, tmp_path):
    def fail(*args):
        raise ValueError("NHANES paired assay source manifest checksum mismatch")

    monkeypatch.setattr(mapping, "report", fail)
    output = tmp_path / "not-created" / "aggregate.json"
    result = CliRunner().invoke(app, COMMAND + ["--output", str(output)])
    assert result.exit_code != 0 and "checksum mismatch" in result.output
    assert not output.parent.exists()


def test_real_offline_cli_exactly_replays_frozen_aggregate_except_registry_fingerprint(
    monkeypatch, tmp_path
):
    frozen_bytes = FROZEN.read_bytes()
    assert hashlib.sha256(frozen_bytes).hexdigest() == FROZEN_SHA256

    def no_network(*args, **kwargs):
        pytest.fail("Admitted assay replay must remain offline")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    output = tmp_path / "admitted-aggregate.json"
    result = CliRunner().invoke(app, COMMAND + ["--output", str(output)])
    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    actual = json.loads(output.read_bytes())
    expected = json.loads(frozen_bytes)
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    assert actual["provenance"]["evidence_sha256"] == registry.content_hash
    assert len(expected["provenance"]["evidence_sha256"]) == 64
    del actual["provenance"]["evidence_sha256"]
    del expected["provenance"]["evidence_sha256"]
    assert encoded(actual) == encoded(expected)  # No other field or numeric type is exempt.
    assert FROZEN.read_bytes() == frozen_bytes
    assert all(actual[gate] is False for gate in mapping.GATES)
    assert actual["source_audit_passed"] is True
    assert actual["model_role"] == "benchmark_only"
    assert len(actual["joint"]["coordinates"]) == summary["joint_coordinates"] == 204
    assert summary["equivalence"] == actual["equivalence"]
    assert "covariance" not in result.output
    assert "SEQN" not in output.read_text(encoding="utf-8")
