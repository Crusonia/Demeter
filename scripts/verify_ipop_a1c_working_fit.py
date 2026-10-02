"""Offline integrity/math audit of the conditional iPOP aggregate working report.

This does not read participant records or independently validate clinical rates.
Optional --raw replays the entire frozen empirical analysis from verified cache.
Historical report bytes remain immutable; only its registry fingerprint and
implementation provenance may differ in an explicitly reported current replay.
Offline checks reconcile retained aggregates; omitted bootstrap draws and source
nuisance optima cannot be independently reconstructed from this report.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.stats import chi2

from demeter.analysis import ipop_a1c as a1c
from demeter.analysis import laboratory_panel as lab
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
GATES = (
    "clinical_fit_performed",
    "diagnosis_or_remission_inference_performed",
    "death_or_censoring_inference_performed",
    "dietary_effect_estimated",
    "national_transport_established",
    "engine_activation_allowed",
    "scientific_acceptance_changed",
)


def _count(value, maximum, message):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(message)
    return value


def _covariance_contract(value, dimension):
    covariance = np.asarray(value)
    if covariance.shape != (dimension, dimension) or not np.isfinite(covariance).all():
        raise ValueError("Invalid joint covariance")
    # Covariance has squared units. A dimensionless probability tolerance can
    # conceal indefiniteness at small values; use scale-relative roundoff.
    tolerance = (
        16
        * np.finfo(float).eps
        * max(float(np.linalg.norm(covariance, ord=2)), np.finfo(float).tiny)
    )
    if (
        not np.allclose(covariance, covariance.T, atol=tolerance, rtol=0)
        or np.linalg.eigvalsh(covariance).min() < -tolerance
    ):
        raise ValueError("Invalid joint covariance")


def _sample_summary_contract(summary, successful, levels, dimension):
    if (
        type(summary["successful_draws"]) is not int
        or summary["successful_draws"] != successful
        or summary["available"] is not (successful >= 2)
    ):
        raise ValueError("Bootstrap successful-count or availability drift")
    if successful < 2:
        if summary["covariance"] is not None or summary["quantiles"] is not None:
            raise ValueError("Unavailable bootstrap summary retained estimates")
        return
    covariance = np.asarray(summary["covariance"])
    quantiles = np.asarray(summary["quantiles"])
    if (
        summary["quantile_levels"] != levels
        or covariance.shape != (dimension, dimension)
        or quantiles.shape != (len(levels), dimension)
        or not np.isfinite(covariance).all()
        or not np.isfinite(quantiles).all()
        or (np.diff(quantiles, axis=0) < 0).any()
    ):
        raise ValueError("Frozen bootstrap quantile controls or summary shape drift")
    _covariance_contract(covariance, dimension)


def _bootstrap_contract(joint, protocol):
    controls = protocol["joint_uncertainty"]
    total = controls["bootstrap_replicates"]
    rate_coordinates = [{"model": "adjacent", "rate_index": i} for i in range(4)]
    predictive_coordinates = [
        {
            "mode": mode,
            "metric": metric,
            "weighting": weighting,
            "higher_is_better": metric == "log_score",
        }
        for mode in ("one_step", "first_only")
        for metric in ("log_score", "brier")
        for weighting in ("equal_label", "transition_weighted")
    ]
    # JSON comparison also distinguishes bool/float indices from frozen integers.
    if json.dumps(joint["rate_coordinates"], sort_keys=True) != json.dumps(
        rate_coordinates, sort_keys=True
    ) or json.dumps(joint["predictive_difference_coordinates"], sort_keys=True) != json.dumps(
        predictive_coordinates, sort_keys=True
    ):
        raise ValueError("Frozen bootstrap summary coordinate drift")
    if (
        joint["unit_resampled"] != "whole_label_path"
        or joint["within_path_dependence_preserved"] is not True
        or joint["independence_across_labels_assumed"] is not True
        or joint["evaluation_resampled_separately_and_paired_across_models"] is not True
    ):
        raise ValueError("Frozen bootstrap resampling design drift")
    dispositions = joint["dispositions"]
    count_keys = (
        "requested",
        "attempted",
        "failed_primary_fits",
        "primary_zero_boundary_draws",
        "primary_computational_cap_draws",
        "primary_rank_deficient_draws",
        "primary_identification_unavailable_draws",
        "paired_prediction_unavailable_draws",
    )
    counts = {
        key: _count(dispositions[key], total, "Invalid bootstrap disposition count")
        for key in count_keys
    }
    if (
        _count(joint["repetitions_requested"], total, "Invalid bootstrap requested count") != total
        or _count(joint["repetitions_attempted"], total, "Invalid bootstrap attempted count")
        != total
        or counts["requested"] != total
        or counts["attempted"] != total
        or type(joint["seed"]) is not int
        or joint["seed"] != controls["seed"]
        or dispositions["nominal_percentile_resolution"] != 1 / total
        or joint["summaries_conditioned_on_successful_finite_draws"] is not True
    ):
        raise ValueError("Frozen bootstrap controls or disposition totals drift")
    successful = total - counts["failed_primary_fits"]
    predictive_successful = total - counts["paired_prediction_unavailable_draws"]
    if (
        predictive_successful > successful
        or any(counts[key] > successful for key in count_keys[3:7])
        or set(joint["per_model_rate_summaries"]) != {"adjacent"}
        or set(joint["predictive_difference_summaries"]) != {"adjacent"}
    ):
        raise ValueError("Bootstrap failure and successful-count closure drift")
    _sample_summary_contract(joint["joint_rate_summary"], successful, controls["quantiles"], 4)
    _sample_summary_contract(
        joint["per_model_rate_summaries"]["adjacent"], successful, controls["quantiles"], 4
    )
    if joint["per_model_rate_summaries"]["adjacent"] != joint["joint_rate_summary"]:
        raise ValueError("Single-primary bootstrap summaries differ")
    _sample_summary_contract(
        joint["predictive_difference_summaries"]["adjacent"],
        predictive_successful,
        controls["quantiles"],
        8,
    )


def _profile_contract(profile, model, settings, protocol):
    index = profile["rate_index"]
    grid_spec = protocol["numerics"]["profile_grid"]
    grid = sorted(
        {
            0.0,
            *np.logspace(
                grid_spec["log10_min_per_source_day"],
                grid_spec["log10_max_per_source_day"],
                grid_spec["points"],
            ).tolist(),
            model["rates"][index],
        }
    )
    cutoff = float(chi2.ppf(protocol["numerics"]["nominal_profile_support_probability"], 1))
    points = profile["points"]
    if (
        [point["rate"] for point in points] != grid
        or profile["support_cutoff"] != cutoff
        or profile["rate_unit"] != "per_source_day"
        or profile["support_reference"] != "caller_declared_interior_asymptotic_only"
        or profile["interior_reference_requires_correctly_specified_independent_label_model"]
        is not True
    ):
        raise ValueError("Frozen profile grid or support controls drift")
    accepted, failed, structural, better = [], 0, 0, False
    for point in points:
        if type(point["converged"]) is not bool:
            raise ValueError("Invalid profile point convergence annotation")
        impossible = point.get("structurally_impossible_for_all_nuisance_rates", False)
        if type(impossible) is not bool:
            raise ValueError("Invalid profile structural-zero annotation")
        if not point["converged"]:
            expected_log = (
                {"value": None, "status": "negative_infinity_zero_probability"}
                if impossible
                else None
            )
            if (
                point["log_likelihood"] != expected_log
                or point["deviance_from_fitted"] is not None
                or point["deviance_status"]
                != ("positive_infinity" if impossible else "unavailable")
            ):
                raise ValueError("Profile failure confused with structural zero probability")
            failed += int(not impossible)
            structural += int(impossible)
            continue
        likelihood = point["log_likelihood"]
        rates = point["rates"]
        if (
            impossible
            or likelihood["status"] != "finite"
            or type(likelihood["value"]) not in (float, int)
            or not np.isfinite(likelihood["value"])
            or len(rates) != len(model["rates"])
            or rates[index] != point["rate"] * settings.day_scale / settings.day_scale
            or any(
                type(rate) not in (float, int) or not np.isfinite(rate) or not 0 <= rate <= cap
                for rate, cap in zip(rates, settings.rate_upper_bounds, strict=True)
            )
        ):
            raise ValueError("Invalid available profile point")
        baseline = model["log_likelihood"]["value"]
        expected_deviance = 2 * (baseline - likelihood["value"])
        # The builder's pathwise baseline and compiled best-fit likelihood can
        # differ by summation roundoff. This budget never changes search tolerances.
        tolerance = 16 * np.finfo(float).eps * max(1, abs(baseline), abs(likelihood["value"]))
        deviance = point["deviance_from_fitted"]
        if (
            type(deviance) not in (float, int)
            or not np.isfinite(deviance)
            or abs(deviance - expected_deviance) > tolerance
            or point["nuisance_zero_indices"]
            != [i for i, rate in enumerate(rates) if i != index and rate == 0]
            or point["nuisance_cap_indices"]
            != [
                i
                for i, (rate, cap) in enumerate(zip(rates, settings.rate_upper_bounds, strict=True))
                if i != index and rate >= cap
            ]
        ):
            raise ValueError("Profile likelihood or nuisance-boundary annotations drift")
        if deviance <= cutoff:
            accepted.append(point["rate"])
        better |= deviance < -settings.probability_tolerance
    zero = (
        any(rate == 0 for rate in model["rates"])
        or 0.0 in accepted
        or any(point.get("nuisance_zero_indices") for point in points)
    )
    cap = settings.rate_upper_bounds[index]
    cap_hit = (
        any(
            rate >= bound
            for rate, bound in zip(model["rates"], settings.rate_upper_bounds, strict=True)
        )
        or cap in accepted
        or any(point.get("nuisance_cap_indices") for point in points)
    )
    lower_open, upper_open = (
        bool(accepted) and grid[0] in accepted,
        bool(accepted) and grid[-1] in accepted,
    )
    expected = {
        "supported_grid_rates": accepted,
        "failed_grid_points": failed,
        "structural_zero_probability_grid_points": structural,
        "lower_grid_limit_open": lower_open,
        "upper_grid_limit_open": upper_open,
        "zero_boundary_supported_or_fitted": zero,
        "computational_cap_hit_or_supported": cap_hit,
        "baseline_improved_by_profile_search": bool(better),
        "regular_interior_interpretation_eligible": not (
            zero or cap_hit or failed or lower_open or upper_open or better
        ),
    }
    if any(
        type(profile[key]) is not type(value) or profile[key] != value
        for key, value in expected.items()
    ):
        raise ValueError("Profile support, failure or interpretation annotations drift")


def assess(root: Path = ROOT, raw: Path | None = None, *, numerical_method: str = "v1") -> dict:
    if type(numerical_method) is not str or numerical_method not in a1c.NUMERICAL_METHODS:
        raise ValueError("Unsupported laboratory numerical method")
    version2 = numerical_method == "exact_box_quadratic_v2"
    numerical_keywords = {"numerical_method": numerical_method} if version2 else {}
    amendment_name = (
        "ipop-a1c-numerical-amendment-v2.json"
        if version2
        else "ipop-a1c-numerical-amendment-v1.json"
    )
    amendment_hash = a1c.NUMERICAL_V2_SHA256 if version2 else a1c.NUMERICAL_PROTOCOL_SHA256
    protocol = a1c.load_protocol(root / "docs/validation/ipop-a1c-working-fit-protocol-v1.json")
    policy = a1c.load_numerical_protocol(
        root / "docs/validation" / amendment_name, **numerical_keywords
    )
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    a1c._registry_contract(registry, protocol, root, **numerical_keywords)
    spec = registry.datasets["ipop_a1c_working_fit_v2" if version2 else "ipop_a1c_working_fit"]
    data = (root / spec["result"]["path"]).read_bytes()
    report = json.loads(data)
    if (
        report["execution_scope"] != "conditional_empirical_laboratory_working_analysis"
        or report["validation_only"] is not False
        or report["analysis_completed"] is not True
        or report["provenance"]["acquisition_receipts_verified"] is not True
        or report["provenance"]["independent_source_validation"] is not False
        or report["provenance"]["numerical_amendment_sha256"] != amendment_hash
        or any(report[key] is not False for key in GATES)
    ):
        raise ValueError("Invalid working report scope")
    provenance = report["provenance"]
    if version2:
        previous = (root / policy["prior_empirical_result_path"]).read_bytes()
        if (
            hashlib.sha256(previous).hexdigest() != a1c.V1_RESULT_SHA256
            or report["analysis_id"] != "ipop_a1c_conditional_working_fit_v2"
            or provenance.get("numerical_method") != numerical_method
            or provenance.get("prior_empirical_result_sha256") != a1c.V1_RESULT_SHA256
            or provenance.get("statistical_selection_changed") is not False
            or report["selection"] != json.loads(previous)["selection"]
            or any(
                report["models"][name].get("numerical_method") != numerical_method
                for name in ("adjacent", "unrestricted")
            )
            or report["joint_uncertainty"].get("numerical_method") != numerical_method
            or any(
                profile.get("numerical_method") != numerical_method
                for profiles in report["profiles"].values()
                for profile in profiles or ()
            )
        ):
            raise ValueError("Adaptive numerical version or frozen selection drift")
    if (
        provenance["supplied_protocol_canonical_sha256"] != a1c.CANONICAL_SHA256
        or any(
            provenance[key] != protocol["source"][key]
            for key in (
                "binding_v1_protocol_sha256",
                "binding_v2_protocol_sha256",
                "prior_v2_result_sha256",
            )
        )
        or provenance["assumptions"] != protocol["conditioning"]
    ):
        raise ValueError("Frozen provenance or conditioning drift")
    evaluation = report["internal_evaluation"]
    if (
        evaluation["kind"] != protocol["evaluation"]["kind"]
        or evaluation["clinical_acceptance_tolerance"] is not None
        or any(
            model.get(key, False) is not False
            for model in report["models"].values()
            for key in ("clinical_fit_performed", "engine_activation_allowed")
        )
        or any(
            report["joint_uncertainty"][key] is not False
            for key in ("clinical_fit_performed", "engine_activation_allowed")
        )
    ):
        raise ValueError("Nested working analysis scope drift")
    prior_data = (root / "docs/validation/ipop-preflight-namespace-result-v2.json").read_bytes()
    if hashlib.sha256(prior_data).hexdigest() != protocol["source"]["prior_v2_result_sha256"]:
        raise ValueError("Prior source binding artifact drift")
    expected_source_bytes = json.loads(prior_data)["provenance"]["source_bytes"]
    if (
        report["provenance"]["source_bytes"] != expected_source_bytes
        or report["acquisition_audit"]["passed"] is not True
    ):
        raise ValueError("Working report source-byte binding drift")
    selection = report["selection"]
    if (
        sum(selection["admitted_row_partition"].values()) != selection["denominator_admitted_rows"]
        or sum(selection["eligible_band_counts"])
        != selection["admitted_row_partition"]["eligible_assay_day"]
        or sum(p["admitted_labels"] for p in selection["partitions"].values())
        != selection["denominator_admitted_labels"]
        or any(
            sum(p["label_partition"].values()) != p["admitted_labels"]
            for p in selection["partitions"].values()
        )
    ):
        raise ValueError("Selection denominators do not reconcile")
    fit_checks = {}
    for name in ("adjacent", "unrestricted"):
        model = report["models"][name]
        settings = a1c.settings_for(protocol, name)
        # JSON deliberately converts immutable setting tuples to arrays.
        if model["settings"] != json.loads(json.dumps(asdict(settings))):
            raise ValueError("Numerical settings drift")
        if (
            model["parameter_edges"] != [list(edge) for edge in lab.EDGES[name]]
            or "gap_range_days" in model["source_support"]
        ):
            raise ValueError("Rate order drift or private coordinate export")
        if (
            model["search_cap_is_clinical_bound"] is not False
            or model.get("optimizer_convergence_is_identification", False) is not False
        ):
            raise ValueError("Numerical search cannot establish clinical bounds or identification")
        if model["fit_performed"] is not True:
            if (
                model["rates"] is not None
                or report["profiles"][name] is not None
                or model["log_likelihood"] is not None
                or model["identification"] is not None
                or model["zero_rate_indices"]
                or model["search_cap_indices"]
                or any(row["converged"] for row in model["multistarts"])
                or evaluation["scores"][name] != {"unavailable": "no_converged_working_fit"}
                or not model.get("failure")
            ):
                raise ValueError(
                    "Unavailable fit must retain null estimates and an explicit failure"
                )
            fit_checks[name] = {"fit_available": False, "failure": model.get("failure")}
            continue
        identification = model["identification"]
        if identification is not None and any(
            identification.get(key, False) is not False
            for key in (
                "global_identification_established",
                "practical_identification_established",
                "observation_to_clinical_state_compatibility_established",
            )
        ):
            raise ValueError("Local numerical rank cannot establish clinical identification")
        accepted_starts = [row for row in model["multistarts"] if row["converged"]]
        if not accepted_starts or any(
            row["direct_likelihood_gradient_verified"] is not True
            or not np.isfinite(row["projected_gradient_norm"])
            or row["projected_gradient_norm"] > settings.optimizer_gtol
            for row in accepted_starts
        ):
            raise ValueError("Invalid direct-gradient convergence claim")
        if model["log_likelihood"]["value"] != max(
            row["log_likelihood"]["value"] for row in accepted_starts
        ) or not any(
            row["rates"] == model["rates"] and row["log_likelihood"] == model["log_likelihood"]
            for row in accepted_starts
        ):
            raise ValueError("Reported fit is not an accepted best prescribed start")
        rates = model["rates"]
        if len(model["multistarts"]) != len(settings.initial_rates) or any(
            type(x) not in (float, int) or not np.isfinite(x) or not 0 <= x <= cap
            for x, cap in zip(rates, settings.rate_upper_bounds, strict=True)
        ):
            raise ValueError("Invalid fit controls or private coordinate export")
        generator = lab.generator(rates, name)
        if not np.allclose(generator.sum(axis=1), 0, atol=settings.probability_tolerance, rtol=0):
            raise ValueError("Generator does not conserve mass")
        for gap in (0.0, 1.0, 100.0):  # Numerical fixture durations, not source coordinates.
            matrix = lab.transition_matrix(
                rates, name, gap, probability_tolerance=settings.probability_tolerance
            )
            if not np.allclose(matrix.sum(axis=1), 1, atol=settings.probability_tolerance, rtol=0):
                raise ValueError("Kernel does not conserve mass")
        profiles = report["profiles"][name]
        if sorted(p["rate_index"] for p in profiles) != list(range(len(rates))) or any(
            p["finite_confidence_interval"] is not None
            or p["clinical_confidence_interval"] is not False
            for p in profiles
        ):
            raise ValueError("Invalid finite profile interval claim")
        for profile in profiles:
            _profile_contract(profile, model, settings, protocol)
        fit_checks[name] = {
            "fit_available": True,
            "generator_and_kernel_conserve_mass": True,
            "profile_count": len(profiles),
            "clinical_interval_claimed": False,
        }
    iid = report["models"]["iid"]
    if iid["fit_performed"] is not True and (
        iid["probabilities"] is not None
        or iid.get("log_likelihood") is not None
        or iid.get("failure") != "no_post_first_observations"
        or evaluation["scores"]["iid"] != {"unavailable": "no_post_first_calibration_observations"}
    ):
        raise ValueError("Unavailable IID fit retained successful results")
    joint = report["joint_uncertainty"]
    if (
        joint["repetitions_requested"] != protocol["joint_uncertainty"]["bootstrap_replicates"]
        or joint["repetitions_attempted"] != joint["repetitions_requested"]
        or joint["failed_draws_redrawn"] is not False
        or joint["rank_deficient_draws_excluded_from_covariance"] is not False
        or joint["selection_measurement_or_transport_uncertainty_included"] is not False
        or len(joint["predictive_difference_coordinates"]) != 8
    ):
        raise ValueError("Invalid joint uncertainty scope")
    summary = joint["joint_rate_summary"]
    if summary["available"]:
        _covariance_contract(summary["covariance"], 4)
    _bootstrap_contract(joint, protocol)
    proof = {
        "passed": True,
        "scope": "offline aggregate integrity and mathematical consistency; no participant replay or independent clinical validation",
        "report_sha256": hashlib.sha256(data).hexdigest(),
        "protocol_sha256": a1c.PROTOCOL_SHA256,
        "numerical_amendment_sha256": amendment_hash,
        "current_registry_sha256": registry.content_hash,
        "historical_run_registry_sha256": report["provenance"]["registry_sha256"],
        "selection_denominators_reconcile": True,
        "reported_source_pins_match_immutable_prior_artifact": True,
        "fit_checks": fit_checks,
        "joint_uncertainty_contract_checked": True,
        "clinical_acceptance_established": False,
        "engine_activation_allowed": False,
        "actual_source_replay": None,
    }
    if version2:
        proof.update(
            numerical_method=numerical_method,
            prior_empirical_result_sha256=a1c.V1_RESULT_SHA256,
            statistical_selection_changed=False,
        )
    if raw is not None:
        replay = a1c.analyze_cache(
            raw, progress=lambda message: print(message, flush=True), **numerical_keywords
        )
        if not replay["analysis_completed"]:
            raise ValueError("Frozen empirical replay failed")
        old, new = copy.deepcopy(report), copy.deepcopy(replay)
        exclusions = (
            "registry_sha256",
            "implementation_sha256",
            "laboratory_implementation_sha256",
        )
        for key in exclusions:
            old["provenance"].pop(key)
            new["provenance"].pop(key)
        if old != new:
            raise ValueError("Empirical replay differs outside explicitly named provenance")
        proof["actual_source_replay"] = {
            "full_byte_equality": data
            == (json.dumps(replay, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(),
            "remaining_payload_exactly_equal": True,
            "excluded_paths": ["/provenance/" + key for key in exclusions],
            "independent_clinical_validation": False,
        }
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--numerical-method", choices=a1c.NUMERICAL_METHODS, default="v1")
    options = parser.parse_args()
    result = assess(raw=options.raw, numerical_method=options.numerical_method)
    if options.output:
        from demeter.analysis.ipop_preflight_io import write_fresh_report

        write_fresh_report(result, options.output, options.raw or ROOT / "data/raw")
    print(json.dumps(result, indent=2, allow_nan=False))
