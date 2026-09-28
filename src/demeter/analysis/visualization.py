"""Scientific views of canonical output dictionaries; no simulation equations here."""

from __future__ import annotations

import html
import json
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = ["#176b91", "#b26a00", "#ae365c", "#343b47"]


def styled(fig: go.Figure, title: str, x: str = "", y: str = "") -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=title,
        xaxis_title=x,
        yaxis_title=y,
        font=dict(family="Arial", size=13),
        margin=dict(t=85, b=65),
        legend=dict(orientation="h", y=-0.22),
        height=470,
    )
    return fig


def graph_figure(structure: dict, kind: str, annual: dict) -> go.Figure:
    """NetworkX lays out the canonical engine graph; edge meaning comes from output."""
    transitions = kind == "transitions"
    edges = structure["transitions"] if transitions else structure["dependencies"]
    graph = nx.DiGraph()
    graph.add_edges_from((e["source"], e["target"]) for e in edges)
    positions = nx.spring_layout(graph, seed=0, k=1.7)
    fig = go.Figure()
    evidence = structure["evidence"]
    for edge in edges:
        keys = (
            [edge["parameter"]]
            if transitions and edge["parameter"]
            else ([] if transitions else edge["parameters"])
        )
        records = [evidence[k] for k in keys]
        synthetic = any(p["status"] == "synthetic" for p in records)
        color = "#b26a00" if synthetic else "#64748b"
        a, b = positions[edge["source"]], positions[edge["target"]]
        label = edge.get("flow", "dependency")
        if transitions:
            label += f": {annual.get(edge['flow'], 0):,.0f} people/year"
        detail = "<br>".join(
            [label]
            + [
                f"{html.escape(p['key'])}: {p['status']}, grade {p['evidence_grade']}<br>"
                f"{html.escape(p['source'])}"
                for p in records
            ]
        )
        if not records:
            detail += "<br>Model arithmetic / sourced baseline; no separate causal grade"
        fig.add_trace(
            go.Scatter(
                x=[float(a[0]), float(b[0])],
                y=[float(a[1]), float(b[1])],
                mode="lines",
                line=dict(color=color, dash="dash" if synthetic else "solid"),
                text=[detail, detail],
                hoverinfo="text",
                showlegend=False,
            )
        )
        fig.add_annotation(
            x=float(b[0] * 0.8 + a[0] * 0.2),
            y=float(b[1] * 0.8 + a[1] * 0.2),
            ax=float(b[0] * 0.6 + a[0] * 0.4),
            ay=float(b[1] * 0.6 + a[1] * 0.4),
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            text="",
            showarrow=True,
            arrowhead=2,
            arrowcolor=color,
        )
    nodes = list(graph)
    fig.add_trace(
        go.Scatter(
            x=[float(positions[n][0]) for n in nodes],
            y=[float(positions[n][1]) for n in nodes],
            mode="markers+text",
            marker=dict(size=17, color=COLORS[0]),
            text=[n.replace("_", " ") for n in nodes],
            textposition="top center",
            hoverinfo="text",
            showlegend=False,
        )
    )
    styled(
        fig,
        ("State transitions / annual flows" if transitions else "Implemented dependency graph")
        + " — VALIDATION ONLY",
    )
    fig.update_xaxes(visible=False, range=[-1.45, 1.45])
    fig.update_yaxes(visible=False, range=[-1.3, 1.3])
    fig.update_layout(height=600)
    return fig


def model_figures(payload: dict) -> dict[str, go.Figure]:
    sim, unc, sensitivity = payload["simulation"], payload["uncertainty"], payload["sensitivity"]
    diag = sim["diagnostics"]
    if not diag or "annual_intervals" not in unc:
        raise ValueError("Instrumented simulation and uncertainty outputs required")
    figures = {}
    annual = sim["annual"]
    states = [s for s in diag["structure"]["states"] if s != "dead"]
    years = [r["year"] for r in annual]
    fig = go.Figure()
    for i, state in enumerate(states):
        fig.add_trace(
            go.Scatter(
                x=years,
                y=[r[state] for r in annual],
                name=state,
                stackgroup="living",
                line=dict(color=COLORS[i]),
            )
        )
    figures["stocks"] = styled(fig, "Living stocks — VALIDATION ONLY", "Model year", "People")
    fig = go.Figure()
    for edge in diag["structure"]["transitions"]:
        fig.add_trace(
            go.Scatter(x=years, y=[r.get(edge["flow"], 0) for r in annual], name=edge["flow"])
        )
    figures["flows"] = styled(fig, "Annual flows — VALIDATION ONLY", "Model year", "People / year")
    for kind in ("transitions", "dependencies"):
        figures[kind] = graph_figure(diag["structure"], kind, annual[-1])
    history = diag["history"]
    for state in states:
        fig = go.Figure(
            go.Heatmap(
                x=list(range(101)),
                y=[r["year"] for r in history],
                z=[[c[state] for c in r["cohorts"]] for r in history],
                colorscale="Viridis",
                colorbar=dict(title="People"),
            )
        )
        figures["cohort_" + state] = styled(
            fig,
            f"Age-cell trajectories: {state} — VALIDATION ONLY",
            "Age (100 = pooled 100+)",
            "Model year",
        )
    for field, label, unit in (
        ("annual_death_probability", "Annual mortality probability", "Probability/year"),
        ("survivors", "Period life-table survivorship", "Survivors per 100000 births"),
        ("life_expectancy", "Period remaining life expectancy", "Years"),
    ):
        fig = go.Figure()
        for snapshot in (history[0], history[-1]):
            table = snapshot["life_table"]
            fig.add_trace(
                go.Scatter(
                    x=[r["start_age"] for r in table],
                    y=[r[field] for r in table],
                    name=f"Year {snapshot['year']}",
                )
            )
        figures[field] = styled(fig, label + " — VALIDATION ONLY", "Age (100+ pooled)", unit)
    for metric, rows in unc["annual_intervals"].items():
        x = [r["year"] for r in rows]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=[r["p2_5"] for r in rows], name="2.5%", line=dict(width=0)))
        fig.add_trace(
            go.Scatter(
                x=x,
                y=[r["p97_5"] for r in rows],
                name="97.5%",
                fill="tonexty",
                line=dict(width=0),
                fillcolor="rgba(23,107,145,.18)",
            )
        )
        fig.add_trace(go.Scatter(x=x, y=[r["median"] for r in rows], name="Median"))
        figures["uncertainty_" + metric] = styled(
            fig,
            metric.replace("_", " ") + " — synthetic 95% sampling interval",
            "Model year",
            "People" if metric == "cumulative_deaths" else "Years",
        )
    evidence = diag["structure"]["evidence"]
    indices = sensitivity["indices"]
    fig = go.Figure(
        go.Bar(
            x=[r["total_order"] for r in indices],
            y=[r["parameter"] for r in indices],
            orientation="h",
            error_x=dict(type="data", array=[r["total_order_conf_half_width"] for r in indices]),
            marker_color=[
                "#b26a00" if evidence[r["parameter"]]["status"] == "synthetic" else COLORS[0]
                for r in indices
            ],
            customdata=[
                [evidence[r["parameter"]]["status"], evidence[r["parameter"]]["evidence_grade"]]
                for r in indices
            ],
            hovertemplate="%{y}: %{x}<br>%{customdata[0]}, grade %{customdata[1]}<extra></extra>",
        )
    )
    figures["sensitivity"] = styled(
        fig,
        f"Sobol total-order: {sensitivity['outcome']} — synthetic ranges",
        "Variance fraction (may be noisy; no clipping)",
        "Parameter",
    )
    figures["sensitivity"].update_yaxes(autorange="reversed")
    for key, draws in unc["parameter_draws"].items():
        p = evidence[key]
        figures["parameter_" + key] = styled(
            go.Figure(go.Histogram(x=draws, name="Actual sampled values", nbinsx=20)),
            f"{key} — {p['status']}, grade {p['evidence_grade']}",
            p["unit"],
            "Draw count",
        )
    return figures


def historical_figures(report: dict) -> dict[str, go.Figure]:
    figures = {}
    for series in report["series"]:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            subplot_titles=(
                "Observed and held-out predictions",
                "Residual: observed minus predicted",
            ),
        )
        obs = series["observations"]
        # Separate segments so a line never implies continuity across a definition break.
        segments = list(dict.fromkeys(r["segment"] for r in obs))
        for segment in segments:
            subset = [r for r in obs if r["segment"] == segment]
            fig.add_trace(
                go.Scatter(
                    x=[r["year"] for r in subset],
                    y=[r["value"] for r in subset],
                    name="Observed: " + segment,
                    line=dict(color="#17212e", width=2),
                ),
                row=1,
                col=1,
            )
        groups = sorted({(r["method"], r["horizon"], r["segment"]) for r in series["folds"]})
        for group_index, (method, horizon, segment) in enumerate(groups):
            color = COLORS[group_index % len(COLORS)]
            rgb = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
            rows = sorted(
                [
                    r
                    for r in series["folds"]
                    if (r["method"], r["horizon"], r["segment"]) == (method, horizon, segment)
                ],
                key=lambda r: r["target_year"],
            )
            x = [r["target_year"] for r in rows]
            name = f"{method}, +{horizon}, {segment}"
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=[r["predicted"] for r in rows],
                    mode="lines+markers",
                    line=dict(color=color),
                    name=name,
                    legendgroup=name,
                    customdata=[[r["origin"], ", ".join(r["shock_flags"])] for r in rows],
                    hovertemplate="Year %{x}: %{y}<br>Origin %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=[r["lower"] for r in rows],
                    mode="lines",
                    line=dict(width=0),
                    name=name + " lower",
                    legendgroup=name,
                    showlegend=False,
                    connectgaps=False,
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=[r["upper"] for r in rows],
                    mode="lines",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},.08)",
                    name=name + " interval",
                    legendgroup=name,
                    showlegend=False,
                    connectgaps=False,
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=[r["residual"] for r in rows],
                    line=dict(color=color),
                    name=name,
                    legendgroup=name,
                    showlegend=False,
                    mode="lines+markers",
                ),
                row=2,
                col=1,
            )
        fig.add_hline(y=0, line_dash="dot", row=2, col=1)
        for shock in report["structural_breaks"]:
            if (
                shock["domain"] in ("all", series["domain"])
                and obs[0]["year"] <= shock["start"] <= obs[-1]["year"]
            ):
                fig.add_vline(x=shock["start"], line_dash="dot", line_color="#b26a00")
        styled(fig, series["label"] + " — historical benchmarks")
        fig.update_yaxes(title_text=series["unit"], row=1, col=1)
        fig.update_yaxes(title_text="Residual (same units)", row=2, col=1)
        fig.update_xaxes(title_text="Calendar year", row=2, col=1)
        fig.update_layout(height=740, legend=dict(orientation="h", y=-0.18))
        figures["history_" + series["id"]] = fig
    return figures


def diet_figures(payload: dict) -> dict[str, go.Figure]:
    """Plot recorded response states; never recompute dynamics in the renderer."""
    sim = payload["simulation"]
    scenario = sim["metadata"]["scenario"]
    if (
        not scenario.get("upf_schedule")
        and scenario.get("diet_response", {}).get("kind") != "dynamic"
    ):
        return {}
    annual = sim["annual"]
    years = [r["year"] for r in annual]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[r["year"] - 1 for r in annual[1:]] + [years[-1]],
            y=[r["relative_upf"] for r in annual[1:]] + [annual[-1]["relative_upf"]],
            name="UPF input (start of year)",
            line_shape="hv",
        )
    )
    for field, label in (
        ("applied_progression_multiplier", "Progression (year end)"),
        ("applied_recovery_multiplier", "Recovery (year end)"),
    ):
        fig.add_trace(go.Scatter(x=years, y=[r[field] for r in annual], name=label))
    result = {
        "diet_response": styled(
            fig,
            "Diet schedule and delayed hazards — VALIDATION ONLY",
            "Model year",
            "Relative multiplier",
        )
    }
    fig = go.Figure()
    for field in ("cumulative_exposure_years", "cumulative_absolute_exposure_years"):
        fig.add_trace(go.Scatter(x=years, y=[r[field] for r in annual], name=field))
    result["diet_duration"] = styled(
        fig,
        "Exposure duration accounting — not irreversible damage",
        "Model year",
        "Relative exposure × years",
    )
    if scenario["diet_response"]["kind"] == "dynamic":
        fig = go.Figure()
        for field in ("shaped_dose", "fast_response", "retained_exposure", "recovery_response"):
            fig.add_trace(go.Scatter(x=years, y=[r[field] for r in annual], name=field))
        result["diet_memory"] = styled(
            fig,
            "Fast, fading-memory and recovery states — VALIDATION ONLY",
            "Model year",
            "Relative dose deviation",
        )
        timing = [
            r
            for r in payload["sensitivity"]["indices"]
            if r["parameter"] in payload["sensitivity"]["timing_parameters"]
        ]
        fig = go.Figure(
            go.Bar(
                x=[r["total_order"] for r in timing],
                y=[r["parameter"] for r in timing],
                orientation="h",
                error_x=dict(type="data", array=[r["total_order_conf_half_width"] for r in timing]),
            )
        )
        result["diet_timing"] = styled(
            fig,
            "Timing within full parameter sensitivity — synthetic ranges",
            "Total-order Sobol index",
            "Parameter",
        )
    challenge = payload.get("diet_lag_challenge")
    if challenge:
        fig = go.Figure()
        rows = challenge["observed_contrasts"]
        fig.add_trace(
            go.Scatter(
                x=[r["year"] for r in rows],
                y=[r["normalized"] for r in rows],
                name="Observed trial contrast, normalized",
                mode="lines+markers",
            )
        )
        for curve in challenge["curves"]:
            fig.add_trace(
                go.Scatter(
                    x=[r["year"] for r in curve["rows"]],
                    y=[r["shortcut_normalized_response"] for r in curve["rows"]],
                    name=f"Shortcut lag {curve['lag_years']:g} years",
                    line_dash="dash",
                )
            )
        result["diet_lag_challenge"] = styled(
            fig,
            "Historical shortcut challenge — curves are NOT model remission predictions",
            "Follow-up year",
            "Relative to first follow-up",
        )
    return result


def glp1_figures(payload: dict) -> dict[str, go.Figure]:
    annual = payload["simulation"]["annual"]
    if "glp1" not in annual[0]:
        return {}
    years, rows = [r["year"] for r in annual], [r["glp1"] for r in annual]
    figures = {}
    for key, title, unit in (
        ("treatment_stocks", "Treatment history and response stocks", "People"),
        ("flows", "Initiation, discontinuation and re-initiation", "People per annual step"),
    ):
        fig = go.Figure()
        for field in rows[0][key]:
            fig.add_trace(go.Scatter(x=years, y=[r[key][field] for r in rows], name=field))
        figures["glp1_" + key] = styled(fig, title + " — VALIDATION ONLY", "Model year", unit)
    fig = go.Figure()
    for field, label in (
        ("population_mean_weight_reduction_fraction", "Weight reduction proxy"),
        ("population_mean_intake_reduction_fraction", "Intake reduction proxy"),
    ):
        fig.add_trace(go.Scatter(x=years, y=[r[field] for r in rows], name=label))
    figures["glp1_response"] = styled(
        fig,
        "Delayed response and washout — synthetic proxies",
        "Model year",
        "Population mean fractional reduction",
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years, y=[r["on_treatment"] for r in rows], name="Treated survivors at year end"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=[r["allocation"]["capacity"] if r["allocation"] else 0 for r in rows],
            name="Slots at annual allocation",
            line_shape="hv",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=[r["allocation"]["unfilled_start_requests"] if r["allocation"] else 0 for r in rows],
            name="Starts denied by capacity",
        )
    )
    figures["glp1_capacity"] = styled(
        fig, "Exogenous treatment supply and allocation", "Model year", "People / slots"
    )
    benchmark = payload.get("glp1_benchmarks")
    if benchmark:
        fig = go.Figure()
        for trial in benchmark["trials"]:
            # Display one explicit estimand; SDs for available-case means are separate in the JSON.
            a = next(a for a in trial["analyses"] if a["estimand"] == "Treatment policy estimand")
            fig.add_trace(
                go.Bar(
                    x=[trial["nct_id"] + "<br>" + trial["timeframe"]],
                    y=[a["value"]],
                    name=trial["nct_id"],
                    error_y=dict(
                        type="data",
                        symmetric=False,
                        array=[a["high"] - a["value"]],
                        arrayminus=[a["value"] - a["low"]],
                    ),
                )
            )
        figures["glp1_trial_benchmarks"] = styled(
            fig,
            "Trial weight contrasts — benchmarks, NOT model effects",
            "Distinct trials and follow-up periods",
            "Percentage-point difference (95% CI)",
        )
    return figures


def build_figures(payload: dict) -> dict[str, go.Figure]:
    if payload.get("kind") != "demeter_observability" or payload.get("schema_version") != 1:
        raise ValueError("Expected canonical Demeter observability schema version 1")
    return {
        **model_figures(payload),
        **historical_figures(payload["historical"]),
        **diet_figures(payload),
        **glp1_figures(payload),
    }


def render_report(payload: dict, destination: Path) -> dict:
    """Export a self-contained offline HTML report and reproducible Plotly JSON."""
    figures = build_figures(payload)
    destination.mkdir(parents=True, exist_ok=True)
    fragments = []
    for i, (name, fig) in enumerate(figures.items()):
        fig.write_json(destination / (name + ".plotly.json"))
        fragments.append(
            f'<section id="{html.escape(name)}"><h2>{html.escape(name.replace("_", " "))}</h2>'
            + fig.to_html(
                full_html=False,
                include_plotlyjs=i == 0,
                div_id="plot-" + name,
                config={"responsive": True},
            )
            + "</section>"
        )
    sim = payload["simulation"]
    notes = "".join(f"<li>{html.escape(note)}</li>" for note in sim["metadata"]["limitations"])
    nav = " | ".join(
        f'<a href="#{name}">{html.escape(name.replace("_", " "))}</a>' for name in figures
    )
    metrics_html = []
    for s in payload["historical"]["series"]:
        metrics_html.append(
            f"<h3>{html.escape(s['label'])}</h3><pre>"
            + html.escape(json.dumps(s["metrics"], indent=2))
            + "</pre>"
        )
    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Demeter scientific observability</title><style>"
        "body{font:16px Arial;margin:2rem auto;max-width:1150px;padding:0 1rem;color:#17212e}"
        ".notice{background:#fff3d8;padding:1rem;border-left:5px solid #b26a00}"
        "section{margin:2rem 0;border-top:1px solid #ccc}pre{overflow:auto;font-size:12px}"
        "nav{line-height:1.8}a{color:#176b91}</style></head><body>"
        "<h1>Demeter · Scientific observability</h1>"
        '<p class="notice"><strong>VALIDATION ONLY — NOT SCIENTIFIC FINDINGS.</strong> '
        "Model pathways and parameter ranges remain synthetic. Historical observations "
        "are sourced; their benchmark forecasts do not validate dietary effects.</p>"
        f"<p>Scenario: {html.escape(sim['scenario'])}. Horizon: {sim['years']} years. "
        f"Parameter draws: {payload['uncertainty']['draws']}; seed: {payload['uncertainty']['seed']}.</p>"
        "<details><summary>Definitions, provenance and limitations</summary><ul>"
        + notes
        + "</ul><p>Heatmaps show age cells, not identified birth cohorts. The 100+ cell pools ages. "
        "Dashed amber graph links depend on synthetic evidence; neutral links include "
        "arithmetic and sourced inputs, not proof of causality. Hover for evidence details.</p><pre>"
        + html.escape(json.dumps(sim["metadata"], indent=2))
        + "</pre></details>"
        "<p>Historical forecast bands use earlier same-horizon errors; missing bands mean "
        "insufficient history. Nominal coverage is not guaranteed. Definition breaks are "
        "not joined. Dotted vertical lines flag redesign/shock dates. Fold roles, skipped "
        "origins and all observations are available in the adjacent diagnostics.json.</p>"
        "<details><summary>Jump to a chart</summary><nav>"
        + nav
        + "</nav></details>"
        + "".join(fragments)
        + "<h2>Historical errors and achieved coverage</h2>"
        + "".join(metrics_html)
        + "</body></html>"
    )
    (destination / "index.html").write_text(document, encoding="utf-8")
    (destination / "diagnostics.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n"
    )
    return {
        "report": str(destination / "index.html"),
        "canonical_data": str(destination / "diagnostics.json"),
        "figures": len(figures),
        "validation_only": True,
        "offline": True,
    }
