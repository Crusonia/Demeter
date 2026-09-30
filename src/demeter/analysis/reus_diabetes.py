"""Reproduce corrected assigned-regimen Cox benchmarks, without a clinical fit."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

DATASET = "reus_corrected_diabetes_benchmark"


def _text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def _table(content: bytes, table_id: str, label: str, headers: list[str]) -> list[list[str]]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("Invalid Reus source XML") from exc
    tables = root.findall(f".//table-wrap[@id='{table_id}']")
    if len(tables) != 1:
        raise ValueError("Expected one uniquely identified Reus table")
    table = tables[0]
    labels = table.findall("label")
    head = table.findall(".//thead/tr")
    actual_headers = [_text(cell) for cell in head[0]] if len(head) == 1 else []
    if (
        len(labels) != 1
        or _text(labels[0]) != label
        or len(head) != 1
        or len(actual_headers) != len(headers) + 1
        or actual_headers[0] != ""
        or len(set(actual_headers)) != len(actual_headers)
        or set(actual_headers[1:]) != set(headers)
    ):
        raise ValueError("Reus table label/comparison headers mismatch")
    # JSON object order is not the source column order. Match exact arm labels.
    positions = [0, *(actual_headers.index(header) for header in headers)]
    rows = [[_text(cell) for cell in row] for row in table.findall(".//tbody/tr")]
    return [
        [row[index] for index in positions] if len(row) == len(positions) else row for row in rows
    ]


def _interval(cell: str) -> tuple[float, float, float]:
    number = r"[0-9]+(?:\.[0-9]+)?"
    match = re.fullmatch(rf"({number})\s*\(\s*({number})\s*[,–−-]\s*({number})\s*\)", cell)
    if not match:
        raise ValueError("Expected a reported Cox HR and confidence interval")
    point, low, high = map(float, match.groups())
    if (
        not all(math.isfinite(x) for x in (point, low, high))
        or not 0 < low <= point <= high
        or low == high
    ):
        raise ValueError("Reus hazard ratios and interval bounds must be finite and positive")
    return point, low, high


def _row(rows: list[list[str]], label: str, arms: list[str]) -> dict:
    matches = [row for row in rows if row and row[0] == label]
    if len(matches) != 1 or len(matches[0]) != len(arms) + 1:
        raise ValueError("Expected one complete Reus analysis row")
    return {arm: _interval(cell) for arm, cell in zip(arms, matches[0][1:], strict=True)}


def extract_reported(correction: bytes, original: bytes, analysis: dict) -> dict:
    """Return every frozen overall contrast; no subgroup pooling or Cox fitting."""
    arms = list(analysis["arm_headers"])
    headers = list(analysis["arm_headers"].values())
    corrected_rows = _table(
        correction, analysis["correction_table_id"], analysis["correction_table_label"], headers
    )
    original_rows = _table(
        original, analysis["original_table_id"], analysis["original_table_label"], headers
    )
    models = {
        model: _row(corrected_rows, label, arms)
        for model, label in analysis["correction_rows"].items()
    }
    original_report = _row(original_rows, analysis["original_report_row"], arms)
    return {
        "models": models,
        "original_report": original_report,
        "original_report_agreement": {
            arm: original_report[arm] == models["original"][arm] for arm in arms
        },
    }


def parameter_key(model: str, arm: str) -> str:
    return f"reus_{model}_{arm}_diabetes_hr"


def audit_reus(registry: EvidenceRegistry, correction: Path, original: Path | None = None) -> dict:
    """Verify immutable contracts, then compare extraction with registered estimates."""
    if DATASET not in registry.datasets:
        raise ValueError("Missing Reus benchmark dataset")
    spec = registry.datasets[DATASET]
    protocol_bytes = Path(spec["protocol_path"]).read_bytes()
    protocol = json.loads(protocol_bytes)
    if (
        spec["model_role"] != "benchmark_only"
        or spec["status"] != "derived"
        or spec["evidence_grade"] != "C"
        or digest(protocol_bytes) != spec["protocol_sha256"]
        or spec["analysis"] != protocol["analysis"]
        or protocol["dataset"] != DATASET
    ):
        raise ValueError("Reus protocol/registry mismatch or unsupported model role")
    source_ids = {"original": spec["original_source_id"], "correction": spec["source_id"]}
    for name, source_id in source_ids.items():
        if source_id not in registry.sources:
            raise ValueError("Missing Reus source definition")
        source = registry.sources[source_id]
        pin = protocol["source_pins"][name]
        if source.url != pin["url"] or source.sha256 != pin["sha256"]:
            raise ValueError("Reus source definition differs from frozen protocol")
    original = original or correction.parent / registry.sources[source_ids["original"]].raw_filename
    contents = {"correction": correction.read_bytes(), "original": original.read_bytes()}
    for name, content in contents.items():
        if digest(content) != protocol["source_pins"][name]["sha256"]:
            raise ValueError(f"Reus {name} source checksum mismatch")
    analysis = spec["analysis"]
    keys = [
        parameter_key(model, arm)
        for model in analysis["correction_rows"]
        for arm in analysis["arm_headers"]
    ]
    if sorted(spec["parameter_keys"]) != sorted(keys):
        raise ValueError("Reus parameter coverage differs from frozen analysis")
    for key in keys:
        if key not in registry.parameters:
            raise ValueError("Missing Reus benchmark parameter")
        parameter = registry.parameters[key]
        if (
            parameter.model_role != "benchmark_only"
            or parameter.status != "estimated"
            or parameter.evidence_grade != "C"
            or parameter.unit != "hazard_ratio"
            or parameter.source_id != source_ids["correction"]
            or parameter.value is None
            or parameter.unresolved
            or not parameter.uncertainty
            or parameter.uncertainty.kind != "interval"
        ):
            raise ValueError("Reus estimates must retain their scoped benchmark contract")
    extracted = extract_reported(contents["correction"], contents["original"], analysis)
    benchmarks, registered_checks = {}, {}
    for model, arms in extracted["models"].items():
        benchmarks[model] = {}
        for arm, (point, low, high) in arms.items():
            key = parameter_key(model, arm)
            parameter = registry.parameters[key]
            registered = (parameter.value, parameter.uncertainty.low, parameter.uncertainty.high)
            registered_checks[key] = registered == (point, low, high)
            benchmarks[model][arm] = {
                "parameter": key,
                "analysis_label": analysis["correction_rows"][model],
                "comparison": analysis["arm_headers"][arm],
                "reported_hazard_ratio": point,
                "reported_interval": [low, high],
                "confidence_level": analysis["confidence_level"],
                "reported_interval_includes_ratio_null": low <= analysis["ratio_null"] <= high,
                "registered_tuple": list(registered),
                "status": "estimated",
                "evidence_grade": parameter.evidence_grade,
                "model_role": "benchmark_only",
            }
    changes = {
        arm: {
            "point_difference": extracted["models"]["corrected"][arm][0]
            - extracted["models"]["original"][arm][0],
            "difference_uncertainty": None,
            "reason": "Dependent original/corrected analyses; covariance unavailable, no difference interval inferred",
        }
        for arm in analysis["arm_headers"]
    }
    checks = {
        "all_registered_estimates_match": all(registered_checks.values()),
        "original_report_agreement": all(extracted["original_report_agreement"].values()),
        "complete_frozen_comparisons": len(registered_checks)
        == analysis["expected_overall_estimates"],
    }
    from demeter.analysis.pathway_compatibility import audit_compatibility

    compatibility = audit_compatibility(registry)
    return {
        "schema_version": 1,
        "analysis_id": protocol["analysis_id"],
        "model_role": "benchmark_only",
        "scientific_release_ready": False,
        "assessment": "Reported-result reproduction and synthetic source-to-model compatibility assessment",
        "population": spec["population"],
        "geography": spec["geography"],
        "time_period": spec["time_period"],
        "results": {
            "benchmarks": benchmarks,
            "original_report_agreement": extracted["original_report_agreement"],
            "registered_estimate_checks": registered_checks,
            "original_corrected_changes": changes,
            "checks": checks,
            "source_reproduction_passed": all(checks.values()),
        },
        "support_decision": protocol["support_decision"],
        "limitations": protocol["limits"],
        "compatibility_diagnostic": compatibility,
        "provenance": {
            "sources": {
                name: registry.sources[key].model_dump(mode="json")
                for name, key in source_ids.items()
            },
            "protocol_sha256": digest(protocol_bytes),
            "definition_sha256": digest(encoded(spec)),
            "parameter_definition_sha256": {
                key: digest(encoded(registry.parameters[key].model_dump(mode="json")))
                for key in keys
            },
            "transform_sha256": digest(Path(__file__).read_bytes()),
            "individual_records_used": False,
            "raw_redistributed": False,
            "cox_fit_reestimated": False,
        },
    }
