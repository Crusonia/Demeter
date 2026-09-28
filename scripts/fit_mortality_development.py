"""Run RFC-1's optional development benchmark without modifying model inputs."""

import argparse
import json
from pathlib import Path

from demeter.analysis.mortality_development import development_report
from demeter.schema import EvidenceRegistry

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/mortality-development.json"))
    args = parser.parse_args()
    report = development_report(EvidenceRegistry.from_yaml("evidence/parameters.yaml"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(report, indent=2, allow_nan=False) + "\n").encode())
    print(args.output)
