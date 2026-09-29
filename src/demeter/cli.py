from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from demeter.analysis.experiments import compare as compare_runs
from demeter.analysis.experiments import sensitivity as sensitivity_run
from demeter.analysis.experiments import uncertainty as uncertainty_run
from demeter.analysis.historical import historical_backtest
from demeter.analysis.diet_response import historical_lag_challenge, timing_sensitivity
from demeter.analysis.observability import observe
from demeter.analysis.validation import mortality_backtest, validate as validation_report
from demeter.data.ingest import rebuild
from demeter.data.historical import rebuild_history
from demeter.data.nhanes import STORE as NHANES_STORE, load_nhanes, rebuild_nhanes
from demeter.data.store import verify_store
from demeter.data.healthspan import crosscheck, load_healthspan, rebuild_healthspan
from demeter.data.prechronic import load_prechronic, rebuild_prechronic
from demeter.data.dietary import load_dietary, rebuild_dietary
from demeter.data.diet_response import rebuild_challenge
from demeter.evidence.appraisal import applicability_report, verify_sources
from demeter.model import simulate
from demeter.nutrition.exposures import catalog
from demeter.schema import EvidenceRegistry, Scenario

app = typer.Typer(no_args_is_help=True, help="Demeter evidence-aware health model.")
evidence_app = typer.Typer(help="Inspect parameter provenance and unresolved science.")
data_app = typer.Typer(help="Rebuild pinned government source inputs.")
release_app = typer.Typer(help="Build, verify and replay inspectable engineering release bundles.")
extension_app = typer.Typer(
    help="Inspect, register and explicitly execute versioned local packages."
)
app.add_typer(evidence_app, name="evidence")
app.add_typer(data_app, name="data")
app.add_typer(release_app, name="release")
app.add_typer(extension_app, name="extensions")
DEFAULT_EVIDENCE = Path("evidence/parameters.yaml")
DEFAULT_EXTENSIONS = Path("outputs/extension-registry.yaml")


@app.command("explore")
def explore(
    project: Path = Path("."),
    destination: Path = Path("outputs/explorer"),
    port: Annotated[int, typer.Option(min=0, max=65535)] = 0,
    browser: bool = True,
) -> None:
    """Open the local educational interface with working model reruns (studio extra)."""
    from demeter.explorer.launcher import launch
    try:
        launch(project, destination, port, browser)
    except (ValueError, RuntimeError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@extension_app.command("list")
def extensions_list(local_registry: Path = DEFAULT_EXTENSIONS) -> None:
    from demeter.extensions import list_packages

    emit(list_packages(local_registry))


@extension_app.command("inspect")
def extensions_inspect(manifest: Path) -> None:
    from demeter.extensions import inspect_package

    emit(inspect_package(manifest))


@extension_app.command("register")
def extensions_register(manifest: Path, local_registry: Path = DEFAULT_EXTENSIONS) -> None:
    from demeter.extensions import register

    emit(register(manifest, local_registry))


@extension_app.command("run")
def extensions_run(
    package: str,
    scenario: str,
    module: str | None = None,
    local_registry: Path = DEFAULT_EXTENSIONS,
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    from demeter.extensions import protect_output, resolve, run

    selected = resolve(package, local_registry)
    protect_output(output, (selected,), local_registry, evidence)
    emit(
        run(registry(evidence), selected, scenario, module).to_dict(),
        output,
    )


@extension_app.command("compare")
def extensions_compare(
    left: str,
    left_scenario: str,
    right: str,
    right_scenario: str,
    left_module: str | None = None,
    right_module: str | None = None,
    local_registry: Path = DEFAULT_EXTENSIONS,
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    from demeter.extensions import compare, protect_output, resolve

    selected_left, selected_right = resolve(left, local_registry), resolve(right, local_registry)
    protect_output(output, (selected_left, selected_right), local_registry, evidence)
    emit(
        compare(
            registry(evidence),
            selected_left,
            left_scenario,
            selected_right,
            right_scenario,
            left_module=left_module,
            right_module=right_module,
        ),
        output,
    )


@release_app.command("build")
def release_build(
    destination: Path,
    draws: int = 128,
    samples: int = 64,
    seed: int = 42,
    allow_dirty: bool = False,
) -> None:
    from demeter.releases import RunSettings, build

    emit(
        build(
            destination,
            RunSettings(draws=draws, samples=samples, seed=seed),
            allow_dirty=allow_dirty,
        )
    )


@release_app.command("verify")
def release_verify(bundle: Path) -> None:
    from demeter.releases import verify

    emit(verify(bundle))


@release_app.command("extract")
def release_extract(bundle: Path, destination: Annotated[Path, typer.Option()]) -> None:
    from demeter.releases import extract

    emit(extract(bundle, destination))


@release_app.command("replay")
def release_replay(bundle: Path, output: Path | None = None) -> None:
    from demeter.releases import replay

    if output and output.resolve().is_relative_to(bundle.resolve()):
        raise typer.BadParameter("Write replay reports outside the immutable bundle")
    result = replay(bundle)
    emit(result, output)
    if not result["passed"]:
        raise typer.Exit(1)


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


@data_app.command("rebuild-linked-mortality")
def rebuild_linked_mortality_data(
    evidence: Path = DEFAULT_EVIDENCE,
    source: Path = Path("data/sources/nhanes-mortality/2011-2012"),
    destination: Path = Path("outputs/linked-mortality-rebuilt"),
) -> None:
    """Rebuild the public-use linkage feasibility audit offline."""
    from demeter.data.linked_mortality import rebuild_linked_mortality

    emit(rebuild_linked_mortality(registry(evidence), source, destination))


@evidence_app.command("linked-mortality")
def linked_mortality_evidence(
    evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None
) -> None:
    """Inspect mortality-linkage coverage; this does not fit clinical parameters."""
    from demeter.data.linked_mortality import load_linked_mortality

    emit(load_linked_mortality(registry(evidence)), output)


@evidence_app.command("audit")
def evidence_audit(evidence: Path = DEFAULT_EVIDENCE) -> None:
    emit(registry(evidence).audit())


@evidence_app.command("applicability")
def evidence_applicability(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Show candidate estimates and unresolved population/endpoint mappings."""
    emit(applicability_report(registry(evidence)), output)


@evidence_app.command("verify-sources")
def evidence_sources(
    evidence: Path = DEFAULT_EVIDENCE,
    raw: Path = Path("data/raw/clinical"),
    download: bool = False,
    output: Path | None = None,
) -> None:
    """Re-extract pinned clinical tables; fail on drift without altering parameters."""
    report = verify_sources(registry(evidence), raw, download)
    emit(report, output)
    if not report["passed"]:
        raise typer.Exit(1)


@data_app.command("rebuild")
def rebuild_data(raw: Path = Path("data/raw")) -> None:
    emit(rebuild(raw))


@data_app.command("verify-store")
def verify_source_store(catalog: Path = Path("data/catalog.json")) -> None:
    """Verify every source file in the versioned repository catalog, offline."""
    report = verify_store(catalog)
    emit(report)
    if not report["passed"]:
        raise typer.Exit(1)


@data_app.command("rebuild-history")
def rebuild_historical_data(
    raw: Path = Path("data/raw/historical"),
    download: bool = False,
) -> None:
    """Rebuild historical observations; reject changed source bytes."""
    emit(rebuild_history(raw, download=download))


@data_app.command("verify-packages")
def verify_evidence_packages(
    root: Path = Path("."),
    check_tracked: bool = False,
    output: Path | None = None,
) -> None:
    """Audit rights, citations, source/package coverage and checksums without fetching."""
    from demeter.data.packages import verify_packages

    report = verify_packages(root, check_tracked=check_tracked)
    emit(report, output)
    if not report["passed"]:
        raise typer.Exit(1)


@data_app.command("rebuild-nhanes")
def rebuild_glycemic_data(
    evidence: Path = DEFAULT_EVIDENCE,
    source: Path = NHANES_STORE,
    destination: Path = Path("outputs/nhanes-rebuilt"),
) -> None:
    """Verify the repository source store and reconstruct survey benchmarks offline."""
    emit(rebuild_nhanes(registry(evidence), source, destination))


@data_app.command("rebuild-healthspan")
def rebuild_healthspan_data(
    evidence: Path = DEFAULT_EVIDENCE,
    source: Path = Path("data/sources/healthspan/nchs-2001"),
    destination: Path = Path("outputs/healthspan-rebuilt"),
) -> None:
    """Re-extract and verify the NCHS method example from the archived PDF, offline."""
    emit(rebuild_healthspan(registry(evidence), source, destination))


@evidence_app.command("healthspan")
def healthspan_benchmark(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Cross-check the healthspan estimator against the published NCHS example."""
    report = crosscheck(load_healthspan(registry(evidence)))
    emit(report, output)
    if not report["passed"]:
        raise typer.Exit(1)


@evidence_app.command("population")
def population_evidence(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Read pinned age/sex glycemic prevalence; never substitute it for T2D states."""
    emit(load_nhanes(registry(evidence)), output)


@data_app.command("rebuild-prechronic")
def rebuild_risk_data(
    evidence: Path = DEFAULT_EVIDENCE,
    source: Path = Path("data/sources/nhanes-risk/2017-2020"),
    destination: Path = Path("outputs/prechronic-rebuilt"),
) -> None:
    """Reconstruct candidate earlier-risk definitions from archived NHANES files."""
    emit(rebuild_prechronic(registry(evidence), source, destination))


@evidence_app.command("prechronic")
def prechronic_evidence(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Report candidate sizes and age/sex distributions without fitting model parameters."""
    emit(load_prechronic(registry(evidence)), output)


@data_app.command("rebuild-dietary")
def rebuild_dietary_data(
    evidence: Path = DEFAULT_EVIDENCE,
    source: Path = Path("data/sources/dietary/2026-09-27"),
    destination: Path = Path("outputs/dietary-rebuilt"),
) -> None:
    """Reconstruct dietary means, sampling uncertainty and reported-day distributions offline."""
    emit(rebuild_dietary(registry(evidence), source, destination))


@evidence_app.command("dietary")
def dietary_evidence(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Read source-linked dietary baselines without fitting causal response parameters."""
    emit(load_dietary(registry(evidence)), output)


@data_app.command("rebuild-glp1")
def rebuild_glp1_data(
    evidence: Path = DEFAULT_EVIDENCE,
    source: Path = Path("data/sources/glp1/2026-09-28"),
    destination: Path = Path("outputs/glp1-rebuilt"),
) -> None:
    """Rebuild clinical benchmarks from archived official JSON and labeled extraction."""
    from demeter.data.glp1 import rebuild_glp1

    emit(rebuild_glp1(registry(evidence), source, destination))


@evidence_app.command("glp1")
def glp1_evidence(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Inspect trial and persistence benchmarks without calibrating model effects."""
    from demeter.data.glp1 import load_glp1

    emit(load_glp1(registry(evidence)), output)


@app.command("food-exposures")
def food_exposures(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """List canonical food/nutrient definitions, units, overlap and activation boundaries."""
    emit(catalog(registry(evidence)), output)


@data_app.command("rebuild-diet-response")
def rebuild_diet_response_data(
    evidence: Path = DEFAULT_EVIDENCE,
    source: Path = Path("data/sources/diet-dynamics/2026-09-27"),
    destination: Path = Path("outputs/diet-response-rebuilt"),
) -> None:
    """Verify factual trial extraction and official NIH corroboration offline."""
    emit(rebuild_challenge(registry(evidence), source, destination))


@app.command("diet-lag-challenge")
def diet_lag_challenge(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Challenge a lag-to-remission shortcut; expose missing structure without fitting."""
    emit(historical_lag_challenge(registry(evidence)), output)


@app.command("timing-sensitivity")
def diet_timing_sensitivity(
    scenario: Path = Path("scenarios/diet_dynamics.yaml"),
    evidence: Path = DEFAULT_EVIDENCE,
    samples: int = 64,
    seed: int = 0,
    output: Path | None = None,
) -> None:
    """Rank timing contributions to healthspan with other parameters held fixed."""
    emit(
        timing_sensitivity(registry(evidence), Scenario.from_yaml(scenario), samples, seed), output
    )


@app.command("leverage")
def food_leverage(
    scenario: Path = Path("scenarios/diet_dynamics.yaml"),
    baseline: Path | None = None,
    evidence: Path = DEFAULT_EVIDENCE,
    draws: int = 32,
    samples: int = 64,
    seed: int = 0,
    destination: Path = Path("outputs/leverage"),
) -> None:
    """Explain food contrasts with exact pathway allocation, sensitivity and evidence context."""
    from demeter.analysis.leverage import leverage
    from demeter.analysis.leverage_visualization import render_leverage

    payload = leverage(
        registry(evidence),
        Scenario.from_yaml(scenario),
        baseline=Scenario.from_yaml(baseline) if baseline else None,
        draws=draws,
        samples=samples,
        seed=seed,
    )
    emit(render_leverage(payload, destination))


@app.command("historical-backtest")
def historical_benchmarks(
    evidence: Path = DEFAULT_EVIDENCE,
    window: int = 10,
    origin: int | None = None,
    coverage: float = 0.9,
    output: Path | None = None,
) -> None:
    """Run rolling 5/10-year benchmarks, or freeze a single calendar origin."""
    emit(
        historical_backtest(
            registry(evidence),
            window=window,
            origins=(origin,) if origin is not None else None,
            coverage=coverage,
        ),
        output,
    )


@app.command("observe")
def observe_scenario(
    scenario: Annotated[Path, typer.Argument(exists=True, readable=True)],
    evidence: Path = DEFAULT_EVIDENCE,
    destination: Path = Path("outputs/observability"),
    draws: int = 64,
    samples: int = 32,
    seed: int = 0,
) -> None:
    """Generate canonical diagnostics and a self-contained scientific HTML report."""
    from demeter.analysis.visualization import render_report

    payload = observe(
        registry(evidence), Scenario.from_yaml(scenario), draws=draws, samples=samples, seed=seed
    )
    emit(render_report(payload, destination))


@app.command("visualize")
def visualize_outputs(
    diagnostics: Annotated[Path, typer.Argument(exists=True, readable=True)],
    destination: Path = Path("outputs/observability-rendered"),
) -> None:
    """Re-render an existing canonical diagnostics file without running the model."""
    from demeter.analysis.visualization import render_report

    emit(render_report(json.loads(diagnostics.read_text()), destination))


@app.command("simulate")
def simulate_scenario(
    scenario: Annotated[Path, typer.Argument(exists=True, readable=True)],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
    transition_module: str | None = None,
) -> None:
    """Emit trajectories, final cohorts, and complete provenance as JSON."""
    from demeter.health.module import load_transition_module

    module = load_transition_module(transition_module) if transition_module else None
    result = simulate(registry(evidence), Scenario.from_yaml(scenario), transition_module=module)
    if transition_module:
        result.metadata["transition_module"]["factory_reference"] = transition_module
    emit(result.to_dict(), output)


@app.command("healthspan")
def healthspan_outcomes(
    scenario: Annotated[Path, typer.Argument(exists=True, readable=True)],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Report period healthspan by age and restricted state time by original cohort."""
    result = simulate(registry(evidence), Scenario.from_yaml(scenario))
    emit({"metadata": result.metadata, **result.healthspan}, output)


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
