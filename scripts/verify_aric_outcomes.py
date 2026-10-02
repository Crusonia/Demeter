"""Verify ARIC publication partitions offline or replay both pinned public sources."""

from __future__ import annotations

import argparse
from pathlib import Path

from demeter.analysis.aric_outcomes_audit import audit_aric_outcomes
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path)
    args = parser.parse_args()
    try:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
        report = audit_aric_outcomes(registry, ROOT, source_cache=args.source_cache)
        if not report["registered_artifacts_verified"]:
            raise ValueError("ARIC verification failed")
    except (ValueError, OSError, KeyError, TypeError, IndexError):
        print("ARIC public outcome verification failed")
        return 1
    mode = "both public sources reproduced" if args.source_cache else "offline facts; raw not read"
    print("ARIC outcomes: " + mode + "; conditional source accounting, no clinical fit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
