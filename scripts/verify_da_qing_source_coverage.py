"""Verify Da Qing literal aggregate extraction while preserving source failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from demeter.analysis.da_qing_coverage import verify_registered
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article-cache", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_registered(
        EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml"), ROOT, args.article_cache
    )
    text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf8", newline="\n") as handle:
            handle.write(text)
    print(text, end="")
    # A reproducible audit is distinct from an internally consistent source.
    # Current publication inconsistency must remain a nonzero disposition.
    return 0 if result["source_consistency_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
