"""Offline failed-v1 integrity and explicitly synthetic available-branch tests.

Available CTMC envelopes below are deliberate synthetic semantic fixtures. They
are not fits to the empirical source and are never registered outside tmp_path.
"""

import hashlib
import json
from pathlib import Path
from runpy import run_path
import shutil

import numpy as np
import pytest
from scipy.stats import chi2
import yaml

from demeter.analysis import ipop_a1c as a1c
from demeter.analysis import laboratory_panel as lab

ROOT = Path(__file__).resolve().parents[1]
ASSESS = run_path(str(ROOT / "scripts/verify_ipop_a1c_working_fit.py"))["assess"]
PROFILE_CONTRACT = run_path(str(ROOT / "scripts/verify_ipop_a1c_working_fit.py"))[
    "_profile_contract"
]


def _platform_transcendental_roundoff(monkeypatch, ulps):
    """Simulate libm reconstruction differences; never perturb frozen reports."""
    logspace, ppf = np.logspace, chi2.ppf

    def platform_logspace(*args, **kwargs):
        result = logspace(*args, **kwargs).copy()
        for _ in range(ulps):
            result[:-1] = np.nextafter(result[:-1], np.inf)
        # 10**0 is the exact computational cap, not a platform-dependent endpoint.
        return result

    def platform_ppf(*args, **kwargs):
        result = float(ppf(*args, **kwargs))
        for _ in range(ulps):
            result = float(np.nextafter(result, np.inf))
        return result

    monkeypatch.setattr(np, "logspace", platform_logspace)
    monkeypatch.setattr(chi2, "ppf", platform_ppf)


def _toy_profiles(paths, rates, structure, likelihood, *, numerical_method="v1"):
    """Complete toy payloads with real toy-path likelihoods, no nuisance fitting.

    Convergence annotations are deliberately forged for semantic branch tests.
    The positive first grid point of the first profile is an explicit synthetic
    numerical failure, distinct from any structurally impossible zero point.
    """
    protocol = a1c.load_protocol()
    settings = a1c.settings_for(protocol, structure)
    spec = protocol["numerics"]["profile_grid"]
    base = [0.0] + np.logspace(
        spec["log10_min_per_source_day"], spec["log10_max_per_source_day"], spec["points"]
    ).tolist()
    cutoff = float(chi2.ppf(protocol["numerics"]["nominal_profile_support_probability"], 1))
    profiles = []
    for index in range(len(rates)):
        grid, points, accepted = sorted(set(base + [rates[index]])), [], []
        failed, structural, better = 0, 0, False
        for value in grid:
            point_rates = list(rates)
            # Match the frozen search's scaled-coordinate expansion exactly,
            # including a possible one-ULP multiplication/division round trip.
            point_rates[index] = value * settings.day_scale / settings.day_scale
            log_value = lab.conditional_log_likelihood(
                paths, point_rates, structure, probability_tolerance=settings.probability_tolerance
            )
            synthetic_failure = index == 0 and value == base[1]
            if not np.isfinite(log_value) or synthetic_failure:
                impossible = not np.isfinite(log_value)
                maximal = list(settings.rate_upper_bounds)
                maximal[index] = value
                assert (lab._unreachable_pairs(paths, maximal, structure) > 0) is impossible
                points.append(
                    {
                        "rate": value,
                        "converged": False,
                        "structurally_impossible_for_all_nuisance_rates": impossible,
                        "log_likelihood": {
                            "value": None,
                            "status": "negative_infinity_zero_probability",
                        }
                        if impossible
                        else None,
                        "deviance_from_fitted": None,
                        "deviance_status": "positive_infinity" if impossible else "unavailable",
                        "multistarts": [
                            {"converged": False, "synthetic_unavailable_control_only": True}
                            for _ in settings.initial_rates
                        ],
                        "evaluation_failures": {},
                    }
                )
                failed += int(not impossible)
                structural += int(impossible)
                continue
            deviance = 2 * (likelihood["value"] - log_value)
            better |= deviance < -settings.probability_tolerance
            if deviance <= cutoff:
                accepted.append(value)
            points.append(
                {
                    "rate": value,
                    "converged": True,
                    "log_likelihood": {"value": log_value, "status": "finite"},
                    "deviance_from_fitted": deviance,
                    "rates": point_rates,
                    "nuisance_zero_indices": [
                        i for i, rate in enumerate(point_rates) if i != index and rate == 0
                    ],
                    "nuisance_cap_indices": [
                        i for i, rate in enumerate(point_rates) if i != index and rate >= 1
                    ],
                    "evaluation_failures": {},
                }
            )
        zero = any(rate == 0 for rate in rates) or 0.0 in accepted
        cap_hit = any(rate >= 1 for rate in rates) or 1.0 in accepted
        lower_open, upper_open = (
            bool(accepted) and grid[0] in accepted,
            bool(accepted) and grid[-1] in accepted,
        )
        profiles.append(
            {
                **({"numerical_method": numerical_method} if numerical_method != "v1" else {}),
                "rate_index": index,
                "rate_unit": "per_source_day",
                "points": points,
                "support_cutoff": cutoff,
                "support_reference": "caller_declared_interior_asymptotic_only",
                "supported_grid_rates": accepted,
                "finite_confidence_interval": None,
                "lower_grid_limit_open": lower_open,
                "upper_grid_limit_open": upper_open,
                "zero_boundary_supported_or_fitted": zero,
                "computational_cap_hit_or_supported": cap_hit,
                "failed_grid_points": failed,
                "structural_zero_probability_grid_points": structural,
                "baseline_improved_by_profile_search": bool(better),
                "regular_interior_interpretation_eligible": not (
                    zero or cap_hit or failed or lower_open or upper_open or better
                ),
                "interior_reference_requires_correctly_specified_independent_label_model": True,
                "clinical_confidence_interval": False,
                "synthetic_profile_fixture_only": True,
            }
        )
    return profiles


def _synthetic_available_primary(report):
    """Forge an available model only to exercise verifier branches, not evidence."""
    model = report["models"]["adjacent"]
    rates = [0.002, 0.003, 0.004, 0.005]
    paths = (lab.PanelPath((0, 20, 100), (0, 1, 2)), lab.PanelPath((0, 50), (1, 0)))
    likelihood = {
        "value": lab.conditional_log_likelihood(
            paths, rates, "adjacent", probability_tolerance=1e-10
        ),
        "status": "finite",
    }
    model.update(
        fit_performed=True,
        rates=rates,
        failure=None,
        log_likelihood=likelihood,
        identification={
            "available": True,
            "global_identification_established": False,
            "practical_identification_established": False,
            "observation_to_clinical_state_compatibility_established": False,
        },
        zero_rate_indices=[],
        search_cap_indices=[],
    )
    for row in model["multistarts"]:
        row["converged"] = False
    model["multistarts"][0].update(
        converged=True,
        rates=list(rates),
        log_likelihood=dict(likelihood),
        direct_likelihood_gradient_verified=True,
        projected_gradient_norm=0.0,
    )
    report["profiles"]["adjacent"] = _toy_profiles(paths, rates, "adjacent", likelihood)
    report["internal_evaluation"]["scores"]["adjacent"] = lab.score_predictions(
        paths, model, probability_tolerance=1e-10
    )


def _edited_report(tmp_path, edit, *, synthetic_available=False):
    for relative in (
        "docs/validation/ipop-a1c-working-fit-protocol-v1.json",
        "docs/validation/ipop-a1c-numerical-amendment-v1.json",
        "docs/validation/ipop-preflight-namespace-result-v2.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    registry = yaml.safe_load((ROOT / "evidence/parameters.yaml").read_text())
    spec = registry["datasets"]["ipop_a1c_working_fit"]
    report = json.loads((ROOT / spec["result"]["path"]).read_bytes())
    if synthetic_available:
        _synthetic_available_primary(report)
    edit(report)
    target = tmp_path / spec["result"]["path"]
    data = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    target.write_bytes(data)
    spec["result"]["sha256"] = hashlib.sha256(data).hexdigest()
    # Refresh outer bindings deliberately: these adversarial fixtures exercise
    # semantic checks rather than stopping at an ordinary checksum mismatch.
    spec["working_rate_parameters"]["value"] = report["models"]["adjacent"]["rates"]
    spec["working_rate_parameters"]["estimation_status"] = (
        "conditional_analysis_completed_primary_estimate_unresolved"
        if report["models"]["adjacent"]["rates"] is None
        else "conditional_working_fit_completed_clinical_use_unresolved"
    )
    spec["result"]["estimated_parameters"] = {
        "primary_rates_per_source_day": report["models"]["adjacent"]["rates"],
        "general_rates_per_source_day": report["models"]["unrestricted"]["rates"],
        "iid_followup_band_probabilities": report["models"]["iid"]["probabilities"],
    }
    if synthetic_available:
        # Do not attach actual failed-run estimate descriptions to toy values.
        spec["result"].pop("estimated_parameter_metadata", None)
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence/parameters.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    return tmp_path


def test_committed_aggregate_audit_stays_offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Aggregate audit must not fetch or replay participant records")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("demeter.analysis.ipop_a1c.analyze_cache", forbidden)
    proof = ASSESS()
    assert proof["passed"] is True
    assert proof["actual_source_replay"] is None
    assert proof["clinical_acceptance_established"] is False
    assert proof["engine_activation_allowed"] is False
    assert proof["selection_denominators_reconcile"] is True
    assert all(check["fit_available"] is False for check in proof["fit_checks"].values())


def test_preserved_failed_v1_disposition_is_not_a_bootstrap_point_estimate():
    path = ROOT / "docs/validation/ipop-a1c-working-result-v1.json"
    data = path.read_bytes()
    assert (
        hashlib.sha256(data).hexdigest()
        == "e44528ab04a13db4f8c30cf2365e86959aa13962a205a65b982615cfe61b9ced"
    )
    report = json.loads(data)
    assert report["analysis_completed"] is True
    for name in ("adjacent", "unrestricted"):
        model = report["models"][name]
        assert model["fit_performed"] is False and model["rates"] is None
        assert model["log_likelihood"] is None and model["identification"] is None
        assert report["profiles"][name] is None
        assert len(model["multistarts"]) == 6
        assert all(
            not row["converged"] and row["iterations"] == 1000 for row in model["multistarts"]
        )
        assert report["internal_evaluation"]["scores"][name] == {
            "unavailable": "no_converged_working_fit"
        }
    assert report["models"]["iid"]["fit_performed"] is True
    joint = report["joint_uncertainty"]
    assert joint["repetitions_attempted"] == 200
    assert joint["dispositions"]["failed_primary_fits"] == 157
    assert joint["joint_rate_summary"]["successful_draws"] == 43
    assert joint["summaries_conditioned_on_successful_finite_draws"] is True
    spec = yaml.safe_load((ROOT / "evidence/parameters.yaml").read_text(encoding="utf-8"))[
        "datasets"
    ]["ipop_a1c_working_fit"]
    assert spec["working_rate_parameters"]["value"] is None
    assert (
        spec["working_rate_parameters"]["estimation_status"]
        == "conditional_analysis_completed_primary_estimate_unresolved"
    )
    assert spec["result"]["estimated_parameters"]["primary_rates_per_source_day"] is None
    assert spec["result"]["estimated_parameters"]["general_rates_per_source_day"] is None
    assert (
        spec["result"]["estimated_parameters"]["iid_followup_band_probabilities"]
        == report["models"]["iid"]["probabilities"]
    )


def test_explicit_synthetic_available_branch_passes_semantic_audit(tmp_path):
    proof = ASSESS(_edited_report(tmp_path, lambda report: None, synthetic_available=True))
    assert proof["fit_checks"]["adjacent"]["fit_available"] is True
    assert proof["fit_checks"]["unrestricted"]["fit_available"] is False
    assert proof["clinical_acceptance_established"] is False


@pytest.mark.parametrize(
    "gate",
    [
        "clinical_fit_performed",
        "diagnosis_or_remission_inference_performed",
        "death_or_censoring_inference_performed",
        "dietary_effect_estimated",
        "national_transport_established",
        "engine_activation_allowed",
        "scientific_acceptance_changed",
    ],
)
def test_aggregate_cannot_promote_scientific_scope_even_with_rehashed_receipt(tmp_path, gate):
    root = _edited_report(tmp_path, lambda report: report.update({gate: True}))
    with pytest.raises(ValueError):
        ASSESS(root)


def test_aggregate_rejects_unreconciled_selection(tmp_path):
    def edit(report):
        report["selection"]["denominator_admitted_rows"] += 1

    with pytest.raises(ValueError, match="denominators"):
        ASSESS(_edited_report(tmp_path, edit))


def test_aggregate_rejects_false_optimizer_gradient_claim(tmp_path):
    def edit(report):
        model = report["models"]["adjacent"]
        for row in model["multistarts"]:
            if row["converged"]:
                row["projected_gradient_norm"] = 1.0

    with pytest.raises(ValueError, match="gradient"):
        ASSESS(_edited_report(tmp_path, edit, synthetic_available=True))


def test_aggregate_rejects_rates_not_from_an_accepted_start(tmp_path):
    def edit(report):
        model = report["models"]["adjacent"]
        model["rates"][0] = 0.7 if model["rates"][0] < 0.5 else 0.3

    with pytest.raises(ValueError, match="accepted best"):
        ASSESS(_edited_report(tmp_path, edit, synthetic_available=True))


def test_aggregate_rejects_altered_rate_order(tmp_path):
    def edit(report):
        report["models"]["adjacent"]["parameter_edges"].reverse()

    with pytest.raises(ValueError, match="Rate order"):
        ASSESS(_edited_report(tmp_path, edit))


def test_aggregate_rejects_duplicate_profile_indices(tmp_path):
    def edit(report):
        report["profiles"]["adjacent"][1]["rate_index"] = 0

    with pytest.raises(ValueError, match="profile interval"):
        ASSESS(_edited_report(tmp_path, edit, synthetic_available=True))


@pytest.mark.parametrize("scale", [1.0, 1e-20])
def test_aggregate_rejects_indefinite_joint_covariance(tmp_path, scale):
    def edit(report):
        summary = report["joint_uncertainty"]["joint_rate_summary"]
        assert summary["available"] is True
        summary["covariance"] = [[scale * int(i == j) for j in range(4)] for i in range(4)]
        summary["covariance"][0][0] = -scale

    with pytest.raises(ValueError, match="covariance"):
        ASSESS(_edited_report(tmp_path, edit))


def test_aggregate_rejects_altered_reported_source_pins(tmp_path):
    def edit(report):
        report["provenance"]["source_bytes"]["clinical"]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="source-byte"):
        ASSESS(_edited_report(tmp_path, edit))


@pytest.mark.parametrize("section", ["model", "bootstrap", "evaluation"])
def test_nested_scope_cannot_promote_clinical_use(tmp_path, section):
    def edit(report):
        if section == "model":
            report["models"]["adjacent"]["engine_activation_allowed"] = True
        elif section == "bootstrap":
            report["joint_uncertainty"]["clinical_fit_performed"] = True
        else:
            report["internal_evaluation"]["clinical_acceptance_tolerance"] = 0.1

    with pytest.raises(ValueError, match="Nested"):
        ASSESS(_edited_report(tmp_path, edit))


@pytest.mark.parametrize("payload", ["likelihood", "identification", "score"])
def test_unavailable_fit_cannot_retain_successful_results(tmp_path, payload):
    def edit(report):
        # Simulate a failed alternative fit, keeping the primary binding intact.
        model = report["models"]["unrestricted"]
        model.update(
            fit_performed=False,
            rates=None,
            failure="no_converged_finite_multistart",
            log_likelihood=None,
            identification=None,
            zero_rate_indices=[],
            search_cap_indices=[],
        )
        for row in model["multistarts"]:
            row["converged"] = False
        report["profiles"]["unrestricted"] = None
        report["internal_evaluation"]["scores"]["unrestricted"] = {
            "unavailable": "no_converged_working_fit"
        }
        if payload == "likelihood":
            model["log_likelihood"] = {"value": -1.0, "impossible": False}
        elif payload == "identification":
            model["identification"] = {"available": True}
        else:
            report["internal_evaluation"]["scores"]["unrestricted"] = {"one_step": 0.1}

    with pytest.raises(ValueError, match="Unavailable"):
        ASSESS(_edited_report(tmp_path, edit))


@pytest.mark.parametrize(
    "field",
    [
        "binding_v1_protocol_sha256",
        "binding_v2_protocol_sha256",
        "prior_v2_result_sha256",
        "supplied_protocol_canonical_sha256",
        "assumptions",
    ],
)
def test_frozen_provenance_cannot_change_with_refreshed_outer_binding(tmp_path, field):
    def edit(report):
        report["provenance"][field] = (
            {"estimand": "clinical diagnosis"} if field == "assumptions" else "0" * 64
        )

    with pytest.raises(ValueError, match="Frozen provenance"):
        ASSESS(_edited_report(tmp_path, edit))


@pytest.mark.parametrize(
    "attack",
    (
        "seed",
        "joint_quantiles",
        "predictive_quantiles",
        "disposition_attempts",
        "hidden_failures",
        "successful_count",
        "predictive_count",
        "excess_boundary_count",
        "fractional_count",
        "resolution",
    ),
)
def test_rehashed_frozen_bootstrap_controls_and_count_closure_reject(tmp_path, attack):
    def edit(report):
        joint = report["joint_uncertainty"]
        if attack == "seed":
            joint["seed"] = 1
        elif attack == "joint_quantiles":
            joint["joint_rate_summary"]["quantile_levels"] = [0.1, 0.5, 0.9]
        elif attack == "predictive_quantiles":
            joint["predictive_difference_summaries"]["adjacent"]["quantile_levels"] = [
                0.1,
                0.5,
                0.9,
            ]
        elif attack == "disposition_attempts":
            joint["dispositions"]["attempted"] = 999
        elif attack == "hidden_failures":
            joint["dispositions"]["failed_primary_fits"] = 0
        elif attack == "successful_count":
            joint["joint_rate_summary"]["successful_draws"] = 999
        elif attack == "predictive_count":
            joint["predictive_difference_summaries"]["adjacent"]["successful_draws"] = 0
        elif attack == "excess_boundary_count":
            joint["dispositions"]["primary_computational_cap_draws"] = 100
        elif attack == "fractional_count":
            joint["dispositions"]["failed_primary_fits"] = 157.0
        else:
            joint["dispositions"]["nominal_percentile_resolution"] = 0.5

    with pytest.raises(ValueError, match="[Bb]ootstrap"):
        ASSESS(_edited_report(tmp_path, edit))


@pytest.mark.parametrize("summary_kind", ("joint", "per_model", "predictive"))
@pytest.mark.parametrize("attack", ("indefinite", "asymmetric"))
def test_rehashed_every_available_covariance_rejects_impossible_matrix(
    tmp_path, summary_kind, attack
):
    def edit(report):
        joint = report["joint_uncertainty"]
        summary = (
            joint["joint_rate_summary"]
            if summary_kind == "joint"
            else joint[
                "per_model_rate_summaries"
                if summary_kind == "per_model"
                else "predictive_difference_summaries"
            ]["adjacent"]
        )
        dimension = 8 if summary_kind == "predictive" else 4
        covariance = [[1e-20 * int(i == j) for j in range(dimension)] for i in range(dimension)]
        if attack == "indefinite":
            covariance[0][0] = -1e-20
        else:
            covariance[0][1] = 1e-21
        summary["covariance"] = covariance

    with pytest.raises(ValueError, match="Invalid joint covariance"):
        ASSESS(_edited_report(tmp_path, edit))


@pytest.mark.parametrize(
    "attack",
    (
        "rate_coordinate_order",
        "predictive_coordinate_order",
        "predictive_direction",
        "noninteger_rate_coordinate",
        "resampling_unit",
        "within_path",
        "independent_labels",
        "paired_evaluation",
    ),
)
def test_rehashed_frozen_bootstrap_coordinates_and_design_reject(tmp_path, attack):
    def edit(report):
        joint = report["joint_uncertainty"]
        if attack == "rate_coordinate_order":
            joint["rate_coordinates"].reverse()
        elif attack == "predictive_coordinate_order":
            joint["predictive_difference_coordinates"].reverse()
        elif attack == "predictive_direction":
            joint["predictive_difference_coordinates"][0]["higher_is_better"] = False
        elif attack == "noninteger_rate_coordinate":
            joint["rate_coordinates"][0]["rate_index"] = False
        elif attack == "resampling_unit":
            joint["unit_resampled"] = "individual_observation"
        else:
            key = {
                "within_path": "within_path_dependence_preserved",
                "independent_labels": "independence_across_labels_assumed",
                "paired_evaluation": "evaluation_resampled_separately_and_paired_across_models",
            }[attack]
            joint[key] = False

    with pytest.raises(ValueError, match="Frozen bootstrap"):
        ASSESS(_edited_report(tmp_path, edit))


@pytest.mark.parametrize(
    "attack",
    (
        "grid",
        "cutoff",
        "hidden_failure",
        "hidden_structural_zero",
        "regularity",
        "supported_rates",
        "open_limit",
        "deviance",
        "structural_as_numerical_failure",
    ),
)
def test_rehashed_profile_controls_and_annotations_reject(tmp_path, attack):
    def edit(report):
        profile = report["profiles"]["adjacent"][0]
        if attack == "grid":
            profile["points"] = profile["points"][:1]
        elif attack == "cutoff":
            profile["support_cutoff"] = 1.0
        elif attack == "hidden_failure":
            assert profile["failed_grid_points"] == 1
            profile["failed_grid_points"] = 0
        elif attack == "hidden_structural_zero":
            assert profile["structural_zero_probability_grid_points"] == 1
            profile["structural_zero_probability_grid_points"] = 0
        elif attack == "regularity":
            assert profile["regular_interior_interpretation_eligible"] is False
            profile["regular_interior_interpretation_eligible"] = True
        elif attack == "supported_rates":
            assert profile["supported_grid_rates"]
            profile["supported_grid_rates"] = []
        elif attack == "open_limit":
            profile["lower_grid_limit_open"] = not profile["lower_grid_limit_open"]
        elif attack == "deviance":
            point = next(point for point in profile["points"] if point["converged"])
            point["deviance_from_fitted"] += 1.0
        else:
            point = profile["points"][0]
            assert point["structurally_impossible_for_all_nuisance_rates"] is True
            point["structurally_impossible_for_all_nuisance_rates"] = False

    with pytest.raises(ValueError, match="[Pp]rofile"):
        ASSESS(_edited_report(tmp_path, edit, synthetic_available=True))


@pytest.mark.parametrize("ulps", (1, 2))
def test_synthetic_profile_accepts_platform_transcendental_roundoff(tmp_path, monkeypatch, ulps):
    root = _edited_report(tmp_path, lambda report: None, synthetic_available=True)
    # Freeze the toy envelope first, then change only local reconstruction math.
    _platform_transcendental_roundoff(monkeypatch, ulps)
    proof = ASSESS(root)
    assert proof["passed"] is True
    assert proof["fit_checks"]["adjacent"]["fit_available"] is True
    assert proof["actual_source_replay"] is None


@pytest.mark.parametrize(
    "attack",
    (
        "grid",
        "cutoff",
        "grid_over_ulps",
        "cutoff_over_ulps",
        "fitted_coordinate",
        "fixed_rate",
        "zero",
        "cap",
        "order",
    ),
)
def test_rehashed_profile_roundoff_does_not_admit_material_or_exact_control_drift(tmp_path, attack):
    def edit(report):
        profile = report["profiles"]["adjacent"][0]
        if attack == "grid":
            profile["points"][1]["rate"] *= 1.01
        elif attack == "cutoff":
            profile["support_cutoff"] *= 1.01
        elif attack in ("grid_over_ulps", "cutoff_over_ulps"):
            value = (
                profile["points"][1]["rate"]
                if attack == "grid_over_ulps"
                else profile["support_cutoff"]
            )
            for _ in range(5 if attack == "grid_over_ulps" else 9):
                value = float(np.nextafter(value, np.inf))
            if attack == "grid_over_ulps":
                profile["points"][1]["rate"] = value
            else:
                profile["support_cutoff"] = value
        elif attack == "fitted_coordinate":
            fitted = report["models"]["adjacent"]["rates"][0]
            point = next(point for point in profile["points"] if point["rate"] == fitted)
            point["rate"] = float(np.nextafter(fitted, np.inf))
        elif attack == "fixed_rate":
            point = next(point for point in profile["points"] if point["converged"])
            point["rates"][0] = float(np.nextafter(point["rates"][0], np.inf))
        elif attack == "zero":
            profile["points"][0]["rate"] = float(np.nextafter(0.0, np.inf))
        elif attack == "cap":
            profile["points"][-1]["rate"] = float(np.nextafter(1.0, 0.0))
        else:
            profile["points"][1], profile["points"][2] = (
                profile["points"][2],
                profile["points"][1],
            )

    with pytest.raises(ValueError, match="[Pp]rofile"):
        ASSESS(_edited_report(tmp_path, edit, synthetic_available=True))


@pytest.mark.parametrize("attack", ("ulp_drift", "missing_endpoint"))
def test_profile_reconstruction_failure_reports_only_safe_aggregate_controls(tmp_path, attack):
    def edit(report):
        profile = report["profiles"]["adjacent"][0]
        if attack == "ulp_drift":
            for _ in range(5):
                profile["points"][1]["rate"] = float(
                    np.nextafter(profile["points"][1]["rate"], np.inf)
                )
            for _ in range(6):
                profile["support_cutoff"] = float(np.nextafter(profile["support_cutoff"], np.inf))
        else:
            profile["points"].pop()

    with pytest.raises(ValueError, match="Frozen profile grid or support controls drift:") as error:
        ASSESS(_edited_report(tmp_path, edit, synthetic_available=True))
    diagnostics = json.loads(str(error.value).split(": ", 1)[1])
    assert set(diagnostics) == {
        "profile_index",
        "retained_point_count",
        "expected_point_count",
        "mismatched_grid_indices",
        "max_grid_ulp_distance",
        "retained_cutoff",
        "expected_cutoff",
        "cutoff_ulp_distance",
        "cutoff_within_roundoff_budget",
        "zero_endpoint_exact",
        "cap_endpoint_exact",
        "fitted_coordinate_exact",
        "point_order_strict",
        "rate_unit_matches",
        "support_reference_matches",
        "interior_assumption_declared",
    }
    assert diagnostics["profile_index"] == 0
    assert diagnostics["expected_point_count"] == 31
    assert diagnostics["retained_point_count"] == (31 if attack == "ulp_drift" else 30)
    assert diagnostics["mismatched_grid_indices"] == ([1] if attack == "ulp_drift" else [30])
    assert diagnostics["max_grid_ulp_distance"] == (5 if attack == "ulp_drift" else 0)
    assert diagnostics["cutoff_ulp_distance"] == (6 if attack == "ulp_drift" else 0)
    assert diagnostics["cutoff_within_roundoff_budget"] is True
    assert diagnostics["expected_cutoff"] == float(chi2.ppf(0.95, 1))
    assert diagnostics["retained_cutoff"] >= diagnostics["expected_cutoff"]
    assert diagnostics["cap_endpoint_exact"] is (attack == "ulp_drift")
    assert all(
        diagnostics[key] is True
        for key in (
            "zero_endpoint_exact",
            "fitted_coordinate_exact",
            "point_order_strict",
            "rate_unit_matches",
            "support_reference_matches",
            "interior_assumption_declared",
        )
    )


@pytest.mark.parametrize("ulps", (8, 9))
def test_inverse_cdf_reconstruction_budget_is_anchored_to_retained_synthetic_control(
    tmp_path, monkeypatch, ulps
):
    root = _edited_report(tmp_path, lambda report: None, synthetic_available=True)
    report = json.loads((root / "docs/validation/ipop-a1c-working-result-v1.json").read_bytes())
    retained = report["profiles"]["adjacent"][0]["support_cutoff"]
    reconstructed = retained
    for _ in range(ulps):
        reconstructed = float(np.nextafter(reconstructed, -np.inf))
    # Anchor to the retained toy value, avoiding accumulated platform differences.
    monkeypatch.setattr(chi2, "ppf", lambda *args, **kwargs: reconstructed)
    if ulps == 8:
        assert ASSESS(root)["passed"] is True
    else:
        with pytest.raises(ValueError, match="Frozen profile grid") as error:
            ASSESS(root)
        diagnostics = json.loads(str(error.value).split(": ", 1)[1])
        assert diagnostics["max_grid_ulp_distance"] == 0
        assert diagnostics["cutoff_ulp_distance"] == 9
        assert diagnostics["cutoff_within_roundoff_budget"] is False


def test_frozen_profile_builder_roundtrip_passes_with_mocked_toy_search(monkeypatch):
    """Real profile annotations around a mocked toy search, never an optimizer fit."""
    protocol = a1c.load_protocol()
    settings = a1c.settings_for(protocol, "adjacent")
    paths = (lab.PanelPath((0, 20, 100), (0, 1, 2)), lab.PanelPath((0, 50), (1, 0)))
    rates = [0.002, 0.003, 0.004, 0.005]
    baseline = lab.conditional_log_likelihood(
        paths, rates, "adjacent", probability_tolerance=settings.probability_tolerance
    )
    fitted = {
        "kind": "ctmc",
        "structure": "adjacent",
        "fit_performed": True,
        "rates": rates,
        "log_likelihood": {"value": baseline, "status": "finite"},
    }

    def mock_toy_search(paths, config, *, fixed, numerical_method):
        values = list(rates)
        values[fixed[0]] = fixed[1] * config.day_scale / config.day_scale
        value = lab.conditional_log_likelihood(
            paths, values, config.structure, probability_tolerance=config.probability_tolerance
        )
        return (value, np.asarray(values), {}) if np.isfinite(value) else None, [], {}

    monkeypatch.setattr(lab, "_search", mock_toy_search)
    grid = [0.0] + np.logspace(-7, 0, 29).tolist()
    profile = lab.profile_rate(
        paths,
        fitted,
        settings,
        0,
        grid,
        support_cutoff=float(chi2.ppf(0.95, 1)),
        numerical_method="exact_box_quadratic_v2",
    )
    assert any(
        point["converged"] and point["rates"][0] != point["rate"] for point in profile["points"]
    )
    PROFILE_CONTRACT(profile, fitted, settings, protocol)
