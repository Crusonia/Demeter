"""Offline integrity/math audit of the conditional iPOP aggregate working report.

This does not read participant records or independently validate clinical rates.
Optional --raw replays the entire frozen empirical analysis from verified cache.
Historical report bytes remain immutable; only its registry fingerprint and
implementation provenance may differ in an explicitly reported current replay.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

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


def assess(root: Path = ROOT, raw: Path | None = None) -> dict:
    protocol = a1c.load_protocol(root / "docs/validation/ipop-a1c-working-fit-protocol-v1.json")
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    a1c._registry_contract(registry, protocol, root)
    spec = registry.datasets["ipop_a1c_working_fit"]
    data = (root / spec["result"]["path"]).read_bytes()
    report = json.loads(data)
    if (
        report["execution_scope"] != "conditional_empirical_laboratory_working_analysis"
        or report["validation_only"] is not False
        or report["analysis_completed"] is not True
        or report["provenance"]["acquisition_receipts_verified"] is not True
        or report["provenance"]["independent_source_validation"] is not False
        or any(report[key] is not False for key in GATES)
    ):
        raise ValueError("Invalid working report scope")
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
        if model["fit_performed"] is not True:
            fit_checks[name] = {"fit_available": False, "failure": model.get("failure")}
            continue
        rates = model["rates"]
        if (
            len(model["multistarts"]) != len(settings.initial_rates)
            or "gap_range_days" in model["source_support"]
            or any(
                type(x) not in (float, int) or not np.isfinite(x) or not 0 <= x <= cap
                for x, cap in zip(rates, settings.rate_upper_bounds, strict=True)
            )
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
        if len(profiles) != len(rates) or any(
            p["finite_confidence_interval"] is not None
            or p["clinical_confidence_interval"] is not False
            for p in profiles
        ):
            raise ValueError("Invalid finite profile interval claim")
        fit_checks[name] = {
            "fit_available": True,
            "generator_and_kernel_conserve_mass": True,
            "profile_count": len(profiles),
            "clinical_interval_claimed": False,
        }
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
        covariance = np.asarray(summary["covariance"])
        tolerance = protocol["numerics"]["probability_tolerance"]
        if (
            covariance.shape != (4, 4)
            or not np.isfinite(covariance).all()
            or not np.allclose(covariance, covariance.T, atol=tolerance, rtol=0)
            or np.linalg.eigvalsh(covariance).min() < -tolerance
        ):
            raise ValueError("Invalid joint covariance")
    proof = {
        "passed": True,
        "scope": "offline aggregate integrity and mathematical consistency; no participant replay or independent clinical validation",
        "report_sha256": hashlib.sha256(data).hexdigest(),
        "protocol_sha256": a1c.PROTOCOL_SHA256,
        "current_registry_sha256": registry.content_hash,
        "historical_run_registry_sha256": report["provenance"]["registry_sha256"],
        "selection_denominators_reconcile": True,
        "fit_checks": fit_checks,
        "joint_uncertainty_contract_checked": True,
        "clinical_acceptance_established": False,
        "engine_activation_allowed": False,
        "actual_source_replay": None,
    }
    if raw is not None:
        replay = a1c.analyze_cache(raw, progress=lambda message: print(message, flush=True))
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
    options = parser.parse_args()
    result = assess(raw=options.raw)
    if options.output:
        from demeter.analysis.ipop_preflight_io import write_fresh_report

        write_fresh_report(result, options.output, options.raw or ROOT / "data/raw")
    print(json.dumps(result, indent=2, allow_nan=False))
