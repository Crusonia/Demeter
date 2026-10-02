import copy
import json
from pathlib import Path

import pytest

from demeter.analysis.pathway_compatibility import (
    DATASET,
    REFERENCES,
    analyze_compatibility,
    audit_compatibility,
)
from demeter.schema import EvidenceRegistry


def fixture():
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    return registry, copy.deepcopy(registry.datasets[DATASET]["analysis"])


def test_matched_annual_entries_do_not_select_transition_mechanism():
    registry, analysis = fixture()
    result = analyze_compatibility(registry, analysis)
    cases = result["endpoint_witness"]["cases"]
    tolerance = analysis["absolute_tolerance"]
    analytic = result["endpoint_witness"]["analytic_one_year_t2d_entries"]
    for case in cases.values():
        assert case["years"][0]["new_t2d_entries"] == pytest.approx(analytic, abs=tolerance, rel=0)
        for year in case["years"]:
            assert sum(year["stocks"].values()) == pytest.approx(
                analysis["population_scale"], abs=tolerance, rel=0
            )
            assert all(value >= 0 for value in year["stocks"].values())
            assert all(value >= 0 for value in year["transition_flows"].values())
    assert cases["A"]["hazards_per_year"] != cases["B"]["hazards_per_year"]
    assert cases["A"]["hazards_per_year"] != cases["C"]["hazards_per_year"]
    for key in ("B", "C"):
        assert cases[key]["years"][0]["stocks"]["insulin_resistant"] != pytest.approx(
            cases["A"]["years"][0]["stocks"]["insulin_resistant"], abs=tolerance, rel=0
        )
        assert cases[key]["years"][1]["new_t2d_entries"] != pytest.approx(
            cases["A"]["years"][1]["new_t2d_entries"], abs=tolerance, rel=0
        )
    assert result["initial_survivor_stocks"]["t2d"] == 0
    assert result["checks"]["stocks_and_flows_conserved_and_nonnegative"]
    assert result["checks"]["analytic_one_year_entries_match_operator"]


def test_dose_and_lag_have_distinct_synthetic_witnesses():
    registry, analysis = fixture()
    result = analyze_compatibility(registry, analysis)
    cases = result["dose_lag_witness"]["cases"]
    reference, dose, lag = (
        cases[key] for key in ("reference", "rescaled_dose_coefficient", "rescaled_lag_coefficient")
    )
    tolerance = analysis["absolute_tolerance"]
    assert reference["beta"] != dose["beta"]
    assert reference["dose_delta"] != dose["dose_delta"]
    assert reference["lag_years"] != lag["lag_years"]
    for first, second in zip(reference["years"], dose["years"], strict=True):
        assert first["log_response"] == pytest.approx(second["log_response"], abs=tolerance, rel=0)
        assert first["multiplier"] == pytest.approx(second["multiplier"], abs=tolerance, rel=0)
    assert reference["years"][0]["log_response"] == pytest.approx(
        lag["years"][0]["log_response"], abs=tolerance, rel=0
    )
    assert reference["years"][1]["log_response"] != pytest.approx(
        lag["years"][1]["log_response"], abs=tolerance, rel=0
    )
    assert result["checks"]["relax_matches_closed_form"]


def test_structural_nulls_are_software_hypotheses_and_no_cox_fit_is_claimed():
    registry, _ = fixture()
    report = audit_compatibility(registry)
    result = report["results"]
    assert (
        result["endpoint_witness"]["reference"]
        == result["endpoint_witness"]["identical_hazard_null"]
    )
    assert all(
        row["multiplier"] == 1
        for row in result["dose_lag_witness"]["cases"]["zero_response_null"]["years"]
    )
    assert all(result["checks"].values())
    assert result["software_witnesses_passed"]
    assert result["classification"] == "validation_only_synthetic_witnesses"
    assert not result["clinical_effect_used"]
    assert not result["clinical_fit_performed"]
    assert not result["formal_cox_identifiability_result"]
    assert not report["scientific_release_ready"]
    assert not report["provenance"]["clinical_hr_used_in_witnesses"]
    assert not report["support_decision"]["engine_activation_permitted"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("counterexample_scale", 1),
        ("counterexample_scale", float("inf")),
        ("counterexample_scale", 1e308),
        ("population_scale", 0),
        ("absolute_tolerance", -1),
        ("relative_tolerance", 0.1),
        ("relative_upf_fixture", 1),
        ("relative_upf_fixture", float("nan")),
        ("diagnostic_years", [True, 2]),
        ("status", "observed"),
    ],
)
def test_invalid_or_unlabeled_synthetic_inputs_fail(key, value):
    registry, analysis = fixture()
    analysis[key] = value
    with pytest.raises(ValueError):
        analyze_compatibility(registry, analysis)


def test_reference_parameter_drift_fails_before_calculation(monkeypatch):
    registry, _ = fixture()
    registry.parameters[REFERENCES[0]].value *= 2
    monkeypatch.setattr(
        "demeter.analysis.pathway_compatibility.analyze_compatibility",
        lambda *a: pytest.fail("Unverified reference used in witness calculation"),
    )
    with pytest.raises(ValueError, match="reference/helper"):
        audit_compatibility(registry)


def test_helper_byte_drift_fails_before_calculation(monkeypatch):
    registry, _ = fixture()
    original = Path.read_bytes

    def changed(path):
        value = original(path)
        return value + b"changed" if path.as_posix().endswith("health/transitions.py") else value

    monkeypatch.setattr(Path, "read_bytes", changed)
    monkeypatch.setattr(
        "demeter.analysis.pathway_compatibility.analyze_compatibility",
        lambda *a: pytest.fail("Unverified helper used in witness calculation"),
    )
    with pytest.raises(ValueError, match="reference/helper"):
        audit_compatibility(registry)


@pytest.mark.parametrize("field", ["analysis", "protocol_sha256", "amendment_sha256"])
def test_definition_drift_fails_before_calculation(field, monkeypatch):
    registry, _ = fixture()
    if field == "analysis":
        registry.datasets[DATASET][field]["counterexample_scale"] = 3
    else:
        registry.datasets[DATASET][field] = "0" * 64
    monkeypatch.setattr(
        "demeter.analysis.pathway_compatibility.analyze_compatibility",
        lambda *a: pytest.fail("Unverified protocol used in witness calculation"),
    )
    with pytest.raises(ValueError, match="protocol/registry"):
        audit_compatibility(registry)


def test_audit_does_not_use_unrelated_clinical_parameters_or_mutate_registry():
    registry, analysis = fixture()
    before = registry.model_dump_json()
    report = audit_compatibility(registry)
    assert registry.model_dump_json() == before
    modified = copy.deepcopy(registry)
    changed = 0
    for key, parameter in modified.parameters.items():
        if key not in REFERENCES and parameter.model_role == "benchmark_only" and parameter.value:
            altered = parameter.value / analysis["counterexample_scale"]
            if parameter.lower_bound is not None and altered < parameter.lower_bound:
                continue
            parameter.value = altered
            parameter.notes = (
                "Deliberately altered unrelated benchmark in a synthetic software test"
            )
            changed += 1
            break
    assert changed
    assert audit_compatibility(modified)["results"] == report["results"]


def test_unpinned_reference_status_cannot_be_promoted():
    registry, analysis = fixture()
    registry.parameters[REFERENCES[0]].status = "observed"
    with pytest.raises(ValueError, match="synthetic/E"):
        analyze_compatibility(registry, analysis)


def test_metadata_pins_expose_all_seven_reference_definitions():
    registry, _ = fixture()
    report = audit_compatibility(registry)
    spec = registry.datasets[DATASET]
    protocol = json.loads(Path(spec["protocol_path"]).read_bytes())
    assert report["analysis_id"] == protocol["analysis_id"]
    assert set(report["provenance"]["reference_definition_sha256"]) == set(REFERENCES)
    assert set(report["provenance"]["helper_sha256"]) == {
        "src/demeter/health/transitions.py",
        "src/demeter/nutrition/response.py",
    }


def test_numerical_repair_preserves_original_frozen_witness_results():
    registry, _ = fixture()
    current = audit_compatibility(registry)
    original = json.loads(Path("docs/validation/issue-58-pathway-compatibility.json").read_bytes())
    replay = json.loads(Path("docs/validation/reus-compatibility-numerics-v2-replay.json").read_bytes())
    assert current["results"] == original["results"] == replay["replayed_report"]["results"]
    assert current["provenance"]["numerical_amendment"] == 2
    assert current["provenance"]["parent_amendment_sha256"] == (
        "4aac541bce132a6aeb59962f49779df8c3d1eecf25f67d5c8db99183dda8084e"
    )
    assert replay["original_results_exactly_reproduced"]
    assert not replay["scientific_acceptance"]


def test_changed_numerical_parent_fails_before_calculation(monkeypatch):
    registry, _ = fixture()
    original = Path.read_bytes

    def changed(path):
        value = original(path)
        return value + b" " if path.name == "reus-diabetes-amendment-1.json" else value

    monkeypatch.setattr(Path, "read_bytes", changed)
    monkeypatch.setattr(
        "demeter.analysis.pathway_compatibility.analyze_compatibility",
        lambda *args: pytest.fail("Unverified numerical amendment parent used"),
    )
    with pytest.raises(ValueError, match="numerical amendment parent"):
        audit_compatibility(registry)
