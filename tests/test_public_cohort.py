import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook
from typer.testing import CliRunner

from demeter.analysis.public_cohort import (
    DATASET,
    analyze_cohort,
    audit_public_cohort,
    read_workbook,
)
from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry


def fixture():
    """Synthetic records deliberately distinguish blank diagnosis from zero."""
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = copy.deepcopy(registry.datasets[DATASET]["analysis"])
    spec.update(
        published_records=6, published_male=3, published_female=3, published_diabetes_events=3
    )
    rows = [
        [1, 30, 1, 5, 8, None, 1, 3.1],
        [2, 30, 1, 5, 5, 1, 1, 3.1],
        [3, 30, 1, 5, 5, None, 0, 3.1],
        [4, 30, 2, 5, 5, 0, 0, 3.1],
        [5, 30, 2, 5, None, 1, 1, 3.1],
        [6, 30, 2, 5, None, 0, 0, 3.1],
    ]
    return pd.DataFrame(rows, columns=spec["columns"]), spec


def test_missing_diagnosis_is_unknown_and_positive_evidence_takes_precedence():
    data, spec = fixture()
    result = analyze_cohort(data, spec)
    assert result["source_reproduction_passed"]
    r = result["endpoint_reconciliation"]
    assert (r["observed_positive_rule"], r["observed_negative_rule"], r["unknown_rule"]) == (
        3,
        1,
        2,
    )
    assert r["known_rule_compared"] == 4
    assert r["known_rule_disagreements"] == 0
    conditional = r["if_blank_diagnosis_meant_negative"]
    assert conditional["compared"] == 5
    assert conditional["unknown"] == 1
    assert result["diagnosis_field"] == dict(zero=2, one=2, missing=2, invalid=0)
    assert result["followup"]["all"]["observed"] == 6
    assert data.loc[2, "diagnosis"] != data.loc[2, "diagnosis"]  # Input remains missing.


@pytest.mark.parametrize(
    "column,value",
    [
        ("sex", 3),
        ("endpoint", 2),
        ("followup", -1),
        ("followup", float("inf")),
        ("baseline_fpg", 0),
        ("diagnosis", 9),
        ("age", 19),
    ],
)
def test_invalid_observations_remain_visible_without_dropping_people(column, value):
    data, spec = fixture()
    data.loc[0, column] = value
    result = analyze_cohort(data, spec)
    assert result["records"] == 6
    assert result["invalid"][column] == 1
    assert not result["source_reproduction_passed"]


def test_duplicate_ids_missing_followup_and_rule_disagreement_fail_checks():
    data, spec = fixture()
    data.loc[1, "id"] = data.loc[0, "id"]
    data.loc[0, "followup"] = None
    data.loc[0, "endpoint"] = 0
    result = analyze_cohort(data, spec)
    assert result["rows_with_duplicated_identifiers"] == 2
    assert result["followup"]["all"]["missing_or_invalid"] == 1
    assert result["endpoint_reconciliation"]["known_rule_disagreements"] == 1
    assert not result["source_reproduction_passed"]


def test_counts_and_headers_are_required():
    data, spec = fixture()
    with pytest.raises(ValueError, match="row count"):
        analyze_cohort(data.iloc[:-1], spec)
    with pytest.raises(ValueError, match="fields"):
        analyze_cohort(data.drop(columns=["endpoint"]), spec)


def test_published_timing_disagreement_is_retained():
    data, spec = fixture()
    data["followup"] = 2.99
    report = analyze_cohort(data, spec)
    assert report["followup"]["all"]["quantiles_years"][2] == 2.99
    assert report["checks"]["published_event_count"]
    assert not report["checks"]["published_median_followup"]
    assert not report["source_reproduction_passed"]


def test_cli_emits_failed_source_report_before_exit(tmp_path, monkeypatch):
    data, spec = fixture()
    data["followup"] = 2.99
    report = {"results": analyze_cohort(data, spec)}
    monkeypatch.setattr("demeter.analysis.public_cohort.audit_public_cohort", lambda *a: report)
    output = tmp_path / "audit.json"
    run = CliRunner().invoke(
        app, ["evidence", "public-cohort", "--workbook", "unused", "--output", str(output)]
    )
    assert run.exit_code == 1
    assert json.loads(output.read_bytes()) == report


def test_formula_cells_are_rejected_without_execution(tmp_path):
    _, spec = fixture()
    book = Workbook()
    sheet = book.active
    sheet.title = spec["sheet"]
    sheet.append(list(spec["columns"].values()))
    sheet.append([1, 30, 1, 5, 8, None, "=1", 3.1])
    path = tmp_path / "synthetic.xlsx"
    book.save(path)
    with pytest.raises(ValueError, match="formulas"):
        read_workbook(path, spec)


def test_source_and_protocol_mismatch_rejected_before_reading(monkeypatch, tmp_path):
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    monkeypatch.setattr(
        "demeter.analysis.public_cohort.read_workbook",
        lambda *args: pytest.fail("Unverified workbook read"),
    )
    path = tmp_path / "bad.xlsx"
    path.write_bytes(b"not the registered source")
    with pytest.raises(ValueError, match="checksum"):
        audit_public_cohort(registry, path)
    registry.datasets[DATASET]["analysis"]["glucose_threshold_mmol_l"] = 8
    with pytest.raises(ValueError, match="protocol/registry"):
        audit_public_cohort(registry, path)
    registry.datasets[DATASET]["model_role"] = "health_model"
    with pytest.raises(ValueError, match="benchmark_only"):
        audit_public_cohort(registry, path)


def test_cli_missing_source_fails_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: pytest.fail("Network call"))
    run = CliRunner().invoke(app, ["evidence", "public-cohort", "--workbook", str(tmp_path / "x")])
    assert run.exit_code == 1


def test_saved_aggregate_receipt_has_current_definition_and_no_person_rows():
    report = json.loads(Path("docs/validation/issue-57-public-cohort.json").read_bytes())
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = registry.datasets[DATASET]
    assert report["provenance"]["definition_sha256"] == digest(encoded(spec))
    assert report["provenance"]["transform_sha256"] == digest(
        Path("src/demeter/analysis/public_cohort.py").read_bytes()
    )
    assert report["model_role"] == "benchmark_only"
    assert not report["scientific_release_ready"]
    assert report["provenance"]["individual_results_exported"] is False
    result = report["results"]
    assert sum(result["sex_counts"].values()) == result["records"]
    assert sum(result["recorded_endpoint"].values()) == result["records"]
    assert [k for k, passed in result["checks"].items() if not passed] == [
        "published_median_followup"
    ]
    r = result["endpoint_reconciliation"]
    assert (
        sum(r[k] for k in ["observed_positive_rule", "observed_negative_rule", "unknown_rule"])
        == result["records"]
    )
