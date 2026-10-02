"""Synthetic witnesses for a source/engine mismatch, without a clinical effect fit."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from demeter.data.ingest import digest
from demeter.data.nhanes import encoded, storage_numbers
from demeter.health.transitions import STATES, transition_survivors
from demeter.nutrition.response import relax
from demeter.schema import EvidenceRegistry

DATASET = "reus_pathway_compatibility"
REFERENCES = (
    "h_to_ir_rate",
    "ir_to_h_rate",
    "ir_to_t2d_rate",
    "initial_healthy_share",
    "initial_ir_share",
    "beta_upf_progression",
    "diet_lag_years",
)
HELPERS = (
    "src/demeter/health/transitions.py",
    "src/demeter/nutrition/response.py",
)
FUNCTIONS = (
    "demeter.health.transitions.transition_survivors",
    "demeter.nutrition.response.relax",
)


def _reference_definitions(registry: EvidenceRegistry) -> dict:
    definitions = {}
    for key in REFERENCES:
        parameter = registry.parameters.get(key)
        if (
            parameter is None
            or parameter.status != "synthetic"
            or parameter.evidence_grade != "E"
            or parameter.value is None
            or parameter.unresolved
        ):
            raise ValueError("Compatibility references must be resolved synthetic/E fixtures")
        definitions[key] = parameter.model_dump(mode="json")
    return definitions


def _positive(value, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"Invalid synthetic {label}")
    return float(value)


def analyze_compatibility(registry: EvidenceRegistry, analysis: dict) -> dict:
    """Use only registered synthetic references; no trial effect is an input.

    This lower-level function permits synthetic test fixtures. The public audit
    verifies the frozen metadata and helper bytes before calling it.
    """
    _reference_definitions(registry)
    if (
        analysis["status"] != "synthetic"
        or analysis["evidence_grade"] != "E"
        or analysis["model_role"] != "benchmark_only"
        or tuple(analysis["registry_references"]) != REFERENCES
        or tuple(analysis["functions"]) != FUNCTIONS
        or analysis["diagnostic_years"] != [1, 2]
        or any(type(year) is not int for year in analysis["diagnostic_years"])
    ):
        raise ValueError("Unsupported synthetic compatibility definition")
    scale = _positive(analysis["counterexample_scale"], "counterexample scale")
    population = _positive(analysis["population_scale"], "population scale")
    tolerance = _positive(analysis["absolute_tolerance"], "absolute tolerance")
    relative = analysis["relative_upf_fixture"]
    if (
        scale <= 1
        or isinstance(relative, bool)
        or not isinstance(relative, (int, float))
        or not math.isfinite(relative)
        or relative < 0
        or relative == 1
        or analysis["relative_tolerance"] != 0
    ):
        raise ValueError("Invalid synthetic dose/scale or relative tolerance")
    values = {key: _positive(registry.value(key), key) for key in REFERENCES}
    a, r, d = (values[key] for key in REFERENCES[:3])
    h, ir = (values[key] for key in REFERENCES[3:5])
    beta, tau = (values[key] for key in REFERENCES[5:])
    initial = np.array([[population * h / (h + ir), population * ir / (h + ir), 0.0]])
    if not np.isfinite(initial).all():
        raise ValueError("Synthetic composition exceeds numerical capacity")

    rates_a = (a, r, d / scale)
    total_a = rates_a[1] + rates_a[2]
    total_b = scale * total_a
    if not all(math.isfinite(value) and value > 0 for value in (total_a, total_b)):
        raise ValueError("Synthetic counterexample exceeds numerical capacity")
    probability = rates_a[2] / total_a * -math.expm1(-total_a)
    d_b = probability * total_b / -math.expm1(-total_b)
    rates_b = (a, total_b - d_b, d_b)
    rates_c = (a * scale, rates_a[1], rates_a[2])
    if not all(math.isfinite(v) and v >= 0 for rates in (rates_a, rates_b, rates_c) for v in rates):
        raise ValueError("Synthetic counterexample exceeds numerical capacity")

    def agrees(left, right) -> bool:
        return bool(np.allclose(left, right, atol=tolerance, rtol=0))

    def run(rates: tuple[float, float, float]) -> dict:
        current = initial.copy()
        years = []
        for year in analysis["diagnostic_years"]:
            # This is one already-eligible survivor batch; index 0 is not an age estimate.
            current, flows = transition_survivors(current, *rates, adult_age=0)
            if not np.isfinite(current).all() or not all(math.isfinite(v) for v in flows.values()):
                raise ValueError("Synthetic endpoint exceeds numerical capacity")
            years.append(
                {
                    "year": year,
                    "stocks": dict(zip(STATES, map(float, current[0]), strict=True)),
                    "new_t2d_entries": flows["ir_to_t2d"],
                    "transition_flows": flows,
                    "conserved": agrees(current.sum(), population),
                    "nonnegative": bool((current >= 0).all())
                    and all(v >= 0 for v in flows.values()),
                }
            )
        return {"hazards_per_year": list(rates), "years": years}

    endpoint_cases = {"A": run(rates_a), "B": run(rates_b), "C": run(rates_c)}
    reference, structural_null = run((a, r, d)), run((a, r, d))
    first = [endpoint_cases[key]["years"][0] for key in endpoint_cases]
    second = [endpoint_cases[key]["years"][1] for key in endpoint_cases]
    analytic = float(initial[0, 1]) * probability
    checks = {
        "analytic_one_year_entries_match_operator": all(
            agrees(row["new_t2d_entries"], analytic) for row in first
        ),
        "matched_one_year_endpoint": all(
            agrees(row["new_t2d_entries"], first[0]["new_t2d_entries"]) for row in first[1:]
        ),
        "distinct_one_year_transient_stocks": all(
            not agrees(list(row["stocks"].values())[:2], list(first[0]["stocks"].values())[:2])
            for row in first[1:]
        ),
        "distinct_second_year_entries": all(
            not agrees(row["new_t2d_entries"], second[0]["new_t2d_entries"]) for row in second[1:]
        ),
        "stocks_and_flows_conserved_and_nonnegative": all(
            row["conserved"] and row["nonnegative"]
            for case in [*endpoint_cases.values(), reference, structural_null]
            for row in case["years"]
        ),
        "identical_hazard_null_reproduces_reference": structural_null == reference,
    }

    delta = relative - 1
    alternative_tau = scale * tau
    if not math.isfinite(alternative_tau):
        raise ValueError("Synthetic response exceeds numerical capacity")
    alternative_beta = beta * -math.expm1(-1 / tau) / -math.expm1(-1 / alternative_tau)
    response_inputs = {
        "reference": (beta, delta, tau),
        "rescaled_dose_coefficient": (scale * beta, delta / scale, tau),
        "rescaled_lag_coefficient": (alternative_beta, delta, alternative_tau),
        "zero_response_null": (beta, 0.0, tau),
    }
    response_cases = {}
    for key, (coefficient, dose, lag) in response_inputs.items():
        if not all(math.isfinite(v) for v in (coefficient, dose, lag, coefficient * dose)):
            raise ValueError("Synthetic response exceeds numerical capacity")
        log_response = 0.0
        rows = []
        for year in analysis["diagnostic_years"]:
            log_response = relax(log_response, coefficient * dose, lag, dt=1)
            try:
                multiplier = math.exp(log_response)
            except OverflowError as exc:
                raise ValueError("Synthetic response exceeds numerical capacity") from exc
            if not math.isfinite(multiplier):
                raise ValueError("Synthetic response exceeds numerical capacity")
            rows.append(
                {
                    "year": year,
                    "log_response": log_response,
                    "multiplier": multiplier,
                    "matches_closed_form": agrees(
                        log_response, coefficient * dose * -math.expm1(-year / lag)
                    ),
                }
            )
        response_cases[key] = {
            "beta": coefficient,
            "dose_delta": dose,
            "lag_years": lag,
            "years": rows,
        }
    response_reference = response_cases["reference"]["years"]
    dose_alternative = response_cases["rescaled_dose_coefficient"]["years"]
    lag_alternative = response_cases["rescaled_lag_coefficient"]["years"]
    checks.update(
        {
            "relax_matches_closed_form": all(
                row["matches_closed_form"]
                for case in response_cases.values()
                for row in case["years"]
            ),
            "dose_coefficient_rescaling_matches_both_years": all(
                agrees(left["log_response"], right["log_response"])
                for left, right in zip(response_reference, dose_alternative, strict=True)
            ),
            "lag_coefficient_rescaling_matches_first_year": agrees(
                response_reference[0]["log_response"], lag_alternative[0]["log_response"]
            ),
            "lag_coefficient_rescaling_differs_second_year": not agrees(
                response_reference[1]["log_response"], lag_alternative[1]["log_response"]
            ),
            "zero_response_null_has_unit_multiplier": all(
                row["log_response"] == 0 and row["multiplier"] == 1
                for row in response_cases["zero_response_null"]["years"]
            ),
        }
    )
    return storage_numbers(
        {
            "classification": "validation_only_synthetic_witnesses",
            "clinical_effect_used": False,
            "clinical_fit_performed": False,
            "formal_cox_identifiability_result": False,
            "initial_survivor_stocks": dict(zip(STATES, map(float, initial[0]), strict=True)),
            "initial_stock_definition": "Normalize registered synthetic H/IR shares; D0=0 in a hypothetical event-free survivor batch. Mortality/aging stages omitted from this isolated operator diagnostic.",
            "endpoint_witness": {
                "one_year_probability_per_initial_ir": probability,
                "analytic_one_year_t2d_entries": analytic,
                "cases": endpoint_cases,
                "reference": reference,
                "identical_hazard_null": structural_null,
                "interpretation": "A/B/C match an artificial one-year endpoint while allocating hazards differently. Differences at year2 show the witness does not match a multi-year trial Cox likelihood.",
            },
            "dose_lag_witness": {
                "cases": response_cases,
                "interpretation": "Synthetic legacy response only; an unmeasured regimen UPF dose and lag are not inferred from these witnesses.",
            },
            "checks": checks,
            "software_witnesses_passed": all(checks.values()),
            "limitations": analysis["limitation"],
            "uncertainty": analysis["uncertainty"],
        }
    )


def audit_compatibility(registry: EvidenceRegistry) -> dict:
    """Verify every frozen dependency before executing synthetic calculations."""
    spec = registry.datasets[DATASET]
    if (
        spec["status"] != "synthetic"
        or spec["evidence_grade"] != "E"
        or spec["model_role"] != "benchmark_only"
    ):
        raise ValueError("Compatibility dataset must remain synthetic/E and benchmark_only")
    protocol_bytes = Path(spec["protocol_path"]).read_bytes()
    amendment_bytes = Path(spec["amendment_path"]).read_bytes()
    protocol, amendment = json.loads(protocol_bytes), json.loads(amendment_bytes)
    parent_amendment = None
    if type(amendment.get("amendment_number")) is int and amendment["amendment_number"] == 2:
        parent_path = amendment.get("parent_amendment_path")
        if parent_path != "docs/validation/reus-diabetes-amendment-1.json":
            raise ValueError("Compatibility numerical amendment parent mismatch")
        parent_bytes = Path(parent_path).read_bytes()
        parent_amendment = json.loads(parent_bytes)
        if (
            digest(parent_bytes) != amendment.get("parent_amendment_sha256")
            or parent_amendment["parent_protocol_sha256"] != amendment["parent_protocol_sha256"]
            or parent_amendment["analysis_id"] != amendment["analysis_id"]
            or parent_amendment["reference_definition_sha256"]
            != amendment["reference_definition_sha256"]
            or amendment.get("changed_helpers") != ["src/demeter/health/transitions.py"]
            or parent_amendment["implementation_sha256"]["src/demeter/nutrition/response.py"]
            != amendment["implementation_sha256"]["src/demeter/nutrition/response.py"]
        ):
            raise ValueError("Compatibility numerical amendment parent mismatch")
    elif "amendment_number" in amendment:
        raise ValueError("Unsupported compatibility numerical amendment")
    if (
        digest(protocol_bytes) != spec["protocol_sha256"]
        or digest(amendment_bytes) != spec["amendment_sha256"]
        or amendment["parent_protocol_sha256"] != digest(protocol_bytes)
        or amendment["analysis_id"] != protocol["analysis_id"]
        or spec["analysis"] != protocol["compatibility_diagnostic"]
        or set(amendment["reference_definition_sha256"]) != set(REFERENCES)
        or set(amendment["implementation_sha256"]) != set(HELPERS)
    ):
        raise ValueError("Compatibility protocol/registry mismatch")
    definitions = _reference_definitions(registry)
    definition_hashes = {key: digest(encoded(value)) for key, value in definitions.items()}
    helper_hashes = {path: digest(Path(path).read_bytes()) for path in HELPERS}
    if (
        definition_hashes != amendment["reference_definition_sha256"]
        or helper_hashes != amendment["implementation_sha256"]
    ):
        raise ValueError("Compatibility reference/helper mismatch")
    result = analyze_compatibility(registry, spec["analysis"])
    return {
        "schema_version": 1,
        "analysis_id": protocol["analysis_id"],
        "status": "synthetic",
        "evidence_grade": "E",
        "model_role": "benchmark_only",
        "scientific_release_ready": False,
        "assessment": "Isolated annual-operator and dose/lag compatibility witnesses; no clinical effect fit",
        "results": result,
        "support_decision": protocol["support_decision"],
        "provenance": {
            "protocol_sha256": digest(protocol_bytes),
            "amendment_sha256": digest(amendment_bytes),
            "definition_sha256": digest(encoded(spec)),
            "reference_definition_sha256": definition_hashes,
            "helper_sha256": helper_hashes,
            "transform_sha256": digest(Path(__file__).read_bytes()),
            "clinical_hr_used_in_witnesses": False,
            "clinical_records_used": False,
            **(
                {"numerical_amendment": 2, "parent_amendment_sha256": digest(parent_bytes)}
                if parent_amendment is not None
                else {}
            ),
        },
    }
