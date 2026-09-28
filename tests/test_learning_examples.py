import json
from pathlib import Path
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from demeter.analysis.experiments import sampled_parameters, with_values
from demeter.cli import app
from demeter.examples.stock_flow import UNITS, run
from demeter.model import required_units, simulate
from demeter.schema import EvidenceRegistry, Scenario

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")


def test_hand_calculations_and_stock_flow_conservation():
    result = run(REGISTRY)
    assert result["rows"][1]["transfer"] == 12.5
    assert result["rows"][2]["remaining"] == 71.09375
    assert result["rows"][2]["received"] == 28.90625
    for previous, row in zip(result["rows"][:-1], result["rows"][1:], strict=True):
        assert row["remaining"] + row["received"] == pytest.approx(100)
        assert row["remaining"] >= 0 and row["received"] >= 0
        assert previous["remaining"] - row["remaining"] == pytest.approx(row["transfer"])
        assert row["received"] - previous["received"] == pytest.approx(row["transfer"])
    assert result["validation_only"]
    assert result["registry_sha256"] == REGISTRY.content_hash
    assert set(result["parameters"]) == set(UNITS)


@pytest.mark.parametrize("fraction", [0, 0.25, 1])
def test_immediate_response_matches_geometric_solution(fraction):
    registry = with_values(
        REGISTRY,
        {
            "toy_target_fraction": fraction,
            "toy_response_fraction": 1,
        },
    )
    for row in run(registry, steps=40)["rows"]:
        assert row["remaining"] == pytest.approx(100 * (1 - fraction) ** row["tick"])
        assert row["remaining"] + row["received"] == pytest.approx(100)


def test_delayed_response_and_empty_stock():
    delayed = run(REGISTRY, steps=20)
    instant = run(with_values(REGISTRY, {"toy_response_fraction": 1}), steps=20)
    for a, b in zip(delayed["rows"][1:], instant["rows"][1:], strict=True):
        assert a["received"] < b["received"]
    empty = run(with_values(REGISTRY, {"toy_initial_tokens": 0}))
    assert all(row["remaining"] == row["received"] == row["transfer"] == 0 for row in empty["rows"])


@pytest.mark.parametrize("steps", [0, -1, 1001, True, 1.5])
def test_bad_steps_fail(steps):
    with pytest.raises(ValueError, match="steps"):
        run(REGISTRY, steps=steps)


@pytest.mark.parametrize("change", ["missing", "unit", "unresolved", "uncertainty", "bounds"])
def test_invalid_teaching_evidence_fails(change):
    raw = REGISTRY.model_dump()
    p = raw["parameters"]["toy_target_fraction"]
    if change == "missing":
        del raw["parameters"]["toy_target_fraction"]
    elif change == "unit":
        p["unit"] = "hazard_per_year"
    elif change == "unresolved":
        p.update(value=None, unresolved=True)
    elif change == "uncertainty":
        p["uncertainty"] = None
    else:
        # Even changing the registry's declared bound cannot permit stock creation.
        p.update(value=1.1, upper_bound=2)
    with pytest.raises(ValueError):
        run(EvidenceRegistry.model_validate(raw))


def test_toy_cannot_change_active_health_dynamics_or_sampling():
    scenario = Scenario(name="lesson_isolation", years=2, exposures={"upf": 0.7})
    assert not set(UNITS) & required_units(scenario).keys()
    assert not set(UNITS) & set(sampled_parameters(REGISTRY, scenario))
    raw = REGISTRY.model_dump()
    for key in UNITS:
        del raw["parameters"][key]
    original = simulate(REGISTRY, scenario)
    removed = simulate(EvidenceRegistry.model_validate(raw), scenario)
    assert original.annual == removed.annual
    assert original.cohorts == removed.cohorts


def test_copied_module_is_importable_from_cli(tmp_path, monkeypatch):
    source = (ROOT / "examples/tutorial_module.py").read_text(encoding="utf-8")
    (tmp_path / "my_learning_module.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    result = CliRunner().invoke(
        app,
        [
            "simulate",
            str(ROOT / "scenarios/reduce_upf_30.yaml"),
            "--evidence",
            str(ROOT / "evidence/parameters.yaml"),
            "--transition-module",
            "my_learning_module:LearningNull",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    baseline = simulate(REGISTRY, Scenario.from_yaml(ROOT / "scenarios/baseline.yaml"))
    assert payload["cohorts"] == baseline.cohorts
    assert (
        payload["metadata"]["transition_module"]["factory_reference"]
        == "my_learning_module:LearningNull"
    )


def test_learning_notebook_runs_from_clean_output_directory(tmp_path):
    # The notebook itself checks arithmetic, nulls, evidence and backtest boundaries.
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_learning_notebook.py"),
            "--destination",
            str(tmp_path / "lesson"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((tmp_path / "lesson/checks.json").read_text(encoding="utf-8"))
    assert summary["calibration_performed"] is False
    assert summary["module_null_matches_baseline"] and summary["control_deltas_zero"]
    assert (tmp_path / "lesson/report/index.html").is_file()
