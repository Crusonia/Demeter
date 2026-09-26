from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from demeter.analysis.experiments import compare as compare_runs
from demeter.analysis.experiments import sensitivity as sensitivity_run
from demeter.analysis.experiments import uncertainty as uncertainty_run
from demeter.analysis.validation import mortality_backtest, validate as validation_report
from demeter.data.ingest import rebuild
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario

app = typer.Typer(no_args_is_help=True, help="Demeter evidence-aware health model.")
evidence_app = typer.Typer(help="Inspect parameter provenance and unresolved science.")
data_app = typer.Typer(help="Rebuild pinned government source inputs.")
app.add_typer(evidence_app, name="evidence")
app.add_typer(data_app, name="data")
DEFAULT_EVIDENCE = Path("evidence/parameters.yaml")


def emit(payload: dict, output: Path | None = None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n")
    typer.echo(text)


def registry(path: Path) -> EvidenceRegistry:
    return EvidenceRegistry.from_yaml(path)


@app.command()
def validate(evidence: Path = DEFAULT_EVIDENCE, scientific_required: bool = False) -> None:
    """Check arithmetic and data; report scientific readiness independently."""
    report = validation_report(registry(evidence))
    emit(report)
    if (
        not report["software_checks_passed"]
        or scientific_required
        and not report["scientific_release_ready"]
    ):
        raise typer.Exit(1)


@evidence_app.command("audit")
def evidence_audit(evidence: Path = DEFAULT_EVIDENCE) -> None:
    emit(registry(evidence).audit())


@data_app.command("rebuild")
def rebuild_data(raw: Path = Path("data/raw")) -> None:
    emit(rebuild(raw))


@app.command("simulate")
def simulate_scenario(
    scenario: Annotated[Path, typer.Argument(exists=True, readable=True)],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Emit trajectories, final cohorts, and complete provenance as JSON."""
    emit(simulate(registry(evidence), Scenario.from_yaml(scenario)).to_dict(), output)


@app.command()
def compare(
    baseline: Annotated[Path, typer.Argument(exists=True, readable=True)],
    intervention: Annotated[Path, typer.Argument(exists=True, readable=True)],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    emit(
        compare_runs(
            registry(evidence), Scenario.from_yaml(baseline), Scenario.from_yaml(intervention)
        ),
        output,
    )


@app.command()
def uncertainty(
    scenario: Annotated[Path, typer.Argument(exists=True, readable=True)],
    evidence: Path = DEFAULT_EVIDENCE,
    draws: int = 128,
    seed: int = 0,
    output: Path | None = None,
) -> None:
    """Propagate registered distributions with a paired baseline and fixed scenario."""
    emit(uncertainty_run(registry(evidence), Scenario.from_yaml(scenario), draws, seed), output)


@app.command()
def sensitivity(
    outcome: Annotated[str, typer.Argument()] = "life_expectancy",
    scenario: Path = Path("scenarios/reduce_upf_30.yaml"),
    evidence: Path = DEFAULT_EVIDENCE,
    samples: int = 64,
    seed: int = 0,
    output: Path | None = None,
) -> None:
    """Rank parameter contributions to variance using SALib Sobol analysis."""
    emit(
        sensitivity_run(registry(evidence), Scenario.from_yaml(scenario), outcome, samples, seed),
        output,
    )


@app.command()
def backtest(train_year: int = 2022, holdout_year: int = 2023, sex: str = "all") -> None:
    emit(mortality_backtest(train_year, holdout_year, sex))


if __name__ == "__main__":
    app()
