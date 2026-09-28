import ast
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest
from SALib.sample import sobol
from typer.testing import CliRunner

from demeter.analysis.experiments import with_values
from demeter.analysis.leverage import (
    SCALE,
    food_reference,
    leverage,
    pathway_game,
    scaled_diet,
    scores,
    shapley_values,
    variance_ranking,
)
from demeter.analysis.leverage_visualization import leverage_figures, render_leverage
from demeter.cli import app
from demeter.health.structure import dietary_pathways
from demeter.model import simulate
from demeter.nutrition.exposures import resolve_diet
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def target(**kwargs):
    return Scenario(name="food_leverage", years=3, exposures={"upf": 0.7}, **kwargs)


def test_shapley_known_interaction_dummy_symmetry_and_order():
    players = ("a", "b", "dummy")
    values = {
        frozenset(s): 10 + 2 * ("a" in s) + 4 * ("b" in s) + 4 * ("a" in s and "b" in s)
        for n in range(4)
        for s in combinations(players, n)
    }
    expected = {"a": 4, "b": 6, "dummy": 0}
    assert shapley_values(players, values) == pytest.approx(expected)
    assert shapley_values(tuple(reversed(players)), values) == pytest.approx(expected)
    assert shapley_values(players, {s: -v for s, v in values.items()}) == pytest.approx(
        {k: -v for k, v in expected.items()}
    )
    with pytest.raises(ValueError, match="every coalition"):
        shapley_values(players, {frozenset(): 0})


@pytest.mark.parametrize("structure", ["legacy", "risk_1", "risk_2"])
@pytest.mark.parametrize("response", ["legacy", "dynamic"])
def test_empty_full_and_hybrid_routing_preserve_endpoints_and_conservation(structure, response):
    s = target(health_structure=structure, diet_response={"kind": response})
    base = food_reference(s)
    paths = tuple(e["flow"] for e in dietary_pathways(s))
    reference = simulate(REGISTRY, base)
    actual = simulate(REGISTRY, s)
    empty = simulate(REGISTRY, s, dietary_reference=base, dietary_paths=())
    full = simulate(REGISTRY, s, dietary_reference=base, dietary_paths=paths)
    assert scores(empty, s) == pytest.approx(scores(reference, base), rel=1e-12)
    assert scores(full, s) == pytest.approx(scores(actual, s), rel=1e-12)
    hybrid = simulate(REGISTRY, s, dietary_reference=base, dietary_paths=paths[:1])
    for row in hybrid.annual:
        assert row["population"] + row["cumulative_deaths"] == pytest.approx(
            hybrid.starting_population
        )
    assert hybrid.metadata["dietary_routing"]["intervention_paths"] == list(paths[:1])
    assert set(hybrid.annual[-1]["routed_base_transition_hazards_per_year"]) == set(
        hybrid.metadata["transition_flows"]
    )
    assert len(paths) == (
        len(hybrid.metadata["transition_flows"])
        if response == "dynamic"
        else (2 if structure == "legacy" else 3)
    )


def test_routing_requires_valid_paths_and_same_nonfood_assumptions():
    s = target()
    base = food_reference(s)
    for paths in (("unknown",), ("healthy_to_ir", "healthy_to_ir")):
        with pytest.raises(ValueError, match="distinct"):
            simulate(REGISTRY, s, dietary_reference=base, dietary_paths=paths)
    with pytest.raises(ValueError, match="both reference"):
        simulate(REGISTRY, s, dietary_paths=())
    with pytest.raises(ValueError, match="identical non-diet"):
        simulate(
            REGISTRY, s, dietary_reference=base.model_copy(update={"years": 4}), dietary_paths=()
        )


def test_food_reference_retains_glp1_and_hybrids_preserve_tagged_population():
    s = target(
        health_structure="risk_1",
        glp1={
            "access_schedule": [
                {
                    "start_year": 1,
                    "access_fraction": 1,
                    "coverage_fraction": 1,
                    "monthly_price_usd": 100,
                    "monthly_copay_usd": 0,
                    "supply_fraction": 0.1,
                }
            ]
        },
    )
    base = food_reference(s)
    assert base.glp1 == s.glp1
    empty = simulate(REGISTRY, s, dietary_reference=base, dietary_paths=())
    ordinary = simulate(REGISTRY, base)
    assert scores(empty, s) == pytest.approx(scores(ordinary, base))
    assert empty.prechronic["future_t2d_entries"] == pytest.approx(
        ordinary.prechronic["future_t2d_entries"]
    )
    with pytest.raises(ValueError, match="identical non-diet"):
        pathway_game(REGISTRY, base.model_copy(update={"glp1": None}), s)


def test_contrast_scaling_preserves_timing_and_validates_full_range():
    s = Scenario.from_yaml("scenarios/diet_dynamics.yaml")
    base = food_reference(s)
    path = resolve_diet(REGISTRY, s)["annual_upf"]
    for scale in (0, 0.5, 1, 1.5):
        actual = resolve_diet(REGISTRY, scaled_diet(REGISTRY, base, s, scale))["annual_upf"]
        assert actual == pytest.approx([1 + scale * (v - 1) for v in path])
    strong = target().model_copy(update={"exposures": {"upf": 0.1}})
    with pytest.raises(ValueError):
        scaled_diet(REGISTRY, food_reference(strong), strong, 1.5)


def test_dummy_recovery_has_no_attribution_even_when_flow_counts_change():
    s = target(health_structure="risk_1", diet_response={"kind": "dynamic"})
    r = with_values(REGISTRY, {"beta_upf_recovery": 0})
    paths, values, allocations = pathway_game(r, food_reference(s), s)
    for metric, rows in allocations.items():
        assert rows["prechronic_to_healthy"] == 0
        assert rows["prediabetes_to_prechronic"] == 0
        assert sum(rows.values()) == pytest.approx(
            values[frozenset(paths)][metric] - values[frozenset()][metric]
        )


def test_sobol_estimator_against_known_linear_variance():
    problem = {"num_vars": 2, "names": ["h_to_ir_rate", "ir_to_h_rate"], "bounds": [[0, 1], [0, 1]]}
    x = sobol.sample(problem, 1024, calc_second_order=False, seed=12)
    report = variance_ranking(REGISTRY, problem, x[:, 0] + 2 * x[:, 1], seed=12)
    by_key = {r["parameter"]: r for r in report["indices"]}
    assert by_key["h_to_ir_rate"]["total_order"] == pytest.approx(0.2, abs=0.01)
    assert by_key["ir_to_h_rate"]["total_order"] == pytest.approx(0.8, abs=0.01)
    zero = variance_ranking(REGISTRY, problem, np.zeros(len(x)), seed=12)
    assert zero["status"] == "zero_variance" and zero["indices"] == []


@pytest.fixture(scope="module")
def report():
    return leverage(
        REGISTRY,
        target(health_structure="risk_1", diet_response={"kind": "dynamic"}),
        draws=2,
        samples=8,
        seed=23,
    )


def test_complete_contract_reconciles_and_separates_evidence(report):
    json.dumps(report, allow_nan=False)
    assert not report["scientific_release_ready"]
    assert len(report["attribution"]["coalitions"]) == 32
    for metric, outcome in report["outcomes"].items():
        rows = report["attribution"]["by_outcome"][metric]
        assert sum(r["nominal"] for r in rows) == pytest.approx(outcome["absolute_delta"])
        assert report["attribution"]["max_draw_residual"][metric] < 1e-7
        assert (
            outcome["delta_interval"]["p2_5"]
            <= outcome["delta_interval"]["median"]
            <= outcome["delta_interval"]["p97_5"]
        )
        for scope in ("intervention_level", "paired_delta"):
            assert SCALE in [
                r["parameter"] for r in report["sensitivity"][metric][scope]["indices"]
            ]
        assert report["structural_experiments"][0]["paired_delta"][metric] == pytest.approx(0)
    assert report["priority_evidence_gaps"]["healthspan"]
    assert report["direct_versus_mediated"]["direct_food_to_mortality"]["empirical_effect"] is None
    assert not report["historical"]["scientific_validation_of_diet"]
    assert not report["historical"]["integrated_health_model_validated"]
    assert any(
        r["exposure"] == "fiber"
        for r in report["unranked_structural_gaps"]["inactive_food_exposures"]
    )


def test_reproducibility_and_no_change_delta_is_not_fictitious_ranking():
    s = target()
    a = leverage(REGISTRY, s, draws=2, samples=8, seed=3)
    assert a == leverage(REGISTRY, s, draws=2, samples=8, seed=3)
    zero = leverage(REGISTRY, food_reference(s), draws=2, samples=8, seed=3)
    for metric in zero["units"]:
        assert zero["outcomes"][metric]["absolute_delta"] == 0
        assert zero["sensitivity"][metric]["paired_delta"]["status"] == "zero_variance"
        assert zero["outcomes"][metric]["delta_interval"] == {"median": 0, "p2_5": 0, "p97_5": 0}


def test_invalid_sampling_contract_and_controls_fail():
    r = REGISTRY.model_copy(deep=True)
    r.parameters[SCALE].model_role = "health_model"
    with pytest.raises(ValueError, match="analysis-only"):
        leverage(r, target(), draws=2, samples=8)
    with pytest.raises(ValueError, match="power-of-two"):
        leverage(REGISTRY, target(), draws=2, samples=7)
    r = REGISTRY.model_copy(deep=True)
    r.parameters[SCALE].uncertainty.kind = "interval"
    with pytest.raises(ValueError, match="independent uniform"):
        leverage(r, target(), draws=2, samples=8)


def test_figures_are_canonical_and_renderer_contains_no_engine_imports(report, tmp_path):
    figures = leverage_figures(report)
    assert len(figures) == 26
    assert list(figures["attribution_healthspan"].data[1].x) == [
        r["nominal"] for r in report["attribution"]["by_outcome"]["healthspan"]
    ]
    assert list(figures["comparison_healthspan"].data[1].y) == [
        r["healthspan"] for r in report["trajectories"]["intervention"]
    ]
    assert render_leverage(report, tmp_path)["offline"]
    assert json.loads((tmp_path / "diagnostics.json").read_text()) == report
    tree = ast.parse(Path("src/demeter/analysis/leverage_visualization.py").read_text())
    forbidden = ("demeter.model", "demeter.analysis.leverage", "demeter.health", "demeter.schema")
    assert not any(
        isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(forbidden)
        for node in ast.walk(tree)
    )


def test_cli_writes_reusable_json_and_offline_report(tmp_path):
    path = tmp_path / "scenario.yaml"
    path.write_text("name: cli_leverage\nyears: 2\nexposures: {upf: 0.7}\n")
    result = CliRunner().invoke(
        app,
        [
            "leverage",
            "--scenario",
            str(path),
            "--draws",
            "2",
            "--samples",
            "8",
            "--destination",
            str(tmp_path / "report"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["figures"] == 26
    data = json.loads((tmp_path / "report/diagnostics.json").read_text())
    assert data["kind"] == "demeter_leverage"
