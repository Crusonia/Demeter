"""Reproduce published paired-label observations and optional engine regression proof."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path

from demeter.analysis.geelong_labels import DATASET, audit_geelong_labels
from demeter.analysis.experiments import sampled_parameters
from demeter.data.nhanes import encoded
from demeter.data.glycemic_uncertainty import joint_report
from demeter.schema import EvidenceRegistry, Scenario
from verify_prediabetes_benchmark import compare_registries, write_report

ROOT = Path(__file__).resolve().parents[1]


def assess(previous: Path | None = None) -> dict:
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    result = audit_geelong_labels(registry)
    if not result["source_audit_passed"]:
        raise ValueError("Geelong source reproduction failed")
    expected = (ROOT / "docs/validation/issue-57-geelong-labels.json").read_bytes()
    committed = json.loads(expected)
    current_hash = result["provenance"]["registry_sha256"]
    if current_hash != registry.content_hash:
        raise ValueError("Geelong replay does not identify the current evidence registry")
    committed_hash = committed["provenance"]["registry_sha256"]
    actual_payload = copy.deepcopy(result)
    committed_payload = copy.deepcopy(committed)
    # Keep historical bytes immutable. Only the unrelated registry fingerprint
    # may vary; every other encoded field, including scientific gates, is exact.
    actual_payload["provenance"].pop("registry_sha256")
    committed_payload["provenance"].pop("registry_sha256")
    if encoded(actual_payload) != encoded(committed_payload):
        raise ValueError("Geelong report changed outside the registry fingerprint")
    proof = {
        "kind": "geelong_label_observation_verification",
        "passed": True,
        "source_report_exactly_reproduced": encoded(result) == expected,
        "source_report_exactly_reproduced_excluding_registry_fingerprint": True,
        "excluded_paths": ["/provenance/registry_sha256"],
        "current_registry_sha256": current_hash,
        "committed_registry_sha256": committed_hash,
        "registry_fingerprint_changed": current_hash != committed_hash,
        "reproduction_scope": (
            "Full byte reproduction separately reported; every encoded payload field except "
            "/provenance/registry_sha256 is reproduced exactly"
        ),
        "model_role": "benchmark_only",
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "scientific_release_ready": False,
        "interpretation": "Used-source observation reproduction and software regression only",
    }
    if previous is not None:
        old = EvidenceRegistry.from_yaml(previous)
        spec = registry.datasets[DATASET]
        added_keys = set(spec["parameter_keys"])
        if (
            registry.parameters.keys() - old.parameters.keys() != added_keys
            or registry.datasets.keys() - old.datasets.keys() != {DATASET}
            or registry.sources.keys() - old.sources.keys() != {spec["source_id"]}
            or any(registry.parameters.get(k) != v for k, v in old.parameters.items())
            or any(registry.datasets.get(k) != v for k, v in old.datasets.items())
            or any(registry.sources.get(k) != v for k, v in old.sources.items())
            or registry.scientific_blockers != old.scientific_blockers
        ):
            raise ValueError("Undeclared change to prior evidence or scientific gates")
        scenario = Scenario.from_yaml(ROOT / "scenarios/reduce_upf_30.yaml")
        if added_keys & set(sampled_parameters(registry, scenario)):
            raise ValueError("Geelong observation parameters entered engine sampling")
        before_after = compare_registries(previous, ROOT)
        before_joint, after_joint = joint_report(old), joint_report(registry)
        before_joint["provenance"].pop("evidence_sha256")
        after_joint["provenance"].pop("evidence_sha256")
        if before_joint != after_joint:
            raise ValueError("Geelong intake changed existing joint survey results")
        before_after["refreshed_observation_reports"]["joint-glycemic-uncertainty.json"] = {
            "all_other_outputs_identical": True,
            "excluded_paths": ["/provenance/evidence_sha256"],
        }
        before_after["interpretation"] = (
            "Paired-label observation likelihood added; canonical engine results remain identical"
        )
        proof.update(
            before_after=before_after,
            prior_parameters_sources_datasets_and_blockers_identical=True,
            added_parameters=sorted(added_keys),
            added_dataset=DATASET,
            added_source=spec["source_id"],
            all_added_parameters_excluded_from_engine_sampling=True,
        )
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-registry", type=Path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    parser.add_argument("--output", type=Path, default=Path(f"outputs/geelong-proof-{stamp}.json"))
    options = parser.parse_args()
    verification = assess(options.previous_registry)
    write_report(verification, options.output)
    print(encoded({key: verification[key] for key in ("passed", "model_role")}).decode(), end="")
