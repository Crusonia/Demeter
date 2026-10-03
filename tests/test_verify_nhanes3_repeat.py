"""Synthetic strict public-report replay tests; never inspect private study records."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def verifier():
    spec = importlib.util.spec_from_file_location(
        "synthetic_repeat_verifier", ROOT / "scripts/verify_nhanes3_repeat.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def replay(verifier, monkeypatch, tmp_path):
    frozen = {
        "kind": "nhanes3_repeat_fpg_nominal_diagnostic",
        "schema_version": 1,
        "source_vintage": "NHANES III 1988-1994; revised primary1A and repeat3A ASCII",
        "model_role": "benchmark_only",
        "validation_only": True,
        "source_audit_passed": True,
        "scientific_gates": dict.fromkeys(verifier.GATES, False),
        "diagnostic_status": "withheld",
        "ledger_conserved": True,
        "provenance": {
            "protocol_sha256": "c" * 64,
            "source_admission_sha256": "d" * 64,
            "code_admission_sha256": "e" * 64,
            "evidence_sha256": "a" * 64,
            "source_sha256": dict.fromkeys(("LAB", "ADULT", "LABSE"), "f" * 64),
            "implementation_sha256": dict.fromkeys(verifier.IMPLEMENTATIONS, "b" * 64),
        },
    }
    path = tmp_path / "frozen.json"
    path.write_bytes(verifier.encoded(frozen))
    monkeypatch.setattr(verifier, "ARTIFACT_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    actual = copy.deepcopy(frozen)
    calls = []

    def report(registry):
        calls.append(True)
        return actual

    monkeypatch.setattr(verifier, "report", report)
    return path, frozen, actual, SimpleNamespace(content_hash="a" * 64), calls


def seal(verifier, monkeypatch, path, value):
    path.write_bytes(verifier.encoded(value))
    monkeypatch.setattr(verifier, "ARTIFACT_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())


def test_exact_offline_public_replay(verifier, replay):
    path, _, _, registry, calls = replay
    result = verifier.verify(registry, path)
    assert calls == [True]
    assert result["source_report_exactly_reproduced"] is True
    assert result["network_used"] is False
    assert result["scientific_gates"] == dict.fromkeys(verifier.GATES, False)
    assert "diagnostic_status" not in result


def test_only_current_registry_hash_difference_allowed_without_mutating_payloads(verifier, replay):
    path, frozen, actual, registry, _ = replay
    actual["provenance"]["evidence_sha256"] = registry.content_hash = "b" * 64
    before = copy.deepcopy(actual)
    result = verifier.verify(registry, path)
    assert result["source_report_exactly_reproduced"] is False
    assert result["excluded_paths"] == ["/provenance/evidence_sha256"]
    assert actual == before and json.loads(path.read_bytes()) == frozen


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
@pytest.mark.parametrize("bad", [True, 0, None])
def test_nested_gates_require_explicit_false(verifier, replay, monkeypatch, location, gate, bad):
    path, frozen, actual, registry, calls = replay
    target = frozen if location == "frozen" else actual
    target["scientific_gates"][gate] = bad
    if location == "frozen":
        seal(verifier, monkeypatch, path, frozen)
    with pytest.raises(ValueError, match="coarse public schema"):
        verifier.verify(registry, path)
    if location == "frozen":
        assert not calls


@pytest.mark.parametrize(
    "key,bad",
    [
        ("kind", "clinical_fit"),
        ("schema_version", True),
        ("model_role", "engine_input"),
        ("validation_only", 1),
        ("source_audit_passed", 1),
        ("ledger_conserved", False),
        ("diagnostic_status", "empty_positive_support"),
        ("scientific_gates", {}),
        ("source_vintage", "modern NHANES"),
    ],
)
def test_scope_refused_before_replay(verifier, replay, monkeypatch, key, bad):
    path, frozen, _, registry, calls = replay
    frozen[key] = bad
    seal(verifier, monkeypatch, path, frozen)
    with pytest.raises(ValueError):
        verifier.verify(registry, path)
    assert not calls


@pytest.mark.parametrize("location", ["top", "provenance", "source", "implementation"])
def test_private_or_unregistered_fields_refused_even_if_resealed(
    verifier, replay, monkeypatch, location
):
    path, frozen, _, registry, calls = replay
    target = {
        "top": frozen,
        "provenance": frozen["provenance"],
        "source": frozen["provenance"]["source_sha256"],
        "implementation": frozen["provenance"]["implementation_sha256"],
    }[location]
    target["unapproved_private_field"] = "not a public checksum"
    seal(verifier, monkeypatch, path, frozen)
    with pytest.raises(ValueError):
        verifier.verify(registry, path)
    assert not calls


@pytest.mark.parametrize("bad", [None, "", "a" * 63, "g" * 64, 1])
def test_frozen_registry_exemption_is_validated(verifier, replay, monkeypatch, bad):
    path, frozen, _, registry, calls = replay
    frozen["provenance"]["evidence_sha256"] = bad
    seal(verifier, monkeypatch, path, frozen)
    with pytest.raises(ValueError):
        verifier.verify(registry, path)
    assert not calls


def test_actual_registry_fingerprint_must_equal_current_registry(verifier, replay):
    path, _, actual, registry, _ = replay
    actual["provenance"]["evidence_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="current registry"):
        verifier.verify(registry, path)


@pytest.mark.parametrize("mutation", ["status", "source", "code", "protocol", "admission"])
def test_other_semantics_never_excluded(verifier, replay, mutation):
    path, _, actual, registry, _ = replay
    if mutation == "status":
        actual["diagnostic_status"] = "contradicted"
    elif mutation == "source":
        actual["provenance"]["source_sha256"]["LAB"] = "a" * 64
    elif mutation == "code":
        actual["provenance"]["implementation_sha256"]["src/demeter/schema.py"] = "a" * 64
    else:
        key = "protocol_sha256" if mutation == "protocol" else "source_admission_sha256"
        actual["provenance"][key] = "a" * 64
    with pytest.raises(ValueError, match="outside the registry fingerprint"):
        verifier.verify(registry, path)


def test_altered_original_bytes_not_resealed_by_report_content(verifier, replay):
    path, _, _, registry, calls = replay
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        verifier.verify(registry, path)
    assert not calls


@pytest.mark.parametrize("raw", [b'{"same":1,"same":2}', b'{"value":NaN}', b"[]", b"\xff"])
def test_bad_json_refused_before_replay(verifier, replay, monkeypatch, raw):
    path, _, _, registry, calls = replay
    path.write_bytes(raw)
    monkeypatch.setattr(verifier, "ARTIFACT_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):
        verifier.verify(registry, path)
    assert not calls


def test_cli_success_exclusive_output_and_failure_no_private_details(
    verifier, replay, monkeypatch, tmp_path, capsys
):
    path, _, _, registry, _ = replay
    result = verifier.verify(registry, path)
    monkeypatch.setattr(verifier, "verify", lambda: result)
    output = tmp_path / "proof.json"
    assert verifier.main(["--output", str(output)]) == 0
    before = output.read_bytes()
    assert json.loads(before) == result
    assert verifier.main(["--output", str(output)]) == 1
    assert output.read_bytes() == before

    def fail():
        raise ValueError("private study key and assay value")

    monkeypatch.setattr(verifier, "verify", fail)
    failure_output = tmp_path / "failed.json"
    assert verifier.main(["--output", str(failure_output)]) == 1
    assert not failure_output.exists()
    assert "private study" not in capsys.readouterr().out


@pytest.mark.parametrize("folder", ["data", "src", "docs", "evidence"])
def test_protected_output_precedes_replay(verifier, monkeypatch, tmp_path, folder):
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "verify", lambda: pytest.fail("unexpected replay"))
    output = tmp_path / folder / "new.json"
    assert verifier.main(["--output", str(output)]) == 1
    assert not output.parent.exists()


def test_output_race_cannot_overwrite_after_preflight(verifier, replay, monkeypatch, tmp_path):
    path, _, _, registry, _ = replay
    result = verifier.verify(registry, path)
    output = tmp_path / "proof.json"

    def replay_race():
        output.write_bytes(b"already written independently")
        return result

    monkeypatch.setattr(verifier, "verify", replay_race)
    assert verifier.main(["--output", str(output)]) == 1
    assert output.read_bytes() == b"already written independently"


def test_admitted_frozen_report_pin(verifier):
    assert (
        verifier.ARTIFACT_SHA256
        == "1b583ad4ce3a211f1af0518e4be7b67d11652d242ec5e1ed8a428c3029dfbc7f"
    )
    assert verifier.ARTIFACT.name == "nhanes3-repeat-fpg-report-v1.json"
