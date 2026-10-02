"""Capture and compare complete validation outputs across source-code changes.

This complements release replay (which requires identical source bytes) and
registry comparison (which runs both registries through the current code).
Snapshots are data only; comparison never imports or executes reference code.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from demeter.analysis.experiments import uncertainty
from demeter.model import simulate
from demeter.releases import ATOL, RTOL, canonical, differences
from demeter.schema import EvidenceRegistry, Scenario

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    "baseline",
    "reduce_upf_30",
    "prechronic_baseline",
    "prechronic_reduce_upf_30",
    "diet_dynamics",
    "glp1_access",
)
UNCERTAINTY_SCENARIOS = ("reduce_upf_30", "prechronic_reduce_upf_30")
CONTRACT = {
    "schema_version": 1,
    "scenarios": list(SCENARIOS),
    "simulation_diagnostics": True,
    "uncertainty_scenarios": list(UNCERTAINTY_SCENARIOS),
    "uncertainty_draws": 4,
    "uncertainty_seed": 42,
    "uncertainty_diagnostics": True,
    "relative_tolerance": RTOL,
    "absolute_tolerance": ATOL,
    "excluded_simulation_paths": ["/metadata/evidence_sha256", "/healthspan/evidence_sha256"],
    "excluded_uncertainty_paths": ["/metadata/evidence_sha256"],
    "interpretation": "Software regression only; synthetic outputs are not clinical findings. "
    "Four fixed-seed draws check reproducibility, not uncertainty convergence.",
}


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def normalized(result: dict, *, simulation: bool) -> dict:
    """Omit exactly declared registry identity paths; keep all other semantics."""
    value = deepcopy(result)
    value["metadata"].pop("evidence_sha256")
    if simulation:
        value["healthspan"].pop("evidence_sha256")
    return value


def capture(root: Path = ROOT) -> dict:
    root = root.resolve()
    # Do not stamp checkout receipts over a wheel or another editable checkout.
    # The CLI runs in a fresh process; loaded Demeter modules must come from the
    # source tree whose inputs and Git state this snapshot records.
    source = (root / "src/demeter").resolve()
    for name, module in list(sys.modules.items()):
        if name == "demeter" or name.startswith("demeter."):
            filename = getattr(module, "__file__", None)
            if filename is not None and not Path(filename).resolve().is_relative_to(source):
                raise ValueError("Loaded Demeter runtime is outside the captured source checkout")
    from demeter.data.ingest import BUNDLE

    if BUNDLE.resolve() != source / "data/bundled":
        raise ValueError("Loaded source bundle is outside the captured source checkout")
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    scenarios = {
        name: Scenario.from_yaml(root / "scenarios" / f"{name}.yaml") for name in SCENARIOS
    }
    results = {
        name: normalized(simulate(registry, scenario, diagnostics=True).to_dict(), simulation=True)
        for name, scenario in scenarios.items()
    }
    sampled = {
        name: normalized(
            uncertainty(registry, scenarios[name], draws=4, seed=42, diagnostics=True),
            simulation=False,
        )
        for name in UNCERTAINTY_SCENARIOS
    }
    source_files = sorted((root / "src/demeter").rglob("*.py"))
    source_receipts = {
        path.relative_to(root).as_posix(): sha256(path.read_bytes()) for path in source_files
    }

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, encoding="utf-8"
        ).strip()

    payload = {
        "contract": deepcopy(CONTRACT),
        "provenance": {
            "git_commit": git("rev-parse", "HEAD"),
            "working_tree_dirty": bool(git("status", "--porcelain")),
            "python": sys.version,
            "evidence_file_sha256": sha256((root / "evidence/parameters.yaml").read_bytes()),
            "evidence_content_sha256": registry.content_hash,
            "runtime_source_sha256": sha256(canonical(source_receipts)),
            "runtime_source_files": source_receipts,
            "parity_script_sha256": sha256(Path(__file__).read_bytes()),
            "scenario_file_sha256": {
                name: sha256((root / "scenarios" / f"{name}.yaml").read_bytes())
                for name in SCENARIOS
            },
        },
        "simulations": results,
        "uncertainty": sampled,
    }
    # Compare the JSON contract, including NumPy scalars that serialize as JSON
    # floats. A saved reference has built-in numeric types on reloading too.
    payload = json.loads(canonical(payload))
    return {"payload_sha256": sha256(canonical(payload)), "payload": payload}


def checked_payload(snapshot: dict) -> dict:
    if type(snapshot) is not dict or set(snapshot) != {"payload_sha256", "payload"}:
        raise ValueError("Unexpected parity snapshot envelope")
    payload = snapshot["payload"]
    if type(payload) is not dict or set(payload) != {
        "contract",
        "provenance",
        "simulations",
        "uncertainty",
    }:
        raise ValueError("Incomplete parity snapshot")
    if snapshot["payload_sha256"] != sha256(canonical(payload)):
        raise ValueError("Parity snapshot checksum mismatch")
    if canonical(payload["contract"]) != canonical(CONTRACT):
        raise ValueError("Parity snapshot contract mismatch; never silently change the reference")
    if (
        type(payload["simulations"]) is not dict
        or set(payload["simulations"]) != set(SCENARIOS)
        or type(payload["uncertainty"]) is not dict
        or set(payload["uncertainty"]) != set(UNCERTAINTY_SCENARIOS)
        or type(payload["provenance"]) is not dict
    ):
        raise ValueError("Incomplete parity scenario inventory")
    return payload


def compare_snapshots(reference: dict, current: dict) -> dict:
    before, after = checked_payload(reference), checked_payload(current)
    checks = {}
    for group in ("simulations", "uncertainty"):
        for name in before[group]:
            a, b = before[group][name], after[group][name]
            mismatches = differences(a, b, f"/{group}/{name}")
            checks[f"{group}/{name}"] = {
                "passed": not mismatches,
                "exactly_equal": a == b,
                "mismatch_count": len(mismatches),
                "first_mismatches": mismatches[:20],
            }
    return {
        "passed": all(check["passed"] for check in checks.values()),
        "scientific_acceptance": False,
        "reference_payload_sha256": reference["payload_sha256"],
        "current_payload_sha256": current["payload_sha256"],
        "reference_provenance": before["provenance"],
        "current_provenance": after["provenance"],
        "contract": deepcopy(CONTRACT),
        "checks": checks,
        "scope": "Complete annual, final cohort, original-cohort state-time, diagnostic life-table, "
        "active hazard evidence, flow "
        "and fixed-seed uncertainty outputs. Source/evidence provenance is reported separately; "
        "only the declared evidence identity paths are omitted from results. "
        "Parity does not establish correctness, independent validation or clinical calibration.",
    }


def write_new(path: Path, value: dict) -> None:
    encoded = canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded)


def read_snapshot(path: Path) -> dict:
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON constant: {value}")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key in parity snapshot")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=unique_keys,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot", help="Capture outputs before changing source code")
    snapshot.add_argument("--output", type=Path, required=True)
    comparison = commands.add_parser("compare", help="Recompute current outputs against a snapshot")
    comparison.add_argument("--reference", type=Path, required=True)
    comparison.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    if options.output.exists():
        parser.error("Output already exists; use a new path to preserve the reference")
    if options.command == "snapshot":
        write_new(options.output, capture())
        print(f"Saved validation-only parity reference: {options.output}")
        return 0
    reference = read_snapshot(options.reference)
    checked_payload(reference)
    report = compare_snapshots(reference, capture())
    write_new(options.output, report)
    print(f"Model parity {'passed' if report['passed'] else 'FAILED'}: {options.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
