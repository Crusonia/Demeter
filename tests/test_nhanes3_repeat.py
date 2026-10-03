"""Synthetic native-layout checks; never acquire or inspect participant records."""

from copy import deepcopy
from itertools import product
import json

import pytest

from demeter.data import nhanes3_repeat as repeat


DEFINITION = {
    "adult_min_months": 240,
    "age_topcode_months": 1080,
    "fasting_min_hours": 8,
    "fpg_positive_min": 126,
}
PROVENANCE = {
    "protocol_sha256": "a" * 64,
    "source_sha256": dict.fromkeys(("LAB", "ADULT", "LABSE"), "b" * 64),
    "implementation_sha256": {"src/demeter/data/nhanes3_repeat.py": "c" * 64},
}
# Independent native offsets; fixtures deliberately do not import parser layouts.
OFFSETS = {
    "LAB": {
        "SEQN": (1, 5),
        "MXPSESSR": (1234, 1234),
        "MXPAXTMR": (1236, 1239),
        "PHPFAST": (1263, 1267),
        "G1P": (1866, 1870),
    },
    "ADULT": {"SEQN": (1, 5), "HAD1": (1561, 1561)},
    "LABSE": {
        "SEQN": (1, 5),
        "MXRSESSR": (6, 6),
        "MXPRDAYS": (9, 10),
        "PHRFAST": (28, 32),
        "G1R": (595, 599),
    },
}
WIDTHS = {"LAB": (1870, 1977), "ADULT": (1561, 3346), "LABSE": (599, 693)}


def row(component, key, **values):
    defaults = {
        "LAB": {"MXPSESSR": "1", "MXPAXTMR": "240", "PHPFAST": "8", "G1P": "126"},
        "ADULT": {"HAD1": "2"},
        "LABSE": {"MXRSESSR": "3", "MXPRDAYS": "53", "PHRFAST": "8", "G1R": "125"},
    }
    fields = {**defaults[component], "SEQN": str(key), **values}
    result = bytearray(b" " * WIDTHS[component][0])
    for name, value in fields.items():
        start, end = OFFSETS[component][name]
        text = str(value).encode("ascii")
        assert len(text) <= end - start + 1
        result[start - 1 : end] = text.rjust(end - start + 1, b" ")
    return bytes(result)


def frame(pairs, *, newline=b"\n", terminated=True):
    rows = {name: [] for name in OFFSETS}
    for key, (first, second) in enumerate(pairs, start=1):
        rows["LAB"].append(row("LAB", key, G1P=first))
        rows["ADULT"].append(row("ADULT", key))
        rows["LABSE"].append(row("LABSE", key, G1R=second))
    return {
        name: newline.join(values) + (newline if values and terminated else b"")
        for name, values in rows.items()
    }


def analyzed(pairs):
    return repeat.analyze(frame(pairs), DEFINITION)


def public(private):
    return repeat.public_result(private, provenance=PROVENANCE)


@pytest.mark.parametrize("component", OFFSETS)
@pytest.mark.parametrize("newline", [b"\n", b"\r\n", b""])
def test_native_minimum_prefix_and_unterminated_final_record(component, newline):
    content = row(component, 1) + newline
    result = repeat.framing_preflight(component, content)
    assert result["record_count"] == 1
    assert result["selected_values_decoded"] is False
    assert result["terminated_final_record"] == bool(newline)
    # A complete native unselected suffix is accepted without being decoded.
    full = row(component, 1).ljust(WIDTHS[component][1], b" ")
    assert repeat.framing_preflight(component, full)["record_count"] == 1


@pytest.mark.parametrize("component", OFFSETS)
def test_width_refusals_do_not_pad_selected_fields(component):
    for content in (row(component, 1)[:-1], b" " * (WIDTHS[component][1] + 1)):
        with pytest.raises(ValueError, match="width policy"):
            repeat.framing_preflight(component, content)


@pytest.mark.parametrize("damage", [b"\x00", b"\t", b"\x1a", b"\x80", b"\xef\xbb\xbf"])
def test_charset_control_bom_refusal_is_sanitized(damage):
    content = damage + row("LAB", 1)
    with pytest.raises(ValueError, match="charset/control") as error:
        repeat.framing_preflight("LAB", content)
    assert "126" not in str(error.value)


@pytest.mark.parametrize("suffix", [b"\r", b"\n\n", b"\r\n\n"])
def test_bare_cr_internal_blank_mixed_newline_refusal(suffix):
    with pytest.raises(ValueError):
        repeat.framing_preflight("LAB", row("LAB", 1) + suffix)


def test_all_framing_checks_before_any_selected_decoding():
    contents = frame([(126, 125)])
    contents["LAB"] = row("LAB", 1, G1P="oops")
    contents["LABSE"] = b"too short"
    with pytest.raises(ValueError, match="LABSE.*width policy"):
        repeat.analyze(contents, DEFINITION)


def test_empty_frames_are_not_evaluable_not_a_vacuous_pass():
    result = repeat.analyze(dict.fromkeys(OFFSETS, b""), DEFINITION)
    assert result["released_repeat_count"] == 0
    assert result["internal_status"] == "not_evaluable"
    assert public(result)["diagnostic_status"] == "not_evaluable"


@pytest.mark.parametrize(
    "field,token",
    [
        ("G1P", "-1"),
        ("G1P", "1e2"),
        ("G1P", "."),
        ("G1P", ".A"),
        ("G1P", "1,2"),
        ("PHPFAST", "8."),
        ("PHPFAST", "+8"),
        ("MXPAXTMR", "2.4"),
        ("SEQN", ""),
        ("SEQN", "1.0"),
    ],
)
def test_unknown_native_lexeme_refuses_without_printing_value(field, token):
    contents = frame([(126, 125)])
    contents["LAB"] = row("LAB", 1, **{field: token})
    with pytest.raises(ValueError, match="syntax") as error:
        repeat.analyze(contents, DEFINITION)
    assert repr(token) not in str(error.value)


def test_alias_across_components_and_exact_duplicate_refuse():
    contents = frame([(126, 125)])
    contents["ADULT"] = row("ADULT", "00001")
    with pytest.raises(ValueError, match="alias"):
        repeat.analyze(contents, DEFINITION)
    contents = frame([(126, 125)])
    contents["LABSE"] *= 2
    with pytest.raises(ValueError, match="duplicate exact"):
        repeat.analyze(contents, DEFINITION)


def test_consistent_leading_zero_lexeme_links_without_coercion():
    contents = {name: row(name, "00001") for name in OFFSETS}
    result = repeat.analyze(contents, DEFINITION)
    assert result["eligibility_counts"]["eligible"] == 1
    assert "00001" not in json.dumps(result)


def test_extra_primary_rows_outside_repeat_frame_and_physical_weights_are_allowed():
    contents = frame([(126, 125)])
    # Arbitrary printable unselected fields are not interpreted or refused.
    first = bytearray(contents["LAB"])
    first[100:105] = b"1e999"
    contents["LAB"] = bytes(first) + row("LAB", 2) + b"\n"
    contents["ADULT"] += row("ADULT", 2) + b"\n"
    result = repeat.analyze(contents, DEFINITION)
    assert result["released_repeat_count"] == 1
    assert result["eligibility_counts"]["eligible"] == 1


def test_known_false_excludes_despite_unknown_primary_link_or_other_unknown_clause():
    contents = frame([(126, 125)])
    contents["LAB"] = b""
    contents["LABSE"] = row("LABSE", 1, PHRFAST="0")
    result = repeat.analyze(contents, DEFINITION)
    assert result["eligibility_counts"] == {"excluded": 1, "unknown": 0, "eligible": 0}
    assert result["excluded_reason_counts"]["repeat_fasting_at_least8_hours"] == 1
    contents = frame([(126, 125)])
    contents["LAB"] = row("LAB", 1, MXPAXTMR="239", PHPFAST="")
    result = repeat.analyze(contents, DEFINITION)
    assert result["excluded_reason_counts"]["mec_age_at_least240_months"] == 1


def test_clause_coverage_keeps_multiple_unknowns_despite_known_false_exclusion():
    contents = frame([(126, 125)])
    contents["LAB"] = b""
    contents["ADULT"] = row("ADULT", 1, HAD1="9")
    contents["LABSE"] = row("LABSE", 1, PHRFAST="0", MXRSESSR="")
    result = repeat.analyze(contents, DEFINITION)
    assert result["eligibility_counts"] == {"excluded": 1, "unknown": 0, "eligible": 0}
    assert result["clause_coverage"]["repeat_fasting_at_least8_hours"] == {
        "passed": 0,
        "failed": 1,
        "unknown": 0,
    }
    for name in repeat.FALSE_REASONS:
        if name != "repeat_fasting_at_least8_hours":
            assert result["clause_coverage"][name] == {"passed": 0, "failed": 0, "unknown": 1}
    assert "clause_coverage" not in public(result)


def test_overlapping_clause_failures_are_coverage_not_additive_people():
    contents = frame([(126, 125)])
    contents["LAB"] = row("LAB", 1, MXPAXTMR="239", PHPFAST="0")
    contents["ADULT"] = row("ADULT", 1, HAD1="1")
    contents["LABSE"] = row("LABSE", 1, PHRFAST="0")
    result = repeat.analyze(contents, DEFINITION)
    assert result["eligibility_counts"]["excluded"] == 1
    assert sum(result["excluded_reason_counts"].values()) == 1
    assert result["excluded_reason_counts"]["mec_age_at_least240_months"] == 1
    assert sum(counts["failed"] for counts in result["clause_coverage"].values()) == 4
    assert all(sum(counts.values()) == 1 for counts in result["clause_coverage"].values())


def test_corrupt_clause_coverage_cannot_be_publicly_projected():
    result = analyzed([(126, 125)] * 2)
    result["clause_coverage"]["literal_HAD1_equals2"]["unknown"] = 1
    with pytest.raises(ValueError, match="clause coverage conservation"):
        public(result)


@pytest.mark.parametrize("age,eligible,unknown", [("1080", 1, 0), ("1081", 0, 1), ("", 0, 1)])
def test_age_topcode_is_lower_bound_and_above_topcode_is_unknown(age, eligible, unknown):
    contents = frame([(126, 125)])
    contents["LAB"] = row("LAB", 1, MXPAXTMR=age)
    result = repeat.analyze(contents, DEFINITION)
    assert result["eligibility_counts"]["eligible"] == eligible
    assert result["eligibility_counts"]["unknown"] == unknown


@pytest.mark.parametrize(
    "code,role,disposition",
    [
        ("1", "literal_yes", "excluded"),
        ("2", "literal_no", "eligible"),
        ("8", "applicable_blank", "unknown"),
        ("9", "dont_know", "unknown"),
        ("", "blank", "unknown"),
        ("3", "undocumented_code", "unknown"),
    ],
)
def test_literal_history_coding_preserves_unknown_reasons(code, role, disposition):
    contents = frame([(126, 125)])
    contents["ADULT"] = row("ADULT", 1, HAD1=code)
    result = repeat.analyze(contents, DEFINITION)
    assert result["history_code_coverage"][role] == 1
    assert result["eligibility_counts"][disposition] == 1


@pytest.mark.parametrize("token", ["", "88888"])
def test_missing_fasting_is_unknown_and_missing_assay_is_not_negative(token):
    contents = frame([(126, 125)])
    contents["LAB"] = row("LAB", 1, PHPFAST=token)
    assert repeat.analyze(contents, DEFINITION)["eligibility_counts"]["unknown"] == 1
    contents["LAB"] = row("LAB", 1, G1P=token)
    result = repeat.analyze(contents, DEFINITION)
    assert result["eligible_assay_availability"]["repeat_only"] == 1
    assert result["internal_status"] == "not_evaluable"


def test_decimal_measurements_use_no_display_scale_or_observed_range_cap():
    result = analyzed([("126.0", "125.9"), ("99999", "99999"), ("0", "126")])
    assert result["qualifying_pair_label_cells"]["positive_negative"] == 1
    assert result["qualifying_pair_label_cells"]["positive_positive"] == 1
    assert result["eligible_assay_availability"]["repeat_only"] == 1


def test_clock_none_blank_and_above_frequency_range_do_not_change_nominal_eligibility():
    contents = frame([(126, 125)] * 3)
    contents["LABSE"] = b"\n".join(
        row("LABSE", key, MXPRDAYS=clock) for key, clock in enumerate(["00", "", "99"], 1)
    )
    result = repeat.analyze(contents, DEFINITION)
    assert result["qualifying_pair_clock_counts"] == {
        "positive_recorded_exam_days": 1,
        "none_never": 1,
        "unknown": 1,
    }
    assert result["internal_status"] == "contradicted"
    assert result["eligibility_counts"]["eligible"] == 3


def test_unlisted_sessions_remain_unknown_not_guessed_home_or_clock():
    contents = frame([(126, 125)])
    contents["LABSE"] = row("LABSE", 1, MXRSESSR="8")
    result = repeat.analyze(contents, DEFINITION)
    assert result["unknown_reason_counts"]["repeat_context_unknown"] == 1
    assert result["eligible_assay_availability"]["both"] == 0


def test_conservation_of_mixed_links_eligibility_assay_and_clock_ledgers():
    contents = frame([(126, 125), (126, 0), (0, 126), (0, 0), (126, 126)] * 2)
    contents["LAB"] = b"\n".join(
        [
            row("LAB", key, G1P=value)
            for key, value in enumerate([126, 126, 0, 0, 126] * 2, 1)
            if key != 9
        ]
    )
    contents["ADULT"] = b"\n".join(
        row("ADULT", key, HAD1="1" if key == 10 else "2") for key in range(1, 11)
    )
    result = repeat.analyze(contents, DEFINITION)
    assert result["released_repeat_count"] == 10
    assert result["eligibility_counts"] == {"excluded": 1, "unknown": 1, "eligible": 8}
    assert result["eligible_assay_availability"] == {
        "both": 3,
        "primary_only": 2,
        "repeat_only": 2,
        "neither": 1,
    }
    assert result["ledger_conserved"] is True


def test_paired_swap_same_margins_different_persistence():
    a = analyzed([(125, 125)] * 2 + [(126, 126)] * 2)
    b = analyzed([(125, 126)] * 2 + [(126, 125)] * 2)
    assert a["internal_status"] == "not_contradicted_in_observed_pairs"
    assert b["internal_status"] == "contradicted"
    assert public(a)["diagnostic_status"] == a["internal_status"]
    assert public(b)["diagnostic_status"] == b["internal_status"]


def test_no_first_positive_support_not_evaluable_despite_pairs():
    result = analyzed([(125, 125)] * 2 + [(125, 126)] * 2)
    assert result["eligible_assay_availability"]["both"] == 4
    assert public(result)["diagnostic_status"] == "not_evaluable"


def test_exhaustive_small_pair_status_and_release_against_independent_enumeration():
    pairs = [(125, 125), (125, 126), (126, 125), (126, 126)]

    def logical(records):
        if any(a >= 126 and b < 126 for a, b in records):
            return "contradicted"
        if any(a >= 126 for a, b in records):
            return "not_contradicted_in_observed_pairs"
        return "not_evaluable"

    for counts in product(range(3), repeat=4):
        records = [pair for pair, count in zip(pairs, counts, strict=True) for _ in range(count)]
        result = analyzed(records)
        status = logical(records)
        sensitive = (
            len(records) == 1
            or 1 in counts
            or any(logical(records[:i] + records[i + 1 :]) != status for i in range(len(records)))
        )
        assert result["internal_status"] == status
        assert sum(result["qualifying_pair_label_cells"].values()) == len(records)
        assert public(result)["diagnostic_status"] == ("withheld" if sensitive else status)


def test_singleton_eligible_without_pair_withheld_without_private_reason_or_mutation():
    result = analyzed([(0, 0)])
    before = deepcopy(result)
    released = public(result)
    assert released["diagnostic_status"] == "withheld"
    assert result == before
    assert not {"reason", "support", "count", "history_code_coverage"} & set(released)
    assert released["source_audit_passed"] is False
    assert all(value is False for value in released["scientific_gates"].values())


def test_release_is_snapshot_and_reordered_link_map_has_same_semantics():
    result = analyzed([(126, 125)] * 2)
    result["link_coverage"] = dict(reversed(list(result["link_coverage"].items())))
    released = public(result)
    assert released["diagnostic_status"] == "contradicted"
    released["provenance"]["source_sha256"]["LAB"] = "d" * 64
    assert PROVENANCE["source_sha256"]["LAB"] == "b" * 64


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(private_row={"SEQN": "12345"}),
        lambda r: r["qualifying_pair_label_cells"].update(assay_value=120),
        lambda r: r["qualifying_pair_clock_counts"].update(unknown=100),
        lambda r: r["eligibility_counts"].update(eligible=True),
        lambda r: r.update(internal_status="not_evaluable"),
        lambda r: r["history_code_coverage"].update(unlinked=10),
    ],
)
def test_tampered_private_shape_or_conservation_cannot_bypass_projection(mutate):
    result = analyzed([(126, 125)] * 2)
    mutate(result)
    with pytest.raises(ValueError):
        public(result)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(private={"SEQN": "12345"}),
        lambda p: p.update(protocol_sha256={"value": "a" * 64}),
        lambda p: p["source_sha256"].update(SEQN="12345"),
        lambda p: p["implementation_sha256"].update({"C:/private/model.py": "a" * 64}),
        lambda p: p["implementation_sha256"].update({"src/demeter/../private.py": "a" * 64}),
    ],
)
def test_recursive_public_provenance_allowlist_refuses_private_or_path_injection(mutate):
    provenance = deepcopy(PROVENANCE)
    mutate(provenance)
    with pytest.raises(ValueError, match="provenance"):
        repeat.public_result(analyzed([]), provenance=provenance)


def test_optional_admission_and_evidence_fingerprints_are_sha_only():
    provenance = {
        **PROVENANCE,
        "source_admission_sha256": "d" * 64,
        "code_admission_sha256": "e" * 64,
        "evidence_sha256": "f" * 64,
    }
    assert repeat.public_result(analyzed([]), provenance=provenance)["provenance"] == provenance
    provenance["evidence_sha256"] = "private"
    with pytest.raises(ValueError):
        repeat.public_result(analyzed([]), provenance=provenance)


@pytest.mark.parametrize(
    "name,value",
    [
        ("adult_min_months", True),
        ("adult_min_months", 240.0),
        ("adult_min_months", 0),
        ("age_topcode_months", 239),
        ("fasting_min_hours", float("nan")),
        ("fasting_min_hours", float("inf")),
        ("fpg_positive_min", False),
        ("fpg_positive_min", "126"),
        ("fpg_positive_min", -1),
    ],
)
def test_invalid_definitions_refuse_before_data(name, value):
    definition = {**DEFINITION, name: value}
    with pytest.raises(ValueError, match="definition"):
        repeat.analyze(dict.fromkeys(OFFSETS, b""), definition)


def test_exact_input_inventories_and_boolean_source_audit_flag():
    with pytest.raises(ValueError):
        repeat.analyze({"LAB": b""}, DEFINITION)
    with pytest.raises(ValueError):
        repeat.analyze(dict.fromkeys(OFFSETS, b""), {**DEFINITION, "weight": 1})
    with pytest.raises(ValueError):
        repeat.public_result(analyzed([]), provenance=PROVENANCE, source_audit_passed=1)
