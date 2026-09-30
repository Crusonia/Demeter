import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from demeter.analysis.public_cohort_timing import DATASET, _agrees, analyze_timing, audit_timing
from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry


def fixture():
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = copy.deepcopy(registry.datasets[DATASET]["analysis"])
    spec.update(
        published_person_years=12.4,
        published_person_years_decimal_places=1,
        published_crude_incidence_per_1000_person_years=80.65,
    )
    intake = copy.deepcopy(registry.datasets["chen_public_intake"]["analysis"])
    intake.update(
        published_records=4, published_male=2, published_female=2, published_diabetes_events=1
    )
    rows = [
        [1, 30, 1, 5, 5, None, 0, 2],
        [2, 30, 1, 5, 5, None, 0, 2],
        [3, 30, 2, 5, 5, None, 0, 3],
        [4, 30, 2, 5, 8, None, 1, 5.4],
    ]
    return pd.DataFrame(rows, columns=intake["columns"]), spec, intake


def test_matching_mean_does_not_repair_failed_median():
    data, spec, intake = fixture()
    result = analyze_timing(data, spec, intake)
    all_records = result["groups"]["all"]
    assert all_records["sum_released_years"] == pytest.approx(12.4)
    assert all_records["arithmetic_mean_years"] == pytest.approx(3.1)
    assert all_records["ordinary_median_years"] == 2.5
    assert result["diagnostic_hypotheses"]["mean_matches_published_median_at_displayed_precision"]
    assert result["checks"]["published_person_years"]
    assert not result["checks"]["published_median_followup"]
    assert not result["original_intake_checks"]["published_median_followup"]
    assert not result["source_reproduction_passed"]


def test_all_and_endpoint_partitions_have_explicit_denominators_and_empty_groups():
    data, spec, intake = fixture()
    groups = analyze_timing(data, spec, intake)["groups"]
    partitions = [g for name, g in groups.items() if name != "all"]
    assert sum(g["records"] for g in partitions) == groups["all"]["records"] == 4
    assert sum(g["sum_released_years"] or 0 for g in partitions) == pytest.approx(12.4)
    assert groups["unclassified_endpoint"]["sum_released_years"] is None
    assert groups["unclassified_endpoint"]["ordinary_median_years"] is None
    assert not groups["unclassified_endpoint"]["complete"]


@pytest.mark.parametrize("value", [None, -1, float("inf"), "bad"])
def test_partial_timing_cannot_match_complete_release_or_generate_a_rate(value):
    data, spec, intake = fixture()
    data["followup"] = data["followup"].astype(object)
    data.loc[0, "followup"] = value
    result = analyze_timing(data, spec, intake)
    group = result["groups"]["all"]
    assert group["records"] == 4
    assert group["observed_followup"] == 3
    assert group["missing_or_invalid_followup"] == 1
    assert not group["complete"]
    assert not result["checks"]["published_person_years"]
    assert result["publication_arithmetic"]["implied_crude_rate_from_complete_release"] is None
    assert not result["source_reproduction_passed"]


@pytest.mark.parametrize("value", [None, 2, float("inf"), "bad"])
def test_unknown_endpoint_is_a_partition_and_prevents_complete_rate(value):
    data, spec, intake = fixture()
    data["endpoint"] = data["endpoint"].astype(object)
    data.loc[0, "endpoint"] = value
    result = analyze_timing(data, spec, intake)
    assert result["groups"]["unclassified_endpoint"]["records"] == 1
    assert sum(g["records"] for k, g in result["groups"].items() if k != "all") == 4
    assert result["publication_arithmetic"]["implied_crude_rate_from_complete_release"] is None
    assert not result["source_reproduction_passed"]


def test_no_observed_durations_are_null_not_zero_or_a_passing_empty_comparison():
    data, spec, intake = fixture()
    data["followup"] = float("nan")
    result = analyze_timing(data, spec, intake)
    assert result["groups"]["all"]["observed_followup"] == 0
    assert result["groups"]["all"]["sum_released_years"] is None
    assert (
        not any(result["checks"].values())
        or result["checks"]["published_crude_rate_from_published_counts"]
    )
    assert not result["checks"]["conservative_calendar_bound_under_any_checked_convention"]


def test_day_grid_and_calendar_diagnostics_are_conditional_without_trimming():
    data, spec, intake = fixture()
    data["followup"] = [731 / 365.25, 732 / 365.25, 1096 / 365.25, 3000 / 365.25]
    result = analyze_timing(data, spec, intake)
    assert result["groups"]["all"]["records"] == 4
    diagnostics = result["calendar_and_day_grid_diagnostics"]
    grid = next(d for d in diagnostics if d["candidate_days_per_year"] == 365.25)
    assert grid["within_integer_day_tolerance"] == 4
    assert all(d["outside_reported_calendar_envelope"] == 1 for d in diagnostics)
    assert not result["checks"]["conservative_calendar_bound_under_any_checked_convention"]
    assert data.loc[3, "followup"] == 3000 / 365.25


def test_publication_and_release_denominators_remain_separate():
    data, spec, intake = fixture()
    spec["published_person_years"] = 10
    result = analyze_timing(data, spec, intake)
    arithmetic = result["publication_arithmetic"]
    assert arithmetic["implied_crude_rate_from_published_counts"] == 100
    assert arithmetic["implied_crude_rate_from_complete_release"] == pytest.approx(80.6451612903)
    assert not result["checks"]["published_crude_rate_from_published_counts"]
    assert result["checks"]["published_crude_rate_from_release"]


def test_a_complete_synthetic_source_can_pass_all_checks():
    data, spec, intake = fixture()
    data["followup"] = 3.1
    result = analyze_timing(data, spec, intake)
    assert all(result["checks"].values())
    assert result["source_reproduction_passed"]


def test_visit_eligibility_is_not_assumed_to_bound_diagnosis_stopping():
    data, spec, intake = fixture()
    data.loc[3, "followup"] = 1
    result = analyze_timing(data, spec, intake)
    assert (
        result["eligibility_interval_diagnostic"]["observed_durations_below_eligibility_interval"]
        == 1
    )
    assert "published_minimum_interval" not in result["checks"]


def test_displayed_precision_assumption_does_not_accept_half_unit_ties():
    assert _agrees(3.11, 3.1, 1)
    assert not _agrees(3.2, 3.1, 1)
    assert not _agrees(12.5, 12, 0)
    assert not _agrees(None, 12, 0)
    assert not _agrees(3.15, 3.1, 1)
    assert not _agrees(3.05, 3.1, 1)
    assert not _agrees(6.175, 6.17, 2)
    assert not _agrees(6.165, 6.17, 2)


def test_source_and_definition_drift_are_rejected_before_reading(tmp_path, monkeypatch):
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    monkeypatch.setattr(
        "demeter.analysis.public_cohort_timing.read_workbook",
        lambda *a: pytest.fail("Unverified workbook analyzed"),
    )
    path = tmp_path / "changed.xlsx"
    path.write_bytes(b"changed archive")
    with pytest.raises(ValueError, match="checksum"):
        audit_timing(registry, path)
    registry.datasets[DATASET]["analysis"]["published_person_years"] += 1
    with pytest.raises(ValueError, match="protocol/registry"):
        audit_timing(registry, path)
    registry.datasets[DATASET]["model_role"] = "health_model"
    with pytest.raises(ValueError, match="benchmark_only"):
        audit_timing(registry, path)


def test_cli_preserves_failed_report_and_never_downloads(tmp_path, monkeypatch):
    data, spec, intake = fixture()
    report = {"results": analyze_timing(data, spec, intake)}
    monkeypatch.setattr("demeter.analysis.public_cohort_timing.audit_timing", lambda *a: report)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: pytest.fail("Network call"))
    output = tmp_path / "timing.json"
    run = CliRunner().invoke(
        app,
        ["evidence", "public-cohort-timing", "--workbook", "unused", "--output", str(output)],
    )
    assert run.exit_code == 1
    assert output.read_bytes() == encoded(report)


def test_committed_receipt_matches_definitions_and_keeps_fitting_disabled():
    report = json.loads(Path("docs/validation/issue-57-chen-timing.json").read_bytes())
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = registry.datasets[DATASET]
    provenance = report["provenance"]
    assert provenance["definition_sha256"] == digest(encoded(spec))
    assert provenance["protocol_sha256"] == spec["protocol_sha256"]
    assert provenance["amendment_sha256"] == spec["amendment_sha256"]
    assert provenance["transform_sha256"] == digest(
        Path("src/demeter/analysis/public_cohort_timing.py").read_bytes()
    )
    assert provenance["reader_sha256"] == digest(
        Path("src/demeter/analysis/public_cohort.py").read_bytes()
    )
    assert report["observation_decision"]["likelihood_mode"] == "unresolved"
    assert not report["observation_decision"]["hazard_fit_permitted"]
    assert not report["observation_decision"]["engine_activation_permitted"]
    assert not report["scientific_release_ready"]
    assert not provenance["individual_results_exported"]
