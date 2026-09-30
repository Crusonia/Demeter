"""Audit fetch-only public documentation metadata and optional local bytes offline."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import AfterValidator, ConfigDict, Field, field_validator, model_validator

from demeter.schema import StrictModel


def validate_cache_filename(value: str) -> str:
    """Require one filename usable without aliases or traversal on all supported OSes."""
    stem = value.split(".", 1)[0].upper()
    if (
        not value
        or value in {".", ".."}
        or value != value.strip()
        or value.endswith(".")
        or re.search(r'[<>:"/\\|?*\x00-\x1f]', value)
        or stem in {"CON", "PRN", "AUX", "NUL"}
        or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", stem)
    ):
        raise ValueError("Documentation cache filename must be a portable basename")
    return value


def validate_https_url(value: str) -> str:
    """Validate an HTTPS URL without rewriting its provenance bytes."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or "\\" in value
        or any(character.isspace() or ord(character) < 32 for character in value)
    ):
        raise ValueError("Documentation URLs must be HTTPS without credentials or whitespace")
    # Accessing port rejects malformed/non-numeric/out-of-range URL ports.
    _ = parsed.port
    return value


PortableCacheFilename = Annotated[str, AfterValidator(validate_cache_filename)]
HttpsDocumentationUrl = Annotated[str, AfterValidator(validate_https_url)]


class DocumentationReceipt(StrictModel):
    """A public-document download receipt, never a participant-data receipt."""

    model_config = ConfigDict(strict=True)

    cache_filename: PortableCacheFilename
    distribution: Literal["fetch_only"]
    url: HttpsDocumentationUrl
    final_url: HttpsDocumentationUrl
    retrieved_utc: datetime
    size_bytes: int = Field(gt=0, strict=True)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal[200]
    content_type: str = Field(min_length=1)
    registry_source_id: str | None = Field(default=None, min_length=1)

    @field_validator("status", mode="before")
    @classmethod
    def strict_status(cls, value):
        if type(value) is not int:
            raise ValueError("Documentation HTTP status must be the integer 200")
        return value

    @field_validator("content_type", "registry_source_id")
    @classmethod
    def meaningful_text(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Documentation metadata text cannot be blank")
        return value

    @model_validator(mode="after")
    def aware_retrieval(self):
        if self.retrieved_utc.utcoffset() is None:
            raise ValueError("Documentation retrieval timestamp must have a timezone")
        return self


class CoverageReceipts(StrictModel):
    """Public field-coverage appraisal, with its non-clinical boundary enforced."""

    model_config = ConfigDict(strict=True)

    schema_version: Literal[1]
    assessment_date: date
    purpose: str = Field(min_length=1)
    rights_approach: str = Field(min_length=1)
    full_documents_redistributed: Literal[False]
    participant_records_acquired: Literal[False]
    participant_records_requested: Literal[False]
    actual_record_coverage: Literal["not_acquired"]
    clinical_fit_allowed: Literal[False]
    frozen_observation_contract_changed: Literal[False]
    sources: dict[str, DocumentationReceipt] = Field(min_length=1)

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int:
            raise ValueError("Documentation schema version must be the integer 1")
        return value

    @field_validator(
        "full_documents_redistributed",
        "participant_records_acquired",
        "participant_records_requested",
        "clinical_fit_allowed",
        "frozen_observation_contract_changed",
        mode="before",
    )
    @classmethod
    def strict_boundary_flags(cls, value):
        if type(value) is not bool:
            raise ValueError("Documentation scope flags must be literal false booleans")
        return value

    @field_validator("purpose", "rights_approach")
    @classmethod
    def meaningful_scope(cls, value):
        if not value.strip():
            raise ValueError("Documentation scope text cannot be blank")
        return value

    @model_validator(mode="after")
    def unique_cache_names(self):
        if any(not key or key != key.strip() for key in self.sources):
            raise ValueError("Documentation source labels cannot be blank or padded")
        names = [item.cache_filename.casefold() for item in self.sources.values()]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate documentation cache filename")
        return self


class DocumentationRightsLike(Protocol):
    """Structural interface; the rights model lives in packages, avoiding a cycle."""

    cache_filename: str
    distribution: str
    privacy: str
    url: str
    final_url: str
    retrieved_at: datetime
    size_bytes: int
    sha256: str
    status: int
    content_type: str
    registry_source_id: str | None


def _unique_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate documentation JSON key: {key}")
        result[key] = value
    return result


def _local_bytes(raw: Path, filename: str) -> tuple[int | None, str | None, str | None]:
    path = raw / filename
    if raw.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(raw.resolve()):
        return None, None, "unsafe_path"
    if not path.is_file():
        return None, None, "missing_or_not_file"
    try:
        content = path.read_bytes()
    except OSError:
        return None, None, "unreadable"
    return len(content), hashlib.sha256(content).hexdigest(), None


def audit_documentation_sources(
    receipt_path: Path,
    rights: Mapping[str, DocumentationRightsLike],
    raw: Path | None = None,
) -> dict:
    """Cross-check every receipt with rights metadata and optionally all source bytes.

    Invalid schemas fail closed. Well-formed metadata mismatches and missing or
    changed local files remain reviewable failed checks. No network is used, no
    raw document content is returned, and byte agreement is not scientific or
    legal validation.
    """
    content = receipt_path.read_bytes()
    json.loads(content, object_pairs_hook=_unique_json_keys)
    receipts = CoverageReceipts.model_validate_json(content)
    checks, source_checks = [], []

    def check(name: str, passed: bool, **detail):
        checks.append({"check": name, "passed": bool(passed), **detail})

    labels, rights_labels = set(receipts.sources), set(rights)
    check(
        "documentation_source_set",
        labels == rights_labels,
        missing_rights=sorted(labels - rights_labels),
        extra_rights=sorted(rights_labels - labels),
    )
    absent = object()
    fields = {
        "cache_filename": "cache_filename",
        "distribution": "distribution",
        "url": "url",
        "final_url": "final_url",
        "retrieved_utc": "retrieved_at",
        "size_bytes": "size_bytes",
        "sha256": "sha256",
        "status": "status",
        "content_type": "content_type",
        "registry_source_id": "registry_source_id",
    }
    for label, receipt in receipts.sources.items():
        item = rights.get(label)
        mismatches = [
            key
            for key, rights_key in fields.items()
            if item is None or getattr(item, rights_key, absent) != getattr(receipt, key)
        ]
        check("documentation_rights_present", item is not None, source=label)
        check("documentation_metadata_match", not mismatches, source=label, fields=mismatches)
        check(
            "documentation_fetch_only",
            item is not None
            and item.distribution == "fetch_only"
            and item.privacy in {"publication", "metadata"},
            source=label,
        )
        source_checks.append(
            {
                "source": label,
                **receipt.model_dump(mode="json"),
                "metadata_match": not mismatches,
                "metadata_mismatches": mismatches,
                "local_byte_check": "not_requested",
                "actual_size_bytes": None,
                "actual_sha256": None,
                "raw_error": None,
            }
        )
    metadata_passed = all(row["passed"] for row in checks)
    if raw is not None:
        for row in source_checks:
            size, sha256, error = _local_bytes(raw, row["cache_filename"])
            row.update(actual_size_bytes=size, actual_sha256=sha256, raw_error=error)
            size_matches, hash_matches = size == row["size_bytes"], sha256 == row["sha256"]
            row["local_byte_check"] = "passed" if size_matches and hash_matches else "failed"
            check("documentation_raw_size", size_matches, source=row["source"])
            check("documentation_raw_checksum", hash_matches, source=row["source"])
    raw_passed = (
        all(row["local_byte_check"] == "passed" for row in source_checks)
        if raw is not None
        else None
    )
    return {
        "schema_version": "documentation_source_audit_v1",
        "kind": "public_documentation_only",
        "passed": all(row["passed"] for row in checks),
        "metadata_passed": metadata_passed,
        "network_used": False,
        "raw_bytes_checked": raw is not None,
        "raw_bytes_passed": raw_passed,
        "full_documents_redistributed": False,
        "participant_records_acquired": False,
        "participant_records_requested": False,
        "actual_record_coverage": "not_acquired",
        "clinical_fit_allowed": False,
        "frozen_observation_contract_changed": False,
        "counts": {
            "sources": len(receipts.sources),
            "rights": len(rights),
            "metadata_matched": sum(row["metadata_match"] for row in source_checks),
            "raw_documents_requested": len(source_checks) if raw is not None else 0,
            "raw_documents_read": sum(row["actual_sha256"] is not None for row in source_checks),
            "raw_documents_passed": sum(
                row["local_byte_check"] == "passed" for row in source_checks
            ),
        },
        "source_checks": source_checks,
        "checks": checks,
        "interpretation": "Checks recorded public-document provenance and optional bytes only. "
        "No raw content is exported, participant coverage remains unverified, "
        "and agreement does not authorize redistribution or clinical fitting.",
    }
