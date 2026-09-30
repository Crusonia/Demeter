"""Frozen-contract and CLI checks use synthetic data, never DPP participant records."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.analysis.dpp_observations import DATASET, WITNESS, audit_dpp_observations
from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry


def registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def test_offline_contract_and_witness_do_not_claim_source_bytes_or_clinical_fit(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline DPP audit must not use network")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    report = audit_dpp_observations(registry())
    assert report["results"] == {
        "software_witnesses_passed": True,
        "documentation_bytes_checked": False,
        "documentation_bytes_passed": None,
    }
    assert all(report["software_witness"]["checks"].values())
    assert {row["local_byte_check"] for row in report["documentation"]["source_checks"]} == {
        "not_requested"
    }
    assert report["participant_records_acquired"] is False
    assert report["clinical_fitting_allowed"] is False
    assert report["direct_initialization_allowed"] is False
    assert report["scientific_release_ready"] is False
    assert report["software_witness"]["evidence_grade"] == "E"
    assert "synthetic-confirmed" not in json.dumps(report)
    assert "record_id" not in json.dumps(report)
    assert report["documentation"]["field_contract"]["DIABT"]["year_denominator"] is None
    assert report["documentation"]["field_contract"]["DIABV"]["interval_bounds"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.datasets[DATASET].update(clinical_fitting_allowed=True),
        lambda r: r.datasets[DATASET].update(direct_initialization_allowed=True),
        lambda r: r.datasets[DATASET].update(model_role="health_model"),
        lambda r: r.datasets[DATASET]["field_contract"]["DIABT"].update(year_denominator=365),
        lambda r: r.datasets[DATASET]["source_context"].update(original_report_cutoff="2001-07-31"),
        lambda r: r.datasets[WITNESS]["input"].update(synthetic=False),
        lambda r: r.datasets[WITNESS]["input"]["participants"][1]["events"].update(
            death_status=False
        ),
        lambda r: r.sources["dpp_catalog_v9"].__setattr__("sha256", "0" * 64),
        lambda r: r.sources.pop("dpp_protocol_4_5"),
    ],
)
def test_changed_contract_or_synthetic_definition_is_rejected_before_adapter(mutate, monkeypatch):
    r = registry()
    mutate(r)

    def forbidden(*args, **kwargs):
        pytest.fail("Changed contract must be rejected before observation processing")

    monkeypatch.setattr("demeter.analysis.dpp_observations.preserve_observations", forbidden)
    with pytest.raises(ValueError, match="DPP"):
        audit_dpp_observations(r)


def test_changed_protocol_bytes_rejected_before_processing(tmp_path):
    r = registry()
    spec = r.datasets[DATASET]
    path = tmp_path / "changed.json"
    path.write_bytes(Path(spec["protocol_path"]).read_bytes() + b" ")
    spec["protocol_path"] = str(path)
    with pytest.raises(ValueError, match="checksum"):
        audit_dpp_observations(r)


def synthetic_documentation_fixture(tmp_path):
    r = registry()
    protocol = json.loads(Path(r.datasets[DATASET]["protocol_path"]).read_bytes())
    raw = tmp_path / "raw"
    raw.mkdir()
    for source_id, pin in protocol["source_pins"].items():
        content = f"Synthetic documentation bytes: {source_id}\n".encode()
        (raw / pin["raw_filename"]).write_bytes(content)
        pin["sha256"] = digest(content)
        r.sources[source_id].sha256 = pin["sha256"]
    path = tmp_path / "synthetic-documentation-contract.json"
    path.write_bytes(encoded(protocol))
    for key in (DATASET, WITNESS):
        r.datasets[key].update(protocol_path=str(path), protocol_sha256=digest(path.read_bytes()))
    r.datasets[DATASET]["source_pins"] = protocol["source_pins"]
    return r, raw


def test_optional_source_bytes_require_all_four_distinct_documents(tmp_path):
    r, raw = synthetic_documentation_fixture(tmp_path)
    report = audit_dpp_observations(r, raw)
    assert report["results"]["documentation_bytes_passed"] is True
    (raw / r.sources["dpp2002_primary"].raw_filename).write_bytes(b"Changed primary report")
    report = audit_dpp_observations(r, raw)
    assert report["results"]["documentation_bytes_passed"] is False
    checks = {row["source_id"]: row for row in report["documentation"]["source_checks"]}
    assert checks["dpp2002_primary"]["local_byte_check"] == "failed"
    assert checks["dpp_release_2008"]["local_byte_check"] == "passed"
    assert report["results"]["software_witnesses_passed"] is True
    assert report["clinical_fitting_allowed"] is False


def test_cli_exports_failed_source_checks_and_keeps_offline_default(tmp_path):
    destination = tmp_path / "audit.json"
    command = ["evidence", "dpp-observations", "--output", str(destination)]
    assert CliRunner().invoke(app, command).exit_code == 0
    assert json.loads(destination.read_bytes())["results"]["documentation_bytes_passed"] is None
    missing = tmp_path / "missing"
    result = CliRunner().invoke(app, command + ["--raw", str(missing)])
    assert result.exit_code == 1
    report = json.loads(destination.read_bytes())
    assert report["results"]["documentation_bytes_passed"] is False
    assert all(
        row["local_byte_check"] == "failed" for row in report["documentation"]["source_checks"]
    )
