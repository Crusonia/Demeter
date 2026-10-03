"""Public replay API binding the preserved v1 calculation to its code admission.

The original calculation and first report stay byte-for-byte frozen. This
additional guard admits no new statistics, source rows or model parameters.
"""

from pathlib import Path

from demeter.data import nhanes_assay_mapping as calculation
from demeter.data import nhanes_current_store as store
from demeter.schema import EvidenceRegistry

DATASET = calculation.DATASET
GATES = calculation.GATES
ADMISSION_PATH = Path("docs/validation/nhanes-assay-mapping-code-admission-v1.json")
ADMISSION_SHA256 = "fad9fa6475a33268d379df45d687c70407b5823215daa6783248001fba382f4b"


def verify_admission(registry: EvidenceRegistry) -> None:
    """Refuse a changed receipt, registry pin or loaded calculation before parsing."""
    content = store._read(ADMISSION_PATH, "paired assay code admission")
    if store.digest(content) != ADMISSION_SHA256:
        raise ValueError("NHANES paired assay code admission checksum mismatch")
    admission = store._json(content)
    pins = admission.get("implementation_sha256")
    spec = registry.datasets.get(DATASET)
    if (
        admission.get("kind") != "nhanes_assay_mapping_code_admission"
        or admission.get("schema_version") != 1
        or admission.get("model_role") != "benchmark_only"
        or admission.get("used_source") is not True
        or admission.get("new_assay_diagnostics_computed_before_code_admission") is not False
        or any(admission.get(name) is not False for name in calculation.GATES)
        or admission.get("protocol_path") != calculation.PROTOCOL_PATH.as_posix()
        or admission.get("protocol_sha256") != calculation.PROTOCOL_SHA256
        or not isinstance(pins, dict)
        or set(pins) != {calculation.IMPLEMENTATION}
        or not isinstance(spec, dict)
        or spec.get("implementation_sha256") != pins
    ):
        raise ValueError("NHANES paired assay code admission differs from frozen contract")
    expected = pins[calculation.IMPLEMENTATION]
    for path in (Path(calculation.IMPLEMENTATION), Path(calculation.__file__)):
        if store.digest(store._read(path, "admitted paired assay calculation")) != expected:
            raise ValueError("NHANES paired assay calculation differs from code admission")
    protocol = calculation._protocol()
    if (
        admission.get("source_manifest_sha256") != protocol["source_manifest_sha256"]
        or admission.get("source_sha256") != protocol["source_sha256"]
    ):
        raise ValueError("NHANES paired assay sources differ from code admission")


def report(registry: EvidenceRegistry, source: Path = store.STORE) -> dict:
    """Replay the frozen aggregate only after independent code-admission verification."""
    verify_admission(registry)
    return calculation.report(registry, source)
