"""Frozen native iPOP A1C working analysis; never a clinical/engine adapter.

Complete immutable source identity precedes parsing. Participant labels, paths,
values, day coordinates and allocation hashes remain ephemeral and private.
Only aggregate source/selection, working-fit and predictive diagnostics escape.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal, DecimalException, localcontext
from math import isfinite
from pathlib import Path

import numpy as np
from scipy.stats import chi2

from demeter.analysis import ipop_crosswalk as v2
from demeter.analysis import ipop_preflight as v1
from demeter.analysis import laboratory_panel as lab

PROTOCOL_PATH = (
    Path(__file__).resolve().parents[3] / "docs/validation/ipop-a1c-working-fit-protocol-v1.json"
)
PROTOCOL_SHA256 = "9b7473bb2454934ba82ef9d80c41c4d94a06c8b5eeadbf029f99aacec60e8ea7"
CANONICAL_SHA256 = "36212ff71b040d35a5e6bd2d36200de7175a050ad2a86200a59be4680dc947ba"
REGISTRY_SELECTION_SHA256 = "34d604ee36ca0b24845db5eb4c9c521a2503b9ed98728e73005cea7c8bf55be3"
NUMERICAL_PROTOCOL_PATH = PROTOCOL_PATH.with_name("ipop-a1c-numerical-amendment-v1.json")
NUMERICAL_PROTOCOL_SHA256 = "11f492eeea19cf8ab9bcc0f5ce58c012ff93e99c1b9057340f87bbf307bb4a42"
NUMERICAL_V2_PATH = PROTOCOL_PATH.with_name("ipop-a1c-numerical-amendment-v2.json")
NUMERICAL_V2_SHA256 = "8f03d5a0f7377d843099b6dbacc2f5fa66c3311aa77cdcf705c74f6d5d0865d0"
V1_RESULT_SHA256 = "e44528ab04a13db4f8c30cf2365e86959aa13962a205a65b982615cfe61b9ced"
NUMERICAL_METHODS = ("v1", "exact_box_quadratic_v2")
REGISTRY_V2_SHA256 = "d97fbc6cb135075c4bab6c315d7c59ea7e5941d315ec33bc6a22b7ce83f0d09b"
ROW_KINDS = ("unusable_day", "unavailable_assay", "outside_percent_range", "eligible_assay_day")
LABEL_KINDS = (
    "no_eligible_observation",
    "repeated_eligible_time",
    "coordinate_conversion_loss",
    "one_observation",
    "multiple_observations",
)


def load_protocol(path: Path = PROTOCOL_PATH) -> dict:
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
            raise ValueError
        protocol = json.loads(raw.decode("utf-8"), object_pairs_hook=v1._unique_json)
        _contract(protocol)
        return protocol
    except Exception:
        raise ValueError("frozen_contract") from None


def load_numerical_protocol(path: Path | None = None, *, numerical_method: str = "v1") -> dict:
    try:
        if numerical_method not in NUMERICAL_METHODS:
            raise ValueError
        expected_hash = (
            NUMERICAL_PROTOCOL_SHA256 if numerical_method == "v1" else NUMERICAL_V2_SHA256
        )
        if path is None:
            path = NUMERICAL_PROTOCOL_PATH if numerical_method == "v1" else NUMERICAL_V2_PATH
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError
        policy = json.loads(raw.decode("utf-8"), object_pairs_hook=v1._unique_json)
        if policy["parent_protocol_sha256"] != PROTOCOL_SHA256:
            raise ValueError
        return policy
    except Exception:
        raise ValueError("frozen_numerical_contract") from None


def _contract(protocol: dict) -> None:
    if type(protocol) is not dict or v1._canonical_sha256(protocol) != CANONICAL_SHA256:
        raise ValueError("frozen_contract")


def _registry_contract(
    registry, protocol: dict, root: Path, *, numerical_method: str = "v1"
) -> None:
    """Reject drift in the evidence description before reading participant bytes.

    A post-analysis result binding is allowed only as explicit historical
    registration, with an immutable report matching the frozen selection and
    the registered conditional parameter vector. It is never engine promotion.
    """
    try:
        dataset = copy.deepcopy(registry.datasets["ipop_a1c_working_fit"])
        result = dataset.pop("result", None)
        rates = dataset["working_rate_parameters"]["value"]
        estimation_status = dataset["working_rate_parameters"]["estimation_status"]
        if result is not None:
            if (
                set(result)
                not in (
                    {"path", "sha256", "estimated_parameters"},
                    {"path", "sha256", "estimated_parameters", "estimated_parameter_metadata"},
                )
                or result["path"] != "docs/validation/ipop-a1c-working-result-v1.json"
                or estimation_status
                != (
                    "conditional_analysis_completed_primary_estimate_unresolved"
                    if rates is None
                    else "conditional_working_fit_completed_clinical_use_unresolved"
                )
            ):
                raise ValueError
            raw = (root / result["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != result["sha256"]:
                raise ValueError
            report = json.loads(raw.decode("utf-8"), object_pairs_hook=v1._unique_json)
            expected_estimates = {
                "primary_rates_per_source_day": report["models"]["adjacent"]["rates"],
                "general_rates_per_source_day": report["models"]["unrestricted"]["rates"],
                "iid_followup_band_probabilities": report["models"]["iid"]["probabilities"],
            }
            _estimate_metadata_contract(result)
            if (
                report["analysis_completed"] is not True
                or report["provenance"]["protocol_sha256"] != PROTOCOL_SHA256
                or report["models"]["adjacent"]["rates"] != rates
                or v1._canonical_sha256(result["estimated_parameters"])
                != v1._canonical_sha256(expected_estimates)
                or any(
                    report[k] is not False
                    for k in (
                        "clinical_fit_performed",
                        "diagnosis_or_remission_inference_performed",
                        "death_or_censoring_inference_performed",
                        "dietary_effect_estimated",
                        "national_transport_established",
                        "engine_activation_allowed",
                        "scientific_acceptance_changed",
                    )
                )
            ):
                raise ValueError
        elif rates is not None or estimation_status != "unresolved_before_frozen_analysis":
            raise ValueError
        dataset["working_rate_parameters"]["value"] = None
        dataset["working_rate_parameters"]["estimation_status"] = (
            "unresolved_before_frozen_analysis"
        )
        if v1._canonical_sha256(dataset) != REGISTRY_SELECTION_SHA256:
            raise ValueError
        source = protocol["source"]
        for role, filename, name in (
            ("clinical", "clinical_tests.txt", "clinical_sha256"),
            ("sample_info", "SampleInfo.csv", "sample_info_sha256"),
        ):
            registered = registry.sources[
                "ipop2022_" + ("clinical_tests" if role == "clinical" else "sample_info")
            ]
            url = (
                "https://raw.githubusercontent.com/gmiaslab/TemporalMultiomicsDiabetes/"
                + source["producer_commit"]
                + "/data/"
                + filename
            )
            if (
                registered.sha256 != source[name]
                or registered.url != url
                or registered.raw_filename != filename
            ):
                raise ValueError
        if numerical_method == "exact_box_quadratic_v2":
            _registry_v2_contract(registry, root)
        elif numerical_method != "v1":
            raise ValueError
    except Exception:
        raise ValueError("registry_contract") from None


def _estimate_metadata_contract(result: dict) -> None:
    metadata = result.get("estimated_parameter_metadata")
    if metadata is None:
        return
    orders = {
        "primary_rates_per_source_day": [
            "band0_to_band1",
            "band1_to_band0",
            "band1_to_band2",
            "band2_to_band1",
        ],
        "general_rates_per_source_day": [
            "band0_to_band1",
            "band1_to_band0",
            "band1_to_band2",
            "band2_to_band1",
            "band0_to_band2",
            "band2_to_band0",
        ],
        "iid_followup_band_probabilities": ["band0", "band1", "band2"],
    }
    if set(metadata) != set(orders):
        raise ValueError
    for key, order in orders.items():
        item = metadata[key]
        if (
            item["status"] != "estimated"
            or item["evidence_grade"] != "D"
            or item["clinical_use_allowed"] is not False
            or item["order"] != order
            or item["unit"]
            != ("probability" if key.startswith("iid_") else "reciprocal source day")
            or not item["conditioning"]
            or not item["uncertainty"]
        ):
            raise ValueError


def _registry_v2_contract(registry, root: Path) -> None:
    """Separate adaptive numerical attempt; original source selection stays frozen."""
    spec = copy.deepcopy(registry.datasets["ipop_a1c_working_fit_v2"])
    policy = load_numerical_protocol(
        root / "docs/validation/ipop-a1c-numerical-amendment-v2.json",
        numerical_method="exact_box_quadratic_v2",
    )
    prior = (root / policy["prior_empirical_result_path"]).read_bytes()
    if hashlib.sha256(prior).hexdigest() != V1_RESULT_SHA256:
        raise ValueError
    result = spec.pop("result", None)
    working = spec["working_rate_parameters"]
    if result is not None:
        if set(result) not in (
            {"path", "sha256", "estimated_parameters"},
            {"path", "sha256", "estimated_parameters", "estimated_parameter_metadata"},
        ):
            raise ValueError
        raw = (root / result["path"]).read_bytes()
        if (
            result["path"] != "docs/validation/ipop-a1c-working-result-v2.json"
            or hashlib.sha256(raw).hexdigest() != result["sha256"]
        ):
            raise ValueError
        report = json.loads(raw.decode("utf-8"), object_pairs_hook=v1._unique_json)
        estimates = {
            "primary_rates_per_source_day": report["models"]["adjacent"]["rates"],
            "general_rates_per_source_day": report["models"]["unrestricted"]["rates"],
            "iid_followup_band_probabilities": report["models"]["iid"]["probabilities"],
        }
        _estimate_metadata_contract(result)
        if (
            report["analysis_completed"] is not True
            or report["validation_only"] is not False
            or report["execution_scope"] != "conditional_empirical_laboratory_working_analysis"
            or report["analysis_id"] != "ipop_a1c_conditional_working_fit_v2"
            or report["provenance"]["acquisition_receipts_verified"] is not True
            or report["provenance"]["protocol_sha256"] != PROTOCOL_SHA256
            or report["provenance"]["source_bytes"]
            != json.loads(prior)["provenance"]["source_bytes"]
            or report["provenance"]["numerical_amendment_sha256"] != NUMERICAL_V2_SHA256
            or report["provenance"]["prior_empirical_result_sha256"] != V1_RESULT_SHA256
            or report["provenance"].get("numerical_method") != "exact_box_quadratic_v2"
            or report["provenance"].get("statistical_selection_changed") is not False
            or any(
                report["models"][name].get("numerical_method") != "exact_box_quadratic_v2"
                for name in ("adjacent", "unrestricted")
            )
            or report["joint_uncertainty"].get("numerical_method") != "exact_box_quadratic_v2"
            or any(
                profile.get("numerical_method") != "exact_box_quadratic_v2"
                for profiles in report["profiles"].values()
                for profile in profiles or ()
            )
            or report["selection"] != json.loads(prior)["selection"]
            or working["value"] != estimates["primary_rates_per_source_day"]
            or result["estimated_parameters"] != estimates
            or working["estimation_status"]
            != (
                "conditional_analysis_completed_primary_estimate_unresolved"
                if working["value"] is None
                else "conditional_working_fit_completed_clinical_use_unresolved"
            )
            or any(
                report[key] is not False
                for key in (
                    "clinical_fit_performed",
                    "diagnosis_or_remission_inference_performed",
                    "death_or_censoring_inference_performed",
                    "dietary_effect_estimated",
                    "national_transport_established",
                    "engine_activation_allowed",
                    "scientific_acceptance_changed",
                )
            )
        ):
            raise ValueError
    elif (
        working["value"] is not None
        or working["estimation_status"] != "unresolved_before_frozen_analysis"
    ):
        raise ValueError
    working["value"] = None
    working["estimation_status"] = "unresolved_before_frozen_analysis"
    if v1._canonical_sha256(spec) != REGISTRY_V2_SHA256:
        raise ValueError


def _admitted(clinical, samples):
    """Reapply all v2 graph edges before assay selection; never export a crosswalk."""
    right, left_partners, right_partners = defaultdict(list), defaultdict(set), defaultdict(set)
    for row in samples:
        if v1._key_kind(row.sample) == "nonempty":
            right[row.sample].append(row)
    for row in clinical:
        if v1._key_kind(row.visit) != "nonempty" or v1._key_kind(row.subject) != "nonempty":
            continue
        for sample in right.get(row.visit, ()):
            if v1._key_kind(sample.subject) == "nonempty":
                left_partners[row.subject].add(sample.subject)
                right_partners[sample.subject].add(row.subject)
    admitted = []
    for row in clinical:
        if v1._key_kind(row.visit) != "nonempty" or v1._key_kind(row.subject) != "nonempty":
            continue
        matches = right.get(row.visit, ())
        if len(matches) != 1:
            continue
        sample = matches[0]
        if (
            v1._key_kind(sample.subject) == "nonempty"
            and len(left_partners[row.subject]) == 1
            and len(right_partners[sample.subject]) == 1
        ):
            admitted.append((row, sample))
    return admitted


def _partition(label: str, protocol: dict) -> str:
    allocation = protocol["allocation"]
    digest = hashlib.sha256((allocation["salt"] + "\0" + label).encode("utf-8")).digest()
    return (
        "evaluation"
        if int.from_bytes(digest, "big") % allocation["modulus"]
        == allocation["evaluation_remainder"]
        else "calibration"
    )


def _centered(days):
    # Exact subtraction precision accounts for both endpoints' complete decimal
    # representations. Reject an excessive/unrepresentable domain rather than
    # collapsing two distinct source times or inventing a spacing.
    exponent = min(x.as_tuple().exponent for x in days)
    precision = max(x.adjusted() for x in days) - exponent + 3
    if precision > 10000:
        raise ValueError("coordinate_conversion_loss")
    with localcontext() as context:
        context.prec = max(precision, 28)
        centered = tuple(float(x - days[0]) for x in days)
    if any(not isfinite(x) for x in centered) or any(
        b <= a or not isfinite(b - a) for a, b in zip(centered, centered[1:], strict=False)
    ):
        raise ValueError("coordinate_conversion_loss")
    return centered


def _prepare(
    clinical_bytes: bytes,
    sample_bytes: bytes,
    protocol: dict,
    *,
    validation_only: bool,
    crosswalk_protocol: dict,
):
    """Private selection. Returns ephemeral paths plus identifier-free counts."""
    _contract(protocol)
    if type(validation_only) is not bool:
        raise ValueError("execution_mode")
    audit = v2.preflight_crosswalk_bytes(
        clinical_bytes, sample_bytes, protocol=crosswalk_protocol, validation_only=validation_only
    )
    if audit["source_audit"]["passed"] is not True:
        raise ValueError("binding_source_audit")
    if not validation_only and any(
        hashlib.sha256(data).hexdigest() != protocol["source"][name]
        for name, data in (
            ("clinical_sha256", clinical_bytes),
            ("sample_info_sha256", sample_bytes),
        )
    ):
        raise ValueError("source_identity")
    clinical = v1._parse_clinical(v1._records(clinical_bytes, v1.CLINICAL_HEADER, "\t"))
    samples = v1._parse_samples(v1._records(sample_bytes, v1.SAMPLE_HEADER, ","))
    admitted = _admitted(clinical, samples)
    if len(admitted) != audit["linkage"]["ordered_partition"][v2.ASSOCIATION_KINDS[-1]]:
        raise ValueError("association_reconciliation")
    lower, upper = (Decimal(str(x)) for x in protocol["measurement"]["thresholds"])
    low_bound, high_bound = (Decimal(str(x)) for x in protocol["measurement"]["percentage_bounds"])
    rows, assay_tokens, grouped = (
        Counter({k: 0 for k in ROW_KINDS}),
        Counter({k: 0 for k in v1.TOKEN_KINDS}),
        defaultdict(list),
    )
    partitions = {
        name: {
            "admitted_labels": 0,
            "label_partition": {k: 0 for k in LABEL_KINDS},
            "eligible_rows": 0,
        }
        for name in ("calibration", "evaluation")
    }
    bands = [0, 0, 0]
    for row, sample in admitted:
        grouped.setdefault(sample.subject, [])
        assay_tokens[row.a1c.kind] += 1
        if sample.day.value is None:
            kind = ROW_KINDS[0]
        elif row.a1c.value is None:
            kind = ROW_KINDS[1]
        elif not low_bound <= row.a1c.value <= high_bound:
            kind = ROW_KINDS[2]
        else:
            kind = ROW_KINDS[3]
            band = 0 if row.a1c.value < lower else 1 if row.a1c.value < upper else 2
            bands[band] += 1
            grouped[sample.subject].append((sample.day.value, band))
        rows[kind] += 1
    paths = {name: [] for name in partitions}
    for label in sorted(grouped):
        name = _partition(label, protocol)
        group = sorted(grouped[label])
        counts = partitions[name]
        counts["admitted_labels"] += 1
        counts["eligible_rows"] += len(group)
        if not group:
            kind = LABEL_KINDS[0]
        elif len({day for day, _ in group}) != len(group):
            kind = LABEL_KINDS[1]
        else:
            try:
                path = lab.PanelPath(
                    _centered(tuple(day for day, _ in group)), tuple(band for _, band in group)
                )
            except (ValueError, OverflowError, DecimalException):
                kind = LABEL_KINDS[2]
            else:
                kind = LABEL_KINDS[3] if len(group) == 1 else LABEL_KINDS[4]
                paths[name].append(path)
        counts["label_partition"][kind] += 1
    if (
        sum(rows.values()) != len(admitted)
        or sum(assay_tokens.values()) != len(admitted)
        or sum(p["admitted_labels"] for p in partitions.values()) != len(grouped)
        or sum(p["eligible_rows"] for p in partitions.values()) != rows[ROW_KINDS[3]]
        or sum(bands) != rows[ROW_KINDS[3]]
        or any(
            sum(p["label_partition"].values()) != p["admitted_labels"] for p in partitions.values()
        )
    ):
        raise ValueError("selection_reconciliation")
    coverage = {
        "full_source_structure": audit["source_structure"],
        "full_source_linkage": audit["linkage"],
        "full_namespace_consistency": audit["namespace_consistency"],
        "denominator_admitted_rows": len(admitted),
        "admitted_row_partition": dict(rows),
        "admitted_assay_token_categories": dict(assay_tokens),
        "eligible_band_counts": bands,
        "denominator_admitted_labels": len(grouped),
        "partitions": partitions,
        "coordinate_values_or_individual_paths_exported": False,
        "participant_identity_verified": False,
        "assay_units_rawness_specimen_clock_verified": False,
    }
    return (
        {name: tuple(value) for name, value in paths.items()},
        coverage,
        audit["provenance"]["source_bytes"],
    )


def settings_for(protocol: dict, structure: str) -> lab.FitSettings:
    _contract(protocol)
    n = protocol["numerics"]
    size = len(lab.EDGES[structure])
    starts = tuple((x,) * size for x in n["constant_starts_per_source_day"])
    starts += tuple(
        tuple(pair[i % 2] for i in range(size)) for pair in n["alternating_starts_per_source_day"]
    )
    return lab.FitSettings(
        structure,
        starts,
        (n["rate_cap_per_source_day"],) * size,
        n["day_scale"],
        n["probability_tolerance"],
        n["optimizer_maxiter"],
        n["optimizer_ftol"],
        n["optimizer_gtol"],
        n["design_jacobian_scaled_coordinate_step"],
        n["design_svd_relative_tolerance"],
    )


def _without_coordinates(model: dict) -> dict:
    # Generic numerical APIs may report aggregate elapsed ranges; the empirical
    # public contract is narrower and exports no original coordinate/gap values.
    if "source_support" in model:
        model["source_support"].pop("gap_range_days", None)
    return model


def analyze_bytes(
    clinical_bytes: bytes,
    sample_bytes: bytes,
    *,
    protocol: dict,
    validation_only: bool = True,
    crosswalk_protocol: dict | None = None,
    progress=None,
    numerical_method: str = "v1",
) -> dict:
    """Fit the frozen working analysis, returning sanitized aggregates only.

    Synthetic mode permits only the existing v2 four identity-pin substitutions;
    selection/model/evaluation/numerical rules remain the identical frozen contract.
    Empirical receipt verification is separately mandatory in analyze_cache.
    """
    report = {
        "analysis_id": (
            "ipop_a1c_conditional_working_fit_v1"
            if numerical_method == "v1"
            else "ipop_a1c_conditional_working_fit_v2"
        ),
        "execution_scope": "synthetic_software_validation_only"
        if validation_only is True
        else "conditional_empirical_laboratory_working_analysis"
        if validation_only is False
        else "invalid_execution_mode",
        "validation_only": validation_only if type(validation_only) is bool else None,
        "analysis_completed": False,
        "failure_stage": None,
        "selection": None,
        "models": None,
        "profiles": None,
        "internal_evaluation": None,
        "joint_uncertainty": None,
        "provenance": None,
        "clinical_fit_performed": False,
        "diagnosis_or_remission_inference_performed": False,
        "death_or_censoring_inference_performed": False,
        "dietary_effect_estimated": False,
        "national_transport_established": False,
        "engine_activation_allowed": False,
        "scientific_acceptance_changed": False,
    }
    stage = "frozen_contract"
    try:
        _contract(protocol)
        load_numerical_protocol(numerical_method=numerical_method)
        numerical_keywords = (
            {} if numerical_method == "v1" else {"numerical_method": numerical_method}
        )
        stage = "source_selection"
        paths, coverage, source_bytes = _prepare(
            clinical_bytes,
            sample_bytes,
            protocol,
            validation_only=validation_only,
            crosswalk_protocol=crosswalk_protocol or v2.load_frozen_crosswalk_protocol(),
        )
        training, evaluation = paths["calibration"], paths["evaluation"]
        stage = "empty_calibration_or_evaluation_partition"
        if not training or not evaluation:
            raise ValueError
        configurations = {
            name: settings_for(protocol, name) for name in ("adjacent", "unrestricted")
        }
        models, profiles, scores = {}, {}, {}
        for name, settings in configurations.items():
            stage = "working_ctmc_fit"
            if progress:
                progress("Fitting frozen " + name + " laboratory process")
            fitted = models[name] = _without_coordinates(
                lab.fit_ctmc(training, settings, **numerical_keywords)
            )
            if not fitted["fit_performed"]:
                profiles[name], scores[name] = None, {"unavailable": "no_converged_working_fit"}
                continue
            stage = "working_profiles"
            grid_spec = protocol["numerics"]["profile_grid"]
            base_grid = [0.0] + np.logspace(
                grid_spec["log10_min_per_source_day"],
                grid_spec["log10_max_per_source_day"],
                grid_spec["points"],
            ).tolist()
            profiles[name] = [
                lab.profile_rate(
                    training,
                    fitted,
                    settings,
                    i,
                    sorted(set(base_grid + [rate])),
                    support_cutoff=float(
                        chi2.ppf(protocol["numerics"]["nominal_profile_support_probability"], 1)
                    ),
                    **numerical_keywords,
                )
                for i, rate in enumerate(fitted["rates"])
            ]
            stage = "internal_prediction"
            scores[name] = lab.score_predictions(
                evaluation, fitted, probability_tolerance=settings.probability_tolerance
            )
        models["iid"] = lab.fit_iid(training)
        models["persistence"] = lab.no_switching_null(training)
        stage = "internal_prediction"
        for name in ("iid", "persistence"):
            scores[name] = (
                lab.score_predictions(
                    evaluation,
                    models[name],
                    probability_tolerance=protocol["numerics"]["probability_tolerance"],
                )
                if name == "persistence" or models[name]["fit_performed"]
                else {"unavailable": "no_post_first_calibration_observations"}
            )
        stage = "joint_path_uncertainty"
        if progress:
            progress("Resampling frozen whole-label paths; retaining all failed draws")
        uncertainty = protocol["joint_uncertainty"]
        joint = lab.paired_path_bootstrap(
            training,
            {"adjacent": configurations["adjacent"]},
            repetitions=uncertainty["bootstrap_replicates"],
            seed=uncertainty["seed"],
            quantile_levels=uncertainty["quantiles"],
            evaluation_paths=evaluation,
            include_iid=True,
            **numerical_keywords,
        )
        # Bootstrap draws contain only fitted aggregate model vectors/scores, not
        # source rows. Add explicit failure/boundary/cap counts, including all draws.
        records = joint["replicates"]
        joint["dispositions"] = {
            "requested": uncertainty["bootstrap_replicates"],
            "attempted": len(records),
            "failed_primary_fits": sum("adjacent" in r["failures"] for r in records),
            "primary_zero_boundary_draws": sum(
                bool(r["models"]["adjacent"].get("zero_rate_indices")) for r in records
            ),
            "primary_computational_cap_draws": sum(
                bool(r["models"]["adjacent"].get("search_cap_indices")) for r in records
            ),
            "primary_rank_deficient_draws": sum(
                (r["models"]["adjacent"].get("identification") or {}).get(
                    "full_column_rank_at_point"
                )
                is False
                for r in records
            ),
            "primary_identification_unavailable_draws": sum(
                r["models"]["adjacent"].get("fit_performed") is True
                and (r["models"]["adjacent"].get("identification") or {}).get("available")
                is not True
                for r in records
            ),
            "paired_prediction_unavailable_draws": sum(
                r["prediction_status"].get("adjacent") != "performed_finite" for r in records
            ),
            "nominal_percentile_resolution": 1 / uncertainty["bootstrap_replicates"],
        }
        # Raw bootstrap vectors are model draws, not participant data. Publishing
        # summaries is sufficient and keeps the public report compact.
        joint.pop("replicates")
        stage = "aggregate_publication"
        report.update(
            analysis_completed=True,
            selection=coverage,
            models=models,
            profiles=profiles,
            internal_evaluation={
                "kind": protocol["evaluation"]["kind"],
                "clinical_acceptance_tolerance": None,
                "scores": scores,
            },
            joint_uncertainty=joint,
            provenance={
                "protocol_sha256": PROTOCOL_SHA256,
                "numerical_amendment_sha256": (
                    NUMERICAL_PROTOCOL_SHA256 if numerical_method == "v1" else NUMERICAL_V2_SHA256
                ),
                "supplied_protocol_canonical_sha256": CANONICAL_SHA256,
                "source_bytes": source_bytes,
                "binding_v1_protocol_sha256": v1.PROTOCOL_SHA256,
                "binding_v2_protocol_sha256": v2.PROTOCOL_SHA256,
                "prior_v2_result_sha256": protocol["source"]["prior_v2_result_sha256"],
                "acquisition_receipts_verified": False,
                "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "laboratory_implementation_sha256": hashlib.sha256(
                    Path(lab.__file__).read_bytes()
                ).hexdigest(),
                "assumptions": protocol["conditioning"],
                "independent_source_validation": False,
            },
        )
        if numerical_method != "v1":
            report["provenance"].update(
                numerical_method=numerical_method,
                prior_empirical_result_sha256=V1_RESULT_SHA256,
                statistical_selection_changed=False,
            )
        json.dumps(report, allow_nan=False)
        return report
    except Exception:
        # Do not expose source tokens, paths, intermediate selected outcomes or
        # numerical exception payloads after an incomplete atomic computation.
        return {
            **report,
            "failure_stage": stage,
            "analysis_completed": False,
            "selection": None,
            "models": None,
            "profiles": None,
            "internal_evaluation": None,
            "joint_uncertainty": None,
            "provenance": None,
        }


def analyze_cache(raw_directory: Path, *, progress=None, numerical_method: str = "v1") -> dict:
    from demeter.data.ipop import load_sources
    from demeter.schema import EvidenceRegistry

    protocol = load_protocol()  # Frozen contracts before cache access.
    load_numerical_protocol(numerical_method=numerical_method)
    root = Path(__file__).resolve().parents[3]
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    _registry_contract(registry, protocol, root, numerical_method=numerical_method)
    acquisition = load_sources(raw_directory, v1.load_frozen_protocol())
    if acquisition["passed"]:
        sources = acquisition["sources"]
        report = analyze_bytes(
            sources["clinical"],
            sources["sample_info"],
            protocol=protocol,
            validation_only=False,
            progress=progress,
            numerical_method=numerical_method,
        )
        if report["analysis_completed"]:
            report["provenance"]["acquisition_receipts_verified"] = True
            report["provenance"]["registry_sha256"] = registry.content_hash
    else:
        report = analyze_bytes(
            b"", b"", protocol=protocol, validation_only=False, numerical_method=numerical_method
        )
        report["failure_stage"] = "acquisition_receipts_or_cached_bytes"
    report["acquisition_audit"] = {
        key: acquisition[key] for key in ("passed", "receipt_saved", "provenance")
    }
    return report
