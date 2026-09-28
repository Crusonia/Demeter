"""Verify the curated raw archive, optionally reproducing both bundles offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from demeter.data.historical import rebuild_history
from demeter.data.ingest import rebuild

ROOT = Path(__file__).resolve().parents[1]
GROUPS = (
    ("baseline", "manifest.json", "us_baseline.json", rebuild),
    ("historical", "historical_manifest.json", "historical.json", rebuild_history),
)


def verify_archive(root: Path = ROOT, *, rebuild_bundles: bool = False) -> dict:
    bundle = root / "src/demeter/data/bundled"
    archive = root / "data/sources"
    receipt = json.loads((archive / "archive.json").read_text(encoding="utf-8"))
    verified = []
    for group, manifest_name, _, _ in GROUPS:
        manifest = json.loads((bundle / manifest_name).read_text(encoding="utf-8"))
        for filename, source in manifest["sources"].items():
            if Path(filename).name != filename:
                raise ValueError(f"Invalid source filename: {filename}")
            relative = f"{group}/2026-09-26/{filename}"
            content = (archive / relative).read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            if sha != source["sha256"]:
                raise ValueError(f"Source checksum mismatch: {relative}")
            record = receipt["artifacts"][relative]
            if record["sha256"] != sha or record["bytes"] != len(content):
                raise ValueError(f"Archive receipt mismatch: {relative}")
            if record["source_manifest"] != f"src/demeter/data/bundled/{manifest_name}":
                raise ValueError(f"Archive manifest reference mismatch: {relative}")
            verified.append(relative)
    if set(receipt["artifacts"]) != set(verified):
        raise ValueError("Archive receipt contains unverified artifacts")

    # Preflight ALL source bytes before any transform. Existing files mean the
    # rebuild functions need no downloads. Temporary outputs preserve the repo.
    rebuilt = []
    if rebuild_bundles:
        with tempfile.TemporaryDirectory(prefix="demeter-source-check-") as temporary:
            destination = Path(temporary)
            for group, manifest_name, bundle_name, transform in GROUPS:
                shutil.copyfile(bundle / manifest_name, destination / manifest_name)
                transform(archive / group / "2026-09-26", destination)
                if (destination / bundle_name).read_bytes() != (bundle / bundle_name).read_bytes():
                    raise ValueError(f"Rebuilt bundle differs: {bundle_name}")
                rebuilt.append(bundle_name)
    return {"passed": True, "source_files": len(verified), "rebuilt_bundles": rebuilt}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rebuild", action="store_true", help="Compare offline rebuilds byte for byte"
    )
    arguments = parser.parse_args()
    print(json.dumps(verify_archive(rebuild_bundles=arguments.rebuild), indent=2))
