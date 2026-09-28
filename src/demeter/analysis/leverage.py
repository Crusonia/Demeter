"""Counterfactual dietary pathway allocation and paired global sensitivity.

Shapley allocations explain this explicit model game, not identified natural
direct/indirect causal effects. Benchmarks and synthetic estimates stay separate.
"""

from __future__ import annotations

from itertools import combinations
from math import factorial, isfinite

import numpy as np
from SALib.analyze import sobol as sobol_analyze
from SALib.sample import sobol as sobol_sample

from demeter.analysis.experiments import sampled_parameters, with_values
from demeter.analysis.historical import historical_backtest, provenance
from demeter.health.structure import dietary_pathways, transitions_for
from demeter.model import model_structure, required_units, simulate, validate_inputs
from demeter.nutrition.exposures import resolve_diet
from demeter.schema import EvidenceRegistry, Scenario

SCALE = "leverage_upf_scale"
METRICS = ("healthspan", "cumulative_t2d_incidence")
UNITS = {
    "healthspan": "period healthy-state years at birth",
    "cumulative_t2d_incidence": "T2D entries over the horizon, people",
}


def food_reference(scenario: Scenario) -> Scenario:
    data = scenario.model_dump()
    data.update(name="food_reference", exposures={"upf": 1.0}, diet={}, upf_schedule=[])
    return Scenario.model_validate(data)


def compatible_food(base, target):
    ignored = {"name", "description", "diet", "exposures", "upf_schedule"}
    if base.model_dump(exclude=ignored) != target.model_dump(exclude=ignored):
        raise ValueError(
            "Food leverage requires identical non-diet assumptions, including GLP-1 policy and response structure"
        )


def scaled_diet(registry, base, target, scale):
    """Change contrast amplitude in relative UPF units, preserving its timing."""
    if not isfinite(scale) or scale < 0:
        raise ValueError("Diet contrast scale must be finite and nonnegative")
    a = resolve_diet(registry, base)["annual_upf"]
    b = resolve_diet(registry, target)["annual_upf"]
    path = [x + scale * (y - x) for x, y in zip(a, b, strict=True)]
    data = target.model_dump()
    data.update(
        exposures={},
        diet={},
        upf_schedule=[
            {"start_year": i + 1, "value": value, "unit": "relative_exposure"}
            for i, value in enumerate(path)
            if i == 0 or value != path[i - 1]
        ],
    )
    result = Scenario.model_validate(data)
    validate_inputs(registry, result)
    return result


def scores(result, scenario):
    incidence_flow = next(e["flow"] for e in transitions_for(scenario) if e["target"] == "t2d")
    return {
        "healthspan": result.annual[-1]["healthspan"],
        "cumulative_t2d_incidence": sum(row.get(incidence_flow, 0.0) for row in result.annual),
    }


def shapley_values(players, values):
    """Exact subset formula; values contain every coalition keyed by frozenset."""
    players = tuple(players)
    if not players or len(players) != len(set(players)):
        raise ValueError("Shapley game needs distinct players")
    expected = {frozenset(c) for n in range(len(players) + 1) for c in combinations(players, n)}
    if set(values) != expected or not all(isfinite(v) for v in values.values()):
        raise ValueError("Shapley game needs finite values for every coalition")
    n = len(players)
    result = {}
    for player in players:
        result[player] = sum(
            factorial(len(s))
            * factorial(n - len(s) - 1)
            / factorial(n)
            * (values[s | {player}] - value)
            for s, value in values.items()
            if player not in s
        )
    delta = values[frozenset(players)] - values[frozenset()]
    if not np.isclose(sum(result.values()), delta, rtol=1e-10, atol=1e-7):
        raise ArithmeticError("Pathway allocation does not reconcile to total change")
    return result


def pathway_game(registry, base, target):
    compatible_food(base, target)
    paths = tuple(e["flow"] for e in dietary_pathways(target))
    values = {}
    for n in range(len(paths) + 1):
        for coalition in combinations(paths, n):
            result = simulate(registry, target, dietary_reference=base, dietary_paths=coalition)
            values[frozenset(coalition)] = scores(result, target)
    contributions = {
        m: shapley_values(paths, {s: v[m] for s, v in values.items()}) for m in METRICS
    }
    return paths, values, contributions


def summary(values):
    low, median, high = np.quantile(np.asarray(values), [0.025, 0.5, 0.975])
    return {"median": float(median), "p2_5": float(low), "p97_5": float(high)}


def evidence(registry, key):
    p = registry.parameters[key]
    return {
        "key": key,
        "status": p.status,
        "grade": p.evidence_grade,
        "unit": p.unit,
        "source": p.source,
        "source_url": p.source_url,
        "unresolved": p.unresolved,
        "uncertainty": p.uncertainty.model_dump() if p.uncertainty else None,
        "role": "scenario_design" if key == SCALE else p.model_role,
        "interpretation": "Sensitivity importance does not change evidence strength",
    }


def sampling_contract(registry, scenario):
    p = registry.parameters[SCALE]
    if (
        p.unit != "scenario_contrast_multiplier"
        or p.model_role != "benchmark_only"
        or p.value != 1
        or p.unresolved
    ):
        raise ValueError(
            "Leverage scale must be a resolved analysis-only coordinate with nominal value one"
        )
    keys = sampled_parameters(registry, scenario)
    if p.uncertainty is None or p.uncertainty.kind != "fixed":
        keys.append(SCALE)
    if any(
        registry.parameters[k].uncertainty is None
        or registry.parameters[k].uncertainty.kind != "uniform"
        for k in keys
    ):
        raise ValueError(
            "Leverage Sobol/Monte Carlo currently require explicit independent uniform distributions"
        )
    if not keys:
        raise ValueError("Leverage analysis needs at least one uncertain input")
    return keys, [
        [registry.parameters[k].uncertainty.low, registry.parameters[k].uncertainty.high]
        for k in keys
    ]


def apply_draw(registry, base, target, keys, row):
    values = dict(zip(keys, row, strict=True))
    scale = values.pop(SCALE, registry.value(SCALE))
    draw = with_values(registry, values)
    return draw, scaled_diet(draw, base, target, scale)


def variance_ranking(registry, problem, values, seed):
    values = np.asarray(values)
    variance = float(np.var(values))
    if variance < 1e-20:
        return {
            "status": "zero_variance",
            "variance": variance,
            "indices": [],
            "interpretation": "Indices undefined for this experiment; not evidence that real-world effects are absent",
        }
    result = sobol_analyze.analyze(problem, values, calc_second_order=False, seed=seed)
    rows = []
    for i, key in enumerate(problem["names"]):
        item = {"parameter": key, "evidence": evidence(registry, key)}
        for label, field in (
            ("first_order", "S1"),
            ("total_order", "ST"),
            ("first_order_conf_half_width", "S1_conf"),
            ("total_order_conf_half_width", "ST_conf"),
        ):
            value = float(result[field][i])
            item[label] = value if isfinite(value) else None
        rows.append(item)
    return {
        "status": "estimated",
        "variance": variance,
        "indices": sorted(
            rows,
            key=lambda r: r["total_order"] if r["total_order"] is not None else -np.inf,
            reverse=True,
        ),
        "interpretation": "Independent input-range variance, including interactions; total-order indices need not sum to one. Bootstrap widths concern estimator noise, not clinical uncertainty. Negative/noisy estimates are retained.",
    }


def structural_cases(registry, base, target):
    null = {"beta_upf_progression": 0.0}
    if target.diet_response.kind == "dynamic":
        null["beta_upf_recovery"] = 0.0
    cases = [
        ("No causal dietary effect (synthetic null)", with_values(registry, null), base, target)
    ]
    if target.diet_response.kind == "dynamic":
        shape = "linear" if target.diet_response.shape == "saturating" else "saturating"
        a, b = base.model_copy(deep=True), target.model_copy(deep=True)
        a.diet_response.shape = b.diet_response.shape = shape
        cases.append((f"Alternative {shape} dose shape", registry, a, b))
    if target.health_structure != "legacy":
        kind = "risk_2" if target.health_structure == "risk_1" else "risk_1"
        cases.append(
            (
                f"Alternative {kind} PreChronic initialization",
                registry,
                base.model_copy(update={"health_structure": kind}),
                target.model_copy(update={"health_structure": kind}),
            )
        )
    return [
        {
            "case": label,
            "paired_delta": {m: y[m] - x[m] for m in METRICS},
            "interpretation": "Separate specified structural experiment; not an uncertainty probability or validated alternative",
        }
        for label, r, a, b in cases
        for x, y in [(scores(simulate(r, a), a), scores(simulate(r, b), b))]
    ]


def leverage(
    registry: EvidenceRegistry,
    target: Scenario,
    *,
    baseline: Scenario | None = None,
    draws=32,
    samples=64,
    seed=0,
):
    if not 2 <= draws <= 256 or not 8 <= samples <= 1024 or samples & (samples - 1) or seed < 0:
        raise ValueError(
            "Leverage requires draws 2-256, power-of-two samples 8-1024, and nonnegative seed"
        )
    base = baseline or food_reference(target)
    compatible_food(base, target)
    keys, bounds = sampling_contract(registry, target)
    if SCALE in keys:
        for endpoint in bounds[keys.index(SCALE)]:
            scaled_diet(registry, base, target, endpoint)
    a, b = simulate(registry, base), simulate(registry, target)
    nominal_base, nominal_target = scores(a, base), scores(b, target)
    paths, coalitions, phi = pathway_game(registry, base, target)
    for metric in METRICS:
        if not np.isclose(
            coalitions[frozenset()][metric], nominal_base[metric], rtol=1e-12, atol=1e-7
        ) or not np.isclose(
            coalitions[frozenset(paths)][metric], nominal_target[metric], rtol=1e-12, atol=1e-7
        ):
            raise ArithmeticError("Empty/full dietary routing must reproduce ordinary scenarios")

    # Same registry/exposure draw is reused for every coalition and both endpoints.
    rng = np.random.default_rng(seed)
    matrix = rng.uniform(np.array(bounds)[:, 0], np.array(bounds)[:, 1], (draws, len(keys)))
    attributed = {m: {p: [] for p in paths} for m in METRICS}
    delta_draws, base_draws, target_draws = ({m: [] for m in METRICS} for _ in range(3))
    max_residual = {m: 0.0 for m in METRICS}
    for row in matrix:
        r, s = apply_draw(registry, base, target, keys, row)
        _, v, allocation = pathway_game(r, base, s)
        for m in METRICS:
            x, y = v[frozenset()][m], v[frozenset(paths)][m]
            base_draws[m].append(x)
            target_draws[m].append(y)
            delta_draws[m].append(y - x)
            max_residual[m] = max(max_residual[m], abs(sum(allocation[m].values()) - (y - x)))
            for p in paths:
                attributed[m][p].append(allocation[m][p])

    # Reuse each Sobol run for both endpoints and both outcome rankings.
    problem = {"num_vars": len(keys), "names": keys, "bounds": bounds}
    design = sobol_sample.sample(problem, samples, calc_second_order=False, seed=seed)
    levels, deltas = ({m: [] for m in METRICS} for _ in range(2))
    for row in design:
        r, s = apply_draw(registry, base, target, keys, row)
        x, y = scores(simulate(r, base), base), scores(simulate(r, s), s)
        for m in METRICS:
            levels[m].append(y[m])
            deltas[m].append(y[m] - x[m])
    sensitivity = {
        m: {
            "intervention_level": variance_ranking(registry, problem, levels[m], seed),
            "paired_delta": variance_ranking(registry, problem, deltas[m], seed),
        }
        for m in METRICS
    }
    edge_map = {e["flow"]: e for e in dietary_pathways(target)}
    attributes = {
        m: [
            {
                "pathway": p,
                "source": edge_map[p]["source"],
                "target": edge_map[p]["target"],
                "nominal": phi[m][p],
                "sampling_interval": summary(attributed[m][p]),
                "transition_parameter": evidence(registry, edge_map[p]["parameter"]),
            }
            for p in paths
        ]
        for m in METRICS
    }
    incidence_flow = next(e["flow"] for e in transitions_for(target) if e["target"] == "t2d")

    def trajectory(result):
        count = 0.0
        rows = []
        for r in result.annual:
            count += r.get(incidence_flow, 0.0)
            rows.append(
                {
                    "year": r["year"],
                    "healthspan": r["healthspan"],
                    "cumulative_t2d_incidence": count,
                }
            )
        return rows

    ontology = registry.datasets["food_exposure_ontology"]["definitions"]
    return {
        "schema_version": 1,
        "kind": "demeter_leverage",
        "validation_only": True,
        "scientific_release_ready": False,
        "provenance": provenance(),
        "metadata": b.metadata,
        "structure": model_structure(registry, target),
        "nominal_annual_endpoint": b.annual[-1],
        "baseline_scenario": base.model_dump(),
        "intervention_scenario": target.model_dump(),
        "units": UNITS,
        "outcomes": {
            m: {
                "baseline": nominal_base[m],
                "intervention": nominal_target[m],
                "absolute_delta": nominal_target[m] - nominal_base[m],
                "relative_delta": (nominal_target[m] - nominal_base[m]) / nominal_base[m]
                if nominal_base[m]
                else None,
                "baseline_interval": summary(base_draws[m]),
                "intervention_interval": summary(target_draws[m]),
                "delta_interval": summary(delta_draws[m]),
            }
            for m in METRICS
        },
        "trajectories": {"baseline": trajectory(a), "intervention": trajectory(b)},
        "attribution": {
            "method": "Exact Shapley allocation of reference-to-intervention dietary hazard switches",
            "interpretation": "Average marginal model contribution across all path orderings; distributes interactions under this reference/game. Not an identified natural direct/indirect effect, causal evidence or unique biological attribution.",
            "paths": list(paths),
            "by_outcome": attributes,
            "coalitions": [
                {"intervention_paths": sorted(s), "outcomes": v} for s, v in coalitions.items()
            ],
            "nominal_residual": {
                m: sum(phi[m].values()) - (nominal_target[m] - nominal_base[m]) for m in METRICS
            },
            "max_draw_residual": max_residual,
            "interval_note": "Paired central 95% parameter/scenario sampling intervals. Contributions reconcile per draw; separate medians and quantiles need not add.",
        },
        "transition_deltas": [
            {**e, "baseline": x, "intervention": y, "absolute_delta": y - x}
            for e in transitions_for(target)
            for x, y in [
                (
                    sum(r.get(e["flow"], 0) for r in a.annual),
                    sum(r.get(e["flow"], 0) for r in b.annual),
                )
            ]
        ],
        "state_person_year_deltas": {
            s: b.healthspan["restricted_cohort"]["state_person_years"][s] - value
            for s, value in a.healthspan["restricted_cohort"]["state_person_years"].items()
        },
        "sensitivity": sensitivity,
        "sampling": {
            "draws": draws,
            "base_samples": samples,
            "seed": seed,
            "parameters": keys,
            "parameter_draws": dict(zip(keys, matrix.T.tolist(), strict=True)),
            "coalition_simulations": (draws + 1) * 2 ** len(paths),
            "sobol_simulations": 2 * len(design),
            "assumptions": "Independent registered uniforms; scenario contrast strength varies while timing and non-diet policy are held fixed. No empirical uncertainty, covariance or full structural uncertainty is claimed.",
        },
        "evidence_overlay": [evidence(registry, k) for k in [*required_units(target), SCALE]],
        "priority_evidence_gaps": {
            m: [
                r
                for r in sensitivity[m]["paired_delta"]["indices"]
                if r["evidence"]["status"] == "synthetic"
                or r["evidence"]["unresolved"]
                or r["evidence"]["grade"] in ("C", "D", "E")
            ]
            for m in METRICS
        },
        "direct_versus_mediated": {
            "direct_food_to_mortality": {
                "implemented": False,
                "model_contribution": 0.0,
                "empirical_effect": None,
                "interpretation": "Absent structural link, not an estimated zero biological effect",
            },
            "implemented_route": "Food response -> competing metabolic transitions -> health composition -> morbidity weighting and state-sensitive mortality -> period healthspan",
            "mortality_and_morbidity_shares": None,
            "limitation": "Path allocations include all downstream model consequences. They do not separately identify natural mediation through morbidity versus mortality.",
        },
        "structural_experiments": structural_cases(registry, base, target),
        "unranked_structural_gaps": {
            "inactive_food_exposures": [
                {
                    "exposure": k,
                    "availability": v["availability"],
                    "limitation": v.get("limitation", "No active causal effect"),
                }
                for k, v in ontology.items()
                if k != "upf"
            ],
            "limitations": [
                "Only UPF has an active dietary hazard mapping; absent exposures are not zero-effect findings.",
                "No calibrated food-to-transition effects, age response, disease remission or national historical observation model.",
                "Covariance, causal transport and omitted mechanisms cannot be ranked by the implemented parameter variance.",
                "GLP-1 policy is held fixed; endogenous treatment composition may still respond to altered health states.",
            ],
        },
        "historical": historical_backtest(registry),
        "historical_scope": "Observed-versus-predicted persistence/trend holdouts provide historical context; they are not validation of these dietary pathways or their attribution.",
    }
