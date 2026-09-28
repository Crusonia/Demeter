"""Verify the immutable, offline source files listed in the repository catalog."""

from __future__ import annotations

import json
from pathlib import Path

from demeter.data.ingest import digest


def verify_store(catalog: Path = Path("data/catalog.json")) -> dict:
    entries = json.loads(catalog.read_text(encoding="utf-8"))
    root = catalog.resolve().parent
    if entries["schema_version"] != 1:
        raise ValueError("Unknown source-store catalog version")
    checks = []
    for store in entries["stores"]:
        manifest_path = (root / store["manifest"]).resolve()
        if not manifest_path.is_relative_to(root):
            raise ValueError("Source manifest escapes the data directory")
        if not manifest_path.is_file():
            checks.append({"store": store["id"], "passed": False, "reason": "missing_manifest"})
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name, receipt in manifest["sources"].items():
            path = (manifest_path.parent / name).resolve()
            if path.parent != manifest_path.parent:
                raise ValueError("Source filename escapes its store")
            sha = digest(path.read_bytes()) if path.is_file() else None
            checks.append(
                {
                    "store": store["id"],
                    "file": name,
                    "expected_sha256": receipt["sha256"],
                    "actual_sha256": sha,
                    "passed": sha == receipt["sha256"],
                    "reason": "verified"
                    if sha == receipt["sha256"]
                    else "missing_file"
                    if sha is None
                    else "checksum_mismatch",
                }
            )
    return {
        "passed": bool(checks) and all(c["passed"] for c in checks),
        "files": len(checks),
        "checks": checks,
        "network_used": False,
    }
