"""Replay finite prepared-column pattern counts without clinical qualification."""

import argparse
import csv
import json
from pathlib import Path
import zipfile

from demeter.data.hutelin_preparation import audit_preparation
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
        result = audit_preparation(args.raw_dir, ROOT, registry)
        content = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
    except (ValueError, OSError, KeyError, TypeError, csv.Error, zipfile.BadZipFile):
        print("Hutelin preparation diagnostic failed; no participant or partial output exported")
        return 1
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
