"""Source-column preparation patterns; never clinical flags or effects."""

from collections import Counter
from decimal import Decimal, localcontext
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile

from demeter.data.hutelin_coverage import EXPECTED_HEADER
from demeter.data.hutelin_preflight import audit_hutelin_preflight
from demeter.schema import EvidenceRegistry

NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
PROTOCOL_SHA256 = "df4f550ddb2a7e5b7e37a3568a1939e7a00a23a9695675a7ab084efc7750302d"
KEYS = (
    "hutelin2026_insulin_reported_loq",
    "hutelin2026_low_value_replacement",
    "hutelin2026_storage_half_quantum",
)
CATEGORIES = (
    "unclassified_token",
    "all_insulin_cells_missing",
    "native_missing_zero_and_replacement_compatible",
    "native_missing_other_prepared_pattern",
    "native_present_prepared_equal",
    "native_present_prepared_missing",
    "native_present_prepared_discrepant",
)


def number(token):
    if token in ("", "NA"):
        return None
    if len(token) > 64 or not NUMBER.fullmatch(token.strip()) or not math.isfinite(float(token)):
        raise ValueError("unclassified numeric token")
    value = Decimal(token)
    if abs(value.as_tuple().exponent) > 300:
        raise ValueError("numeric token outside frozen precision scope")
    return value


def replacement_compatible(token, replacement, half_quantum):
    value = number(token)
    if value is None:
        return False
    # An explicitly hypothesized nearest-last-printed-decimal interval.
    # This is storage compatibility, never a verified rounding or assay rule.
    with localcontext() as context:
        context.prec = 80
        margin = half_quantum.scaleb(value.as_tuple().exponent)
        return value - margin <= replacement <= value + margin


def classify(row, replacement, half_quantum):
    try:
        native = number(row["insulin"])
        zero = number(row["insulin_w0"])
        prepared = number(row["insulin_impute"])
    except ValueError:
        return "unclassified_token"
    if native is None:
        if zero is None and prepared is None:
            return "all_insulin_cells_missing"
        if zero == 0 and replacement_compatible(row["insulin_impute"], replacement, half_quantum):
            return "native_missing_zero_and_replacement_compatible"
        return "native_missing_other_prepared_pattern"
    if zero is None or prepared is None:
        return "native_present_prepared_missing"
    if native == zero == prepared:
        return "native_present_prepared_equal"
    return "native_present_prepared_discrepant"


def diagnostic(rows, replacement, half_quantum):
    counts = Counter(classify(row, replacement, half_quantum) for row in rows)
    return {
        "records": sum(counts.values()),
        "exclusive_pattern_counts": {category: counts[category] for category in CATEGORIES},
        "interpretation": "Prepared-source patterns only; no verified censor flag, assay lineage or clinical use.",
        "clinical_parameters_admitted": False,
    }


def audit_preparation(raw_dir: Path, root: Path, registry: EvidenceRegistry) -> dict:
    protocol_raw = (
        root / "docs/validation/hutelin2026-preparation-pattern-protocol-v1.json"
    ).read_bytes()
    if hashlib.sha256(protocol_raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("preparation protocol differs from frozen scope")
    protocol = json.loads(protocol_raw)
    selected = {
        "parameters": {k: registry.parameters[k].model_dump(mode="json") for k in KEYS},
        "source": registry.sources[protocol["source_id"]].model_dump(mode="json"),
    }
    if (
        hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()
        != protocol["registry_scope_sha256"]
    ):
        raise ValueError("preparation registry definitions differ from frozen scope")
    if any(registry.parameters[k].model_role != "benchmark_only" for k in KEYS):
        raise ValueError("preparation method must remain benchmark-only")
    loq, replacement, half_quantum = (registry.value(key) for key in KEYS)
    if replacement != loq / math.sqrt(2):
        raise ValueError("source replacement formula mismatch")
    # All source/documentary identity checks precede additional value interpretation.
    preflight = audit_hutelin_preflight(
        raw_dir, root / "docs/validation/hutelin2026-preflight-contract-v1.json"
    )
    if preflight["contract_sha256"] != protocol["preflight_contract_sha256"]:
        raise ValueError("preflight scope mismatch")
    source = registry.sources[protocol["source_id"]]
    with (raw_dir / source.raw_filename).open("rb") as stream:
        original_pdf = stream.read(8 * 1024 * 1024 + 1)
    if hashlib.sha256(original_pdf).hexdigest() != source.sha256:
        raise ValueError("source method document mismatch")
    with (raw_dir / "data-original.zip").open("rb") as stream:
        archive_raw = stream.read(protocol["limits"]["archive_bytes"] + 1)
    if hashlib.sha256(archive_raw).hexdigest() != protocol["archive_sha256"]:
        raise ValueError("source data archive mismatch")
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        info = archive.getinfo(protocol["member"])
        if info.file_size > protocol["limits"]["member_bytes"]:
            raise ValueError("selected member size limit")
        member = archive.read(info)
    if hashlib.sha256(member).hexdigest() != protocol["member_sha256"]:
        raise ValueError("selected member identity mismatch")
    if b"\0" in member:
        raise ValueError("selected member framing mismatch")
    reader = csv.reader(io.StringIO(member.decode("utf-8-sig"), newline=""), strict=True)
    if tuple(next(reader, ())) != EXPECTED_HEADER:
        raise ValueError("selected header mismatch")

    def rows():
        for index, cells in enumerate(reader):
            if index >= protocol["limits"]["rows"] or len(cells) != len(EXPECTED_HEADER):
                raise ValueError("selected record framing or count limit")
            if any("\n" in c or "\r" in c for c in cells):
                raise ValueError("selected record must be flat")
            values = dict(zip(EXPECTED_HEADER, cells, strict=True))
            yield {key: values[key] for key in protocol["selected_numeric_fields"]}

    result = diagnostic(rows(), Decimal.from_float(replacement), Decimal.from_float(half_quantum))
    if sum(result["exclusive_pattern_counts"].values()) != result["records"]:
        raise ValueError("preparation pattern accounting mismatch")
    return dict(
        schema_version=1,
        protocol_sha256=PROTOCOL_SHA256,
        registry_scope_sha256=protocol["registry_scope_sha256"],
        archive_sha256=protocol["archive_sha256"],
        member_sha256=protocol["member_sha256"],
        runtime_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        participant_values_exported=False,
        source_rounding_verified=False,
        assay_flags_qualified=False,
        scientific_release_ready=False,
        **result,
    )
