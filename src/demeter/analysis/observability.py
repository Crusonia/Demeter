"""Run canonical instrumentation once; rendering can subsequently stay offline."""

from __future__ import annotations

from demeter.analysis.experiments import sensitivity, uncertainty
from demeter.analysis.historical import historical_backtest, provenance
from demeter.analysis.diet_response import historical_lag_challenge
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario


def observe(
    registry: EvidenceRegistry,
    scenario: Scenario,
    *,
    draws: int = 64,
    samples: int = 32,
    seed: int = 0,
) -> dict:
    return {
        "schema_version": 1,
        "kind": "demeter_observability",
        "metadata": provenance(),
        "simulation": simulate(registry, scenario, diagnostics=True).to_dict(),
        "uncertainty": uncertainty(registry, scenario, draws, seed, diagnostics=True),
        "sensitivity": sensitivity(registry, scenario, samples=samples, seed=seed),
        "historical": historical_backtest(registry),
        **(
            {"diet_lag_challenge": historical_lag_challenge(registry)}
            if scenario.diet_response.kind == "dynamic"
            else {}
        ),
    }
