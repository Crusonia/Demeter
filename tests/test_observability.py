import ast
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.analysis.experiments import uncertainty
from demeter.analysis.observability import observe
from demeter.analysis.visualization import build_figures, render_report
from demeter.cli import app
from demeter.model import REQUIRED_UNITS, simulate
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
SCENARIO = Scenario(name="instrumentation", years=2, exposures={"upf": 0.7})


@pytest.fixture(scope="module")
def payload():
    return observe(REGISTRY, SCENARIO, draws=4, samples=8, seed=12)


def test_instrumentation_preserves_dynamics_and_conservation():
    plain = simulate(REGISTRY, SCENARIO)
    detailed = simulate(REGISTRY, SCENARIO, diagnostics=True)
    assert plain.ending_population == detailed.ending_population
    assert plain.cumulative_deaths == detailed.cumulative_deaths
    for a, b in zip(plain.annual, detailed.annual, strict=True):
        assert a == {k: b[k] for k in a}
    for history, annual in zip(detailed.diagnostics["history"], detailed.annual, strict=True):
        for state in ("healthy", "insulin_resistant", "t2d"):
            assert sum(c[state] for c in history["cohorts"]) == pytest.approx(annual[state])
        assert history["life_table"][0]["life_expectancy"] == annual["life_expectancy"]
        assert history["life_table"][-1]["qx"] == 1
        assert history["life_table"][-1]["annual_death_probability"] < 1
        if annual["year"]:
            assert sum(
                annual[f"{s}_deaths"] for s in ("healthy", "insulin_resistant", "t2d")
            ) == pytest.approx(annual["deaths"])
    final = detailed.diagnostics["history"][-1]["cohorts"]
    assert [{k: v for k, v in r.items() if k != "sex"} for r in detailed.cohorts] == final


def test_uncertainty_instrumentation_preserves_draws_and_terminal_summaries(payload):
    uninstrumented = uncertainty(REGISTRY, SCENARIO, draws=4, seed=12)
    for key in uninstrumented:
        assert uninstrumented[key] == payload["uncertainty"][key]
    for outcome, rows in payload["uncertainty"]["annual_intervals"].items():
        assert {k: v for k, v in rows[-1].items() if k != "year"} == uninstrumented["outcomes"][
            outcome
        ]
    assert all(len(v) == 4 for v in payload["uncertainty"]["parameter_draws"].values())


def test_graph_exports_actual_states_parameters_and_flows(payload):
    structure = payload["simulation"]["diagnostics"]["structure"]
    assert set(structure["evidence"]) == set(REQUIRED_UNITS)
    assert "prechronic" not in structure["states"]  # Do not draw a not-yet-implemented state.
    assert len(structure["transitions"]) == 6
    for edge in structure["transitions"]:
        assert edge["flow"] in payload["simulation"]["annual"][-1]
        assert edge["parameter"] is None or edge["parameter"] in structure["evidence"]


def test_plotted_values_are_canonical(payload):
    figures = build_figures(payload)
    sim = payload["simulation"]
    assert list(figures["stocks"].data[0].y) == [r["healthy"] for r in sim["annual"]]
    assert [list(r) for r in figures["cohort_t2d"].data[0].z] == [
        [c["t2d"] for c in h["cohorts"]] for h in sim["diagnostics"]["history"]
    ]
    assert list(figures["annual_death_probability"].data[0].y) == [
        r["annual_death_probability"] for r in sim["diagnostics"]["history"][0]["life_table"]
    ]
    assert list(figures["sensitivity"].data[0].x) == [
        r["total_order"] for r in payload["sensitivity"]["indices"]
    ]
    assert list(figures["uncertainty_life_expectancy"].data[2].y) == [
        r["median"] for r in payload["uncertainty"]["annual_intervals"]["life_expectancy"]
    ]
    s = payload["historical"]["series"][0]
    fig = figures["history_" + s["id"]]
    predictions = next(
        t for t in fig.data if t.name.startswith("linear_trend, +5") and t.showlegend is not False
    )
    rows = [r for r in s["folds"] if r["method"] == "linear_trend" and r["horizon"] == 5]
    assert list(predictions.y) == [r["predicted"] for r in rows]
    assert list(predictions.x) == [r["target_year"] for r in rows]


def test_rendering_is_offline_and_repeatable_without_changing_payload(payload, tmp_path):
    before = json.dumps(payload, sort_keys=True)
    a = render_report(payload, tmp_path / "a")
    b = render_report(payload, tmp_path / "b")
    assert a["figures"] >= 30
    page = Path(a["report"]).read_text(encoding="utf-8")
    assert "VALIDATION ONLY" in page and "Plotly.newPlot" in page
    assert "<script src=" not in page  # Plotly must be embedded, no CDN runtime dependency.
    assert page == Path(b["report"]).read_text(encoding="utf-8")
    assert json.dumps(payload, sort_keys=True) == before
    assert json.loads(Path(a["canonical_data"]).read_text()) == payload


def test_renderer_has_no_engine_or_equation_dependencies():
    import demeter.analysis.visualization as module

    tree = ast.parse(Path(module.__file__).read_text())
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any(m and m.startswith("demeter") for m in modules)


def test_visualize_cli_consumes_existing_outputs(payload, tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload))
    result = CliRunner().invoke(
        app, ["visualize", str(source), "--destination", str(tmp_path / "report")]
    )
    assert result.exit_code == 0, result.output
    assert Path(json.loads(result.output)["report"]).exists()
    with pytest.raises(ValueError, match="schema"):
        build_figures({"kind": "other"})


def test_notebook_cells_execute_on_canonical_payload(payload, tmp_path, monkeypatch):
    notebook = json.loads(Path("notebooks/observability.ipynb").read_text())
    (tmp_path / "evidence").mkdir()
    directory = tmp_path / "outputs" / "observability"
    directory.mkdir(parents=True)
    (directory / "diagnostics.json").write_text(json.dumps(payload))
    monkeypatch.chdir(tmp_path)
    namespace = {}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), "observability.ipynb", "exec"), namespace)
    assert namespace["payload"] == payload
    assert len(namespace["figures"]) == 37


def test_prediction_and_residual_share_legend_color(payload):
    fig = build_figures(payload)["history_e0_both_sexes"]
    predictions = [t for t in fig.data if t.mode == "lines+markers" and t.showlegend is not False]
    for predicted in predictions:
        residual = next(t for t in fig.data if t.name == predicted.name and t.showlegend is False)
        assert residual.line.color == predicted.line.color
