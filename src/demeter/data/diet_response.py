"""Reload factual historical challenge data without transporting trial effects into the engine."""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

from demeter.data.ingest import BUNDLE, digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

DATASET = "diet_response_challenge"
STORE = Path("data/sources/diet-dynamics/2026-09-27")


def rebuild_challenge(
    registry: EvidenceRegistry, source: Path = STORE, destination: Path = BUNDLE
) -> dict:
    spec = registry.datasets[DATASET]
    if spec["model_role"] != "historical_challenge_only":
        raise ValueError("Trial trajectory must remain historical_challenge_only")
    receipt = json.loads((source / "manifest.json").read_bytes())
    if set(receipt["sources"]) != {"niddk-look-ahead.html", "look-ahead-extract.json"}:
        raise ValueError("Invalid historical challenge source manifest")
    for name, record in receipt["sources"].items():
        if digest((source / name).read_bytes()) != record["sha256"]:
            raise ValueError(f"Historical challenge source checksum mismatch: {name}")
    facts = json.loads((source / "look-ahead-extract.json").read_bytes())
    expected = {(year, arm) for year in spec["years"] for arm in ("lifestyle", "control")}
    if {(r["year"], r["arm"]) for r in facts["rows"]} != expected or len(facts["rows"]) != len(
        expected
    ):
        raise ValueError("Missing or duplicate trial observations")
    for r in facts["rows"]:
        if (
            not 0 <= r["low"] <= r["value"] <= r["high"] <= 100
            or not 0 <= r["cases"] <= r["n"]
            or r["n"] <= 0
        ):
            raise ValueError("Invalid trial observation")
        if abs(100 * r["cases"] / r["n"] - r["value"]) > spec["rounding_tolerance_percent"]:
            raise ValueError("Trial counts do not reconcile to published percentage")
    html = (source / "niddk-look-ahead.html").read_text(encoding="utf-8")
    text = " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())
    patterns = [
        r"After one year, about ([0-9.]+) percent",
        r"By the fourth year of the study, ([0-9.]+) percent",
    ]
    corroboration = []
    for year, pattern in zip(spec["corroborated_years"], patterns, strict=True):
        match = re.search(pattern, text)
        expected_value = next(
            r["value"] for r in facts["rows"] if (r["year"], r["arm"]) == (year, "lifestyle")
        )
        if not match or float(match[1]) != expected_value:
            raise ValueError("Official NIDDK summary disagrees with trial extraction")
        corroboration.append({"year": year, "value": float(match[1]), "passed": True})
    report = {
        "schema_version": 1,
        "model_role": spec["model_role"],
        "scientific_release_ready": False,
        "facts": facts,
        "corroboration": corroboration,
        "limitations": spec["limitations"],
        "provenance": {
            "sources": receipt["sources"],
            "definition_sha256": digest(encoded(spec)),
            "transform": "demeter.data.diet_response.rebuild_challenge",
        },
    }
    content = encoded(report)
    manifest = {
        "schema_version": 1,
        "bundle_sha256": digest(content),
        "definition_sha256": digest(encoded(spec)),
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "diet_response_challenge.json").write_bytes(content)
    (destination / "diet_response_manifest.json").write_bytes(encoded(manifest))
    return manifest


def load_challenge(registry: EvidenceRegistry, bundle: Path = BUNDLE) -> dict:
    content = (bundle / "diet_response_challenge.json").read_bytes()
    manifest = json.loads((bundle / "diet_response_manifest.json").read_bytes())
    if (
        digest(content) != manifest["bundle_sha256"]
        or digest(encoded(registry.datasets[DATASET])) != manifest["definition_sha256"]
    ):
        raise ValueError("Diet response challenge checksum or definition mismatch")
    report = json.loads(content)
    if report["model_role"] != "historical_challenge_only" or report["scientific_release_ready"]:
        raise ValueError("Invalid trial challenge role")
    return report
