import json
import shutil
from functools import partial
from math import exp, log

import numpy as np
import pytest
from typer.testing import CliRunner

from demeter.analysis.experiments import compare, sampled_parameters, uncertainty, with_values
from demeter.analysis.visualization import glp1_figures
from demeter.cli import app
from demeter.data.glp1 import STORE, load_glp1, rebuild_glp1
from demeter.data.ingest import BUNDLE
from demeter.health.glp1 import GLP1Cohort, GLP1_UNITS, affordability
from demeter.health.structure import move, states_for
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def scenario(**kwargs):
    data = {
        "name": "glp1",
        "years": 5,
        "health_structure": "risk_1",
        "glp1": {
            "access_schedule": [
                {
                    "start_year": 1,
                    "access_fraction": 1,
                    "coverage_fraction": 1,
                    "monthly_price_usd": 100,
                    "monthly_copay_usd": 0,
                    "supply_fraction": 1,
                }
            ]
        },
    }
    data.update(kwargs)
    return Scenario.model_validate(data)


def isolated(registry=REGISTRY, s=None):
    s = s or scenario()
    states = states_for(s)
    stocks = np.zeros((101, len(states)))
    stocks[40, 0] = 100
    return GLP1Cohort(stocks, states, partial(move, structure=s.health_structure), registry, s)


def test_analytic_initiation_response_and_withdrawal():
    r = with_values(
        REGISTRY,
        {
            "glp1_eligible_fraction": 1,
            "glp1_low_response_share": 0,
            "glp1_initiation_rate": log(2),
            "glp1_discontinuation_rate": 0,
            "glp1_response_lag": 1,
            "glp1_washout_lag": 2,
        },
    )
    s = scenario()
    off = s.glp1.access_schedule[0].model_copy(update={"start_year": 2, "access_fraction": 0})
    s.glp1.access_schedule.append(off)
    c = isolated(r, s)
    zero = np.zeros_like(c.stocks)
    c.advance(1, zero, (0,) * 5, 18)
    assert c.joint.sum() == pytest.approx(100)
    assert c.treatment_report()["on_treatment"] == pytest.approx(50)
    assert c.joint[:, :, :, 2, :].sum() == pytest.approx(50 * (1 - exp(-1)))
    c.advance(2, zero, (0,) * 5, 18)
    report = c.treatment_report()
    assert report["on_treatment"] == 0
    assert report["flows"]["discontinuations"] == pytest.approx(50)
    assert report["residual_response_off_treatment"] == pytest.approx(
        50 * (1 - exp(-1)) * exp(-0.5)
    )
    assert c.stocks.sum() == pytest.approx(100)
    assert c.person_years.sum() == pytest.approx(200)


@pytest.mark.parametrize("structure", ["legacy", "risk_1", "risk_2"])
def test_joint_conservation_and_zero_effect_baseline(structure):
    s = scenario(health_structure=structure)
    r = with_values(REGISTRY, {"glp1_progression_beta": 0, "glp1_recovery_beta": 0})
    result = simulate(r, s, diagnostics=True)
    baseline = simulate(r, s.model_copy(update={"glp1": None}))
    for actual, expected in zip(result.annual, baseline.annual, strict=True):
        assert actual["population"] + actual["cumulative_deaths"] == pytest.approx(
            result.starting_population
        )
        assert sum(actual["glp1"]["treatment_stocks"].values()) == pytest.approx(
            actual["population"]
        )
        for field in ("healthspan", "population", "cumulative_deaths", "restricted_healthy_years"):
            assert actual[field] == pytest.approx(expected[field], rel=1e-12)
        g = actual["glp1"]
        assert g["on_treatment"] == pytest.approx(
            g["cumulative_flows"]["initiations"]
            + g["cumulative_flows"]["reinitiations"]
            - g["cumulative_flows"]["discontinuations"]
            - g["cumulative_on_treatment_deaths"]
        )
        assert all(v >= 0 for v in g["treatment_stocks"].values())
    assert result.healthspan["restricted_cohort"]["state_person_years"] == pytest.approx(
        baseline.healthspan["restricted_cohort"]["state_person_years"]
    )


@pytest.mark.parametrize("blocked", ["eligibility", "access", "supply", "initiation"])
def test_no_treatment_reproduces_baseline(blocked):
    s, r = scenario(), REGISTRY
    if blocked in ("eligibility", "initiation"):
        r = with_values(
            r, {"glp1_eligible_fraction" if blocked == "eligibility" else "glp1_initiation_rate": 0}
        )
    else:
        setattr(s.glp1.access_schedule[0], blocked + "_fraction", 0)
    delta = compare(r, s.model_copy(update={"glp1": None}), s)
    assert all(abs(v["absolute_delta"]) < 1e-6 for v in delta["outcomes"].values())
    assert simulate(r, s).annual[-1]["glp1"]["on_treatment"] == 0


def test_capacity_shrink_restart_and_cohort_tagging():
    s = Scenario.from_yaml("scenarios/glp1_access.yaml")
    result = simulate(REGISTRY, s)
    for row in result.annual[1:]:
        g = row["glp1"]
        assert g["on_treatment"] <= g["allocation"]["capacity"] + 1e-6
        assert g["on_treatment"] <= g["eligible_adults"]
        assert sum(g["allocation"]["discontinuation_by_reason"].values()) == pytest.approx(
            g["flows"]["discontinuations"], abs=1e-7
        )
    assert result.annual[9]["glp1"]["on_treatment"] == 0
    assert result.annual[9]["glp1"]["residual_response_off_treatment"] > 0
    assert (
        result.annual[11]["glp1"]["residual_response_off_treatment"]
        < result.annual[9]["glp1"]["residual_response_off_treatment"]
    )
    assert result.annual[12]["glp1"]["flows"]["reinitiations"] > 0
    assert result.prechronic["future_t2d_entries"] <= result.annual[-1]["cumulative_t2d_incidence"]
    tagged = result.prechronic["initial_prechronic_cohort"]
    assert sum(
        v["remaining_population"] + v["deaths"] for v in tagged["by_initial_age"]
    ) == pytest.approx(sum(v["initial_population"] for v in tagged["by_initial_age"]))


def test_adult_boundary_and_persistent_indication():
    r = with_values(REGISTRY, {"glp1_eligible_fraction": 1})
    c = isolated(r)
    # Move the whole test population to age 17; it becomes adult only after step 1.
    c.joint[17] = c.joint[40]
    c.joint[40] = 0
    c.stocks = c.joint.sum(axis=(1, 2, 3))
    c.baseline_adults = 100
    c.advance(1, np.zeros_like(c.stocks), (0,) * 5, 18)
    assert c.treatment_report()["on_treatment"] == 0
    c.advance(2, np.zeros_like(c.stocks), (0,) * 5, 18)
    assert c.treatment_report()["on_treatment"] > 0


def test_t2d_persistence_differs_and_capacity_prioritizes_continuers():
    r = with_values(
        REGISTRY,
        {
            "glp1_eligible_fraction": 1,
            "glp1_low_response_share": 0,
            "glp1_discontinuation_rate": log(2),
            "glp1_discontinuation_t2d_rate": 0,
        },
    )
    c = isolated(r)
    c.joint.fill(0)
    c.joint[40, 1, 1, 2, 0] = 40
    c.joint[40, 1, 1, 2, 3] = 40
    c.joint[40, 1, 1, 0, 0] = 20
    c.scenario.glp1.access_schedule[0].supply_fraction = 0.3
    c.advance(1, np.zeros_like(c.stocks), (0,) * 5, 18)
    # 60 requested continuations, 30 slots: proportional rationing; no new starts.
    assert c.joint[:, :, :, 2, 0].sum() == pytest.approx(10)
    assert c.joint[:, :, :, 2, 3].sum() == pytest.approx(20)
    assert c.last_treatment_flows["initiations"] == 0
    assert c.treatment_report()["on_treatment"] == pytest.approx(30)


def test_tagged_cohorts_share_full_population_allocation():
    c = isolated()
    stocks = c.stocks * 0.25
    tag = GLP1Cohort(stocks, c.states, c.mover, c.registry, c.scenario)
    for year in range(1, 5):
        plan = c.plan(year, 18)
        c.advance(year, np.full_like(c.stocks, 0.1), (0.1,) * 5, 18, plan=plan)
        tag.advance(year, np.full_like(c.stocks, 0.1), (0.1,) * 5, 18, plan=plan)
        assert np.allclose(tag.joint, c.joint * 0.25, atol=1e-12, rtol=1e-12)


def test_heterogeneity_and_price_coverage_are_distinct():
    s = scenario()
    step = s.glp1.access_schedule[0]
    assert affordability(REGISTRY, step) == 1
    step.coverage_fraction = 0
    expensive = affordability(REGISTRY, step)
    step.monthly_price_usd = 50
    assert expensive < affordability(REGISTRY, step) < 1
    step.coverage_fraction = 1
    assert affordability(REGISTRY, step) == 1
    r = with_values(REGISTRY, {"glp1_low_response_factor": 0, "glp1_low_response_share": 0.5})
    c = isolated(r, s)
    c.advance(1, np.zeros_like(c.stocks), (0.2, 0, 0, 0, 0), 18)
    # Exposure is equal at entry, but high-response people progress less.
    assert c.joint[:, :, 1, :, 1].sum() < c.joint[:, :, 0, :, 1].sum()


def test_evidence_units_bounds_and_schedule_validation():
    for key, value in (("glp1_response_lag", 0), ("glp1_affordability_scale", 0)):
        with pytest.raises(ValueError, match="GLP-1"):
            simulate(with_values(REGISTRY, {key: value}), scenario())
    bad = REGISTRY.model_copy(deep=True)
    bad.parameters["glp1_weight_loss"].model_role = "benchmark_only"
    with pytest.raises(ValueError, match="Benchmark-only"):
        simulate(bad, scenario())
    data = scenario().model_dump()
    data["glp1"]["access_schedule"].append(data["glp1"]["access_schedule"][0].copy())
    with pytest.raises(ValueError, match="unique"):
        Scenario.model_validate(data)
    with pytest.raises(ValueError, match="Scientific mode blocked"):
        simulate(REGISTRY, scenario(mode="scientific"))


def test_pairing_and_uncertainty_use_only_active_parameters():
    s = scenario(years=2)
    assert set(GLP1_UNITS) <= set(sampled_parameters(REGISTRY, s))
    assert not set(GLP1_UNITS) & set(sampled_parameters(REGISTRY))
    a = uncertainty(REGISTRY, s, draws=2, seed=3)
    assert a == uncertainty(REGISTRY, s, draws=2, seed=3)
    assert a["paired_deltas"]["healthspan"]["median"] > 0


def test_sources_rebuild_without_network_and_corruption_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: pytest.fail("network use"))
    rebuild_glp1(REGISTRY, destination=tmp_path)
    assert (tmp_path / "glp1_benchmarks.json").read_bytes() == (
        BUNDLE / "glp1_benchmarks.json"
    ).read_bytes()
    report = load_glp1(REGISTRY, tmp_path)
    assert not report["engine_parameters_updated"]
    assert report["trials"][1]["analyses"][0]["value"] == -14.75
    assert report["trials"][1]["rows"][1]["value"] == 6.5
    assert report["trials"][0]["rows"][0]["sd"] == 10.1
    source = tmp_path / "source"
    shutil.copytree(STORE, source)
    (source / "NCT03548987.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        rebuild_glp1(REGISTRY, source=source, destination=tmp_path)
    (tmp_path / "glp1_benchmarks.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        load_glp1(REGISTRY, tmp_path)


def test_cli_and_canonical_figures(tmp_path):
    evidence = CliRunner().invoke(app, ["evidence", "glp1"])
    assert evidence.exit_code == 0
    assert json.loads(evidence.output)["model_role"] == "benchmark_only"
    result = simulate(REGISTRY, scenario()).to_dict()
    figures = glp1_figures({"simulation": result, "glp1_benchmarks": load_glp1(REGISTRY)})
    assert len(figures) == 5
    assert list(figures["glp1_treatment_stocks"].data[0].y) == [
        r["glp1"]["treatment_stocks"]["never"] for r in result["annual"]
    ]
    reload_result = CliRunner().invoke(
        app, ["data", "rebuild-glp1", "--destination", str(tmp_path)]
    )
    assert reload_result.exit_code == 0
