"""Typed local experiments over the canonical engine; never edit source evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field
import yaml

from demeter.extensions import curated
from demeter.health.glp1 import validate_glp1
from demeter.model import required_units, validate_inputs
from demeter.nutrition.exposures import resolve_diet
from demeter.nutrition.response import DietaryResponse
from demeter.releases import RunSettings
from demeter.schema import EvidenceRegistry, Scenario, StrictModel

# These define applicability rather than an experimental response.
READ_ONLY = {"upf_min_multiplier", "upf_max_multiplier"}
PROFILES = {"preview": {"draws": 4, "samples": 8}, "standard": {"draws": 64, "samples": 32}}


class ParameterEdit(StrictModel):
    value: float
    low: float | None = None
    high: float | None = None


class Experiment(StrictModel):
    catalog_id: str
    scenario: Scenario
    overrides: dict[str, ParameterEdit] = Field(default_factory=dict, max_length=100)
    profile: Literal["preview", "standard"] = "preview"
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)
    reference_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    prediction: str = Field(default="", max_length=4000)
    notes: str = Field(default="", max_length=4000)


def scenario_catalog(root: Path) -> list[dict]:
    records = []
    for package_id, package in curated(root).items():
        for key in package.manifest.scenarios:
            scenario = package.scenario(key)
            records.append(
                {
                    "id": package_id + "/" + key,
                    "label": key.replace("_", " ").capitalize(),
                    "classification": package.classification,
                    "package": package_id,
                    "manifest_sha256": package.manifest_sha256,
                    "scenario": scenario.model_dump(mode="json"),
                }
            )
    if not records:
        raise ValueError("Open a Demeter source checkout containing extensions/catalog.yaml")
    return records


def registry_for(root: Path) -> EvidenceRegistry:
    return EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")


def editable_parameters(registry: EvidenceRegistry, scenario: Scenario) -> dict:
    return {
        key: registry.parameters[key].model_dump(mode="json")
        for key in required_units(scenario)
        if key not in READ_ONLY
        and registry.parameters[key].status == "synthetic"
        and registry.parameters[key].model_role == "health_model"
        and not registry.parameters[key].unresolved
    }


def resolve_experiment(root: Path, request: Experiment) -> tuple[EvidenceRegistry, dict]:
    entry = next((r for r in scenario_catalog(root) if r["id"] == request.catalog_id), None)
    if entry is None:
        raise ValueError("Choose a scenario from the reviewed project catalog")
    scenario = request.scenario
    if scenario.mode != "validation" or scenario.allow_extrapolation:
        raise ValueError(
            "The learning interface supports validation mode within the exposure envelope"
        )
    base = registry_for(root)
    editable = editable_parameters(base, scenario)
    data = base.model_dump(mode="json")
    for key, edit in request.overrides.items():
        if key not in editable:
            raise ValueError(f"{key}: only active synthetic response assumptions can be edited")
        parameter = data["parameters"][key]
        parameter["value"] = edit.value
        u = parameter["uncertainty"]
        if edit.low is not None or edit.high is not None:
            if u is None or u["kind"] != "uniform" or edit.low is None or edit.high is None:
                raise ValueError(f"{key}: supply both bounds of an existing uniform distribution")
            u.update(
                low=edit.low,
                high=edit.high,
                rationale="User-specified synthetic range for a saved local experiment",
            )
        if u and u["kind"] == "uniform" and not u["low"] <= edit.value <= u["high"]:
            raise ValueError(f"{key}: nominal value must be within its stated sampling range")
        parameter["notes"] = (parameter.get("notes") or "") + " Local experiment override."
    resolved = EvidenceRegistry.model_validate(data)
    validate_inputs(resolved, scenario)
    # Check each editable interval endpoint through the same model validators. This
    # catches invalid lags/fractions that the nominal value alone would not expose.
    for key in request.overrides:
        p = resolved.parameters[key]
        if p.uncertainty and p.uncertainty.kind == "uniform":
            for endpoint in (p.uncertainty.low, p.uncertainty.high):
                probe = resolved.model_dump()
                probe["parameters"][key]["value"] = endpoint
                boundary = EvidenceRegistry.model_validate(probe)
                validate_inputs(boundary, scenario)
                DietaryResponse(boundary, scenario)
                if scenario.glp1:
                    validate_glp1(boundary)
    # Dynamic/GLP validation is also exercised by a canonical nominal simulation
    # during validation; it doesn't write source files or launch a worker.
    from demeter.model import simulate

    simulate(resolved, scenario)
    settings = RunSettings(seed=request.seed, **PROFILES[request.profile])
    return resolved, {
        "catalog": entry,
        "settings": settings.model_dump(),
        "base_evidence_sha256": base.content_hash,
        "resolved_evidence_sha256": resolved.content_hash,
        "exposure": resolve_diet(resolved, scenario),
    }


def reference_scenario(scenario: Scenario) -> Scenario:
    raw = scenario.model_dump()
    raw.update(
        name="No-intervention reference",
        description="Same population, horizon and structure; "
        "no dietary or GLP-1 intervention; original evidence assumptions.",
        exposures={"upf": 1.0},
        diet={},
        upf_schedule=[],
        glp1=None,
    )
    return Scenario.model_validate(raw)


def assumptions_diff(left: dict, right: dict, prefix: str = "") -> list[dict]:
    changes = []
    for key in sorted(left.keys() | right.keys()):
        path, a, b = prefix + key, left.get(key), right.get(key)
        if isinstance(a, dict) and isinstance(b, dict):
            changes.extend(assumptions_diff(a, b, path + "."))
        elif a != b:
            changes.append({"field": path, "reference": a, "experiment": b})
    return changes


def compare_payloads(left: dict, right: dict) -> dict:
    from demeter.analysis.experiments import compatible, outcomes_for

    a, b = Scenario.model_validate(left["scenario"]), Scenario.model_validate(right["scenario"])
    compatible(a, b)
    # One common definition/version is required; independent uncertainty bands are
    # retained separately and no difference interval is manufactured.
    if left["code"] != right["code"]:
        raise ValueError("Comparison requires the same engine source fingerprint")
    first, last = left["simulation"]["annual"][-1], right["simulation"]["annual"][-1]
    rows = [
        {
            "metric": key,
            "unit": "people"
            if key
            in (
                "cumulative_deaths",
                "cumulative_t2d_incidence",
                "t2d_incidence_from_initial_prechronic",
            )
            else "years",
            "reference": first[key],
            "experiment": last[key],
            "absolute_delta": last[key] - first[key],
            "relative_delta": (last[key] - first[key]) / first[key] if first[key] else None,
        }
        for key in outcomes_for(a)
    ]
    return {
        "reference_label": left["label"],
        "experiment_label": right["label"],
        "year": b.years,
        "outcomes": rows,
        "assumptions": assumptions_diff(
            {"scenario": left["scenario"], "overrides": left["overrides"]},
            {"scenario": right["scenario"], "overrides": right["overrides"]},
        ),
        "interval_note": "Nominal contrasts only. Separate uncertainty bands cannot be "
        "subtracted to create a difference interval.",
        "validation_only": True,
    }


def yaml_text(value: dict) -> str:
    # JSON roundtrip keeps only portable scalars and actual numeric values.
    return yaml.safe_dump(json.loads(json.dumps(value)), sort_keys=False, allow_unicode=True)
