"""An isolated, synthetic two-container lesson; not a health-model component."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path

from demeter.schema import EvidenceRegistry

UNITS = {
    "toy_initial_tokens": "tokens",
    "toy_target_fraction": "fraction_per_tick",
    "toy_response_fraction": "fraction",
}


def run(registry: EvidenceRegistry, *, steps: int = 4) -> dict:
    """Return boundary stocks and preceding-interval transfers, in abstract ticks."""
    if type(steps) is not int or not 1 <= steps <= 1000:
        raise ValueError("steps must be an integer from 1 to 1000")
    values = {}
    for key, unit in UNITS.items():
        p = registry.parameters.get(key)
        if p is None or p.unit != unit:
            raise ValueError(f"Missing parameter or wrong units: {key} requires {unit}")
        value = registry.value(key)
        if (
            not isfinite(value)
            or value < 0
            or (key != "toy_initial_tokens" and value > 1)
            or p.uncertainty is None
            or p.status != "synthetic"
            or p.model_role != "benchmark_only"
        ):
            raise ValueError(f"Invalid synthetic teaching parameter: {key}")
        values[key] = value
    remaining = values["toy_initial_tokens"]
    received = effective = 0.0
    rows = [
        {
            "tick": 0,
            "remaining": remaining,
            "received": received,
            "effective_fraction": effective,
            "transfer": 0.0,
        }
    ]
    for tick in range(1, steps + 1):
        effective += values["toy_response_fraction"] * (values["toy_target_fraction"] - effective)
        transfer = remaining * effective
        remaining -= transfer
        received += transfer
        rows.append(
            {
                "tick": tick,
                "remaining": remaining,
                "received": received,
                "effective_fraction": effective,
                "transfer": transfer,
            }
        )
    return {
        "kind": "demeter_stock_flow_lesson",
        "validation_only": True,
        "limitations": "Invented tokens and abstract ticks; no clinical or empirical interpretation.",
        "units": {"remaining": "tokens", "received": "tokens", "transfer": "tokens_in_tick"},
        "steps": steps,
        "registry_sha256": registry.content_hash,
        "parameters": {k: registry.parameters[k].model_dump(mode="json") for k in UNITS},
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=Path("evidence/parameters.yaml"))
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(run(EvidenceRegistry.from_yaml(args.evidence), steps=args.steps), indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8", newline="\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
