"""Replay the frozen iPOP bootstrap for an additive, post-outcome score summary.

No complete-data fit/profile is rerun, and no original report is overwritten.
Only aggregate bootstrap score differences leave the verified private cache.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from demeter.analysis import ipop_a1c as a1c
from demeter.analysis import laboratory_bootstrap_reporting as reporting
from demeter.analysis import laboratory_panel as lab
from demeter.data.ipop import load_sources
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = "docs/validation/ipop-a1c-predictive-summary-protocol-v1.json"
POLICY_SHA256 = "967c74c8c6d5bb208f307009b0198b8ec53abc2376594153cccb5d20af04818a"
IMPLEMENTATIONS = (
    "src/demeter/analysis/ipop_a1c.py",
    "src/demeter/analysis/laboratory_panel.py",
    "src/demeter/analysis/laboratory_bootstrap_reporting.py",
    "scripts/replay_ipop_predictive_supplement.py",
)


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def contract():
    if digest(POLICY_PATH) != POLICY_SHA256:
        raise ValueError("Reporting policy identity failed")
    policy = json.loads((ROOT / POLICY_PATH).read_text(encoding="utf-8"))
    for group in ("frozen_implementations", "inherited_protocols"):
        for path, expected in policy[group].items():
            if digest(path) != expected:
                raise ValueError("Frozen implementation or protocol identity failed")
    parent = policy["parent_result"]
    if digest(parent["path"]) != parent["sha256"]:
        raise ValueError("Preserved parent result identity failed")
    protocol = a1c.load_protocol()
    a1c.load_numerical_protocol(numerical_method="exact_box_quadratic_v2")
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    a1c._registry_contract(registry, protocol, ROOT, numerical_method="exact_box_quadratic_v2")
    return policy, protocol, json.loads((ROOT / parent["path"]).read_text(encoding="utf-8"))


def replay(raw_directory, *, freeze_commit):
    # All frozen source/design contracts precede cache access.
    policy, protocol, parent = contract()
    implementation_hashes = {path: digest(path) for path in IMPLEMENTATIONS}
    if len(freeze_commit) != 40 or any(c not in "0123456789abcdef" for c in freeze_commit):
        raise ValueError("A full frozen Git commit is required")
    for path in (*IMPLEMENTATIONS, POLICY_PATH):
        frozen = subprocess.check_output(["git", "show", f"{freeze_commit}:{path}"], cwd=ROOT)
        if hashlib.sha256(frozen).hexdigest() != digest(path):
            raise ValueError("Current implementation differs from the frozen commit")
    started = datetime.now(timezone.utc).isoformat()
    acquired = load_sources(raw_directory, a1c.v1.load_frozen_protocol())
    if not acquired["passed"]:
        raise ValueError("Acquisition receipt or source identity failed")
    paths, selection, source_bytes = a1c._prepare(
        acquired["sources"]["clinical"],
        acquired["sources"]["sample_info"],
        protocol,
        validation_only=False,
        crosswalk_protocol=a1c.v2.load_frozen_crosswalk_protocol(),
    )
    if selection != parent["selection"] or source_bytes != parent["provenance"]["source_bytes"]:
        raise ValueError("Source selection differs from the preserved parent")
    uncertainty = protocol["joint_uncertainty"]
    print("Replaying unchanged whole-label bootstrap; aggregate score reporting only", flush=True)
    bootstrap = lab.paired_path_bootstrap(
        paths["calibration"],
        {"adjacent": a1c.settings_for(protocol, "adjacent")},
        repetitions=uncertainty["bootstrap_replicates"],
        seed=uncertainty["seed"],
        quantile_levels=uncertainty["quantiles"],
        evaluation_paths=paths["evaluation"],
        include_iid=True,
        numerical_method="exact_box_quadratic_v2",
    )
    # Same-platform exact reconciliation, before any supplemental publication.
    expected = {k: v for k, v in parent["joint_uncertainty"].items() if k != "dispositions"}
    observed = {k: v for k, v in bootstrap.items() if k != "replicates"}
    if observed != expected:
        raise ValueError("Bootstrap replay differs from original rate or complete-vector summary")
    summaries = reporting.summarize_predictive_bootstrap(
        bootstrap, quantile_levels=uncertainty["quantiles"]
    )
    for path, expected_hash in implementation_hashes.items():
        if digest(path) != expected_hash:
            raise ValueError("Implementation changed during replay")
    return {
        "schema_version": 1,
        "analysis_id": policy["analysis_id"],
        "analysis_completed": True,
        "execution_scope": "conditional_empirical_laboratory_working_analysis",
        "validation_only": False,
        "post_outcome_reporting_amendment": True,
        "source_selection_unchanged": True,
        "full_data_fits_or_profiles_rerun": False,
        "legacy_bootstrap_summaries_reproduced_exactly": True,
        "aggregate_bootstrap_score_vectors_retained": True,
        "participant_records_or_predictions_exported": False,
        "provenance": {
            "reporting_protocol_sha256": POLICY_SHA256,
            "parent_result_sha256": policy["parent_result"]["sha256"],
            "implementation_sha256": implementation_hashes,
            "freeze_commit": freeze_commit,
            "started_at": started,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "acquisition_receipts_verified": True,
            "source_bytes": source_bytes,
            "bootstrap_seed": uncertainty["seed"],
            "numerical_method": "exact_box_quadratic_v2",
            "independent_source_validation": False,
        },
        "selection": selection,
        "predictive_uncertainty": summaries,
        **policy["activation"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a fresh output path; existing evidence is immutable")
    try:
        result = replay(args.raw, freeze_commit=args.freeze_commit)
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        with args.output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
    except Exception:
        # Do not expose private source tokens or numerical exception payloads.
        print(
            "Supplement unavailable: acquisition, frozen-contract or replay reconciliation failed"
        )
        return 1
    print("Completed additive aggregate supplement; original reports and engine gates preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
