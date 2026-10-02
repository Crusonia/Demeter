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


@evidence_app.command("food-intake")
def food_intake_evidence(
    archive: Annotated[
        Path, typer.Option(help="Local pinned author ZIP; never downloaded implicitly")
    ],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Reproduce the paired menu/intake benchmark; no disease effect is activated."""
    from demeter.analysis.food_intake import reproduce_intake
    from demeter.data.nhanes import encoded

    try:
        report = reproduce_intake(registry(evidence), archive)
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)
    if not report["results"]["published_reproduction_passed"]:
        raise typer.Exit(1)


@evidence_app.command("public-cohort")
def public_cohort_evidence(
    workbook: Annotated[Path, typer.Option(help="Local pinned Chen workbook")],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Audit public longitudinal observations without activating transition rates."""
    from demeter.analysis.public_cohort import audit_public_cohort
    from demeter.data.nhanes import encoded

    try:
        report = audit_public_cohort(registry(evidence), workbook)
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)
    if not report["results"]["source_reproduction_passed"]:
        raise typer.Exit(1)


@evidence_app.command("public-cohort-timing")
def public_cohort_timing_evidence(
    workbook: Annotated[Path, typer.Option(help="Local pinned Chen workbook")],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Audit follow-up arithmetic and preserve unresolved observation semantics."""
    from demeter.analysis.public_cohort_timing import audit_timing
    from demeter.data.nhanes import encoded

    try:
        report = audit_timing(registry(evidence), workbook)
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)
    if not report["results"]["source_reproduction_passed"]:
        raise typer.Exit(1)


@evidence_app.command("reus-diabetes")
def reus_diabetes_evidence(
    correction: Annotated[Path, typer.Option(help="Local pinned Reus correction XML")],
    original: Annotated[Path, typer.Option(help="Local pinned original Reus XML")],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Reproduce corrected trial benchmarks and check synthetic model compatibility."""
    from demeter.analysis.reus_diabetes import audit_reus
    from demeter.data.nhanes import encoded

    try:
        report = audit_reus(registry(evidence), correction, original)
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)
    if (
        not report["results"]["source_reproduction_passed"]
        or not report["compatibility_diagnostic"]["results"]["software_witnesses_passed"]
    ):
        raise typer.Exit(1)


@evidence_app.command("preview-endpoints")
def preview_endpoint_evidence(
    raw: Annotated[
        Path, typer.Option(help="Directory containing all four pinned PREVIEW publications")
    ],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Reproduce source normal-glucose endpoints and missing-label envelopes offline."""
    from demeter.analysis.preview_endpoints import audit_preview
    from demeter.data.nhanes import encoded

    try:
        report = audit_preview(registry(evidence), raw)
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)
    if not report["results"]["source_reproduction_passed"]:
        raise typer.Exit(1)


@evidence_app.command("totum-source-rows")
def totum_source_row_evidence(
    raw: Annotated[Path, typer.Option(help="Directory containing all five pinned TOTUM63 sources")],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Audit public glucose source-row coverage offline; no clinical fit or effect."""
    from demeter.analysis.totum_source_rows import DATASET, audit_totum_source_rows
    from demeter.data.nhanes import encoded

    try:
        selected = registry(evidence)
        report = audit_totum_source_rows(selected, raw)
        spec = selected.datasets[DATASET]
        protected = {
            evidence.resolve(),
            Path(spec["protocol_path"]).resolve(),
            Path(spec["receipts_path"]).resolve(),
            *(raw / selected.sources[key].raw_filename for key in spec["source_ids"].values()),
        }
        if output and (
            output.resolve() in {path.resolve() for path in protected}
            or output.exists()
            and any(output.samefile(path) for path in protected if path.exists())
        ):
            raise ValueError("Output must not overwrite a source, registry or frozen record")
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)
    if not report["source_audit_passed"]:
        raise typer.Exit(1)


@evidence_app.command("whitehall-endpoint")
def whitehall_endpoint_evidence(
    raw: Annotated[Path, typer.Option(help="Directory containing both pinned Whitehall II PDFs")],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
    descriptive_only: bool = False,
) -> None:
    """Reproduce FPG labels; optionally evaluate a conditional binomial working model."""
    from demeter.analysis.whitehall_endpoints import DATASET, audit_whitehall_endpoint
    from demeter.data.nhanes import encoded

    exclusive_output = False
    try:
        selected = registry(evidence)
        spec = selected.datasets[DATASET]
        protected = {
            evidence,
            Path(spec["protocol_path"]),
            Path(spec["receipts_path"]),
            Path("docs/validation/whitehall-fpg-endpoint-protocol-v1.json"),
            Path("docs/validation/whitehall-fpg-source-receipts-v1.json"),
            *(raw / selected.sources[key].raw_filename for key in spec["source_ids"].values()),
        }
        if output:
            destination = output.resolve()
            unsafe = destination in {path.absolute() for path in protected}
            unsafe = unsafe or destination.is_relative_to(raw.absolute())
            for path in protected:
                try:
                    unsafe = unsafe or destination == path.resolve()
                    unsafe = unsafe or (output.exists() and path.exists() and output.samefile(path))
                except OSError:
                    exclusive_output = True
            try:
                unsafe = unsafe or destination.is_relative_to(raw.resolve())
            except OSError:
                # An unreadable source must still yield a failure receipt. Exclusive
                # creation prevents overwriting an input whose alias is unresolved.
                exclusive_output = True
            if unsafe or exclusive_output and output.exists():
                typer.echo(
                    "Output must not overwrite a source, registry or frozen record", err=True
                )
                raise typer.Exit(1)
        report = audit_whitehall_endpoint(selected, raw, working_likelihood=not descriptive_only)
    except (ValueError, OSError, KeyError) as exc:
        typer.echo("Whitehall evidence metadata or output path is invalid", err=True)
        raise typer.Exit(1) from exc
    if output:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb" if exclusive_output else "wb") as target:
                target.write(encoded(report))
        except OSError as exc:
            typer.echo("Unable to save the Whitehall aggregate report", err=True)
            raise typer.Exit(1) from exc
    emit(report)
    if not report["source_audit_passed"]:
        raise typer.Exit(1)


@evidence_app.command("malawi-cohort")
def malawi_cohort_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    project: Path = Path("."),
    output: Path | None = None,
    raw: Path | None = None,
) -> None:
    """Audit public follow-up counts and bounds; optionally replay pinned article XML."""
    from demeter.analysis.malawi_cohort_audit import audit_malawi_cohort
    from demeter.data.nhanes import encoded

    try:
        root = project.resolve()
        if output is not None:
            destination = output.resolve()
            protected = [evidence.resolve()]
            if raw is not None:
                protected.append(raw.resolve())
            if (
                output.exists()
                or destination in protected
                or any(
                    destination.is_relative_to((root / folder).resolve())
                    for folder in (
                        "data",
                        "src",
                        "docs",
                        "evidence",
                    )
                )
            ):
                typer.echo("Output must be new and outside sources and frozen records", err=True)
                raise typer.Exit(1)
        report = audit_malawi_cohort(registry(evidence), root, raw=raw)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as target:
                target.write(encoded(report))
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        typer.echo("Malawi aggregate evidence or output is invalid", err=True)
        raise typer.Exit(1) from exc
    emit(report)


@evidence_app.command("aric-outcomes")
def aric_outcomes_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    project: Path = Path("."),
    output: Path | None = None,
    source_cache: Path | None = None,
) -> None:
    """Audit overlapping publication panels; optionally replay both public sources."""
    from demeter.analysis.aric_outcomes_audit import audit_aric_outcomes
    from demeter.data.nhanes import encoded

    try:
        root = project.resolve()
        if output is not None:
            destination = output.resolve()
            if (
                output.exists()
                or destination == evidence.resolve()
                or (source_cache is not None and destination.is_relative_to(source_cache.resolve()))
                or any(
                    destination.is_relative_to((root / folder).resolve())
                    for folder in ("data", "src", "docs", "evidence", ".git")
                )
            ):
                typer.echo("Output must be new and outside sources and frozen records", err=True)
                raise typer.Exit(1)
        report = audit_aric_outcomes(registry(evidence), root, source_cache=source_cache)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as target:
                target.write(encoded(report))
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        typer.echo("ARIC source evidence or output is invalid", err=True)
        raise typer.Exit(1) from exc
    emit(report)


@evidence_app.command("kerala-observations")
def kerala_observation_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    project: Path = Path("."),
    output: Path | None = None,
    source_cache: Path | None = None,
) -> None:
    """Verify source-native nominal observations; optionally replay pinned private cells."""
    from demeter.analysis.kerala_observation_audit import audit_kerala_observations
    from demeter.data.nhanes import encoded

    try:
        root = project.resolve()
        if output is not None:
            destination = output.resolve()
            protected_folders = [root / folder for folder in ("data", "src", "docs", "evidence")]
            if source_cache is not None:
                protected_folders.append(source_cache.resolve())
            if (
                output.exists()
                or destination == evidence.resolve()
                or any(destination.is_relative_to(folder.resolve()) for folder in protected_folders)
            ):
                typer.echo("Output must be new and outside sources and frozen records", err=True)
                raise typer.Exit(1)
        report = audit_kerala_observations(registry(evidence), root, source_cache=source_cache)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as target:
                target.write(encoded(report))
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        typer.echo("Kerala observation evidence or output is invalid", err=True)
        raise typer.Exit(1) from exc
    emit(report)


@evidence_app.command("kerala-endpoints")
def kerala_endpoint_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    project: Path = Path("."),
    output: Path | None = None,
    source_cache: Path | None = None,
    publication: Path | None = None,
    assume_complete_deaths: bool = False,
) -> None:
    """Bound source-native recorded endpoints; missing outcomes are never assumed negative."""
    from demeter.analysis.kerala_endpoints import audit_kerala_endpoints
    from demeter.data.nhanes import encoded

    try:
        root = project.resolve()
        if output is not None:
            destination = output.resolve()
            protected = [evidence.resolve()]
            if publication is not None:
                protected.append(publication.resolve())
            protected_folders = [root / folder for folder in ("data", "src", "docs", "evidence")]
            if source_cache is not None:
                protected_folders.append(source_cache.resolve())
            if (
                output.exists()
                or destination in protected
                or any(destination.is_relative_to(folder.resolve()) for folder in protected_folders)
            ):
                typer.echo("Output must be new and outside sources and frozen records", err=True)
                raise typer.Exit(1)
        report = audit_kerala_endpoints(
            registry(evidence),
            root,
            source_cache=source_cache,
            publication=publication,
            assume_complete_deaths=assume_complete_deaths,
        )
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as target:
                target.write(encoded(report))
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        typer.echo("Kerala endpoint evidence or output is invalid", err=True)
        raise typer.Exit(1) from exc
    emit(report)


@evidence_app.command("geelong-labels")
def geelong_label_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
    source: Path | None = None,
    descriptive_only: bool = False,
) -> None:
    """Reproduce paired glycemic labels and their conditional multinomial working model."""
    from demeter.analysis.geelong_labels import DATASET, audit_geelong_labels
    from demeter.data.nhanes import encoded

    exclusive_output = False
    try:
        selected = registry(evidence)
        spec = selected.datasets[DATASET]
        source_path = source if source is not None else Path(spec["source_path"])
        protected = {
            DEFAULT_EVIDENCE,
            evidence,
            source_path,
            Path(spec["source_path"]),
            Path(spec["protocol_path"]),
            Path(spec["bundle_path"]),
            Path("docs/validation/geelong-label-protocol-v1.json"),
        }
        protected_folders = {
            Path("data"),
            Path("src/demeter/data/bundled"),
            Path("docs/validation"),
        }
        if output:
            destination = output.resolve()
            unsafe = destination in {path.absolute() for path in protected}
            for folder in protected_folders:
                unsafe = unsafe or destination.is_relative_to(folder.absolute())
                try:
                    unsafe = unsafe or destination.is_relative_to(folder.resolve())
                except OSError:
                    exclusive_output = True
            for path in protected:
                try:
                    unsafe = unsafe or destination == path.resolve()
                    unsafe = unsafe or (output.exists() and path.exists() and output.samefile(path))
                except OSError:
                    exclusive_output = True
            if unsafe or exclusive_output and output.exists():
                typer.echo(
                    "Output must not overwrite a source, registry or frozen record", err=True
                )
                raise typer.Exit(1)
        report = audit_geelong_labels(
            selected, source_path, working_likelihood=not descriptive_only
        )
    except (ValueError, OSError, KeyError) as exc:
        typer.echo("Geelong evidence metadata or output path is invalid", err=True)
        raise typer.Exit(1) from exc
    if output:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb" if exclusive_output else "wb") as target:
                target.write(encoded(report))
        except OSError as exc:
            typer.echo("Unable to save the Geelong aggregate report", err=True)
            raise typer.Exit(1) from exc
    emit(report)
    if not report["source_audit_passed"]:
        raise typer.Exit(1)


@evidence_app.command("longitudinal-likelihood")
def longitudinal_likelihood_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Run the frozen synthetic linked-path exercise; no participant import or fit."""
    from yaml import YAMLError, safe_load

    from demeter.analysis.longitudinal_likelihood_validation import (
        DATASET,
        PROTOCOL_PATH,
        RFC_PATH,
        likelihood_failure_report,
        likelihood_software_report,
        load_likelihood_registry,
    )

    protected = [DEFAULT_EVIDENCE, evidence, Path(PROTOCOL_PATH), Path(RFC_PATH)]
    selected = None
    # Preserve explicitly declared input paths even when a malformed numeric
    # input prevents loading the registry. This inspection cannot authorize a fit.
    try:
        document = safe_load(evidence.read_text(encoding="utf-8"))
        datasets = document.get("datasets", {}) if type(document) is dict else {}
        spec = datasets.get(DATASET, {}) if type(datasets) is dict else {}
        if type(spec) is dict:
            protected.extend(
                Path(spec[field])
                for field in ("protocol_path", "rfc_path")
                if type(spec.get(field)) is str
            )
    except (OSError, ValueError, YAMLError):
        pass
    try:
        selected = load_likelihood_registry(evidence)
        spec = selected.datasets.get(DATASET, {})
        protected.extend(
            Path(spec[field])
            for field in ("protocol_path", "rfc_path")
            if type(spec.get(field)) is str
        )
    except (OSError, ValueError, YAMLError):
        pass
    if output:
        try:
            protected_output = any(output.resolve() == path.resolve() for path in protected)
            existing_output = output.exists() or output.is_symlink()
        except (OSError, RuntimeError, ValueError):
            typer.echo("Output path could not be verified; existing files are preserved.")
            raise typer.Exit(1) from None
        if protected_output:
            typer.echo("Output must not replace an evidence registry or frozen contract.")
            raise typer.Exit(1)
        if existing_output:
            typer.echo("Output must be a new file; existing evidence and reports are preserved.")
            raise typer.Exit(1)
    report = (
        likelihood_software_report(selected)
        if selected is not None
        else likelihood_failure_report("registered_registry")
    )
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if output:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write((text + "\n").encode("utf-8"))
        except OSError:
            typer.echo("Could not create a new output file; existing files are preserved.")
            raise typer.Exit(1) from None
    typer.echo(text)
    if not report["software_checks_passed"]:
        raise typer.Exit(1)


@evidence_app.command("paired-remission")
def paired_remission_evidence(
    raw: Annotated[
        Path, typer.Option(help="Directory containing the two pinned DiRECT PDFs and NLM XML")
    ],
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Bound paired source labels while retaining unassessed and death unknowns."""
    from demeter.analysis.paired_remission_sources import (
        DATASET,
        AMENDMENT_PATH,
        FAILURE_PATH,
        PROTOCOL_PATH,
        RECEIPTS_PATH,
        V2_PATH,
        V2_FAILURE_PATH,
        audit_paired_remission,
    )
    from demeter.data.nhanes import encoded

    exclusive_output = False
    try:
        selected = registry(evidence)
        spec = selected.datasets[DATASET]
        protected = {
            evidence,
            Path(PROTOCOL_PATH),
            Path(RECEIPTS_PATH),
            Path(AMENDMENT_PATH),
            Path(FAILURE_PATH),
            Path(V2_PATH),
            Path(V2_FAILURE_PATH),
            Path(spec["protocol_path"]),
            Path(spec["receipts_path"]),
            Path(spec["amendment_path"]),
            Path(spec["failed_intake_path"]),
            *(raw / selected.sources[key].raw_filename for key in spec["source_ids"].values()),
        }
        if output:
            destination = output.resolve()
            unsafe = destination in {path.absolute() for path in protected}
            unsafe = unsafe or destination.is_relative_to(raw.absolute())
            for path in protected:
                try:
                    unsafe = unsafe or destination == path.resolve()
                    unsafe = unsafe or (output.exists() and path.exists() and output.samefile(path))
                except OSError:
                    exclusive_output = True
            try:
                unsafe = unsafe or destination.is_relative_to(raw.resolve())
            except OSError:
                exclusive_output = True
            if unsafe or exclusive_output and output.exists():
                typer.echo(
                    "Output must not overwrite a source, registry or frozen record", err=True
                )
                raise typer.Exit(1)
        report = audit_paired_remission(selected, raw)
    except (ValueError, OSError, KeyError) as exc:
        typer.echo("Paired observation metadata or output path is invalid", err=True)
        raise typer.Exit(1) from exc
    if output:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb" if exclusive_output else "wb") as target:
                target.write(encoded(report))
        except OSError as exc:
            typer.echo("Unable to save the paired observation aggregate report", err=True)
            raise typer.Exit(1) from exc
    emit(report)
    if not report["source_audit_passed"]:
        raise typer.Exit(1)


@evidence_app.command("pathway-compatibility")
def pathway_compatibility_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
) -> None:
    """Run offline synthetic witnesses; no clinical effect is fitted or activated."""
    from demeter.analysis.pathway_compatibility import audit_compatibility
    from demeter.data.nhanes import encoded

    try:
        report = audit_compatibility(registry(evidence))
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)
    if not report["results"]["software_witnesses_passed"]:
        raise typer.Exit(1)


@evidence_app.command("dpp-observations")
def dpp_observation_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    raw: Annotated[
        Path | None,
        typer.Option(
            help="Optional directory of pinned public documentation; no participant records"
        ),
    ] = None,
    output: Path | None = None,
) -> None:
    """Audit DPP documentation and synthetic observation preservation offline."""
    from demeter.analysis.dpp_observations import audit_dpp_observations

    try:
        report = audit_dpp_observations(registry(evidence), raw)
    except (ValueError, OSError, KeyError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    emit(report, output)
    if (
        not report["results"]["software_witnesses_passed"]
        or report["results"]["documentation_bytes_passed"] is False
    ):
        raise typer.Exit(1)


@evidence_app.command("applicability")
def evidence_applicability(evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None) -> None:
    """Show candidate estimates and unresolved population/endpoint mappings."""
    emit(applicability_report(registry(evidence)), output)


@data_app.command("fetch-ipop")
def fetch_ipop_sources(
    destination: Annotated[Path, typer.Option(help="Fresh ignored source cache directory")],
) -> None:
    """Fetch only the two frozen public iPOP files into a fresh ignored cache."""
    from demeter.analysis.ipop_preflight import load_frozen_protocol
    from demeter.data.ipop import fetch_sources

    try:
        result = fetch_sources(load_frozen_protocol(), destination)
    except (ValueError, OSError):
        typer.echo(
            "iPOP acquisition failed before intake; no clinical analysis performed.", err=True
        )
        raise typer.Exit(1) from None
    # The in-memory wrapper may contain source bytes; never serialize its full return value.
    emit({key: result[key] for key in ("passed", "receipt_saved", "provenance")})
    if not result["passed"]:
        raise typer.Exit(1)


@evidence_app.command("ipop-preflight")
def ipop_preflight(
    raw: Annotated[Path, typer.Option(help="Existing cache with immutable acquisition receipts")],
    output: Annotated[Path, typer.Option(help="Fresh aggregate report path; never overwritten")],
) -> None:
    """Audit pinned linked laboratory coverage offline; no clinical fit or activation."""
    from demeter.analysis.ipop_preflight_io import audit_preflight, write_fresh_report

    try:
        report = audit_preflight(raw)
        write_fresh_report(report, output, raw)
    except (ValueError, OSError):
        typer.echo(
            "iPOP intake or fresh report publication failed; source evidence preserved.", err=True
        )
        raise typer.Exit(1) from None
    emit(report)
    if not report["source_audit"]["passed"]:
        raise typer.Exit(1)


@evidence_app.command("ipop-crosswalk-preflight")
def ipop_crosswalk_preflight(
    raw: Annotated[Path, typer.Option(help="Existing cache with immutable acquisition receipts")],
    output: Annotated[Path, typer.Option(help="Fresh aggregate report path; never overwritten")],
) -> None:
    """Audit conditional subject namespace consistency; no identity certification or fit."""
    from demeter.analysis.ipop_preflight_io import audit_crosswalk, write_fresh_report

    try:
        report = audit_crosswalk(raw)
        write_fresh_report(report, output, raw)
    except (ValueError, OSError, RuntimeError):
        typer.echo(
            "iPOP intake or fresh report publication failed; source evidence preserved.", err=True
        )
        raise typer.Exit(1) from None
    emit(report)
    if not report["source_audit"]["passed"]:
        raise typer.Exit(1)


@evidence_app.command("ipop-a1c-working-fit")
def ipop_a1c_working_fit(
    raw: Annotated[Path, typer.Option(help="Existing pinned iPOP cache with acquisition receipts")],
    output: Annotated[Path, typer.Option(help="Fresh aggregate report path; never overwritten")],
    numerical_method: Annotated[
        str, typer.Option(help="Frozen numerical version: v1 or exact_box_quadratic_v2")
    ] = "v1",
) -> None:
    """Frozen conditional A1C-band fit with internal prediction and joint uncertainty."""
    from demeter.analysis.ipop_a1c import analyze_cache
    from demeter.analysis.ipop_preflight_io import write_fresh_report

    try:
        report = analyze_cache(
            raw,
            progress=lambda message: typer.echo(message, err=True),
            numerical_method=numerical_method,
        )
        write_fresh_report(report, output, raw)
    except (ValueError, OSError, RuntimeError):
        typer.echo(
            "iPOP working analysis or fresh publication failed; source evidence preserved.",
            err=True,
        )
        raise typer.Exit(1) from None
    emit(report)
    if not report["analysis_completed"]:
        raise typer.Exit(1)


@evidence_app.command("verify-sources")
def evidence_sources(
    evidence: Path = DEFAULT_EVIDENCE,
    raw: Path = Path("data/raw/clinical"),
    download: bool = False,
    output: Path | None = None,
) -> None:
    """Verify pinned sources, clinical tables and dataset reproduction checks."""
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
    documentation_raw: Path | None = None,
    output: Path | None = None,
) -> None:
    """Audit rights, citations, source/package coverage and checksums without fetching."""
    from demeter.data.packages import verify_packages

    report = verify_packages(root, check_tracked=check_tracked, documentation_raw=documentation_raw)
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


@evidence_app.command("state-mapping")
def state_mapping_evidence(
    evidence: Path = DEFAULT_EVIDENCE,
    output: Path | None = None,
    partial: Annotated[
        bool, typer.Option(help="Preserve known categories and bound incomplete observations")
    ] = False,
) -> None:
    """Audit observed categories, unclassified coverage and unresolved engine mappings."""
    from demeter.data.state_mapping import mapping_report
    from demeter.data.nhanes import encoded
    from demeter.data.partial_observations import partial_report

    report = (partial_report if partial else mapping_report)(registry(evidence))
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded(report))
    emit(report)


@evidence_app.command("glycemic-uncertainty")
def glycemic_uncertainty_evidence(
    evidence: Path = DEFAULT_EVIDENCE, output: Path | None = None
) -> None:
    """Joint sampling covariance of observed categories; no engine initialization."""
    from demeter.data.glycemic_uncertainty import joint_report
    from demeter.data.nhanes import encoded

    report = joint_report(registry(evidence))
    if output is None:
        emit(report)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects existing source files through hard/symbolic aliases.
    with output.open("xb") as handle:
        handle.write(encoded(report))
    emit(
        {
            "output": str(output),
            "kind": report["kind"],
            "model_role": report["model_role"],
            "direct_initialization_allowed": report["direct_initialization_allowed"],
            "provenance": report["provenance"],
        }
    )


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
