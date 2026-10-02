"""Benchmark integration guards; raw parser and bounds have separate source/math tests."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import demeter.analysis.malawi_cohort_audit as module
from demeter.cli import app
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def package(tmp_path):
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    names = [module.PROTOCOL_PATH, module.REPORT_PATH, *module.TRANSFORMS.values()]
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    return registry, tmp_path


def reseal_report(registry, root, mutation):
    path = root / module.REPORT_PATH
    content = json.loads(path.read_bytes())
    mutation(content)
    path.write_bytes(encoded(content))
    registry.datasets[module.DATASET]["report_sha256"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_offline_audit_is_explicit_and_does_not_extract_source(package, monkeypatch):
    registry, root = package
    before = registry.model_dump(mode="json")

    def forbidden(*args, **kwargs):
        pytest.fail("Offline report verification must not read a source")

    monkeypatch.setattr(module, "extract_malawi_cohort", forbidden)
    result = module.audit_malawi_cohort(registry, root)
    assert registry.model_dump(mode="json") == before
    assert result["registered_artifacts_verified"] is True
    assert result["raw_values_read"] is False
    assert result["source_aggregates_reproduced"] is None
    assert result["network_used"] is False
    assert result["scientific_release_ready"] is False
    report = result["report"]
    assert report["scientific_gates"] == module.GATES
    assert report["working_fit_performed"] is False
    assert report["sampling_interval"] is None
    assert (
        report["completion_estimand"]["untraced_people_have_observed_ascertainment_dates"] is False
    )
    counts = report["ascertainment_bounds"]["counts"]
    assert counts["n"] == counts["observed_alive"] + counts["confirmed_deaths"] + counts["untraced"]


@pytest.mark.parametrize(
    "path", [module.PROTOCOL_PATH, module.REPORT_PATH, *module.TRANSFORMS.values()]
)
def test_byte_drift_rejected_before_reproduction(package, path):
    registry, root = package
    target = root / path
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError):
        module.audit_malawi_cohort(registry, root)


@pytest.mark.parametrize(
    "field", ["value", "status", "model_role", "source_id", "unit", "evidence_grade"]
)
def test_registry_record_mismatch_is_rejected(package, field):
    registry, root = package
    parameter = registry.parameters["malawi_dm_count"]
    values = {
        "value": 46,
        "status": "estimated",
        "model_role": "health_model",
        "source_id": None,
        "unit": "annual_hazard",
        "evidence_grade": "B",
    }
    setattr(parameter, field, values[field])
    with pytest.raises(ValueError):
        module.audit_malawi_cohort(registry, root)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda report: report.update(working_fit_performed=True),
        lambda report: report["source_facts"].update(participant_records=["PRIVATE_MARKER"]),
        lambda report: report["source_facts"]["observed"].update(extra_count=1),
        lambda report: report["source_facts"]["derived"].update(untraced_count=198),
        lambda report: report["source_facts"]["scientific_gates"].update(clinical_fit_allowed=0),
        lambda report: report["source_facts"]["source_discrepancies"]["person_years"].update(
            results=714.0
        ),
        lambda report: report["source_facts"]["source_locators"].update(dm_count="PRIVATE_MARKER"),
        lambda report: report["ascertainment_bounds"]["counts"].update(untraced=0),
        lambda report: report.update(private_unselected_text="PRIVATE_MARKER"),
    ],
)
def test_resealed_report_cannot_expand_scope_or_repair_unknowns(package, mutation):
    registry, root = package
    reseal_report(registry, root, mutation)
    with pytest.raises((ValueError, KeyError, TypeError)) as error:
        module.audit_malawi_cohort(registry, root)
    assert "PRIVATE_MARKER" not in str(error.value)


def test_raw_dispatch_checks_extracted_report_not_only_bytes(package, tmp_path, monkeypatch):
    """Synthetic dispatch witness; actual pinned XML reproduction is a separate receipt."""
    registry, root = package
    raw = tmp_path / "synthetic.xml"
    raw.write_bytes(b"SYNTHETIC_XML")
    facts = json.loads((root / module.REPORT_PATH).read_bytes())["source_facts"]
    calls = []

    def extractor(content, protocol):
        calls.append((content, protocol["protocol_id"]))
        return deepcopy(facts)

    monkeypatch.setattr(module, "extract_malawi_cohort", extractor)
    result = module.audit_malawi_cohort(registry, root, raw=raw)
    assert calls == [(b"SYNTHETIC_XML", "malawi-public-cohort-intake-v1")]
    assert result["raw_values_read"] is True
    assert result["source_aggregates_reproduced"] is True
    facts["observed"]["dm_count"] += 1
    with pytest.raises(ValueError):
        module.audit_malawi_cohort(registry, root, raw=raw)


def test_cli_exports_offline_json_without_overwriting_sources(tmp_path):
    output = tmp_path / "report.json"
    runner = CliRunner()
    result = runner.invoke(
        app, ["evidence", "malawi-cohort", "--project", str(ROOT), "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_bytes())["source_aggregates_reproduced"] is None
    before = output.read_bytes()
    again = runner.invoke(app, ["evidence", "malawi-cohort", "--output", str(output)])
    assert again.exit_code == 1
    assert output.read_bytes() == before


@pytest.mark.parametrize("folder", ["src", "docs", "data", "evidence"])
def test_cli_cannot_create_outputs_in_source_folders(package, folder):
    registry, root = package
    evidence = root / "registry.yaml"
    evidence.write_text(
        "not needed because destination validation precedes registry", encoding="utf-8"
    )
    output = root / folder / "new.json"
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "malawi-cohort",
            "--project",
            str(root),
            "--evidence",
            str(evidence),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 1
    assert not output.exists()


def test_cli_bad_raw_has_sanitized_failure_and_no_output(tmp_path):
    raw = tmp_path / "bad.xml"
    raw.write_bytes(b"PRIVATE_MARKER")
    output = tmp_path / "failure.json"
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "malawi-cohort",
            "--project",
            str(ROOT),
            "--raw",
            str(raw),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 1
    assert "PRIVATE_MARKER" not in result.output
    assert not output.exists()


def test_cli_protects_raw_input_destination(tmp_path):
    raw = tmp_path / "source.xml"
    raw.write_bytes(b"SYNTHETIC")
    result = CliRunner().invoke(
        app, ["evidence", "malawi-cohort", "--raw", str(raw), "--output", str(raw)]
    )
    assert result.exit_code == 1
    assert raw.read_bytes() == b"SYNTHETIC"
