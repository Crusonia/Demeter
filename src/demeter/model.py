from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite

import numpy as np

from demeter import __version__
from demeter.data.baseline import population_counts, source_rows
from demeter.data.ingest import BUNDLE
from demeter.health.transitions import STATES, TRANSITIONS, transition_survivors
from demeter.health.healthspan import CohortTime, metric_contract
from demeter.population.mechanics import (
    age_survivors,
    calibrate_mortality,
    period_outcomes,
    state_shares,
)
from demeter.schema import EvidenceRegistry, Scenario

REQUIRED_UNITS = {
    "initial_healthy_share": "fraction",
    "initial_ir_share": "fraction",
    "initial_t2d_share": "fraction",
    "h_to_ir_rate": "hazard_per_year",
    "ir_to_h_rate": "hazard_per_year",
    "ir_to_t2d_rate": "hazard_per_year",
    "mortality_ir_ratio": "hazard_ratio",
    "mortality_t2d_ratio": "hazard_ratio",
    "beta_upf_progression": "log_multiplier_per_relative_exposure",
    "diet_lag_years": "years",
    "adult_age": "years",
    "upf_min_multiplier": "relative_exposure",
    "upf_max_multiplier": "relative_exposure",
}
LIMITATIONS = [
    "VALIDATION ONLY — NOT A SCIENTIFIC ESTIMATE: metabolic inputs remain synthetic.",
    "Closed population: births and migration are zero; this is not a U.S. population forecast.",
    "Initial adult state fractions are constant across ages/sex; pediatric metabolic disease is omitted.",
    "The IR state is a synthetic prediabetes proxy; normoglycemia does not establish overall metabolic health.",
    "Period life expectancy freezes the current mortality schedule; it is not predicted cohort lifespan.",
    "Metabolically healthy years use a Sullivan prevalence weighting; this is not overall HALE.",
    "The 100+ tail holds state membership fixed and assumes exponential mortality within states.",
    "Mortality and population source uncertainty, structural uncertainty, and correlated parameters are not propagated.",
]


@dataclass(frozen=True)
class SimulationResult:
    scenario: str
    years: int
    validation_only: bool
    starting_population: float
    ending_population: float
    cumulative_deaths: float
    ending_state_shares: dict[str, float]
    annual: list[dict]
    cohorts: list[dict]
    metadata: dict
    diagnostics: dict | None = None
    healthspan: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def validate_inputs(registry: EvidenceRegistry, scenario: Scenario) -> tuple[np.ndarray, bool]:
    for key, unit in REQUIRED_UNITS.items():
        if key not in registry.parameters or registry.parameters[key].unit != unit:
            raise ValueError(f"Missing parameter or wrong units: {key} requires {unit}")
        if registry.parameters[key].model_role != "health_model":
            raise ValueError(f"Benchmark-only evidence cannot drive model input: {key}")
        value = registry.value(key)
        if value < 0 or not isfinite(value):
            raise ValueError(f"Invalid model parameter: {key}")
    shares = np.array(
        [
            registry.value(k)
            for k in ("initial_healthy_share", "initial_ir_share", "initial_t2d_share")
        ]
    )
    if (shares > 1).any() or not np.isclose(shares.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("initial health-state shares must sum to 1")
    if (
        registry.value("diet_lag_years") <= 0
        or min(registry.value("mortality_ir_ratio"), registry.value("mortality_t2d_ratio")) <= 0
    ):
        raise ValueError("lag and mortality hazard ratios must be positive")
    adult = registry.value("adult_age")
    if not adult.is_integer() or not 1 <= adult <= 100:
        raise ValueError("adult_age must be an integer in [1,100]")
    upf = scenario.exposures.get("upf", 1)
    extrapolated = (
        not registry.value("upf_min_multiplier") <= upf <= registry.value("upf_max_multiplier")
    )
    if extrapolated and not scenario.allow_extrapolation:
        raise ValueError(
            "UPF exposure is outside the registered envelope; explicit allow_extrapolation required"
        )
    if scenario.mode == "scientific":
        audit = registry.audit()
        if any(
            audit[k]
            for k in (
                "synthetic",
                "unresolved",
                "missing_uncertainty",
                "missing_provenance",
                "scientific_blockers",
            )
        ):
            raise ValueError(
                "Scientific mode blocked: run demeter evidence audit; unresolved scientific gates remain"
            )
        raise ValueError(
            "Scientific mode blocked in 0.1.0a1: health calibration and validation are not implemented"
        )
    return shares, extrapolated


def simulate(
    registry: EvidenceRegistry, scenario: Scenario, *, diagnostics: bool = False
) -> SimulationResult:
    """Age-structured annual validation model on observed U.S. demographic inputs."""
    initial_shares, extrapolated = validate_inputs(registry, scenario)
    adult = int(registry.value("adult_age"))
    reference = np.tile(initial_shares, (101, 1))
    reference[:adult] = [1, 0, 0]
    stocks = population_counts(scenario.baseline_year, scenario.sex)[:, None] * reference
    rows = source_rows(scenario.baseline_year, scenario.sex)
    ratios = np.array(
        [1, registry.value("mortality_ir_ratio"), registry.value("mortality_t2d_ratio")]
    )
    hazards = calibrate_mortality(rows, reference, ratios)
    starting = float(stocks.sum())
    cohort_time = CohortTime(stocks)
    cumulative, applied_log_effect = 0.0, 0.0
    annual, history = [], []
    target = registry.value("beta_upf_progression") * (scenario.exposures.get("upf", 1) - 1)
    if abs(target) > 50:
        raise ValueError("Scenario log effect is numerically unsupported")
    relaxation = -np.expm1(-1 / registry.value("diet_lag_years"))

    def snapshot(year, deaths=0.0, flows=None):
        shares = state_shares(stocks, reference)
        outcomes = period_outcomes(
            rows, shares, hazards, include_table=diagnostics or year == scenario.years
        )
        table = outcomes.pop("life_table", None)
        if year == scenario.years:
            final_period.extend(table)
        if diagnostics:
            history.append(
                {
                    "year": year,
                    "cohorts": [
                        {
                            "age": age,
                            **{state: float(stocks[age, i]) for i, state in enumerate(STATES)},
                        }
                        for age in range(101)
                    ],
                    "life_table": table,
                }
            )
        return dict(
            year=year,
            population=float(stocks.sum()),
            deaths=deaths,
            cumulative_deaths=cumulative,
            births=0.0,
            net_migration=0.0,
            healthy=float(stocks[:, 0].sum()),
            insulin_resistant=float(stocks[:, 1].sum()),
            t2d=float(stocks[:, 2].sum()),
            applied_progression_multiplier=exp(applied_log_effect),
            empty_age_groups_using_reference=int((stocks.sum(axis=1) == 0).sum()),
            **outcomes,
            restricted_healthy_years=float(cohort_time.person_years[:, 0].sum() / starting),
            **(flows or {}),
        )

    final_period = []
    annual.append(snapshot(0))
    for year in range(1, scenario.years + 1):
        applied_log_effect += relaxation * (target - applied_log_effect)
        deaths = stocks * -np.expm1(-hazards)
        survivors = stocks - deaths
        moved, flows = transition_survivors(
            survivors,
            registry.value("h_to_ir_rate") * exp(applied_log_effect),
            registry.value("ir_to_h_rate"),
            registry.value("ir_to_t2d_rate") * exp(applied_log_effect),
            adult,
        )
        stocks = age_survivors(moved)
        cohort_time.advance(
            year,
            hazards,
            (
                registry.value("h_to_ir_rate") * exp(applied_log_effect),
                registry.value("ir_to_h_rate"),
                registry.value("ir_to_t2d_rate") * exp(applied_log_effect),
            ),
            adult,
        )
        if not np.allclose(cohort_time.age_stocks(), stocks, rtol=1e-12, atol=1e-7):
            raise ArithmeticError("Original-cohort accounting differs from the engine")
        if diagnostics:
            flows.update(
                {f"{state}_deaths": float(deaths[:, i].sum()) for i, state in enumerate(STATES)}
            )
        cumulative += float(deaths.sum())
        if stocks.min() < -1e-7 or not np.isclose(
            stocks.sum() + cumulative, starting, rtol=1e-12, atol=1e-5
        ):
            raise ArithmeticError("population conservation or nonnegativity failed")
        annual.append(snapshot(year, float(deaths.sum()), flows))
    total = float(stocks.sum())
    cohorts = [
        {
            "age": age,
            "sex": scenario.sex,
            **{state: float(stocks[age, i]) for i, state in enumerate(STATES)},
        }
        for age in range(101)
    ]
    import json

    source_manifest = json.loads((BUNDLE / "manifest.json").read_text())
    audit = registry.audit()
    validation_only = scenario.mode == "validation"
    metadata = {
        "model_version": __version__,
        "scenario": scenario.model_dump(),
        "evidence_sha256": registry.content_hash,
        "source_bundle_sha256": source_manifest["bundle_sha256"],
        "mortality_vintage": scenario.baseline_year,
        "population_vintage": "Census 2025",
        "status": "VALIDATION ONLY — NOT A SCIENTIFIC ESTIMATE"
        if validation_only
        else "scientific",
        "extrapolation": extrapolated,
        "parameter_status_counts": audit["status_counts"],
        "synthetic_parameters": audit["synthetic"],
        "unresolved_parameters": audit["unresolved"],
        "scientific_blockers": registry.scientific_blockers,
        "limitations": LIMITATIONS,
        "healthspan_metric": metric_contract(),
    }
    return SimulationResult(
        scenario.name,
        scenario.years,
        validation_only,
        starting,
        total,
        cumulative,
        {s: float(stocks[:, i].sum() / total) if total else 0 for i, s in enumerate(STATES)},
        annual,
        cohorts,
        metadata,
        {
            "history": history,
            "structure": model_structure(registry),
            "state_definitions": {
                "healthy": "Synthetic normoglycemic/healthy proxy, not absence of all disease",
                "insulin_resistant": "Synthetic IR/prediabetes proxy, not separately measured PreChronic",
                "t2d": "Synthetic T2D state; no remission pathway implemented",
            },
            "cohort_semantics": "Age cells after each annual step; 100+ is pooled, not a birth cohort",
        }
        if diagnostics
        else None,
        {
            "definition": metric_contract(),
            "period_by_age": [
                {
                    "age": row["start_age"],
                    "life_expectancy": row["life_expectancy"],
                    "healthspan": row["healthspan"],
                    "state_years": row["state_life_expectancy"],
                }
                for row in final_period
            ],
            "restricted_cohort": cohort_time.report(),
            "validation_only": validation_only,
            "evidence_sha256": registry.content_hash,
        },
    )


def model_structure(registry: EvidenceRegistry) -> dict:
    """Describe the implemented dependency graph; edges are not causal validation."""
    transitions = [dict(t) for t in TRANSITIONS]
    transitions.extend(
        {
            "source": s,
            "target": "dead",
            "flow": f"{s}_deaths",
            "parameter": {
                "insulin_resistant": "mortality_ir_ratio",
                "t2d": "mortality_t2d_ratio",
            }.get(s),
        }
        for s in STATES
    )
    dependencies = [
        {
            "source": "upf_exposure",
            "target": "lagged_response",
            "parameters": ["beta_upf_progression", "diet_lag_years"],
        },
        {"source": "lagged_response", "target": "healthy_to_ir", "parameters": ["h_to_ir_rate"]},
        {"source": "lagged_response", "target": "ir_to_t2d", "parameters": ["ir_to_t2d_rate"]},
        {"source": "healthy_to_ir", "target": "state_shares", "parameters": []},
        {"source": "ir_to_t2d", "target": "state_shares", "parameters": []},
        {"source": "ir_to_healthy", "target": "state_shares", "parameters": ["ir_to_h_rate"]},
        {
            "source": "state_shares",
            "target": "mortality_schedule",
            "parameters": ["mortality_ir_ratio", "mortality_t2d_ratio"],
        },
        {"source": "nchs_mortality", "target": "mortality_schedule", "parameters": []},
        {"source": "mortality_schedule", "target": "life_expectancy", "parameters": []},
        {"source": "mortality_schedule", "target": "healthy_years", "parameters": []},
        {"source": "state_shares", "target": "healthy_years", "parameters": []},
    ]
    return {
        "states": list(STATES) + ["dead"],
        "transitions": transitions,
        "dependencies": dependencies,
        "evidence": {k: registry.parameters[k].model_dump(mode="json") for k in REQUIRED_UNITS},
        "interpretation": "Implemented dependencies and state transitions; synthetic edges are not established causal effects",
    }
