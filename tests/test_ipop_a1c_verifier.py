"""Offline failed-v1 integrity and explicitly synthetic available-branch tests.

Available CTMC envelopes below are deliberate synthetic semantic fixtures. They
are not fits to the empirical source and are never registered outside tmp_path.
"""

import hashlib
import json
from pathlib import Path
from runpy import run_path
import shutil

import pytest
import yaml

from demeter.analysis import laboratory_panel as lab

ROOT = Path(__file__).resolve().parents[1]
ASSESS = run_path(str(ROOT / "scripts/verify_ipop_a1c_working_fit.py"))["assess"]


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
    report["profiles"]["adjacent"] = [
        {"rate_index": i, "finite_confidence_interval": None, "clinical_confidence_interval": False}
        for i in range(4)
    ]
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
