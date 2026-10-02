"""Audit additive predictive summaries from retained aggregate bootstrap vectors.

This reads no participant cache. It verifies summary arithmetic, not the fitting
of source records or independent predictive/clinical validity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from demeter.analysis import laboratory_bootstrap_reporting as reporting

from replay_ipop_predictive_supplement import IMPLEMENTATIONS, ROOT, contract, digest

RESULT_PATH = ROOT / "docs/validation/ipop-a1c-predictive-summary-result-v1.json"


def assess(result):
    policy, protocol, parent = contract()
    uncertainty = protocol["joint_uncertainty"]
    gates = policy["activation"]
    for key, value in gates.items():
        if result.get(key) is not value:
            raise ValueError("Scientific/engine gate differs from frozen policy")
    required = {
        "schema_version": 1,
        "analysis_id": policy["analysis_id"],
        "analysis_completed": True,
        "execution_scope": "conditional_empirical_laboratory_working_analysis",
        "validation_only": False,
        "post_outcome_reporting_amendment": True,
        "source_selection_unchanged": True,
        "full_data_fits_or_profiles_rerun": False,
        "legacy_bootstrap_summaries_reproduced_exactly": True,
        "aggregate_bootstrap_score_vectors_retained": True,
        "participant_records_or_predictions_exported": False,
    }
    for key, value in required.items():
        if type(result.get(key)) is not type(value) or result[key] != value:
            raise ValueError("Reporting scope differs from frozen policy")
    if set(result) != set(required) | set(gates) | {
        "provenance",
        "selection",
        "predictive_uncertainty",
    }:
        raise ValueError("Unexpected public result fields")
    if result["selection"] != parent["selection"]:
        raise ValueError("Selection differs from preserved parent")
    provenance = result["provenance"]
    if set(provenance) != {
        "reporting_protocol_sha256",
        "parent_result_sha256",
        "implementation_sha256",
        "freeze_commit",
        "started_at",
        "completed_at",
        "acquisition_receipts_verified",
        "source_bytes",
        "bootstrap_seed",
        "numerical_method",
        "independent_source_validation",
    }:
        raise ValueError("Unexpected public provenance fields")
    if (
        provenance["reporting_protocol_sha256"]
        != digest("docs/validation/ipop-a1c-predictive-summary-protocol-v1.json")
        or provenance["parent_result_sha256"] != policy["parent_result"]["sha256"]
    ):
        raise ValueError("Reporting or parent identity failed")
    if provenance["implementation_sha256"] != {p: digest(p) for p in IMPLEMENTATIONS}:
        raise ValueError("Reporting implementation identity failed")
    if provenance["source_bytes"] != parent["provenance"]["source_bytes"]:
        raise ValueError("Source identity failed")
    if provenance["acquisition_receipts_verified"] is not True:
        raise ValueError("Unverified acquisition")
    if provenance["independent_source_validation"] is not False:
        raise ValueError("Unsupported independent validation claim")
    if (
        type(provenance["bootstrap_seed"]) is not int
        or provenance["bootstrap_seed"] != uncertainty["seed"]
    ):
        raise ValueError("Bootstrap seed differs")
    if provenance["numerical_method"] != "exact_box_quadratic_v2":
        raise ValueError("Frozen fitting method differs")
    commit = provenance["freeze_commit"]
    if (
        type(commit) is not str
        or len(commit) != 40
        or any(c not in "0123456789abcdef" for c in commit)
    ):
        raise ValueError("Invalid freeze commit identity")
    start, end = (datetime.fromisoformat(provenance[k]) for k in ("started_at", "completed_at"))
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError("Invalid execution chronology")
    report = result["predictive_uncertainty"]
    expected_meta = {
        "schema_version": 1,
        "scope": "additive conditional predictive metric reporting",
        "coordinates": parent["joint_uncertainty"]["predictive_difference_coordinates"],
        "quantile_levels": uncertainty["quantiles"],
        "repetitions_requested": uncertainty["bootstrap_replicates"],
        "repetitions_attempted": uncertainty["bootstrap_replicates"],
        "failed_draws_redrawn": False,
        "covariance_uses_pairwise_deletion": False,
        "clinical_fit_performed": False,
        "engine_activation_allowed": False,
    }
    for key, value in expected_meta.items():
        if json.dumps(report.get(key), sort_keys=True) != json.dumps(value, sort_keys=True):
            raise ValueError("Bootstrap reporting controls differ")
    if set(report) != set(expected_meta) | {"models", "replicate_score_vectors"}:
        raise ValueError("Unexpected public uncertainty fields")
    if set(report["models"]) != {"adjacent"} or set(report["replicate_score_vectors"]) != {
        "adjacent"
    }:
        raise ValueError("Unexpected bootstrap model")
    vectors = report["replicate_score_vectors"]["adjacent"]
    if len(vectors) != uncertainty["bootstrap_replicates"]:
        raise ValueError("Requested/attempted draw closure failed")
    if any(
        set(row)
        != {
            "replicate",
            "fit_available",
            "fit_status",
            "prediction_status",
            "values",
            "coordinate_status",
        }
        for row in vectors
    ):
        raise ValueError("Unexpected public aggregate vector fields")
    reconstructed = reporting.summarize_predictive_vectors(
        vectors, quantile_levels=uncertainty["quantiles"]
    )
    if reconstructed != report["models"]["adjacent"]:
        raise ValueError("Retained aggregate vectors do not reproduce summaries")
    complete = reconstructed["complete_vector"]["summary"]
    if complete != parent["joint_uncertainty"]["predictive_difference_summaries"]["adjacent"]:
        raise ValueError("Original complete-vector summary not preserved")
    return {
        "passed": True,
        "source_records_read": False,
        "aggregate_draws_reconciled": len(vectors),
        "complete_vector_draws": reconstructed["complete_vector"]["finite_draws"],
        "metric_block_draws": {
            name: block["finite_draws"] for name, block in reconstructed["metric_blocks"].items()
        },
        "summary_arithmetic_reconstructed": True,
        "source_fitting_independently_verified": False,
        **gates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    try:
        raw = args.result.read_bytes()
        result = json.loads(raw.decode("utf-8"))
        report = {**assess(result), "result_sha256": hashlib.sha256(raw).hexdigest()}
    except Exception:
        print(json.dumps({"passed": False, "source_records_read": False}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
