"""Verify the frozen nominal-observation report offline or with a private raw cache."""

from __future__ import annotations

import argparse
from pathlib import Path

from demeter.analysis.kerala_observation_audit import audit_kerala_observations
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path)
    args = parser.parse_args()
    try:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
        report = audit_kerala_observations(registry, ROOT, source_cache=args.source_cache)
        if not report["registered_artifacts_verified"]:
            raise ValueError("Registered metadata verification failed")
    except (ValueError, OSError, KeyError, TypeError, IndexError):
        print("Kerala observation report verification failed")
        return 1
    result = (
        "private raw aggregates exactly reproduced"
        if args.source_cache
        else "offline metadata verified; raw values not read"
    )
    print("Kerala nominal observations: " + result + "; no source likelihood or clinical fit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
