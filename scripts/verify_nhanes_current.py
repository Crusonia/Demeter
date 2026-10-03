"""Offline exact replay of the separately frozen 2021–2023 glycemic benchmark."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from demeter.data.nhanes import encoded
from demeter.data.nhanes_current_store import DATASET, report
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/validation/nhanes-2021-2023-glycemic-reconstruction-v1.json"
ARTIFACT_SHA256 = "888593964284e0d8eae32ca82f9f5a64d6bf20a9e98e7d1f271bd57f649f17a9"
GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
AUDIT_STATUS = "admitted_sources_definitions_and_implementations_verified"


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate frozen NHANES report key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Nonfinite frozen NHANES report value")


def _fingerprint(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _validate(value: dict) -> str:
    if (
        not isinstance(value, dict)
        or value.get("kind") != DATASET
        or value.get("model_role") != "benchmark_only"
        or value.get("validation_only") is not True
        or any(value.get(key) is not False for key in GATES)
        or value.get("source_audit_passed") is not True
        or value.get("source_audit_status") != AUDIT_STATUS
        or not isinstance(value.get("provenance"), dict)
        or not _fingerprint(value["provenance"].get("evidence_sha256"))
    ):
        raise ValueError("NHANES replay requires a source-audited benchmark with inactive gates")
    return value["provenance"]["evidence_sha256"]


def verify(registry=None, frozen_path: Path = ARTIFACT) -> dict:
    """Recalculate offline; exclude only the declared current registry fingerprint."""
    if not _fingerprint(ARTIFACT_SHA256):
        raise ValueError("NHANES current report has not been immutably admitted")
    try:
        frozen_bytes = frozen_path.read_bytes()
    except OSError:
        raise ValueError("Unavailable frozen NHANES current report") from None
    if hashlib.sha256(frozen_bytes).hexdigest() != ARTIFACT_SHA256:
        raise ValueError("Frozen NHANES current report checksum mismatch")
    try:
        frozen = json.loads(
            frozen_bytes, object_pairs_hook=_unique, parse_constant=_invalid_constant
        )
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Invalid frozen NHANES current report encoding") from None
    frozen_hash = _validate(frozen)
    if registry is None:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    actual = report(registry)
    current_hash = _validate(actual)
    if not _fingerprint(registry.content_hash) or current_hash != registry.content_hash:
        raise ValueError("NHANES current replay does not identify the current registry")
    actual_payload = copy.deepcopy(actual)
    frozen_payload = copy.deepcopy(frozen)
    actual_payload["provenance"].pop("evidence_sha256")
    frozen_payload["provenance"].pop("evidence_sha256")
    if encoded(actual_payload) != encoded(frozen_payload):
        raise ValueError("NHANES current report changed outside the registry fingerprint")
    return {
        "kind": "nhanes_current_glycemic_verification",
        "passed": True,
        "network_used": False,
        "frozen_report_sha256": ARTIFACT_SHA256,
        "source_report_exactly_reproduced": encoded(actual) == frozen_bytes,
        "source_report_exactly_reproduced_excluding_registry_fingerprint": True,
        "excluded_paths": ["/provenance/evidence_sha256"],
        "current_registry_sha256": current_hash,
        "committed_registry_sha256": frozen_hash,
        "registry_fingerprint_changed": current_hash != frozen_hash,
        "model_role": "benchmark_only",
        "validation_only": True,
        **{key: False for key in GATES},
        "reproduction_scope": (
            "Exact encoded aggregate report payload except /provenance/evidence_sha256; "
            "loaded source bytes, definitions and implementations verified offline by the wrapper. "
            "This is used-source reconstruction, not independent validation or clinical calibration."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    parser.add_argument("--output", type=Path, default=Path(f"outputs/nhanes-current-{stamp}.json"))
    args = parser.parse_args()
    try:
        result = verify()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(encoded(result))
    except (ValueError, OSError, KeyError, TypeError):
        print("NHANES current verification failed; no participant records exported.")
        return 1
    print(encoded({key: result[key] for key in ("passed", "model_role", "network_used")}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
