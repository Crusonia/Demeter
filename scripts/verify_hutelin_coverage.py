"""Inspect finite selected-field coverage in Hutelin's pinned public source ZIP."""

import argparse
import csv
import json
from pathlib import Path
import zipfile

from demeter.data.hutelin_coverage import audit_hutelin_coverage

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit_hutelin_coverage(args.raw_dir, ROOT)
        content = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
    except (ValueError, OSError, KeyError, TypeError, csv.Error, zipfile.BadZipFile):
        print("Hutelin coverage failed; no partial or participant result exported")
        return 1
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
