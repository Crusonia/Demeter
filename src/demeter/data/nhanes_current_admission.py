"""Public current-cycle replay bound independently to frozen source and code proof.

The byte-preserved v1 modules and aggregate remain unchanged. This guard adds
no observations, statistical calculation, registry definition or activation.
"""

import hashlib
import json
from pathlib import Path

from demeter.data import nhanes_current as calculation
from demeter.data import nhanes_current_store as store
from demeter.schema import EvidenceRegistry

DATASET = "nhanes_glycemic_2021_2023"
GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
ADMISSION_PATH = Path("docs/validation/nhanes-2021-2023-source-admission-v1.json")
ADMISSION_SHA256 = "8d405e7e209eefc04de86b29e40f2c40e1e51f6b3c288398130bb44a97c18165"
REPORT_PATH = Path("docs/validation/nhanes-2021-2023-glycemic-reconstruction-v1.json")
REPORT_SHA256 = "888593964284e0d8eae32ca82f9f5a64d6bf20a9e98e7d1f271bd57f649f17a9"
IMPLEMENTATIONS = {
    "src/demeter/data/nhanes_current.py": calculation,
    "src/demeter/data/nhanes_current_store.py": store,
}


def _digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise ValueError("Unavailable independently admitted NHANES artifact") from None


def _frozen(path: Path, expected: str) -> dict:
    try:
        content = path.read_bytes()
    except OSError:
        raise ValueError("Unavailable independently admitted NHANES artifact") from None
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("Independent NHANES admission artifact checksum mismatch")
    try:
        result = json.loads(content)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Invalid independently admitted NHANES artifact") from None
    if not isinstance(result, dict):
        raise ValueError("Invalid independently admitted NHANES artifact")
    return result


def verify_admission(registry: EvidenceRegistry) -> None:
    """Bind source/registry/disk/loaded code before any v1 calculation function."""
    admission = _frozen(ADMISSION_PATH, ADMISSION_SHA256)
    frozen = _frozen(REPORT_PATH, REPORT_SHA256)
    provenance = frozen.get("provenance", {})
    spec = registry.datasets.get(DATASET)
    source_pins = {name: receipt["sha256"] for name, receipt in admission["sources"].items()}
    pins = provenance.get("implementation_sha256")
    if (
        admission.get("kind") != "nhanes_2021_2023_source_admission"
        or admission.get("model_role") != "benchmark_only"
        or admission.get("participant_records_parsed_at_admission") is not False
        or any(
            admission.get(name) is not False
            for name in GATES
            if name != "sampling_distribution_assumed"
        )
        or frozen.get("kind") != DATASET
        or frozen.get("model_role") != "benchmark_only"
        or frozen.get("validation_only") is not True
        or frozen.get("source_audit_passed") is not True
        or any(frozen.get(name) is not False for name in GATES)
        or not isinstance(spec, dict)
        or spec.get("model_role") != "benchmark_only"
        or any(spec.get(name) is not False for name in GATES)
        or not isinstance(pins, dict)
        or set(pins) != set(IMPLEMENTATIONS)
        or spec.get("implementation_sha256") != pins
        or spec.get("protocol_sha256") != admission.get("protocol_sha256")
        or provenance.get("protocol_sha256") != admission.get("protocol_sha256")
        or spec.get("source_manifest_sha256") != admission.get("source_manifest_sha256")
        or provenance.get("source_manifest_sha256") != admission.get("source_manifest_sha256")
        or spec.get("source_sha256") != source_pins
        or provenance.get("source_sha256") != source_pins
    ):
        raise ValueError("NHANES source or code pins differ from independent frozen admission")
    for name, module in IMPLEMENTATIONS.items():
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or Path(origin).suffix != ".py":
            raise ValueError("NHANES independently admitted loaded source is unavailable")
        if _digest(Path(name)) != pins[name] or _digest(Path(origin)) != pins[name]:
            raise ValueError("NHANES calculation bytes differ from independent frozen admission")


def report(
    registry: EvidenceRegistry, source: Path = Path("data/sources/nhanes/2021-2023")
) -> dict:
    """Return the unchanged v1 report only after independent admission checks."""
    verify_admission(registry)
    return store.report(registry, source)
