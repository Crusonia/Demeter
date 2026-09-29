from copy import deepcopy
import json

import pytest

from demeter.analysis.chart_evidence import chart_evidence, evidence_html
from demeter.analysis.observability import observe
from demeter.analysis.teaching import guide_for, guide_html
from demeter.analysis.visualization import build_figures
from demeter.schema import EvidenceRegistry, Scenario


@pytest.fixture(scope="module")
def saved():
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    payload = observe(registry, Scenario(name="evidence", years=1), draws=2, samples=8)
    registry.datasets["us_population"]["source"] = "Changed after this run"
    return payload


def test_chart_sources_exclude_unused_registry_and_select_real_arrow_inputs(saved):
    context = chart_evidence(saved, "dependencies")
    active = saved["simulation"]["metadata"]["active_parameters"]
    assert {p["key"] for p in context["parameters"]} == set(active)
    arrow = next(m for m in context["mechanisms"] if m["label"] == "upf_exposure → lagged_response")
    assert arrow["parameters"] == ["beta_upf_progression", "diet_lag_years"]
    arithmetic = next(
        m for m in context["mechanisms"] if m["label"] == "mortality_schedule → life_expectancy"
    )
    assert arithmetic["parameters"] == [] and "does not establish" in arithmetic["note"]
    assert not any(p["key"].startswith("nhanes_") for p in context["parameters"])
    population = next(s for s in context["sources"] if s["key"] == "us_population")
    assert "Changed after" not in population["record"]["source"]
    receipts = saved["evidence_context"]["baseline_sources"]
    assert set(receipts) == {"census_2025.csv", "nchs_2024_all.xlsx"}


def test_parameter_and_sensitivity_context_do_not_claim_to_be_all_dependencies(saved):
    context = chart_evidence(saved, "parameter_diet_lag_years")
    assert [p["key"] for p in context["parameters"]] == ["diet_lag_years"]
    assert context["sources"] == [] and context["mechanisms"] == []
    sensitivity = chart_evidence(saved, "sensitivity")
    assert [p["key"] for p in sensitivity["parameters"]] == [
        r["parameter"] for r in saved["sensitivity"]["indices"]
    ]
    assert "Fixed background inputs" in sensitivity["note"]
    response = chart_evidence(saved, "diet_response")
    assert [p["key"] for p in response["parameters"]] == ["beta_upf_progression", "diet_lag_years"]
    assert chart_evidence(saved, "diet_duration")["parameters"] == []


def test_historical_evidence_is_its_own_observation_not_model_coefficients(saved):
    context = chart_evidence(saved, "history_e0_both_sexes")
    assert context["parameters"] == [] and context["mechanisms"] == []
    assert len(context["sources"]) == 1
    row = context["sources"][0]["record"]
    assert row["population"] == "U.S., all races, Both Sexes"
    assert row["unit"] == "years"
    assert row["receipt"] == saved["historical"]["metadata"]["sources"]["nchs_life_expectancy.csv"]
    assert "forecasts are derived" in row["status"]


def test_trials_and_lag_challenge_keep_benchmark_scope(saved):
    from demeter.data.glp1 import load_glp1
    from demeter.analysis.diet_response import historical_lag_challenge

    payload = deepcopy(saved)
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    payload["glp1_benchmarks"] = load_glp1(registry)
    trial = chart_evidence(payload, "glp1_trial_benchmarks")
    assert trial["parameters"] == []
    assert len(trial["sources"]) == 2
    for row in trial["sources"]:
        assert row["record"]["eligibility"] and row["record"]["timeframe"]
        assert len(row["record"]["uncertainty"]) == 1
        assert row["record"]["uncertainty"][0]["estimand"] == "Treatment policy estimand"
    payload["diet_lag_challenge"] = historical_lag_challenge(registry)
    challenge = chart_evidence(payload, "diet_lag_challenge")
    assert [p["key"] for p in challenge["parameters"]] == ["diet_lag_years"]
    assert "shortcut" in challenge["scope"]


def test_missing_source_snapshot_or_custom_dependencies_are_not_reinvented(saved):
    payload = deepcopy(saved)
    payload.pop("evidence_context")
    structure = payload["simulation"]["diagnostics"]["structure"]
    structure["dependencies"] = []
    structure["interpretation"] = "Custom equation dependencies are not inferred"
    context = chart_evidence(payload, "dependencies")
    assert context["mechanisms"] == []
    assert any("older run" in s for s in context["unresolved"])
    assert structure["interpretation"] in context["unresolved"]


def test_context_and_offline_renderer_only_use_saved_data_and_escape_text(saved, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Rendering must not read a live registry or run a model")

    monkeypatch.setattr(EvidenceRegistry, "from_yaml", forbidden)
    monkeypatch.setattr("demeter.model.simulate", forbidden)
    original = json.dumps(saved, sort_keys=True)
    for name in build_figures(saved):
        assert "Evidence for this chart" in evidence_html(chart_evidence(saved, name))
    assert json.dumps(saved, sort_keys=True) == original
    context = chart_evidence(saved, "parameter_diet_lag_years")
    context["parameters"][0].update(
        source_url="javascript:alert(1)", notes='<img src=x onerror="alert(1)">'
    )
    rendered = evidence_html(context)
    assert 'href="javascript:' not in rendered and "<img" not in rendered
    assert "&lt;img" in rendered
    assert json.dumps(saved, sort_keys=True) == original


def test_guided_exercises_and_legacy_content():
    guide = guide_for("dependencies")
    assert all(guide[k] for k in ("predict", "challenge", "evidence"))
    assert "What evidence would change" in guide_html("dependencies")
    legacy = {"*": {k: guide[k] for k in ("question", "read", "mechanism", "try", "limit")}}
    assert "Predict before running" not in guide_html("old", legacy)
    assert guide_for("old", legacy) == legacy["*"]
