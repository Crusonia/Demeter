"""Rebuild clinical benchmarks from official trial JSON and a labeled factual extraction."""

from __future__ import annotations

import json
import math
from pathlib import Path

from demeter.data.ingest import BUNDLE, digest
from demeter.data.nhanes import encoded

STORE = Path("data/sources/glp1/2026-09-28")


def rebuild_glp1(registry, source=STORE, destination=BUNDLE):
    spec = registry.datasets["glp1_benchmarks"]
    if spec["model_role"] != "benchmark_only":
        raise ValueError("GLP-1 clinical benchmarks cannot drive uncalibrated health hazards")
    manifest = json.loads((source / "manifest.json").read_bytes())
    expected = {f"{nct}.json" for nct in spec["trial_ids"]} | {"persistence-extract.json"}
    if set(manifest["sources"]) != expected:
        raise ValueError("Unexpected GLP-1 source manifest")
    for name, receipt in manifest["sources"].items():
        raw = (source / name).read_bytes()
        if digest(raw) != receipt["sha256"] or len(raw) != receipt["bytes"]:
            raise ValueError(f"GLP-1 source checksum mismatch: {name}")
    trials = []
    for nct in spec["trial_ids"]:
        raw = json.loads((source / f"{nct}.json").read_bytes())
        protocol = raw["protocolSection"]
        if protocol["identificationModule"]["nctId"] != nct:
            raise ValueError("Trial identity mismatch")
        matches = [
            o
            for o in raw["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
            if o["title"] == spec["outcome_title"][nct] and o["type"] == "PRIMARY"
        ]
        if len(matches) != 1:
            raise ValueError("Ambiguous trial endpoint")
        o = matches[0]
        if (o["paramType"], o["dispersionType"], o["unitOfMeasure"]) != (
            "MEAN",
            "Standard Deviation",
            "Percentage point",
        ):
            raise ValueError("Unexpected trial endpoint units or dispersion")
        groups = {g["id"]: g["title"] for g in o["groups"]}
        rows = []
        for group in o["classes"]:
            counts = {c["groupId"]: int(c["value"]) for c in group["denoms"][0]["counts"]}
            for cat in group["categories"]:
                for m in cat["measurements"]:
                    value, sd = float(m["value"]), float(m["spread"])
                    if (
                        not math.isfinite(value)
                        or not math.isfinite(sd)
                        or sd < 0
                        or counts[m["groupId"]] <= 0
                    ):
                        raise ValueError("Invalid trial outcome")
                    rows.append(
                        {
                            "period": group["title"],
                            "arm": groups[m["groupId"]],
                            "value": value,
                            "sd": sd,
                            "n": counts[m["groupId"]],
                        }
                    )
        analyses = [
            {
                "estimand": a["groupDescription"],
                "value": float(a["paramValue"]),
                "low": float(a["ciLowerLimit"]),
                "high": float(a["ciUpperLimit"]),
                "confidence_percent": float(a["ciPctValue"]),
                "method": a["statisticalMethod"],
            }
            for a in o["analyses"]
        ]
        if not analyses or any(not a["low"] <= a["value"] <= a["high"] for a in analyses):
            raise ValueError("Invalid trial analysis intervals")
        trials.append(
            {
                "nct_id": nct,
                "title": protocol["identificationModule"]["briefTitle"],
                "eligibility": protocol["eligibilityModule"],
                "vintage": protocol["statusModule"],
                "outcome": o["title"],
                "timeframe": o["timeFrame"],
                "unit": o["unitOfMeasure"],
                "observation_definition": o["description"],
                "rows": rows,
                "analyses": analyses,
                "source_url": manifest["sources"][f"{nct}.json"]["url"],
            }
        )
    persistence = json.loads((source / "persistence-extract.json").read_bytes())
    rows = persistence["rows"]
    if len(rows) != 4 or {(r["event"], r["t2d"]) for r in rows} != {
        (event, diabetes)
        for event in ("discontinuation", "reinitiation")
        for diabetes in (True, False)
    }:
        raise ValueError("Missing/duplicate persistence strata")
    for r in rows:
        if not 0 <= r["low"] <= r["value"] <= r["high"] <= 1 or r["year"] <= 0 or r["n"] <= 0:
            raise ValueError("Invalid persistence observation")
    report = {
        "schema_version": 1,
        "model_role": "benchmark_only",
        "scientific_release_ready": False,
        "engine_parameters_updated": False,
        "evidence_appraisal": spec["evidence_appraisal"],
        "trials": trials,
        "persistence": persistence,
        "limitations": spec["limitations"],
        "provenance": {
            "sources": manifest["sources"],
            "definition_sha256": digest(encoded(spec)),
            "transform": "demeter.data.glp1.rebuild_glp1",
        },
    }
    content = encoded(report)
    receipt = {
        "schema_version": 1,
        "bundle_sha256": digest(content),
        "definition_sha256": digest(encoded(spec)),
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "glp1_benchmarks.json").write_bytes(content)
    (destination / "glp1_manifest.json").write_bytes(encoded(receipt))
    return receipt


def load_glp1(registry, bundle=BUNDLE):
    content = (bundle / "glp1_benchmarks.json").read_bytes()
    manifest = json.loads((bundle / "glp1_manifest.json").read_bytes())
    if (
        digest(content) != manifest["bundle_sha256"]
        or digest(encoded(registry.datasets["glp1_benchmarks"])) != manifest["definition_sha256"]
    ):
        raise ValueError("GLP-1 benchmark checksum or definition mismatch")
    report = json.loads(content)
    if (
        report["model_role"] != "benchmark_only"
        or report["scientific_release_ready"]
        or report["engine_parameters_updated"]
    ):
        raise ValueError("Invalid GLP-1 benchmark role")
    return report
