"""Evaluate RFC-55 without fitting; explicit --download is the first outcome intake."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from urllib.request import urlopen

from demeter.analysis.mortality_validation import PROTOCOL, STORE, load_protocol, validation_report
from demeter.data.ingest import digest


def download(root: Path) -> Path:
    protocol = load_protocol(root)
    # The protocol and its interpreter must exist in a prior committed snapshot.
    # This proves chronology within this repository, not blinding of other researchers.
    sha = digest((root / PROTOCOL).read_bytes())
    committed = subprocess.check_output(["git", "show", "HEAD:" + PROTOCOL.as_posix()], cwd=root)
    if digest(committed) != sha:
        raise ValueError("Commit the frozen protocol before retrieving reserved outcomes")
    freeze_commit = subprocess.check_output(
        ["git", "log", "--format=%H", "--diff-filter=A", "--", PROTOCOL.as_posix()],
        cwd=root,
        text=True,
    ).strip()
    if not freeze_commit or "\n" in freeze_commit:
        raise ValueError("A unique pre-outcome protocol commit is required")
    for path, expected in protocol["protected_files"].items():
        original = subprocess.check_output(["git", "show", freeze_commit + ":" + path], cwd=root)
        if digest(original) != expected:
            raise ValueError(f"Protocol implementation was not frozen at registration: {path}")
    destination = root / STORE
    manifest_path = destination / "manifest.json"
    if manifest_path.exists():
        raise ValueError("Reserved sources already archived; use the offline command")
    destination.mkdir(parents=True, exist_ok=True)
    # Individual receipts make a partially interrupted first intake resumable.
    receipts_path = destination / "intake.json"
    if receipts_path.exists():
        manifest = json.loads(receipts_path.read_bytes())
        if (
            manifest["protocol_sha256"] != sha
            or manifest["protocol_freeze_commit"] != freeze_commit
        ):
            raise ValueError("Existing intake belongs to another protocol")
    else:
        manifest = {
            "schema_version": 1,
            "cycle": "2013-2014",
            "protocol_sha256": sha,
            "protocol_freeze_commit": freeze_commit,
            "usage": "Public-use statistical analysis only; no identification; retain CDC/NCHS terms.",
            "sources": {},
        }
    for name, metadata in protocol["sources"].items():
        path = destination / name
        if path.exists():
            if (
                name not in manifest["sources"]
                or digest(path.read_bytes()) != manifest["sources"][name]["sha256"]
            ):
                raise ValueError(f"Unreceipted or modified first-intake source: {name}")
            continue
        with urlopen(metadata["url"], timeout=120) as response:
            content = response.read()
        if name.endswith(".xpt") and not content.startswith(b"HEADER RECORD"):
            raise ValueError(f"Not an XPORT source: {name}")
        if name.endswith(".dat") and (not content or content.lstrip().startswith(b"<")):
            raise ValueError(f"Not a mortality fixed-width source: {name}")
        path.write_bytes(content)
        manifest["sources"][name] = {
            **metadata,
            "sha256": digest(content),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }
        receipts_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"Archived official source: {name}", flush=True)
    receipts_path.replace(manifest_path)
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download",
        action="store_true",
        help="First intake only, after committing preregistration",
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/mortality-validation.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.download:
        download(root)
    report = validation_report(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(args.output)
