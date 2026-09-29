import json
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
    report = verify_packages()
    assert report["passed"], [c for c in report["checks"] if not c["passed"]]
    assert len(report["sources"]) == 49
    assert len(report["artifacts"]) == 30
    assert len(report["packages"]) == 15
    assert not report["network_used"]
    assert {s["distribution"] for s in report["sources"]} == {"archived", "fetch_only"}


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
