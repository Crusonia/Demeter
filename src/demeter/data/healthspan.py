"""Reconstruct the NCHS Sullivan example from an immutable government PDF."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

from demeter.data.ingest import BUNDLE, digest
from demeter.data.nhanes import encoded, storage_numbers
from demeter.health.healthspan import sullivan
from demeter.schema import EvidenceRegistry

STORE = Path("data/sources/healthspan/nchs-2001")
DATASET = "healthspan_method_benchmark"


def extract_table(path: Path, spec: dict) -> list[dict]:
    text = PdfReader(path).pages[spec["pdf_page_index"]].extract_text(extraction_mode="layout")
    if "Table" not in text or "Sullivan" not in text:
        raise ValueError("NCHS healthspan table heading missing")
    rows = []
    for line in text.splitlines():
        match = re.match(
            r"^\s*(\d+)(?:\s*[–-]\s*(\d+))?\s+years(?:\s+and\s+over)?\s+[\s.]*\.[\s.]+(.*)$", line
        )
        if not match:
            continue
        values = re.findall(r"\d[\d,]*(?:\.\d+)?", match[3])
        if len(values) != 7:
            raise ValueError("Unexpected NCHS healthspan table columns")
        lx, lived, unhealthy, healthy, hlived, hremaining, hle = map(
            lambda value: float(value.replace(",", "")), values
        )
        if abs(healthy + unhealthy - 1) > 1e-10:
            raise ValueError("NCHS health shares do not partition the population")
        rows.append(
            {
                "age": int(match[1]),
                "survivors": lx,
                "person_years": lived,
                "healthy_prevalence": healthy,
                "published_healthy_person_years": hlived,
                "published_remaining_healthy_person_years": hremaining,
                "published_health_expectancy": hle,
            }
        )
    if [r["age"] for r in rows] != spec["ages"]:
        raise ValueError("Missing, duplicated, or unexpected NCHS age intervals")
    return rows


def crosscheck(report: dict) -> dict:
    rows = report["rows"]
    calculated = sullivan(
        [r["age"] for r in rows],
        [r["survivors"] for r in rows],
        [r["person_years"] for r in rows],
        [[r["healthy_prevalence"], 1 - r["healthy_prevalence"]] for r in rows],
        ("good_or_better_self_reported_health", "fair_or_poor_self_reported_health"),
    )
    checks = []
    for observed, result in zip(rows, calculated, strict=True):
        actual = result["state_years"]["good_or_better_self_reported_health"]
        checks.append(
            {
                "age": observed["age"],
                "published": observed["published_health_expectancy"],
                "calculated": actual,
                "absolute_error_years": abs(actual - observed["published_health_expectancy"]),
                "passed": round(actual, report["published_decimal_places"])
                == observed["published_health_expectancy"],
            }
        )
    return {
        "passed": all(r["passed"] for r in checks),
        "checks": checks,
        "scope": "Estimator arithmetic against NCHS Table 2; not calibration of metabolic health states or dietary effects",
        "scientific_release_ready": False,
        "source": report["source"],
        "population": report["population"],
        "provenance": report["provenance"],
    }


def rebuild_healthspan(
    registry: EvidenceRegistry, source: Path = STORE, destination: Path = BUNDLE
) -> dict:
    spec = registry.datasets[DATASET]
    if spec["model_role"] != "method_validation_only":
        raise ValueError("Healthspan method example cannot be used as engine evidence")
    manifest = json.loads((source / "manifest.json").read_bytes())
    path = source / "statnt21.pdf"
    if digest(path.read_bytes()) != manifest["sources"][path.name]["sha256"]:
        raise ValueError("NCHS healthspan source checksum mismatch")
    report = {
        "schema_version": 1,
        "model_role": "method_validation_only",
        "population": spec["population"],
        "source": spec["source_url"],
        "published_decimal_places": spec["published_decimal_places"],
        "rows": extract_table(path, spec),
        "provenance": {
            "source_sha256": manifest["sources"][path.name]["sha256"],
            "dataset_definition_sha256": digest(encoded(spec)),
            "transform": "demeter.data.healthspan.extract_table",
            "transform_version": 1,
        },
    }
    if not crosscheck(report)["passed"]:
        raise ValueError("NCHS healthspan reconstruction failed published targets")
    content = encoded(storage_numbers(report))
    receipt = {
        "schema_version": 1,
        "bundle_sha256": digest(content),
        "dataset_definition_sha256": digest(encoded(spec)),
        "sources": manifest["sources"],
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "healthspan_benchmark.json").write_bytes(content)
    (destination / "healthspan_manifest.json").write_bytes(encoded(receipt))
    return receipt


def load_healthspan(registry: EvidenceRegistry, bundle: Path = BUNDLE) -> dict:
    content = (bundle / "healthspan_benchmark.json").read_bytes()
    manifest = json.loads((bundle / "healthspan_manifest.json").read_bytes())
    if digest(content) != manifest["bundle_sha256"]:
        raise ValueError("Healthspan benchmark checksum mismatch")
    if digest(encoded(registry.datasets[DATASET])) != manifest["dataset_definition_sha256"]:
        raise ValueError("Healthspan benchmark definition changed; rebuild required")
    report = json.loads(content)
    if report["schema_version"] != 1 or report["model_role"] != "method_validation_only":
        raise ValueError("Invalid healthspan benchmark role/schema")
    return report
