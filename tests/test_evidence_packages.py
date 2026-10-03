import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.packages import verify_packages


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def package_root(tmp_path):
    """Tiny synthetic distribution, independent of the scientific data/parameters."""
    receipt = dict(
        url="https://example.org/toy",
        sha256=digest(b"aggregate,2\n"),
        retrieved_at="2026-09-28T00:00:00+00:00",
    )
    source = "data/sources/toy/source.csv"
    save(
        tmp_path / "data/catalog.json",
        dict(
            schema_version=1,
            stores=[
                dict(
                    id="toy",
                    manifest="sources/toy/manifest.json",
                    derived_bundle="../src/demeter/data/bundled/toy.json",
                )
            ],
        ),
    )
    save(tmp_path / "data/sources/toy/manifest.json", dict(sources={"source.csv": receipt}))
    (tmp_path / source).write_bytes(b"aggregate,2\n")
    bundle = "src/demeter/data/bundled/toy.json"
    save(tmp_path / bundle, {})
    transform = "src/demeter/data/toy.py"
    (tmp_path / transform).write_text("# synthetic transform fixture\n")
    rights = dict(
        schema_version=1,
        policies={
            "toy": dict(
                title="Synthetic test policy",
                terms_urls=["https://example.org/terms"],
                checked_on="2026-09-28",
                redistribution="conditional",
                download="Synthetic fixture",
                transform="Synthetic fixture",
                conditions=["Not an actual source license"],
            )
        },
        source_files={
            source: dict(
                policy="toy",
                privacy="aggregate",
                publisher="Synthetic fixture",
                vintage="test",
                citation="Synthetic fixture",
                notes="No empirical data",
                **receipt,
            )
        },
        clinical_sources={},
    )
    save(tmp_path / "data/rights.json", rights)
    package = dict(
        store="toy",
        dependencies=[],
        registry_datasets=["toy"],
        registry_parameters=[],
        artifacts=[dict(path=bundle, sha256=digest(b"{}"))],
        transform_files=[transform],
        rebuild=["synthetic fixture only"],
        model_role="test_only",
        redistribution="synthetic fixture",
    )
    save(
        tmp_path / "data/evidence-packages.json",
        dict(schema_version=1, packages={"toy": package}, supporting_artifacts=[]),
    )
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence/parameters.yaml").write_text(
        yaml.safe_dump(dict(parameters={}, datasets={"toy": {}}))
    )
    return tmp_path


def edit(root, filename, change):
    path = root / filename
    data = json.loads(path.read_bytes())
    change(data)
    save(path, data)


def failed(report, check):
    return any(row["check"] == check and not row["passed"] for row in report["checks"])


def test_real_packages_cover_every_source_and_bundle_without_network(monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Package audit must stay offline")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    report = verify_packages(check_tracked=True)
    assert report["passed"], [c for c in report["checks"] if not c["passed"]]
    assert len(report["sources"]) == 102
    assert len(report["artifacts"]) == 224
    assert len(report["packages"]) == 40
    assert not report["network_used"]
    assert report["documentation"]["metadata_passed"]
    assert len(report["documentation"]["source_checks"]) == 15
    assert not report["documentation"]["raw_bytes_checked"]
    assert report["documentation"]["raw_bytes_passed"] is None
    assert {s["distribution"] for s in report["sources"]} == {"archived", "fetch_only"}
    current_nhanes = report["packages"]["nhanes_2021_2023"]
    assert current_nhanes["model_role"] == "benchmark_only"
    assert current_nhanes["registry_parameters"] == []
    assert current_nhanes["registry_datasets"] == ["nhanes_glycemic_2021_2023"]
    assert len(current_nhanes["artifacts"]) == 4
    mapping = report["packages"]["nhanes_assay_observation"]
    assert mapping["model_role"] == "benchmark_only"
    assert mapping["registry_parameters"] == []
    assert mapping["registry_datasets"] == ["nhanes_assay_observation_2021_2023"]
    assert len(mapping["artifacts"]) == 4
    aric = report["packages"]["aric_outcomes_benchmark"]
    assert aric["model_role"] == "benchmark_only"
    assert len(aric["registry_parameters"]) == 58
    assert len(aric["artifacts"]) == 3
    da_qing = report["packages"]["da_qing_source_coverage"]
    assert da_qing["model_role"] == "benchmark_only"
    assert da_qing["registry_parameters"] == []
    assert len(da_qing["artifacts"]) == 3
    kerala = report["packages"]["kerala_source_admission"]
    assert kerala["model_role"] == "benchmark_only"
    assert kerala["registry_parameters"] == []
    assert len(kerala["artifacts"]) == 17
    assert {
        "docs/validation/kerala-source-admission-v2.json",
        "docs/validation/kerala-selected-source-representation-v2.json",
        "docs/validation/kerala-longitudinal-output-redaction-protocol-v2.json",
    } <= {a["path"] for a in kerala["artifacts"]}
    kerala_sources = [s for s in report["sources"] if s["policy"] == "kerala_public_appraisal"]
    assert len(kerala_sources) == 4
    assert all(s["distribution"] == "fetch_only" for s in kerala_sources)
    da_qing_source = next(
        s for s in report["sources"] if s.get("source_id") == "da_qing2016_mortality_publication"
    )
    assert da_qing_source["distribution"] == "fetch_only"
    direct_sources = [s for s in report["sources"] if s["policy"] == "direct_paired_public_facts"]
    assert {s["source_id"] for s in direct_sources} == {
        "direct_one_year_accepted",
        "direct_two_year_accepted",
        "direct_two_year_pubmed",
    }
    assert all(s["distribution"] == "fetch_only" for s in direct_sources)
    direct_package = report["packages"]["direct_paired_observations"]
    assert direct_package["store"] is None
    assert direct_package["model_role"] == "benchmark_only"
    assert len(direct_package["artifacts"]) == 10
    assert {
        "docs/validation/direct-paired-failed-intake-v1.json",
        "docs/validation/direct-paired-amendment-v2-failure.json",
        "docs/validation/direct-paired-observations-amendment-v3.json",
    } <= {a["path"] for a in direct_package["artifacts"]}


def test_cli_audit_is_reviewable_and_missing_rights_fail(package_root, tmp_path):
    output = tmp_path / "audit.json"
    args = ["data", "verify-packages", "--root", str(package_root), "--output", str(output)]
    assert CliRunner().invoke(app, args).exit_code == 0
    assert json.loads(output.read_bytes())["sources"][0]["url"] == "https://example.org/toy"
    edit(package_root, "data/rights.json", lambda d: d["source_files"].clear())
    assert CliRunner().invoke(app, args).exit_code == 1
    assert failed(json.loads(output.read_bytes()), "source_rights_record")


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://example.org/different"),
        ("sha256", "0" * 64),
        ("retrieved_at", "2026-09-27T00:00:00+00:00"),
    ],
)
def test_rights_metadata_cannot_drift_from_receipt(package_root, field, value):
    edit(
        package_root,
        "data/rights.json",
        lambda d: d["source_files"]["data/sources/toy/source.csv"].update({field: value}),
    )
    assert failed(verify_packages(package_root), "rights_receipt_match")


@pytest.mark.parametrize(
    "path,check",
    [
        ("data/sources/toy/source.csv", "source_checksum"),
        ("src/demeter/data/bundled/toy.json", "artifact_checksum"),
    ],
)
def test_changed_bytes_fail(package_root, path, check):
    (package_root / path).write_bytes(b"unreviewed change")
    assert failed(verify_packages(package_root), check)


def test_extra_source_and_bundle_files_fail_even_when_checksums_pass(package_root):
    (package_root / "data/sources/toy/unreviewed.csv").write_bytes(b"synthetic test")
    (package_root / "src/demeter/data/bundled/unreviewed.json").write_bytes(b"{}")
    result = verify_packages(package_root)
    assert (
        sum(r["check"] == "distribution_allowlist" and not r["passed"] for r in result["checks"])
        == 2
    )


def test_prohibited_raw_redistribution_fails(package_root):
    edit(
        package_root,
        "data/rights.json",
        lambda d: d["policies"]["toy"].update(redistribution="not_permitted"),
    )
    assert failed(verify_packages(package_root), "raw_redistribution")


@pytest.mark.parametrize(
    "field,value",
    [
        ("privacy", "identifiable_health_records"),
        ("policy", "unknown"),
        ("retrieved_at", "2026-09-28T00:00:00"),
    ],
)
def test_unreviewed_classification_and_naive_timestamps_rejected(package_root, field, value):
    edit(
        package_root,
        "data/rights.json",
        lambda d: d["source_files"]["data/sources/toy/source.csv"].update({field: value}),
    )
    with pytest.raises(ValueError):
        verify_packages(package_root)


@pytest.mark.parametrize("path", ["../outside.csv", "C:/outside.csv", "data\\source.csv"])
def test_package_paths_cannot_escape_root(package_root, path):
    edit(
        package_root,
        "data/evidence-packages.json",
        lambda d: d["packages"]["toy"]["artifacts"][0].update(path=path),
    )
    with pytest.raises(ValueError, match="repository-relative"):
        verify_packages(package_root)


def test_missing_dataset_or_package_coverage_fails(package_root):
    edit(package_root, "data/evidence-packages.json", lambda d: d["packages"].clear())
    result = verify_packages(package_root)
    assert failed(result, "package_store_coverage")
    assert failed(result, "dataset_coverage")


def test_cyclic_package_dependencies_are_rejected(package_root):
    edit(
        package_root,
        "data/evidence-packages.json",
        lambda d: d["packages"]["toy"].update(dependencies=["toy"]),
    )
    with pytest.raises(ValueError, match="Invalid dependencies"):
        verify_packages(package_root)


@pytest.mark.parametrize(
    "name",
    [
        "patients.csv",
        "publication.xml",
        ".github/patients.json",
        "web/measurements.json",
        "data/raw/private.txt",
        "outputs/result.json",
    ],
)
def test_tracked_unapproved_data_and_caches_fail(package_root, monkeypatch, name):
    target = package_root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"synthetic forbidden-file test")
    monkeypatch.setattr(
        "demeter.data.packages.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=name.encode() + b"\0"),
    )
    result = verify_packages(package_root, check_tracked=True)
    assert failed(result, "tracked_data_allowlist")


@pytest.mark.parametrize("name", ["web/package.json", "web/package-lock.json", "web/tsconfig.json"])
def test_known_frontend_metadata_is_not_classified_as_a_dataset(package_root, monkeypatch, name):
    save(package_root / name, {"development": True})
    monkeypatch.setattr(
        "demeter.data.packages.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=name.encode() + b"\0"),
    )
    assert verify_packages(package_root, check_tracked=True)["passed"]


@pytest.mark.parametrize("name", ["notes.md", "web/package.json"])
def test_fetch_only_article_bytes_are_rejected_even_when_renamed(package_root, monkeypatch, name):
    raw = b"synthetic full article test"
    registry_path = package_root / "evidence/parameters.yaml"
    registry = yaml.safe_load(registry_path.read_text())
    receipt = dict(
        url="https://example.org/article",
        citation="Synthetic article",
        doi="test",
        raw_filename="article.html",
        sha256=digest(raw),
        retrieved_at="2026-09-28T00:00:00+00:00",
        license="Test fetch-only",
    )
    registry["sources"] = {"article": receipt}
    registry_path.write_text(yaml.safe_dump(registry))
    rights = dict(
        policy="toy",
        privacy="publication",
        publisher="Test",
        vintage="Test",
        citation="Synthetic",
        notes="Synthetic",
        distribution="fetch_only",
        alternative="Use permitted facts",
        **{k: receipt[k] for k in ["url", "sha256", "retrieved_at"]},
    )
    edit(package_root, "data/rights.json", lambda d: d["clinical_sources"].update(article=rights))
    target = package_root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    monkeypatch.setattr(
        "demeter.data.packages.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=name.encode() + b"\0"),
    )
    assert failed(verify_packages(package_root, check_tracked=True), "fetch_only_not_tracked")


@pytest.fixture
def archived_registry_source(package_root):
    """Link a reviewed archive to its registry identity without duplicating bytes."""
    source_path = "data/sources/toy/source.csv"
    source_rights = json.loads((package_root / "data/rights.json").read_bytes())["source_files"][
        source_path
    ]
    registry_path = package_root / "evidence/parameters.yaml"
    registry = yaml.safe_load(registry_path.read_text())
    registry["sources"] = {
        "toy_publication": dict(
            **{key: source_rights[key] for key in ("url", "sha256", "retrieved_at")},
            citation="Synthetic publication",
            doi="test",
            raw_filename="source.csv",
            license="Synthetic permitted archive",
        )
    }
    registry_path.write_text(yaml.safe_dump(registry))
    edit(
        package_root,
        "data/rights.json",
        lambda d: d["clinical_sources"].update(
            toy_publication=dict(
                **source_rights,
                distribution="archived",
                archive_path=source_path,
                alternative="Use reviewed aggregate archive",
            )
        ),
    )
    return package_root


def test_permitted_registry_archive_is_verified_once(archived_registry_source, monkeypatch):
    monkeypatch.setattr(
        "demeter.data.packages.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=b"data/sources/toy/source.csv\0"),
    )
    result = verify_packages(archived_registry_source, check_tracked=True)
    assert result["passed"]
    assert len(result["sources"]) == 1
    assert result["sources"][0]["registry_source_ids"] == ["toy_publication"]


@pytest.mark.parametrize(
    "changes",
    [{"archive_path": None}, {"distribution": "fetch_only"}],
)
def test_archive_declaration_must_be_explicit(archived_registry_source, changes):
    edit(
        archived_registry_source,
        "data/rights.json",
        lambda d: d["clinical_sources"]["toy_publication"].update(changes),
    )
    with pytest.raises(ValueError, match="archive path"):
        verify_packages(archived_registry_source)


@pytest.mark.parametrize(
    "field,value",
    [
        ("archive_path", "data/sources/toy/other.csv"),
        ("sha256", "0" * 64),
        ("url", "https://example.org/other"),
    ],
)
def test_registry_archive_identity_cannot_drift(archived_registry_source, field, value):
    edit(
        archived_registry_source,
        "data/rights.json",
        lambda d: d["clinical_sources"]["toy_publication"].update({field: value}),
    )
    assert not verify_packages(archived_registry_source)["passed"]


def test_archive_bytes_are_not_permission_for_another_path(archived_registry_source, monkeypatch):
    root = archived_registry_source
    (root / "unreviewed.xml").write_bytes((root / "data/sources/toy/source.csv").read_bytes())
    monkeypatch.setattr(
        "demeter.data.packages.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=b"unreviewed.xml\0"),
    )
    assert failed(verify_packages(root, check_tracked=True), "tracked_data_allowlist")


@pytest.fixture
def documentation_root(package_root):
    """Synthetic fetch-only document, independent rights and receipt inventory."""
    content = b"Synthetic document bytes, not a clinical source.\n"
    raw = package_root / "local-documents"
    raw.mkdir()
    (raw / "document.html").write_bytes(content)
    receipt = dict(
        cache_filename="document.html",
        distribution="fetch_only",
        registry_source_id=None,
        url="https://example.org/document",
        final_url="https://example.org/document",
        retrieved_utc="2026-09-30T00:00:00+00:00",
        size_bytes=len(content),
        sha256=digest(content),
        status=200,
        content_type="text/html",
    )
    # Top-level scope declarations are copied, never source records or effects.
    coverage = json.loads(Path("docs/validation/dpp-coverage-source-receipts.json").read_bytes())
    coverage["sources"] = {"toy_document": receipt}
    filename = "docs/validation/documentation-receipts.json"
    save(package_root / filename, coverage)
    rights = dict(
        policy="toy",
        privacy="publication",
        publisher="Synthetic fixture",
        vintage="Synthetic fixture",
        citation="Synthetic fixture",
        notes="No scientific or legal assertion",
        alternative="Synthetic fixture only",
        retrieved_at=receipt["retrieved_utc"],
        **{k: v for k, v in receipt.items() if k != "retrieved_utc"},
    )
    edit(
        package_root,
        "data/rights.json",
        lambda d: d.update(
            documentation_receipts=filename, documentation_sources={"toy_document": rights}
        ),
    )
    edit(
        package_root,
        "data/evidence-packages.json",
        lambda d: d["supporting_artifacts"].append(
            dict(path=filename, sha256=digest((package_root / filename).read_bytes()))
        ),
    )
    return package_root, raw, filename


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://example.org/wrong"),
        ("sha256", "0" * 64),
        ("retrieved_utc", "2026-09-29T00:00:00+00:00"),
        ("size_bytes", 999),
    ],
)
def test_document_receipt_tampering_fails_even_after_outer_hash_refresh(
    documentation_root, field, value
):
    root, _, filename = documentation_root
    edit(root, filename, lambda d: d["sources"]["toy_document"].update({field: value}))
    edit(
        root,
        "data/evidence-packages.json",
        lambda d: d["supporting_artifacts"][0].update(
            sha256=digest((root / filename).read_bytes())
        ),
    )
    report = verify_packages(root)
    assert not report["passed"]
    assert not report["documentation"]["metadata_passed"]
    assert not failed(report, "artifact_checksum")


def test_documentation_cli_raw_failure_is_saved_before_exit(documentation_root, tmp_path):
    root, raw, _ = documentation_root
    output = tmp_path / "documentation-audit.json"
    args = [
        "data",
        "verify-packages",
        "--root",
        str(root),
        "--documentation-raw",
        str(raw),
        "--output",
        str(output),
    ]
    assert CliRunner().invoke(app, args).exit_code == 0
    assert json.loads(output.read_bytes())["documentation"]["raw_bytes_passed"] is True
    (raw / "document.html").write_bytes(b"Changed synthetic bytes")
    assert CliRunner().invoke(app, args).exit_code == 1
    report = json.loads(output.read_bytes())
    assert not report["passed"]
    assert report["documentation"]["raw_bytes_passed"] is False


@pytest.mark.parametrize("operation", ["resolve", "is_file"])
def test_document_metadata_permission_failure_is_saved_by_cli(
    documentation_root, tmp_path, monkeypatch, operation
):
    root, raw, _ = documentation_root
    target = raw / "document.html"
    original = getattr(Path, operation)

    def denied_for_raw_document(path, *args, **kwargs):
        if path == target:
            raise PermissionError("Synthetic document metadata permission error")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, operation, denied_for_raw_document)
    output = tmp_path / "permission-failure.json"
    args = [
        "data",
        "verify-packages",
        "--root",
        str(root),
        "--documentation-raw",
        str(raw),
        "--output",
        str(output),
    ]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    report = json.loads(output.read_bytes())
    assert not report["passed"]
    row = report["documentation"]["source_checks"][0]
    assert row["local_byte_check"] == "failed"
    assert row["raw_error"] == "unreadable"


def test_documentation_fetch_only_guard_rejects_renamed_bytes(documentation_root, monkeypatch):
    root, raw, _ = documentation_root
    target = root / "notes.md"
    target.write_bytes((raw / "document.html").read_bytes())
    monkeypatch.setattr(
        "demeter.data.packages.subprocess.run",
        lambda *a, **k: SimpleNamespace(stdout=b"notes.md\0"),
    )
    assert failed(verify_packages(root, check_tracked=True), "fetch_only_not_tracked")


@pytest.mark.parametrize("link", [None, "unknown_registry_source"])
def test_known_document_cannot_drop_or_change_registry_link(documentation_root, link):
    root, _, filename = documentation_root
    receipt = json.loads((root / filename).read_bytes())["sources"]["toy_document"]
    registry_path = root / "evidence/parameters.yaml"
    registry = yaml.safe_load(registry_path.read_text())
    registry["sources"] = {
        "registered_document": dict(
            url=receipt["url"],
            citation="Synthetic source",
            doi="test",
            raw_filename=receipt["cache_filename"],
            sha256=receipt["sha256"],
            retrieved_at=receipt["retrieved_utc"],
            license="Synthetic fetch-only fixture",
        )
    }
    registry_path.write_text(yaml.safe_dump(registry))
    edit(
        root,
        filename,
        lambda d: d["sources"]["toy_document"].update(registry_source_id=link),
    )
    edit(
        root,
        "data/rights.json",
        lambda d: d["documentation_sources"]["toy_document"].update(registry_source_id=link),
    )
    edit(
        root,
        "data/evidence-packages.json",
        lambda d: d["supporting_artifacts"][0].update(
            sha256=digest((root / filename).read_bytes())
        ),
    )
    assert failed(verify_packages(root), "documentation_registry_link")
