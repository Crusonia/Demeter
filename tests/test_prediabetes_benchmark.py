"""Reproduce a published benchmark without making it an engine input."""

import hashlib
import json
import errno
from pathlib import Path
import runpy
import shutil

import pytest
import yaml

from demeter.schema import EvidenceRegistry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = runpy.run_path(str(ROOT / "scripts/verify_prediabetes_benchmark.py"))
extract_interval = SCRIPT["extract_interval"]
verify_benchmark = SCRIPT["verify_benchmark"]
write_report = SCRIPT["write_report"]
STORE = SCRIPT["STORE"]
KEY = SCRIPT["KEY"]

# Entirely synthetic table: the awareness column deliberately differs from
# prediabetes. These values are parser fixtures, not clinical evidence.
SYNTHETIC_TABLE = """
Estimated Crude Percentage of Prediabetes and Awareness
Adults Aged 18 Years or Older, United States, 2021–2023
Percentage (95% CI)
Age Group
Prediabetes Awareness
18–44 7.6 (4.2–11.0) 91.7 (89.1–94.3)
≥65 13.4 (10.1–16.7) 81.2 (78.0–84.4)
"""


@pytest.fixture
def benchmark_root(tmp_path):
    """Copy the three verification inputs, retaining the real source bytes."""
    registry_path = tmp_path / "evidence/parameters.yaml"
    registry_path.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "evidence/parameters.yaml", registry_path)
    manifest_path = ROOT / STORE / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    destination = tmp_path / STORE
    destination.mkdir(parents=True)
    shutil.copyfile(manifest_path, destination / "manifest.json")
    filename = manifest["extraction"]["filename"]
    shutil.copyfile(ROOT / STORE / filename, destination / filename)
    return tmp_path


def test_archived_pdf_matches_registered_interval_and_retains_benchmark_scope(monkeypatch):
    def unexpected_network(*args, **kwargs):
        pytest.fail("Archived benchmark verification attempted network access")

    monkeypatch.setattr("urllib.request.urlopen", unexpected_network)
    report = verify_benchmark(ROOT)
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    parameter = registry.parameters[KEY]
    manifest = json.loads((ROOT / STORE / "manifest.json").read_bytes())
    filename = manifest["extraction"]["filename"]
    source = manifest["sources"][filename]
    raw = (ROOT / STORE / filename).read_bytes()

    assert report["passed"] is True
    assert report["network_used"] is False
    assert report["scientific_release_ready"] is False
    assert report["registry_key"] == KEY
    assert report["model_role"] == parameter.model_role == "benchmark_only"
    assert parameter.status == "observed"
    assert parameter.unit == "fraction"
    assert parameter.uncertainty.kind == "interval"
    assert report["value"] == parameter.value
    assert report["uncertainty"] == {
        "kind": "interval",
        "low": parameter.uncertainty.low,
        "high": parameter.uncertainty.high,
    }
    assert parameter.uncertainty.low <= parameter.value <= parameter.uncertainty.high
    assert KEY not in registry.audit()["missing_uncertainty"]
    assert report["evidence_sha256"] == registry.content_hash
    assert report["source"] == source
    assert report["source_locator"] == manifest["extraction"]["locator"]
    assert len(raw) == source["bytes"]
    assert hashlib.sha256(raw).hexdigest() == source["sha256"]


@pytest.mark.parametrize("separator", ["–", "-"])
def test_synthetic_extractor_selects_prediabetes_column_not_awareness(separator):
    selected = extract_interval(
        SYNTHETIC_TABLE.replace("–", separator).replace("2021-2023", "2021–2023")
    )
    assert selected == (0.134, 0.101, 0.167)
    assert selected != (0.812, 0.780, 0.844)


def test_synthetic_extractor_rejects_missing_crude_heading():
    table = SYNTHETIC_TABLE.replace(
        "Estimated Crude Percentage of Prediabetes and Awareness",
        "Estimated Age-adjusted Percentage of Prediabetes and Awareness",
    )
    with pytest.raises(ValueError, match="crude prediabetes table heading missing"):
        extract_interval(table)


def test_synthetic_extractor_rejects_duplicate_older_age_rows():
    table = SYNTHETIC_TABLE + "≥65 14.5 (11.2–17.8) 82.3 (79.1–85.5)\n"
    with pytest.raises(ValueError, match="exactly one CDC ≥65 row"):
        extract_interval(table)


@pytest.mark.parametrize("tamper", ["low", "high", "sampling_kind", "active_role"])
def test_changed_registered_interval_or_role_fails_against_unchanged_source(benchmark_root, tamper):
    # Prove the minimal copy is usable before mutation, so rejection cannot be
    # explained by a missing source, receipt, or unrelated registry contract.
    assert verify_benchmark(benchmark_root)["passed"] is True
    registry_path = benchmark_root / "evidence/parameters.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    parameter = registry["parameters"][KEY]
    if tamper == "low":
        parameter["uncertainty"]["low"] += 0.001
    elif tamper == "high":
        parameter["uncertainty"]["high"] -= 0.001
    elif tamper == "sampling_kind":
        parameter["uncertainty"]["kind"] = "uniform"
    else:
        parameter["model_role"] = "health_model"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="published interval does not match"):
        verify_benchmark(benchmark_root)


def test_changed_pdf_bytes_fail_before_pdf_interpretation(benchmark_root):
    assert verify_benchmark(benchmark_root)["passed"] is True
    manifest = json.loads((benchmark_root / STORE / "manifest.json").read_bytes())
    path = benchmark_root / STORE / manifest["extraction"]["filename"]
    path.write_bytes(path.read_bytes() + b"\nsynthetic source mutation\n")

    with pytest.raises(ValueError, match="source bytes differ from the pinned receipt"):
        verify_benchmark(benchmark_root)


@pytest.mark.parametrize("tamper", ["schema", "registry_key", "receipt_role"])
def test_changed_manifest_identity_cannot_promote_or_relabel_benchmark(benchmark_root, tamper):
    assert verify_benchmark(benchmark_root)["passed"] is True
    manifest_path = benchmark_root / STORE / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if tamper == "schema":
        manifest["schema_version"] = 2
    elif tamper == "registry_key":
        manifest["extraction"]["registry_key"] = "synthetic_unrelated_benchmark"
    else:
        filename = manifest["extraction"]["filename"]
        manifest["sources"][filename]["model_role"] = "health_model"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest identity or role"):
        verify_benchmark(benchmark_root)


def test_new_report_destination_receives_complete_json(tmp_path):
    report = {
        "passed": True,
        "scientific_release_ready": False,
        "scope": "synthetic report-writing fixture",
        "synthetic_unicode": "≥65",
    }
    output = tmp_path / "new-results" / "benchmark.json"

    write_report(report, output)

    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert output.read_bytes().endswith(b"\n")


def test_existing_synthetic_file_is_not_overwritten(tmp_path):
    output = tmp_path / "existing.json"
    original = b'{"synthetic": "preserve existing bytes"}\n'
    output.write_bytes(original)

    with pytest.raises(ValueError, match="Output must be a new file"):
        write_report({"synthetic": "replacement"}, output)

    assert output.read_bytes() == original


def test_hardlink_alias_cannot_overwrite_synthetic_source(tmp_path):
    source = tmp_path / "synthetic-source.pdf"
    original = b"%PDF-1.7\nsynthetic immutable source bytes\n"
    source.write_bytes(original)
    output = tmp_path / "hardlink-output.json"
    output.hardlink_to(source)

    with pytest.raises(ValueError, match="Output must be a new file"):
        write_report({"synthetic": "replacement"}, output)

    assert output.samefile(source)
    assert source.read_bytes() == output.read_bytes() == original


def test_symlink_alias_cannot_overwrite_synthetic_source_when_permitted(tmp_path):
    source = tmp_path / "synthetic-source.pdf"
    original = b"%PDF-1.7\nsynthetic immutable source bytes\n"
    source.write_bytes(original)
    output = tmp_path / "symlink-output.json"
    try:
        output.symlink_to(source)
    except OSError as exc:
        if (
            isinstance(exc, PermissionError)
            or exc.errno in (errno.EACCES, errno.EPERM)
            or getattr(exc, "winerror", None) == 1314
        ):
            pytest.skip("Host permissions do not allow creating a file symlink")
        raise

    with pytest.raises(ValueError, match="Output must be a new file"):
        write_report({"synthetic": "replacement"}, output)

    assert output.is_symlink()
    assert output.samefile(source)
    assert source.read_bytes() == output.read_bytes() == original
