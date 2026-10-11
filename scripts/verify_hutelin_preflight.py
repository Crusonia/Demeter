"""Replay Hutelin's selected public source identities and two CSV headers offline."""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from pathlib import Path

from demeter.data.hutelin_preflight import audit_hutelin_preflight

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = audit_hutelin_preflight(
            args.raw_dir, ROOT / "docs/validation/hutelin2026-preflight-contract-v1.json"
        )
        content = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
    except (ValueError, OSError, KeyError, TypeError, csv.Error, zipfile.BadZipFile):
        print("Hutelin documentary/header preflight failed; no participant output produced")
        return 1
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
