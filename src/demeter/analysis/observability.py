"""Run canonical instrumentation once; rendering can subsequently stay offline."""

from __future__ import annotations

from copy import deepcopy
import json

from demeter.analysis.experiments import sensitivity, uncertainty
from demeter.analysis.historical import historical_backtest, provenance
from demeter.analysis.diet_response import historical_lag_challenge
from demeter.data.glp1 import load_glp1
from demeter.data.ingest import BUNDLE
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
    manifest = json.loads((BUNDLE / "manifest.json").read_bytes())
    return {
        "schema_version": 1,
        "kind": "demeter_observability",
        "metadata": provenance(),
        "evidence_context": {
            "datasets": deepcopy(
                {
                    key: registry.datasets[key]
                    for key in ("us_population", "us_mortality", "diet_response_challenge")
                    if key in registry.datasets
                }
            ),
            "baseline_sources": {
                key: row
                for key, row in manifest["sources"].items()
                if key == "census_2025.csv"
                or (row.get("year") == scenario.baseline_year and row.get("sex") == scenario.sex)
            },
        },
        "simulation": simulate(registry, scenario, diagnostics=True).to_dict(),
        "uncertainty": uncertainty(registry, scenario, draws, seed, diagnostics=True),
        "sensitivity": sensitivity(registry, scenario, samples=samples, seed=seed),
        "historical": historical_backtest(registry),
        **({"glp1_benchmarks": load_glp1(registry)} if scenario.glp1 else {}),
        **(
            {"diet_lag_challenge": historical_lag_challenge(registry)}
            if scenario.diet_response.kind == "dynamic"
            else {}
        ),
    }
