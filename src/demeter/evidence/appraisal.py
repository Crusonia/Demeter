from __future__ import annotations

import hashlib
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import numpy as np

from demeter.model import REQUIRED_UNITS
from demeter.schema import EvidenceRegistry, TableExtraction


class _Tables(HTMLParser):
    """Extract textual HTML cells without guessing headers or statistical meaning."""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise ValueError("Nested tables require a reviewed extraction")
            self.table = []
        elif self.table is not None and tag == "tr":
            self.row = []
        elif self.row is not None and tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def extract_interval(content: bytes, spec: TableExtraction) -> tuple[float, float, float]:
    """Return point/lower/upper, preserving a published CI as an interval only."""
    parser = _Tables()
    parser.feed(content.decode("utf-8"))
    try:
        rows = [r for r in parser.tables[spec.table_index] if r and r[0] == spec.row_label]
        cell = rows[spec.row_occurrence][spec.column_index]
    except IndexError as exc:
        raise ValueError("Pinned table locator no longer matches the source") from exc
    pattern = r"([0-9.]+)\s*\(([0-9.]+)[,\-–]\s*([0-9.]+)\)"
    match = re.fullmatch(pattern, cell)
    if match is None:
        raise ValueError(f"Expected point and confidence interval, got {cell!r}")
    value, low, high = (float(v) * spec.scale for v in match.groups())
    if not all(np.isfinite([value, low, high])) or not 0 <= low <= value <= high:
        raise ValueError("Invalid source interval")
    return value, low, high


def _verify_dataset(registry: EvidenceRegistry, key: str, path: Path) -> dict:
    """Dispatch explicit dataset contracts; an unrecognized contract cannot pass."""
    from demeter.analysis.food_intake import reproduce_intake
    from demeter.analysis.public_cohort import audit_public_cohort

    verifiers = {
        "food_intake_reproduction": (reproduce_intake, "published_reproduction_passed"),
        "chen_public_intake": (audit_public_cohort, "source_reproduction_passed"),
    }
    if key not in verifiers:
        return {"dataset": key, "passed": False, "reason": "unsupported_dataset_verification"}
    verify, pass_field = verifiers[key]
    try:
        report = verify(registry, path)
    except (ValueError, OSError) as exc:
        return {"dataset": key, "passed": False, "reason": str(exc)}
    return {
        "dataset": key,
        "passed": report["results"][pass_field],
        "analysis_id": report["analysis_id"],
        "results": report["results"],
    }


def verify_sources(registry: EvidenceRegistry, raw: Path, download: bool = False) -> dict:
    """Verify receipts, clinical tables and dataset audits without rewriting evidence."""
    checks = []
    for source_id, source in registry.sources.items():
        path = raw / source.raw_filename
        if download and not path.exists():
            raw.mkdir(parents=True, exist_ok=True)
            request = urllib.request.Request(source.url, headers={"User-Agent": "Demeter/0.1"})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    content = response.read()
            except OSError as exc:
                checks.append(
                    {
                        "source": source_id,
                        "passed": False,
                        "reason": "download_failed",
                        "error": str(exc),
                    }
                )
                continue
            if hashlib.sha256(content).hexdigest() != source.sha256:
                checks.append(
                    {"source": source_id, "passed": False, "reason": "download_checksum_mismatch"}
                )
                continue
            path.write_bytes(content)
        if not path.exists():
            checks.append({"source": source_id, "passed": False, "reason": "missing_raw_artifact"})
            continue
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != source.sha256:
            checks.append({"source": source_id, "passed": False, "reason": "checksum_mismatch"})
            continue
        parameters = []
        for key, p in registry.parameters.items():
            if p.source_id != source_id or p.applicability is None:
                continue
            try:
                triple = extract_interval(content, p.applicability.extraction)
                passed = (
                    p.uncertainty is not None
                    and p.uncertainty.kind == "interval"
                    and bool(
                        np.allclose(
                            triple,
                            [p.value, p.uncertainty.low, p.uncertainty.high],
                            rtol=0,
                            atol=1e-12,
                        )
                    )
                )
                parameters.append({"parameter": key, "passed": passed, "extracted": triple})
            except ValueError as exc:
                parameters.append({"parameter": key, "passed": False, "reason": str(exc)})
        datasets = [
            _verify_dataset(registry, key, path)
            for key, dataset in registry.datasets.items()
            if dataset.get("source_id") == source_id
        ]
        checks.append(
            {
                "source": source_id,
                "passed": bool(parameters or datasets)
                and all(p["passed"] for p in parameters + datasets),
                "checksum_passed": True,
                "sha256": source.sha256,
                "parameters": parameters,
                "datasets": datasets,
                **({"reason": "no_registered_verification"} if not parameters + datasets else {}),
            }
        )
    return {
        "passed": bool(checks) and all(c["passed"] for c in checks),
        "evidence_sha256": registry.content_hash,
        "checks": checks,
        "interpretation": "Verifies source checksums, registered table extractions and dataset reproductions; not causal identification or national transportability.",
    }


def applicability_report(registry: EvidenceRegistry) -> dict:
    rows = []
    for target, unit in REQUIRED_UNITS.items():
        p = registry.parameters.get(target)
        candidates = []
        for key, candidate in registry.parameters.items():
            a = candidate.applicability
            if a is not None and target in a.candidate_for:
                candidates.append(
                    {
                        "parameter": key,
                        "value": candidate.value,
                        "unit": candidate.unit,
                        "uncertainty": candidate.uncertainty.model_dump()
                        if candidate.uncertainty
                        else None,
                        "source_id": candidate.source_id,
                        "applicability": a.model_dump(),
                    }
                )
        rows.append(
            {
                "model_input": target,
                "required_unit": unit,
                "current_status": p.status if p else "missing",
                "candidates": candidates,
                "replacement_identified": False,
            }
        )
    return {
        "evidence_sha256": registry.content_hash,
        "scientific_release_ready": False,
        "inputs": rows,
        "scientific_blockers": registry.scientific_blockers,
        "interpretation": "Source-backed benchmarks are not accepted national engine parameters. No pooled rate or causal effect is inferred.",
    }
