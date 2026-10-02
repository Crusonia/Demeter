"""Synthetic exact replay and refusal tests; no participant records inspected."""

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def verifier():
    spec = importlib.util.spec_from_file_location(
        "synthetic_verify_nhanes_current", ROOT / "scripts/verify_nhanes_current.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def replay(verifier, monkeypatch, tmp_path):
    frozen = {
        "kind": verifier.DATASET,
        "model_role": "benchmark_only",
        "validation_only": True,
        **{key: False for key in verifier.GATES},
        "source_audit_passed": True,
        "source_audit_status": verifier.AUDIT_STATUS,
        "provenance": {
            "evidence_sha256": "a" * 64,
            "protocol_sha256": "c" * 64,
            "source_sha256": {"synthetic": "d" * 64},
            "implementation_sha256": {"synthetic.py": "e" * 64},
        },
        "domains": [{"estimate": 0.25, "n": 4}],
        "joint": {"covariance": [[0.001]]},
        "limitations": ["Synthetic fixture, no clinical evidence"],
    }
    path = tmp_path / "frozen.json"
    path.write_bytes(verifier.encoded(frozen))
    monkeypatch.setattr(verifier, "ARTIFACT_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    actual = copy.deepcopy(frozen)
    called = []

    def report(registry):
        called.append(True)
        return actual

    monkeypatch.setattr(verifier, "report", report)
    registry = SimpleNamespace(content_hash="a" * 64)
    return path, frozen, actual, registry, called


def seal(verifier, monkeypatch, path, value):
    path.write_bytes(verifier.encoded(value))
    monkeypatch.setattr(verifier, "ARTIFACT_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())


def test_exact_offline_replay(verifier, replay):
    path, _, _, registry, called = replay
    result = verifier.verify(registry, path)
    assert called == [True]
    assert result["passed"] is True
    assert result["network_used"] is False
    assert result["source_report_exactly_reproduced"] is True
    assert result["registry_fingerprint_changed"] is False
    assert all(result[key] is False for key in verifier.GATES)


def test_only_disclosed_registry_fingerprint_drift_allowed(verifier, replay):
    path, frozen, actual, registry, _ = replay
    actual["provenance"]["evidence_sha256"] = "b" * 64
    registry.content_hash = "b" * 64
    before = copy.deepcopy(actual)
    result = verifier.verify(registry, path)
    assert result["source_report_exactly_reproduced"] is False
    assert result["source_report_exactly_reproduced_excluding_registry_fingerprint"] is True
    assert result["excluded_paths"] == ["/provenance/evidence_sha256"]
    assert result["committed_registry_sha256"] == "a" * 64
    assert actual == before
    assert json.loads(path.read_bytes()) == frozen


@pytest.mark.parametrize("location", ["frozen", "actual"])
@pytest.mark.parametrize(
    "gate",
    [
        "direct_initialization_allowed",
        "clinical_fit_allowed",
        "engine_activation_allowed",
        "sampling_distribution_assumed",
        "scientific_release_ready",
    ],
)
@pytest.mark.parametrize("value", [True, 0, None])
def test_every_gate_must_be_explicit_false(verifier, replay, monkeypatch, location, gate, value):
    path, frozen, actual, registry, called = replay
    target = frozen if location == "frozen" else actual
    target[gate] = value
    if location == "frozen":
        seal(verifier, monkeypatch, path, frozen)
    with pytest.raises(ValueError, match="inactive gates"):
        verifier.verify(registry, path)
    if location == "frozen":
        assert called == []


@pytest.mark.parametrize("location", ["frozen", "actual"])
@pytest.mark.parametrize(
    "key,value",
    [
        ("model_role", "engine_input"),
        ("kind", "other"),
        ("validation_only", 1),
        ("source_audit_passed", False),
        ("source_audit_passed", 1),
        ("source_audit_status", "unverified"),
        ("provenance", {}),
    ],
)
def test_benchmark_and_source_audit_refusals(verifier, replay, monkeypatch, location, key, value):
    path, frozen, actual, registry, _ = replay
    target = frozen if location == "frozen" else actual
    target[key] = value
    if location == "frozen":
        seal(verifier, monkeypatch, path, frozen)
    with pytest.raises(ValueError, match="source-audited benchmark"):
        verifier.verify(registry, path)


@pytest.mark.parametrize("fingerprint", [None, "", "a" * 63, "g" * 64, 1])
def test_frozen_fingerprint_is_not_an_unchecked_exemption(
    verifier, replay, monkeypatch, fingerprint
):
    path, frozen, _, registry, called = replay
    frozen["provenance"]["evidence_sha256"] = fingerprint
    seal(verifier, monkeypatch, path, frozen)
    with pytest.raises(ValueError):
        verifier.verify(registry, path)
    assert called == []


def test_actual_fingerprint_must_identify_current_registry(verifier, replay):
    path, _, actual, registry, _ = replay
    actual["provenance"]["evidence_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="current registry"):
        verifier.verify(registry, path)


@pytest.mark.parametrize("mutation", ["point", "covariance", "source", "code", "protocol", "extra"])
def test_no_other_payload_change_is_excluded(verifier, replay, mutation):
    path, _, actual, registry, _ = replay
    if mutation == "point":
        actual["domains"][0]["estimate"] += 0.001
    elif mutation == "covariance":
        actual["joint"]["covariance"][0][0] += 0.001
    elif mutation in {"source", "code", "protocol"}:
        key = {
            "source": "source_sha256",
            "code": "implementation_sha256",
            "protocol": "protocol_sha256",
        }[mutation]
        actual["provenance"][key] = "f" * 64
    else:
        actual["provenance"]["additional"] = False
    with pytest.raises(ValueError, match="outside the registry fingerprint"):
        verifier.verify(registry, path)


def test_original_bytes_cannot_be_resealed_by_report_content(verifier, replay):
    path, _, _, registry, called = replay
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verifier.verify(registry, path)
    assert called == []


def test_unadmitted_artifact_refused_before_math(verifier, replay, monkeypatch):
    path, _, _, registry, called = replay
    monkeypatch.setattr(verifier, "ARTIFACT_SHA256", None)
    with pytest.raises(ValueError, match="immutably admitted"):
        verifier.verify(registry, path)
    assert called == []


@pytest.mark.parametrize("payload", [b'{"same":1,"same":2}', b'{"n":NaN}', b"[]", b"\xff"])
def test_bad_json_is_refused_before_math(verifier, replay, monkeypatch, payload):
    path, _, _, registry, called = replay
    path.write_bytes(payload)
    monkeypatch.setattr(verifier, "ARTIFACT_SHA256", hashlib.sha256(payload).hexdigest())
    with pytest.raises(ValueError):
        verifier.verify(registry, path)
    assert called == []


def test_parser_and_source_failures_are_propagated_without_success(verifier, replay, monkeypatch):
    path, _, _, registry, _ = replay

    def fail(registry):
        raise ValueError("source pin refused")

    monkeypatch.setattr(verifier, "report", fail)
    with pytest.raises(ValueError, match="source pin refused"):
        verifier.verify(registry, path)


def test_integer_float_storage_change_is_not_silently_equivalent(verifier, replay):
    path, _, actual, registry, _ = replay
    actual["domains"][0]["n"] = 4.0
    with pytest.raises(ValueError, match="outside the registry fingerprint"):
        verifier.verify(registry, path)


def test_cli_writes_only_new_proof_file(verifier, replay, monkeypatch, tmp_path, capsys):
    path, _, _, registry, _ = replay
    result = verifier.verify(registry, path)
    output = tmp_path / "proof.json"
    monkeypatch.setattr(verifier, "verify", lambda: result)
    monkeypatch.setattr(sys, "argv", ["verify_nhanes_current.py", "--output", str(output)])
    assert verifier.main() == 0
    assert json.loads(output.read_bytes()) == result
    assert json.loads(capsys.readouterr().out) == {
        "passed": True,
        "model_role": "benchmark_only",
        "network_used": False,
    }
    before = output.read_bytes()
    assert verifier.main() == 1
    assert output.read_bytes() == before
    assert "verification failed" in capsys.readouterr().out


def test_cli_failed_source_validation_exports_no_details_or_proof(
    verifier, monkeypatch, tmp_path, capsys
):
    output = tmp_path / "proof.json"

    def fail():
        raise ValueError("synthetic private participant path and assay")

    monkeypatch.setattr(verifier, "verify", fail)
    monkeypatch.setattr(sys, "argv", ["verify_nhanes_current.py", "--output", str(output)])
    assert verifier.main() == 1
    text = capsys.readouterr().out
    assert "private" not in text
    assert "assay" not in text
    assert not output.exists()
