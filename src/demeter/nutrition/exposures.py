"""Observed dietary context is distinct from the synthetic health-response pathway."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from demeter.data.dietary import load_dietary, reference_value
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.nutrition.response import DYNAMIC_UNITS, SATURATION_UNITS
from demeter.schema import EvidenceRegistry, ExposureId, Scenario, StrictModel

ONTOLOGY = "food_exposure_ontology"


class ExposureDefinition(StrictModel):
    kind: Literal["food_category", "nutrient", "energy", "quality_index"]
    unit: str | None
    definition: str = Field(min_length=1)
    availability: Literal["active_validation", "observed_context", "unresolved"]
    physical_min: float | None = None
    physical_max: float | None = None
    baseline_available: bool = False
    effect_parameters: list[str] = Field(default_factory=list)
    overlap: list[ExposureId] = Field(default_factory=list)
    limitation: str = Field(min_length=1)

    @model_validator(mode="after")
    def coherent(self):
        if self.availability != "unresolved" and (not self.unit or not self.baseline_available):
            raise ValueError("Available exposures require units and observed baselines")
        if bool(self.effect_parameters) != (self.availability == "active_validation"):
            raise ValueError("Only active validation exposures may have effect parameters")
        if (
            self.physical_min is not None
            and self.physical_max is not None
            and self.physical_min >= self.physical_max
        ):
            raise ValueError("Invalid physical exposure bounds")
        return self


class ExposureOntology(StrictModel):
    schema_version: Literal[1]
    status: Literal["derived"]
    evidence_grade: Literal["C"]
    model_role: Literal["exposure_contract"]
    baseline_dataset: Literal["dietary_baselines"]
    definitions: dict[ExposureId, ExposureDefinition]


def ontology(registry: EvidenceRegistry) -> ExposureOntology:
    contract = ExposureOntology.model_validate(registry.datasets[ONTOLOGY])
    # This is an implementation guard, not a generic plug-in effect registry.
    active = {
        k: v.effect_parameters for k, v in contract.definitions.items() if v.effect_parameters
    }
    if active != {"upf": ["beta_upf_progression", "diet_lag_years"]}:
        raise ValueError("Unimplemented or overlapping dietary effect pathway")
    for key in active["upf"]:
        if key not in registry.parameters or registry.parameters[key].model_role != "health_model":
            raise ValueError(f"Missing active dietary evidence: {key}")
    for definition in contract.definitions.values():
        if set(definition.overlap) - contract.definitions.keys():
            raise ValueError("Unknown overlapping exposure")
    return contract


def catalog(registry: EvidenceRegistry) -> dict:
    contract = ontology(registry)
    baselines = load_dietary(registry)
    return {
        **contract.model_dump(),
        "baseline_definition_sha256": baselines["provenance"]["definition_sha256"],
        "baseline_periods": sorted({r["period"] for r in baselines["rows"]}),
        "relative_upf_envelope": {
            "low": registry.parameters["upf_min_multiplier"].model_dump(mode="json"),
            "high": registry.parameters["upf_max_multiplier"].model_dump(mode="json"),
            "interpretation": "Synthetic validation envelope, not a causal evidence-supported dose range",
        },
        "effect_evidence": {
            k: registry.parameters[k].model_dump(mode="json")
            for k in contract.definitions["upf"].effect_parameters
        },
        "optional_dynamic_response_evidence": {
            k: registry.parameters[k].model_dump(mode="json")
            for k in {**DYNAMIC_UNITS, **SATURATION_UNITS}
        },
        "transition_mapping": {
            "legacy": ["healthy_to_ir", "ir_to_t2d"],
            "prechronic": [
                "healthy_to_prechronic",
                "prechronic_to_prediabetes",
                "prediabetes_to_t2d",
            ],
        },
        "overlap_policy": "Only UPF drives health transitions. Other observed changes require explicit context_only; no independent additive effects or composite scores.",
        "scientific_release_ready": False,
    }


def resolve_diet(registry: EvidenceRegistry, scenario: Scenario) -> dict:
    """Normalize explicit absolute targets without silently activating correlated effects."""
    contract = ontology(registry)
    # Revalidate after model_copy/dict edits; those can bypass Pydantic validators.
    scenario = Scenario.model_validate(scenario.model_dump())
    baselines = (
        load_dietary(registry)
        if scenario.diet or any(step.unit == "percent_energy" for step in scenario.upf_schedule)
        else None
    )
    multiplier = scenario.exposures.get("upf", 1.0)
    changes = {}
    for key, change in scenario.diet.items():
        definition = contract.definitions[key]
        if definition.availability == "unresolved":
            raise ValueError(f"Unresolved dietary definition/baseline: {key}")
        if change.unit != definition.unit:
            raise ValueError(f"{key} requires unit {definition.unit}")
        if (definition.physical_min is not None and change.target < definition.physical_min) or (
            definition.physical_max is not None and change.target > definition.physical_max
        ):
            raise ValueError(f"{key} target outside physical range")
        if change.role == "model_effect" and definition.availability != "active_validation":
            raise ValueError(
                f"No independently identified health effect for {key}; use context_only"
            )
        reference = reference_value(baselines, key, change.reference_period, scenario.sex)
        if change.unit != reference["unit"]:
            raise ValueError(f"{key} ontology unit does not match its observed reference")
        if change.role == "model_effect":
            if reference["mean"] <= 0:
                raise ValueError("Active dietary reference must be positive")
            multiplier = change.target / reference["mean"]
        changes[key] = {
            **change.model_dump(),
            "reference": reference,
            "absolute_change": change.target - reference["mean"],
            "applied_to_health": change.role == "model_effect",
            "target_status": "scenario_assumption",
        }
    path = [multiplier] * scenario.years
    schedule = []
    for step in scenario.upf_schedule:
        reference = None
        value = step.value
        if step.unit == "percent_energy":
            bounds = contract.definitions["upf"]
            if not bounds.physical_min <= value <= bounds.physical_max:
                raise ValueError("UPF schedule target outside physical range")
            reference = reference_value(baselines, "upf", step.reference_period, scenario.sex)
            if reference["unit"] != step.unit or reference["mean"] <= 0:
                raise ValueError("UPF schedule reference units or mean invalid")
            value /= reference["mean"]
        path[step.start_year - 1 :] = [value] * (scenario.years - step.start_year + 1)
        schedule.append({**step.model_dump(), "relative_upf": value, "reference": reference})
    return {
        "upf_multiplier": multiplier,
        "annual_upf": path,
        "schedule": schedule,
        "changes": changes,
        "ontology_sha256": digest(encoded(registry.datasets[ONTOLOGY])),
        "baseline_definition_sha256": baselines["provenance"]["definition_sha256"]
        if baselines
        else None,
        "baseline_bundle_sha256": digest(encoded(baselines)) if baselines else None,
        "reference_uncertainty_propagated": False,
        "limitations": [
            "Observed baselines do not establish causal effects; effect and lag remain synthetic.",
            "Reference means are held fixed; sampling SEs and descriptive intake distributions are retained, not sampled as independent causal parameters.",
            "Absolute changes are targets, not a mass-balanced food substitution or energy-balance model.",
            "Context-only targets do not alter health; absence of an implemented effect is not evidence of no effect.",
            "Adult survey references do not initialize individual diets: UPF is 19+, nutrients 20+, and the engine adult threshold is separately registered; age, period and population transport remain unresolved.",
        ],
    }
