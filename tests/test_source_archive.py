"""A clone must contain enough unchanged source data to reproduce its bundles."""

import runpy
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
verify_archive = runpy.run_path(str(ROOT / "scripts/verify_source_archive.py"))["verify_archive"]


def test_committed_sources_rebuild_both_bundles_without_network(monkeypatch):
    def offline(*args, **kwargs):
        pytest.fail("Committed sources must rebuild without network access")

    monkeypatch.setattr("urllib.request.urlopen", offline)
    report = verify_archive(rebuild_bundles=True)
    assert report["passed"]
    assert set(report["rebuilt_bundles"]) == {"us_baseline.json", "historical.json"}


def test_changed_raw_bytes_fail_before_rebuild(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "data/sources", tmp_path / "data/sources")
    shutil.copytree(ROOT / "src/demeter/data/bundled", tmp_path / "src/demeter/data/bundled")
    path = tmp_path / "data/sources/baseline/2026-09-26/census_2025.csv"
    path.write_bytes(path.read_bytes() + b"\n")

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid source bytes reached a rebuild")

    monkeypatch.setitem(
        verify_archive.__globals__,
        "GROUPS",
        (("baseline", "manifest.json", "us_baseline.json", unexpected),),
    )
    with pytest.raises(ValueError, match="Source checksum mismatch"):
        verify_archive(tmp_path, rebuild_bundles=True)
