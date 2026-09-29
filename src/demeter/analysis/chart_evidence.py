"""Explain saved diagnostics without loading a registry or running equations."""

from __future__ import annotations

from copy import deepcopy
import html
import json


def chart_evidence(payload: dict, name: str) -> dict:
    sim = payload["simulation"]
    structure = sim["diagnostics"]["structure"]
    active = structure["evidence"]
    snapshot = payload.get("evidence_context", {})
    context = {
        "schema_version": 1,
        "scope": "Active model inputs",
        "note": "These inputs belong to this saved run. A citation or grade does not establish a causal effect.",
        "evidence_sha256": sim["metadata"]["evidence_sha256"],
        "parameters": [],
        "sources": [],
        "mechanisms": [],
        "sampled_parameters": [],
        "limitations": list(sim["metadata"]["limitations"]),
        "unresolved": list(sim["metadata"]["scientific_blockers"]),
    }

    def source(key, record):
        context["sources"].append({"key": key, "record": deepcopy(record)})

    def dataset(key):
        record = snapshot.get("datasets", {}).get(key)
        if record:
            source(key, record)
        else:
            context["unresolved"].append(f"Dataset metadata not saved: {key}")

    keys = list(active)
    if name.startswith("history_"):
        history = payload["historical"]
        series = next((s for s in history["series"] if s["id"] == name[8:]), None)
        keys = []
        context.update(
            scope="Observed historical benchmark and derived forecasts",
            note=history["causal_policy"],
            limitations=history["limitations"],
            unresolved=[],
        )
        if series:
            source(
                series["id"],
                {
                    **{
                        k: v
                        for k, v in series.items()
                        if k not in ("folds", "metrics", "observations")
                    },
                    "status": "observed benchmark; forecasts are derived",
                    "time_period": f"{min(r['year'] for r in series['observations'])}–{max(r['year'] for r in series['observations'])}",
                    "uncertainty": history["interval_method"],
                    "receipt": history["metadata"]["sources"].get(series["source"], {}),
                },
            )
        else:
            context["unresolved"].append("Historical series context unavailable in this saved run")
    elif name == "glp1_trial_benchmarks":
        keys = []
        benchmark = payload["glp1_benchmarks"]
        context.update(
            scope="Trial-specific randomized comparisons",
            unresolved=[],
            note="Trial weight contrasts do not calibrate metabolic hazards or mortality.",
            limitations=benchmark["limitations"],
        )
        for trial in benchmark["trials"]:
            source(
                trial["nct_id"],
                {
                    **trial,
                    "status": "observed trial; estimated treatment contrast",
                    "population": trial["eligibility"]["eligibilityCriteria"],
                    "time_period": trial["timeframe"],
                    "uncertainty": [
                        a for a in trial["analyses"] if a["estimand"] == "Treatment policy estimand"
                    ],
                    "evidence_appraisal": benchmark["evidence_appraisal"]["trials"],
                    "receipt": benchmark["provenance"],
                },
            )
    elif name == "diet_lag_challenge":
        challenge = payload["diet_lag_challenge"]
        spec = snapshot.get("datasets", {}).get("diet_response_challenge", {})
        keys = [spec["lag_parameter"]] if spec.get("lag_parameter") in active else []
        context.update(
            scope="Observed challenge against a synthetic shortcut",
            note=challenge["hypothesis_tested"],
            limitations=challenge["source"]["limitations"],
        )
        dataset("diet_response_challenge")
        source("challenge_source", challenge["source"])
    elif name.startswith("parameter_"):
        keys = [name[10:]] if name[10:] in active else []
        context["scope"] = "One sampled assumption"
    elif name in ("sensitivity", "diet_timing"):
        keys = [r["parameter"] for r in payload["sensitivity"]["indices"]]
        if name == "diet_timing":
            keys = [k for k in keys if k in payload["sensitivity"]["timing_parameters"]]
        context["scope"] = "Inputs ranked in this sensitivity analysis"
        context["note"] = (
            "Rankings depend on the stated ranges and model. Fixed background inputs still affect the result. Sensitivity is not evidence strength."
        )
    elif name in ("diet_duration", "diet_response", "diet_memory"):
        context["scope"] = (
            "Exposure accounting" if name == "diet_duration" else "Diet response assumptions"
        )
        targets = {"lagged_response", "recovery_response"}
        edges = [e for e in structure["dependencies"] if e["target"] in targets]
        keys = (
            []
            if name == "diet_duration"
            else list(dict.fromkeys(k for e in edges for k in e["parameters"]))
        )
        context["note"] = (
            "Duration integrates the specified relative exposure over model time; it is not an estimate of irreversible damage."
            if name == "diet_duration"
            else "These are the declared inputs to the diet response. Downstream transition rates are not identified by the timing curve."
        )
        if not edges and name != "diet_duration":
            context["unresolved"].append(structure["interpretation"])
    else:
        dataset("us_population")
        dataset("us_mortality")
        for key, receipt in snapshot.get("baseline_sources", {}).items():
            source(key, receipt)
        if not snapshot:
            context["unresolved"].append(
                "Detailed source metadata was not captured by this older run"
            )
        edges = structure["transitions"] if name == "transitions" else structure["dependencies"]
        for i, edge in enumerate(edges):
            params = edge.get("parameters", [edge["parameter"]] if edge.get("parameter") else [])
            context["mechanisms"].append(
                {
                    "id": str(i),
                    "label": f"{edge['source']} → {edge['target']}",
                    "parameters": params,
                    "note": "Directly declared inputs for this link; other upstream inputs can still matter."
                    if params
                    else "No parameter is attached to this link in the saved graph. It may represent arithmetic or a baseline input; this does not establish causality or a zero effect.",
                }
            )
        if not edges:
            context["unresolved"].append(structure["interpretation"])
    context["scenario"] = deepcopy(sim["metadata"]["scenario"])
    context["parameters"] = [deepcopy(active[k]) for k in keys if k in active]
    context["sampled_parameters"] = [
        k for k in keys if k in payload["uncertainty"].get("parameter_draws", {})
    ]
    return context


def evidence_html(context: dict) -> str:
    """Safe, network-free evidence details for the standalone report."""

    def escaped(value):
        return html.escape(str(value))

    def record(title, row):
        links = []
        for key in ("source_url", "url", "documentation"):
            url = row.get(key) or row.get("receipt", {}).get(key)
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                links.append(f'<a href="{escaped(url)}" rel="noreferrer">Read source</a>')
        fields = "".join(
            f"<dt>{escaped(key.replace('_', ' '))}</dt><dd>{escaped(row.get(key) or 'Not recorded')}</dd>"
            for key in (
                "status",
                "unit",
                "population",
                "geography",
                "time_period",
                "uncertainty",
                "notes",
            )
        )
        return (
            f'<article class="source"><h4>{escaped(title)}</h4><dl>{fields}</dl>'
            + " ".join(links)
            + "<details><summary>Full saved record</summary><pre>"
            + escaped(json.dumps(row, indent=2, ensure_ascii=False))
            + "</pre></details></article>"
        )

    parameters = {p["key"]: p for p in context["parameters"]}
    mechanisms = "".join(
        f"<details><summary>{escaped(m['label'])}</summary><p>{escaped(m['note'])}</p>"
        + "".join(record(k, parameters[k]) for k in m["parameters"] if k in parameters)
        + "</details>"
        for m in context["mechanisms"]
    )
    return (
        '<details class="chart-evidence"><summary>Evidence for this chart</summary>'
        + f"<h3>{escaped(context['scope'])}</h3><p>{escaped(context['note'])}</p>"
        + mechanisms
        + "".join(record(k, p) for k, p in parameters.items())
        + "".join(record(s["key"], s["record"]) for s in context["sources"])
        + "<h4>Unresolved evidence and limits</h4><ul>"
        + "".join(f"<li>{escaped(v)}</li>" for v in context["unresolved"] + context["limitations"])
        + "</ul></details>"
    )
