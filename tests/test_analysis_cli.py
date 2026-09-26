import json

import pytest
from typer.testing import CliRunner

from demeter.analysis.experiments import compare, sensitivity, uncertainty
from demeter.analysis.validation import mortality_backtest
from demeter.cli import app
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
SCENARIO = Scenario(name="fixture", years=2, exposures={"upf": 0.7})


def test_paired_uncertainty_is_reproducible_and_zero_effect_is_zero():
    a = uncertainty(REGISTRY, SCENARIO, draws=4, seed=12)
    assert a == uncertainty(REGISTRY, SCENARIO, draws=4, seed=12)
    zero = uncertainty(REGISTRY, Scenario(name="zero", years=2, exposures={}), draws=4, seed=12)
    for summary in zero["paired_deltas"].values():
        assert summary == {"median": 0, "p2_5": 0, "p97_5": 0}


def test_sobol_executes_with_finite_indices():
    result = sensitivity(REGISTRY, SCENARIO, samples=8, seed=4)
    json.dumps(result, allow_nan=False)
    assert result["model_evaluations"] > 8
    assert len(result["indices"]) == 7


def test_comparison_rejects_different_horizons():
    with pytest.raises(ValueError, match="same horizon"):
        compare(REGISTRY, SCENARIO, Scenario(name="other", years=3, exposures={}))


def test_historical_backtest_uses_only_training_schedule_for_prediction():
    a = mortality_backtest(2022, 2023)
    b = mortality_backtest(2022, 2024)
    assert a["predicted_e0"] == b["predicted_e0"]
    assert a["observed_e0"] != b["observed_e0"]
    assert not a["holdout_used_in_prediction"]
    assert not a["scientific_validation_of_diet"]


@pytest.mark.parametrize(
    "command",
    [
        ["validate"],
        ["evidence", "audit"],
        ["backtest"],
        ["simulate", "scenarios/baseline.yaml"],
        ["compare", "scenarios/baseline.yaml", "scenarios/reduce_upf_30.yaml"],
    ],
)
def test_cli_json_outputs(command):
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    assert isinstance(json.loads(result.output), dict)


def test_scientific_release_gate_fails_explicitly():
    result = CliRunner().invoke(app, ["validate", "--scientific-required"])
    assert result.exit_code == 1
    assert json.loads(result.output)["scientific_release_ready"] is False


def test_required_sensitivity_cli_accepts_positional_outcome():
    result = CliRunner().invoke(app, ["sensitivity", "life_expectancy", "--samples", "8"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["outcome"] == "life_expectancy"
