"""Versioned local packages; inspect without importing, execute only by explicit selection.

This is a provenance/compatibility boundary, not a Python security sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from typing import Literal

from pydantic import Field, model_validator
import yaml

from demeter import __version__
from demeter.contracts import API_VERSION, require_api
from demeter.model import SimulationResult, simulate
from demeter.schema import EvidenceRegistry, Scenario, StrictModel

PROJECT = Path(__file__).resolve().parents[2]
CATALOG = PROJECT / "extensions/catalog.yaml"
LOCAL_REGISTRY = Path("outputs/extension-registry.yaml")
Classification = Literal["canonical", "experimental", "third_party"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(root: Path, name: str) -> Path:
    """Portable relative file names, with no traversal, symlink or drive aliases."""
    from demeter.releases import safe_name

    safe_name(name)
    path = root
    for part in name.split("/"):
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Package symlinks are unsupported: {name}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Package path escapes root: {name}")
    return path


class ModuleEntry(StrictModel):
    file: str
    factory: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")


class PackageManifest(StrictModel):
    schema_version: Literal[1]
    package_id: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    authors: list[str] = Field(min_length=1)
    license: str = Field(min_length=1)
    description: str = Field(min_length=1)
    model_versions: list[str] = Field(min_length=1)
    module_api: str
    health_structures: list[Literal["legacy", "risk_1", "risk_2"]] = Field(min_length=1)
    evidence_status: Literal["synthetic", "mixed", "sourced", "unresolved"]
    validation_status: Literal["unvalidated", "software_tested"]
    validation_notes: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    files: dict[str, str] = Field(min_length=1)
    scenarios: dict[str, str] = Field(min_length=1)
    modules: dict[str, ModuleEntry] = Field(default_factory=dict)
    evidence: str | None = None

    @property
    def selector(self) -> str:
        return f"{self.package_id}@{self.version}"

    @model_validator(mode="after")
    def declared_files(self):
        from demeter.releases import safe_name

        for value in [
            *self.authors,
            self.license,
            self.description,
            self.validation_notes,
            *self.limitations,
        ]:
            if not value.strip():
                raise ValueError("Package metadata must not be blank")
        for name, digest in self.files.items():
            safe_name(name)
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"Invalid SHA-256 for {name}")
        paths = [*self.scenarios.values(), *(m.file for m in self.modules.values())]
        if self.evidence:
            paths.append(self.evidence)
        if any(path not in self.files for path in paths):
            raise ValueError("Every scenario, module and evidence file requires a checksum")
        if any(not m.file.endswith(".py") for m in self.modules.values()):
            raise ValueError("Module factories require a Python source file")
        if any(not key or "@" in key for key in (*self.scenarios, *self.modules)):
            raise ValueError("Scenario and module entry names must be nonempty and omit @")
        return self


class CatalogEntry(StrictModel):
    manifest: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: Literal["canonical", "experimental"]


class ProjectCatalog(StrictModel):
    schema_version: Literal[1]
    packages: dict[str, CatalogEntry]


class LocalEntry(StrictModel):
    manifest: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LocalRegistry(StrictModel):
    schema_version: Literal[1] = 1
    packages: dict[str, LocalEntry] = Field(default_factory=dict)


def local_registry(path: Path) -> LocalRegistry:
    return (
        LocalRegistry.model_validate(yaml.safe_load(path.read_bytes()))
        if path.exists()
        else LocalRegistry()
    )


@dataclass(frozen=True)
class Package:
    manifest: PackageManifest
    manifest_sha256: str
    path: Path
    root: Path
    classification: Classification
    contents: dict[str, bytes]

    def verify(self) -> None:
        if sha256(self.path.read_bytes()) != self.manifest_sha256:
            raise ValueError("Package manifest changed; use a new version and register again")
        for name, expected in self.manifest.files.items():
            if (
                sha256(self.contents[name]) != expected
                or sha256(safe_path(self.root, name).read_bytes()) != expected
            ):
                raise ValueError(f"Package checksum mismatch: {name}")

    def receipt(self) -> dict:
        return {
            "selector": self.manifest.selector,
            "classification": self.classification,
            "manifest_sha256": self.manifest_sha256,
            "manifest": self.manifest.model_dump(mode="json"),
            "declarations_are_publisher_claims": True,
            "scientific_approval": False,
            "pin_scope": "Declared package files; external imports require the recorded model version and a preserved environment. Hashes are not signatures.",
        }

    def scenario(self, key: str) -> Scenario:
        if key not in self.manifest.scenarios:
            raise ValueError(f"Unknown scenario entry: {key}")
        value = Scenario.model_validate(yaml.safe_load(self.contents[self.manifest.scenarios[key]]))
        if value.health_structure not in self.manifest.health_structures:
            raise ValueError("Scenario health structure is not declared compatible")
        # An author's validation-status declaration cannot authorize scientific execution.
        if value.mode != "validation":
            raise ValueError("Extension packages currently support validation-mode scenarios only")
        return value

    def evidence_registry(self, base: EvidenceRegistry) -> EvidenceRegistry:
        data = base.model_dump(mode="json")
        if self.manifest.evidence:
            extra = yaml.safe_load(self.contents[self.manifest.evidence])
            if not isinstance(extra, dict) or set(extra) - {
                "parameters",
                "sources",
                "scientific_blockers",
            }:
                raise ValueError(
                    "Package evidence may only append parameters, sources and blockers"
                )
            for kind in ("parameters", "sources"):
                records = extra.get(kind, {})
                if not isinstance(records, dict):
                    raise ValueError(f"Package {kind} must be a mapping")
                if data[kind].keys() & records.keys():
                    raise ValueError(f"Package cannot override existing {kind}")
                if any(
                    not isinstance(k, str) or not k.startswith(self.manifest.package_id + ".")
                    for k in records
                ):
                    raise ValueError("New evidence keys must use the package namespace")
                data[kind].update(records)
            blockers = extra.get("scientific_blockers", [])
            if not isinstance(blockers, list) or any(not isinstance(b, str) for b in blockers):
                raise ValueError("Scientific blockers must be a list of strings")
            data["scientific_blockers"].extend(blockers)
        return EvidenceRegistry.model_validate(data)

    def module(self, key: str | None):
        if key is None:
            return None
        if key not in self.manifest.modules:
            raise ValueError(f"Unknown module entry: {key}")
        entry = self.manifest.modules[key]
        path = safe_path(self.root, entry.file)
        name = "_demeter_extension_" + self.manifest_sha256 + "_" + sha256(entry.file.encode())
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        # Compile the verified bytes directly: do not use potentially stale .pyc caches.
        exec(compile(self.contents[entry.file], str(path), "exec"), module.__dict__)
        factory = getattr(module, entry.factory, None)
        if not callable(factory):
            raise ValueError("Module entry must name a callable zero-argument factory")
        instance = factory()
        if not callable(getattr(instance, "describe", None)) or not callable(
            getattr(instance, "hazards", None)
        ):
            raise ValueError("Factory must return a transition module")
        source = inspect.getsourcefile(type(instance))
        if source is None or Path(source).resolve() != path.resolve():
            raise ValueError("Returned module class must be defined in its pinned entry file")
        return instance


def _read(
    path: Path, root: Path, classification: Classification, expected: str | None = None
) -> Package:
    if path.is_symlink() or root.is_symlink():
        raise ValueError("Package symlinks are unsupported")
    raw = path.read_bytes()
    digest = sha256(raw)
    if expected is not None and digest != expected:
        raise ValueError("Package manifest checksum mismatch")
    manifest = PackageManifest.model_validate(yaml.safe_load(raw))
    if classification == "third_party" and manifest.package_id.startswith("demeter."):
        raise ValueError("The demeter namespace is reserved for the curated catalog")
    require_api(manifest.module_api)
    if __version__ not in manifest.model_versions:
        raise ValueError(f"Package does not declare compatibility with Demeter {__version__}")
    contents = {name: safe_path(root, name).read_bytes() for name in manifest.files}
    package = Package(manifest, digest, path.resolve(), root.resolve(), classification, contents)
    package.verify()
    # Parse scenarios without importing executable modules.
    for key in manifest.scenarios:
        package.scenario(key)
    return package


def curated() -> dict[str, Package]:
    if not CATALOG.exists():
        return {}
    catalog = ProjectCatalog.model_validate(yaml.safe_load(CATALOG.read_bytes()))
    output = {}
    for selector, entry in catalog.packages.items():
        package = _read(
            safe_path(PROJECT, entry.manifest), PROJECT, entry.classification, entry.sha256
        )
        if selector != package.manifest.selector:
            raise ValueError("Curated catalog key differs from package identity")
        output[selector] = package
    return output


def resolve(selector: str, registry: Path = LOCAL_REGISTRY) -> Package:
    if selector in (packages := curated()):
        return packages[selector]
    entries = local_registry(registry).packages
    if selector not in entries:
        raise ValueError(f"Package is not registered: {selector}")
    entry = entries[selector]
    path = Path(entry.manifest)
    if not path.is_absolute():
        raise ValueError("Local registry manifest paths must be absolute")
    package = _read(path, path.parent, "third_party", entry.sha256)
    if package.manifest.selector != selector:
        raise ValueError("Local registry key differs from package identity")
    return package


def inspect_package(path: Path) -> dict:
    return {
        **_read(path.absolute(), path.absolute().parent, "third_party").receipt(),
        "code_executed": False,
    }


def register(path: Path, registry: Path = LOCAL_REGISTRY) -> dict:
    package = _read(path.absolute(), path.absolute().parent, "third_party")
    if registry.resolve() in {
        package.path,
        *(safe_path(package.root, p).resolve() for p in package.manifest.files),
    }:
        raise ValueError("Local registry must be outside pinned package files")
    entries = local_registry(registry)
    key = package.manifest.selector
    entry = LocalEntry(manifest=str(package.path), sha256=package.manifest_sha256)
    if key in entries.packages and entries.packages[key] != entry:
        raise ValueError("Registered versions are immutable; use a new package version")
    entries.packages[key] = entry
    registry.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=registry.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(yaml.safe_dump(entries.model_dump(), sort_keys=True))
    try:
        os.replace(temporary, registry)
    finally:
        temporary.unlink(missing_ok=True)
    return {**package.receipt(), "code_executed": False, "local_registry": str(registry)}


def list_packages(registry: Path = LOCAL_REGISTRY) -> dict:
    packages = curated()
    for key in local_registry(registry).packages:
        if key in packages:
            raise ValueError("Local registry cannot shadow the curated catalog")
        packages[key] = resolve(key, registry)
    return {"code_executed": False, "packages": [p.receipt() for p in packages.values()]}


def run(
    base: EvidenceRegistry, package: Package, scenario: str, module: str | None = None
) -> SimulationResult:
    package.verify()
    model_scenario = package.scenario(scenario)
    evidence = package.evidence_registry(base)
    result = simulate(evidence, model_scenario, transition_module=package.module(module))
    package.verify()
    result.metadata["extension_provenance"] = {
        "schema_version": 1,
        "core_model_version": __version__,
        "module_api_version": API_VERSION,
        "active_packages": [package.receipt()],
        "scenario_entry": scenario,
        "module_entry": module,
        "equations": "package_module" if module else "canonical_engine",
        "base_evidence_sha256": base.content_hash,
        "merged_evidence_sha256": evidence.content_hash,
        "added_parameter_keys": sorted(evidence.parameters.keys() - base.parameters.keys()),
        "actual_active_evidence": evidence.audit(
            parameter_keys=result.metadata["active_parameters"]
        ),
        "validation": "Contract checks and engine conservation/bounds passed; publisher testing claims are not independently verified; clinical calibration is deferred.",
        "uncertainty": "Deterministic conditional evaluation; package comparisons do not propagate uncertainty.",
    }
    return result


def compare(
    base: EvidenceRegistry,
    left: Package,
    left_scenario: str,
    right: Package,
    right_scenario: str,
    *,
    left_module: str | None = None,
    right_module: str | None = None,
) -> dict:
    a, b = left.scenario(left_scenario), right.scenario(right_scenario)
    if any(getattr(a, k) != getattr(b, k) for k in ("years", "baseline_year", "sex", "mode")):
        raise ValueError(
            "Package comparison requires equal horizons, mortality vintages, sex and mode"
        )
    results = (
        run(base, left, left_scenario, left_module),
        run(base, right, right_scenario, right_module),
    )
    if results[0].starting_population != results[1].starting_population:
        raise ValueError("Package comparison requires the same initial population")
    outcomes = {}
    for key in ("life_expectancy", "t2d_free_life_expectancy", "cumulative_deaths"):
        x, y = (r.annual[-1][key] for r in results)
        outcomes[key] = {
            "left": x,
            "right": y,
            "absolute_delta": y - x,
            "relative_delta": (y - x) / x if x else None,
        }
    return {
        "validation_only": True,
        "interpretation": "Descriptive scenario/structure contrast, not causal attribution. State membership, starting allocation and equation differences may all contribute. Healthy-state years are not subtracted across different definitions.",
        "outcome_units": {
            "life_expectancy": "years",
            "t2d_free_life_expectancy": "years",
            "cumulative_deaths": "people",
        },
        "outcomes": outcomes,
        "left": results[0].to_dict(),
        "right": results[1].to_dict(),
    }
