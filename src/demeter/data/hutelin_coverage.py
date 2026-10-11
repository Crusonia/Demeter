"""Finite source-specific blood-record coverage; no clinical effect estimation."""

from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile

from demeter.data.hutelin_preflight import audit_hutelin_preflight

PROTOCOL_SHA256 = "00baba7b9a0579d15595f51f88309b2199ab63e0535575696d17972b3df326bd"


def audit_hutelin_coverage(raw_dir: Path, root: Path) -> dict:
    protocol_path = root / "docs/validation/hutelin2026-blood-coverage-protocol-v1.json"
    protocol_raw = protocol_path.read_bytes()
    if hashlib.sha256(protocol_raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("coverage protocol differs from frozen scope")
    protocol = json.loads(protocol_raw)
    # Documentary/header guard completes before any participant row is opened.
    preflight = audit_hutelin_preflight(
        raw_dir, root / "docs/validation/hutelin2026-preflight-contract-v1.json"
    )
    if preflight["contract_sha256"] != protocol["source_preflight_contract_sha256"]:
        raise ValueError("preflight identity differs from frozen coverage scope")
    with (raw_dir / "data-original.zip").open("rb") as stream:
        original = stream.read(8388609)
    if hashlib.sha256(original).hexdigest() != protocol["source_archive_sha256"]:
        raise ValueError("coverage source differs from frozen archive")
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        info = archive.getinfo(protocol["selected_member"])
        if info.file_size > protocol["limits"]["member_bytes"]:
            raise ValueError("coverage member exceeds frozen size limit")
        # Reading this one selected member verifies its full decompression/CRC.
        raw = archive.read(info)
    result = coverage_csv(
        raw,
        max_bytes=protocol["limits"]["member_bytes"],
        max_rows=protocol["limits"]["data_rows"],
    )
    return dict(
        protocol_sha256=PROTOCOL_SHA256,
        preflight_contract_sha256=preflight["contract_sha256"],
        archive_sha256=protocol["source_archive_sha256"],
        selected_member_sha256=hashlib.sha256(raw).hexdigest(),
        selected_member_crc_verified=True,
        participant_rows_decoded=True,
        participant_records_exported=False,
        runtime_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        assay_provenance="Finite numeric prepared values; not verified raw assay observations.",
        interpretation="Descriptive source coverage only; no AUC, clinical rate or causal effect.",
        **result,
    )


CONDITIONS = ("mpf", "upf")
TIMES = (0, 5, 10, 20, 40, 60, 90, 120, 180)
REFERENCE_GRIDS = {
    "code_suffix_grid": TIMES,
    "published_postmeal_grid_with_unverified_source0_baseline": (0, 5, 20, 40, 60, 90, 120, 180),
}
FIELDS = ("glucose", "insulin", "insulin_w0", "insulin_impute")
NUMERIC_TOKEN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
EXPECTED_HEADER = (
    "id",
    "condition",
    "time",
    "a1c",
    "time_fac",
    "gluc1",
    "gluc2",
    "gluc3",
    "gluc_ave",
    "glucose",
    "insulin",
    "insulin_w0",
    "insulin_impute",
)


def coverage_csv(raw, max_bytes=1048576, max_rows=10000):
    """CSV strings are transient; only the declared fields receive semantic use."""
    if len(raw) > max_bytes or b"\0" in raw:
        raise ValueError("CSV bytes outside selected framing scope")
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    if tuple(next(reader, ())) != EXPECTED_HEADER:
        raise ValueError("CSV header differs from selected source")

    def projected_rows():
        for index, cells in enumerate(reader):
            if index >= max_rows:
                raise ValueError("CSV record limit exceeded")
            if len(cells) != len(EXPECTED_HEADER) or any("\n" in c or "\r" in c for c in cells):
                raise ValueError("CSV record outside selected flat-row framing")
            source = dict(zip(EXPECTED_HEADER, cells, strict=True))
            yield {field: source[field] for field in ("id", "condition", "time", *FIELDS)}

    return coverage(projected_rows())


def _finite_number(value):
    if not isinstance(value, str) or not NUMERIC_TOKEN.fullmatch(value.strip()):
        raise ValueError("not a scalar numeric token")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("not a finite numeric token")
    return number


def token_status(value):
    if value in ("", "NA"):
        return "literal_missing"
    try:
        _finite_number(value)
    except (ValueError, TypeError):
        return "unclassified"
    return "finite_numeric"


def coverage(rows):
    """Input rows are transient; returned object contains no person-linked fields."""
    totals = Counter()
    invalid_reasons = Counter()
    keys = Counter()
    sessions = defaultdict(set)
    assay = {field: Counter() for field in FIELDS}
    support = {condition: Counter() for condition in CONDITIONS}
    complete_assays = {field: defaultdict(set) for field in FIELDS}
    grouped_assays = {
        c: {t: {field: Counter() for field in FIELDS} for t in TIMES} for c in CONDITIONS
    }
    for row in rows:
        totals["physical_rows"] += 1
        for field in FIELDS:
            assay[field][token_status(row[field])] += 1
        reasons = []
        if row["id"] in ("", "NA") or not row["id"].strip():
            reasons.append("missing_id")
        if row["condition"] not in CONDITIONS:
            reasons.append("unknown_condition")
        label = None
        try:
            value = _finite_number(row["time"])
            if not math.isfinite(value) or not value.is_integer():
                reasons.append("malformed_time")
            elif value not in TIMES:
                reasons.append("unexpected_time")
            else:
                label = int(value)
        except (ValueError, TypeError):
            reasons.append("malformed_time")
        if reasons:
            totals["invalid_key_rows"] += 1
            invalid_reasons.update(reasons)
            continue
        totals["valid_key_rows"] += 1
        key = (row["id"], row["condition"], label)
        keys[key] += 1
        sessions[row["id"]].add(row["condition"])
        support[row["condition"]][label] += 1
        for field in FIELDS:
            grouped_assays[row["condition"]][label][field][token_status(row[field])] += 1
            if token_status(row[field]) == "finite_numeric":
                complete_assays[field][(row["id"], row["condition"])].add(label)
    paired = sum(set(CONDITIONS) == conditions for conditions in sessions.values())
    repeated_keys = {key for key, count in keys.items() if count > 1}
    repeated_sessions = {(key[0], key[1]) for key in repeated_keys}
    # Completeness for the fixed code grid is coverage, not a justified AUC horizon.
    full = {
        name: {
            field: sum(
                set(grid).issubset(labels) and session not in repeated_sessions
                for session, labels in groups.items()
            )
            for field, groups in complete_assays.items()
        }
        for name, grid in REFERENCE_GRIDS.items()
    }
    result = dict(
        physical_rows=totals["physical_rows"],
        valid_key_rows=totals["valid_key_rows"],
        invalid_key_rows=totals["invalid_key_rows"],
        nonexclusive_invalid_reason_counts=dict(invalid_reasons),
        unique_valid_keys=len(keys),
        duplicate_key_count=len(repeated_keys),
        extra_duplicate_rows=sum(count - 1 for count in keys.values()),
        duplicate_affected_sessions=len(repeated_sessions),
        participants_with_valid_keys=len(sessions),
        paired_condition_participants=paired,
        single_condition_participants=len(sessions) - paired,
        valid_key_time_support={c: {str(t): support[c][t] for t in TIMES} for c in CONDITIONS},
        assay_token_accounting={
            field: {
                status: counts[status]
                for status in ["literal_missing", "finite_numeric", "unclassified"]
            }
            for field, counts in assay.items()
        },
        reference_grid_coverage_sessions_finite_without_duplicate_keys=full,
        valid_key_assay_token_support={
            c: {
                str(t): {
                    field: {
                        status: counts[status]
                        for status in ["literal_missing", "finite_numeric", "unclassified"]
                    }
                    for field, counts in fields.items()
                }
                for t, fields in by_time.items()
            }
            for c, by_time in grouped_assays.items()
        },
        clinical_parameters_admitted=False,
        outcome_estimates=None,
    )
    assert result["physical_rows"] == result["valid_key_rows"] + result["invalid_key_rows"]
    assert result["valid_key_rows"] == result["unique_valid_keys"] + result["extra_duplicate_rows"]
    assert all(
        sum(values.values()) == result["physical_rows"]
        for values in result["assay_token_accounting"].values()
    )
    return result
