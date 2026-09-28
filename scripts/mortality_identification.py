"""Reproduce the validation-only counterexample to aggregate identification.

Uses registered synthetic uncertainty endpoints, never fits clinical parameters.
Run from the repository root with ``uv run python scripts/mortality_identification.py``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from demeter.data.baseline import source_rows
from demeter.model import simulate
from demeter.population.mechanics import calibrate_mortality, period_outcomes
from demeter.schema import EvidenceRegistry, Scenario

ROOT = Path(__file__).resolve().parents[1]


def diagnostic(registry: EvidenceRegistry, scenario: Scenario) -> dict:
    rows = source_rows(scenario.baseline_year, scenario.sex)
    shares = np.tile(
        [registry.value(f"initial_{state}_share") for state in ("healthy", "ir", "t2d")],
        (len(rows), 1),
    )
    shares[: int(registry.value("adult_age"))] = [1.0, 0.0, 0.0]
    demonstrations = []
    for endpoint in ("low", "high"):
        candidate = registry.model_copy(deep=True)
        for key in ("mortality_ir_ratio", "mortality_t2d_ratio"):
            parameter = candidate.parameters[key]
            if parameter.status != "synthetic":
                raise ValueError(f"This demonstration requires a synthetic {key}")
            value = getattr(parameter.uncertainty, endpoint)
            if value is None:
                raise ValueError(f"Missing registered {endpoint} endpoint for {key}")
            parameter.value = value
        ir = candidate.value("mortality_ir_ratio")
        t2d = candidate.value("mortality_t2d_ratio")
        hazards = calibrate_mortality(rows, shares, np.array([1.0, ir, t2d]))
        predicted_qx = (shares[:-1] * -np.expm1(-hazards[:-1])).sum(axis=1)
        outcomes = period_outcomes(rows, shares, hazards)
        result = simulate(candidate, scenario)
        demonstrations.append(
            {
                "registered_stress_endpoint": endpoint,
                "mortality_ir_ratio": ir,
                "mortality_t2d_ratio": t2d,
                "maximum_age_0_99_qx_error": float(
                    np.max(np.abs(predicted_qx - [row["qx"] for row in rows[:-1]]))
                ),
                "initial_period_life_expectancy": outcomes["life_expectancy"],
                "terminal_e100_error": float(
                    abs(np.sum(shares[-1] / hazards[-1]) - rows[-1]["ex"])
                ),
                "ending_period_life_expectancy": result.annual[-1]["life_expectancy"],
                "cumulative_deaths": result.cumulative_deaths,
            }
        )
    return {
        "purpose": "Computational non-identification demonstration; not fitted clinical evidence",
        "validation_only": True,
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "evidence_sha256": registry.content_hash,
        "scenario": scenario.model_dump(mode="json"),
        "parameter_selection": (
            "Endpoints of existing registered synthetic mortality-ratio uncertainty; "
            "all remaining inputs unchanged"
        ),
        "demonstrations": demonstrations,
        "conclusion": (
            "Different state hazard ratios reproduce the same initial age-specific mortality "
            "and life expectancy, yet yield different later trajectories. Aggregate life-table "
            "fit cannot identify state mortality decomposition. No parameter is promoted."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs/mortality-identification.json"
    )
    args = parser.parse_args()
    report = diagnostic(
        EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml"),
        Scenario.from_yaml(ROOT / "scenarios/baseline.yaml"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, indent=2, allow_nan=False) + "\n").encode())
    print(args.output)
