"""Finite documentary/header replay; never decode participant rows or execute R."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

CONTRACT_SHA256 = "8d7caec48404816c0382db08052c5f5a4f55e252e5d0b686d8da7d899ab3d2bf"


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _check_archive(archive: zipfile.ZipFile, limits: dict) -> None:
    infos = archive.infolist()
    if (
        len(infos) > limits["archive_members"]
        or len({info.filename for info in infos}) != len(infos)
        or sum(info.file_size for info in infos) > limits["declared_uncompressed_bytes"]
        or any(info.flag_bits & 1 for info in infos)
    ):
        raise ValueError("archive directory outside selected scope")


def _header(archive: zipfile.ZipFile, selected: dict, limits: dict) -> dict:
    info = archive.getinfo(selected["member"])
    if info.is_dir() or info.file_size > limits["selected_member_bytes"]:
        raise ValueError("selected CSV member outside size limit")
    # readline is deliberately bounded; no CSV reader ever receives a participant row.
    # ZIP decompression may buffer bytes beyond the header; these are not decoded/exported.
    with archive.open(info) as stream:
        raw = stream.readline(limits["header_bytes"] + 1)
    if not raw.endswith(b"\n") or len(raw) > limits["header_bytes"]:
        raise ValueError("selected header missing newline or exceeds limit")
    columns = next(csv.reader([raw.decode("utf-8-sig")], strict=True))
    if not columns or len(columns) > limits["header_columns"]:
        raise ValueError("selected header column limit")
    observed = dict(
        member=selected["member"],
        header_sha256=_digest(raw),
        header_bytes=len(raw),
        columns=columns,
    )
    if observed != selected:
        raise ValueError("selected header differs from pinned source")
    return observed


def _audit(raw_dir: Path, contract: dict) -> dict:
    limits = contract["limits"]
    originals = {}
    sources = []
    for source in contract["sources"]:
        name = source["local_filename"]
        if Path(name).name != name or name in ("", ".", ".."):
            raise ValueError("source filename must be a basename")
        with (raw_dir / name).open("rb") as stream:
            raw = stream.read(limits["source_bytes"] + 1)
        if len(raw) > limits["source_bytes"]:
            raise ValueError("source exceeds byte limit")
        if len(raw) != source["bytes"] or _digest(raw) != source["sha256"]:
            raise ValueError("source bytes differ from pinned source")
        originals[name] = raw
        sources.append(dict(filename=name, bytes=len(raw), sha256=_digest(raw)))

    headers = []
    code_members = []
    for name, raw in originals.items():
        if not name.endswith(".zip"):
            continue
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            _check_archive(archive, limits)
            if name == "data-original.zip":
                headers = [_header(archive, row, limits) for row in contract["headers"]]
                if "data/derived/imputed_data.csv" in archive.namelist():
                    raise ValueError("unexpected precomputed imputed data member")
            for selected in contract["code_members"]:
                if selected["archive"] != name:
                    continue
                info = archive.getinfo(selected["member"])
                if info.file_size > limits["selected_member_bytes"]:
                    raise ValueError("selected code exceeds member limit")
                content = archive.read(info)
                if len(content) != selected["bytes"] or _digest(content) != selected["sha256"]:
                    raise ValueError("selected code differs from pinned source")
                code_members.append(dict(selected))

    return dict(
        schema_version=1,
        contract_id=contract["id"],
        record_doi=contract["record_doi"],
        source_identities_verified=sources,
        selected_headers_verified=headers,
        selected_code_identities_verified=code_members,
        participant_rows_decoded=False,
        full_data_member_crc_verified=False,
        author_code_executed=False,
        outcome_estimates=None,
        clinical_parameters_admitted=False,
        scientific_release_ready=False,
        interpretation="Source/header reproduction only; not clinical or independent validation.",
    )


def audit_hutelin_preflight(raw_dir: Path, contract_path: Path) -> dict:
    raw = contract_path.read_bytes()
    if _digest(raw) != CONTRACT_SHA256:
        raise ValueError("preflight contract differs from reviewed scope")
    report = _audit(raw_dir, json.loads(raw))
    return dict(contract_sha256=CONTRACT_SHA256, **report)
