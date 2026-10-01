"""Synthetic replay metadata; no participant data or empirical fitting."""

import copy
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

from demeter.data.nhanes import encoded

CURRENT_HASH = "a" * 64
HISTORICAL_HASH = "b" * 64


@pytest.fixture
def verifier(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    return runpy.run_path(str(root / "scripts/verify_geelong_labels.py"))["assess"]


def _replay(verifier, monkeypatch, *, actual_change=None, committed_change=None, compact=False):
    actual = {
        "source_audit_passed": True,
        "provenance": {
            "registry_sha256": CURRENT_HASH,
            "protocol_sha256": "c" * 64,
            "implementation_sha256": "d" * 64,
        },
        "observed_labels": {"synthetic_counts": [1, 2, 3]},
        "working_fit": {"synthetic_log_likelihood": -1.25},
        "clinical_transition_fit_performed": False,
        "engine_activation_allowed": False,
        "scientific_release_ready": False,
    }
    committed = copy.deepcopy(actual)
    committed["provenance"]["registry_sha256"] = HISTORICAL_HASH
    if actual_change:
        actual_change(actual)
    if committed_change:
        committed_change(committed)
    globals_ = verifier.__globals__
    monkeypatch.setattr(
        globals_["EvidenceRegistry"],
        "from_yaml",
        lambda path: SimpleNamespace(content_hash=CURRENT_HASH),
    )
    monkeypatch.setitem(globals_, "audit_geelong_labels", lambda registry: actual)
    original = Path.read_bytes
    expected_path = globals_["ROOT"] / "docs/validation/issue-57-geelong-labels.json"
    expected_bytes = (
        json.dumps(committed, separators=(",", ":")).encode() if compact else encoded(committed)
    )
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda path: expected_bytes if path == expected_path else original(path),
    )
    return actual, committed


def test_registry_only_replay_discloses_scope_without_mutating_either_report(verifier, monkeypatch):
    actual, committed = _replay(verifier, monkeypatch)
    before = copy.deepcopy((actual, committed))
    proof = verifier()
    assert proof["passed"] is True
    assert proof["source_report_exactly_reproduced"] is False
    assert proof["source_report_exactly_reproduced_excluding_registry_fingerprint"] is True
    assert proof["excluded_paths"] == ["/provenance/registry_sha256"]
    assert proof["current_registry_sha256"] == CURRENT_HASH
    assert proof["committed_registry_sha256"] == HISTORICAL_HASH
    assert proof["registry_fingerprint_changed"] is True
    assert (actual, committed) == before
    assert proof["clinical_fit_allowed"] is False
    assert proof["engine_activation_allowed"] is False
    assert proof["scientific_release_ready"] is False


def test_identical_fingerprint_and_bytes_are_reported_as_full_reproduction(verifier, monkeypatch):
    _replay(
        verifier,
        monkeypatch,
        committed_change=lambda report: report["provenance"].update(registry_sha256=CURRENT_HASH),
    )
    proof = verifier()
    assert proof["source_report_exactly_reproduced"] is True
    assert proof["registry_fingerprint_changed"] is False


def test_equal_payload_with_different_formatting_is_not_full_byte_reproduction(
    verifier, monkeypatch
):
    _replay(
        verifier,
        monkeypatch,
        compact=True,
        committed_change=lambda report: report["provenance"].update(registry_sha256=CURRENT_HASH),
    )
    proof = verifier()
    assert proof["source_report_exactly_reproduced"] is False
    assert proof["source_report_exactly_reproduced_excluding_registry_fingerprint"] is True
    assert proof["registry_fingerprint_changed"] is False


def test_stale_current_registry_fingerprint_is_rejected(verifier, monkeypatch):
    _replay(
        verifier,
        monkeypatch,
        actual_change=lambda report: report["provenance"].update(registry_sha256=HISTORICAL_HASH),
    )
    with pytest.raises(ValueError, match="current evidence registry"):
        verifier()


@pytest.mark.parametrize(
    "change",
    [
        lambda report: report["observed_labels"]["synthetic_counts"].__setitem__(0, 2),
        lambda report: report["working_fit"].update(synthetic_log_likelihood=-1.250000000001),
        lambda report: report["provenance"].update(protocol_sha256="e" * 64),
        lambda report: report["provenance"].update(implementation_sha256="e" * 64),
        lambda report: report.update(clinical_transition_fit_performed=True),
        lambda report: report.update(scientific_release_ready=True),
        lambda report: report.update(engine_activation_allowed=0),
    ],
)
def test_every_other_numeric_provenance_or_scientific_gate_change_is_rejected(
    verifier, monkeypatch, change
):
    _replay(verifier, monkeypatch, actual_change=change)
    with pytest.raises(ValueError, match="outside the registry fingerprint"):
        verifier()


def test_failed_source_audit_cannot_become_successful_verification(verifier, monkeypatch):
    _replay(
        verifier,
        monkeypatch,
        actual_change=lambda report: report.update(source_audit_passed=False),
    )
    with pytest.raises(ValueError, match="source reproduction failed"):
        verifier()
