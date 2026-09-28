import json
import shutil

import numpy as np
import pytest
from typer.testing import CliRunner

from demeter.analysis.experiments import compare, uncertainty
from demeter.cli import app
from demeter.data.healthspan import STORE, crosscheck, load_healthspan, rebuild_healthspan
from demeter.data.ingest import BUNDLE
from demeter.health.healthspan import CohortTime, lived_within_year, sullivan
from demeter.health.transitions import STATES
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def test_sullivan_hand_calculation_partitions_remaining_life_and_is_radix_invariant():
    # Synthetic arithmetic: 750 + 250 person-years / 100 births = 10 years.
    rows = sullivan([0, 10], [100, 50], [750, 250], [[0.8, 0.2], [0.4, 0.6]], ("healthy", "other"))
    assert rows[0]["life_expectancy"] == 10
    assert rows[0]["state_years"] == {"healthy": 7, "other": 3}
    assert rows[1]["state_years"] == {"healthy": 2, "other": 3}
    scaled = sullivan(
        [0, 10], [1000, 500], [7500, 2500], [[0.8, 0.2], [0.4, 0.6]], ("healthy", "other")
    )
    assert [r["state_years"] for r in rows] == [r["state_years"] for r in scaled]


@pytest.mark.parametrize(
    "bad",
    [
        [[0.8, 0.3], [0.4, 0.6]],
        [[1.1, -0.1], [0.4, 0.6]],
        [[np.nan, 0.2], [0.4, 0.6]],
        [[0.8], [0.4]],
    ],
)
def test_missing_overlapping_or_invalid_health_states_are_rejected(bad):
    with pytest.raises(ValueError, match="complete state partition"):
        sullivan([0, 10], [100, 50], [750, 250], bad, ("healthy", "other"))


def test_extinct_age_is_undefined_and_zero_health_is_a_real_zero():
    rows = sullivan([0, 10], [100, 0], [500, 0], [[0, 1], [0, 1]], ("healthy", "other"))
    assert rows[0]["state_years"]["healthy"] == 0
    assert rows[1]["state_years"]["healthy"] is None
    assert rows[1]["life_expectancy"] is None
    with pytest.raises(ValueError):
        sullivan([0, 10], [100, 0], [500, 1], [[0, 1], [0, 1]], ("healthy", "other"))


def test_within_year_exposure_matches_constant_hazard_integral_and_zero_limit():
    stock = np.array([[100.0, 100, 100]])
    rate = np.array([[0.0, np.log(2), 100]])
    lived = lived_within_year(stock, rate)
    assert lived[0, 0] == 100
    assert lived[0, 1] == pytest.approx(50 / np.log(2))
    assert lived[0, 2] == pytest.approx(1)
    assert np.all((lived >= 0) & (lived <= stock))


def test_endpoint_transitions_do_not_reassign_time_already_lived():
    tracker = CohortTime(np.array([[100.0, 0, 0], [0, 0, 0]]))
    tracker.advance(1, np.zeros((2, 3)), (np.log(2), 0, 0), 0)
    assert tracker.report()["state_person_years"] == dict(zip(STATES, [100, 0, 0], strict=True))
    tracker.advance(2, np.zeros((2, 3)), (0, 0, 0), 0)
    assert tracker.report()["state_person_years"] == dict(zip(STATES, [150, 50, 0], strict=True))
    assert tracker.report()["by_initial_age"][0]["cumulative_transitions"][
        "healthy_to_ir"
    ] == pytest.approx(50)
    assert (
        tracker.report()["by_initial_age"][1]["state_years_per_initial_person"]["healthy"] is None
    )
    with pytest.raises(ValueError, match="consecutive"):
        tracker.advance(4, np.zeros((2, 3)), (0, 0, 0), 0)


def test_original_cohort_time_conserves_counts_and_retains_open_age_membership():
    result = simulate(REGISTRY, Scenario(name="cohorts", years=25, exposures={}))
    report = result.healthspan["restricted_cohort"]
    cohorts = report["by_initial_age"]
    assert len(cohorts) == 101
    assert cohorts[-1]["initial_age_is_open"]
    assert sum(c["remaining_population"] for c in cohorts) == pytest.approx(
        result.ending_population
    )
    assert sum(c["deaths"] for c in cohorts) == pytest.approx(result.cumulative_deaths)
    assert sum(c["remaining_population"] for c in cohorts[75:]) == pytest.approx(
        sum(result.cohorts[100][s] for s in STATES)
    )
    for c in cohorts:
        assert 0 <= sum(c["state_years_per_initial_person"].values()) <= 25
    for state in STATES:
        assert sum(c["state_person_years"][state] for c in cohorts) == pytest.approx(
            report["state_person_years"][state]
        )
    for flow in ("healthy_to_ir", "ir_to_healthy", "ir_to_t2d"):
        assert sum(c["cumulative_transitions"][flow] for c in cohorts) == pytest.approx(
            sum(r.get(flow, 0) for r in result.annual)
        )
    for row in result.healthspan["period_by_age"]:
        assert sum(row["state_years"].values()) == pytest.approx(row["life_expectancy"])
        assert 0 <= row["healthspan"] <= row["life_expectancy"]
    assert (
        result.annual[-1]["healthspan"]
        == result.annual[-1]["metabolically_healthy_life_expectancy"]
    )


def test_paired_uncertainty_and_comparison_include_period_and_cohort_metrics():
    scenario = Scenario(name="same", years=2, exposures={})
    report = uncertainty(REGISTRY, scenario, draws=4, seed=31)
    assert (
        report["outcomes"]["healthspan"]
        == report["outcomes"]["metabolically_healthy_life_expectancy"]
    )
    for rows in (report["healthspan_by_age"], report["restricted_healthy_years_by_initial_age"]):
        assert len(rows) == 101
        assert all(all(v == 0 for v in r["paired_delta"].values()) for r in rows)
    assert report["healthspan_by_age"][0]["period_healthspan"] == report["outcomes"]["healthspan"]
    delta = compare(REGISTRY, scenario, scenario)
    assert all(v == 0 for v in delta["transition_deltas"].values())
    assert all(v == 0 for v in delta["state_time_deltas"].values())


def test_nchs_published_example_crosschecks_all_ages_and_rebuilds_offline(tmp_path, monkeypatch):
    def offline(*args, **kwargs):
        pytest.fail("Healthspan method verification must work offline")

    monkeypatch.setattr("urllib.request.urlopen", offline)
    rebuild_healthspan(REGISTRY, destination=tmp_path)
    for name in ("healthspan_benchmark.json", "healthspan_manifest.json"):
        assert (tmp_path / name).read_bytes() == (BUNDLE / name).read_bytes()
    report = crosscheck(load_healthspan(REGISTRY, tmp_path))
    assert report["passed"] and len(report["checks"]) == 18
    assert report["checks"][0]["published"] == 69.8
    assert report["checks"][13]["published"] == 13.8
    assert not report["scientific_release_ready"]


def test_healthspan_source_and_bundle_corruption_fail(tmp_path):
    shutil.copyfile(STORE / "manifest.json", tmp_path / "manifest.json")
    (tmp_path / "statnt21.pdf").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="source checksum"):
        rebuild_healthspan(REGISTRY, source=tmp_path, destination=tmp_path / "out")
    assert not (tmp_path / "out").exists()
    shutil.copyfile(BUNDLE / "healthspan_manifest.json", tmp_path / "healthspan_manifest.json")
    (tmp_path / "healthspan_benchmark.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="benchmark checksum"):
        load_healthspan(REGISTRY, tmp_path)


def test_healthspan_cli_keeps_definitions_evidence_and_unavailable_metrics(tmp_path):
    output = tmp_path / "healthspan.json"
    run = CliRunner().invoke(
        app, ["healthspan", "scenarios/baseline.yaml", "--output", str(output)]
    )
    assert run.exit_code == 0, run.output
    report = json.loads(output.read_bytes())
    assert report["definition"]["primary"] == "healthspan"
    assert report["definition"]["unavailable"]["qaly"]
    assert report["validation_only"]
    assert report["evidence_sha256"] == REGISTRY.content_hash
    run = CliRunner().invoke(app, ["evidence", "healthspan"])
    assert run.exit_code == 0 and json.loads(run.output)["passed"]
