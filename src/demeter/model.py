from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from math import isfinite

import numpy as np

from demeter import __version__
from demeter.contracts import TransitionModule
from demeter.data.baseline import population_counts, source_rows
from demeter.data.ingest import BUNDLE
from demeter.health.structure import PRECHRONIC_UNITS, move, rates_for, states_for, transitions_for
from demeter.health.healthspan import CohortTime, metric_contract
from demeter.health.glp1 import GLP1Cohort, GLP1_UNITS
from demeter.nutrition.exposures import resolve_diet
from demeter.nutrition.response import DietaryResponse, response_units
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
    prechronic: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def required_units(
    scenario: Scenario, *, transition_parameters: dict[str, str] | None = None
) -> dict:
    units = REQUIRED_UNITS.copy()
    units.update(response_units(scenario))
    if scenario.glp1:
        units.update(GLP1_UNITS)
    if scenario.health_structure != "legacy":
        for key in ("h_to_ir_rate", "ir_to_h_rate"):
            units.pop(key)
        units.update(PRECHRONIC_UNITS)
        units[f"initial_pc_fraction_{scenario.health_structure}"] = "fraction"
    if transition_parameters is not None:
        for key, unit in transition_parameters.items():
            if key in units and unit != units[key]:
                raise ValueError(f"A module cannot redefine core parameter units: {key}")
        for edge in transitions_for(scenario):
            units.pop(edge["parameter"], None)
        units.update(transition_parameters)
    return units


def validate_inputs(
    registry: EvidenceRegistry,
    scenario: Scenario,
    *,
    transition_parameters: dict[str, str] | None = None,
) -> tuple[np.ndarray, bool]:
    units = required_units(scenario, transition_parameters=transition_parameters)
    core_units = required_units(scenario)
    for key, unit in units.items():
        if key not in registry.parameters or registry.parameters[key].unit != unit:
            raise ValueError(f"Missing parameter or wrong units: {key} requires {unit}")
        if registry.parameters[key].model_role != "health_model":
            raise ValueError(f"Benchmark-only evidence cannot drive model input: {key}")
        value = registry.value(key)
        if (key in core_units and value < 0) or not isfinite(value):
            raise ValueError(f"Invalid model parameter: {key}")
    shares = np.array(
        [
            registry.value(k)
            for k in ("initial_healthy_share", "initial_ir_share", "initial_t2d_share")
        ]
    )
    if (shares > 1).any() or not np.isclose(shares.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("initial health-state shares must sum to 1")
    if scenario.health_structure != "legacy":
        split = registry.value(f"initial_pc_fraction_{scenario.health_structure}")
        if not 0 <= split <= 1 or registry.value("mortality_pc_ratio") <= 0:
            raise ValueError("Invalid PreChronic fraction or mortality ratio")
        shares = np.array([shares[0] * (1 - split), shares[0] * split, shares[1], shares[2]])
    if (
        registry.value("diet_lag_years") <= 0
        or min(registry.value("mortality_ir_ratio"), registry.value("mortality_t2d_ratio")) <= 0
    ):
        raise ValueError("lag and mortality hazard ratios must be positive")
    adult = registry.value("adult_age")
    if not adult.is_integer() or not 1 <= adult <= 100:
        raise ValueError("adult_age must be an integer in [1,100]")
    path = resolve_diet(registry, scenario)["annual_upf"]
    extrapolated = any(
        not registry.value("upf_min_multiplier") <= value <= registry.value("upf_max_multiplier")
        for value in path
    )
    if extrapolated and not scenario.allow_extrapolation:
        raise ValueError(
            "UPF exposure is outside the registered envelope; explicit allow_extrapolation required"
        )
    if scenario.mode == "scientific":
        audit = registry.audit(parameter_keys=units)
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
    registry: EvidenceRegistry,
    scenario: Scenario,
    *,
    diagnostics: bool = False,
    dietary_reference: Scenario | None = None,
    dietary_paths: tuple[str, ...] | None = None,
    transition_module: TransitionModule | None = None,
) -> SimulationResult:
    """Age-structured annual validation model on observed U.S. demographic inputs."""
    binding = None
    if transition_module is not None:
        from demeter.health.module import BoundTransitionModule

        if dietary_reference is not None or dietary_paths is not None:
            raise ValueError("Dietary pathway routing requires canonical transition equations")
        binding = BoundTransitionModule(transition_module, registry, scenario)
    module_parameters = {p.key: p.unit for p in binding.parameters} if binding else None
    active_parameters = tuple(required_units(scenario, transition_parameters=module_parameters))
    initial_shares, extrapolated = validate_inputs(
        registry, scenario, transition_parameters=module_parameters
    )
    if (dietary_reference is None) != (dietary_paths is None):
        raise ValueError("Dietary routing needs both reference scenario and selected paths")
    reference_response, reference_diet = None, None
    if dietary_reference is not None:
        from demeter.health.structure import dietary_pathways

        omitted = {"name", "description", "exposures", "diet", "upf_schedule"}
        if scenario.model_dump(exclude=omitted) != dietary_reference.model_dump(exclude=omitted):
            raise ValueError("Dietary attribution requires identical non-diet assumptions")
        available = {e["flow"] for e in dietary_pathways(scenario)}
        if len(set(dietary_paths)) != len(dietary_paths) or set(dietary_paths) - available:
            raise ValueError("Dietary routing requires distinct implemented dietary paths")
        _, reference_extrapolated = validate_inputs(registry, dietary_reference)
        extrapolated = extrapolated or reference_extrapolated
        reference_response = DietaryResponse(registry, dietary_reference)
        reference_diet = resolve_diet(registry, dietary_reference)
    states = states_for(scenario)
    mover = partial(move, structure=scenario.health_structure)
    prechronic_enabled = scenario.health_structure != "legacy"
    adult = int(registry.value("adult_age"))
    reference = np.tile(initial_shares, (101, 1))
    reference[:adult] = np.eye(len(states))[0]
    stocks = population_counts(scenario.baseline_year, scenario.sex)[:, None] * reference
    rows = source_rows(scenario.baseline_year, scenario.sex)
    ratios = np.array(
        [
            1,
            *([registry.value("mortality_pc_ratio")] if prechronic_enabled else []),
            registry.value("mortality_ir_ratio"),
            registry.value("mortality_t2d_ratio"),
        ]
    )
    hazards = calibrate_mortality(rows, reference, ratios)
    starting = float(stocks.sum())
    cohort_factory = (
        partial(GLP1Cohort, registry=registry, scenario=scenario) if scenario.glp1 else CohortTime
    )
    cohort_time = cohort_factory(stocks, states, mover)
    initial_pc = None
    if prechronic_enabled:
        tagged = np.zeros_like(stocks)
        tagged[:, states.index("prechronic")] = stocks[:, states.index("prechronic")]
        initial_pc = cohort_factory(tagged, states, mover)
    cumulative = 0.0
    annual, history = [], []
    dietary = resolve_diet(registry, scenario)
    response = DietaryResponse(registry, scenario)
    dietary_state = response.snapshot()

    def snapshot(year, deaths=0.0, flows=None):
        shares = state_shares(stocks, reference)
        outcomes = period_outcomes(
            rows,
            shares,
            hazards,
            include_table=diagnostics or year == scenario.years,
            states=states,
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
                            **{state: float(stocks[age, i]) for i, state in enumerate(states)},
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
            **{state: float(stocks[:, i].sum()) for i, state in enumerate(states)},
            **dietary_state,
            **({"glp1": cohort_time.treatment_report()} if scenario.glp1 else {}),
            empty_age_groups_using_reference=int((stocks.sum(axis=1) == 0).sum()),
            **outcomes,
            restricted_healthy_years=float(cohort_time.person_years[:, 0].sum() / starting),
            **(
                {
                    "restricted_prechronic_years": float(
                        cohort_time.person_years[:, 1].sum() / starting
                    ),
                    "cumulative_t2d_incidence": float(
                        cohort_time.flow_totals.get("prediabetes_to_t2d", np.zeros(1)).sum()
                    ),
                    "t2d_incidence_from_initial_prechronic": float(
                        initial_pc.flow_totals.get("prediabetes_to_t2d", np.zeros(1)).sum()
                    ),
                }
                if prechronic_enabled
                else {}
            ),
            **(flows or {}),
        )

    final_period = []
    annual.append(snapshot(0))
    for year in range(1, scenario.years + 1):
        dietary_state = response.advance(dietary["annual_upf"][year - 1])
        multipliers = (
            dietary_state["applied_progression_multiplier"],
            dietary_state["applied_recovery_multiplier"],
        )
        rates = (
            binding.rates(year, stocks, *multipliers)
            if binding
            else rates_for(registry, scenario, *multipliers)
        )
        if binding:
            dietary_state["module_base_hazards_per_year"] = {
                edge["flow"]: value
                for edge, value in zip(transitions_for(scenario), rates, strict=True)
            }
        if reference_response is not None:
            ref_state = reference_response.advance(reference_diet["annual_upf"][year - 1])
            ref_rates = rates_for(
                registry,
                scenario,
                ref_state["applied_progression_multiplier"],
                ref_state["applied_recovery_multiplier"],
            )
            rates = tuple(
                rate if edge["flow"] in dietary_paths else ref_rate
                for edge, rate, ref_rate in zip(
                    transitions_for(scenario), rates, ref_rates, strict=True
                )
            )
            dietary_state["routed_base_transition_hazards_per_year"] = {
                edge["flow"]: float(rate)
                for edge, rate in zip(transitions_for(scenario), rates, strict=True)
            }
        if scenario.glp1:
            plan = cohort_time.plan(year, adult)
            cohort_time.advance(year, hazards, rates, adult, plan=plan)
            deaths = cohort_time.last_deaths
            flows = cohort_time.last_health_flows.copy()
            stocks = cohort_time.age_stocks()
            if initial_pc is not None:
                initial_pc.advance(year, hazards, rates, adult, plan=plan)
        else:
            deaths = stocks * -np.expm1(-hazards)
            survivors = stocks - deaths
            moved, flows = mover(survivors, rates, adult)
            stocks = age_survivors(moved)
            cohort_time.advance(year, hazards, rates, adult)
            if initial_pc is not None:
                initial_pc.advance(year, hazards, rates, adult)
        if not np.allclose(cohort_time.age_stocks(), stocks, rtol=1e-12, atol=1e-7):
            raise ArithmeticError("Original-cohort accounting differs from the engine")
        if diagnostics:
            flows.update(
                {f"{state}_deaths": float(deaths[:, i].sum()) for i, state in enumerate(states)}
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
            **{state: float(stocks[age, i]) for i, state in enumerate(states)},
        }
        for age in range(101)
    ]
    import json

    source_manifest = json.loads((BUNDLE / "manifest.json").read_text())
    audit = registry.audit(parameter_keys=active_parameters)
    validation_only = scenario.mode == "validation"
    metadata = {
        "model_version": __version__,
        "scenario": scenario.model_dump(),
        "dietary_exposures": dietary,
        "diet_response": {
            **scenario.diet_response.model_dump(),
            "role": "inputs_to_replacement_module" if binding else "canonical_hazard_modifiers",
            "units": {
                "fast_response": "log_multiplier"
                if scenario.diet_response.kind == "legacy"
                else "relative_exposure",
                "retained_exposure": "relative_exposure",
                "recovery_response": "relative_exposure",
                "cumulative_exposure_years": "relative_exposure * years",
            },
            "initialization": "Zero deviation and no pre-run exposure history; shared adult response, not individual lifetime dose",
            "timing": "End-of-year multipliers are supplied to the replacement module; their use is module-defined. Annual health operator order is unchanged"
            if binding
            else "End-of-year response modifies year-end competing transition hazards; annual health operator order is unchanged",
            "limitations": [
                "All response parameters remain synthetic; no clinical dose range, saturation or timing is established.",
                "Cumulative exposure is reported; only bounded fading memory affects hazards, avoiding an assumed irreversible dose effect.",
                "Age-dependent response and clinical T2D remission/relapse are unresolved; only existing H/IR or H/PreChronic/prediabetes reversals are modified.",
                "Recovery and progression have independent amplitudes and lags; observation/diagnosis delay is not separately identified.",
            ]
            if not binding
            else [
                "Response states and multipliers describe the built-in input calculation, not necessarily an effect on hazards.",
                "The replacement module may ignore or reinterpret dietary inputs; inspect its declared equations, evidence dependencies and recorded hazards.",
                "Canonical dietary pathway and independence assumptions are not asserted for replacement equations; scientific applicability remains unresolved.",
            ],
        },
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
        "limitations": LIMITATIONS
        if not prechronic_enabled
        else [item for item in LIMITATIONS if not item.startswith("The IR state")]
        + [
            "PreChronic and prediabetes are distinct synthetic stocks; risk definitions are research proxies, not clinical diagnoses.",
            "NHANES candidate counts do not initialize the engine; allocation, reversibility, progression, and state mortality await calibration.",
            "Dietary multipliers are supplied to replacement equations; which paths respond is module-defined and not established causal evidence."
            if binding
            else "The synthetic UPF response multiplies three progression paths; this mapping and reversal hazards are not established causal effects.",
        ],
        "healthspan_metric": metric_contract(scenario.health_structure),
        "health_structure": scenario.health_structure,
        "active_parameters": list(active_parameters),
        "extension_provenance": {
            "schema_version": 1,
            "core_model_version": __version__,
            "active_packages": [],
            "scenario_origin": "unregistered; see the explicit scenario and evidence hashes",
            "equations": "unregistered_module" if binding else "canonical_engine",
            "unregistered_module": binding.provenance if binding else None,
            "registration_note": "Direct API/import execution has no verified author, license or package identity. Use the extension registry to record package provenance.",
        },
        **({"transition_module": binding.provenance} if binding else {}),
        **(
            {
                "dietary_routing": {
                    "reference_scenario": dietary_reference.model_dump(),
                    "intervention_paths": list(dietary_paths),
                    "interpretation": "Counterfactual hybrid: only selected dietary hazard modifiers use intervention exposure; other paths retain reference exposure. No flows are removed.",
                }
            }
            if dietary_reference is not None
            else {}
        ),
        **(
            {
                "glp1": {
                    "validation_only": True,
                    "evidence_dataset": "glp1_benchmarks",
                    "eligibility": "Persistent synthetic indication tag, independent of metabolic state; adult gate uses adult_age; no clinical BMI/contraindication assessment",
                    "heterogeneity": "Fixed low/high response strata; joint treatment and health stocks retain selection/history",
                    "supply": "Concurrent slots as a fraction of initial adult population; continuers prioritized, proportional rationing within each allocation stage",
                    "timing": cohort_time.report()["timing"],
                    "limitations": [
                        "All treatment parameters are synthetic; trial/observational benchmarks are not calibrated engine effects.",
                        "No prevalent treatment at initialization; adoption is an incident-use experiment, not a forecast of current U.S. use.",
                        "Annual two-phase response/washout is not individual dose titration or weight physiology; no within-year start-stop cycling.",
                        "Price/coverage/access are exogenous scenario assumptions. The affordability equation is uncalibrated; no expenditure, savings or insurance forecast.",
                        "Response modifies existing health hazards through a synthetic weight bridge. Intake is a diagnostic proxy, not an additional dietary effect.",
                        "Treatment modifiers apply to replacement-module base hazards; dietary use and any additional interactions are module-defined, not inferred from the canonical equations."
                        if binding
                        else "Diet and treatment hazard multipliers combine independently; interactions, adverse-event outcomes, direct cardiovascular mortality effects and T2D remission are unresolved.",
                        "The same response/washout phase represents intake and weight; endpoints and mechanisms require separate clinical appraisal before scientific use.",
                    ],
                }
            }
            if scenario.glp1
            else {}
        ),
        "transition_flows": [edge["flow"] for edge in transitions_for(scenario)],
    }
    structure = None
    if diagnostics:
        if binding:
            # No canonical hazard parameter links are inferred for arbitrary replacement equations.
            structure = {
                "states": list(states) + ["dead"],
                "transitions": [
                    {k: v for k, v in edge.items() if k != "parameter"}
                    for edge in transitions_for(scenario)
                ]
                + [{"source": s, "target": "dead", "flow": f"{s}_deaths"} for s in states],
                "dependencies": [],
                "module_contract": binding.provenance,
                "evidence": {
                    k: registry.parameters[k].model_dump(mode="json") for k in active_parameters
                },
                "interpretation": "Stock/flow topology only; custom equation dependencies are not inferred. Inspect the module contract, source and recorded hazards.",
            }
        else:
            structure = model_structure(registry, scenario)
    return SimulationResult(
        scenario.name,
        scenario.years,
        validation_only,
        starting,
        total,
        cumulative,
        {s: float(stocks[:, i].sum() / total) if total else 0 for i, s in enumerate(states)},
        annual,
        cohorts,
        metadata,
        {
            "history": history,
            "structure": structure,
            "state_definitions": metric_contract(scenario.health_structure)["states"],
            "cohort_semantics": "Age cells after each annual step; 100+ is pooled, not a birth cohort",
        }
        if diagnostics
        else None,
        {
            "definition": metric_contract(scenario.health_structure),
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
        {
            "definition": scenario.health_structure,
            "validation_only": True,
            "initial_prechronic_cohort": initial_pc.report(),
            "future_t2d_entries": annual[-1]["t2d_incidence_from_initial_prechronic"],
            "share_of_future_t2d_entries": annual[-1]["t2d_incidence_from_initial_prechronic"]
            / annual[-1]["cumulative_t2d_incidence"]
            if annual[-1]["cumulative_t2d_incidence"]
            else None,
            "interpretation": "Future T2D entries among people initially in the synthetic PreChronic stock; cohort accounting, not causal attributable burden or calibrated prediction",
        }
        if initial_pc is not None
        else None,
    )


def model_structure(registry: EvidenceRegistry, scenario: Scenario | None = None) -> dict:
    """Describe the implemented dependency graph; edges are not causal validation."""
    scenario = scenario or Scenario(name="structure", exposures={})
    states = states_for(scenario)
    transitions = [dict(t) for t in transitions_for(scenario)]
    transitions.extend(
        {
            "source": s,
            "target": "dead",
            "flow": f"{s}_deaths",
            "parameter": {
                "insulin_resistant": "mortality_ir_ratio",
                "prediabetes": "mortality_ir_ratio",
                "prechronic": "mortality_pc_ratio",
                "t2d": "mortality_t2d_ratio",
            }.get(s),
        }
        for s in states
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
    if scenario.health_structure != "legacy":
        for edge in dependencies:
            if edge["target"] == "mortality_schedule" and edge["source"] == "state_shares":
                edge["parameters"].append("mortality_pc_ratio")
        dependencies = [
            edge
            for edge in dependencies
            if not any(
                key in ("healthy_to_ir", "ir_to_t2d", "ir_to_healthy")
                for key in (edge["source"], edge["target"])
            )
        ]
        for edge in transitions_for(scenario):
            dependencies.append(
                {
                    "source": edge["flow"],
                    "target": "state_shares",
                    "parameters": [edge["parameter"]],
                }
            )
            if edge["flow"] in (
                "healthy_to_prechronic",
                "prechronic_to_prediabetes",
                "prediabetes_to_t2d",
            ):
                dependencies.append(
                    {
                        "source": "lagged_response",
                        "target": edge["flow"],
                        "parameters": [edge["parameter"]],
                    }
                )
    if scenario.diet_response.kind == "dynamic":
        extra = list(response_units(scenario))
        progression_keys = [
            k for k in extra if k not in ("beta_upf_recovery", "diet_recovery_lag_years")
        ]
        dependencies[0]["parameters"].extend(progression_keys)
        dependencies.append(
            {
                "source": "upf_exposure",
                "target": "recovery_response",
                "parameters": ["beta_upf_recovery", "diet_recovery_lag_years"]
                + (
                    ["diet_half_saturation"] if scenario.diet_response.shape == "saturating" else []
                ),
            }
        )
        reverse = (
            ("ir_to_healthy",)
            if scenario.health_structure == "legacy"
            else ("prechronic_to_healthy", "prediabetes_to_prechronic")
        )
        dependencies.extend(
            {"source": "recovery_response", "target": flow, "parameters": []} for flow in reverse
        )
    if scenario.glp1:
        dependencies.extend(
            [
                {
                    "source": "glp1_eligibility_access",
                    "target": "glp1_treatment_stocks",
                    "parameters": [
                        "glp1_eligible_fraction",
                        "glp1_initiation_rate",
                        "glp1_reinitiation_rate",
                        "glp1_discontinuation_rate",
                        "glp1_discontinuation_t2d_rate",
                        "glp1_affordability_scale",
                        "glp1_low_response_share",
                    ],
                },
                {
                    "source": "glp1_treatment_stocks",
                    "target": "glp1_response",
                    "parameters": [
                        "glp1_response_lag",
                        "glp1_washout_lag",
                        "glp1_low_response_factor",
                    ],
                },
                {
                    "source": "glp1_response",
                    "target": "glp1_weight_proxy",
                    "parameters": ["glp1_weight_loss"],
                },
                {
                    "source": "glp1_response",
                    "target": "glp1_intake_proxy",
                    "parameters": ["glp1_intake_reduction"],
                },
                *[
                    {
                        "source": "glp1_weight_proxy",
                        "target": t["flow"],
                        "parameters": [
                            "glp1_progression_beta"
                            if states.index(t["target"]) > states.index(t["source"])
                            else "glp1_recovery_beta",
                        ],
                    }
                    for t in transitions_for(scenario)
                ],
            ]
        )
    return {
        "states": list(states) + ["dead"],
        "transitions": transitions,
        "dependencies": dependencies,
        "evidence": {
            k: registry.parameters[k].model_dump(mode="json") for k in required_units(scenario)
        },
        "interpretation": "Implemented dependencies and state transitions; synthetic edges are not established causal effects",
    }
