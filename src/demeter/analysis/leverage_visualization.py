"""Offline plots of the saved leverage contract; no engine calls or attribution math."""

from __future__ import annotations

import html
import json
from pathlib import Path

import plotly.graph_objects as go

from demeter.analysis.visualization import graph_figure, historical_figures, styled


def leverage_figures(payload):
    if payload.get("kind") != "demeter_leverage" or payload.get("schema_version") != 1:
        raise ValueError("Expected canonical Demeter leverage schema version 1")
    figures = {
        "dependencies": graph_figure(
            payload["structure"], "dependencies", payload["nominal_annual_endpoint"]
        )
    }
    for metric, unit in payload["units"].items():
        fig = go.Figure()
        for name, rows in payload["trajectories"].items():
            fig.add_trace(
                go.Scatter(x=[r["year"] for r in rows], y=[r[metric] for r in rows], name=name)
            )
        figures["comparison_" + metric] = styled(
            fig, metric + " — nominal scenario comparison", "Model year", unit
        )
        rows = payload["attribution"]["by_outcome"][metric]
        fig = go.Figure(
            go.Bar(
                x=[r["sampling_interval"]["median"] for r in rows],
                y=[r["pathway"] for r in rows],
                orientation="h",
                error_x=dict(
                    type="data",
                    symmetric=False,
                    array=[
                        r["sampling_interval"]["p97_5"] - r["sampling_interval"]["median"]
                        for r in rows
                    ],
                    arrayminus=[
                        r["sampling_interval"]["median"] - r["sampling_interval"]["p2_5"]
                        for r in rows
                    ],
                ),
                name="Sampling median / central 95% range",
                marker_color="#b26a00",
                text=[
                    f"Transition evidence: {r['transition_parameter']['status']}, grade {r['transition_parameter']['grade']}"
                    for r in rows
                ],
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[r["nominal"] for r in rows],
                y=[r["pathway"] for r in rows],
                mode="markers",
                marker_symbol="x",
                marker_color="#17212e",
                name="Nominal exact allocation",
            )
        )
        figures["attribution_" + metric] = styled(
            fig,
            metric + " — pathway allocation, NOT causal identification",
            unit + " change",
            "Dietary hazard pathway",
        )
        for scope, ranking in payload["sensitivity"][metric].items():
            rows = ranking["indices"]
            fig = go.Figure()
            if rows:
                fig.add_trace(
                    go.Bar(
                        x=[r["total_order"] for r in rows],
                        y=[r["parameter"] for r in rows],
                        orientation="h",
                        error_x=dict(
                            type="data", array=[r["total_order_conf_half_width"] for r in rows]
                        ),
                        marker_color=[
                            "#b26a00" if r["evidence"]["status"] == "synthetic" else "#176b91"
                            for r in rows
                        ],
                        text=[
                            f"{r['evidence']['status']}, grade {r['evidence']['grade']}; {r['evidence']['role']}"
                            for r in rows
                        ],
                    )
                )
                fig.update_yaxes(autorange="reversed")
            else:
                fig.add_annotation(
                    text="Zero variance: indices undefined for this experiment", showarrow=False
                )
            figures[f"sensitivity_{metric}_{scope}"] = styled(
                fig,
                f"{metric}: {scope} variance — evidence status in hover",
                "Total-order Sobol index ± bootstrap half-width",
                "Input",
            )
    rows = payload["transition_deltas"]
    figures["transition_counts"] = styled(
        go.Figure(go.Bar(x=[r["flow"] for r in rows], y=[r["absolute_delta"] for r in rows])),
        "Changed transition counts — accounting, not additive healthspan effects",
        "Transition",
        "Cumulative people moved: intervention minus baseline",
    )
    rows = payload["state_person_year_deltas"]
    figures["state_time"] = styled(
        go.Figure(go.Bar(x=list(rows), y=list(rows.values()))),
        "Changed state time in the original population",
        "Health state",
        "Person-years: intervention minus baseline",
    )
    for metric, unit in payload["units"].items():
        rows = payload["structural_experiments"]
        figures["structure_" + metric] = styled(
            go.Figure(
                go.Bar(
                    x=["Nominal"] + [r["case"] for r in rows],
                    y=[payload["outcomes"][metric]["absolute_delta"]]
                    + [r["paired_delta"][metric] for r in rows],
                )
            ),
            "Specified structural alternatives — not probability-weighted",
            "Structure",
            unit + " change",
        )
    figures.update(historical_figures(payload["historical"]))
    return figures


def render_leverage(payload, destination: Path):
    figures = leverage_figures(payload)
    destination.mkdir(parents=True, exist_ok=True)
    sections = []
    for i, (name, fig) in enumerate(figures.items()):
        fig.write_json(destination / (name + ".plotly.json"))
        sections.append(
            f'<section id="{name}">'
            + fig.to_html(
                full_html=False,
                include_plotlyjs=i == 0,
                div_id="plot-" + name,
                config={"responsive": True},
            )
            + "</section>"
        )

    def source_link(value):
        if not value:
            return "No source URL registered"
        escaped = html.escape(str(value), quote=True)
        if str(value).startswith(("https://", "http://")):
            return f'<a href="{escaped}">{escaped}</a>'
        return escaped

    evidence = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(r[k]))}</td>" for k in ("key", "status", "grade", "role"))
        + f"<td>{source_link(r['source_url'])}</td>"
        + "</tr>"
        for r in payload["evidence_overlay"]
    )
    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Demeter food leverage</title><style>body{font:16px Arial;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#17212e}"
        ".notice{padding:1rem;background:#fff3d8;border-left:5px solid #b26a00}section{margin:2rem 0;border-top:1px solid #ccc}"
        "td,th{padding:.5rem;border-bottom:1px solid #ccc;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{font-size:13px}</style></head><body>"
        "<h1>Demeter · Food leverage and pathway attribution</h1>"
        '<p class="notice"><strong>VALIDATION ONLY — NOT SCIENTIFIC FINDINGS.</strong> '
        "Synthetic inputs and scenario ranges explain software behavior. Sensitivity is not causal certainty; Shapley allocations depend on the chosen model and counterfactual.</p>"
        f"<p>{html.escape(payload['baseline_scenario']['name'])} → {html.escape(payload['intervention_scenario']['name'])}. "
        f"Horizon: {payload['metadata']['scenario']['years']} years. Draws: {payload['sampling']['draws']}; Sobol base samples: {payload['sampling']['base_samples']}; seed: {payload['sampling']['seed']}.</p>"
        "<p>Pathway contributions reconcile for the nominal run and each draw. Separate medians and interval endpoints need not add. "
        "Direct food-to-mortality effects are absent from this model, which does not establish a zero empirical effect.</p>"
        "<p>Historical observed-versus-predicted plots below show independent benchmark holdouts, not validation of dietary attribution.</p>"
        "<details><summary>Outcome values and sampling intervals</summary><pre>"
        + html.escape(json.dumps(payload["outcomes"], indent=2))
        + "</pre></details>"
        + "".join(sections)
        + "<h2>Evidence strength, kept separate from sensitivity</h2><table><tr><th>Input</th><th>Status</th><th>Grade</th><th>Role</th><th>Source link</th></tr>"
        + evidence
        + "</table>"
        + "<h2>Unranked structural and evidence gaps</h2><pre>"
        + html.escape(json.dumps(payload["unranked_structural_gaps"], indent=2))
        + "</pre>"
        + "<details><summary>Method, reconciliation and provenance</summary><pre>"
        + html.escape(
            json.dumps(
                {
                    "attribution": payload["attribution"],
                    "sampling": payload["sampling"],
                    "provenance": payload["provenance"],
                    "evidence_sha256": payload["metadata"]["evidence_sha256"],
                },
                indent=2,
            )
        )
        + "</pre></details></body></html>"
    )
    (destination / "index.html").write_text(document, encoding="utf-8")
    (destination / "diagnostics.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return {
        "report": str(destination / "index.html"),
        "canonical_data": str(destination / "diagnostics.json"),
        "figures": len(figures),
        "validation_only": True,
        "offline": True,
    }
