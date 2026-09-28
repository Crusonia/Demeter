"""Offline, inspectable engineering release snapshots and explicit numerical replay."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import distributions
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import tempfile
import tomllib
import zipfile
from typing import Literal

from pydantic import Field, model_validator
import yaml

from demeter import __version__
from demeter.analysis.experiments import compare, sensitivity, uncertainty
from demeter.analysis.historical import historical_backtest
from demeter.analysis.validation import validate
from demeter.contracts import API_VERSION
from demeter.data.ingest import digest
from demeter.data.packages import verify_packages
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario, StrictModel

# Numerical comparison tolerances, not model/evidence parameters.
RTOL, ATOL = 1e-10, 1e-8
RESULT_NAMES = (
    "baseline",
    "intervention",
    "comparison",
    "uncertainty",
    "sensitivity",
    "validation",
    "historical",
)


class RunSettings(StrictModel):
    draws: int = Field(default=128, ge=2, le=10000, strict=True)
    samples: int = Field(default=64, ge=8, le=1024, strict=True)
    seed: int = Field(default=42, ge=0, strict=True)

    @model_validator(mode="after")
    def power_of_two(self):
        if self.samples & (self.samples - 1):
            raise ValueError("samples must be a power of two")
        return self


class FileReceipt(StrictModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)


class ClinicalCalibration(StrictModel):
    status: Literal["deferred"]
    fitted_parameters: list[str] = Field(max_length=0)
    windows: list = Field(max_length=0)
    reason: str = Field(min_length=1)


class ReleaseProfile(StrictModel):
    schema_version: Literal[1]
    model_structure_version: str = Field(min_length=1)
    scenario_schema_version: str = Field(min_length=1)
    baseline: str
    intervention: str
    supported_health_structures: list[Literal["legacy", "risk_1", "risk_2"]]
    breaking_changes: list[str]
    changes: list[str] = Field(min_length=1)
    clinical_calibration: ClinicalCalibration

    @model_validator(mode="after")
    def scenario_paths(self):
        for name in (self.baseline, self.intervention):
            safe_name(name)
            if not name.startswith("scenarios/") or not name.endswith(".yaml"):
                raise ValueError("Release profiles require repository scenario YAML paths")
        return self


class ReleaseManifest(StrictModel):
    schema_version: Literal[1] = 1
    kind: Literal["demeter_engineering_release"] = "demeter_engineering_release"
    created_at: str
    software_version: str
    profile: dict
    module_api_version: str
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    working_tree_dirty: bool
    classification: Literal["engineering_checkpoint", "development_snapshot"]
    scientific_release_ready: Literal[False] = False
    settings: RunSettings
    runtime: dict
    evidence: dict
    data: dict
    calibration: dict
    validation: dict
    scenario_compatibility: dict
    source_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_files: dict[str, FileReceipt]
    artifacts: dict[str, FileReceipt]

    @model_validator(mode="after")
    def coherent(self):
        ReleaseProfile.model_validate(self.profile)
        if self.working_tree_dirty != (self.classification == "development_snapshot"):
            raise ValueError("Dirty source must be classified as a development snapshot")
        for path in (*self.source_files, *self.artifacts):
            safe_name(path)
        required = {"source.zip", "MODEL_CARD.md", "REPRODUCE.md", "data-audit.json"}
        required.update(f"results/{name}.json" for name in RESULT_NAMES)
        if set(self.artifacts) != required:
            raise ValueError("Incomplete or unexpected release artifact inventory")
        if (
            not {"uv.lock", "pyproject.toml", "evidence/parameters.yaml", "releases/profile.yaml"}
            <= self.source_files.keys()
        ):
            raise ValueError("Source snapshot lacks reproducibility inputs")
        return self


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or "\\" in name
        or ":" in name
        or any(part in ("", ".", "..") for part in name.split("/"))
        or any(part.endswith((".", " ")) for part in path.parts)
        or any(c in name for c in '<>"|?*')
        or any(ord(c) < 32 for c in name)
        or any(
            part.split(".")[0].upper()
            in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *[f"COM{i}" for i in range(10)],
                *[f"LPT{i}" for i in range(10)],
            }
            for part in path.parts
        )
    ):
        raise ValueError(f"Unsafe archive path: {name!r}")
    return name


def inside(root: Path, name: str) -> Path:
    safe_name(name)
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes bundle: {name}")
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise ValueError(f"Symlink not permitted: {name}")
    return path


def canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def receipt(content: bytes) -> FileReceipt:
    return FileReceipt(sha256=digest(content), bytes=len(content))


def source_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    if not (root / "releases/profile.yaml").is_file():
        raise ValueError("Release commands require the source checkout, not an installed wheel")
    return root


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    ).strip()


def runtime() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": dict(
            sorted((d.metadata["Name"], d.version) for d in distributions() if d.metadata["Name"])
        ),
        "dependency_policy": "uv.lock pins installation; package binaries/environment are not bundled",
    }


def profile_at(root: Path) -> dict:
    profile = ReleaseProfile.model_validate(
        yaml.safe_load((root / "releases/profile.yaml").read_text(encoding="utf-8"))
    ).model_dump()
    for name in ("baseline", "intervention"):
        inside(root, profile[name])
    return profile


def calculate(root: Path, settings: RunSettings) -> dict:
    profile = profile_at(root)
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    baseline, intervention = (
        Scenario.from_yaml(root / profile[k]) for k in ("baseline", "intervention")
    )
    if baseline.mode != "validation" or intervention.mode != "validation":
        raise ValueError("Engineering bundles cannot claim scientific scenario mode")
    return {
        "baseline": simulate(registry, baseline).to_dict(),
        "intervention": simulate(registry, intervention).to_dict(),
        "comparison": compare(registry, baseline, intervention),
        "uncertainty": uncertainty(registry, intervention, settings.draws, settings.seed),
        "sensitivity": sensitivity(
            registry, intervention, samples=settings.samples, seed=settings.seed
        ),
        "validation": validate(registry),
        "historical": historical_backtest(registry),
    }


def source_inventory(root: Path) -> dict[str, FileReceipt]:
    names = sorted(filter(None, git(root, "ls-files", "-z").split("\0")))
    if len({n.casefold() for n in names}) != len(names):
        raise ValueError("Source paths collide on a case-insensitive filesystem")
    result = {}
    for name in names:
        path = inside(root, name)
        if not path.is_file():
            raise ValueError(f"Tracked source missing or not a regular file: {name}")
        result[name] = receipt(path.read_bytes())
    return result


def tree_hash(files: dict[str, FileReceipt]) -> str:
    return digest(canonical({k: v.model_dump() for k, v in files.items()}))


def model_card(manifest: dict, results: dict) -> str:
    base = results["baseline"]
    checks = results["validation"]
    backtest = checks["historical_backtest"]
    audit = manifest["evidence"]["audit"]
    lines = [
        "# Demeter model card",
        "",
        "**VALIDATION ONLY — NOT SCIENTIFIC FINDINGS.**",
        "",
        f"- Software: `{manifest['software_version']}`; structure: `{manifest['profile']['model_structure_version']}`.",
        f"- Source commit: `{manifest['git_commit']}`; dirty: `{manifest['working_tree_dirty']}`.",
        f"- Source tree: `{manifest['source_tree_sha256']}`.",
        f"- Evidence content hash: `{manifest['evidence']['content_sha256']}`.",
        f"- Classification: `{manifest['classification']}`; clinical parameter fitting deferred.",
        "",
        "## Purpose and population",
        "",
        "An engineering health vertical: dietary exposure, metabolic transitions, mortality and period longevity. "
        "U.S. age cells 0–99 and 100+, with a closed population. Canonical snapshots use the scenarios in the profile; "
        "their full definitions and compatibility schema are in the manifest/source archive.",
        "",
        f"Baseline mortality year: {base['metadata']['mortality_vintage']}; population vintage: {base['metadata']['population_vintage']}.",
        "All data publishers, dates, URLs, checksums, rights and reload commands are in `data-audit.json` and the source manifests.",
        "",
        "## Calibration and validation",
        "",
        "Clinical calibration windows and fitted clinical parameters: none. Existing annual mortality mixture normalization "
        "matches a source schedule; that arithmetic is not independent health validation. Historical benchmark training "
        "windows, interval-validation roles and holdouts are recorded per fold in `results/historical.json`.",
        "",
        f"Software/data checks passed: `{checks['software_checks_passed']}`. Scientific release ready: `false`.",
        f"Maximum population accounting residual: {checks['max_population_accounting_error_people']:.8g} people.",
        f"The {backtest['train_year']}→{backtest['holdout_year']} mortality persistence error is {backtest['error_years']:.6g} years. "
        "This residual is retained, not tuned away; it does not validate dietary effects.",
        "",
        "## Uncertainty, sensitivity and evidence gaps",
        "",
        f"Settings: {manifest['settings']['draws']} paired draws, {manifest['settings']['samples']} Sobol base samples, "
        f"seed {manifest['settings']['seed']}. These counts are not a convergence certificate.",
        "Full distributions/assumptions, uncertainty summaries, Sobol indices and historical errors are archived. "
        "Synthetic parameter ranges are not empirical confidence intervals; structural/source uncertainty is incomplete.",
        "",
        "Active baseline synthetic parameters: "
        + ", ".join(base["metadata"]["synthetic_parameters"])
        + ".",
        "Registry unresolved records (including benchmarks): "
        + (", ".join(audit["unresolved"]) or "none explicitly marked")
        + ".",
        "Missing registry uncertainty: "
        + (", ".join(audit["missing_uncertainty"]) or "none")
        + ".",
        "",
        *[f"- {gap}" for gap in audit["scientific_blockers"]],
        "",
        "See `docs/EVIDENCE_GAPS.md`, `docs/V0_1_STATUS.md` and `docs/ISSUE_1_AUDIT.md` in the archived source for context.",
        "",
        "## Limitations and unsupported uses",
        "",
        *[f"- {item}" for item in base["metadata"]["limitations"]],
        "",
        "No clinical recommendation, diet-induced lifespan finding, healthcare-cost forecast, agricultural result or investment conclusion is supported.",
        "",
        "## Compatibility and changes",
        "",
        f"Scenario schema: `{manifest['profile']['scenario_schema_version']}`; module API: `{manifest['module_api_version']}`. "
        "Only canonical baseline/intervention calculations are replayed by this bundle; experimental scenarios remain archived inputs, not validated releases.",
        *[f"- {item}" for item in manifest["profile"]["changes"]],
        "Declared breaking changes: "
        + ("; ".join(manifest["profile"]["breaking_changes"]) or "none")
        + ".",
        "",
        "## Reproduction and review",
        "",
        "Use `REPRODUCE.md`. Integrity verification checks bytes; numerical replay checks computations. Neither establishes "
        "authenticity, independent review or scientific acceptance. The generating command does not run or certify the full test suite; "
        "retain CI links and release-review decisions separately. No named scientific approval is asserted.",
        "",
    ]
    return "\n".join(lines)


REPRODUCE = """# Reproduce this engineering checkpoint

1. Retain the published manifest checksum separately. Use a trusted Demeter checkout:
   `uv run demeter release verify PATH_TO_BUNDLE` (read-only; does not execute archived code).
2. Review the model card and the source's rights/NOTICE files. No scientific acceptance is implied.
3. Extract source.zip to a NEW directory beside the bundle, never over an existing checkout:
   `uv run demeter release extract PATH_TO_BUNDLE --destination PATH_TO_NEW_SOURCE`.
4. Inspect/trust that source before executing it. In the extracted source directory, install
   its locked environment with `uv sync --locked`. Installation may need network access;
   Python/package binaries are not included. Run `uv run demeter release replay PATH_TO_BUNDLE
   --output PATH_TO_REPLAY_REPORT.json` using an absolute bundle path.
5. Replay checks the loaded source/input bytes, recomputes all seven results and reports
   exact or tolerance-based agreement (relative 1e-10, absolute 1e-8). Runtime differences
   are reported. Only historical Git-location fields may differ after extraction; no
   scientific value or input hash is excluded. Replay does not modify the original bundle.

Baseline/intervention YAML, complete parameter registry, all redistributable pinned source
data and notices, model-ready bundles, transformation code and uv.lock are in source.zip.
Fetch-only clinical articles are excluded; their recorded factual values/receipts remain.
Rebuild source-derived data using the recorded package recipes as a separate verification.
Keep the whole bundle with any published result. Git commit or CI retention alone is not
a permanent archive. These unsigned checksums detect modification, not a maliciously
rewritten bundle: establish source authenticity through your trusted release channel.
"""


def build(destination: Path, settings: RunSettings, *, allow_dirty: bool = False) -> dict:
    root = source_root()
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("Bundle creation requires the source checkout's own Git repository")
    package = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if package["project"]["version"] != __version__:
        raise ValueError("Package and runtime versions disagree")
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Release destination already exists; use a new immutable directory")
    if destination.is_relative_to(root) and not destination.is_relative_to(root / "outputs"):
        raise ValueError("Within the checkout, write release bundles only under outputs/")
    commit = git(root, "rev-parse", "HEAD")
    dirty = bool(git(root, "status", "--porcelain"))
    if dirty and not allow_dirty:
        raise ValueError(
            "Release requires a clean checkout; --allow-dirty labels a development snapshot"
        )
    audit = verify_packages(root, check_tracked=True)
    if not audit["passed"]:
        raise ValueError("Evidence package audit failed; inspect demeter data verify-packages")
    source = source_inventory(root)
    # Untracked source is never copied, but must not silently affect the imported model.
    for folder in ("src/demeter", "evidence", "scenarios", "releases"):
        for path in (root / folder).rglob("*"):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.relative_to(root).as_posix() not in source
            ):
                raise ValueError(f"Untracked reproducibility input must be staged first: {path}")
    results = calculate(root, settings)
    if not results["validation"]["software_checks_passed"]:
        raise ValueError("Software/data validation failed; no release bundle created")
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    profile = profile_at(root)
    manifest = dict(
        created_at=datetime.now(timezone.utc).isoformat(),
        software_version=__version__,
        profile=profile,
        module_api_version=API_VERSION,
        git_commit=commit,
        working_tree_dirty=dirty,
        classification="development_snapshot" if dirty else "engineering_checkpoint",
        settings=settings.model_dump(),
        runtime=runtime(),
        evidence={
            "content_sha256": registry.content_hash,
            "file_sha256": source["evidence/parameters.yaml"].sha256,
            "audit": registry.audit(),
        },
        data={
            "inventory": "data-audit.json",
            "sources": audit["sources"],
            "artifacts": audit["artifacts"],
            "source_manifests": sorted(
                {s["manifest"] for s in audit["sources"] if s.get("manifest")}
            ),
        },
        calibration={
            "clinical": profile["clinical_calibration"],
            "mortality": {
                "method": "existing per-age mixture normalization to source life table",
                "year": results["baseline"]["metadata"]["mortality_vintage"],
            },
            "historical_benchmarks": {
                "artifact": "results/historical.json",
                "windows": "Each series.fold records training_years, interval_validation and holdout roles",
            },
        },
        validation={
            "artifact": "results/validation.json",
            "scientific_release_ready": False,
            "historical": "results/historical.json",
            "sensitivity": "results/sensitivity.json",
            "uncertainty": "results/uncertainty.json",
            "independent_scientific_review": "not asserted",
        },
        scenario_compatibility={
            "schema": Scenario.model_json_schema(),
            "baseline": results["baseline"]["metadata"]["scenario"],
            "intervention": results["intervention"]["metadata"]["scenario"],
        },
        source_tree_sha256=tree_hash(source),
        source_files=source,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".demeter-release-", dir=destination.parent) as temp:
        stage = Path(temp)
        with zipfile.ZipFile(
            stage / "source.zip", "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for name, expected in source.items():
                content = inside(root, name).read_bytes()
                if receipt(content) != expected:
                    raise ValueError("Source changed while building bundle")
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, content)
        (stage / "results").mkdir()
        for name, value in results.items():
            (stage / "results" / f"{name}.json").write_bytes(canonical(value))
        (stage / "data-audit.json").write_bytes(canonical(audit))
        (stage / "MODEL_CARD.md").write_text(
            model_card(manifest, results), encoding="utf-8", newline="\n"
        )
        (stage / "REPRODUCE.md").write_text(REPRODUCE, encoding="utf-8", newline="\n")
        artifacts = {
            p.relative_to(stage).as_posix(): receipt(p.read_bytes())
            for p in sorted(stage.rglob("*"))
            if p.is_file()
        }
        parsed = ReleaseManifest(**manifest, artifacts=artifacts)
        encoded = canonical(parsed.model_dump(mode="json"))
        (stage / "manifest.json").write_bytes(encoded)
        (stage / "manifest.sha256").write_text(
            digest(encoded) + "\n", encoding="ascii", newline="\n"
        )
        if source_inventory(root) != source or git(root, "rev-parse", "HEAD") != commit:
            raise ValueError("Source changed during calculation; discard and rebuild")
        verify(stage)
        # Only rename our newly created sibling temporary directory into an absent target.
        if stage.parent.resolve() != destination.parent or destination.exists():
            raise ValueError("Release destination changed during build")
        os.rename(stage, destination)
    return {
        "bundle": str(destination),
        "manifest_sha256": digest(encoded),
        "git_commit": commit,
        "classification": parsed.classification,
        "scientific_release_ready": False,
    }


def verify(bundle: Path) -> dict:
    bundle = bundle.resolve()
    encoded = inside(bundle, "manifest.json").read_bytes()
    if digest(encoded) != inside(bundle, "manifest.sha256").read_text(encoding="ascii").strip():
        raise ValueError("Manifest checksum mismatch")
    manifest = ReleaseManifest.model_validate_json(encoded)
    if tree_hash(manifest.source_files) != manifest.source_tree_sha256:
        raise ValueError("Source tree checksum mismatch")
    expected_names = set(manifest.artifacts) | {"manifest.json", "manifest.sha256"}
    actual_names = {
        p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file() or p.is_symlink()
    }
    if actual_names != expected_names:
        raise ValueError("Missing or unexpected bundle files")
    for name, expected in manifest.artifacts.items():
        if receipt(inside(bundle, name).read_bytes()) != expected:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    with zipfile.ZipFile(bundle / "source.zip") as archive:
        names = archive.namelist()
        if (
            len(set(names)) != len(names)
            or len({n.casefold() for n in names}) != len(names)
            or set(names) != set(manifest.source_files)
        ):
            raise ValueError("Source ZIP inventory mismatch or colliding names")
        for entry in archive.infolist():
            safe_name(entry.filename)
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError("Nonregular source ZIP entry")
            expected = manifest.source_files[entry.filename]
            if entry.file_size != expected.bytes or receipt(archive.read(entry)) != expected:
                raise ValueError(f"Source ZIP checksum mismatch: {entry.filename}")
        registry = EvidenceRegistry.model_validate(
            yaml.safe_load(archive.read("evidence/parameters.yaml"))
        )
        profile = yaml.safe_load(archive.read("releases/profile.yaml"))
        package = tomllib.loads(archive.read("pyproject.toml").decode("utf-8"))
        if (
            manifest.evidence
            != {
                "content_sha256": registry.content_hash,
                "file_sha256": manifest.source_files["evidence/parameters.yaml"].sha256,
                "audit": registry.audit(),
            }
            or manifest.profile != profile
            or manifest.software_version != package["project"]["version"]
            or manifest.calibration["clinical"] != profile["clinical_calibration"]
        ):
            raise ValueError("Manifest metadata disagrees with archived source/evidence")
        for name in ("baseline", "intervention"):
            scenario = Scenario.model_validate(yaml.safe_load(archive.read(profile[name])))
            result = json.loads((bundle / "results" / f"{name}.json").read_bytes())
            if (
                result["metadata"]["scenario"] != scenario.model_dump(mode="json")
                or manifest.scenario_compatibility[name] != scenario.model_dump(mode="json")
                or result["metadata"]["evidence_sha256"] != registry.content_hash
                or result["metadata"]["model_version"] != manifest.software_version
                or result["validation_only"] is not True
            ):
                raise ValueError("Result provenance disagrees with manifest/source")
    audit = json.loads((bundle / "data-audit.json").read_bytes())
    uncertainty_result = json.loads((bundle / "results/uncertainty.json").read_bytes())
    sensitivity_result = json.loads((bundle / "results/sensitivity.json").read_bytes())
    validation_result = json.loads((bundle / "results/validation.json").read_bytes())
    if (
        not audit["passed"]
        or manifest.data["sources"] != audit["sources"]
        or manifest.data["artifacts"] != audit["artifacts"]
        or uncertainty_result["draws"] != manifest.settings.draws
        or sensitivity_result["base_samples"] != manifest.settings.samples
        or uncertainty_result["seed"] != manifest.settings.seed
        or sensitivity_result["seed"] != manifest.settings.seed
        or validation_result["scientific_release_ready"] is not False
        or not validation_result["software_checks_passed"]
    ):
        raise ValueError("Manifest settings/status disagree with archived diagnostics")
    return {
        "passed": True,
        "manifest_sha256": digest(encoded),
        "source_files": len(manifest.source_files),
        "artifacts": len(manifest.artifacts),
        "code_executed": False,
        "scientific_acceptance": False,
    }


def extract(bundle: Path, destination: Path) -> dict:
    verify(bundle)
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Extraction destination must not exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".demeter-extract-", dir=destination.parent) as temp:
        stage = Path(temp)
        with zipfile.ZipFile(bundle / "source.zip") as archive:
            for name in archive.namelist():
                target = inside(stage, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
        if stage.parent.resolve() != destination.parent or destination.exists():
            raise ValueError("Extraction destination changed")
        os.rename(stage, destination)
    return {"source": str(destination), "code_executed": False}


def differences(expected, actual, path="") -> list[str]:
    if type(expected) is not type(actual):
        return [path + ": type changed"]
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return [path + ": keys changed"]
        return [d for k in expected for d in differences(expected[k], actual[k], f"{path}/{k}")]
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [path + ": length changed"]
        return [
            d
            for i, (a, b) in enumerate(zip(expected, actual, strict=True))
            for d in differences(a, b, f"{path}/{i}")
        ]
    if isinstance(expected, float):
        return (
            []
            if math.isclose(expected, actual, rel_tol=RTOL, abs_tol=ATOL)
            else [path + ": numeric mismatch"]
        )
    return [] if expected == actual else [path + ": value changed"]


def replay(bundle: Path) -> dict:
    verify(bundle)
    manifest = ReleaseManifest.model_validate_json((bundle / "manifest.json").read_bytes())
    root = source_root()
    for name, expected in manifest.source_files.items():
        if receipt(inside(root, name).read_bytes()) != expected:
            raise ValueError(f"Replay source differs: {name}; use the extracted source snapshot")
    expected_runtime_files = {
        name for name in manifest.source_files if name.startswith("src/demeter/")
    }
    actual_runtime_files = {
        p.relative_to(root).as_posix()
        for p in (root / "src/demeter").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    if actual_runtime_files != expected_runtime_files:
        raise ValueError("Unexpected or missing runtime source files")
    current = calculate(root, manifest.settings)
    comparisons = {}
    ignored = ["historical/metadata/git_commit", "historical/metadata/working_tree_dirty"]
    for name, value in current.items():
        expected = json.loads((bundle / "results" / f"{name}.json").read_bytes())
        if name == "historical":
            for field in ("git_commit", "working_tree_dirty"):
                expected["metadata"].pop(field)
                value["metadata"].pop(field)
        errors = differences(expected, value, name)
        comparisons[name] = {
            "passed": not errors,
            "exact": not errors and expected == value,
            "mismatch_count": len(errors),
            "first_mismatches": errors[:20],
        }
    return {
        "passed": all(r["passed"] for r in comparisons.values()),
        "comparisons": comparisons,
        "relative_tolerance": RTOL,
        "absolute_tolerance": ATOL,
        "ignored_location_metadata": ignored,
        "original_runtime": manifest.runtime,
        "replay_runtime": runtime(),
        "source_tree_sha256": manifest.source_tree_sha256,
        "scientific_acceptance": False,
    }
