"""Verify registered Kerala source receipts and optionally replay aggregate counts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from demeter.analysis.kerala_registration import verify_registered
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path)
    parser.add_argument("--replay-aggregates", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error("Output already exists; preserve receipts with a new filename")
    try:
        result = verify_registered(
            EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml"),
            ROOT,
            args.source_cache,
            replay_aggregates=args.replay_aggregates,
        )
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"registered_artifacts_verified": False, "error": str(error)}))
        return 1
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf8", newline="\n") as stream:
            stream.write(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
