"""Pinned current-cycle NHANES intake; private joins and aggregate reporting only."""

from __future__ import annotations

from datetime import datetime
import hashlib
from importlib import import_module
from io import BytesIO
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from demeter.data.nhanes import encoded, storage_numbers

STORE = Path("data/sources/nhanes/2021-2023")
DATASET = "nhanes_glycemic_2021_2023"
PROTOCOL_PATH = Path("docs/validation/nhanes-2021-2023-intake-protocol-v1.json")
PROTOCOL_SHA256 = "5dae6588b3953f54e9fc89d5ebae701bf988b8f17a5d38a989f9be6fbc3c6a8c"
COLUMNS = {
    "DEMO_L.xpt": (
        "SDDSRVYR",
        "RIDSTATR",
        "RIAGENDR",
        "RIDAGEYR",
        "RIDEXPRG",
        "SDMVSTRA",
        "SDMVPSU",
    ),
    "DIQ_L.xpt": ("DIQ010",),
    "GHB_L.xpt": ("LBXGH", "WTPH2YR"),
    "GLU_L.xpt": ("LBXGLU", "WTSAF2YR"),
}
PUBLIC_BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/"
USE_TERMS = "https://www.cdc.gov/nchs/policy/data-user-agreement.html"
XPORT_HEADER = b"HEADER RECORD*******LIBRARY HEADER RECORD!!!!!!!"
IMPLEMENTATIONS = ("src/demeter/data/nhanes_current.py", "src/demeter/data/nhanes_current_store.py")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate NHANES metadata key")
        result[key] = value
    return result


def _json(content: bytes) -> dict:
    try:
        value = json.loads(content, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Invalid NHANES metadata encoding") from None
    if not isinstance(value, dict):
        raise ValueError("NHANES metadata requires an object")
    return value


def _timestamp(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Invalid NHANES receipt timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid NHANES receipt timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("NHANES receipt timestamp requires timezone")
    return parsed


def _read(path: Path, description: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise ValueError(f"Unavailable NHANES {description}") from None


def _valid_keys(frame: pd.DataFrame) -> bool:
    if "SEQN" not in frame or not frame.columns.is_unique:
        return False
    keys = frame.SEQN
    if (
        not is_numeric_dtype(keys.dtype)
        or is_bool_dtype(keys.dtype)
        or is_complex_dtype(keys.dtype)
        or keys.isna().any()
        or keys.duplicated().any()
    ):
        return False
    values = keys.to_numpy(dtype=float)
    return bool(
        np.isfinite(values).all()
        and (values > 0).all()
        and (values < 2**53).all()
        and np.equal(values, np.floor(values)).all()
    )


def read_xpt(path: Path, columns: tuple[str, ...], content: bytes | None = None) -> pd.DataFrame:
    """Select released fields, reject ambiguous keys, and never print source values."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            frame = pd.read_sas(path if content is None else BytesIO(content), format="xport")
    except Exception:
        raise ValueError("Invalid NHANES XPORT component") from None
    if (
        not isinstance(frame, pd.DataFrame)
        or not frame.columns.is_unique
        or any(name not in frame for name in ("SEQN", *columns))
    ):
        raise ValueError("NHANES component missing required selected fields")
    if "WTSAFPRP" in frame.columns:
        raise ValueError("Current NHANES cannot use a pooled historical weight component")
    frame = frame.loc[:, ["SEQN", *columns]].copy()
    # Exact IBM XPORT zero-decoding correction, not an epsilon/clinical rule.
    frame = frame.replace(float.fromhex("0x1p-260"), 0.0)
    if not _valid_keys(frame):
        raise ValueError("NHANES linkage keys must be unique positive exact integers")
    return frame


def _join(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frame = tables["DEMO_L.xpt"]
    if not frame.SDDSRVYR.eq(12).all() or not frame.RIDSTATR.isin([1, 2]).all():
        raise ValueError("NHANES component has incompatible cycle or interview status")
    for name in COLUMNS:
        if name == "DEMO_L.xpt":
            continue
        table = tables[name]
        if not table.SEQN.isin(frame.SEQN).all():
            raise ValueError("NHANES component contains orphan linkage keys")
        try:
            frame = frame.merge(table, on="SEQN", how="left", validate="one_to_one", sort=False)
        except Exception:
            raise ValueError("Invalid NHANES one-to-one component linkage") from None
    return frame


def verify_protocol() -> dict:
    """Verify the immutable protocol and preserved artifacts before source parsing."""
    content = _read(PROTOCOL_PATH, "intake protocol")
    if digest(content) != PROTOCOL_SHA256:
        raise ValueError("NHANES intake protocol checksum mismatch")
    protocol = _json(content)
    gates = (
        "direct_initialization_allowed",
        "clinical_fit_allowed",
        "engine_activation_allowed",
        "scientific_release_ready",
        "sampling_distribution_assumed",
    )
    if (
        type(protocol.get("schema_version")) is not int
        or protocol["schema_version"] != 1
        or protocol.get("kind") != "nhanes_2021_2023_intake_protocol"
        or protocol.get("model_role") != "benchmark_only"
        or protocol.get("source_store") != STORE.as_posix()
        or any(protocol.get(key) is not False for key in gates)
        or protocol.get("source_urls") != {name: PUBLIC_BASE + name for name in COLUMNS}
        or protocol.get("required_columns")
        != {name: ["SEQN", *columns] for name, columns in COLUMNS.items()}
        or protocol.get("use_terms_url") != USE_TERMS
        or not isinstance(protocol.get("existing_artifact_sha256"), dict)
    ):
        raise ValueError("Invalid frozen NHANES intake contract")
    for name, expected in protocol["existing_artifact_sha256"].items():
        if digest(_read(Path(name), "preserved artifact")) != expected:
            raise ValueError("Preserved NHANES source or implementation checksum mismatch")
    return protocol


def verify_demographics_reuse(
    protocol: dict, manifest_content: bytes, original: dict, content: bytes
) -> None:
    reuse = protocol["demographics_reuse"]
    if (
        digest(manifest_content) != protocol["existing_artifact_sha256"][reuse["source_manifest"]]
        or digest(content) != reuse["sha256"]
        or original.get("sha256") != reuse["sha256"]
        or type(original.get("bytes")) is not int
        or original["bytes"] != len(content)
        or original.get("url") != PUBLIC_BASE + "DEMO_L.xpt"
        or original.get("retrieved_at") != reuse["original_retrieved_at"]
        or reuse.get("reuse_is_new_role_not_new_acquisition") is not True
    ):
        raise ValueError("NHANES demographics reuse differs from frozen original acquisition")


def _manifest(
    source: Path, protocol: dict, manifest_content: bytes | None = None
) -> tuple[dict, dict[str, bytes]]:
    manifest = _json(
        _read(source / "manifest.json", "source manifest")
        if manifest_content is None
        else manifest_content
    )
    if (
        type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
        or manifest.get("protocol_path") != PROTOCOL_PATH.as_posix()
        or manifest.get("protocol_sha256") != PROTOCOL_SHA256
        or manifest.get("source_store") != STORE.as_posix()
        or manifest.get("participant_records_parsed") is not False
        or not isinstance(manifest.get("sources"), dict)
        or set(manifest["sources"]) != set(COLUMNS)
    ):
        raise ValueError("Invalid NHANES current source manifest")
    created = _timestamp(protocol["created_at"])
    started = _timestamp(manifest.get("acquisition_started_at"))
    finished = _timestamp(manifest.get("acquisition_finished_at"))
    if started < created or finished < started:
        raise ValueError("NHANES acquisition chronology precedes protocol freeze")
    blobs = {}
    for name in COLUMNS:
        receipt = manifest["sources"][name]
        if not isinstance(receipt, dict) or (
            receipt.get("url") != protocol["source_urls"][name]
            or receipt.get("codebook_url") != protocol["assay_method_sources"][name]
            or receipt.get("use_terms") != USE_TERMS
            or receipt.get("format") != "SAS XPORT"
            or receipt.get("model_role") != "benchmark_only"
            or receipt.get("publisher") != "CDC/NCHS"
            or receipt.get("vintage") != "August 2021-August 2023"
            or type(receipt.get("bytes")) is not int
            or receipt["bytes"] <= 0
        ):
            raise ValueError("Invalid NHANES source receipt")
        content = _read(source / name, "source component")
        if digest(content) != receipt.get("sha256") or len(content) != receipt["bytes"]:
            raise ValueError("NHANES source checksum or size mismatch")
        if not content.startswith(XPORT_HEADER):
            raise ValueError("NHANES source is not an XPORT component")
        retrieved = _timestamp(receipt.get("retrieved_at"))
        if name == "DEMO_L.xpt":
            reuse = protocol["demographics_reuse"]
            original = receipt.get("original_acquisition")
            original_content = _read(Path(reuse["source_manifest"]), "original reuse manifest")
            original_receipt = _json(original_content)["sources"][name]
            verify_demographics_reuse(protocol, original_content, original_receipt, content)
            if (
                receipt.get("acquisition_kind") != "reuse"
                or receipt.get("retrieved_at") != reuse["original_retrieved_at"]
                or not isinstance(original, dict)
                or original
                != {
                    "source_store": Path(reuse["path"]).parent.as_posix(),
                    "source_manifest_sha256": digest(original_content),
                    "url": original_receipt["url"],
                    "retrieved_at": original_receipt["retrieved_at"],
                    "sha256": original_receipt["sha256"],
                    "bytes": original_receipt["bytes"],
                }
                or not started <= _timestamp(receipt.get("reused_at")) <= finished
            ):
                raise ValueError("Invalid NHANES demographics reuse receipt")
        elif receipt.get("acquisition_kind") != "download" or not started <= retrieved <= finished:
            raise ValueError("Invalid NHANES new acquisition chronology")
        blobs[name] = content
    return manifest, blobs


def read_store(source: Path = STORE) -> tuple[pd.DataFrame, dict]:
    """Offline source verification followed by private selected-field linkage."""
    protocol = verify_protocol()
    manifest, blobs = _manifest(source, protocol)
    return _frame(source, blobs), manifest


def _frame(source: Path, blobs: dict[str, bytes]) -> pd.DataFrame:
    # Consume the verified byte snapshots rather than reopening mutable paths.
    tables = {
        name: read_xpt(source / name, columns, blobs[name]) for name, columns in COLUMNS.items()
    }
    return _join(tables)


def _registry_contract(registry, protocol: dict) -> dict:
    values = registry.model_dump(mode="json")
    datasets = values["datasets"]
    spec = datasets.get(DATASET)
    if not isinstance(spec, dict) or any(
        spec.get(key) != value for key, value in protocol["definition_fields"].items()
    ):
        raise ValueError("NHANES current registered definition differs from frozen protocol")
    if spec.get("protocol_sha256") != PROTOCOL_SHA256:
        raise ValueError("NHANES current registered protocol pin mismatch")
    if any(
        spec.get(key) is not False
        for key in (
            "direct_initialization_allowed",
            "clinical_fit_allowed",
            "engine_activation_allowed",
            "sampling_distribution_assumed",
            "scientific_release_ready",
        )
    ):
        raise ValueError("NHANES current scientific gates must remain explicitly false")
    for group, scope_key in (
        ("parameters", "preserved_parameter_keys"),
        ("sources", "preserved_source_keys"),
    ):
        scope = spec.get(scope_key)
        if (
            not isinstance(scope, list)
            or any(not isinstance(name, str) or not name for name in scope)
            or scope != sorted(set(scope))
            or any(name not in values[group] for name in scope)
        ):
            raise ValueError("NHANES intake preserved evidence scope is invalid")
        preserved = {name: values[group][name] for name in scope}
        if digest(encoded(preserved)) != protocol[f"existing_{group}_sha256"]:
            raise ValueError("NHANES intake changed preserved evidence records")
    for name, expected in protocol["existing_definition_sha256"].items():
        if name not in datasets or digest(encoded(datasets[name])) != expected:
            raise ValueError("NHANES intake changed a preserved dataset definition")
    expected = spec.get("implementation_sha256")
    if not isinstance(expected, dict) or set(expected) != set(IMPLEMENTATIONS):
        raise ValueError("NHANES intake implementations must be explicitly admitted")
    for name in IMPLEMENTATIONS:
        if digest(_read(Path(name), "current implementation")) != expected[name]:
            raise ValueError("NHANES current implementation checksum mismatch")
    return spec


def _loaded_code(protocol: dict, spec: dict) -> dict:
    """Check actual imported source files, including equivalent installed copies."""
    expected = dict(protocol["existing_artifact_sha256"])
    expected.update(spec["implementation_sha256"])
    implementations = dict(
        zip(
            IMPLEMENTATIONS,
            ("demeter.data.nhanes_current", "demeter.data.nhanes_current_store"),
            strict=True,
        )
    )
    loaded = {}
    for name, pinned in expected.items():
        path = Path(name)
        if name in implementations:
            module_name = implementations[name]
        elif path.suffix == ".py" and path.parts[:2] == ("src", "demeter"):
            module_name = ".".join(path.with_suffix("").parts[1:])
        else:
            continue
        try:
            module = import_module(module_name)
        except Exception:
            raise ValueError("NHANES admitted source module unavailable") from None
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or Path(origin).suffix != ".py":
            raise ValueError("NHANES loaded implementation source is unavailable")
        actual = digest(_read(Path(origin), "loaded implementation"))
        if actual != pinned:
            raise ValueError("NHANES loaded implementation checksum mismatch")
        loaded[name] = {
            "module": module_name,
            "admitted_source_path": name,
            "sha256": actual,
            "loaded_file_verified": True,
        }
    return loaded


def report(registry, source: Path = STORE) -> dict:
    """Verify admitted source/definitions before computing an aggregate benchmark."""
    protocol = verify_protocol()
    spec = _registry_contract(registry, protocol)
    loaded_code = _loaded_code(protocol, spec)
    manifest_content = _read(source / "manifest.json", "source manifest")
    if digest(manifest_content) != spec.get("source_manifest_sha256"):
        raise ValueError("NHANES current manifest is not the admitted immutable source store")
    manifest, blobs = _manifest(source, protocol, manifest_content)
    source_pins = {name: row["sha256"] for name, row in manifest["sources"].items()}
    if spec.get("source_sha256") != source_pins:
        raise ValueError("NHANES current raw sources differ from admitted registry pins")
    frame = _frame(source, blobs)
    from demeter.data.nhanes_current import assess

    result = assess(frame, registry)
    result["source_audit_passed"] = True
    result["source_audit_status"] = "admitted_sources_definitions_and_implementations_verified"
    result["provenance"] = {
        "evidence_sha256": registry.content_hash,
        "protocol_path": PROTOCOL_PATH.as_posix(),
        "protocol_sha256": PROTOCOL_SHA256,
        "used_source": protocol["used_source"],
        "chronology": protocol["chronology"],
        "source_manifest_sha256": digest(manifest_content),
        "source_sha256": source_pins,
        "existing_artifact_sha256": protocol["existing_artifact_sha256"],
        "existing_definition_sha256": protocol["existing_definition_sha256"],
        "implementation_sha256": spec["implementation_sha256"],
        "loaded_implementation": loaded_code,
        "definitions": {DATASET: spec},
        "serialization": "Derived floats rounded to 12 significant digits; not measurement precision",
    }
    return storage_numbers(result)
