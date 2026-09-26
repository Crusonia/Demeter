from __future__ import annotations

import numpy as np
from SALib.analyze import sobol as sobol_analyze
from SALib.sample import sobol as sobol_sample

from demeter.model import REQUIRED_UNITS, simulate
from demeter.schema import EvidenceRegistry, Scenario

OUTCOMES = ("life_expectancy", "metabolically_healthy_life_expectancy", "cumulative_deaths")


def sampled_parameters(registry: EvidenceRegistry) -> list[str]:
    keys = []
    for key in REQUIRED_UNITS:
        u = registry.parameters[key].uncertainty
        if u is None or u.kind in ("range", "interval"):
            raise ValueError(
                f"{key} needs an explicit sampling distribution; an interval is insufficient"
            )
        if u.kind != "fixed":
            keys.append(key)
    return keys


def with_values(registry: EvidenceRegistry, values: dict[str, float]) -> EvidenceRegistry:
    data = registry.model_dump()
    for key, value in values.items():
        data["parameters"][key]["value"] = float(value)
    return EvidenceRegistry.model_validate(data)


def compatible(left: Scenario, right: Scenario) -> None:
    if (left.years, left.baseline_year, left.sex, left.mode) != (
        right.years,
        right.baseline_year,
        right.sex,
        right.mode,
    ):
        raise ValueError("comparison requires the same horizon, mortality vintage, sex, and mode")


def compare(registry: EvidenceRegistry, left: Scenario, right: Scenario) -> dict:
    compatible(left, right)
    base, intervention = simulate(registry, left), simulate(registry, right)
    changes = {}
    for metric in OUTCOMES:
        a, b = base.annual[-1][metric], intervention.annual[-1][metric]
        changes[metric] = {
            "baseline": a,
            "intervention": b,
            "absolute_delta": b - a,
            "relative_delta": (b - a) / a if a else None,
        }
    return {
        "validation_only": base.validation_only or intervention.validation_only,
        "baseline": left.name,
        "intervention": right.name,
        "outcomes": changes,
        "metadata": base.metadata,
        "intervention_scenario": right.model_dump(),
    }


def uncertainty(
    registry: EvidenceRegistry,
    scenario: Scenario,
    draws: int = 128,
    seed: int = 0,
    *,
    diagnostics: bool = False,
) -> dict:
    if not 2 <= draws <= 10000 or seed < 0:
        raise ValueError("draws must be 2–10000 and seed nonnegative")
    keys = sampled_parameters(registry)
    rng = np.random.default_rng(seed)
    baseline = scenario.model_copy(update={"name": "paired_baseline", "exposures": {"upf": 1.0}})
    collected = {key: [] for key in OUTCOMES}
    deltas = {key: [] for key in OUTCOMES}
    trajectories = {key: [] for key in OUTCOMES}
    parameter_draws = {key: [] for key in keys}
    metadata = simulate(registry, scenario).metadata
    for _ in range(draws):
        values = {}
        for key in keys:
            p = registry.parameters[key]
            u = p.uncertainty
            values[key] = (
                rng.uniform(u.low, u.high) if u.kind == "uniform" else rng.normal(p.value, u.sd)
            )
        draw = with_values(registry, values)
        a, b = simulate(draw, baseline), simulate(draw, scenario)
        if diagnostics:
            for key in keys:
                parameter_draws[key].append(float(values[key]))
            for key in OUTCOMES:
                trajectories[key].append([r[key] for r in b.annual])
        for key in OUTCOMES:
            collected[key].append(b.annual[-1][key])
            deltas[key].append(b.annual[-1][key] - a.annual[-1][key])

    def summarize(values):
        low, median, high = np.quantile(values, [0.025, 0.5, 0.975])
        return {"median": float(median), "p2_5": float(low), "p97_5": float(high)}

    result = {
        "metadata": metadata,
        "validation_only": scenario.mode == "validation",
        "seed": seed,
        "draws": draws,
        "sampled_parameters": keys,
        "fixed_parameters": [k for k in REQUIRED_UNITS if k not in keys],
        "interval_type": "central 95% parameter-sampling interval; synthetic ranges, not empirical confidence",
        "assumptions": "Independent parameters, fixed scenario, paired baseline uses identical draws; no structural uncertainty",
        "outcomes": {k: summarize(v) for k, v in collected.items()},
        "paired_deltas": {k: summarize(v) for k, v in deltas.items()},
    }
    if diagnostics:
        result["parameter_draws"] = parameter_draws
        result["annual_intervals"] = {
            k: [
                {"year": year, **summarize(np.array(v)[:, year])}
                for year in range(scenario.years + 1)
            ]
            for k, v in trajectories.items()
        }
    return result


def sensitivity(
    registry: EvidenceRegistry,
    scenario: Scenario,
    outcome: str = "life_expectancy",
    samples: int = 64,
    seed: int = 0,
) -> dict:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    if samples < 8 or samples > 1024 or samples & (samples - 1) or seed < 0:
        raise ValueError("samples must be a power of two from 8 to 1024 and seed nonnegative")
    keys = sampled_parameters(registry)
    if not keys:
        raise ValueError("no uncertain parameters to analyze")
    if any(registry.parameters[k].uncertainty.kind != "uniform" for k in keys):
        raise ValueError(
            "Sobol analysis currently requires independent uniform parameter distributions"
        )
    bounds = [
        [registry.parameters[k].uncertainty.low, registry.parameters[k].uncertainty.high]
        for k in keys
    ]
    problem = {"num_vars": len(keys), "names": keys, "bounds": bounds}
    matrix = sobol_sample.sample(problem, samples, calc_second_order=False, seed=seed)
    y = np.array(
        [
            simulate(with_values(registry, dict(zip(keys, row, strict=True))), scenario).annual[-1][
                outcome
            ]
            for row in matrix
        ]
    )
    if float(np.var(y)) < 1e-20:
        raise ValueError("outcome variance is zero; Sobol indices are undefined")
    result = sobol_analyze.analyze(problem, y, calc_second_order=False, seed=seed)
    indices = [
        {
            "parameter": key,
            "first_order": float(result["S1"][i]),
            "total_order": float(result["ST"][i]),
            "first_order_conf_half_width": float(result["S1_conf"][i]),
            "total_order_conf_half_width": float(result["ST_conf"][i]),
        }
        for i, key in enumerate(keys)
    ]
    return {
        "metadata": simulate(registry, scenario).metadata,
        "outcome": outcome,
        "method": "SALib Sobol",
        "seed": seed,
        "base_samples": samples,
        "model_evaluations": len(y),
        "interpretation": "Variance under independent synthetic parameter ranges; indices may be noisy at small N",
        "indices": sorted(indices, key=lambda item: item["total_order"], reverse=True),
    }
