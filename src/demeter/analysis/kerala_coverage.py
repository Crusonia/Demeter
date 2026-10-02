"""Verify the Kerala before-values intake boundary without reading records."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit, urlunsplit
import xml.etree.ElementTree as ET
import zipfile


GATES = {
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "independent_validation_allowed",
    "scientific_release_ready",
}
DIRECT_IDENTIFIERS = re.compile(
    r"(^|[_\s])(name|firstname|surname|email|phone|mobile|address|dob|date.?of.?birth)([_\s]|$)",
    re.I,
)
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
TAG = "{" + NS["m"] + "}"


class _PrefixReader:
    """Prevent XML parser read-ahead beyond the permitted header prefix."""

    def __init__(self, source: Any) -> None:
        self.source = source

    def read(self, size: int = -1) -> bytes:
        return self.source.read(1 if size != 0 else 0)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(result.utcoffset() is not None, "UTC timestamp requires timezone")
    _require(result.utcoffset().total_seconds() == 0, "timestamp must be UTC")
    return result


def _gates(value: dict[str, Any]) -> None:
    _require(set(value) == GATES, "exact four scientific gates required")
    _require(all(item is False for item in value.values()), "scientific gates must be false")


def _pinned_path(root: Path, spec: dict[str, Any]) -> Path:
    path = (root / spec["path"]).resolve()
    _require(path.is_relative_to(root.resolve()), "artifact path escapes package")
    _require(path.is_file(), "pinned artifact absent")
    _require(path.stat().st_size == spec["bytes"], "artifact byte size mismatch")
    _require(_digest(path) == spec["sha256"], "artifact SHA256 mismatch")
    return path


def _sanitize_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    result = dict(receipt)
    parts = urlsplit(result["final_url"])
    result["final_url"] = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    result["resolved_query_omitted"] = bool(parts.query)
    result["signed_query_omitted"] = any(
        key.lower().startswith(("x-amz-", "x-goog-")) for key in parse_qs(parts.query)
    )
    return result


def _semantic_bindings(root: Path, documents: dict[str, Any], source_cache: Path | None) -> None:
    translation = documents["kerala-source-artifact-translation-v1.json"]
    historical = documents["kerala-source-schema-coverage-original-redacted-v1.json"]
    coverage = documents["kerala-clinical-contract-schema-coverage-v1.json"]
    v2 = documents["kerala-joint-coverage-intake-protocol-v2.json"]
    receipts = documents["kerala-source-acquisition-receipts-v1.json"]
    schema = documents["kerala-source-schema-protocol-v1.json"]
    snapshots = documents["kerala-source-followup-snapshot-amendment-v1.json"]
    for protocol in (translation, historical, snapshots):
        _gates(protocol["scientific_gates"])
    for protocol in (translation, snapshots):
        _require(
            protocol["participant_values_inspected"] is False, "additive repair must precede values"
        )
        _require(
            protocol["quantitative_workbook_counts_inspected"] is False,
            "additive repair must precede counts",
        )
    aliases = {
        item["original_path"]: item["committed_artifact"] for item in translation["path_aliases"]
    }
    _require(
        set(aliases)
        == {
            "schema-preflight-protocol-v1.json",
            "schema-preflight-header-addendum-v1.json",
            "finite-joint-coverage-intake-protocol-v1.json",
            "schema-headers-v1.json",
        },
        "exact translation aliases required",
    )
    for spec in aliases.values():
        _pinned_path(root, spec)
    for key in ("frozen_protocol_v2", "redacted_historical_coverage", "amended_published_coverage"):
        _pinned_path(root, translation[key])
    _require(
        translation["frozen_protocol_v2"]["path"]
        == "docs/validation/kerala-joint-coverage-intake-protocol-v2.json",
        "translation must bind immutable v2",
    )
    original = translation["original_coverage"]
    _require(original["raw_commit_allowed"] is False, "unredacted historical coverage private")
    _require(
        v2["source_scope"]["contract_coverage"]
        == {
            "path": original["original_path"],
            "bytes": original["bytes"],
            "sha256": original["sha256"],
        },
        "original contract coverage bind",
    )
    _require(
        v2["source_scope"]["header_preflight"]
        == {
            "path": "schema-headers-v1.json",
            "bytes": aliases["schema-headers-v1.json"]["bytes"],
            "sha256": aliases["schema-headers-v1.json"]["sha256"],
        },
        "v2 header source bind",
    )
    for key, alias in (
        ("protocol", "schema-preflight-protocol-v1.json"),
        ("header_addendum", "schema-preflight-header-addendum-v1.json"),
        ("header_manifest", "schema-headers-v1.json"),
    ):
        _require(
            historical[key]
            == {
                "path": alias,
                "bytes": aliases[alias]["bytes"],
                "sha256": aliases[alias]["sha256"],
            },
            "historical protocol/header bind",
        )
    _require(
        schema["metadata_sha256"]
        == historical["metadata"]["sha256"]
        == translation["metadata_original_sha256"]
        == receipts["metadata_receipt"]["sha256"],
        "metadata identity bind",
    )
    _require(
        schema["expected_files"] == receipts["release_metadata"]["files"],
        "frozen advertised file metadata drift",
    )
    ignore = {"source_appraisal_amendment", "next_finite_gate"}
    _require(
        {key: value for key, value in historical.items() if key not in ignore}
        == {key: value for key, value in coverage.items() if key not in ignore},
        "undeclared historical coverage change",
    )
    expected_raw = {
        item["raw_filename"]: {
            "path": item["raw_filename"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
        }
        for item in receipts["workbook_receipts"]
    }
    raw_specs = v2["source_scope"]["raw_files"]
    _require(
        len(raw_specs) == len(expected_raw)
        and {item["path"]: item for item in raw_specs} == expected_raw,
        "frozen v2 raw file pins differ from receipts",
    )
    header_maps = {
        "primary" if item["file_id"] == 39461149 else "secondary": {
            column["label"]: column["column"] for column in item["headers"]
        }
        for item in documents["kerala-source-headers-v1.json"]
    }
    for row in coverage["fields"]:
        for field in row.get("fields", []):
            book, location = field["locator"].split(":", 1)
            _require(
                book in header_maps and field["field"] in header_maps[book],
                "contract field absent from header manifest",
            )
            _require(
                location == "Sheet 1!" + header_maps[book][field["field"]],
                "contract field locator mismatch",
            )
    _require(
        snapshots["source_doi"] == receipts["publication_receipt"]["doi"]
        and snapshots["source_sha256"] == receipts["publication_receipt"]["sha256"],
        "snapshot amendment primary source bind",
    )
    for arm in snapshots["published_snapshots"].values():
        for wave in arm.values():
            _require(
                all(type(value) is int and value >= 0 for value in wave.values()),
                "source snapshot counts must be nonnegative integers",
            )
            _require(
                sum(value for key, value in wave.items() if key != "total_lost")
                == wave["total_lost"],
                "snapshot reason arithmetic mismatch",
            )
        _require(
            arm["12_month"]["died"] == arm["24_month"]["died"],
            "repeated cumulative death source counts changed",
        )
    if source_cache is not None:
        raw_original = (source_cache / original["original_path"]).resolve()
        _require(
            raw_original.is_relative_to(source_cache.resolve()),
            "historical cache path escapes source cache",
        )
        _require(
            raw_original.stat().st_size == original["bytes"]
            and _digest(raw_original) == original["sha256"],
            "original ignored coverage pin",
        )
        raw_obj = _json(raw_original)
        raw_obj["actual_source_receipts"] = [
            _sanitize_receipt(item) for item in raw_obj["actual_source_receipts"]
        ]
        raw_obj["publication_receipt"] = _sanitize_receipt(raw_obj["publication_receipt"])
        _require(raw_obj == historical, "original coverage redaction projection mismatch")


def read_headers_only(path: Path) -> list[dict[str, str]]:
    """Read the declared row 2 headers; never return participant cell values."""
    with zipfile.ZipFile(path) as book:
        names = book.namelist()
        _require(len(names) == len(set(names)), "duplicate archive entries")
        _require(
            not any(
                token in name.lower()
                for name in names
                for token in ("vbaproject", "externallink", "connections.xml")
            ),
            "active or external workbook content unsupported",
        )
        _require(
            sum(part.file_size for part in book.infolist()) <= 32_000_000,
            "workbook decompression size exceeds bounded header reader",
        )
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        sheets = workbook.findall("m:sheets/m:sheet", NS)
        _require(
            len(sheets) == 1 and sheets[0].attrib["name"] == "Sheet 1",
            "declared single sheet changed",
        )
        row = None
        with book.open("xl/worksheets/sheet1.xml") as source:
            for _, element in ET.iterparse(_PrefixReader(source), events=("end",)):
                if element.tag == TAG + "row":
                    if element.attrib.get("r") == "2":
                        row = element
                        break
                    element.clear()
        _require(row is not None, "declared header row absent")
        cells = []
        wanted = set()
        for cell in row.findall("m:c", NS):
            value, inline = cell.find("m:v", NS), cell.find("m:is", NS)
            if value is None and inline is None:
                continue
            _require(cell.find("m:f", NS) is None, "formula header unsupported")
            kind = cell.attrib.get("t")
            _require(kind in {"s", "inlineStr"}, "nontext header unsupported")
            index = int(value.text) if kind == "s" else None
            _require(index is None or index >= 0, "negative header shared-string index")
            if index is not None:
                wanted.add(index)
            cells.append((cell.attrib["r"], index, inline))
        shared = {}
        if wanted:
            with book.open("xl/sharedStrings.xml") as source:
                position = 0
                for _, element in ET.iterparse(_PrefixReader(source), events=("end",)):
                    if element.tag == TAG + "si":
                        if position in wanted:
                            shared[position] = "".join(element.itertext())
                        element.clear()
                        if position >= max(wanted):
                            break
                        position += 1
            _require(set(shared) == wanted, "header shared-string index absent")
        headers = []
        for column, index, inline in cells:
            label = shared[index] if index is not None else "".join(inline.itertext())
            _require(
                bool(label) and len(label) < 120 and "\n" not in label, "ambiguous header text"
            )
            _require(
                DIRECT_IDENTIFIERS.search(label) is None,
                "direct identifier header stops record analysis",
            )
            headers.append({"column": column, "label": label})
        _require(
            len({item["label"] for item in headers}) == len(headers), "duplicate header labels"
        )
        return headers


def verify_admission(package_root: Path, source_cache: Path | None = None) -> dict[str, Any]:
    """Verify authored pins/guards; optional caches reproduce headers only.

    The manifest itself must be bound by the evidence registry/package manifest
    when integrated. This function does not grant value access, establish source
    code meanings, prove participant deidentification or accept a clinical model.
    """
    package_root = package_root.resolve()
    package = _json(package_root / "docs/validation/kerala-source-admission-v2.json")
    _require(package["package_id"] == "kerala-source-admission-v2", "package identity")
    _require(
        package["parent_v1_sha256"]
        == _digest(package_root / "docs/validation/kerala-source-admission-v1.json"),
        "frozen admission v1 parent bind",
    )
    _require(package["source_id"] == "kerala2018_public_trial_v3", "source identity")
    _require(package["dataset_id"] == "kerala_source_admission", "dataset identity")
    _require(package["parameter_keys"] == [], "no model parameters permitted")
    _require(package["model_role"] == "benchmark_only", "benchmark role required")
    for flag in ("clinical_fit_allowed", "engine_activation_allowed", "scientific_release_ready"):
        _require(package[flag] is False, "package scientific flag drift")
    artifacts = package["artifacts"]
    _require(len({item["path"] for item in artifacts}) == len(artifacts), "duplicate artifact")
    documents = {
        Path(item["path"]).name: _json(_pinned_path(package_root, item)) for item in artifacts
    }
    required = {
        "kerala-source-schema-protocol-v1.json",
        "kerala-source-header-amendment-v1.json",
        "kerala-joint-coverage-intake-protocol-v1.json",
        "kerala-joint-coverage-intake-protocol-v2.json",
        "kerala-source-headers-v1.json",
        "kerala-source-appraisal-amendment-v1.json",
        "kerala-source-acquisition-receipts-v1.json",
        "kerala-clinical-contract-schema-coverage-v1.json",
        "kerala-source-schema-coverage-original-redacted-v1.json",
        "kerala-source-artifact-translation-v1.json",
        "kerala-source-followup-snapshot-amendment-v1.json",
    }
    _require(set(documents) == required, "exact before-values artifact set required")
    schema = documents["kerala-source-schema-protocol-v1.json"]
    v1 = documents["kerala-joint-coverage-intake-protocol-v1.json"]
    v2 = documents["kerala-joint-coverage-intake-protocol-v2.json"]
    amendment = documents["kerala-source-appraisal-amendment-v1.json"]
    coverage = documents["kerala-clinical-contract-schema-coverage-v1.json"]
    for protocol in (schema, v1, v2, amendment, coverage):
        _gates(protocol["scientific_gates"])
    _require(schema["participant_rows_allowed"] is False, "schema cannot inspect rows")
    _require(schema["aggregate_outcomes_allowed"] is False, "schema cannot inspect outcomes")
    for protocol in (v1, v2):
        chronology = protocol["chronology"]
        _require(
            chronology["participant_values_inspected"] is False,
            "intake protocol was not before values",
        )
        _require(
            chronology["quantitative_workbook_counts_inspected"] is False,
            "intake protocol was not before quantitative counts",
        )
        _require(
            chronology["independent_validation_claim_allowed"] is False,
            "used-source protocol cannot claim independence",
        )
    for field in ("participant_values_inspected", "quantitative_workbook_counts_inspected"):
        _require(amendment[field] is False, "appraisal amendment not before values")
    _require(
        coverage["participant_rows_inspected"] is False,
        "schema coverage cannot contain row inspection",
    )
    _require(
        coverage["aggregate_workbook_outcomes_inspected"] is False,
        "schema coverage cannot contain outcomes",
    )
    _require(
        v2["supersedes"]["sha256"]
        == _digest(package_root / "docs/validation/kerala-joint-coverage-intake-protocol-v1.json"),
        "immutable prior protocol bind",
    )
    _require(
        _time(schema["frozen_at_utc"])
        <= _time(v1["frozen_at_utc"])
        <= _time(v2["frozen_at_utc"])
        <= _time(amendment["frozen_at_utc"]),
        "protocol chronology inconsistent",
    )
    receipts = documents["kerala-source-acquisition-receipts-v1.json"]
    _require(
        receipts["source_id"] == package["source_id"] == coverage["source_id"],
        "receipt/coverage source identity mismatch",
    )
    _require(
        coverage["actual_source_receipts"] == receipts["workbook_receipts"],
        "coverage workbook receipts differ from acquisition bundle",
    )
    _require(
        coverage["publication_receipt"] == receipts["publication_receipt"],
        "coverage publication receipt differs from acquisition bundle",
    )
    for key, name in (
        ("protocol", "kerala-source-schema-protocol-v1.json"),
        ("header_manifest", "kerala-source-headers-v1.json"),
    ):
        _require(
            coverage[key]["sha256"] == _digest(package_root / "docs/validation" / name),
            "coverage protocol/header artifact binding mismatch",
        )
    _pinned_path(package_root, coverage["source_appraisal_amendment"])
    metadata = receipts["release_metadata"]
    _require(
        metadata["id"] == 5661610 and metadata["version"] == 3,
        "exact public release version required",
    )
    _require(
        metadata["is_public"] is True and metadata["is_embargoed"] is False,
        "public unembargoed release required",
    )
    _require(metadata["doi"] == "10.6084/m9.figshare.5661610.v3", "version DOI")
    _require(metadata["license"]["name"] == "CC BY 4.0", "release license")
    _require(
        metadata["license"]["url"] == "https://creativecommons.org/licenses/by/4.0/",
        "release license URL",
    )
    file_ids = {39461149, 39461152}
    advertised = {item["id"]: item for item in metadata["files"]}
    actual = {item["file_id"]: item for item in receipts["workbook_receipts"]}
    _require(
        set(advertised) == file_ids and set(actual) == file_ids,
        "exact two advertised files required",
    )
    _require(
        len(metadata["files"]) == len(actual) == len(receipts["workbook_receipts"]),
        "duplicate source file",
    )
    headers = documents["kerala-source-headers-v1.json"]
    _require(len(headers) == 2, "two header manifests required")
    mapped = {item["file_id"]: item for item in headers}
    _require(set(mapped) == file_ids, "header file identities")
    for identifier in sorted(file_ids):
        public, receipt, manifest = advertised[identifier], actual[identifier], mapped[identifier]
        _require(receipt["status"] == 200, "successful source receipt required")
        _require(receipt["url"] == public["download_url"], "public URL mismatch")
        _require(receipt["bytes"] == public["size"], "source size mismatch")
        _require(
            receipt["md5"] == public["supplied_md5"] == public["computed_md5"],
            "advertised MD5 mismatch",
        )
        _require(receipt["raw_filename"] == public["name"], "raw file name mismatch")
        _require(receipt["source_doi"] == metadata["doi"], "receipt version DOI mismatch")
        _require(receipt["license"] == metadata["license"], "receipt license mismatch")
        _require(not urlsplit(receipt["final_url"]).query, "transient resolved query retained")
        _require(
            not any(
                key.lower().startswith(("x-amz-", "x-goog-"))
                for key in parse_qs(urlsplit(receipt["url"]).query)
            ),
            "signed public URL retained",
        )
        _require(isinstance(receipt["signed_query_omitted"], bool), "query disposition missing")
        _require(manifest["file_sha256"] == receipt["sha256"], "header source pin mismatch")
        _require(
            manifest["sheet"] == "Sheet 1" and manifest["header_row"] == 2, "header locator changed"
        )
        _require(
            manifest["participant_rows_inspected"] is False, "header manifest cannot inspect rows"
        )
        labels = manifest["headers"]
        _require(len({item["label"] for item in labels}) == len(labels), "duplicate labels")
        _require(len({item["column"] for item in labels}) == len(labels), "duplicate locators")
        _require(
            all(re.fullmatch(r"[A-Z]+2", item["column"]) for item in labels), "nonheader locator"
        )
        _require(
            all(DIRECT_IDENTIFIERS.search(item["label"]) is None for item in labels),
            "direct identifier header",
        )
        selected = v2[
            "minimum_fields_primary" if identifier == 39461149 else "minimum_fields_secondary"
        ]
        _require(
            len(selected) == len(set(selected))
            and set(selected) <= {item["label"] for item in labels},
            "selected fields absent or duplicated",
        )
        _require(
            _time(schema["frozen_at_utc"]) <= _time(receipt["retrieved_at_utc"]),
            "schema protocol not before source acquisition",
        )
        if source_cache is not None:
            raw = (source_cache / receipt["raw_filename"]).resolve()
            _require(raw.is_relative_to(source_cache.resolve()), "raw path escapes cache")
            _require(
                raw.stat().st_size == receipt["bytes"] and _digest(raw) == receipt["sha256"],
                "raw cache source pin mismatch",
            )
            _require(
                hashlib.md5(raw.read_bytes()).hexdigest() == receipt["md5"],
                "raw cache MD5 mismatch",
            )
            _require(read_headers_only(raw) == labels, "raw header reproduction failed")
    _semantic_bindings(package_root, documents, source_cache)
    return {
        "source_id": package["source_id"],
        "artifact_pins_verified": True,
        "before_values_protocol_recorded": True,
        "optional_source_header_reproduction": source_cache is not None,
        "participant_records_inspected": False,
        "participant_values_inspected": False,
        "joint_person_wave_coverage_verified": False,
        "source_code_semantics_verified": False,
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "independent_validation_allowed": False,
        "scientific_release_ready": False,
        "interpretation": "Intake artifacts and optional headers verified; clinical admission remains unresolved.",
    }
