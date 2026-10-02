"""Reproduce the frozen offline Kerala endpoint-bound report exactly."""

from __future__ import annotations

from pathlib import Path
import hashlib

from demeter.analysis.kerala_endpoints import audit_kerala_endpoints
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
        actual = encoded(audit_kerala_endpoints(registry, ROOT))
        expected = (ROOT / "docs/validation/kerala-endpoint-bounds-v1.json").read_bytes()
        if (
            hashlib.sha256(expected).hexdigest()
            != registry.datasets["kerala_endpoint_bounds"]["report_sha256"]
        ):
            raise ValueError("Frozen endpoint report pin differs")
        if actual != expected:
            raise ValueError("Frozen endpoint report differs")
    except (ValueError, OSError, KeyError, TypeError):
        print("Kerala endpoint report verification failed")
        return 1
    print("Kerala endpoint report exactly reproduced; benchmark-only, no clinical fit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
