"""Verify the Malawi aggregate benchmark offline or against pinned public XML."""

from __future__ import annotations

import argparse
from pathlib import Path

from demeter.analysis.malawi_cohort_audit import audit_malawi_cohort
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path)
    args = parser.parse_args()
    try:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
        report = audit_malawi_cohort(registry, ROOT, raw=args.raw)
        if not report["registered_artifacts_verified"]:
            raise ValueError("Registered aggregate verification failed")
    except (ValueError, OSError, KeyError, TypeError, IndexError):
        print("Malawi aggregate benchmark verification failed")
        return 1
    mode = "public XML exactly reproduced" if args.raw else "offline facts checked; raw not read"
    print("Malawi follow-up: " + mode + "; no annual hazard, sampling interval or clinical fit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
