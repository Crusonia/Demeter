from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from demeter.analysis import kerala_coverage as coverage
from demeter.analysis.kerala_registration import DATASET, verify_registered
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
REPORT = "docs/validation/kerala-selected-source-representation-v1.json"


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf8")


def _repin_report(registry, root):
    registry.datasets[DATASET]["representation_sha256"] = coverage._digest(root / REPORT)


@pytest.fixture
def registered_package(tmp_path):
    root = tmp_path / "package"
    validation = root / "docs/validation"
    validation.mkdir(parents=True)
    for path in (ROOT / "docs/validation").glob("kerala-*.json"):
        shutil.copy2(path, validation / path.name)
    report = json.loads((root / REPORT).read_bytes())
    for pin in report["execution_code_pins"].values():
        destination = root / pin["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / pin["path"], destination)
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    # The fixture can exercise the wrapper while integration updates the registry.
    registry.datasets[DATASET].update(
        representation_path=REPORT,
        representation_sha256=coverage._digest(root / REPORT),
    )
    return registry, root


def test_actual_registered_source_is_offline_and_requires_no_author_git(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline registration must not inspect author Git history")

    monkeypatch.setattr(subprocess, "check_output", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    result = verify_registered(EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml"), ROOT)
    assert result["registered_artifacts_verified"] is True
    assert result["public_workbook_headers_reproduced"] is None
    assert result["registered_aggregate_reproduction"] is None
    assert result["historical_redirect_projection_reproduced"] is None
    assert all(value is False for value in result["scientific_gates"].values())


def test_frozen_registration_can_verify_outside_git(registered_package):
    registry, root = registered_package
    assert not (root / ".git").exists()
    assert verify_registered(registry, root)["registered_artifacts_verified"] is True


def test_pinned_report_byte_drift_fails(registered_package):
    registry, root = registered_package
    with (root / REPORT).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="representation checksum"):
        verify_registered(registry, root)


@pytest.mark.parametrize("location", ["dataset", "report"])
@pytest.mark.parametrize("gate", sorted(coverage.GATES))
def test_every_scientific_gate_remains_false(registered_package, location, gate):
    registry, root = registered_package
    if location == "dataset":
        registry.datasets[DATASET][gate] = True
    else:
        report = json.loads((root / REPORT).read_bytes())
        report["scientific_gates"][gate] = True
        _write(root / REPORT, report)
        _repin_report(registry, root)
    with pytest.raises(ValueError, match="scientific gates"):
        verify_registered(registry, root)


@pytest.mark.parametrize("field", ["url", "doi", "raw_filename", "sha256", "retrieved_at"])
def test_typed_registry_source_receipt_drift_fails(registered_package, field):
    registry, root = registered_package
    source_id = registry.datasets[DATASET]["source_id"]
    source = registry.sources[source_id]
    replacement = "incorrect"
    if field == "retrieved_at":
        replacement = coverage._time("2000-01-01T00:00:00+00:00")
    registry.sources[source_id] = source.model_copy(update={field: replacement})
    with pytest.raises(ValueError, match="registered source"):
        verify_registered(registry, root)


@pytest.mark.parametrize("label", ["module", "script"])
def test_execution_code_drift_fails(registered_package, label):
    registry, root = registered_package
    report = json.loads((root / REPORT).read_bytes())
    with (root / report["execution_code_pins"][label]["path"]).open("ab") as stream:
        stream.write(b"\n# changed replay implementation\n")
    with pytest.raises(ValueError, match="code|checksum"):
        verify_registered(registry, root)


@pytest.mark.parametrize(
    "flag", ["participant_records_exported", "raw_numeric_code_meanings_inferred"]
)
def test_repinning_cannot_promote_report_semantics(registered_package, flag):
    registry, root = registered_package
    report = json.loads((root / REPORT).read_bytes())
    report[flag] = True
    _write(root / REPORT, report)
    _repin_report(registry, root)
    with pytest.raises(ValueError, match="scientific boundary"):
        verify_registered(registry, root)


def test_replay_requires_source_cache(registered_package):
    registry, root = registered_package
    with pytest.raises(ValueError, match="requires exact public source cache"):
        verify_registered(registry, root, replay_aggregates=True)


@pytest.mark.parametrize("mismatch", [False, True])
def test_persisted_cardinality_keys_replay_without_private_records(
    registered_package, tmp_path, monkeypatch, mismatch
):
    registry, root = registered_package
    cache = tmp_path / "synthetic-cache"
    cache.mkdir()
    receipt_path = root / "docs/validation/kerala-source-acquisition-receipts-v1.json"
    receipts = json.loads(receipt_path.read_bytes())
    report = json.loads((root / REPORT).read_bytes())
    for receipt in receipts["workbook_receipts"]:
        raw = cache / receipt["raw_filename"]
        raw.write_bytes(b"synthetic workbook bytes; no participant records")
        receipt.update(
            bytes=raw.stat().st_size,
            sha256=coverage._digest(raw),
            md5=hashlib.md5(raw.read_bytes()).hexdigest(),
        )
    _write(receipt_path, receipts)
    report["source_files"] = [
        {key: receipt[key] for key in ("file_id", "raw_filename", "bytes", "sha256", "md5")}
        for receipt in receipts["workbook_receipts"]
    ]
    _write(root / REPORT, report)
    _repin_report(registry, root)
    headers = json.loads((root / "docs/validation/kerala-source-headers-v1.json").read_bytes())
    expected_headers = {
        receipt["raw_filename"]: header["headers"]
        for receipt, header in zip(receipts["workbook_receipts"], headers, strict=True)
    }
    # Isolate wire-format replay from the independently tested admission/header decoder.
    monkeypatch.setattr(coverage, "verify_admission", lambda *args: {"synthetic_guard": True})
    monkeypatch.setattr(coverage, "read_headers_only", lambda path: expected_headers[path.name])
    monkeypatch.setattr(coverage, "_selected_rows", lambda *args: [])
    actual = copy.deepcopy(report["aggregate_representation"])
    for book in ("primary", "secondary"):
        name = "distinct_timepoint_cardinality_per_key"
        actual[book][name] = {int(key): count for key, count in actual[book][name].items()}
    if mismatch:
        actual["secondary"]["distinct_timepoint_cardinality_per_key"][3] -= 1
    monkeypatch.setattr(coverage, "aggregate_representation", lambda *args: actual)
    if mismatch:
        with pytest.raises(ValueError, match="aggregate replay mismatch"):
            verify_registered(registry, root, cache, replay_aggregates=True)
    else:
        result = verify_registered(registry, root, cache, replay_aggregates=True)
        assert result["registered_aggregate_reproduction"] is True
        assert result["public_workbook_headers_reproduced"] is True
        assert result["historical_redirect_projection_reproduced"] is None
        assert result["participant_records_exported"] is False


def test_cli_refuses_to_overwrite_existing_receipt(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "kerala_registered_cli", ROOT / "scripts/verify_kerala_registered_coverage.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    output = tmp_path / "receipt.json"
    output.write_bytes(b"immutable existing receipt\n")
    monkeypatch.setattr(sys, "argv", [str(spec.origin), "--output", str(output)])
    monkeypatch.setattr(
        cli, "verify_registered", lambda *args, **kwargs: pytest.fail("should stop before replay")
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    assert output.read_bytes() == b"immutable existing receipt\n"
