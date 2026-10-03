"""Offline exact replay of the admitted coarse NHANES III repeat-label report."""

from __future__ import annotations

import argparse
import copy
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re

from demeter.data.nhanes3_repeat_admission import report
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/validation/nhanes3-repeat-fpg-report-v1.json"
ARTIFACT_SHA256 = "1b583ad4ce3a211f1af0518e4be7b67d11652d242ec5e1ed8a428c3029dfbc7f"
GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
PUBLIC_KEYS = {
    "kind",
    "schema_version",
    "source_vintage",
    "model_role",
    "validation_only",
    "source_audit_passed",
    "scientific_gates",
    "diagnostic_status",
    "ledger_conserved",
    "provenance",
}
PROVENANCE_KEYS = {
    "protocol_sha256",
    "source_sha256",
    "implementation_sha256",
    "source_admission_sha256",
    "code_admission_sha256",
    "evidence_sha256",
}
IMPLEMENTATIONS = {
    "src/demeter/data/nhanes3_repeat.py",
    "src/demeter/data/nhanes3_repeat_store.py",
    "src/demeter/schema.py",
}


def encoded(value) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate frozen repeat report key")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("Nonfinite frozen repeat report value")


def _fingerprint(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _validate(value) -> str:
    if (
        not isinstance(value, dict)
        or set(value) != PUBLIC_KEYS
        or value.get("kind") != "nhanes3_repeat_fpg_nominal_diagnostic"
        or type(value.get("schema_version")) is not int
        or value["schema_version"] != 1
        or value.get("source_vintage")
        != "NHANES III 1988-1994; revised primary1A and repeat3A ASCII"
        or value.get("model_role") != "benchmark_only"
        or value.get("validation_only") is not True
        or value.get("source_audit_passed") is not True
        or value.get("ledger_conserved") is not True
        or not isinstance(value.get("scientific_gates"), dict)
        or set(value["scientific_gates"]) != set(GATES)
        or any(value["scientific_gates"][key] is not False for key in GATES)
        or value.get("diagnostic_status")
        not in {"withheld", "contradicted", "not_evaluable", "not_contradicted_in_observed_pairs"}
    ):
        raise ValueError("Repeat replay requires the inactive source-audited coarse public schema")
    provenance = value.get("provenance")
    if (
        not isinstance(provenance, dict)
        or set(provenance) != PROVENANCE_KEYS
        or any(
            not _fingerprint(provenance[key])
            for key in PROVENANCE_KEYS - {"source_sha256", "implementation_sha256"}
        )
        or not isinstance(provenance["source_sha256"], dict)
        or set(provenance["source_sha256"]) != {"LAB", "ADULT", "LABSE"}
        or not isinstance(provenance["implementation_sha256"], dict)
        or set(provenance["implementation_sha256"]) != IMPLEMENTATIONS
        or any(
            not _fingerprint(pin)
            for pin in (
                *provenance["source_sha256"].values(),
                *provenance["implementation_sha256"].values(),
            )
        )
    ):
        raise ValueError("Repeat replay public provenance is invalid")
    return provenance["evidence_sha256"]


def verify(registry=None, frozen_path: Path = ARTIFACT) -> dict:
    """Reproduce only the public projection, permitting one bound registry-hash difference."""
    if not _fingerprint(ARTIFACT_SHA256):
        raise ValueError("Repeat report has not been immutably admitted")
    try:
        raw = frozen_path.read_bytes()
    except OSError:
        raise ValueError("Unavailable frozen repeat report") from None
    if hashlib.sha256(raw).hexdigest() != ARTIFACT_SHA256:
        raise ValueError("Frozen repeat report checksum mismatch")
    try:
        frozen = json.loads(raw, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Invalid frozen repeat report encoding") from None
    frozen_hash = _validate(frozen)
    if registry is None:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    actual = report(registry)
    current_hash = _validate(actual)
    if not _fingerprint(registry.content_hash) or current_hash != registry.content_hash:
        raise ValueError("Repeat replay must identify the current registry")
    actual_payload, frozen_payload = copy.deepcopy(actual), copy.deepcopy(frozen)
    actual_payload["provenance"].pop("evidence_sha256")
    frozen_payload["provenance"].pop("evidence_sha256")
    if encoded(actual_payload) != encoded(frozen_payload):
        raise ValueError("Repeat report changed outside the registry fingerprint")
    return {
        "kind": "nhanes3_repeat_fpg_verification",
        "passed": True,
        "network_used": False,
        "frozen_report_sha256": ARTIFACT_SHA256,
        "source_report_exactly_reproduced": encoded(actual) == raw,
        "source_report_exactly_reproduced_excluding_registry_fingerprint": True,
        "excluded_paths": ["/provenance/evidence_sha256"],
        "current_registry_sha256": current_hash,
        "committed_registry_sha256": frozen_hash,
        "registry_fingerprint_changed": current_hash != frozen_hash,
        "model_role": "benchmark_only",
        "validation_only": True,
        "scientific_gates": dict.fromkeys(GATES, False),
        "reproduction_scope": (
            "Exact encoded coarse public report except /provenance/evidence_sha256; "
            "independent admission verifies actual source, definition and loaded implementation "
            "identities offline. Used-source replay is not independent validation or clinical fitting."
        ),
    }


def _output_preflight(output: Path) -> None:
    destination = output.resolve()
    protected = [(ROOT / name).resolve() for name in ("data", "src", "docs", "evidence")]
    if os.path.lexists(output) or any(destination.is_relative_to(path) for path in protected):
        raise ValueError("Verification output must be new and outside protected records")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    parser.add_argument("--output", type=Path, default=Path(f"outputs/nhanes3-repeat-{stamp}.json"))
    args = parser.parse_args(argv)
    try:
        _output_preflight(args.output)
        result = verify()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(encoded(result))
    except (ValueError, OSError, KeyError, TypeError):
        print("NHANES III repeat verification failed; no participant records exported.")
        return 1
    print(encoded({key: result[key] for key in ("passed", "model_role", "network_used")}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
