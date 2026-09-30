"""Synthetic receipt audits; never acquire or redistribute external documents."""

import copy
import hashlib
import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from demeter.data.documentation import CoverageReceipts, audit_documentation_sources


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def documentation(tmp_path):
    payload = {
        "schema_version": 1,
        "assessment_date": "2026-09-30",
        "purpose": "Synthetic public-document metadata test only.",
        "rights_approach": "Synthetic fetch-only policy.",
        "full_documents_redistributed": False,
        "participant_records_acquired": False,
        "participant_records_requested": False,
        "actual_record_coverage": "not_acquired",
        "clinical_fit_allowed": False,
        "frozen_observation_contract_changed": False,
        "sources": {},
    }
    raw = tmp_path / "raw"
    raw.mkdir()
    rights = {}
    for label, filename, source_id in [
        ("PRIMARY", "paper.html", "synthetic_primary"),
        ("FORM", "form.pdf", None),
    ]:
        content = f"Synthetic document {label}; not participant records.".encode()
        receipt = {
            "cache_filename": filename,
            "distribution": "fetch_only",
            "url": f"https://example.org/{filename}",
            "final_url": f"https://example.org/{filename}",
            "retrieved_utc": "2026-09-30T19:16:23.469918+00:00",
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "status": 200,
            "content_type": "text/html" if label == "PRIMARY" else "application/pdf",
            "registry_source_id": source_id,
        }
        payload["sources"][label] = receipt
        item = {**receipt, "privacy": "publication"}
        item["retrieved_at"] = datetime.fromisoformat(item.pop("retrieved_utc"))
        rights[label] = SimpleNamespace(**item)
        (raw / filename).write_bytes(content)
    path = tmp_path / "receipts.json"
    write_json(path, payload)
    return path, payload, rights, raw


def failed(report, check):
    return any(row["check"] == check and not row["passed"] for row in report["checks"])


def test_offline_audit_distinguishes_metadata_from_unchecked_raw(documentation, monkeypatch):
    path, _, rights, _ = documentation

    def no_network(*args, **kwargs):
        pytest.fail("Documentation audit must not fetch documents")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    monkeypatch.setattr("socket.socket.connect", no_network)
    report = audit_documentation_sources(path, rights)
    assert report["passed"] and report["metadata_passed"]
    assert not report["network_used"]
    assert report["raw_bytes_checked"] is False
    assert report["raw_bytes_passed"] is None
    assert report["counts"]["raw_documents_requested"] == 0
    assert report["counts"]["raw_documents_read"] == 0
    assert {row["local_byte_check"] for row in report["source_checks"]} == {"not_requested"}
    assert all(row["actual_sha256"] is None for row in report["source_checks"])
    assert report["participant_records_acquired"] is False
    assert report["clinical_fit_allowed"] is False
    assert "Synthetic document" not in json.dumps(report)


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://example.org/changed"),
        ("final_url", "https://example.org/redirected"),
        ("sha256", "0" * 64),
        ("retrieved_utc", "2026-09-29T19:16:23.469918+00:00"),
        ("size_bytes", 123456),
        ("cache_filename", "renamed.html"),
        ("content_type", "application/pdf"),
        ("registry_source_id", "wrong_link"),
    ],
)
def test_semantic_tamper_fails_even_after_new_outer_checksum(documentation, field, value):
    path, payload, rights, _ = documentation
    original_outer_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    payload["sources"]["PRIMARY"][field] = value
    write_json(path, payload)
    new_outer_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert original_outer_sha != new_outer_sha
    report = audit_documentation_sources(path, rights)
    assert not report["passed"]
    assert failed(report, "documentation_metadata_match")
    row = next(row for row in report["source_checks"] if row["source"] == "PRIMARY")
    assert row["metadata_mismatches"] == [field]


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_exact_source_set_required(documentation, change):
    path, _, rights, _ = documentation
    if change == "missing":
        rights.pop("FORM")
    else:
        rights["UNREVIEWED"] = rights["FORM"]
    report = audit_documentation_sources(path, rights)
    assert not report["passed"]
    assert failed(report, "documentation_source_set")
    assert len(report["source_checks"]) == 2


@pytest.mark.parametrize(
    "field,value", [("distribution", "archived"), ("privacy", "public_use_microdata")]
)
def test_documentation_rights_cannot_admit_participant_data_or_raw_distribution(
    documentation, field, value
):
    path, _, rights, _ = documentation
    setattr(rights["FORM"], field, value)
    report = audit_documentation_sources(path, rights)
    assert not report["passed"]
    assert failed(report, "documentation_fetch_only")


def test_raw_mode_checks_every_document_without_exporting_contents(documentation):
    path, _, rights, raw = documentation
    report = audit_documentation_sources(path, rights, raw)
    assert report["passed"] and report["raw_bytes_passed"] is True
    assert report["raw_bytes_checked"] is True
    assert report["counts"]["raw_documents_requested"] == 2
    assert report["counts"]["raw_documents_read"] == 2
    assert report["counts"]["raw_documents_passed"] == 2
    assert {row["local_byte_check"] for row in report["source_checks"]} == {"passed"}
    assert "Synthetic document" not in json.dumps(report)


@pytest.mark.parametrize("change", ["changed_same_size", "changed_size", "missing", "directory"])
def test_missing_or_changed_raw_remains_a_saved_failure(documentation, change):
    path, _, rights, raw = documentation
    source = raw / "form.pdf"
    if change == "changed_same_size":
        source.write_bytes(b"x" * source.stat().st_size)
    elif change == "changed_size":
        source.write_bytes(b"x")
    else:
        source.unlink()
        if change == "directory":
            source.mkdir()
    report = audit_documentation_sources(path, rights, raw)
    assert report["metadata_passed"] is True
    assert not report["passed"] and report["raw_bytes_passed"] is False
    assert len(report["source_checks"]) == 2
    row = next(row for row in report["source_checks"] if row["source"] == "FORM")
    assert row["local_byte_check"] == "failed"
    assert failed(report, "documentation_raw_checksum")
    if change != "changed_same_size":
        assert failed(report, "documentation_raw_size")
    # This is JSON-serializable failure evidence; a caller can always save it.
    assert json.loads(json.dumps(report))["raw_bytes_passed"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("cache_filename", "../outside.pdf"),
        ("cache_filename", "folder/file.pdf"),
        ("cache_filename", "folder\\file.pdf"),
        ("cache_filename", "C:outside.pdf"),
        ("cache_filename", "/outside.pdf"),
        ("cache_filename", ".."),
        ("cache_filename", "CON.pdf"),
        ("cache_filename", "file.pdf."),
        ("cache_filename", "file.pdf "),
        ("url", "http://example.org/source"),
        ("url", "https://"),
        ("final_url", "http://example.org/source"),
        ("url", "https://user:secret@example.org/source"),
        ("url", "https://example.org:invalid/source"),
        ("retrieved_utc", "2026-09-30T19:16:23"),
        ("size_bytes", 0),
        ("size_bytes", -1),
        ("size_bytes", True),
        ("size_bytes", "55"),
        ("size_bytes", 55.0),
        ("sha256", "g" * 64),
        ("sha256", "0" * 63),
        ("status", 404),
        ("status", "200"),
        ("status", 200.0),
        ("content_type", ""),
        ("content_type", "   "),
        ("distribution", "archived"),
        ("participant_records", []),
    ],
)
def test_invalid_receipts_fail_closed(documentation, field, value):
    path, payload, rights, _ = documentation
    payload["sources"]["PRIMARY"][field] = value
    write_json(path, payload)
    with pytest.raises(ValueError):
        audit_documentation_sources(path, rights)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", "1"),
        ("clinical_fit_allowed", True),
        ("clinical_fit_allowed", 0),
        ("participant_records_acquired", True),
        ("participant_records_requested", True),
        ("full_documents_redistributed", True),
        ("frozen_observation_contract_changed", True),
        ("actual_record_coverage", "verified"),
        ("sources", {}),
    ],
)
def test_scope_cannot_be_silently_promoted(documentation, field, value):
    path, payload, rights, _ = documentation
    payload[field] = value
    write_json(path, payload)
    with pytest.raises(ValueError):
        audit_documentation_sources(path, rights)


@pytest.mark.parametrize("filename", ["paper.html", "PAPER.HTML"])
def test_duplicate_cache_names_rejected_portably(documentation, filename):
    path, payload, rights, _ = documentation
    payload["sources"]["FORM"]["cache_filename"] = filename
    write_json(path, payload)
    with pytest.raises(ValueError, match="Duplicate documentation cache filename"):
        audit_documentation_sources(path, rights)


def test_duplicate_json_keys_are_not_silently_overwritten(documentation):
    path, _, rights, _ = documentation
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace('"schema_version": 1', '"schema_version": 99, "schema_version": 1')
    )
    with pytest.raises(ValueError, match="Duplicate documentation JSON key"):
        audit_documentation_sources(path, rights)


def test_unreadable_raw_is_a_failure_without_disclosing_bytes(documentation, monkeypatch):
    path, _, rights, raw = documentation
    original = type(path).read_bytes

    def unreadable(self):
        if self.name == "form.pdf":
            raise PermissionError("Synthetic denied access")
        return original(self)

    monkeypatch.setattr(type(path), "read_bytes", unreadable)
    report = audit_documentation_sources(path, rights, raw)
    assert not report["passed"]
    row = next(row for row in report["source_checks"] if row["source"] == "FORM")
    assert row["raw_error"] == "unreadable"
    assert row["actual_size_bytes"] is None and row["actual_sha256"] is None


@pytest.mark.parametrize("operation", ["resolve", "is_file", "is_symlink"])
def test_permission_denied_during_path_inspection_returns_failure_rows(
    documentation, monkeypatch, operation
):
    path, _, rights, raw = documentation
    original = getattr(type(path), operation)

    def denied(self, *args, **kwargs):
        if self.name == "form.pdf":
            raise PermissionError("Synthetic metadata inspection denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(path), operation, denied)
    report = audit_documentation_sources(path, rights, raw)
    assert report["metadata_passed"] is True
    assert report["raw_bytes_checked"] is True
    assert report["raw_bytes_passed"] is False and report["passed"] is False
    assert len(report["source_checks"]) == 2
    form = next(row for row in report["source_checks"] if row["source"] == "FORM")
    assert form["raw_error"] == "unreadable"
    assert form["local_byte_check"] == "failed"
    assert form["actual_size_bytes"] is None and form["actual_sha256"] is None
    assert report["counts"]["raw_documents_read"] == 1
    assert json.loads(json.dumps(report))["raw_bytes_passed"] is False


def test_symlink_resolution_loop_is_reported_as_unsafe_path(documentation, monkeypatch):
    path, _, rights, raw = documentation
    original = type(path).resolve

    def loop(self, *args, **kwargs):
        if self.name == "form.pdf":
            raise RuntimeError("Synthetic symlink-resolution loop")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(path), "resolve", loop)
    report = audit_documentation_sources(path, rights, raw)
    assert not report["passed"]
    form = next(row for row in report["source_checks"] if row["source"] == "FORM")
    assert form["raw_error"] == "unsafe_path"
    assert form["actual_size_bytes"] is None and form["actual_sha256"] is None


def test_symlink_raw_is_not_followed(documentation, tmp_path):
    path, _, rights, raw = documentation
    source = raw / "form.pdf"
    other = tmp_path / "outside.pdf"
    other.write_bytes(source.read_bytes())
    source.unlink()
    try:
        source.symlink_to(other)
    except OSError:
        pytest.skip("Host does not permit creating a synthetic symlink")
    report = audit_documentation_sources(path, rights, raw)
    assert not report["passed"]
    row = next(row for row in report["source_checks"] if row["source"] == "FORM")
    assert row["raw_error"] == "unsafe_path"


def test_optional_registry_link_does_not_invent_an_empirical_source(documentation):
    _, payload, _, _ = documentation
    del payload["sources"]["FORM"]["registry_source_id"]
    parsed = CoverageReceipts.model_validate_json(json.dumps(payload))
    assert parsed.sources["FORM"].registry_source_id is None
    assert parsed.sources["PRIMARY"].registry_source_id == "synthetic_primary"
    # Validation must not modify the caller's source payload.
    before = copy.deepcopy(payload)
    CoverageReceipts.model_validate_json(json.dumps(payload))
    assert payload == before
