"""Audit repository evidence packages without fetching or granting data-use rights."""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from demeter.data.ingest import digest
from demeter.schema import EvidenceRegistry, StrictModel


class RightsPolicy(StrictModel):
    title: str = Field(min_length=1)
    terms_urls: list[str] = Field(min_length=1)
    checked_on: date
    redistribution: Literal["conditional", "facts_only", "not_permitted"]
    download: str = Field(min_length=1)
    transform: str = Field(min_length=1)
    conditions: list[str] = Field(min_length=1)


class SourceRights(StrictModel):
    policy: str
    privacy: Literal["aggregate", "public_use_microdata", "publication", "metadata"]
    publisher: str = Field(min_length=1)
    vintage: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    notes: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: datetime

    @model_validator(mode="after")
    def timezone_required(self):
        if self.retrieved_at.utcoffset() is None:
            raise ValueError("Source retrieval timestamp must have a timezone")
        return self


class ExternalRights(SourceRights):
    distribution: Literal["fetch_only"]
    alternative: str = Field(min_length=1)


class RightsInventory(StrictModel):
    schema_version: Literal[1]
    policies: dict[str, RightsPolicy]
    source_files: dict[str, SourceRights]
    clinical_sources: dict[str, ExternalRights]

    @model_validator(mode="after")
    def known_policies(self):
        for source in [*self.source_files.values(), *self.clinical_sources.values()]:
            if source.policy not in self.policies:
                raise ValueError(f"Unknown rights policy: {source.policy}")
        for policy in self.policies.values():
            if any(not url.startswith("https://") for url in policy.terms_urls):
                raise ValueError("Rights policies need HTTPS source links")
        return self


class Artifact(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidencePackage(StrictModel):
    store: str | None
    dependencies: list[str]
    registry_datasets: list[str]
    registry_parameters: list[str]
    artifacts: list[Artifact]
    transform_files: list[str] = Field(min_length=1)
    rebuild: list[str] = Field(min_length=1)
    model_role: str = Field(min_length=1)
    redistribution: str = Field(min_length=1)


class PackageManifest(StrictModel):
    schema_version: Literal[1]
    packages: dict[str, EvidencePackage]
    supporting_artifacts: list[Artifact]

    @model_validator(mode="after")
    def references(self):
        paths = [a.path for p in self.packages.values() for a in p.artifacts]
        paths += [a.path for a in self.supporting_artifacts]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate package artifact; use a dependency instead")
        for name, package in self.packages.items():
            if name in package.dependencies or set(package.dependencies) - self.packages.keys():
                raise ValueError(f"Invalid dependencies for {name}")
        visiting, visited = set(), set()

        def visit(name):
            if name in visiting:
                raise ValueError("Evidence package dependency cycle")
            if name in visited:
                return
            visiting.add(name)
            for dependency in self.packages[name].dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in self.packages:
            visit(name)
        return self


def _inside(root: Path, relative: str) -> Path:
    """Use portable relative paths; reject traversal, symlinks and Windows drives."""
    parts = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or ":" in relative
        or parts.is_absolute()
        or ".." in parts.parts
        or str(parts) != relative
    ):
        raise ValueError(f"Not a portable repository-relative path: {relative}")
    path = root.joinpath(*parts.parts)
    if not path.resolve().is_relative_to(root) or any(
        p.is_symlink() for p in [path, *path.parents]
    ):
        raise ValueError(f"Evidence path escapes repository or uses a symlink: {relative}")
    return path


def verify_packages(root: Path = Path("."), *, check_tracked: bool = False) -> dict:
    """Check coverage, provenance, rights classification and bytes, entirely offline.

    This verifies recorded decisions, not the legal correctness of those decisions
    or absence of identifying information in a newly approved source.
    """
    root = root.resolve()
    rights = RightsInventory.model_validate_json(_inside(root, "data/rights.json").read_bytes())
    packages = PackageManifest.model_validate_json(
        _inside(root, "data/evidence-packages.json").read_bytes()
    )
    registry = EvidenceRegistry.from_yaml(_inside(root, "evidence/parameters.yaml"))
    catalog = json.loads(_inside(root, "data/catalog.json").read_bytes())
    if catalog["schema_version"] != 1:
        raise ValueError("Unknown source-store catalog version")
    stores = {store["id"]: store for store in catalog["stores"]}
    if len(stores) != len(catalog["stores"]):
        raise ValueError("Duplicate source-store ID")
    checks, sources, outputs = [], [], []
    transform_hashes = {}
    allowed = {
        "data/catalog.json",
        "data/rights.json",
        "data/evidence-packages.json",
        "data/sources/archive.json",
        "data/sources/README.md",
        "evidence/parameters.yaml",
    }

    def check(name: str, passed: bool, **detail):
        checks.append({"check": name, "passed": bool(passed), **detail})

    def artifact(item: Artifact):
        path = _inside(root, item.path)
        actual = digest(path.read_bytes()) if path.is_file() else None
        check("artifact_checksum", actual == item.sha256, path=item.path)
        allowed.add(item.path)
        outputs.append(item.model_dump())

    expected_sources = set()
    for store_id, store in stores.items():
        manifest_name = "data/" + store["manifest"]
        manifest_path = _inside(root, manifest_name)
        allowed.add(manifest_name)
        manifest = json.loads(manifest_path.read_bytes())
        for filename, receipt in manifest["sources"].items():
            if PurePosixPath(filename).name != filename or "\\" in filename:
                raise ValueError("Source filename must be a basename")
            name = str(PurePosixPath(manifest_name).parent / filename)
            if name in expected_sources:
                raise ValueError(f"Duplicate source artifact: {name}")
            expected_sources.add(name)
            allowed.add(name)
            item = rights.source_files.get(name)
            check("source_rights_record", item is not None, path=name)
            if item is None:
                continue
            policy = rights.policies[item.policy]
            check(
                "rights_receipt_match",
                item.url == receipt["url"]
                and item.sha256 == receipt["sha256"]
                and item.retrieved_at == datetime.fromisoformat(receipt["retrieved_at"]),
                path=name,
            )
            check("raw_redistribution", policy.redistribution != "not_permitted", path=name)
            check(
                "source_identity",
                all(
                    getattr(item, key) == receipt[key]
                    for key in ("publisher", "vintage")
                    if receipt.get(key)
                ),
                path=name,
            )
            source_path = _inside(root, name)
            sha = digest(source_path.read_bytes()) if source_path.is_file() else None
            check("source_checksum", sha == receipt["sha256"], path=name)
            retrieved = datetime.fromisoformat(receipt["retrieved_at"])
            check(
                "source_provenance",
                bool(receipt["url"].startswith("https://")) and retrieved.utcoffset() is not None,
                path=name,
            )
            sources.append(
                {
                    "path": name,
                    "store": store_id,
                    "distribution": "archived",
                    "manifest": manifest_name,
                    "url": receipt["url"],
                    "sha256": receipt["sha256"],
                    "retrieved_at": receipt["retrieved_at"],
                    **item.model_dump(mode="json"),
                }
            )
    check(
        "rights_coverage",
        bool(expected_sources) and expected_sources == set(rights.source_files),
        extra=sorted(set(rights.source_files) - expected_sources),
    )
    check("clinical_coverage", set(rights.clinical_sources) == set(registry.sources))
    for source_id, source in registry.sources.items():
        item = rights.clinical_sources.get(source_id)
        if item is None:
            continue
        rights.policies[item.policy]  # Reject undefined policies even for fetch-only sources.
        check(
            "clinical_receipt_match",
            item.url == source.url
            and item.sha256 == source.sha256
            and item.retrieved_at == source.retrieved_at,
            source=source_id,
        )
        sources.append(
            {
                "source_id": source_id,
                **source.model_dump(mode="json"),
                **item.model_dump(mode="json"),
            }
        )
    package_stores, datasets, parameters = [], set(), set()
    for name, package in packages.packages.items():
        if package.store:
            package_stores.append(package.store)
            store = stores[package.store]
            bundle = store.get("derived_bundle")
            if bundle:
                bundle_path = (root / "data" / bundle).resolve()
                check(
                    "package_bundle",
                    bundle_path.is_relative_to(root)
                    and bundle_path.relative_to(root).as_posix()
                    in {a.path for a in package.artifacts},
                    package=name,
                )
        datasets.update(package.registry_datasets)
        parameters.update(package.registry_parameters)
        check(
            "registry_references",
            not (set(package.registry_datasets) - registry.datasets.keys())
            and not (set(package.registry_parameters) - registry.parameters.keys()),
            package=name,
        )
        for file in package.transform_files:
            transform = _inside(root, file)
            check("transform_exists", transform.is_file(), package=name, path=file)
            if transform.is_file():
                transform_hashes[file] = digest(transform.read_bytes())
        for item in package.artifacts:
            artifact(item)
    check(
        "package_store_coverage",
        bool(stores) and set(package_stores) == set(stores) and len(package_stores) == len(stores),
    )
    check("dataset_coverage", datasets == set(registry.datasets))
    expected_parameters = {key for key, value in registry.parameters.items() if value.source_id}
    check("clinical_parameter_coverage", expected_parameters <= parameters)
    for item in packages.supporting_artifacts:
        artifact(item)

    # An allowlist prevents an unrelated dataset entering the store or wheel merely
    # because an existing manifest and its checksums still pass.
    for directory in ("data/sources", "src/demeter/data/bundled"):
        for path in (root / directory).rglob("*"):
            if path.is_file():
                name = path.relative_to(root).as_posix()
                check("distribution_allowlist", name in allowed, path=name)
    if check_tracked:
        tracked = (
            subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z"],
                check=True,
                capture_output=True,
            )
            .stdout.decode("utf-8")
            .split("\0")
        )
        data_extensions = {
            ".csv",
            ".tsv",
            ".xlsx",
            ".xls",
            ".xpt",
            ".parquet",
            ".sav",
            ".dta",
            ".pdf",
            ".html",
            ".htm",
            ".json",
            ".zip",
        }
        for name in filter(None, tracked):
            file = _inside(root, name)
            if file.is_file():
                check(
                    "fetch_only_not_tracked",
                    digest(file.read_bytes()) not in {s.sha256 for s in registry.sources.values()},
                    path=name,
                )
            forbidden_cache = name.startswith(("data/raw/", "data/processed/", "outputs/"))
            is_data = PurePosixPath(name).suffix.lower() in data_extensions
            # These exact files configure development tools; they are not datasets.
            # Still check their bytes against fetch-only sources above. Do not
            # exempt web/ wholesale: data added there needs the ordinary review.
            development_metadata = {
                ".github/branch-protection.json",
                "web/package.json",
                "web/package-lock.json",
                "web/tsconfig.json",
            }
            if name.endswith("/.gitkeep") or name in development_metadata:
                continue
            if forbidden_cache or is_data:
                check("tracked_data_allowlist", not forbidden_cache and name in allowed, path=name)
    return {
        "passed": all(item["passed"] for item in checks),
        "network_used": False,
        "tracked_files_checked": check_tracked,
        "evidence_sha256": registry.content_hash,
        "transform_sha256": transform_hashes,
        "sources": sources,
        "artifacts": outputs,
        "policies": {key: p.model_dump(mode="json") for key, p in rights.policies.items()},
        "packages": {key: p.model_dump() for key, p in packages.packages.items()},
        "checks": checks,
        "interpretation": "Checks recorded provenance, terms and inventory; not legal certification, "
        "a PII detector, or scientific validation. Raw clinical articles are "
        "fetch-only and are not required for this offline package audit.",
    }
