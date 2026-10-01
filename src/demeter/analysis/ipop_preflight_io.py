"""Offline receipt-based iPOP intake and exclusive aggregate report publication."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path

from demeter.analysis.ipop_preflight import load_frozen_protocol, preflight_bytes
from demeter.data.ipop import load_sources


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except RuntimeError:
        raise ValueError("protected_or_existing_report_path") from None


def _linked_parent(path: Path) -> bool:
    for parent in (path, *path.parents):
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            return True
        try:
            attributes = getattr(parent.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            return True
    return False


def audit_preflight(raw_directory: Path) -> dict:
    """Verify the frozen selection and immutable acquisition before parsing records."""
    protocol = load_frozen_protocol()
    acquisition = load_sources(raw_directory, protocol)
    if acquisition["passed"]:
        sources = acquisition["sources"]
        report = preflight_bytes(
            sources["clinical"], sources["sample_info"], protocol=protocol, validation_only=False
        )
        if report["source_audit"]["passed"]:
            report["provenance"]["acquisition_receipts_verified"] = True
            report["provenance"]["verification_scope"] = (
                "historical acquisition receipt metadata and current complete frozen-source "
                "byte identity, selected structure and aggregate preservation only"
            )
    else:
        # Empty, identity-invalid bytes cannot reach a participant parser. Reuse
        # the core's constant failure schema without interpreting any source.
        report = preflight_bytes(b"", b"", protocol=protocol, validation_only=False)
        report["source_audit"]["failure_stage"] = "acquisition_receipts_or_cached_bytes"
    report["analysis_id"] = "ipop_public_linked_file_preflight_v1"
    report["model_role"] = "source_intake_only"
    report["acquisition_audit"] = {
        "passed": acquisition["passed"],
        "receipt_saved": acquisition["receipt_saved"],
        "provenance": acquisition["provenance"],
    }
    report["intake_implementation_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    json.dumps(report, allow_nan=False)
    return report


def audit_crosswalk(raw_directory: Path) -> dict:
    """Replay the separately frozen namespace hypothesis with verified source receipts."""
    from demeter.analysis.ipop_crosswalk import (
        load_frozen_crosswalk_protocol,
        preflight_crosswalk_bytes,
    )

    # Freeze verification precedes cache access. Acquisition remains bound to
    # the original two-file v1 selection; the v2 hypothesis changes no bytes.
    protocol = load_frozen_crosswalk_protocol()
    acquisition = load_sources(raw_directory, load_frozen_protocol())
    if acquisition["passed"]:
        sources = acquisition["sources"]
        report = preflight_crosswalk_bytes(
            sources["clinical"], sources["sample_info"], protocol=protocol, validation_only=False
        )
        if report["source_audit"]["passed"]:
            report["provenance"]["acquisition_receipts_verified"] = True
            report["provenance"]["verification_scope"] = (
                "historical acquisition receipt metadata and current complete frozen-source "
                "byte identity, selected structure and conditional namespace-association "
                "aggregates only; participant identity and clinical acceptance unverified"
            )
    else:
        report = preflight_crosswalk_bytes(b"", b"", protocol=protocol, validation_only=False)
        report["source_audit"]["failure_stage"] = "acquisition_receipts_or_cached_bytes"
    report["analysis_id"] = "ipop_public_namespace_crosswalk_preflight_v2"
    report["model_role"] = "source_intake_only"
    report["acquisition_audit"] = {
        "passed": acquisition["passed"],
        "receipt_saved": acquisition["receipt_saved"],
        "provenance": acquisition["provenance"],
    }
    report["intake_implementation_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    json.dumps(report, allow_nan=False)
    return report


def write_fresh_report(report: dict, output: Path, raw_directory: Path) -> None:
    """Keep reports outside source/evidence paths and never replace existing bytes."""
    root = _safe_resolve(Path.cwd())
    target = _safe_resolve(output)
    protected = (
        _safe_resolve(raw_directory),
        root / "data/raw",
        root / "data/sources",
        root / "data/processed",
        root / "evidence",
        root / "docs/validation",
        root / "src",
        root / ".git",
    )
    if (
        output.exists()
        or output.is_symlink()
        or any(target.is_relative_to(path) for path in protected)
        or target in (root / "data/rights.json", root / "data/evidence-packages.json")
        or _linked_parent(output)
    ):
        raise ValueError("protected_or_existing_report_path")
    encoded = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(encoded)
