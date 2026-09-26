from __future__ import annotations

import json
from pathlib import Path

import typer

from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario


app = typer.Typer(no_args_is_help=True, help="Demeter systems-modeling CLI.")
DEFAULT_EVIDENCE = Path("evidence/parameters.yaml")


def _load(evidence: Path, scenario: Path):
    return EvidenceRegistry.from_yaml(evidence), Scenario.from_yaml(scenario)


@app.command()
def validate(evidence: Path = DEFAULT_EVIDENCE) -> None:
    """Validate the evidence registry and report scientific status."""
    registry = EvidenceRegistry.from_yaml(evidence)
    counts: dict[str, int] = {}
    for parameter in registry.parameters.values():
        counts[parameter.status] = counts.get(parameter.status, 0) + 1

    typer.echo(f"Validated {len(registry.parameters)} parameters.")
    typer.echo("Status counts: " + json.dumps(counts, sort_keys=True))
    if registry.contains_synthetic:
        typer.echo("VALIDATION ONLY: synthetic parameters are present.")


@app.command()
def simulate_scenario(
    scenario: Path = typer.Argument(..., exists=True, readable=True),
    evidence: Path = DEFAULT_EVIDENCE,
) -> None:
    """Run one scenario and emit machine-readable JSON."""
    registry, spec = _load(evidence, scenario)
    result = simulate(registry, spec)
    typer.echo(
        json.dumps(
            {
                "scenario": result.scenario,
                "years": result.years,
                "validation_only": result.validation_only,
                "starting_population": result.starting_population,
                "ending_population": result.ending_population,
                "cumulative_deaths": result.cumulative_deaths,
                "ending_state_shares": result.ending_state_shares,
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command()
def compare(
    baseline: Path = typer.Argument(..., exists=True, readable=True),
    intervention: Path = typer.Argument(..., exists=True, readable=True),
    evidence: Path = DEFAULT_EVIDENCE,
) -> None:
    """Compare two scenarios using the same evidence registry."""
    registry = EvidenceRegistry.from_yaml(evidence)
    left = simulate(registry, Scenario.from_yaml(baseline))
    right = simulate(registry, Scenario.from_yaml(intervention))

    payload = {
        "validation_only": left.validation_only or right.validation_only,
        "baseline": left.scenario,
        "intervention": right.scenario,
        "delta_cumulative_deaths": right.cumulative_deaths - left.cumulative_deaths,
        "delta_t2d_share": (
            right.ending_state_shares["t2d"] - left.ending_state_shares["t2d"]
        ),
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
