"""Reproduce a frozen synthetic likelihood exercise; no participant import or fit."""

from __future__ import annotations

import itertools
import json
from math import exp, expm1, isfinite, log
from pathlib import Path

import numpy as np
import yaml
from scipy.integrate import quad

from demeter.analysis.longitudinal_likelihood import (
    PanelObservation,
    RateSegment,
    SoftwareObservationContract,
    StateSpace,
    TerminalObservation,
    observable_jacobian,
    path_likelihood,
    transition_matrix,
    validate_categorical_emissions,
)
from demeter.data.ingest import digest
from demeter.schema import EvidenceRegistry

DATASET = "longitudinal_likelihood_software"
PROTOCOL_PATH = "docs/validation/longitudinal-likelihood-protocol-v1.json"
PROTOCOL_SHA256 = "fb830574b696c623ca00282bda3c31093369c05ddb420458a53a83f27a22910e"
RFC_PATH = "docs/rfcs/RFC-57-longitudinal-likelihood.md"
RFC_SHA256 = "680d1a1b854e07e73f633db8b57a602df15a1193c46f6426d95907c136e44385"


def _frozen(path: str, expected: str) -> dict | None:
    content = Path(path).read_bytes()
    if digest(content) != expected:
        raise ValueError("Frozen likelihood contract differs")
    return json.loads(content) if path.endswith(".json") else None


def load_likelihood_registry(path: str | Path) -> EvidenceRegistry:
    """Reject malformed fixture scalars before normal registry parsing can coerce them."""
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    protocol = _frozen(PROTOCOL_PATH, PROTOCOL_SHA256)
    if type(document) is not dict or type(document.get("parameters")) is not dict:
        raise ValueError("A parameter registry mapping is required")
    for key in protocol["numeric_inputs"]:
        record = document["parameters"].get(key)
        if type(record) is not dict:
            raise ValueError("A registered fixture input is missing")
        value = record.get("value")
        if type(value) not in (int, float):
            raise ValueError("Fixture input must be a finite numeric YAML scalar")
        try:
            finite = isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("Fixture input must be a finite numeric YAML scalar")
    return EvidenceRegistry.model_validate(document)


def _generator(protocol: dict, values: dict, overrides=()) -> np.ndarray:
    labels = protocol["state_space"]["state_order"]
    q = np.zeros((len(labels), len(labels)))
    for edge in [*protocol["software_validation"]["base_off_diagonal_rates"], *overrides]:
        q[labels.index(edge["from"]), labels.index(edge["to"])] = values[edge["parameter_key"]]
    np.fill_diagonal(q, -q.sum(axis=1))
    return q


def _contract(stopping: str) -> SoftwareObservationContract:
    return SoftwareObservationContract(
        time_unit="years",
        observation_timing="exogenous",
        missingness="explicit_coarsening",
        selection="synthetic_fixed_cohort",
        treatment="piecewise_declared",
        stopping=stopping,
    )


def _json_contribution(result: dict) -> dict:
    result = dict(result)
    if not isfinite(result["log_likelihood"]):
        result["log_likelihood"] = None
        result["log_likelihood_status"] = "negative_infinity_structurally_zero"
    else:
        result["log_likelihood_status"] = "finite"
    return result


def likelihood_failure_report(stage: str) -> dict:
    """Sanitized aggregate failure; never expose exception data or record paths."""
    return {
        "schema_version": 1,
        "validation_only": True,
        "evidence_grade": "E",
        "model_role": "benchmark_only",
        "computational_evaluation_passed": False,
        "software_checks_passed": False,
        "source_eligibility_promoted": False,
        "clinical_fit_performed": False,
        "clinical_fit_allowed": False,
        "independent_prediction_performed": False,
        "engine_activation_allowed": False,
        "engine_parameters_updated": False,
        "scientific_release_ready": False,
        "external_human_scientific_review": "pending",
        "failure": {
            "stage": stage,
            "reason": "Frozen input or mathematical evaluation failed; no clinical fit permitted.",
        },
    }


def likelihood_software_report(registry: EvidenceRegistry) -> dict:
    """Fixed registered fixture only; reject changed pins/roles before arithmetic."""
    report = likelihood_failure_report("frozen_contract")
    report.pop("failure")
    stage = "frozen_contract"
    try:
        protocol = _frozen(PROTOCOL_PATH, PROTOCOL_SHA256)
        _frozen(RFC_PATH, RFC_SHA256)
        spec = registry.datasets[DATASET]
        for field, expected in {
            "protocol_path": PROTOCOL_PATH,
            "protocol_sha256": PROTOCOL_SHA256,
            "rfc_path": RFC_PATH,
            "rfc_sha256": RFC_SHA256,
            "model_role": "benchmark_only",
            "status": "synthetic",
            "evidence_grade": "E",
            "clinical_fit_allowed": False,
            "engine_activation_allowed": False,
        }.items():
            if type(spec.get(field)) is not type(expected) or spec[field] != expected:
                raise ValueError("Dataset contract differs")
        stage = "registered_inputs"
        if spec.get("parameter_keys") != list(protocol["numeric_inputs"]):
            raise ValueError("Dataset parameter links differ from the frozen input order")
        values = {}
        for key, expected in protocol["numeric_inputs"].items():
            parameter = registry.parameters[key]
            if parameter.key != key:
                raise ValueError("Registered parameter identity differs")
            if type(parameter.value) not in (int, float) or not isfinite(parameter.value):
                raise ValueError("Fixture numeric input requires a finite nonboolean scalar")
            if any(getattr(parameter, field) != expected[field] for field in expected):
                raise ValueError("Registered input differs")
            if parameter.unresolved or parameter.source_id is not None:
                raise ValueError("Fixture input is unresolved or incorrectly sourced")
            if parameter.uncertainty is None or parameter.uncertainty.kind != "fixed":
                raise ValueError("Fixture numerical input requires a fixed software rationale")
            values[key] = registry.value(key)
        report["provenance"] = {
            "protocol_path": PROTOCOL_PATH,
            "protocol_sha256": PROTOCOL_SHA256,
            "rfc_path": RFC_PATH,
            "rfc_sha256": RFC_SHA256,
            "evidence_sha256": registry.content_hash,
            "implementation_sha256": {
                path: digest(Path(path).read_bytes())
                for path in (
                    "src/demeter/analysis/longitudinal_likelihood.py",
                    "src/demeter/analysis/longitudinal_likelihood_validation.py",
                )
            },
            "registered_inputs": protocol["numeric_inputs"],
            "new_empirical_source_values": False,
        }
        stage = "mathematical_evaluation"
        fixture = protocol["software_validation"]
        labels = tuple(protocol["state_space"]["state_order"])
        death = labels.index("death")
        space = StateSpace(
            labels, tuple(None if x == "death" else x in ("D", "R") for x in labels), death
        )
        initial = np.zeros(len(labels))
        initial[labels.index(fixture["entry_state"])] = 1
        tolerance = values[fixture["controls"]["probability_absolute_tolerance_key"]]
        log_tolerance = values[fixture["controls"]["log_likelihood_absolute_tolerance_key"]]
        segments = tuple(
            RateSegment(
                values[item["start_key"]],
                values[item["end_key"]],
                _generator(protocol, values, item["overrides"]),
            )
            for item in fixture["rate_segments"]
        )
        alphabet = fixture["emissions"]["alphabet"]
        categories = fixture["emissions"]["category_states"]
        emissions = validate_categorical_emissions(
            [[int(label in categories[category]) for category in alphabet] for label in labels],
            state_count=len(labels),
            tolerance=tolerance,
        )
        observations = []
        for item in fixture["panel_path"]:
            weights = emissions[:, [alphabet.index(x) for x in item["categories"]]].sum(axis=1)
            if item["history_report"] != "not_assessed":
                history = item["history_report"] == "diagnosed_history"
                weights *= [attribute is history for attribute in space.diagnosis_history]
            observations.append(
                PanelObservation(
                    values[item["time_key"]],
                    weights,
                    "coarsened" if len(item["categories"]) > 1 else "category",
                )
            )
        horizon = values[fixture["first_entry"]["censor_time_key"]]
        panel = path_likelihood(
            space,
            initial,
            segments,
            observations,
            terminal=TerminalObservation("panel", horizon),
            contract=_contract("observation_sequence_only"),
            tolerance=tolerance,
        )

        # Enumerate all intermediate compatible state sequences independently of
        # the scaled forward algorithm. Compose known regime kernels chronologically.
        kernels, previous = [], 0.0
        for observation in observations:
            kernel = np.eye(len(labels))
            for segment in segments:
                duration = min(observation.time_year, segment.end_year) - max(
                    previous, segment.start_year
                )
                if duration > 0:
                    kernel = kernel @ transition_matrix(
                        space, segment.generator, duration, tolerance=tolerance
                    )
            kernels.append(kernel)
            previous = observation.time_year
        enumerated = 0.0
        entry = labels.index(fixture["entry_state"])
        for states in itertools.product(range(len(labels)), repeat=len(observations)):
            contribution, previous_state = 1.0, entry
            for kernel, observation, state in zip(kernels, observations, states, strict=True):
                contribution *= kernel[previous_state, state] * observation.emission[state]
                previous_state = state
            enumerated += contribution

        targets = {"diagnosis": (labels.index("D"),), "death": (death,)}

        def event_result(kind, event=None, lower=None, prefix=(), endpoint=None):
            stopping = {
                "right_censor": "independent_right_censoring",
                "non_event_endpoint": "non_event_assessment",
            }.get(kind, "first_entry_ascertainment")
            return path_likelihood(
                space,
                initial,
                segments,
                prefix,
                terminal=TerminalObservation(
                    kind,
                    horizon,
                    event=event,
                    interval_start_year=lower,
                    endpoint_emission=endpoint,
                ),
                contract=_contract(stopping),
                event_targets=targets,
                tolerance=tolerance,
            )

        contributions = {
            "linked_panel": panel,
            "exact_diagnosis": event_result("exact_first_entry", "diagnosis"),
            "interval_diagnosis": event_result(
                "interval_first_entry",
                "diagnosis",
                values[fixture["first_entry"]["interval_lower_key"]],
            ),
            "cumulative_diagnosis": event_result("interval_first_entry", "diagnosis", 0.0),
            "cumulative_competing_death": event_result("interval_first_entry", "death", 0.0),
            "event_free_right_censor": event_result("right_censor"),
            "linked_prefix_interval_diagnosis": event_result(
                "interval_first_entry",
                "diagnosis",
                values[fixture["first_entry"]["interval_lower_key"]],
                observations[:1],
            ),
            "event_free_lower_endpoint": event_result(
                "non_event_endpoint", endpoint=tuple(int(x == "N") for x in labels)
            ),
            "exact_death_after_panel": path_likelihood(
                space,
                initial,
                segments,
                observations,
                terminal=TerminalObservation("exact_first_entry", horizon, event="death"),
                contract=_contract("first_entry_ascertainment"),
                event_targets={"death": (death,)},
                tolerance=tolerance,
            ),
        }
        mass = sum(
            contributions[key]["likelihood"]
            for key in (
                "cumulative_diagnosis",
                "cumulative_competing_death",
                "event_free_right_censor",
            )
        )
        # Independent analytic competing-hazard identity using registered toy
        # rates, with all other toy edges disabled by structural definition.
        q_simple = np.zeros((len(labels), len(labels)))
        d, c = values["longitudinal_toy_p_to_d_rate"], values["longitudinal_toy_p_to_death_rate"]
        q_simple[entry, labels.index("D")], q_simple[entry, death] = d, c
        q_simple[entry, entry] = -(d + c)
        simple = (RateSegment(0, horizon, q_simple),)
        simple_interval = path_likelihood(
            space,
            initial,
            simple,
            (),
            terminal=TerminalObservation(
                "interval_first_entry", horizon, event="diagnosis", interval_start_year=0
            ),
            contract=_contract("first_entry_ascertainment"),
            event_targets=targets,
            tolerance=tolerance,
        )
        analytic_interval = d / (d + c) * -expm1(-(d + c) * horizon)
        quadrature = quad(
            lambda t: d * exp(-(d + c) * t), 0, horizon, epsabs=tolerance, epsrel=tolerance
        )[0]

        identification = fixture["local_identification"]
        parameter_keys = identification["parameter_order"]
        point = np.array([values[key] for key in parameter_keys])
        step = values[identification["step_key"]]
        rank_tolerance = values[identification["rank_threshold_key"]]

        def full_observable(parameters):
            chosen = {**values, **dict(zip(parameter_keys, parameters, strict=True))}
            if (parameters < 0).any():
                raise ValueError("Rate perturbation outside the declared nonnegative domain")
            return transition_matrix(
                space, _generator(protocol, chosen), horizon, tolerance=tolerance
            )[:death].reshape(-1)

        def collapsed_observable(parameters):
            full = full_observable(parameters).reshape(death, len(labels))
            return [full[entry, labels.index("N")] + full[entry, labels.index("R")]]

        diagnostics = {
            name: observable_jacobian(
                function, point, np.full(len(point), step), rank_tolerance=rank_tolerance
            )
            for name, function in (
                ("full_design", full_observable),
                ("scalar_design", collapsed_observable),
            )
        }
        alternative = fixture["indistinguishable_scalar_alternative"]
        a, b = values[alternative["base_a_key"]], values[alternative["base_b_key"]]
        q = b / (a + b) * -expm1(-(a + b) * horizon)
        total = a + values["longitudinal_toy_segment_b_p_to_n_rate"]
        b2 = q * total / -expm1(-total * horizon)
        a2 = total - b2
        q2 = b2 / (a2 + b2) * -expm1(-(a2 + b2) * horizon)
        other_entry = a / (a + b) * -expm1(-(a + b) * horizon)
        other_alternative = a2 / total * -expm1(-total * horizon)
        checks = {
            "linked_forward_matches_enumeration": abs(panel["likelihood"] - enumerated)
            <= tolerance,
            "scaled_log_matches_enumeration": abs(panel["log_likelihood"] - log(enumerated))
            <= log_tolerance,
            "competing_event_death_survival_mass": abs(mass - 1) <= tolerance,
            "interval_matches_analytic_competing_hazards": abs(
                simple_interval["likelihood"] - analytic_interval
            )
            <= tolerance,
            "analytic_interval_matches_quadrature": abs(analytic_interval - quadrature)
            <= tolerance,
            "full_design_local_rank_nine": diagnostics["full_design"]["local_numerical_rank"]
            == len(parameter_keys),
            "scalar_design_local_rank_one": diagnostics["scalar_design"]["local_numerical_rank"]
            == 1,
            "restricted_alternative_nonnegative_and_distinct": min(a2, b2) >= 0
            and abs(a2 - a) + abs(b2 - b) > tolerance,
            "restricted_alternative_same_scalar_endpoint": abs(q - q2) <= tolerance,
            "restricted_alternative_full_rows_differ": abs(other_entry - other_alternative)
            > tolerance,
        }
        report.update(
            computational_evaluation_passed=True,
            software_checks_passed=all(checks.values()),
            checks={key: bool(value) for key, value in checks.items()},
            state_space=protocol["state_space"],
            observation_definitions=fixture["panel_path"],
            contributions={key: _json_contribution(value) for key, value in contributions.items()},
            independent_panel_enumeration=enumerated,
            cumulative_mass=mass,
            local_identification={
                "parameter_order": parameter_keys,
                "parameter_unit": "hazard_per_year",
                **diagnostics,
            },
            restricted_scalar_alternative={
                "base_rates": {"a": a, "b": b},
                "alternative_rates": {"a": a2, "b": b2},
                "base_endpoint": q,
                "alternative_endpoint": q2,
                "scope": alternative["comparison_model"],
            },
            source_gate=protocol["source_gate"],
            limitations=[
                "Arbitrary software states/rates only; no clinical observations, thresholds, fit or uncertainty distribution.",
                "A supplied software assumption does not prove actual source coverage or clinical eligibility.",
                "Local numerical rank is not global, practical or causal identification.",
                "Continuous-time kernels are separate from the current annual engine operator.",
                "Dietary effects, dose, lag, national transport and independent empirical evaluation remain unresolved.",
            ],
        )
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        report["failure"] = {
            "stage": stage,
            "reason": "Frozen input or mathematical evaluation failed; no clinical fit permitted.",
        }
    return report
