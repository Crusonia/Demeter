"""Synthetic byte/header checks; ordinary tests never open public participant data."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from demeter.data.hutelin_preflight import (
    CONTRACT_SHA256,
    _audit,
    _check_archive,
    _header,
    audit_hutelin_preflight,
)

ROOT = Path(__file__).resolve().parents[1]
LIMITS = dict(
    source_bytes=8192,
    archive_members=10,
    declared_uncompressed_bytes=8192,
    selected_member_bytes=4096,
    header_bytes=32,
    header_columns=8,
)
HEADER = b"id,condition,time,glucose\n"
SELECTED = dict(
    member="data/raw/blood.csv",
    header_sha256=hashlib.sha256(HEADER).hexdigest(),
    header_bytes=len(HEADER),
    columns=["id", "condition", "time", "glucose"],
)


def archive_bytes(content=HEADER + b"\xffinvalid-utf8-participant-row\n"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(SELECTED["member"], content)
    return stream.getvalue()


def test_header_never_decodes_following_row():
    with zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive:
        assert _header(archive, SELECTED, LIMITS) == SELECTED


@pytest.mark.parametrize(
    "content",
    [b"id,condition,time,other\n", b"x" * 33 + b"\n", b"id,condition,time,glucose", b"\xff\n"],
)
def test_changed_unterminated_oversized_or_invalid_header_rejected(content):
    with zipfile.ZipFile(io.BytesIO(archive_bytes(content))) as archive:
        with pytest.raises((ValueError, UnicodeDecodeError)):
            _header(archive, SELECTED, LIMITS)


def test_member_limit_and_missing_selected_member():
    with zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive:
        with pytest.raises(ValueError):
            _header(archive, SELECTED, dict(LIMITS, selected_member_bytes=1))
        with pytest.raises(KeyError):
            _header(archive, dict(SELECTED, member="unselected.csv"), LIMITS)


def test_directory_total_limit():
    with zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive:
        with pytest.raises(ValueError):
            _check_archive(archive, dict(LIMITS, declared_uncompressed_bytes=1))


def test_duplicate_directory_members_rejected():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("same", "one")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("same", "two")
    with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as archive:
        with pytest.raises(ValueError):
            _check_archive(archive, LIMITS)


def test_finite_synthetic_audit_and_source_change(tmp_path):
    raw = archive_bytes()
    source = tmp_path / "data-original.zip"
    source.write_bytes(raw)
    contract = dict(
        limits=LIMITS,
        sources=[dict(local_filename=source.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())],
        headers=[SELECTED],
        code_members=[],
        id="synthetic",
        record_doi="synthetic",
    )
    report = _audit(tmp_path, contract)
    assert report["selected_headers_verified"] == [SELECTED]
    assert report["participant_rows_decoded"] is False
    assert report["full_data_member_crc_verified"] is False
    assert report["outcome_estimates"] is None
    source.write_bytes(raw + b"modified")
    with pytest.raises(ValueError, match="source bytes differ"):
        _audit(tmp_path, contract)


def test_changed_contract_fails_before_any_source_access(tmp_path):
    contract = tmp_path / "modified.json"
    contract.write_text("{}")
    with pytest.raises(ValueError, match="contract differs"):
        audit_hutelin_preflight(tmp_path / "does-not-exist", contract)


def test_committed_scope_and_actual_receipt_reconcile():
    raw = (ROOT / "docs/validation/hutelin2026-preflight-contract-v1.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_SHA256
    contract = json.loads(raw)
    report = json.loads((ROOT / "docs/validation/hutelin2026-preflight-result-v1.json").read_bytes())
    assert report["contract_sha256"] == CONTRACT_SHA256
    assert report["record_doi"] == contract["record_doi"]
    assert report["selected_headers_verified"] == contract["headers"]
    assert report["selected_code_identities_verified"] == contract["code_members"]
    assert report["source_identities_verified"] == [
        dict(filename=row["local_filename"], bytes=row["bytes"], sha256=row["sha256"])
        for row in contract["sources"]
    ]
    assert report["scientific_release_ready"] is False
    assert report["clinical_parameters_admitted"] is False
