import json
import shutil

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from demeter.analysis.experiments import (
    compare,
    sampled_parameters,
    sensitivity,
    uncertainty,
    with_values,
)
from demeter.analysis.observability import observe
from demeter.analysis.visualization import build_figures
from demeter.cli import app
from demeter.data.ingest import BUNDLE
from demeter.data.prechronic import (
    DATASET,
    DIAGNOSES,
    STORE,
    classify,
    load_prechronic,
    rebuild_prechronic,
    survey_count,
)
from demeter.health.structure import PRECHRONIC_STATES, prechronic_transitions
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def scenario(**kwargs):
    return Scenario(name="test", years=3, health_structure="risk_1", exposures={}, **kwargs)


def sample():
    rows = []
    for _ in range(8):
        row = {
            "DIQ010": 2,
            "LBXGH": 5,
            "LBXGLU": 90,
            "RIAGENDR": 1,
            "BMXWAIST": 90,
            "LBDHDD": 60,
            "LBXTR": 100,
            **dict.fromkeys(DIAGNOSES, 2),
        }
        row.update({f"BPXOSY{j}": 110 for j in (1, 2, 3)})
        row.update({f"BPXODI{j}": 70 for j in (1, 2, 3)})
        rows.append(row)
    f = pd.DataFrame(rows, dtype=float)
    f.loc[1:, "BMXWAIST"] = 110
    f.loc[2, "LBDHDD"] = 30
    f.loc[3, "LBXGH"] = 5.8
    f.loc[4, "LBXGLU"] = 130
    f.loc[5, "BPQ020"] = 1
    f.loc[6, "MCQ160B"] = 9
    f.loc[7, "BPXOSY3"] = np.nan
    return f


def test_candidate_definitions_are_nonglycemic_disjoint_and_missing_is_not_healthy():
    a = REGISTRY.datasets[DATASET]["analysis"]
    ga = REGISTRY.datasets["nhanes_glycemic_prevalence"]["analysis"]
    one, two = [classify(sample(), a, ga, k) for k in ("risk_1", "risk_2")]
    assert one.iloc[:6].tolist() == [
        "lower_measured_risk",
        "prechronic_candidate",
        "prechronic_candidate",
        "prediabetes",
        "diabetes_any_type",
        "other_reported_diagnosis",
    ]
    assert one.iloc[6:].isna().all()
    assert two[1] == "lower_measured_risk" and two[2] == "prechronic_candidate"
    f = sample().iloc[:1].copy()
    f.loc[0, ["BPXOSY1", "BPXOSY2", "BPXOSY3"]] = 130
    f.loc[0, ["BPXODI1", "BPXODI2", "BPXODI3"]] = 85
    assert classify(f, a, ga, "risk_1")[0] == "prechronic_candidate"
    assert classify(f, a, ga, "risk_2")[0] == "lower_measured_risk"  # BP is one marker.


def test_survey_total_preserves_design_and_scales_people_and_uncertainty():
    f = pd.DataFrame(
        {"SDMVSTRA": [1, 1, 2, 2], "SDMVPSU": [1, 2, 1, 2], "WTSAFPRP": [10.0, 20, 30, 40]}
    )
    mask = pd.Series([True, False, True, False])
    result = survey_count(f, mask, 0.95)
    assert result["estimate"] == 40
    assert result["standard_error"] == pytest.approx(np.sqrt(1000))
    f.WTSAFPRP *= 10
    scaled = survey_count(f, mask, 0.95)
    assert scaled["estimate"] == 400
    assert scaled["standard_error"] == pytest.approx(result["standard_error"] * 10)
    assert scaled["interval"]["high"] == pytest.approx(result["interval"]["high"] * 10)


def test_competing_exits_no_within_step_cascade_and_zero_rates():
    stock = np.array([[100.0, 50, 20, 10]])
    zero, flows = prechronic_transitions(stock, *([0] * 5), adult_age=0)
    np.testing.assert_array_equal(zero, stock)
    assert all(v == 0 for v in flows.values())
    output, flows = prechronic_transitions(stock, *([100.0] * 5), adult_age=0, by_row=True)
    assert output.min() >= 0
    assert output.sum() == pytest.approx(stock.sum())
    assert flows["prechronic_to_healthy"] + flows["prechronic_to_prediabetes"] <= 50
    assert flows["prediabetes_to_prechronic"] + flows["prediabetes_to_t2d"] <= 20
    only_h = np.array([[100.0, 0, 0, 0]])
    output, flows = prechronic_transitions(only_h, *([100.0] * 5), adult_age=0)
    assert output[0, 2] == output[0, 3] == 0
    assert output[0, 1] == pytest.approx(100)
    with pytest.raises(ValueError):
        prechronic_transitions(stock, 0, 0, -1, 0, 0, adult_age=0)


@pytest.mark.parametrize("definition", ["risk_1", "risk_2"])
def test_four_state_conservation_lifetime_accounting_and_tagged_burden(definition):
    result = simulate(
        REGISTRY,
        Scenario(name="long", years=100, health_structure=definition, exposures={}),
        diagnostics=True,
    )
    assert result.ending_population + result.cumulative_deaths == pytest.approx(
        result.starting_population
    )
    assert set(result.ending_state_shares) == set(PRECHRONIC_STATES)
    report = result.healthspan["restricted_cohort"]
    initial = result.prechronic["initial_prechronic_cohort"]
    for row in result.annual:
        assert row["population"] + row["cumulative_deaths"] == pytest.approx(
            result.starting_population
        )
        assert sum(row[s] for s in PRECHRONIC_STATES) == pytest.approx(row["population"])
        assert sum(row["state_life_expectancy"].values()) == pytest.approx(row["life_expectancy"])
        assert 0 <= row["t2d_incidence_from_initial_prechronic"] <= row["cumulative_t2d_incidence"]
    for s in PRECHRONIC_STATES:
        assert 0 <= initial["state_person_years"][s] <= report["state_person_years"][s]
    assert result.prechronic["future_t2d_entries"] == pytest.approx(
        sum(c["cumulative_transitions"]["prediabetes_to_t2d"] for c in initial["by_initial_age"])
    )
    assert result.prechronic["future_t2d_entries"] <= sum(
        c["initial_population"] for c in initial["by_initial_age"]
    )
    assert result.annual[1]["t2d_incidence_from_initial_prechronic"] == 0
    assert "prechronic_years" not in result.healthspan["definition"]["unavailable"]


def test_no_initial_prechronic_is_zero_tagged_burden_and_no_division_error():
    registry = with_values(REGISTRY, {"initial_pc_fraction_risk_1": 0})
    result = simulate(registry, scenario())
    assert result.prechronic["future_t2d_entries"] == 0
    assert all(
        v is None
        for v in result.prechronic["initial_prechronic_cohort"][
            "state_years_per_initial_person"
        ].values()
    )


def test_pairing_structure_guard_and_new_parameter_sampling():
    s = scenario()
    result = uncertainty(REGISTRY, s, draws=4, seed=42)
    assert "h_to_pc_rate" in result["sampled_parameters"]
    assert "h_to_ir_rate" not in sampled_parameters(REGISTRY, s)
    assert all(v == 0 for d in result["paired_deltas"].values() for v in d.values())
    assert (
        result["outcomes"]["prechronic_years"]["p97_5"]
        > result["outcomes"]["prechronic_years"]["p2_5"]
    )
    with pytest.raises(ValueError, match="structure"):
        compare(REGISTRY, s, s.model_copy(update={"health_structure": "risk_2"}))
    change = compare(REGISTRY, s, s.model_copy(update={"exposures": {"upf": 0.7}}))
    assert "prechronic_to_prediabetes" in change["transition_deltas"]
    assert "prechronic" in change["state_time_deltas"]
    assert change["outcomes"]["cumulative_t2d_incidence"]["absolute_delta"] < 0
    assert sensitivity(REGISTRY, s, "prechronic_years", samples=8)["indices"]


def test_offline_benchmark_rebuild_corruption_and_definition_checks(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: pytest.fail("Must be offline"))
    rebuild_prechronic(REGISTRY, destination=tmp_path)
    for name in ("prechronic_prevalence.json", "prechronic_manifest.json"):
        assert (tmp_path / name).read_bytes() == (BUNDLE / name).read_bytes()
    report = load_prechronic(REGISTRY)
    one, two = report["definitions"]
    for a, b in zip(one["domains"], two["domains"], strict=True):
        assert a["complete_n"] == b["complete_n"]
        assert sum(v["proportion"]["estimate"] for v in a["states"].values()) == pytest.approx(1)
        assert (
            a["states"]["prechronic_candidate"]["count"]["estimate"]
            >= b["states"]["prechronic_candidate"]["count"]["estimate"]
        )
    raw = REGISTRY.model_dump()
    raw["datasets"][DATASET]["analysis"]["waist_male_cm"] = 100
    with pytest.raises(ValueError, match="checksum"):
        load_prechronic(EvidenceRegistry.model_validate(raw))
    shutil.copyfile(STORE / "manifest.json", tmp_path / "manifest.json")
    (tmp_path / "P_BMX.xpt").write_bytes(b"bad")
    with pytest.raises(ValueError, match="checksum"):
        rebuild_prechronic(REGISTRY, source=tmp_path, destination=tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_cli_and_observability_keep_prechronic_visible(tmp_path):
    run = CliRunner().invoke(
        app,
        [
            "healthspan",
            "scenarios/prechronic_baseline.yaml",
            "--output",
            str(tmp_path / "report.json"),
        ],
    )
    assert run.exit_code == 0, run.output
    report = json.loads((tmp_path / "report.json").read_bytes())
    assert report["definition"]["candidate_definition"] == "risk_1"
    assert report["validation_only"]
    run = CliRunner().invoke(app, ["evidence", "prechronic"])
    assert run.exit_code == 0
    payload = observe(REGISTRY, scenario(), draws=2, samples=8)
    figures = build_figures(payload)
    assert "cohort_prechronic" in figures
    assert "uncertainty_prechronic_years" in figures
    assert "prechronic" in [t.name for t in figures["stocks"].data]


def test_new_structure_cannot_enable_scientific_mode():
    with pytest.raises(ValueError, match="Scientific mode blocked"):
        simulate(REGISTRY, scenario(mode="scientific"))
    with pytest.raises(ValueError):
        Scenario(name="bad", exposures={}, health_structure="unregistered")
