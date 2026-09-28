import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.historical import rebuild_history
from demeter.data.ingest import BUNDLE, digest, rebuild
from demeter.data.store import verify_store


def test_all_catalogued_sources_reload_offline(monkeypatch):
    def no_network(*a, **kw):
        raise AssertionError("Source verification must not download")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    report = verify_store()
    assert report["passed"]
    assert report["files"] == 36
    assert not report["network_used"]


def test_missing_and_changed_source_files_fail_cli(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {"schema_version": 1, "stores": [{"id": "synthetic", "manifest": "manifest.json"}]}
        )
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": {"source.json": {"sha256": digest(b"{}")}}}))
    missing = verify_store(catalog)
    assert not missing["passed"]
    assert missing["checks"][0]["reason"] == "missing_file"
    (tmp_path / "source.json").write_bytes(b"[]")
    result = CliRunner().invoke(app, ["data", "verify-store", "--catalog", str(catalog)])
    assert result.exit_code == 1
    assert json.loads(result.output)["checks"][0]["reason"] == "checksum_mismatch"


def test_existing_model_datasets_rebuild_from_store_without_network(tmp_path, monkeypatch):
    def no_network(*a, **kw):
        raise AssertionError("A complete source store must rebuild offline")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    for manifest in ("manifest.json", "historical_manifest.json"):
        shutil.copyfile(BUNDLE / manifest, tmp_path / manifest)
    rebuild(Path("data/sources/baseline/2026-09-26"), tmp_path)
    rebuild_history(Path("data/sources/historical/2026-09-26"), tmp_path)
    for bundle in ("us_baseline.json", "historical.json"):
        assert (tmp_path / bundle).read_bytes() == (BUNDLE / bundle).read_bytes()
