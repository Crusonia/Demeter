"""Offline v2 verifier fixtures, never scientific artifacts or empirical fits.

These tests deliberately forge a synthetic v2 empirical envelope from the
preserved PUBLIC failed-v1 aggregate, keeping its original bytes/source/selection
pins immutable. Available-model fixtures also forge convergence metadata around
toy-path likelihoods solely to exercise semantic audit branches. They do not
establish any fitted point, clinical acceptance, or actual participant replay.
The positive public-v2 control audits only the completed aggregate. No raw/cache
reads, acquisition, or empirical optimization occur.
"""

import copy
import hashlib
import json
from pathlib import Path
from runpy import run_path
import sys

import pytest
import yaml

from demeter.analysis import ipop_a1c as a1c
from demeter.analysis import laboratory_panel as lab
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_ipop_a1c_working_fit.py"
ASSESS = run_path(str(SCRIPT))["assess"]
V1_FIXTURES = run_path(str(ROOT / "tests/test_ipop_a1c_verifier.py"))
TOY_PROFILES = V1_FIXTURES["_toy_profiles"]
PLATFORM_ROUNDOFF = V1_FIXTURES["_platform_transcendental_roundoff"]
METHOD = "exact_box_quadratic_v2"
RESULT_PATH = "docs/validation/ipop-a1c-working-result-v2.json"
PUBLIC_FILES = (
    "docs/validation/ipop-a1c-working-fit-protocol-v1.json",
    "docs/validation/ipop-a1c-numerical-amendment-v1.json",
    "docs/validation/ipop-a1c-numerical-amendment-v2.json",
    "docs/validation/ipop-preflight-namespace-result-v2.json",
    "docs/validation/ipop-a1c-working-result-v1.json",
)


@pytest.fixture
def synthetic_report(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline synthetic audit must not acquire, parse, replay, or optimize data")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr(a1c, "analyze_cache", forbidden)
    monkeypatch.setattr(a1c, "analyze_bytes", forbidden)
    monkeypatch.setattr(lab, "fit_ctmc", forbidden)
    for relative in PUBLIC_FILES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    original = (tmp_path / PUBLIC_FILES[-1]).read_bytes()
    assert hashlib.sha256(original).hexdigest() == a1c.V1_RESULT_SHA256
    report = json.loads(original)
    # This deliberately forged envelope exists only in test temporary storage.
    report["analysis_id"] = "ipop_a1c_conditional_working_fit_v2"
    report["synthetic_verifier_fixture_only"] = True
    report["provenance"].update(
        numerical_method=METHOD,
        numerical_amendment_sha256=a1c.NUMERICAL_V2_SHA256,
        prior_empirical_result_sha256=a1c.V1_RESULT_SHA256,
        statistical_selection_changed=False,
    )
    for name in ("adjacent", "unrestricted"):
        assert report["models"][name]["rates"] is None
        report["models"][name]["numerical_method"] = METHOD
    report["joint_uncertainty"]["numerical_method"] = METHOD
    return report


def _register(root, report):
    registry = yaml.safe_load((ROOT / "evidence/parameters.yaml").read_text(encoding="utf-8"))
    spec = registry["datasets"]["ipop_a1c_working_fit_v2"]
    raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    (root / RESULT_PATH).write_bytes(raw)
    primary = report["models"]["adjacent"]["rates"]
    spec["working_rate_parameters"]["value"] = primary
    spec["working_rate_parameters"]["estimation_status"] = (
        "conditional_analysis_completed_primary_estimate_unresolved"
        if primary is None
        else "conditional_working_fit_completed_clinical_use_unresolved"
    )
    # Refresh checksum and parameter bindings, replacing any future registration
    # without opening its empirical v2 result. Reject on semantic drift alone.
    spec["result"] = {
        "path": RESULT_PATH,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "estimated_parameters": {
            "primary_rates_per_source_day": primary,
            "general_rates_per_source_day": report["models"]["unrestricted"]["rates"],
            "iid_followup_band_probabilities": report["models"]["iid"]["probabilities"],
        },
    }
    (root / "evidence").mkdir(exist_ok=True)
    (root / "evidence/parameters.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    return root


def _forge_available_model(report, name):
    """Deliberately forged semantic branch fixture, never an optimizer result."""
    paths = (lab.PanelPath((0, 20, 100), (0, 1, 2)), lab.PanelPath((0, 50), (1, 0)))
    rates = [0.002, 0.003, 0.004, 0.005] + ([0.001, 0.0015] if name == "unrestricted" else [])
    likelihood = {
        "value": lab.conditional_log_likelihood(paths, rates, name, probability_tolerance=1e-10),
        "status": "finite",
    }
    model = report["models"][name]
    model.update(
        fit_performed=True,
        rates=rates,
        failure=None,
        log_likelihood=likelihood,
        identification={
            "available": False,
            "global_identification_established": False,
            "practical_identification_established": False,
            "observation_to_clinical_state_compatibility_established": False,
        },
        optimizer_convergence_is_identification=False,
    )
    for row in model["multistarts"]:
        row["converged"] = False
    model["multistarts"][0].update(
        converged=True,
        rates=list(rates),
        log_likelihood=copy.deepcopy(likelihood),
        direct_likelihood_gradient_verified=True,
        projected_gradient_norm=0.0,
    )
    report["profiles"][name] = TOY_PROFILES(paths, rates, name, likelihood, numerical_method=METHOD)
    report["internal_evaluation"]["scores"][name] = lab.score_predictions(
        paths, model, probability_tolerance=1e-10
    )


def test_synthetic_failed_v2_envelope_passes_offline(tmp_path, synthetic_report):
    proof = ASSESS(_register(tmp_path, synthetic_report), numerical_method=METHOD)
    assert proof["passed"] is True
    assert proof["report_sha256"] != a1c.V1_RESULT_SHA256
    assert proof["numerical_method"] == METHOD
    assert proof["numerical_amendment_sha256"] == a1c.NUMERICAL_V2_SHA256
    assert proof["prior_empirical_result_sha256"] == a1c.V1_RESULT_SHA256
    assert proof["statistical_selection_changed"] is False
    assert proof["actual_source_replay"] is None
    assert all(check["fit_available"] is False for check in proof["fit_checks"].values())
    assert proof["clinical_acceptance_established"] is False
    assert proof["engine_activation_allowed"] is False


@pytest.mark.parametrize("name", ("adjacent", "unrestricted"))
def test_synthetic_available_v2_semantic_branch_passes(tmp_path, synthetic_report, name):
    _forge_available_model(synthetic_report, name)
    proof = ASSESS(_register(tmp_path, synthetic_report), numerical_method=METHOD)
    assert proof["fit_checks"][name]["fit_available"] is True
    assert proof["fit_checks"][name]["generator_and_kernel_conserve_mass"] is True
    assert proof["fit_checks"][name]["profile_count"] == len(lab.EDGES[name])
    assert proof["actual_source_replay"] is None
    assert proof["clinical_acceptance_established"] is False


@pytest.mark.parametrize(
    "attack,error",
    (
        ("top_scope", "registry_contract"),
        ("model_scope", "Nested working analysis"),
        ("bootstrap_scope", "Nested working analysis"),
        ("evaluation_scope", "Nested working analysis"),
        ("controls", "Numerical settings"),
        ("covariance", "Invalid joint covariance"),
        ("method", "registry_contract"),
        ("joint_method", "registry_contract"),
        ("model_method", "registry_contract"),
        ("prior_binding", "registry_contract"),
        ("selection_claim", "registry_contract"),
        ("source_pins", "registry_contract"),
        ("selection", "registry_contract"),
    ),
)
def test_rehashed_v2_scope_controls_and_bindings_reject(tmp_path, synthetic_report, attack, error):
    report = synthetic_report
    if attack == "top_scope":
        report["clinical_fit_performed"] = True
    elif attack == "model_scope":
        report["models"]["adjacent"]["engine_activation_allowed"] = True
    elif attack == "bootstrap_scope":
        report["joint_uncertainty"]["clinical_fit_performed"] = True
    elif attack == "evaluation_scope":
        report["internal_evaluation"]["clinical_acceptance_tolerance"] = 0.1
    elif attack == "controls":
        report["models"]["adjacent"]["settings"]["optimizer_gtol"] = 0.001
    elif attack == "covariance":
        summary = report["joint_uncertainty"]["joint_rate_summary"]
        assert summary["available"] is True
        summary["covariance"] = [[1e-20 * int(i == j) for j in range(4)] for i in range(4)]
        summary["covariance"][0][0] = -1e-20
    elif attack == "method":
        report["provenance"]["numerical_method"] = "v1"
    elif attack == "joint_method":
        del report["joint_uncertainty"]["numerical_method"]
    elif attack == "model_method":
        report["models"]["unrestricted"]["numerical_method"] = "v1"
    elif attack == "prior_binding":
        report["provenance"]["prior_empirical_result_sha256"] = "0" * 64
    elif attack == "selection_claim":
        report["provenance"]["statistical_selection_changed"] = True
    elif attack == "source_pins":
        report["provenance"]["source_bytes"]["clinical"]["sha256"] = "0" * 64
    else:
        report["selection"]["denominator_admitted_rows"] += 1
    with pytest.raises(ValueError, match=error):
        ASSESS(_register(tmp_path, report), numerical_method=METHOD)


@pytest.mark.parametrize(
    "attack,error",
    (
        ("gradient", "gradient"),
        ("profile", "profile interval"),
        ("profile_method", "registry_contract"),
    ),
)
def test_rehashed_available_v2_gradient_and_profile_claims_reject(
    tmp_path, synthetic_report, attack, error
):
    _forge_available_model(synthetic_report, "adjacent")
    if attack == "gradient":
        synthetic_report["models"]["adjacent"]["multistarts"][0]["projected_gradient_norm"] = 1.0
    elif attack == "profile":
        synthetic_report["profiles"]["adjacent"][0]["finite_confidence_interval"] = [0.0, 1.0]
    else:
        synthetic_report["profiles"]["adjacent"][0]["numerical_method"] = "v1"
    with pytest.raises(ValueError, match=error):
        ASSESS(_register(tmp_path, synthetic_report), numerical_method=METHOD)


def test_default_v1_proof_matches_explicit_selection_and_keeps_schema(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline default audit must not replay participant data")

    monkeypatch.setattr(a1c, "analyze_cache", forbidden)
    proof = ASSESS()
    assert proof == ASSESS(numerical_method="v1")
    assert "numerical_method" not in proof
    assert proof["numerical_amendment_sha256"] == a1c.NUMERICAL_PROTOCOL_SHA256
    assert proof["report_sha256"] == a1c.V1_RESULT_SHA256


@pytest.mark.parametrize("ulps", (0, 1, 2))
def test_completed_public_v2_aggregate_passes_without_source_replay(monkeypatch, ulps):
    def forbidden(*args, **kwargs):
        pytest.fail("Public aggregate audit must not acquire or replay participant data")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr(a1c, "analyze_cache", forbidden)
    PLATFORM_ROUNDOFF(monkeypatch, ulps)
    proof = ASSESS(numerical_method=METHOD)
    assert proof["passed"] is True
    assert all(check["fit_available"] is True for check in proof["fit_checks"].values())
    assert proof["actual_source_replay"] is None
    assert proof["clinical_acceptance_established"] is False
    assert proof["engine_activation_allowed"] is False


def test_optional_raw_dispatch_is_mocked_and_selects_v2(tmp_path, synthetic_report, monkeypatch):
    root = _register(tmp_path, synthetic_report)
    calls = []

    def fake_replay(raw, *, progress, numerical_method):
        calls.append((raw, numerical_method))
        return copy.deepcopy(synthetic_report)

    monkeypatch.setattr(a1c, "analyze_cache", fake_replay)
    unused = tmp_path / "synthetic_unused_cache"
    proof = ASSESS(root, raw=unused, numerical_method=METHOD)
    assert calls == [(unused, METHOD)]
    assert proof["actual_source_replay"]["remaining_payload_exactly_equal"] is True
    assert not unused.exists()


def test_cli_selects_v2_using_only_temporary_synthetic_aggregate(
    tmp_path, synthetic_report, monkeypatch, capsys
):
    _register(tmp_path, synthetic_report)
    registry = EvidenceRegistry.from_yaml(tmp_path / "evidence/parameters.yaml")
    monkeypatch.setattr(EvidenceRegistry, "from_yaml", lambda *args: registry)
    original_read = Path.read_bytes

    def supplied(path):
        if path == ROOT / RESULT_PATH:
            return original_read(tmp_path / RESULT_PATH)
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", supplied)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--numerical-method", METHOD])
    run_path(str(SCRIPT), run_name="__main__")
    proof = json.loads(capsys.readouterr().out)
    assert proof["numerical_method"] == METHOD
    assert (
        proof["report_sha256"] == registry.datasets["ipop_a1c_working_fit_v2"]["result"]["sha256"]
    )
    assert proof["actual_source_replay"] is None


@pytest.mark.parametrize("attack", ("seed", "quantiles", "failures", "resolution", "attempts"))
def test_rehashed_v2_bootstrap_controls_and_closure_reject(tmp_path, synthetic_report, attack):
    joint = synthetic_report["joint_uncertainty"]
    if attack == "seed":
        joint["seed"] = 1
    elif attack == "quantiles":
        joint["joint_rate_summary"]["quantile_levels"] = [0.1, 0.5, 0.9]
    elif attack == "failures":
        joint["dispositions"]["failed_primary_fits"] = 0
    elif attack == "resolution":
        joint["dispositions"]["nominal_percentile_resolution"] = 0.5
    else:
        joint["dispositions"]["attempted"] = 999
    with pytest.raises(ValueError, match="[Bb]ootstrap"):
        ASSESS(_register(tmp_path, synthetic_report), numerical_method=METHOD)


@pytest.mark.parametrize(
    "attack",
    (
        "predictive_indefinite_covariance",
        "predictive_asymmetric_covariance",
        "rate_coordinate_order",
        "predictive_coordinate_order",
        "predictive_direction",
        "resampling_unit",
        "within_path",
        "independent_labels",
        "paired_evaluation",
    ),
)
def test_rehashed_v2_summary_math_coordinates_and_design_reject(tmp_path, synthetic_report, attack):
    joint = synthetic_report["joint_uncertainty"]
    if attack.startswith("predictive_") and attack.endswith("covariance"):
        covariance = [[1e-20 * int(i == j) for j in range(8)] for i in range(8)]
        if attack == "predictive_indefinite_covariance":
            covariance[0][0] = -1e-20
        else:
            covariance[0][1] = 1e-21
        joint["predictive_difference_summaries"]["adjacent"]["covariance"] = covariance
    elif attack == "rate_coordinate_order":
        joint["rate_coordinates"].reverse()
    elif attack == "predictive_coordinate_order":
        joint["predictive_difference_coordinates"].reverse()
    elif attack == "predictive_direction":
        joint["predictive_difference_coordinates"][0]["higher_is_better"] = False
    elif attack == "resampling_unit":
        joint["unit_resampled"] = "individual_observation"
    else:
        key = {
            "within_path": "within_path_dependence_preserved",
            "independent_labels": "independence_across_labels_assumed",
            "paired_evaluation": "evaluation_resampled_separately_and_paired_across_models",
        }[attack]
        joint[key] = False
    with pytest.raises(ValueError, match="Invalid joint covariance|Frozen bootstrap"):
        ASSESS(_register(tmp_path, synthetic_report), numerical_method=METHOD)


@pytest.mark.parametrize("attack", ("grid", "cutoff", "failure", "regularity"))
def test_rehashed_v2_profile_controls_reject(tmp_path, synthetic_report, attack):
    _forge_available_model(synthetic_report, "adjacent")
    profile = synthetic_report["profiles"]["adjacent"][0]
    if attack == "grid":
        profile["points"] = profile["points"][:1]
    elif attack == "cutoff":
        profile["support_cutoff"] = 1.0
    elif attack == "failure":
        assert profile["failed_grid_points"] == 1
        profile["failed_grid_points"] = 0
    else:
        profile["regular_interior_interpretation_eligible"] = True
    with pytest.raises(ValueError, match="[Pp]rofile"):
        ASSESS(_register(tmp_path, synthetic_report), numerical_method=METHOD)


@pytest.mark.parametrize("ulps", (1, 2))
def test_synthetic_v2_profile_accepts_platform_transcendental_roundoff(
    tmp_path, synthetic_report, monkeypatch, ulps
):
    _forge_available_model(synthetic_report, "adjacent")
    root = _register(tmp_path, synthetic_report)
    PLATFORM_ROUNDOFF(monkeypatch, ulps)
    proof = ASSESS(root, numerical_method=METHOD)
    assert proof["passed"] is True
    assert proof["fit_checks"]["adjacent"]["fit_available"] is True
    assert proof["actual_source_replay"] is None


@pytest.mark.parametrize("successful", (0, 1))
def test_consistent_unavailable_v2_bootstrap_summaries_pass(tmp_path, synthetic_report, successful):
    joint = synthetic_report["joint_uncertainty"]
    joint["dispositions"].update(
        failed_primary_fits=200 - successful,
        paired_prediction_unavailable_draws=200 - successful,
    )
    empty = {
        "available": False,
        "successful_draws": successful,
        "covariance": None,
        "quantiles": None,
    }
    joint["joint_rate_summary"] = copy.deepcopy(empty)
    joint["per_model_rate_summaries"]["adjacent"] = copy.deepcopy(empty)
    joint["predictive_difference_summaries"]["adjacent"] = copy.deepcopy(empty)
    proof = ASSESS(_register(tmp_path, synthetic_report), numerical_method=METHOD)
    assert proof["passed"] is True
    assert proof["actual_source_replay"] is None
