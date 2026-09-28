"""Timing sensitivity and a historical challenge that can expose, not fit away, failure."""

from __future__ import annotations

from math import expm1

from demeter.analysis.experiments import sensitivity
from demeter.data.diet_response import DATASET, load_challenge
from demeter.health.structure import transitions_for
from demeter.model import required_units
from demeter.nutrition.response import TIMING_KEYS
from demeter.schema import EvidenceRegistry, Scenario


def timing_sensitivity(registry: EvidenceRegistry, scenario: Scenario, samples=64, seed=0) -> dict:
    keys = tuple(
        k
        for k in TIMING_KEYS
        if k in required_units(scenario)
        and (
            registry.parameters[k].uncertainty is None
            or registry.parameters[k].uncertainty.kind != "fixed"
        )
    )
    if not keys:
        raise ValueError("No uncertain timing parameters to analyze")
    report = sensitivity(registry, scenario, "healthspan", samples, seed, parameters=keys)
    report["scope"] = (
        "Timing-only Sobol ranking conditional on fixed amplitudes, memory weight, transition rates and population inputs; synthetic ranges, not empirical identification"
    )
    report["timing_ranking"] = report["indices"]
    return report


def historical_lag_challenge(registry: EvidenceRegistry) -> dict:
    source = load_challenge(registry)
    spec = registry.datasets[DATASET]
    rows = source["facts"]["rows"]
    by_arm = {(r["year"], r["arm"]): r for r in rows}
    years = spec["years"]
    gaps = [by_arm[y, "lifestyle"]["value"] - by_arm[y, "control"]["value"] for y in years]
    if not gaps[0] > 0:
        raise ValueError("Historical challenge needs a positive first-year reference contrast")
    normalized = [value / gaps[0] for value in gaps]
    lag = registry.parameters[spec["lag_parameter"]]
    values = {"value": lag.value, "low": lag.uncertainty.low, "high": lag.uncertainty.high}
    curves = []
    for label in spec["curve_candidates"]:
        tau = values[label]
        if tau is None or tau <= 0:
            raise ValueError("Historical challenge needs positive registered lag candidates")
        # This deliberately tests an invalid shortcut, not a disease observation model.
        predicted = [-expm1(-year / tau) / (-expm1(-years[0] / tau)) for year in years]
        curves.append(
            {
                "candidate": label,
                "lag_years": tau,
                "rows": [
                    {
                        "year": year,
                        "observed_normalized_contrast": observed,
                        "shortcut_normalized_response": p,
                        "descriptive_residual": observed - p,
                    }
                    for year, observed, p in zip(years, normalized, predicted, strict=True)
                ],
                "later_point_decline_reproduced": predicted[-1] < predicted[0],
            }
        )
    structures = {}
    for kind in ("legacy", "risk_1", "risk_2"):
        s = Scenario(name="structure_check", health_structure=kind)
        exits = [t for t in transitions_for(s) if t["source"] == "t2d"]
        structures[kind] = {
            "t2d_remission_path_present": bool(exits),
            "outgoing_nonmortality_transitions": exits,
        }
    return {
        "schema_version": 1,
        "validation_only": True,
        "scientific_release_ready": False,
        "source": source,
        "engine_parameters_updated": False,
        "lag_identified": False,
        "hypothesis_tested": "Constant sustained intervention passed through a single positive first-order lag can be used directly as remission prevalence contrast",
        "normalization": "Each descriptive contrast is divided by year-one contrast; each lag curve is divided by its own year-one value. No engine parameter or amplitude is fitted.",
        "observed_contrasts": [
            {"year": y, "difference_percentage_points": g, "normalized": n}
            for y, g, n in zip(years, gaps, normalized, strict=True)
        ],
        "curves": curves,
        "engine_structure_check": structures,
        "point_trajectory_contradicts_shortcut": normalized[-1] < normalized[0]
        and all(not c["later_point_decline_reproduced"] for c in curves),
        "statistical_test": None,
        "interpretation": "Observed point contrasts decline while every positive-lag sustained-step shortcut increases. This rejects that observation shortcut, not the use of lag filters inside a stock/flow model. Repeated-measure covariance is unavailable; no significance or optimal lag is inferred. T2D remission and its observation model remain absent, so this trial cannot calibrate the national engine.",
    }
