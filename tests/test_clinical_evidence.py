import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from demeter.cli import app
from demeter.evidence.appraisal import applicability_report, extract_interval, verify_sources
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario, TableExtraction

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
HTML = b"""<table><tr><th>Group</th><th>Estimate</th></tr>
<tr><td>A</td><td>9.0 (8.0-10.0)</td></tr>
<tr><td><b>A</b></td><td>2.0 (1.0-3.0)</td></tr></table>"""


def fixture_registry():
    raw = REGISTRY.model_dump(mode="json")
    raw["parameters"] = {k: v for k, v in raw["parameters"].items() if not v["source_id"]}
    raw["sources"] = {
        "test_source": {
            "url": "https://example.org/synthetic-test-fixture",
            "citation": "Synthetic parser fixture, not clinical evidence",
            "doi": "test-fixture",
            "raw_filename": "fixture.html",
            "sha256": hashlib.sha256(HTML).hexdigest(),
            "retrieved_at": "2026-09-26T00:00:00+00:00",
            "license": "Synthetic test data",
        }
    }
    p = REGISTRY.parameters["aric_hba1c_prediabetes_diabetes_incidence"].model_dump(mode="json")
    p.update(
        key="test_benchmark",
        source_id="test_source",
        value=0.002,
        source_url=raw["sources"]["test_source"]["url"],
    )
    p["uncertainty"].update(low=0.001, high=0.003)
    p["applicability"]["extraction"] = dict(
        table_index=0, row_label="A", row_occurrence=1, column_index=1, scale=0.001
    )
    raw["parameters"]["test_benchmark"] = p
    return EvidenceRegistry.model_validate(raw)


def test_duplicate_row_selection_scale_and_markup():
    p = fixture_registry().parameters["test_benchmark"]
    assert extract_interval(HTML, p.applicability.extraction) == pytest.approx(
        (0.002, 0.001, 0.003)
    )


@pytest.mark.parametrize(
    "content",
    [
        b"<html>Access denied</html>",
        HTML.replace(b"2.0 (1.0-3.0)", b"2.0 (3.0-1.0)"),
        HTML.replace(b"2.0 (1.0-3.0)", b"2.0 (1.0-3.0)*"),
        b"<table><table></table></table>",
    ],
)
def test_source_format_drift_fails_closed(content):
    with pytest.raises(ValueError):
        extract_interval(
            content, fixture_registry().parameters["test_benchmark"].applicability.extraction
        )


def test_pinned_source_and_estimate_both_verified(tmp_path):
    registry = fixture_registry()
    path = tmp_path / "fixture.html"
    path.write_bytes(HTML)
    assert verify_sources(registry, tmp_path)["passed"]
    registry.parameters["test_benchmark"].value = 0.0025
    assert not verify_sources(registry, tmp_path)["passed"]
    path.write_bytes(HTML + b" ")
    result = verify_sources(registry, tmp_path)
    assert result["checks"][0]["reason"] == "checksum_mismatch"


def test_missing_source_does_not_download_by_default(tmp_path, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Offline verification attempted a network request")

    monkeypatch.setattr("urllib.request.urlopen", unexpected)
    result = verify_sources(fixture_registry(), tmp_path)
    assert not result["passed"]
    assert result["checks"][0]["reason"] == "missing_raw_artifact"


def test_changed_download_is_never_saved_or_promoted(tmp_path, monkeypatch):
    from io import BytesIO

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: BytesIO(b"changed source"))
    registry = fixture_registry()
    original = registry.content_hash
    result = verify_sources(registry, tmp_path, download=True)
    assert not result["passed"]
    assert not (tmp_path / "fixture.html").exists()
    assert registry.content_hash == original


@pytest.mark.parametrize(
    "mutation", ["missing_source", "unknown_target", "active_candidate", "path", "naive_time"]
)
def test_invalid_evidence_contracts_fail(mutation):
    raw = fixture_registry().model_dump(mode="json")
    p = raw["parameters"]["test_benchmark"]
    if mutation == "missing_source":
        p["source_id"] = "absent"
    elif mutation == "unknown_target":
        p["applicability"]["candidate_for"] = ["typo"]
    elif mutation == "active_candidate":
        p["model_role"] = "health_model"
    elif mutation == "path":
        raw["sources"]["test_source"]["raw_filename"] = "../source.html"
    else:
        raw["sources"]["test_source"]["retrieved_at"] = "2026-09-26T00:00:00"
    with pytest.raises(ValidationError):
        EvidenceRegistry.model_validate(raw)


def test_benchmark_cannot_drive_engine_even_after_renaming_and_unit_change():
    raw = fixture_registry().model_dump(mode="json")
    p = raw["parameters"].pop("test_benchmark")
    p.update(key="ir_to_t2d_rate", unit="hazard_per_year")
    raw["parameters"]["ir_to_t2d_rate"] = p
    with pytest.raises(ValueError, match="Benchmark-only"):
        simulate(EvidenceRegistry.model_validate(raw), Scenario(name="x", exposures={}))


def test_appraised_sources_do_not_change_simulations_or_uncertainty_inputs():
    from demeter.analysis.experiments import sampled_parameters

    raw = REGISTRY.model_dump(mode="json")
    raw["parameters"] = {k: v for k, v in raw["parameters"].items() if not v["source_id"]}
    raw["sources"] = {}
    prior = EvidenceRegistry.model_validate(raw)
    scenario = Scenario(name="unchanged", exposures={"upf": 0.7}, years=5)
    before, after = simulate(prior, scenario), simulate(REGISTRY, scenario)
    assert before.annual == after.annual
    assert before.cohorts == after.cohorts
    assert sampled_parameters(prior) == sampled_parameters(REGISTRY)
    assert before.metadata["evidence_sha256"] != after.metadata["evidence_sha256"]


def test_appraisals_show_all_model_inputs_and_keep_release_blocked():
    from demeter.model import REQUIRED_UNITS

    report = applicability_report(REGISTRY)
    assert {r["model_input"] for r in report["inputs"]} == set(REQUIRED_UNITS)
    progression = next(r for r in report["inputs"] if r["model_input"] == "ir_to_t2d_rate")
    assert len(progression["candidates"]) == 4
    assert not report["scientific_release_ready"]
    assert not progression["replacement_identified"]
    assert REGISTRY.sources["aric_rooney_2021_corrected"].correction_url


def test_clinical_cli_outputs_and_missing_sources_exit(tmp_path):
    output = tmp_path / "report.json"
    result = CliRunner().invoke(app, ["evidence", "applicability", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_text())["scientific_release_ready"] is False
    result = CliRunner().invoke(app, ["evidence", "verify-sources", "--raw", str(tmp_path)])
    assert result.exit_code == 1
    assert json.loads(result.output)["passed"] is False


def test_registered_clinical_estimates_have_receipts_and_intervals():
    candidates = [p for p in REGISTRY.parameters.values() if p.applicability]
    assert len(candidates) == 6
    for p in candidates:
        assert p.model_role == "benchmark_only"
        assert p.uncertainty.kind == "interval"
        assert p.uncertainty.low <= p.value <= p.uncertainty.high
        assert p.source_url == REGISTRY.sources[p.source_id].url
        assert p.applicability.blockers
    report_path = Path("docs/validation/issue-1-clinical-sources.json")
    report = json.loads(report_path.read_text())
    # Keep this historical extraction receipt immutable when unrelated datasets change.
    # Verify every recorded clinical estimate and source against today's registry.
    checked = set()
    for check in report["checks"]:
        assert check["sha256"] == REGISTRY.sources[check["source"]].sha256
        for extracted in check["parameters"]:
            p = REGISTRY.parameters[extracted["parameter"]]
            assert p.source_id == check["source"]
            assert extracted["extracted"] == [p.value, p.uncertainty.low, p.uncertainty.high]
            checked.add(p.key)
    assert checked == {p.key for p in candidates}


def test_table_extraction_requires_positive_scale():
    with pytest.raises(ValidationError):
        TableExtraction(table_index=0, row_label="A", column_index=1, scale=0)


def test_conflicting_source_identity_rejected():
    raw = fixture_registry().model_dump(mode="json")
    raw["parameters"]["test_benchmark"]["source_url"] = "https://example.org/wrong-paper"
    with pytest.raises(ValidationError, match="source URL"):
        EvidenceRegistry.model_validate(raw)


def test_source_network_failure_returns_failed_report(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("source unavailable")

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    result = verify_sources(fixture_registry(), tmp_path, download=True)
    assert not result["passed"]
    assert result["checks"][0]["reason"] == "download_failed"


@pytest.mark.parametrize(
    "dataset,verifier,pass_field",
    [
        (
            "chen_public_intake",
            "demeter.analysis.public_cohort.audit_public_cohort",
            "source_reproduction_passed",
        ),
        (
            "food_intake_reproduction",
            "demeter.analysis.food_intake.reproduce_intake",
            "published_reproduction_passed",
        ),
        (
            "chen_followup_timing_audit",
            "demeter.analysis.public_cohort_timing.audit_timing",
            "source_reproduction_passed",
        ),
    ],
)
@pytest.mark.parametrize("reproduced", [False, True])
def test_dataset_sources_dispatch_after_verified_download(
    tmp_path, monkeypatch, dataset, verifier, pass_field, reproduced
):
    from io import BytesIO

    registry = fixture_registry()
    del registry.parameters["test_benchmark"]
    registry.datasets = {dataset: {"source_id": "test_source"}}
    results = {pass_field: reproduced, "checks": {"published_summary": reproduced}}

    def audit(actual_registry, path):
        assert actual_registry is registry
        assert path.read_bytes() == HTML
        return {"analysis_id": "synthetic-reproduction", "results": results}

    monkeypatch.setattr(verifier, audit)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: BytesIO(HTML))
    report = verify_sources(registry, tmp_path, download=True)
    assert report["passed"] is reproduced
    check = report["checks"][0]
    assert check["checksum_passed"]
    assert check["parameters"] == []
    assert check["datasets"] == [
        {
            "dataset": dataset,
            "passed": reproduced,
            "analysis_id": "synthetic-reproduction",
            "results": results,
        }
    ]
    # Already-present downloads must not bypass checksum verification or reach the analyzer.
    (tmp_path / "fixture.html").write_bytes(b"changed source")
    monkeypatch.setattr(verifier, lambda *a: pytest.fail("Unverified dataset analyzed"))
    assert verify_sources(registry, tmp_path)["checks"][0]["reason"] == "checksum_mismatch"


def test_dataset_protocol_errors_are_failed_checks_and_do_not_hide_other_sources(
    tmp_path, monkeypatch
):
    registry = fixture_registry()
    registry.datasets = {"chen_public_intake": {"source_id": "test_source"}}
    registry.sources["another_source"] = registry.sources["test_source"].model_copy()
    (tmp_path / "fixture.html").write_bytes(HTML)

    def invalid(*a):
        raise ValueError("Public cohort protocol/registry mismatch")

    monkeypatch.setattr("demeter.analysis.public_cohort.audit_public_cohort", invalid)
    report = verify_sources(registry, tmp_path)
    assert not report["passed"]
    assert len(report["checks"]) == 2
    first = report["checks"][0]
    assert first["parameters"][0]["passed"]
    assert not first["passed"]
    assert first["datasets"][0]["reason"] == "Public cohort protocol/registry mismatch"
    assert report["checks"][1]["reason"] == "no_registered_verification"


def test_unknown_dataset_contract_cannot_pass_on_checksum_only(tmp_path):
    registry = fixture_registry()
    registry.datasets = {"unimplemented": {"source_id": "test_source"}}
    (tmp_path / "fixture.html").write_bytes(HTML)
    result = verify_sources(registry, tmp_path)
    assert not result["passed"]
    check = result["checks"][0]
    assert check["checksum_passed"]
    assert check["parameters"][0]["passed"]
    assert check["datasets"][0]["reason"] == "unsupported_dataset_verification"
