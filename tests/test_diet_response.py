import json
import shutil
from math import exp, expm1

import numpy as np
import pytest
from typer.testing import CliRunner

from demeter.analysis.diet_response import historical_lag_challenge, timing_sensitivity
from demeter.analysis.experiments import sampled_parameters, uncertainty, with_values
from demeter.analysis.observability import observe
from demeter.analysis.visualization import build_figures
from demeter.cli import app
from demeter.data.diet_response import DATASET, STORE, load_challenge, rebuild_challenge
from demeter.data.ingest import BUNDLE
from demeter.health.structure import rates_for
from demeter.model import simulate
from demeter.nutrition.exposures import resolve_diet
from demeter.nutrition.response import DietaryResponse, TIMING_KEYS, dose_shape, relax
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def dynamic(**kwargs):
    return Scenario.model_validate(
        {
            "name": "timing",
            "years": 6,
            "health_structure": "risk_1",
            "diet_response": {"kind": "dynamic"},
            "upf_schedule": [
                {"start_year": 2, "value": 0.7, "unit": "relative_exposure"},
                {"start_year": 5, "value": 1, "unit": "relative_exposure"},
            ],
            **kwargs,
        }
    )


def test_single_lag_analytic_solution_and_time_step_semigroup():
    s = Scenario(name="legacy")
    response = DietaryResponse(REGISTRY, s)
    for year in range(1, 6):
        state = response.advance(0.7)
        assert response.snapshot() == state
        expected = (
            REGISTRY.value("beta_upf_progression")
            * (-0.3)
            * (1 - exp(-year / REGISTRY.value("diet_lag_years")))
        )
        assert state["applied_progression_multiplier"] == pytest.approx(exp(expected))
        assert state["applied_recovery_multiplier"] == 1
    for value in (-0.3, 0.5):
        once = relax(0, value, 2, 1)
        fine = 0
        for _ in range(12):
            fine = relax(fine, value, 2, 1 / 12)
        assert fine == pytest.approx(once, rel=1e-13)


def test_dynamic_exact_filters_and_step_refinement():
    s = dynamic(upf_schedule=[])
    one, fine = DietaryResponse(REGISTRY, s), DietaryResponse(REGISTRY, s)
    state = one.advance(0.7)
    for _ in range(12):
        small = fine.advance(0.7, dt=1 / 12)
    assert small == pytest.approx(state, abs=1e-13)
    assert state["fast_response"] == pytest.approx(
        -0.3 * (-expm1(-1 / REGISTRY.value("diet_improvement_lag_years")))
    )
    assert state["retained_exposure"] == pytest.approx(
        -0.3 * (-expm1(-1 / REGISTRY.value("diet_memory_years")))
    )
    assert state["recovery_response"] == pytest.approx(
        0.3 * (-expm1(-1 / REGISTRY.value("diet_recovery_lag_years")))
    )


def test_dose_shapes_saturate_without_threshold_or_discontinuity():
    assert dose_shape(0, "saturating", 0.3) == 0
    assert dose_shape(0.3, "saturating", 0.3) == pytest.approx(0.15)
    assert dose_shape(-0.3, "saturating", 0.3) == pytest.approx(-0.15)
    assert abs(dose_shape(1e6, "saturating", 0.3)) < 0.3
    assert dose_shape(1e-9, "saturating", 0.3) / 1e-9 == pytest.approx(1)
    assert dose_shape(0.6, "linear") == 0.6
    with pytest.raises(ValueError):
        dose_shape(0.3, "saturating", 0)


def test_duration_memory_and_withdrawal_are_reversible_not_instantaneous():
    s = dynamic(upf_schedule=[])
    short, long = DietaryResponse(REGISTRY, s), DietaryResponse(REGISTRY, s)
    recent = short.advance(0.7)
    for _ in range(5):
        sustained = long.advance(0.7)
    assert sustained["retained_exposure"] < recent["retained_exposure"] < 0
    after = long.advance(1)
    assert sustained["retained_exposure"] < after["retained_exposure"] < 0
    assert after["applied_progression_multiplier"] < 1 < after["applied_recovery_multiplier"]
    assert after["cumulative_exposure_years"] == pytest.approx(-1.5)
    for _ in range(300):
        after = long.advance(1)
    assert after["applied_progression_multiplier"] == pytest.approx(1, abs=1e-12)
    assert after["applied_recovery_multiplier"] == pytest.approx(1, abs=1e-12)
    assert after["cumulative_exposure_years"] == pytest.approx(-1.5)
    # Opposite signed exposures may cancel in the signed integral, never in absolute duration.
    r = DietaryResponse(REGISTRY, s)
    r.advance(0.7)
    record = r.advance(1.3)
    assert record["cumulative_exposure_years"] == pytest.approx(0)
    assert record["cumulative_absolute_exposure_years"] == pytest.approx(0.6)


@pytest.mark.parametrize("structure", ["legacy", "risk_1", "risk_2"])
def test_schedule_delay_conservation_and_reverse_flows(structure):
    s = dynamic(health_structure=structure)
    result = simulate(REGISTRY, s, diagnostics=True)
    base = simulate(REGISTRY, dynamic(health_structure=structure, upf_schedule=[]))
    assert result.annual[0] == base.annual[0]
    assert {k: result.annual[1][k] for k in base.annual[1]} == base.annual[1]
    assert result.annual[2]["relative_upf"] == 0.7
    assert 0 < result.annual[2]["applied_progression_multiplier"] < 1
    assert result.annual[2]["applied_recovery_multiplier"] > 1
    assert result.annual[5]["relative_upf"] == 1
    assert result.annual[5]["applied_progression_multiplier"] < 1
    assert result.ending_population + result.cumulative_deaths == pytest.approx(
        result.starting_population, abs=1e-5
    )
    assert result.validation_only
    edges = result.diagnostics["structure"]["dependencies"]
    reverse = "ir_to_healthy" if structure == "legacy" else "prechronic_to_healthy"
    assert any(e["source"] == "recovery_response" and e["target"] == reverse for e in edges)
    # Recovery changes its own baseline hazard; it is not forced to inverse progression.
    a = rates_for(REGISTRY, s, 0.8, 1.1)
    b = rates_for(REGISTRY, s, 1, 1)
    assert a[1] / b[1] == pytest.approx(1.1)


def test_absolute_and_relative_paths_agree_and_preserve_source_units():
    relative = dynamic()
    absolute = dynamic(
        upf_schedule=[
            {
                "start_year": 2,
                "value": 37.1,
                "unit": "percent_energy",
                "reference_period": "2021_2023",
            },
            {
                "start_year": 5,
                "value": 53,
                "unit": "percent_energy",
                "reference_period": "2021_2023",
            },
        ]
    )
    assert resolve_diet(REGISTRY, relative)["annual_upf"] == pytest.approx(
        resolve_diet(REGISTRY, absolute)["annual_upf"]
    )
    a, b = simulate(REGISTRY, relative), simulate(REGISTRY, absolute)
    assert a.ending_state_shares == pytest.approx(b.ending_state_shares)
    assert b.metadata["dietary_exposures"]["schedule"][0]["reference"]["source"]


def test_invalid_schedule_and_later_extrapolation_fail_before_execution():
    step = {"start_year": 2, "value": 0.7, "unit": "relative_exposure"}
    for config in (
        {"upf_schedule": [step, step]},
        {"upf_schedule": [{**step, "start_year": 7}]},
        {"upf_schedule": [{**step, "start_year": 0}]},
        {"upf_schedule": [{**step, "value": float("nan")}]},
        {"exposures": {"upf": 1}},
        {"upf_schedule": [{**step, "unit": "percent_energy"}]},
        {"upf_schedule": [{**step, "reference_period": "2021_2023"}]},
        {"diet_response": {"kind": "legacy", "shape": "saturating"}},
    ):
        with pytest.raises(ValueError):
            dynamic(**config)
    s = dynamic(upf_schedule=[step, {**step, "start_year": 6, "value": 0.2}])
    with pytest.raises(ValueError, match="envelope"):
        simulate(REGISTRY, s)
    assert simulate(REGISTRY, s.model_copy(update={"allow_extrapolation": True})).metadata[
        "extrapolation"
    ]
    with pytest.raises(ValueError, match="physical range"):
        simulate(
            REGISTRY,
            dynamic(
                upf_schedule=[
                    {
                        **step,
                        "value": 101,
                        "unit": "percent_energy",
                        "reference_period": "2021_2023",
                    }
                ],
                allow_extrapolation=True,
            ),
        )


def test_active_timing_parameters_are_sampled_and_paired_baseline_clears_schedule():
    s = dynamic()
    assert set(TIMING_KEYS) <= set(sampled_parameters(REGISTRY, s))
    assert "diet_memory_years" not in sampled_parameters(REGISTRY, Scenario(name="legacy"))
    assert "diet_half_saturation" not in sampled_parameters(REGISTRY, s)
    report = uncertainty(REGISTRY, s, draws=2, seed=42)
    assert report["paired_deltas"]["healthspan"]["median"] > 0
    unchanged = uncertainty(REGISTRY, dynamic(upf_schedule=[]), draws=2, seed=42)
    assert all(v == 0 for metric in unchanged["paired_deltas"].values() for v in metric.values())
    null = with_values(REGISTRY, {"beta_upf_progression": 0, "beta_upf_recovery": 0})
    a, b = simulate(null, s), simulate(null, dynamic(upf_schedule=[]))
    assert a.ending_state_shares == b.ending_state_shares
    assert a.annual[-1]["healthspan"] == b.annual[-1]["healthspan"]


def test_invalid_timing_rejected_and_scientific_mode_stays_blocked():
    for key in TIMING_KEYS:
        bad = with_values(REGISTRY, {key: 0})
        with pytest.raises(ValueError, match="positive"):
            simulate(bad, dynamic())
    with pytest.raises(ValueError, match="Scientific mode blocked"):
        simulate(REGISTRY, dynamic(mode="scientific"))


def test_timing_sensitivity_is_conditional_reproducible_and_includes_washout():
    a = timing_sensitivity(REGISTRY, dynamic(), samples=8, seed=12)
    b = timing_sensitivity(REGISTRY, dynamic(), samples=8, seed=12)
    assert a == b
    assert {r["parameter"] for r in a["timing_ranking"]} == set(TIMING_KEYS)
    assert "beta_upf_progression" in a["conditional_on_fixed_parameters"]
    assert a["outcome"] == "healthspan"
    assert all(np.isfinite(r["total_order"]) for r in a["indices"])


def test_conditional_timing_analysis_holds_unselected_intervals_fixed():
    raw = REGISTRY.model_dump()
    raw["parameters"]["diet_memory_years"]["uncertainty"] = {
        "kind": "fixed",
        "rationale": "Test conditioning choice",
    }
    raw["parameters"]["beta_upf_progression"]["uncertainty"]["kind"] = "interval"
    registry = EvidenceRegistry.model_validate(raw)
    report = timing_sensitivity(registry, dynamic(), samples=8, seed=12)
    assert "diet_memory_years" not in report["sampled_parameters"]
    assert "beta_upf_progression" in report["conditional_on_fixed_parameters"]


def test_historical_challenge_reloads_offline_exposes_failed_shortcut_and_does_not_fit(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **kw: pytest.fail("No network in reconstruction")
    )
    rebuild_challenge(REGISTRY, destination=tmp_path)
    for name in ("diet_response_challenge.json", "diet_response_manifest.json"):
        assert (tmp_path / name).read_bytes() == (BUNDLE / name).read_bytes()
    source = load_challenge(REGISTRY)
    assert len(source["facts"]["rows"]) == 8
    assert all(row["passed"] for row in source["corroboration"])
    before = REGISTRY.content_hash
    report = historical_lag_challenge(REGISTRY)
    assert report["point_trajectory_contradicts_shortcut"]
    assert not report["lag_identified"] and not report["engine_parameters_updated"]
    assert not report["scientific_release_ready"]
    assert all(
        not row["t2d_remission_path_present"] for row in report["engine_structure_check"].values()
    )
    assert all(c["rows"][0]["descriptive_residual"] == 0 for c in report["curves"])
    assert report["observed_contrasts"][-1]["difference_percentage_points"] == pytest.approx(5.3)
    assert REGISTRY.content_hash == before


def test_challenge_source_or_definition_drift_fails(tmp_path):
    shutil.copytree(STORE, tmp_path / "source")
    (tmp_path / "source" / "look-ahead-extract.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        rebuild_challenge(REGISTRY, tmp_path / "source", tmp_path / "out")
    bad = REGISTRY.model_copy(deep=True)
    bad.datasets[DATASET]["years"] = [1, 4]
    with pytest.raises(ValueError, match="checksum"):
        load_challenge(bad)


def test_observability_and_cli_keep_response_and_historical_failures_visible(tmp_path):
    payload = observe(REGISTRY, dynamic(), draws=2, samples=8, seed=12)
    figures = build_figures(payload)
    assert (
        set(("diet_response", "diet_duration", "diet_memory", "diet_timing", "diet_lag_challenge"))
        <= figures.keys()
    )
    assert list(figures["diet_response"].data[1].y) == [
        r["applied_progression_multiplier"] for r in payload["simulation"]["annual"]
    ]
    assert list(figures["diet_lag_challenge"].data[0].y) == [
        r["normalized"] for r in payload["diet_lag_challenge"]["observed_contrasts"]
    ]
    output = tmp_path / "challenge.json"
    run = CliRunner().invoke(app, ["diet-lag-challenge", "--output", str(output)])
    assert run.exit_code == 0, run.output
    assert json.loads(output.read_text())["point_trajectory_contradicts_shortcut"]
