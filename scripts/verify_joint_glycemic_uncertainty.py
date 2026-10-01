"""Offline survey reproduction and optional complete engine before/after proof."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path

from demeter.data.glycemic_uncertainty import DATASET, joint_report
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry
from verify_prediabetes_benchmark import compare_registries, write_report


def assess(previous: Path | None = None) -> dict:
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    result = joint_report(registry)
    expected = Path("docs/validation/joint-glycemic-uncertainty.json").read_bytes()
    committed = json.loads(expected)
    current_hash = result["provenance"]["evidence_sha256"]
    if current_hash != registry.content_hash:
        raise ValueError("Joint survey replay does not identify the current evidence registry")
    committed_hash = committed["provenance"]["evidence_sha256"]
    actual_payload = copy.deepcopy(result)
    committed_payload = copy.deepcopy(committed)
    # Preserve the historical artifact. Only unrelated registry provenance may
    # vary; every other encoded field, including scientific gates, stays exact.
    actual_payload["provenance"].pop("evidence_sha256")
    committed_payload["provenance"].pop("evidence_sha256")
    if encoded(actual_payload) != encoded(committed_payload):
        raise ValueError("Joint survey report changed outside the registry fingerprint")
    full_bytes_equal = encoded(result) == expected
    proof = {
        "kind": "joint_glycemic_uncertainty_verification",
        "passed": True,
        "source_report_exactly_reproduced": full_bytes_equal,
        "source_report_exactly_reproduced_excluding_registry_fingerprint": True,
        "excluded_paths": ["/provenance/evidence_sha256"],
        "current_registry_sha256": current_hash,
        "committed_registry_sha256": committed_hash,
        "registry_fingerprint_changed": current_hash != committed_hash,
        "reproduction_scope": (
            "Full byte reproduction separately reported; every encoded payload field except "
            "/provenance/evidence_sha256 is reproduced exactly"
        ),
        "protocol_sha256": result["provenance"]["protocol_sha256"],
        "model_role": "benchmark_only",
        "direct_initialization_allowed": False,
    }
    if previous is not None:
        old = EvidenceRegistry.from_yaml(previous)
        if old.parameters != registry.parameters or old.sources != registry.sources:
            raise ValueError(
                "Joint survey work changed prior parameters or clinical source records"
            )
        if registry.datasets.keys() - old.datasets.keys() != {DATASET} or any(
            registry.datasets.get(key) != value for key, value in old.datasets.items()
        ):
            raise ValueError("Joint survey work changed prior datasets or undeclared definitions")
        before_after = compare_registries(previous)
        before_after["interpretation"] = (
            "Empirical sampling covariance added only; no engine or clinical initialization change"
        )
        proof["before_after"] = before_after
        proof["prior_parameters_and_sources_identical"] = True
        proof["prior_datasets_identical"] = True
        proof["added_dataset"] = DATASET
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-registry", type=Path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    parser.add_argument("--output", type=Path, default=Path(f"outputs/joint-survey-{stamp}.json"))
    options = parser.parse_args()
    verification = assess(options.previous_registry)
    write_report(verification, options.output)
    print(encoded({key: verification[key] for key in ("passed", "model_role")}).decode(), end="")
