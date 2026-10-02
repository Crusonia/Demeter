"""Explicit alternative health structures; new rates remain synthetic fixtures."""

from __future__ import annotations

import numpy as np

from demeter.health.transitions import (
    STATES,
    TRANSITIONS,
    _split_competing_exits,
    transition_survivors,
)

PRECHRONIC_STATES = ("healthy", "prechronic", "prediabetes", "t2d")
PRECHRONIC_TRANSITIONS = (
    {
        "source": "healthy",
        "target": "prechronic",
        "flow": "healthy_to_prechronic",
        "parameter": "h_to_pc_rate",
    },
    {
        "source": "prechronic",
        "target": "healthy",
        "flow": "prechronic_to_healthy",
        "parameter": "pc_to_h_rate",
    },
    {
        "source": "prechronic",
        "target": "prediabetes",
        "flow": "prechronic_to_prediabetes",
        "parameter": "pc_to_pd_rate",
    },
    {
        "source": "prediabetes",
        "target": "prechronic",
        "flow": "prediabetes_to_prechronic",
        "parameter": "pd_to_pc_rate",
    },
    {
        "source": "prediabetes",
        "target": "t2d",
        "flow": "prediabetes_to_t2d",
        "parameter": "ir_to_t2d_rate",
    },
)
PRECHRONIC_UNITS = {
    "h_to_pc_rate": "hazard_per_year",
    "pc_to_h_rate": "hazard_per_year",
    "pc_to_pd_rate": "hazard_per_year",
    "pd_to_pc_rate": "hazard_per_year",
    "mortality_pc_ratio": "hazard_ratio",
}


def states_for(scenario) -> tuple[str, ...]:
    return STATES if scenario.health_structure == "legacy" else PRECHRONIC_STATES


def transitions_for(scenario) -> tuple[dict, ...]:
    return TRANSITIONS if scenario.health_structure == "legacy" else PRECHRONIC_TRANSITIONS


def dietary_pathways(scenario) -> tuple[dict, ...]:
    """Flows whose hazards the chosen dietary response can modify."""
    states = states_for(scenario)
    return tuple(
        edge
        for edge in transitions_for(scenario)
        if scenario.diet_response.kind == "dynamic"
        or states.index(edge["target"]) > states.index(edge["source"])
    )


def prechronic_transitions(stocks, *rates, adult_age, by_row=False):
    """One endpoint transition per annual step; exits compete for source survivors."""
    stocks = np.asarray(stocks, dtype=float)
    rates = np.asarray(rates, dtype=float)
    if (
        stocks.ndim != 2
        or stocks.shape[1] != 4
        or rates.shape != (5,)
        or not 0 <= adult_age <= len(stocks)
    ):
        raise ValueError("Invalid four-state transition dimensions or adult boundary")
    if (
        not np.isfinite(stocks).all()
        or (stocks < 0).any()
        or not np.isfinite(rates).all()
        or (rates < 0).any()
    ):
        raise ValueError("Stocks and hazards must be finite and nonnegative")
    output, by_age = stocks.copy(), {}
    for source, state in enumerate(PRECHRONIC_STATES):
        indices = [i for i, edge in enumerate(PRECHRONIC_TRANSITIONS) if edge["source"] == state]
        movements, exits, robust = _split_competing_exits(
            stocks[adult_age:, source], rates[indices]
        )
        if robust:
            # Remove the source exit once: subtracting a dominant cause and
            # then a tiny representable cause can otherwise create negatives.
            output[adult_age:, source] -= exits
        for i, moved in zip(indices, movements, strict=True):
            edge = PRECHRONIC_TRANSITIONS[i]
            if not robust:
                output[adult_age:, source] -= moved
            output[adult_age:, PRECHRONIC_STATES.index(edge["target"])] += moved
            by_age[edge["flow"]] = np.pad(moved, (adult_age, 0))
    flows = {key: float(values.sum()) for key, values in by_age.items()}
    if by_row:
        flows["by_row"] = by_age
    return output, flows


def move(stocks, rates, adult, *, structure="legacy", by_row=False):
    if structure == "legacy":
        return transition_survivors(stocks, *rates, adult, by_row=by_row)
    return prechronic_transitions(stocks, *rates, adult_age=adult, by_row=by_row)


def rates_for(registry, scenario, multiplier, recovery_multiplier=1):
    if scenario.health_structure == "legacy":
        return (
            registry.value("h_to_ir_rate") * multiplier,
            registry.value("ir_to_h_rate") * recovery_multiplier,
            registry.value("ir_to_t2d_rate") * multiplier,
        )
    progression = ("healthy_to_prechronic", "prechronic_to_prediabetes", "prediabetes_to_t2d")
    return tuple(
        registry.value(edge["parameter"])
        * (multiplier if edge["flow"] in progression else recovery_multiplier)
        for edge in PRECHRONIC_TRANSITIONS
    )
