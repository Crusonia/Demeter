"""Detect source-change regressions in complete, validation-only model outputs."""

from copy import deepcopy
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def parity():
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        yield importlib.import_module("check_model_parity")
    finally:
        sys.path.remove(str(ROOT / "scripts"))


@pytest.fixture(scope="module")
def snapshot(parity):
    return parity.capture()


def reseal(parity, snapshot):
    snapshot["payload_sha256"] = parity.sha256(parity.canonical(snapshot["payload"]))
    return snapshot


@pytest.fixture(scope="module")
def compact_snapshot(parity, snapshot):
    # Shorten repeated arrays for deliberate mutation checks. Full scenario
    # coverage and the persisted roundtrip use the complete snapshot above.
    def compact(value):
        if isinstance(value, dict):
            return {key: compact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [compact(item) for item in value[:2]]
        return value

    result = deepcopy(snapshot)
    for group in ("simulations", "uncertainty"):
        result["payload"][group] = compact(snapshot["payload"][group])
    return reseal(parity, result)


def test_complete_engine_snapshot_covers_experiments_and_uncertainty(parity, snapshot):
    result = parity.compare_snapshots(snapshot, deepcopy(snapshot))
    assert result["passed"]
    assert not result["scientific_acceptance"]
    assert len(result["checks"]) == 8
    assert all(check["exactly_equal"] for check in result["checks"].values())
    for value in snapshot["payload"]["simulations"].values():
        assert value["validation_only"]
        assert len(value["cohorts"]) == 101
        assert value["diagnostics"]["history"]
        assert value["healthspan"]["restricted_cohort"]["by_initial_age"]
        assert "evidence_sha256" not in value["metadata"]
        assert "evidence_sha256" not in value["healthspan"]
        assert value["metadata"]["source_bundle_sha256"]
    for value in snapshot["payload"]["uncertainty"].values():
        assert value["draws"] == 4
        assert value["seed"] == 42
        assert value["parameter_draws"]
        assert value["annual_intervals"]


def test_persisted_reference_preserves_numpy_scalar_json_semantics(parity, snapshot, tmp_path):
    path = tmp_path / "reference.json"
    parity.write_new(path, snapshot)
    report = parity.compare_snapshots(parity.read_snapshot(path), snapshot)
    assert report["passed"]
    assert all(check["exactly_equal"] for check in report["checks"].values())


@pytest.mark.parametrize("target", ("annual", "cohort", "state_time", "hazard", "uncertainty"))
def test_changes_beyond_headline_metrics_fail_parity(parity, compact_snapshot, target):
    altered = deepcopy(compact_snapshot)
    model = altered["payload"]["simulations"]["baseline"]
    if target == "annual":
        model["annual"][1]["cumulative_deaths"] += 10
    elif target == "cohort":
        model["cohorts"][0]["healthy"] += 10
    elif target == "state_time":
        model["healthspan"]["restricted_cohort"]["state_person_years"]["healthy"] += 10
    elif target == "hazard":
        model["diagnostics"]["structure"]["evidence"]["h_to_ir_rate"]["value"] += 0.01
    else:
        altered["payload"]["uncertainty"]["reduce_upf_30"]["outcomes"]["life_expectancy"][
            "median"
        ] += 0.1
    report = parity.compare_snapshots(compact_snapshot, reseal(parity, altered))
    assert not report["passed"]
    assert sum(check["mismatch_count"] for check in report["checks"].values()) > 0


def test_provenance_is_reported_and_active_evidence_semantics_are_checked(parity, compact_snapshot):
    changed = deepcopy(compact_snapshot)
    changed["payload"]["provenance"]["git_commit"] = "a" * 40
    changed["payload"]["provenance"]["evidence_content_sha256"] = "b" * 64
    result = parity.compare_snapshots(compact_snapshot, reseal(parity, changed))
    assert result["passed"]
    assert result["reference_provenance"] != result["current_provenance"]
    changed["payload"]["simulations"]["baseline"]["metadata"]["status"] = "scientific"
    assert not parity.compare_snapshots(compact_snapshot, reseal(parity, changed))["passed"]


def test_normalization_does_not_mutate_or_hide_other_hash_paths(parity):
    original = {
        "metadata": {"evidence_sha256": "a", "source_bundle_sha256": "b"},
        "healthspan": {"evidence_sha256": "a", "value": 2.0},
        "nested": {"evidence_sha256": "retain me"},
    }
    normalized = parity.normalized(original, simulation=True)
    assert original["metadata"]["evidence_sha256"] == "a"
    assert normalized == {
        "metadata": {"source_bundle_sha256": "b"},
        "healthspan": {"value": 2.0},
        "nested": {"evidence_sha256": "retain me"},
    }


def test_capture_rejects_source_checkout_that_is_not_the_loaded_runtime(parity, tmp_path):
    with pytest.raises(ValueError, match="runtime is outside"):
        parity.capture(tmp_path)


def test_reference_integrity_inventory_and_contract_fail_closed(parity, compact_snapshot):
    damaged = deepcopy(compact_snapshot)
    damaged["payload"]["simulations"]["baseline"]["ending_population"] += 1
    with pytest.raises(ValueError, match="checksum"):
        parity.checked_payload(damaged)
    del damaged["payload"]["simulations"]["diet_dynamics"]
    with pytest.raises(ValueError, match="inventory"):
        parity.checked_payload(reseal(parity, damaged))
    damaged = deepcopy(compact_snapshot)
    damaged["payload"]["contract"]["absolute_tolerance"] = 1
    with pytest.raises(ValueError, match="contract"):
        parity.checked_payload(reseal(parity, damaged))


@pytest.mark.parametrize("encoded", ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}'))
def test_rejects_ambiguous_or_nonfinite_json(parity, tmp_path, encoded):
    path = tmp_path / "reference.json"
    path.write_text(encoded, encoding="utf-8")
    with pytest.raises(ValueError):
        parity.read_snapshot(path)


def test_output_is_never_overwritten_or_recomputed(parity, monkeypatch, tmp_path):
    destination = tmp_path / "reference.json"
    parity.write_new(destination, {"retained": True})
    with pytest.raises(FileExistsError):
        parity.write_new(destination, {"retained": False})
    monkeypatch.setattr(parity, "capture", lambda: pytest.fail("Existing output must stop capture"))
    with pytest.raises(SystemExit):
        parity.main(["snapshot", "--output", str(destination)])
    assert parity.read_snapshot(destination) == {"retained": True}


def test_failed_comparison_writes_diagnostics_and_exits_one(
    parity, compact_snapshot, monkeypatch, tmp_path
):
    reference, output = tmp_path / "reference.json", tmp_path / "comparison.json"
    parity.write_new(reference, compact_snapshot)
    changed = deepcopy(compact_snapshot)
    changed["payload"]["simulations"]["baseline"]["ending_population"] += 10
    monkeypatch.setattr(parity, "capture", lambda: reseal(parity, changed))
    assert parity.main(["compare", "--reference", str(reference), "--output", str(output)]) == 1
    report = parity.read_snapshot(output)
    assert not report["passed"]
    assert report["checks"]["simulations/baseline"]["first_mismatches"]


def test_small_float_roundoff_is_distinguished_from_exact_equality(parity, compact_snapshot):
    changed = deepcopy(compact_snapshot)
    changed["payload"]["simulations"]["baseline"]["ending_population"] += 1e-6
    report = parity.compare_snapshots(compact_snapshot, reseal(parity, changed))
    assert report["passed"]
    assert not report["checks"]["simulations/baseline"]["exactly_equal"]
