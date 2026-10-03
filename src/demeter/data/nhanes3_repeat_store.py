"""Source/definition checks for the separately admitted NHANES III diagnostic.

The public admission entry point verifies this module's loaded bytes and the
independent receipts before calling it. No network, parser or clinical fit here.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from demeter.data import nhanes3_repeat as calculation
from demeter.schema import EvidenceRegistry

DATASET = "nhanes_iii_repeat_fpg_observation"
STORE = Path("data/sources/nhanes3/1988-1994-repeat")
PROTOCOL_PATH = Path("docs/validation/nhanes3-repeat-intake-protocol-v1.json")
PROTOCOL_SHA256 = "1728d637312da8fd4911d8152b15275eb70760e351286a2a898e95453786798f"
DOCUMENTATION_PATH = Path("docs/validation/nhanes3-repeat-documentation-receipts-v1.json")
DOCUMENTATION_SHA256 = "64e45fa41246d0054a12c7c105bf6be744b72450171beb18803701116a840384"
PARAMETERS = {
    "adult_min_months": "nhanes3_repeat_adult_min_months",
    "age_topcode_months": "nhanes3_repeat_mec_age_topcode",
    "fasting_min_hours": "nhanes3_repeat_fasting_min_hours",
    "fpg_positive_min": "nhanes3_repeat_fpg_positive_min",
}
DEFINITION = {
    "adult_min_months": 240,
    "age_topcode_months": 1080,
    "fasting_min_hours": 8,
    "fpg_positive_min": 126,
}
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def semantic_sha256(value) -> str:
    return digest(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    )


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate NHANES III receipt key")
        value[key] = item
    return value


def _nonfinite(value):
    raise ValueError("Nonfinite NHANES III receipt value")


def read_json(content: bytes) -> dict:
    try:
        value = json.loads(content, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Invalid NHANES III receipt encoding") from None
    if not isinstance(value, dict):
        raise ValueError("NHANES III receipt must be an object")
    return value


def read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise ValueError("Unavailable NHANES III admitted artifact") from None


def _inactive(receipt: dict, kind: str) -> None:
    if (
        not isinstance(receipt, dict)
        or receipt.get("kind") != kind
        or type(receipt.get("schema_version")) is not int
        or receipt["schema_version"] != 1
        or receipt.get("model_role") != "benchmark_only"
        or receipt.get("used_source") is not True
        or receipt.get("scientific_gates") != dict.fromkeys(calculation.GATES, False)
        or any(
            receipt.get("scientific_gates", {}).get(name) is not False for name in calculation.GATES
        )
        or receipt.get("protocol_sha256") != PROTOCOL_SHA256
    ):
        raise ValueError("NHANES III admission scope/gates differ from the frozen contract")


def verify(
    registry: EvidenceRegistry,
    source_admission: dict,
    code_admission: dict,
    source: Path = STORE,
) -> tuple[dict[str, bytes], dict]:
    """Verify admitted inputs before any selected value is decoded.

    Receipts must first be checked against the public guard's independent byte
    pins; accepting mutable receipts alone would not admit an empirical source.
    """
    _inactive(source_admission, "nhanes3_repeat_source_admission")
    _inactive(code_admission, "nhanes3_repeat_code_admission")
    if (
        source_admission.get("participant_values_decoded_before_admission") is not False
        or code_admission.get("empirical_diagnostic_computed_before_code_admission") is not False
        or source_admission.get("source_sha256") != code_admission.get("source_sha256")
        or source_admission.get("source_manifest_sha256")
        != code_admission.get("source_manifest_sha256")
    ):
        raise ValueError("NHANES III source/code admissions disagree")
    protocol_content = read(PROTOCOL_PATH)
    if digest(protocol_content) != PROTOCOL_SHA256:
        raise ValueError("NHANES III frozen protocol checksum mismatch")
    protocol = read_json(protocol_content)
    if (
        protocol.get("kind") != "nhanes3_repeat_intake_protocol"
        or protocol.get("scientific_gates") != dict.fromkeys(calculation.GATES, False)
        or protocol.get("source_store") != STORE.as_posix()
        or protocol.get("documentation_receipts")
        != {"path": DOCUMENTATION_PATH.as_posix(), "sha256": DOCUMENTATION_SHA256}
    ):
        raise ValueError("NHANES III protocol roles differ from the frozen contract")
    if digest(read(DOCUMENTATION_PATH)) != DOCUMENTATION_SHA256:
        raise ValueError("NHANES III documentary receipt checksum mismatch")
    for name, expected in protocol["existing_evidence_preservation"][
        "prior_frozen_and_source_artifact_sha256"
    ].items():
        if digest(read(Path(name))) != expected:
            raise ValueError("Prior frozen/source artifact differs from NHANES III protocol")
    preserved = protocol["existing_evidence_preservation"]
    current = registry.model_dump(mode="json")
    for section in ("parameters", "sources"):
        keys = preserved["preserved_" + section[:-1] + "_keys"]
        if (
            any(key not in current[section] for key in keys)
            or semantic_sha256({key: current[section][key] for key in keys})
            != preserved["selected_original_" + section + "_sha256"]
        ):
            raise ValueError("Prior original evidence records differ from NHANES III protocol")
    for key, expected in preserved["prior_dataset_sha256"].items():
        if key not in current["datasets"] or semantic_sha256(current["datasets"][key]) != expected:
            raise ValueError("Prior dataset definition differs from NHANES III protocol")
    dataset = registry.datasets.get(DATASET)
    if not isinstance(dataset, dict) or semantic_sha256(dataset) != code_admission.get(
        "registry_dataset_sha256"
    ):
        raise ValueError("NHANES III registry definition differs from code admission")
    parameter_pins = code_admission.get("registry_parameter_sha256")
    expected_keys = {*PARAMETERS.values(), "nhanes3_repeat_adult_min_years"}
    if not isinstance(parameter_pins, dict) or set(parameter_pins) != expected_keys:
        raise ValueError("NHANES III parameter admission shape invalid")
    for key, expected in parameter_pins.items():
        parameter = registry.parameters.get(key)
        if parameter is None or semantic_sha256(parameter.model_dump(mode="json")) != expected:
            raise ValueError("NHANES III parameter differs from code admission")
    source_pins = code_admission.get("registry_documentary_source_sha256")
    if not isinstance(source_pins, dict) or set(source_pins) != set(
        dataset["documentation_source_ids"]
    ):
        raise ValueError("NHANES III documentary source admission shape invalid")
    for key, expected in source_pins.items():
        documentary = registry.sources.get(key)
        if documentary is None or semantic_sha256(documentary.model_dump(mode="json")) != expected:
            raise ValueError("NHANES III documentary source differs from code admission")
    if dataset.get("definition_parameters") != PARAMETERS:
        raise ValueError("NHANES III selected definition keys differ")
    for role, key in PARAMETERS.items():
        if (
            registry.value(key) != DEFINITION[role]
            or registry.parameters[key].model_role != "benchmark_only"
        ):
            raise ValueError("NHANES III fixed definition/role differs from protocol")
    if source.is_symlink() or not source.is_dir():
        raise ValueError("NHANES III source must be an admitted plain directory")
    names = {component + ".DAT" for component in calculation.LAYOUTS} | {"manifest.json"}
    if {item.name for item in source.iterdir()} != names or any(
        item.is_symlink() or not item.is_file() for item in source.iterdir()
    ):
        raise ValueError("NHANES III store has unexpected or unsafe components")
    manifest_content = read(source / "manifest.json")
    if digest(manifest_content) != source_admission.get("source_manifest_sha256"):
        raise ValueError("NHANES III manifest differs from independent source admission")
    manifest = read_json(manifest_content)
    if manifest.get("protocol_sha256") != PROTOCOL_SHA256:
        raise ValueError("NHANES III manifest protocol differs")
    receipts = manifest.get("sources")
    if not isinstance(receipts, dict) or set(receipts) != names - {"manifest.json"}:
        raise ValueError("NHANES III manifest component set invalid")
    source_pins = source_admission.get("source_sha256")
    size_pins = source_admission.get("source_size_bytes")
    if (
        not isinstance(source_pins, dict)
        or set(source_pins) != set(calculation.LAYOUTS)
        or not isinstance(size_pins, dict)
        or set(size_pins) != set(calculation.LAYOUTS)
    ):
        raise ValueError("NHANES III source admission component pins invalid")
    content = {}
    for component, layout in calculation.LAYOUTS.items():
        filename = component + ".DAT"
        receipt = receipts[filename]
        expected = source_pins[component]
        size = size_pins[component]
        if (
            not isinstance(receipt, dict)
            or not isinstance(expected, str)
            or not _SHA.fullmatch(expected)
            or type(size) is not int
            or size <= 0
            or receipt.get("url") != protocol["source_urls"][component]["url"]
            or receipt.get("sha256") != expected
            or receipt.get("bytes") != size
            or receipt.get("original_bytes_preserved") is not True
            or receipt.get("participant_records_decoded") is not False
            or layout["minimum"]
            != protocol["source_urls"][component]["minimum_selected_prefix_width"]
            or layout["maximum"]
            != protocol["source_urls"][component]["producer_data_max_width_excluding_newline"]
        ):
            raise ValueError("NHANES III source receipt/layout differs from admission")
        try:
            timestamp = datetime.fromisoformat(receipt["retrieved_at"].replace("Z", "+00:00"))
        except (TypeError, ValueError, KeyError):
            raise ValueError("Invalid NHANES III source receipt timestamp") from None
        if timestamp.utcoffset() is None:
            raise ValueError("NHANES III source receipt timestamp requires timezone")
        payload = read(source / filename)
        if len(payload) != size or digest(payload) != expected:
            raise ValueError("NHANES III original bytes differ from independent source admission")
        content[component] = payload
    return content, {
        "protocol_sha256": PROTOCOL_SHA256,
        "source_sha256": dict(source_pins),
        "implementation_sha256": code_admission["implementation_sha256"],
        "evidence_sha256": registry.content_hash,
    }
