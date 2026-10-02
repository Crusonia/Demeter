"""Explicit, bounded public NHANES acquisition after the committed intake freeze."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from urllib.request import urlopen

from demeter.data import nhanes_current_store as intake

DEMO_STORE = Path("data/sources/dietary/2026-09-27")
XPORT_HEADER = b"HEADER RECORD*******LIBRARY HEADER RECORD!!!!!!!"
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024  # An acquisition guard, not a scientific parameter.
TITLES = {
    "DEMO_L.xpt": "Demographic Variables and Sample Weights",
    "DIQ_L.xpt": "Diabetes",
    "GHB_L.xpt": "Glycohemoglobin",
    "GLU_L.xpt": "Plasma Fasting Glucose",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _committed_protocol() -> str:
    """Require the exact protocol in HEAD, not merely a local resealed file."""
    intake.verify_protocol()
    try:
        stored = subprocess.run(
            ["git", "show", f"HEAD:{intake.PROTOCOL_PATH.as_posix()}"],
            check=True,
            capture_output=True,
        ).stdout
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise ValueError("NHANES acquisition requires the committed intake protocol") from None
    if intake.digest(stored) != intake.PROTOCOL_SHA256:
        raise ValueError("Committed NHANES intake protocol identity mismatch")
    return head


def _download(name: str) -> bytes:
    url = intake.PUBLIC_BASE + name
    try:
        with urlopen(url, timeout=60) as response:
            final = urlparse(response.geturl())
            if (
                response.status != 200
                or final.scheme != "https"
                or final.netloc != "wwwn.cdc.gov"
                or final.query
                or final.path != urlparse(url).path
            ):
                raise ValueError("Unexpected NHANES public download response")
            content = response.read(MAX_DOWNLOAD_BYTES + 1)
    except Exception:
        raise ValueError(
            "NHANES public download unavailable; no access workaround attempted"
        ) from None
    if len(content) > MAX_DOWNLOAD_BYTES or not content.startswith(XPORT_HEADER):
        raise ValueError("NHANES public download is not a bounded XPORT component")
    return content


def fetch(destination: Path = intake.STORE, demographics: Path = DEMO_STORE) -> dict:
    """Fetch once without parsing records. Existing destinations are never overwritten."""
    protocol = intake.verify_protocol()
    parent_commit = _committed_protocol()
    original_manifest_content = intake._read(demographics / "manifest.json", "reuse manifest")
    original_manifest = intake._json(original_manifest_content)
    original = original_manifest["sources"]["DEMO_L.xpt"]
    demo_content = intake._read(demographics / "DEMO_L.xpt", "reuse component")
    intake.verify_demographics_reuse(protocol, original_manifest_content, original, demo_content)
    if destination.exists():
        raise ValueError("NHANES acquisition destination already exists; overwrite refused")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    receipts = {}
    started_at = _now()
    for name in intake.COLUMNS:
        content = demo_content if name == "DEMO_L.xpt" else _download(name)
        with (destination / name).open("xb") as file:
            file.write(content)
        receipt = {
            "url": intake.PUBLIC_BASE + name,
            "codebook_url": intake.PUBLIC_BASE + name.replace(".xpt", ".htm"),
            "publisher": "CDC/NCHS",
            "title": TITLES[name],
            "vintage": "August 2021-August 2023",
            "format": "SAS XPORT",
            "bytes": len(content),
            "sha256": intake.digest(content),
            "use_terms": intake.USE_TERMS,
            "model_role": "benchmark_only",
            "acquisition_kind": "download",
            "retrieved_at": _now(),
        }
        if name == "DEMO_L.xpt":
            receipt.update(
                acquisition_kind="reuse",
                retrieved_at=original["retrieved_at"],
                reused_at=_now(),
                original_acquisition={
                    "source_store": DEMO_STORE.as_posix(),
                    "source_manifest_sha256": intake.digest(original_manifest_content),
                    "url": original["url"],
                    "retrieved_at": original["retrieved_at"],
                    "sha256": original["sha256"],
                    "bytes": original["bytes"],
                },
            )
        receipts[name] = receipt
    manifest = {
        "schema_version": 1,
        "protocol_path": intake.PROTOCOL_PATH.as_posix(),
        "protocol_sha256": intake.PROTOCOL_SHA256,
        "source_store": intake.STORE.as_posix(),
        "acquisition_started_at": started_at,
        "acquisition_finished_at": _now(),
        "prior_protocol_commit": parent_commit,
        "participant_records_parsed": False,
        "sources": receipts,
    }
    with (destination / "manifest.json").open("xb") as file:
        file.write((json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="Explicitly authorize public downloads"
    )
    parser.add_argument("--destination", type=Path, default=intake.STORE)
    parser.add_argument("--demographics-store", type=Path, default=DEMO_STORE)
    args = parser.parse_args()
    if not args.download:
        parser.error("Use --download for this explicit online acquisition")
    try:
        manifest = fetch(args.destination, args.demographics_store)
    except (ValueError, OSError, KeyError):
        print(
            "Public NHANES acquisition failed; source files are never overwritten. No records exported."
        )
        return 1
    print(
        json.dumps(
            {
                "kind": "nhanes_current_source_acquisition",
                "schema_version": 1,
                "sources": {
                    name: {"sha256": row["sha256"], "bytes": row["bytes"]}
                    for name, row in manifest["sources"].items()
                },
                "participant_records_parsed": False,
            },
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
