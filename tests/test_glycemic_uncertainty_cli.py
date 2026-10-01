import copy
import json
from pathlib import Path
import runpy

import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry


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


def test_offline_cli_reproduces_committed_payload_except_current_registry_fingerprint(tmp_path):
    output = tmp_path / "joint.json"
    result = CliRunner().invoke(app, ["evidence", "glycemic-uncertainty", "--output", str(output)])
    assert result.exit_code == 0, result.output
    actual = output.read_bytes()
    expected = Path("docs/validation/joint-glycemic-uncertainty.json").read_bytes()
    report = json.loads(actual)
    committed = json.loads(expected)
    assert (
        report["provenance"]["evidence_sha256"]
        == EvidenceRegistry.from_yaml("evidence/parameters.yaml").content_hash
    )
    replay_payload = copy.deepcopy(report)
    committed_payload = copy.deepcopy(committed)
    replay_payload["provenance"].pop("evidence_sha256")
    committed_payload["provenance"].pop("evidence_sha256")
    if encoded(replay_payload) != encoded(committed_payload):
        pytest.fail(
            "Report payload differs outside /provenance/evidence_sha256: "
            f"actual SHA {digest(encoded(replay_payload))}, "
            f"expected SHA {digest(encoded(committed_payload))}"
        )
    assert actual == encoded(report)
    assert not report["scientific_release_ready"]
    assert not report["direct_initialization_allowed"]


@pytest.fixture
def replay_verifier(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    return runpy.run_path(str(root / "scripts/verify_joint_glycemic_uncertainty.py"))["assess"]


def _synthetic_replay(verifier, monkeypatch, *, actual_change=None, committed_change=None):
    """Metadata-replay fixtures only; no survey observations or model estimates."""
    current_hash = EvidenceRegistry.from_yaml("evidence/parameters.yaml").content_hash
    actual = {
        "provenance": {"evidence_sha256": current_hash, "protocol_sha256": "f" * 64},
        "joint": {"estimates": [0.25], "covariance": [[0.125]]},
        "scientific_release_ready": False,
        "direct_initialization_allowed": False,
    }
    committed = copy.deepcopy(actual)
    committed["provenance"]["evidence_sha256"] = "0" * 64
    if actual_change:
        actual_change(actual)
    if committed_change:
        committed_change(committed)
    monkeypatch.setitem(verifier.__globals__, "joint_report", lambda registry: actual)
    original = Path.read_bytes
    expected_path = Path("docs/validation/joint-glycemic-uncertainty.json")
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda path: encoded(committed) if path == expected_path else original(path),
    )
    return actual, committed, current_hash


def test_verifier_discloses_registry_only_replay_and_preserves_both_payloads(
    replay_verifier, monkeypatch
):
    actual, committed, current_hash = _synthetic_replay(replay_verifier, monkeypatch)
    before = copy.deepcopy((actual, committed))
    proof = replay_verifier()
    assert proof["passed"] is True
    assert proof["source_report_exactly_reproduced"] is False
    assert proof["source_report_exactly_reproduced_excluding_registry_fingerprint"] is True
    assert proof["excluded_paths"] == ["/provenance/evidence_sha256"]
    assert proof["current_registry_sha256"] == current_hash
    assert proof["committed_registry_sha256"] == "0" * 64
    assert proof["registry_fingerprint_changed"] is True
    assert (actual, committed) == before
    assert proof["direct_initialization_allowed"] is False


def test_verifier_reports_full_byte_equality_when_registry_is_unchanged(
    replay_verifier, monkeypatch
):
    current_hash = EvidenceRegistry.from_yaml("evidence/parameters.yaml").content_hash
    _synthetic_replay(
        replay_verifier,
        monkeypatch,
        committed_change=lambda report: report["provenance"].update(evidence_sha256=current_hash),
    )
    proof = replay_verifier()
    assert proof["source_report_exactly_reproduced"] is True
    assert proof["registry_fingerprint_changed"] is False


@pytest.mark.parametrize(
    "change",
    [
        lambda report: report["joint"]["estimates"].__setitem__(0, 0.250000000001),
        lambda report: report["joint"]["covariance"][0].__setitem__(0, 0.125000000001),
        lambda report: report["provenance"].update(protocol_sha256="e" * 64),
        lambda report: report.update(scientific_release_ready=True),
        lambda report: report.update(direct_initialization_allowed=0),
    ],
)
def test_verifier_rejects_every_other_payload_change(replay_verifier, monkeypatch, change):
    _synthetic_replay(replay_verifier, monkeypatch, actual_change=change)
    with pytest.raises(ValueError, match="outside the registry fingerprint"):
        replay_verifier()


def test_verifier_rejects_stale_current_registry_claim(replay_verifier, monkeypatch):
    _synthetic_replay(
        replay_verifier,
        monkeypatch,
        actual_change=lambda report: report["provenance"].update(evidence_sha256="0" * 64),
    )
    with pytest.raises(ValueError, match="current evidence registry"):
        replay_verifier()
