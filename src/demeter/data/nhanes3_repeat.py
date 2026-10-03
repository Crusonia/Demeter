"""Pure, validation-only NHANES III nominal repeat-FPG diagnostic.

This module acquires nothing and verifies no empirical source/code admission.
An admitted caller must do that before supplying actual bytes. Only selected
native fields are decoded; rows, keys and measurements are never returned.
Private aggregate ledgers must not be published. ``public_result`` is the sole
coarse release projection. No elapsed-time, survey or clinical model is fitted.
"""

from collections.abc import Mapping
from decimal import Decimal
from io import BytesIO
import math
import re

LAYOUTS = {
    "LAB": {
        "minimum": 1870,
        "maximum": 1977,
        "fields": {
            "SEQN": (1, 5),
            "MXPSESSR": (1234, 1234),
            "MXPAXTMR": (1236, 1239),
            "PHPFAST": (1263, 1267),
            "G1P": (1866, 1870),
        },
    },
    "ADULT": {
        "minimum": 1561,
        "maximum": 3346,
        "fields": {"SEQN": (1, 5), "HAD1": (1561, 1561)},
    },
    "LABSE": {
        "minimum": 599,
        "maximum": 693,
        "fields": {
            "SEQN": (1, 5),
            "MXRSESSR": (6, 6),
            "MXPRDAYS": (9, 10),
            "PHRFAST": (28, 32),
            "G1R": (595, 599),
        },
    },
}
GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
FALSE_REASONS = (
    "mec_age_at_least240_months",
    "literal_HAD1_equals2",
    "primary_fasting_at_least8_hours",
    "repeat_fasting_at_least8_hours",
    "primary_context_session_in123",
    "repeat_context_session_in123",
)
UNKNOWN_REASONS = (
    "primary_link_unavailable",
    "adult_link_unavailable",
    "mec_age_unknown",
    "HAD1_unknown",
    "primary_fasting_unknown",
    "repeat_fasting_unknown",
    "primary_context_unknown",
    "repeat_context_unknown",
)
CELLS = ("negative_negative", "negative_positive", "positive_negative", "positive_positive")
CLOCKS = ("positive_recorded_exam_days", "none_never", "unknown")
AVAILABILITY = ("both", "primary_only", "repeat_only", "neither")
HISTORY_CODES = (
    "literal_yes",
    "literal_no",
    "applicable_blank",
    "dont_know",
    "blank",
    "undocumented_code",
    "unlinked",
)
_DEFINITION = {"adult_min_months", "age_topcode_months", "fasting_min_hours", "fpg_positive_min"}
_INTEGER = re.compile(r"[0-9]+\Z")
_DECIMAL = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MODULE = re.compile(r"src/demeter/(?:[A-Za-z_][A-Za-z_0-9]*/)*[A-Za-z_][A-Za-z_0-9]*\.py\Z")


def _lines(content: bytes):
    for line in BytesIO(content):
        if line.endswith(b"\r\n"):
            yield line[:-2]
        elif line.endswith(b"\n"):
            yield line[:-1]
        else:
            yield line


def framing_preflight(component: str, content: bytes) -> dict:
    """Check framing only, without selected-field decoding or value-bearing errors.

    Empty bytes define an empty synthetic frame. Uniform LF or CRLF and a valid
    unterminated final record are allowed. The selected prefix may omit only an
    unselected tail, an explicit adapter policy rather than a SAS requirement.
    """
    if component not in LAYOUTS or not isinstance(content, bytes):
        raise ValueError("repeat source requires a known component and immutable bytes")
    if content.translate(None, bytes(range(32, 127)) + b"\r\n"):
        raise ValueError(f"{component} unsupported source charset/control framing")
    crlf = content.count(b"\r\n")
    lf = content.count(b"\n")
    if content.count(b"\r") != crlf or (crlf and crlf != lf):
        raise ValueError(f"{component} unsupported source newline framing")
    count = 0
    layout = LAYOUTS[component]
    for line in _lines(content):
        if not layout["minimum"] <= len(line) <= layout["maximum"]:
            raise ValueError(f"{component} source record outside selected-prefix width policy")
        count += 1
    return {
        "component": component,
        "record_count": count,
        "encoding": "ASCII",
        "line_endings": "CRLF" if crlf else "LF" if lf else "none",
        "terminated_final_record": bool(content and content.endswith(b"\n")),
        "selected_values_decoded": False,
    }


def _definition(definition: Mapping) -> dict:
    if not isinstance(definition, Mapping) or set(definition) != _DEFINITION:
        raise ValueError("repeat definition requires exactly four declared numeric definitions")
    result = dict(definition)
    for name in ("adult_min_months", "age_topcode_months"):
        if type(result[name]) is not int or result[name] <= 0:
            raise ValueError("repeat age definitions must be positive Python integers")
    if result["adult_min_months"] > result["age_topcode_months"]:
        raise ValueError("repeat adult definition exceeds source topcode lower bound")
    for name in ("fasting_min_hours", "fpg_positive_min"):
        value = result[name]
        if (
            type(value) not in (int, float)
            or value <= 0
            or (type(value) is float and not math.isfinite(value))
        ):
            raise ValueError("repeat threshold definitions must be finite positive numbers")
        result[name] = Decimal(str(value))
    return result


def _integer(token: str, field: str, *, blank_allowed: bool = True) -> int | None:
    if not token and blank_allowed:
        return None
    if not _INTEGER.fullmatch(token):
        raise ValueError(f"repeat unsupported integer syntax in {field}")
    return int(token)


def _decimal(token: str, field: str) -> Decimal | None:
    if token in ("", "88888"):
        return None
    if not _DECIMAL.fullmatch(token):
        raise ValueError(f"repeat unsupported decimal syntax in {field}")
    return Decimal(token)


def _selected(component: str, content: bytes, aliases: dict) -> dict:
    selected = {}
    for line in _lines(content):
        fields = {
            name: line[start - 1 : end].decode("ascii").strip(" ")
            for name, (start, end) in LAYOUTS[component]["fields"].items()
        }
        key = fields.pop("SEQN")
        numeric_key = _integer(key, "SEQN", blank_allowed=False)
        if key in selected:
            raise ValueError(f"{component} duplicate exact source key")
        if numeric_key in aliases and aliases[numeric_key] != key:
            raise ValueError("repeat unresolved numeric-looking source key alias")
        aliases[numeric_key] = key
        row = {}
        for field, token in fields.items():
            row[field] = (
                _decimal(token, field)
                if field in {"G1P", "G1R", "PHPFAST", "PHRFAST"}
                else _integer(token, field)
            )
        selected[key] = row
    return selected


def _status(cells: Mapping) -> str:
    if cells["positive_negative"]:
        return "contradicted"
    if cells["positive_positive"]:
        return "not_contradicted_in_observed_pairs"
    return "not_evaluable"


def analyze(contents: Mapping[str, bytes], definition: Mapping) -> dict:
    """Return a private finite-frame aggregate, never source rows or identifiers.

    Every component is framing-checked before any selected value is decoded.
    Missingness remains unknown; any known failed clause takes precedence. Clock
    coverage partitions qualifying pairs but never changes nominal eligibility.
    Actual empirical inputs require the caller's independent admission guard.
    """
    if not isinstance(contents, Mapping) or set(contents) != set(LAYOUTS):
        raise ValueError("repeat sources require exactly LAB, ADULT and LABSE")
    config = _definition(definition)
    for component in LAYOUTS:
        framing_preflight(component, contents[component])
    aliases = {}
    selected = {
        component: _selected(component, contents[component], aliases) for component in LAYOUTS
    }
    result = {
        "kind": "nhanes3_repeat_private_aggregate",
        "released_repeat_count": len(selected["LABSE"]),
        "eligibility_counts": dict.fromkeys(("excluded", "unknown", "eligible"), 0),
        "excluded_reason_counts": dict.fromkeys(FALSE_REASONS, 0),
        "unknown_reason_counts": dict.fromkeys(UNKNOWN_REASONS, 0),
        "link_coverage": dict.fromkeys(
            ("primary_link_available", "adult_link_available", "both_links_available"), 0
        ),
        "eligible_assay_availability": dict.fromkeys(AVAILABILITY, 0),
        "qualifying_pair_label_cells": dict.fromkeys(CELLS, 0),
        "qualifying_pair_clock_counts": dict.fromkeys(CLOCKS, 0),
        "history_code_coverage": dict.fromkeys(HISTORY_CODES, 0),
        "clause_coverage": {
            clause: dict.fromkeys(("passed", "failed", "unknown"), 0) for clause in FALSE_REASONS
        },
    }
    for key, repeat in selected["LABSE"].items():
        primary = selected["LAB"].get(key)
        adult = selected["ADULT"].get(key)
        coverage = result["link_coverage"]
        coverage["primary_link_available"] += primary is not None
        coverage["adult_link_available"] += adult is not None
        coverage["both_links_available"] += primary is not None and adult is not None
        age = primary["MXPAXTMR"] if primary else None
        if age is not None and age > config["age_topcode_months"]:
            age = None
        history = adult["HAD1"] if adult else None
        history_role = (
            "unlinked"
            if adult is None
            else {
                1: "literal_yes",
                2: "literal_no",
                8: "applicable_blank",
                9: "dont_know",
                None: "blank",
            }.get(history, "undocumented_code")
        )
        result["history_code_coverage"][history_role] += 1
        fast_p = primary["PHPFAST"] if primary else None
        fast_r = repeat["PHRFAST"]
        session_p = primary["MXPSESSR"] if primary else None
        session_r = repeat["MXRSESSR"]
        clauses = (
            None if age is None else age >= config["adult_min_months"],
            None if history not in (1, 2) else history == 2,
            None if fast_p is None else fast_p >= config["fasting_min_hours"],
            None if fast_r is None else fast_r >= config["fasting_min_hours"],
            True if session_p in (1, 2, 3) else None,
            True if session_r in (1, 2, 3) else None,
        )
        for name, state in zip(FALSE_REASONS, clauses, strict=True):
            role = "unknown" if state is None else "passed" if state else "failed"
            result["clause_coverage"][name][role] += 1
        if False in clauses:
            result["eligibility_counts"]["excluded"] += 1
            result["excluded_reason_counts"][FALSE_REASONS[clauses.index(False)]] += 1
            continue
        unknowns = (
            primary is None,
            adult is None,
            age is None,
            history not in (1, 2),
            fast_p is None,
            fast_r is None,
            session_p not in (1, 2, 3),
            session_r not in (1, 2, 3),
        )
        if any(unknowns):
            result["eligibility_counts"]["unknown"] += 1
            result["unknown_reason_counts"][UNKNOWN_REASONS[unknowns.index(True)]] += 1
            continue
        result["eligibility_counts"]["eligible"] += 1
        assay_p = primary["G1P"]
        assay_r = repeat["G1R"]
        valid_p = assay_p is not None and assay_p > 0
        valid_r = assay_r is not None and assay_r > 0
        availability = (
            "both"
            if valid_p and valid_r
            else "primary_only"
            if valid_p
            else "repeat_only"
            if valid_r
            else "neither"
        )
        result["eligible_assay_availability"][availability] += 1
        if not (valid_p and valid_r):
            continue
        labels = (
            "positive" if assay_p >= config["fpg_positive_min"] else "negative",
            "positive" if assay_r >= config["fpg_positive_min"] else "negative",
        )
        result["qualifying_pair_label_cells"]["_".join(labels)] += 1
        clock = repeat["MXPRDAYS"]
        clock_role = "unknown" if clock is None else "none_never" if clock == 0 else CLOCKS[0]
        result["qualifying_pair_clock_counts"][clock_role] += 1
    result["internal_status"] = _status(result["qualifying_pair_label_cells"])
    result["ledger_conserved"] = True
    _verify_private(result)
    return result


def _counts(value, keys) -> dict:
    if (
        not isinstance(value, dict)
        or set(value) != set(keys)
        or any(type(count) is not int or count < 0 for count in value.values())
    ):
        raise ValueError("repeat private aggregate count shape invalid")
    return value


def _verify_private(private: dict) -> None:
    expected = {
        "kind",
        "released_repeat_count",
        "eligibility_counts",
        "excluded_reason_counts",
        "unknown_reason_counts",
        "link_coverage",
        "eligible_assay_availability",
        "qualifying_pair_label_cells",
        "qualifying_pair_clock_counts",
        "internal_status",
        "ledger_conserved",
        "history_code_coverage",
        "clause_coverage",
    }
    if not isinstance(private, dict) or set(private) != expected:
        raise ValueError("repeat private aggregate shape invalid")
    n = private["released_repeat_count"]
    if type(n) is not int or n < 0 or private["kind"] != "nhanes3_repeat_private_aggregate":
        raise ValueError("repeat private finite-frame identity invalid")
    eligibility = _counts(private["eligibility_counts"], ("excluded", "unknown", "eligible"))
    excluded = _counts(private["excluded_reason_counts"], FALSE_REASONS)
    unknown = _counts(private["unknown_reason_counts"], UNKNOWN_REASONS)
    availability = _counts(private["eligible_assay_availability"], AVAILABILITY)
    cells = _counts(private["qualifying_pair_label_cells"], CELLS)
    clocks = _counts(private["qualifying_pair_clock_counts"], CLOCKS)
    links = _counts(
        private["link_coverage"],
        ("primary_link_available", "adult_link_available", "both_links_available"),
    )
    history = _counts(private["history_code_coverage"], HISTORY_CODES)
    coverage = private["clause_coverage"]
    if not isinstance(coverage, dict) or set(coverage) != set(FALSE_REASONS):
        raise ValueError("repeat private clause coverage shape invalid")
    for name in FALSE_REASONS:
        counts = _counts(coverage[name], ("passed", "failed", "unknown"))
        if sum(counts.values()) != n:
            raise ValueError("repeat private clause coverage conservation invalid")
    p = links["primary_link_available"]
    a = links["adult_link_available"]
    both = links["both_links_available"]
    if (
        sum(eligibility.values()) != n
        or sum(excluded.values()) != eligibility["excluded"]
        or sum(unknown.values()) != eligibility["unknown"]
        or sum(availability.values()) != eligibility["eligible"]
        or sum(cells.values()) != availability["both"]
        or sum(clocks.values()) != availability["both"]
        or sum(history.values()) != n
        or history["unlinked"] != n - a
        or not max(0, p + a - n) <= both <= min(p, a) <= n
        or eligibility["eligible"] > both
        or private["ledger_conserved"] is not True
        or private["internal_status"] != _status(cells)
    ):
        raise ValueError("repeat private aggregate conservation/status invalid")


def _provenance(provenance: Mapping) -> dict:
    required = {"protocol_sha256", "source_sha256", "implementation_sha256"}
    optional = {"source_admission_sha256", "code_admission_sha256", "evidence_sha256"}
    if (
        not isinstance(provenance, Mapping)
        or not required <= set(provenance)
        or not set(provenance) <= required | optional
    ):
        raise ValueError("repeat public provenance shape invalid")
    for name in {"protocol_sha256"} | (optional & set(provenance)):
        if not isinstance(provenance[name], str) or not _SHA.fullmatch(provenance[name]):
            raise ValueError("repeat public provenance checksum invalid")
    sources = provenance["source_sha256"]
    code = provenance["implementation_sha256"]
    if (
        not isinstance(sources, Mapping)
        or set(sources) != set(LAYOUTS)
        or not isinstance(code, Mapping)
        or not code
        or any(not isinstance(k, str) or not _MODULE.fullmatch(k) for k in code)
        or any(
            not isinstance(v, str) or not _SHA.fullmatch(v)
            for v in (*sources.values(), *code.values())
        )
    ):
        raise ValueError("repeat public source/code provenance invalid")
    return {**provenance, "source_sha256": dict(sources), "implementation_sha256": dict(code)}


def public_result(private: dict, *, provenance: Mapping, source_audit_passed: bool = False) -> dict:
    """Project a validated private ledger to the fixed coarse release schema.

    Singleton and delete-one checks concern unredacted internal status. They do
    not trim the finite cohort, assume sampling, or provide differential privacy.
    Admission is the caller's responsibility; this flag is not an audit itself.
    """
    if type(source_audit_passed) is not bool:
        raise ValueError("repeat source audit flag must be a Boolean")
    _verify_private(private)
    identity = _provenance(provenance)
    cells = private["qualifying_pair_label_cells"]
    status = private["internal_status"]
    sensitive = private["eligibility_counts"]["eligible"] == 1 or 1 in cells.values()
    for name, count in cells.items():
        if count:
            reduced = dict(cells)
            reduced[name] -= 1
            sensitive |= _status(reduced) != status
    return {
        "kind": "nhanes3_repeat_fpg_nominal_diagnostic",
        "schema_version": 1,
        "source_vintage": "NHANES III 1988-1994; revised primary1A and repeat3A ASCII",
        "model_role": "benchmark_only",
        "validation_only": True,
        "source_audit_passed": source_audit_passed,
        "scientific_gates": dict.fromkeys(GATES, False),
        "diagnostic_status": "withheld" if sensitive else status,
        "ledger_conserved": True,
        "provenance": identity,
    }
