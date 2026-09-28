import json
from pathlib import Path
import shutil
import stat
import zipfile

import pytest
from pydantic import ValidationError

from demeter import releases
from demeter.data.ingest import digest


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    destination = tmp_path_factory.mktemp("release") / "bundle"
    releases.build(destination, releases.RunSettings(draws=2, samples=8, seed=42), allow_dirty=True)
    return destination


@pytest.fixture
def copied(bundle, tmp_path):
    return Path(shutil.copytree(bundle, tmp_path / "bundle"))


def reseal(bundle, change):
    data = json.loads((bundle / "manifest.json").read_bytes())
    change(data)
    encoded = releases.canonical(data)
    (bundle / "manifest.json").write_bytes(encoded)
    (bundle / "manifest.sha256").write_text(digest(encoded), encoding="ascii")


def test_complete_bundle_and_scientific_boundary(bundle):
    assert releases.verify(bundle)["passed"]
    data = releases.ReleaseManifest.model_validate_json((bundle / "manifest.json").read_bytes())
    assert data.settings == releases.RunSettings(draws=2, samples=8, seed=42)
    assert data.scientific_release_ready is False
    assert data.calibration["clinical"]["windows"] == []
    assert data.data["source_manifests"]
    assert data.evidence["audit"]["synthetic"]
    assert "uv.lock" in data.source_files
    assert "baseline_mortality" not in data.calibration["clinical"]["fitted_parameters"]
    assert "VALIDATION ONLY" in (bundle / "MODEL_CARD.md").read_text(encoding="utf-8")
    baseline = json.loads((bundle / "results/baseline.json").read_bytes())
    assert len(baseline["cohorts"]) == 101
    assert baseline["ending_population"] + baseline["cumulative_deaths"] == pytest.approx(
        baseline["starting_population"]
    )
    assert baseline["metadata"]["evidence_sha256"] == data.evidence["content_sha256"]


@pytest.mark.parametrize("change", ["modified", "missing", "extra", "manifest"])
def test_artifact_tampering_fails(copied, change):
    target = copied / "results/baseline.json"
    if change == "modified":
        target.write_text("{}")
    elif change == "missing":
        target.unlink()
    elif change == "extra":
        (copied / "extra.txt").write_text("extra")
    else:
        (copied / "manifest.json").write_text("{}")
    with pytest.raises(ValueError):
        releases.verify(copied)


@pytest.mark.parametrize(
    "path",
    ["../outside", "/absolute", "C:/drive", "a\\b", "a/../b", "a//b", "NUL.txt", "a.", "a\nb"],
)
def test_nonportable_paths_fail(path):
    with pytest.raises(ValueError, match="Unsafe archive path"):
        releases.safe_name(path)


@pytest.mark.parametrize("change", ["extra", "symlink", "content"])
def test_zip_tampering_rejected_even_with_updated_outer_checksum(copied, change):
    archive_path = copied / "source.zip"
    with zipfile.ZipFile(archive_path) as archive:
        rows = [(entry, archive.read(entry)) for entry in archive.infolist()]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry, content in rows:
            if entry.filename == "README.md":
                if change == "content":
                    content = b"altered source"
                elif change == "symlink":
                    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(entry, content)
        if change == "extra":
            archive.writestr("../outside", "not extracted")
    reseal(
        copied,
        lambda data: data["artifacts"].update(
            {"source.zip": releases.receipt(archive_path.read_bytes()).model_dump()}
        ),
    )
    with pytest.raises(ValueError):
        releases.verify(copied)


def test_extract_never_overwrites_and_preserves_bytes(bundle, tmp_path):
    target = tmp_path / "source"
    result = releases.extract(bundle, target)
    assert result["code_executed"] is False
    manifest = releases.ReleaseManifest.model_validate_json((bundle / "manifest.json").read_bytes())
    for name, expected in manifest.source_files.items():
        assert releases.receipt((target / name).read_bytes()) == expected
    with pytest.raises(ValueError, match="must not exist"):
        releases.extract(bundle, target)
    with pytest.raises(ValueError, match="already exists"):
        releases.build(bundle, releases.RunSettings())
    with pytest.raises(ValueError, match="outside the immutable bundle"):
        releases.extract(bundle, bundle / "source")


def test_dirty_checkout_requires_explicit_development_mode(monkeypatch, tmp_path):
    original = releases.git
    monkeypatch.setattr(
        releases,
        "git",
        lambda root, *args: (
            " M src/demeter/model.py" if args[0] == "status" else original(root, *args)
        ),
    )
    with pytest.raises(ValueError, match="clean checkout"):
        releases.build(tmp_path / "release", releases.RunSettings(draws=2, samples=8))


def test_release_schema_cannot_claim_scientific_acceptance(copied):
    reseal(copied, lambda data: data.update(scientific_release_ready=True))
    with pytest.raises(ValidationError):
        releases.verify(copied)


@pytest.mark.parametrize("field", ["evidence", "settings", "profile"])
def test_resealed_metadata_must_match_actual_source_and_diagnostics(copied, field):
    def change(data):
        if field == "evidence":
            data[field]["content_sha256"] = "0" * 64
        elif field == "settings":
            data[field]["seed"] += 1
        else:
            data[field]["model_structure_version"] = "pretend-structure"

    reseal(copied, change)
    with pytest.raises(ValueError):
        releases.verify(copied)


def test_replay_rejects_altered_results_even_when_resealed(copied, monkeypatch):
    # A checksum is not a correctness certificate: recomputation must detect this.
    target = copied / "results/baseline.json"
    changed = json.loads(target.read_bytes())
    changed["cumulative_deaths"] += 10
    target.write_bytes(releases.canonical(changed))
    reseal(
        copied,
        lambda data: data["artifacts"].update(
            {"results/baseline.json": releases.receipt(target.read_bytes()).model_dump()}
        ),
    )
    assert releases.verify(copied)["passed"]
    report = releases.replay(copied)
    assert not report["passed"]
    assert not report["comparisons"]["baseline"]["passed"]
    assert "baseline/cumulative_deaths" in report["comparisons"]["baseline"]["first_mismatches"][0]


def test_comparison_does_not_hide_structural_or_large_numeric_changes():
    assert not releases.differences({"v": 1.0}, {"v": 1.0 + 1e-12})
    assert releases.differences({"v": 1.0}, {"v": 1.01})
    assert releases.differences({"v": 1.0}, {"v": "1.0"})
    assert releases.differences([1], [1, 2])
    assert releases.differences({"v": 1.0}, {"v": 1.0, "new": 0})


def test_source_change_cannot_be_replayed(bundle, monkeypatch, tmp_path):
    source = tmp_path / "source"
    releases.extract(bundle, source)
    (source / "evidence/parameters.yaml").write_text("parameters: {}")
    monkeypatch.setattr(releases, "source_root", lambda: source)
    with pytest.raises(ValueError, match="Replay source differs"):
        releases.replay(bundle)


def test_committed_checkpoint_receipt_matches_archived_baseline():
    archive = releases.source_root() / "releases/archives/0.1.0a1-e969c41"
    record = json.loads((archive / "receipt.json").read_bytes())
    for name, expected in record["archived_files"].items():
        assert releases.receipt((archive / name).read_bytes()).model_dump() == expected
    baseline = json.loads((archive / "baseline.json").read_bytes())
    assert baseline["metadata"]["evidence_sha256"] == record["evidence_sha256"]
    assert baseline["metadata"]["scenario"] == record["scenario"]
    assert baseline["validation_only"] and not record["scientific_release_ready"]
    assert record["working_tree_dirty"] is False
    assert record["replay"]["passed"]
    assert set(record["replay"]["comparisons"]) == set(releases.RESULT_NAMES)
