"""Frozen, source-specific iPOP structural preflight; no clinical interpretation.

The pure byte API checks both complete source identities before decoding either
file. Acquisition receipts belong to the separate empirical audit wrapper; this
module does not fetch resources, import participant files, or fit a model.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

PROTOCOL_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs/validation/ipop-numerical-preflight-protocol-v1.json"
)
PROTOCOL_SHA256 = "2d8b53ae10a018fde16bc91108db57d49a788f473fc8fc0dfe65a44e28ac2b89"
FROZEN_CANONICAL_SHA256 = "4a3c5621f680d09cf5c8562b4403d934f44d5db6df2624f17c6dddf183e6e2a7"
VALIDATION_TEMPLATE_SHA256 = "d402ec8a026fd70d9030a221a449f874f397db2bb683faa007d1c5f81930cfab"
COMMIT = "ba55996cb51a8bc4fbe9374633e9cb3223c6ea8c"
CLINICAL_HEADER = (
    "VisitID",
    "A1C",
    "AG",
    "ALB",
    "ALCRU",
    "ALKP",
    "ALT",
    "AST",
    "BASO",
    "BASOAB",
    "BUN",
    "CA",
    "CHOL",
    "CHOLHDL",
    "CL",
    "CO2",
    "CR",
    "EGFR",
    "EOS",
    "EOSAB",
    "GLOB",
    "GLU",
    "HCT",
    "HDL",
    "HGB",
    "HSCRP",
    "IGM",
    "INSF",
    "INSU",
    "K",
    "LDL",
    "LDLHDL",
    "LYM",
    "LYMAB",
    "MCH",
    "MCHC",
    "MCV",
    "MONO",
    "MONOAB",
    "NA.",
    "NEUT",
    "NEUTAB",
    "NHDL",
    "PLT",
    "RBC",
    "RDW",
    "TBIL",
    "TGL",
    "TP",
    "UALB",
    "UALBCR",
    "WBC",
    "SubjectID",
    "CollectionDate",
    "CL1",
    "CL2",
    "CL3",
    "CL4",
)
SAMPLE_HEADER = ("SubjectID", "SampleID", "Days_Since_Start", "CL4")
SELECTED = {
    "clinical": ("VisitID", "SubjectID", "A1C", "GLU", "CL4"),
    "sample_info": SAMPLE_HEADER,
}
TOKEN_KINDS = (
    "empty",
    "whitespace_only",
    "finite_decimal",
    "explicit_nonfinite",
    "nonnumeric_or_undocumented_code",
)
KEY_KINDS = ("empty", "whitespace_only", "nonempty")
DAY_KINDS = ("finite", "absent", "nonfinite", "malformed")
ASSOCIATION_KINDS = (
    "missing_clinical_visit_or_subject_key",
    "no_exact_sample_key_match",
    "multiple_sample_rows_for_matching_key",
    "missing_subject_in_unique_sample_match",
    "subject_disagreement_in_unique_sample_match",
    "unique_sample_match_with_subject_agreement",
)
DECIMAL_SYNTAX = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", re.ASCII)
NONFINITE_SYNTAX = re.compile(r"[+-]?(?:nan|inf|infinity)", re.ASCII | re.IGNORECASE)
FAILURE_STAGES = frozenset(
    (
        "frozen_contract",
        "source_identity",
        "source_encoding",
        "source_header",
        "source_structure",
        "numeric_token_representation",
        "aggregate_reconciliation",
        "success_provenance",
    )
)


class _FailedStage(ValueError):
    """Only a constant stage survives into the report; messages never do."""


@dataclass(frozen=True)
class _Number:
    lexical: str
    kind: str
    value: Decimal | None
    surrounding_whitespace: bool


@dataclass(frozen=True)
class _Clinical:
    visit: str
    subject: str
    a1c: _Number
    glu: _Number
    context: str


@dataclass(frozen=True)
class _Sample:
    subject: str
    sample: str
    day: _Number
    context: str


def _unique_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _FailedStage("frozen_contract")
        result[key] = value
    return result


def load_frozen_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Read only the committed contract, rejecting byte or JSON structure drift."""
    try:
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != PROTOCOL_SHA256:
            raise _FailedStage("frozen_contract")
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_json)
        _contract(value, False)
        return value
    except Exception:
        raise _FailedStage("frozen_contract") from None


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _contract(protocol: dict[str, Any], validation_only: bool) -> None:
    if (
        type(validation_only) is not bool
        or type(protocol) is not dict
        or type(protocol.get("schema_version")) is not int
        or protocol["schema_version"] != 1
    ):
        raise _FailedStage("frozen_contract")
    if validation_only:
        template = copy.deepcopy(protocol)
        for role in SELECTED:
            for key in ("git_blob", "tree_size_bytes"):
                template["source_selection"][role].pop(key)
        expected = VALIDATION_TEMPLATE_SHA256
    else:
        template = protocol
        expected = FROZEN_CANONICAL_SHA256
    if _canonical_sha256(template) != expected:
        raise _FailedStage("frozen_contract")
    source = protocol["source_selection"]
    if source["commit"] != COMMIT:
        raise _FailedStage("frozen_contract")
    for role, selected in SELECTED.items():
        if source[role]["selected_columns"] != list(selected):
            raise _FailedStage("frozen_contract")
    if (
        source["clinical"]["path"] != "data/clinical_tests.txt"
        or source["sample_info"]["path"] != "data/SampleInfo.csv"
    ):
        raise _FailedStage("frozen_contract")
    for key in (
        "clinical_threshold_mapping_allowed",
        "clinical_likelihood_or_fit_allowed",
        "biological_transition_rates_allowed",
        "diagnosis_or_remission_inference_allowed",
        "death_or_censoring_inference_allowed",
        "dietary_causal_inference_allowed",
        "national_transport_or_initialization_allowed",
        "engine_activation_allowed",
        "new_numeric_model_parameters",
        "independent_validation",
        "scientific_acceptance_changed",
    ):
        if protocol["fixed_scope_flags"][key] is not False:
            raise _FailedStage("frozen_contract")


def _verify_bytes(data: bytes, pin: dict[str, Any], basename: str) -> dict[str, Any]:
    size = pin["tree_size_bytes"]
    blob = pin["git_blob"]
    if (
        type(data) is not bytes
        or type(size) is not int
        or size < 0
        or not isinstance(blob, str)
        or re.fullmatch(r"[0-9a-f]{40}", blob) is None
    ):
        raise _FailedStage("source_identity")
    if len(data) != size:
        raise _FailedStage("source_identity")
    actual_blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if actual_blob != blob:
        raise _FailedStage("source_identity")
    return {
        "basename": basename,
        "size_bytes": len(data),
        "git_blob": actual_blob,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _key_kind(token: str) -> str:
    if token == "":
        return "empty"
    return "whitespace_only" if token.isspace() else "nonempty"


def _number(token: str) -> _Number:
    kind = _key_kind(token)
    if kind != "nonempty":
        return _Number(token, kind, None, False)
    trimmed = token.strip()
    surrounds = trimmed != token
    if NONFINITE_SYNTAX.fullmatch(trimmed):
        return _Number(token, "explicit_nonfinite", None, surrounds)
    if DECIMAL_SYNTAX.fullmatch(trimmed):
        try:
            value = Decimal(trimmed)
        except (InvalidOperation, ValueError, OverflowError):
            raise _FailedStage("numeric_token_representation") from None
        if not value.is_finite():
            raise _FailedStage("numeric_token_representation")
        return _Number(token, "finite_decimal", value, surrounds)
    return _Number(token, "nonnumeric_or_undocumented_code", None, False)


def _validate_quoting(text: str, delimiter: str) -> None:
    """Reject quote repair accepted by csv.reader; allow legal quoted CR/LF."""
    state = "start"
    for char in text:
        if state == "quoted":
            if char == '"':
                state = "after_quote"
        elif state == "after_quote":
            if char == '"':
                state = "quoted"
            elif char == delimiter or char in "\r\n":
                state = "start"
            else:
                raise _FailedStage("source_structure")
        elif char == delimiter or char in "\r\n":
            state = "start"
        elif char == '"':
            if state != "start":
                raise _FailedStage("source_structure")
            state = "quoted"
        else:
            state = "unquoted"
    if state == "quoted":
        raise _FailedStage("source_structure")


def _records(data: bytes, header: tuple[str, ...], delimiter: str) -> tuple[tuple[str, ...], ...]:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _FailedStage("source_encoding") from None
    if "\0" in text:
        raise _FailedStage("source_structure")
    _validate_quoting(text, delimiter)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        supplied_header = tuple(next(reader))
        if supplied_header != header or len(set(supplied_header)) != len(supplied_header):
            raise _FailedStage("source_header")
        rows: list[tuple[str, ...]] = []
        for raw in reader:
            row = tuple(raw)
            if len(row) != len(header) or row == header:
                raise _FailedStage("source_structure")
            rows.append(row)
        return tuple(rows)
    except StopIteration:
        raise _FailedStage("source_header") from None
    except csv.Error:
        raise _FailedStage("source_structure") from None


def _parse_clinical(rows: tuple[tuple[str, ...], ...]) -> tuple[_Clinical, ...]:
    index = {name: i for i, name in enumerate(CLINICAL_HEADER)}
    return tuple(
        _Clinical(
            row[index["VisitID"]],
            row[index["SubjectID"]],
            _number(row[index["A1C"]]),
            _number(row[index["GLU"]]),
            row[index["CL4"]],
        )
        for row in rows
    )


def _parse_samples(rows: tuple[tuple[str, ...], ...]) -> tuple[_Sample, ...]:
    return tuple(_Sample(row[0], row[1], _number(row[2]), row[3]) for row in rows)


def _support(counter: Counter[Any]) -> dict[str, int]:
    repeated = [n for n in counter.values() if n > 1]
    return {
        "groups_with_multiple_rows": len(repeated),
        "rows_in_repeated_groups": sum(repeated),
        "extra_rows_beyond_one_per_group": sum(n - 1 for n in repeated),
    }


def _key_summary(tokens: tuple[str, ...]) -> dict[str, Any]:
    classes = Counter(_key_kind(token) for token in tokens)
    present = Counter(token for token in tokens if _key_kind(token) == "nonempty")
    return {
        "denominator_rows": len(tokens),
        "token_classes": {kind: classes[kind] for kind in KEY_KINDS},
        "distinct_nonempty_labels": len(present),
        "repeated_key_support": _support(present),
        "leading_or_trailing_whitespace_rows": sum(
            token != token.strip() for token in tokens if _key_kind(token) == "nonempty"
        ),
    }


def _numeric_summary(numbers: tuple[_Number, ...]) -> dict[str, Any]:
    counter = Counter(number.kind for number in numbers)
    return {
        "denominator_rows": len(numbers),
        "token_classes": {kind: counter[kind] for kind in TOKEN_KINDS},
        "numeric_surrounding_whitespace_rows": sum(
            number.surrounding_whitespace for number in numbers
        ),
    }


def _day_kind(number: _Number) -> str:
    return {
        "finite_decimal": "finite",
        "empty": "absent",
        "whitespace_only": "absent",
        "explicit_nonfinite": "nonfinite",
        "nonnumeric_or_undocumented_code": "malformed",
    }[number.kind]


def _context_summary(tokens: tuple[str, ...]) -> dict[str, Any]:
    counter = Counter(_key_kind(token) for token in tokens)
    return {
        "denominator_rows": len(tokens),
        "token_classes": {kind: counter[kind] for kind in KEY_KINDS},
    }


def _summarize(clinical: tuple[_Clinical, ...], samples: tuple[_Sample, ...]) -> dict[str, Any]:
    right: dict[str, list[_Sample]] = defaultdict(list)
    for sample in samples:
        if _key_kind(sample.sample) == "nonempty":
            right[sample.sample].append(sample)
    partition = Counter({kind: 0 for kind in ASSOCIATION_KINDS})
    linked: list[tuple[_Clinical, _Sample]] = []
    for row in clinical:
        if _key_kind(row.visit) != "nonempty" or _key_kind(row.subject) != "nonempty":
            kind = ASSOCIATION_KINDS[0]
        elif not right.get(row.visit):
            kind = ASSOCIATION_KINDS[1]
        elif len(right[row.visit]) != 1:
            kind = ASSOCIATION_KINDS[2]
        else:
            sample = right[row.visit][0]
            if _key_kind(sample.subject) != "nonempty":
                kind = ASSOCIATION_KINDS[3]
            elif row.subject != sample.subject:
                kind = ASSOCIATION_KINDS[4]
            else:
                kind = ASSOCIATION_KINDS[5]
                linked.append((row, sample))
        partition[kind] += 1

    crossings = {
        name: Counter({kind: 0 for kind in DAY_KINDS})
        for name in ("A1C_finite", "GLU_finite", "both_assays_finite")
    }
    subject_clocks: dict[str, dict[str, set[Decimal]]] = {
        name: {} for name in ("A1C", "GLU", "either_finite_assay")
    }
    day_groups: dict[tuple[str, Decimal], list[str]] = defaultdict(list)
    contexts = Counter(
        {
            kind: 0
            for kind in (
                "both_present_exact_equal",
                "both_present_unequal",
                "at_least_one_structurally_absent",
            )
        }
    )
    linked_days = Counter({kind: 0 for kind in DAY_KINDS})
    for row, sample in linked:
        a1c = row.a1c.kind == "finite_decimal"
        glu = row.glu.kind == "finite_decimal"
        day = _day_kind(sample.day)
        linked_days[day] += 1
        for name, selected in (
            ("A1C_finite", a1c),
            ("GLU_finite", glu),
            ("both_assays_finite", a1c and glu),
        ):
            if selected:
                crossings[name][day] += 1
        for name, selected in (("A1C", a1c), ("GLU", glu), ("either_finite_assay", a1c or glu)):
            if selected:
                coordinates = subject_clocks[name].setdefault(row.subject, set())
                if sample.day.value is not None:
                    coordinates.add(sample.day.value)
        if sample.day.value is not None:
            day_groups[(row.subject, sample.day.value)].append(sample.sample)
        if _key_kind(row.context) != "nonempty" or _key_kind(sample.context) != "nonempty":
            contexts["at_least_one_structurally_absent"] += 1
        elif row.context == sample.context:
            contexts["both_present_exact_equal"] += 1
        else:
            contexts["both_present_unequal"] += 1

    clinical_visit_keys = {row.visit for row in clinical if _key_kind(row.visit) == "nonempty"}
    linked_subjects = {row.subject for row, _ in linked}
    subject_categories = {}
    for name, subjects in subject_clocks.items():
        categories = Counter(
            "no_finite_day"
            if not days
            else "one_distinct_finite_day"
            if len(days) == 1
            else "multiple_distinct_finite_days"
            for days in subjects.values()
        )
        subject_categories[name] = {
            "denominator_total_distinct_unambiguous_linked_subject_labels": len(linked_subjects),
            "distinct_linked_subject_labels_with_no_finite_assay": len(linked_subjects)
            - len(subjects),
            "denominator_distinct_linked_subject_labels_with_finite_assay": len(subjects),
            "coordinate_coverage": {
                kind: categories[kind]
                for kind in (
                    "no_finite_day",
                    "one_distinct_finite_day",
                    "multiple_distinct_finite_days",
                )
            },
        }
    clinical_patterns = Counter(
        (row.visit, row.subject, row.a1c.lexical, row.glu.lexical, row.context) for row in clinical
    )
    sample_patterns = Counter(
        (row.subject, row.sample, row.day.lexical, row.context) for row in samples
    )
    result = {
        "source_structure": {
            "clinical": {
                "source_record_count": len(clinical),
                "keys": {
                    "VisitID": _key_summary(tuple(row.visit for row in clinical)),
                    "SubjectID": _key_summary(tuple(row.subject for row in clinical)),
                },
                "repeated_selected_token_patterns": _support(clinical_patterns),
            },
            "sample_info": {
                "source_record_count": len(samples),
                "keys": {
                    "SampleID": _key_summary(tuple(row.sample for row in samples)),
                    "SubjectID": _key_summary(tuple(row.subject for row in samples)),
                },
                "repeated_selected_token_patterns": _support(sample_patterns),
            },
        },
        "numeric_token_coverage": {
            "A1C": _numeric_summary(tuple(row.a1c for row in clinical)),
            "GLU": _numeric_summary(tuple(row.glu for row in clinical)),
            "Days_Since_Start": _numeric_summary(tuple(row.day for row in samples)),
        },
        "linkage": {
            "denominator_clinical_rows": len(clinical),
            "ordered_partition": {kind: partition[kind] for kind in ASSOCIATION_KINDS},
            "right_duplicate_key_support": _support(
                Counter({key: len(rows) for key, rows in right.items()})
            ),
            "sample_rows_without_any_exact_nonempty_clinical_visit_key_match": sum(
                _key_kind(row.sample) != "nonempty" or row.sample not in clinical_visit_keys
                for row in samples
            ),
            "many_to_many_materialization_performed": False,
        },
        "unambiguous_linked_coverage": {
            "denominator_linked_clinical_rows": len(linked),
            "total_distinct_unambiguous_linked_subject_labels": len(linked_subjects),
            "finite_assay_by_day_disposition": {
                name: {kind: counts[kind] for kind in DAY_KINDS}
                for name, counts in crossings.items()
            },
            "distinct_subject_label_coordinate_coverage": subject_categories,
            "sample_day_disposition_all_linked_rows": {
                kind: linked_days[kind] for kind in DAY_KINDS
            },
            "denominator_linked_rows_with_finite_day": linked_days["finite"],
            "same_subject_equal_finite_day_support": _support(
                Counter({key: len(rows) for key, rows in day_groups.items()})
            ),
            "subjects_with_multiple_sample_labels_at_an_equal_finite_day": len(
                {subject for (subject, _), rows in day_groups.items() if len(set(rows)) > 1}
            ),
            "repeated_unique_sample_association_support": _support(
                Counter(sample.sample for _, sample in linked)
            ),
            "unambiguous_repeated_coordinate_coverage_present": any(
                len(days) > 1 for days in subject_clocks["either_finite_assay"].values()
            ),
        },
        "context_coverage": {
            "clinical_CL4": _context_summary(tuple(row.context for row in clinical)),
            "sample_info_CL4": _context_summary(tuple(row.context for row in samples)),
            "linked_context_comparison": {
                "denominator_linked_rows": len(linked),
                "partition": dict(contexts),
            },
        },
    }
    _reconcile(result)
    return result


def _reconcile(result: dict[str, Any]) -> None:
    if set(result) != {
        "source_structure",
        "numeric_token_coverage",
        "linkage",
        "unambiguous_linked_coverage",
        "context_coverage",
    }:
        raise _FailedStage("aggregate_reconciliation")

    def integer(value: Any) -> int:
        if type(value) is not int or value < 0:
            raise _FailedStage("aggregate_reconciliation")
        return value

    def partition(value: dict[str, Any], keys: tuple[str, ...]) -> int:
        if set(value) != set(keys):
            raise _FailedStage("aggregate_reconciliation")
        return sum(integer(value[key]) for key in keys)

    def support(value: dict[str, Any], denominator: int) -> None:
        groups = integer(value["groups_with_multiple_rows"])
        rows = integer(value["rows_in_repeated_groups"])
        extra = integer(value["extra_rows_beyond_one_per_group"])
        if (
            not 2 * groups <= rows <= denominator
            or extra != rows - groups
            or (groups == 0) != (rows == 0)
        ):
            raise _FailedStage("aggregate_reconciliation")

    structures = result["source_structure"]
    for source in structures.values():
        n = integer(source["source_record_count"])
        support(source["repeated_selected_token_patterns"], n)
        for summary in source["keys"].values():
            present = integer(summary["token_classes"]["nonempty"])
            distinct = integer(summary["distinct_nonempty_labels"])
            support(summary["repeated_key_support"], present)
            if (
                integer(summary["denominator_rows"]) != n
                or partition(summary["token_classes"], KEY_KINDS) != n
                or distinct
                != present - summary["repeated_key_support"]["extra_rows_beyond_one_per_group"]
                or not 0 <= integer(summary["leading_or_trailing_whitespace_rows"]) <= present
            ):
                raise _FailedStage("aggregate_reconciliation")
    clinical_n = structures["clinical"]["source_record_count"]
    sample_n = structures["sample_info"]["source_record_count"]
    for field, expected_n in (
        ("A1C", clinical_n),
        ("GLU", clinical_n),
        ("Days_Since_Start", sample_n),
    ):
        summary = result["numeric_token_coverage"][field]
        if (
            integer(summary["denominator_rows"]) != expected_n
            or partition(summary["token_classes"], TOKEN_KINDS) != expected_n
            or not 0
            <= integer(summary["numeric_surrounding_whitespace_rows"])
            <= summary["token_classes"]["finite_decimal"]
            + summary["token_classes"]["explicit_nonfinite"]
        ):
            raise _FailedStage("aggregate_reconciliation")
    linkage = result["linkage"]
    linked = result["unambiguous_linked_coverage"]
    n = integer(linked["denominator_linked_clinical_rows"])
    total_subjects = integer(linked["total_distinct_unambiguous_linked_subject_labels"])
    if (
        integer(linkage["denominator_clinical_rows"]) != clinical_n
        or partition(linkage["ordered_partition"], ASSOCIATION_KINDS) != clinical_n
        or linkage["ordered_partition"][ASSOCIATION_KINDS[5]] != n
        or not total_subjects
        <= min(
            n,
            structures["clinical"]["keys"]["SubjectID"]["distinct_nonempty_labels"],
            structures["sample_info"]["keys"]["SubjectID"]["distinct_nonempty_labels"],
        )
        or linkage["many_to_many_materialization_performed"] is not False
    ):
        raise _FailedStage("aggregate_reconciliation")
    support(linkage["right_duplicate_key_support"], sample_n)
    sample_keys = structures["sample_info"]["keys"]["SampleID"]
    unused = integer(linkage["sample_rows_without_any_exact_nonempty_clinical_visit_key_match"])
    if (
        linkage["right_duplicate_key_support"] != sample_keys["repeated_key_support"]
        or not sample_keys["token_classes"]["empty"]
        + sample_keys["token_classes"]["whitespace_only"]
        <= unused
        <= sample_n
    ):
        raise _FailedStage("aggregate_reconciliation")
    days = linked["sample_day_disposition_all_linked_rows"]
    if (
        partition(days, DAY_KINDS) != n
        or integer(linked["denominator_linked_rows_with_finite_day"]) != days["finite"]
    ):
        raise _FailedStage("aggregate_reconciliation")
    crossings = linked["finite_assay_by_day_disposition"]
    for counts in crossings.values():
        partition(counts, DAY_KINDS)
    for kind in DAY_KINDS:
        a1c = crossings["A1C_finite"][kind]
        glu = crossings["GLU_finite"][kind]
        both = crossings["both_assays_finite"][kind]
        if not both <= min(a1c, glu) or a1c + glu - both > days[kind]:
            raise _FailedStage("aggregate_reconciliation")
    for coverage in linked["distinct_subject_label_coordinate_coverage"].values():
        eligible = integer(coverage["denominator_distinct_linked_subject_labels_with_finite_assay"])
        absent = integer(coverage["distinct_linked_subject_labels_with_no_finite_assay"])
        if (
            integer(coverage["denominator_total_distinct_unambiguous_linked_subject_labels"])
            != total_subjects
            or absent + eligible != total_subjects
            or partition(
                coverage["coordinate_coverage"],
                ("no_finite_day", "one_distinct_finite_day", "multiple_distinct_finite_days"),
            )
            != eligible
        ):
            raise _FailedStage("aggregate_reconciliation")
    subjects = linked["distinct_subject_label_coordinate_coverage"]
    a1c_subjects = subjects["A1C"]["denominator_distinct_linked_subject_labels_with_finite_assay"]
    glu_subjects = subjects["GLU"]["denominator_distinct_linked_subject_labels_with_finite_assay"]
    either_subjects = subjects["either_finite_assay"][
        "denominator_distinct_linked_subject_labels_with_finite_assay"
    ]
    if (
        not max(a1c_subjects, glu_subjects)
        <= either_subjects
        <= min(total_subjects, a1c_subjects + glu_subjects)
    ):
        raise _FailedStage("aggregate_reconciliation")
    support(linked["same_subject_equal_finite_day_support"], days["finite"])
    support(linked["repeated_unique_sample_association_support"], n)
    if integer(linked["subjects_with_multiple_sample_labels_at_an_equal_finite_day"]) > min(
        total_subjects, linked["same_subject_equal_finite_day_support"]["groups_with_multiple_rows"]
    ):
        raise _FailedStage("aggregate_reconciliation")
    repeated = (
        subjects["either_finite_assay"]["coordinate_coverage"]["multiple_distinct_finite_days"] > 0
    )
    if linked["unambiguous_repeated_coordinate_coverage_present"] is not repeated:
        raise _FailedStage("aggregate_reconciliation")
    context_linked = result["context_coverage"]["linked_context_comparison"]
    if (
        integer(context_linked["denominator_linked_rows"]) != n
        or partition(
            context_linked["partition"],
            (
                "both_present_exact_equal",
                "both_present_unequal",
                "at_least_one_structurally_absent",
            ),
        )
        != n
    ):
        raise _FailedStage("aggregate_reconciliation")
    for role, field in (("clinical", "clinical_CL4"), ("sample_info", "sample_info_CL4")):
        context = result["context_coverage"][field]
        if (
            integer(context["denominator_rows"]) != structures[role]["source_record_count"]
            or partition(context["token_classes"], KEY_KINDS) != context["denominator_rows"]
        ):
            raise _FailedStage("aggregate_reconciliation")

    def counts_are_safe(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                counts_are_safe(child)
        elif type(value) is int:
            if value < 0:
                raise _FailedStage("aggregate_reconciliation")
        elif type(value) is not bool:
            raise _FailedStage("aggregate_reconciliation")

    counts_are_safe(result)


def preflight_bytes(
    clinical_bytes: bytes,
    sample_bytes: bytes,
    *,
    protocol: dict[str, Any],
    validation_only: bool = True,
) -> dict[str, Any]:
    """Return structural aggregates for frozen source bytes or labeled fixtures.

    This API never opens source/output files, fetches resources, or exposes rows.
    It verifies no acquisition receipt or clinical observation assumption. The
    empirical wrapper must verify those receipts before calling this pure core.
    """
    execution_scope = (
        "synthetic_software_validation_only"
        if validation_only is True
        else "actual_source_intake_only"
        if validation_only is False
        else "invalid_execution_mode"
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "execution_scope": execution_scope,
        "validation_only": validation_only if type(validation_only) is bool else None,
        "source_audit": {
            "passed": False,
            "failure_stage": None,
            "frozen_protocol_sha256": PROTOCOL_SHA256,
        },
        "source_structure": None,
        "numeric_token_coverage": None,
        "linkage": None,
        "unambiguous_linked_coverage": None,
        "context_coverage": None,
        "provenance": None,
        "clinical_fit_performed": False,
        "clinical_threshold_mapping_performed": False,
        "diagnosis_or_remission_inference_performed": False,
        "death_or_censoring_inference_performed": False,
        "engine_activation_allowed": False,
        "scientific_acceptance_changed": False,
    }
    stage = "frozen_contract"
    try:
        _contract(protocol, validation_only)
        stage = "source_identity"
        source = protocol["source_selection"]
        # Both identities precede even UTF-8 decoding of either source.
        pins = {
            "clinical": _verify_bytes(clinical_bytes, source["clinical"], "clinical_tests.txt"),
            "sample_info": _verify_bytes(sample_bytes, source["sample_info"], "SampleInfo.csv"),
        }
        stage = "source_structure"
        clinical_records = _records(clinical_bytes, CLINICAL_HEADER, "\t")
        sample_records = _records(sample_bytes, SAMPLE_HEADER, ",")
        stage = "numeric_token_representation"
        clinical = _parse_clinical(clinical_records)
        samples = _parse_samples(sample_records)
        stage = "aggregate_reconciliation"
        results = _summarize(clinical, samples)
        stage = "success_provenance"
        provenance = {
            "frozen_protocol_sha256": PROTOCOL_SHA256,
            "supplied_protocol_canonical_sha256": _canonical_sha256(protocol),
            "validation_semantics_sha256": VALIDATION_TEMPLATE_SHA256,
            "producer_commit": COMMIT,
            "source_bytes": pins,
            "acquisition_performed": False,
            "acquisition_receipts_verified": False,
            "verification_scope": (
                "synthetic in-memory byte identity and selected structural preservation only"
                if validation_only
                else "complete frozen-source byte identity and selected structural preservation only"
            ),
            "numeric_surrounding_whitespace_rule": "strip surrounding Unicode whitespace for ASCII numeric syntax classification only; retain original lexical token",
            "decimal_equality": "exact Decimal equality; no float tolerance or chronology inferred from row order",
            "expected_headers": {
                "clinical": list(CLINICAL_HEADER),
                "sample_info": list(SAMPLE_HEADER),
            },
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "units_rawness_and_specimen_clock_verified": False,
            "sampling_model_selected": False,
        }
        success = dict(report)
        success.update(results)
        success["source_audit"] = {
            "passed": True,
            "failure_stage": None,
            "frozen_protocol_sha256": PROTOCOL_SHA256,
            "meaning": (
                "synthetic source integrity, structure and aggregate preservation checks only"
                if validation_only
                else "frozen source integrity, structure and aggregate preservation checks only"
            ),
        }
        success["provenance"] = provenance
        json.dumps(success, allow_nan=False)  # Finish metadata before atomic publication.
        return success
    except Exception as exc:
        reason = str(exc) if isinstance(exc, _FailedStage) else stage
        report["source_audit"]["failure_stage"] = reason if reason in FAILURE_STAGES else stage
        return report
