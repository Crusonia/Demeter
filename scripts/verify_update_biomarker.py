"""Replay published UPDATE biomarker summaries offline, optionally against its PDF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from demeter.data.update_biomarker import audit_update_biomarker
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pdf", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
        report = audit_update_biomarker(registry, ROOT, source_pdf=args.source_pdf)
        content = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as output:
                output.write(content)
    except (ValueError, OSError, KeyError, TypeError, IndexError):
        print("UPDATE public biomarker source-summary replay failed")
        return 1
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
