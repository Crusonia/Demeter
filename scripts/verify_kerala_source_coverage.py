"""Inspect the recorded intake boundary without accessing participant values."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kerala_admission_local", ROOT / "src/demeter/analysis/kerala_coverage.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
verify_admission = MODULE.verify_admission


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=ROOT)
    parser.add_argument("--source-cache", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify_admission(args.package_root, args.source_cache)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"artifact_pins_verified": False, "error": str(error)}))
        return 1
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
