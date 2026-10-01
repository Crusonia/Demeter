"""Synthetic validation-only fixtures; no real participant files are opened."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from demeter.analysis import ipop_preflight as candidate

PROTOCOL = candidate.load_frozen_protocol()

SECTIONS = (
    "source_structure",
    "numeric_token_coverage",
    "linkage",
    "unambiguous_linked_coverage",
    "context_coverage",
    "provenance",
)
PRIVATE = "PRIVATE_SYNTHETIC_MARKER"


def _encode(header, rows, delimiter, line="\r\n"):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator=line)
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _clinical_rows(specs):
    rows = []
    for i, spec in enumerate(specs):
        # Excluded fields differ even for identical selected patterns.
        raw = {name: f"{PRIVATE}_EXCLUDED_{i}" for name in candidate.CLINICAL_HEADER}
        raw.update(spec)
        rows.append([raw[name] for name in candidate.CLINICAL_HEADER])
    return rows


def _pin(data):
    return {
        "git_blob": hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest(),
        "tree_size_bytes": len(data),
    }


def _protocol(clinical, samples):
    p = copy.deepcopy(PROTOCOL)
    for role, data in (("clinical", clinical), ("sample_info", samples)):
        p["source_selection"][role].update(_pin(data))
    return p


def _audit(clinical, samples, **kwargs):
    return candidate.preflight_bytes(
        clinical, samples, protocol=_protocol(clinical, samples), **kwargs
    )


def _good_bytes():
    clinical_specs = [
        {
            "VisitID": "VISIT_A",
            "SubjectID": PRIVATE + "_SUBJECT",
            "A1C": "1",
            "GLU": "2",
            "CL4": PRIVATE + "_CONTEXT",
        },
        {
            "VisitID": "VISIT_A",
            "SubjectID": PRIVATE + "_SUBJECT",
            "A1C": "1",
            "GLU": "2",
            "CL4": PRIVATE + "_CONTEXT",
        },
        {
            "VisitID": "VISIT_B",
            "SubjectID": PRIVATE + "_SUBJECT",
            "A1C": " 1.00 ",
            "GLU": "",
            "CL4": "",
        },
        {
            "VisitID": "VISIT_C",
            "SubjectID": PRIVATE + "_SUBJECT",
            "A1C": "NA",
            "GLU": "3",
            "CL4": PRIVATE + "_CONTEXT",
        },
        {
            "VisitID": "VISIT_D",
            "SubjectID": PRIVATE + "_NO_DAY",
            "A1C": "0",
            "GLU": "-1",
            "CL4": PRIVATE + "_CONTEXT",
        },
        {
            "VisitID": "UNMATCHED_PRIVATE_VISIT",
            "SubjectID": PRIVATE,
            "A1C": PRIVATE + "_CODE",
            "GLU": "null",
            "CL4": PRIVATE,
        },
        {"VisitID": "", "SubjectID": PRIVATE, "A1C": " ", "GLU": "", "CL4": PRIVATE},
        {"VisitID": " ", "SubjectID": " ", "A1C": "True", "GLU": "1_0", "CL4": " "},
        {"VisitID": "VISIT_E", "SubjectID": PRIVATE, "A1C": "1", "GLU": "2", "CL4": PRIVATE},
        {"VisitID": "VISIT_F", "SubjectID": PRIVATE, "A1C": "1", "GLU": "2", "CL4": PRIVATE},
        {"VisitID": "VISIT_G", "SubjectID": PRIVATE, "A1C": "1", "GLU": "2", "CL4": PRIVATE},
        {"VisitID": " VISIT_A", "SubjectID": PRIVATE, "A1C": "1", "GLU": "2", "CL4": PRIVATE},
    ]
    sample_rows = [
        [PRIVATE + "_SUBJECT", "VISIT_A", "0", PRIVATE + "_CONTEXT"],
        [PRIVATE + "_SUBJECT", "VISIT_B", "2", PRIVATE + "_CONTEXT"],
        [PRIVATE + "_SUBJECT", "VISIT_C", "2.00", PRIVATE + "_OTHER_CONTEXT"],
        [PRIVATE + "_NO_DAY", "VISIT_D", "NaN", PRIVATE + "_CONTEXT"],
        [PRIVATE, "VISIT_E", "5", PRIVATE],
        [PRIVATE, "VISIT_E", "5", PRIVATE],
        ["", "VISIT_F", "6", PRIVATE],
        [PRIVATE + "_OTHER", "VISIT_G", "7", PRIVATE],
        [PRIVATE, "UNUSED_PRIVATE_SAMPLE", "9", PRIVATE],
        [PRIVATE, "", "0", PRIVATE],
        [PRIVATE, " ", "0", PRIVATE],
    ]
    return _encode(candidate.CLINICAL_HEADER, _clinical_rows(clinical_specs), "\t", "\r"), _encode(
        candidate.SAMPLE_HEADER, sample_rows, ","
    )


def _assert_failed(report, stage):
    assert report["source_audit"]["passed"] is False
    assert report["source_audit"]["failure_stage"] == stage
    assert all(report[section] is None for section in SECTIONS)
    assert PRIVATE not in json.dumps(report, allow_nan=False)
    assert report["clinical_fit_performed"] is False
    assert report["engine_activation_allowed"] is False


def test_exhaustive_linkage_preserves_duplicates_and_blocks_ambiguous_keys():
    report = _audit(*_good_bytes())
    assert report["source_audit"]["passed"] is True
    assert report["source_structure"]["clinical"]["source_record_count"] == 12
    assert report["source_structure"]["sample_info"]["source_record_count"] == 11
    assert list(report["linkage"]["ordered_partition"].values()) == [2, 2, 1, 1, 1, 5]
    assert sum(report["linkage"]["ordered_partition"].values()) == 12
    assert report["linkage"]["sample_rows_without_any_exact_nonempty_clinical_visit_key_match"] == 3
    assert report["linkage"]["right_duplicate_key_support"] == {
        "groups_with_multiple_rows": 1,
        "rows_in_repeated_groups": 2,
        "extra_rows_beyond_one_per_group": 1,
    }
    assert (
        report["source_structure"]["clinical"]["repeated_selected_token_patterns"][
            "rows_in_repeated_groups"
        ]
        == 2
    )
    assert (
        report["source_structure"]["clinical"]["keys"]["VisitID"][
            "leading_or_trailing_whitespace_rows"
        ]
        == 1
    )
    assert report["linkage"]["many_to_many_materialization_performed"] is False


def test_exact_decimal_equal_days_and_native_repeated_labels_not_people():
    report = _audit(*_good_bytes())
    linked = report["unambiguous_linked_coverage"]
    assert linked["denominator_linked_clinical_rows"] == 5
    assert linked["sample_day_disposition_all_linked_rows"] == {
        "finite": 4,
        "absent": 0,
        "nonfinite": 1,
        "malformed": 0,
    }
    assert linked["finite_assay_by_day_disposition"] == {
        "A1C_finite": {"finite": 3, "absent": 0, "nonfinite": 1, "malformed": 0},
        "GLU_finite": {"finite": 3, "absent": 0, "nonfinite": 1, "malformed": 0},
        "both_assays_finite": {"finite": 2, "absent": 0, "nonfinite": 1, "malformed": 0},
    }
    for coverage in linked["distinct_subject_label_coordinate_coverage"].values():
        assert coverage["denominator_distinct_linked_subject_labels_with_finite_assay"] == 2
        assert coverage["coordinate_coverage"] == {
            "no_finite_day": 1,
            "one_distinct_finite_day": 0,
            "multiple_distinct_finite_days": 1,
        }
    assert linked["same_subject_equal_finite_day_support"] == {
        "groups_with_multiple_rows": 2,
        "rows_in_repeated_groups": 4,
        "extra_rows_beyond_one_per_group": 2,
    }
    assert linked["subjects_with_multiple_sample_labels_at_an_equal_finite_day"] == 1
    assert linked["repeated_unique_sample_association_support"]["rows_in_repeated_groups"] == 2
    assert linked["unambiguous_repeated_coordinate_coverage_present"] is True
    assert report["context_coverage"]["linked_context_comparison"]["partition"] == {
        "both_present_exact_equal": 3,
        "both_present_unequal": 1,
        "at_least_one_structurally_absent": 1,
    }


def test_report_has_no_selected_or_excluded_values_and_no_clinical_promotion():
    report = _audit(*_good_bytes())
    encoded = json.dumps(report, allow_nan=False)
    for token in (
        PRIVATE,
        "VISIT_A",
        "VISIT_B",
        "UNMATCHED_PRIVATE_VISIT",
        "UNUSED_PRIVATE_SAMPLE",
        "NO_DAY",
        "2.00",
    ):
        assert token not in encoded
    assert report["validation_only"] is True
    assert "candidate_only" not in report
    assert report["execution_scope"] == "synthetic_software_validation_only"
    assert report["provenance"]["units_rawness_and_specimen_clock_verified"] is False
    assert report["provenance"]["sampling_model_selected"] is False
    assert report["clinical_fit_performed"] is False
    assert report["diagnosis_or_remission_inference_performed"] is False
    assert report["death_or_censoring_inference_performed"] is False
    assert report["scientific_acceptance_changed"] is False


@pytest.mark.parametrize(
    "token,kind,value",
    [
        ("", "empty", None),
        (" \t", "whitespace_only", None),
        ("0", "finite_decimal", "0"),
        ("-1", "finite_decimal", "-1"),
        (" .5 ", "finite_decimal", ".5"),
        ("+2.", "finite_decimal", "2"),
        ("2e-3", "finite_decimal", ".002"),
        ("+NaN", "explicit_nonfinite", None),
        (" -Infinity ", "explicit_nonfinite", None),
        ("INF", "explicit_nonfinite", None),
        ("NA", "nonnumeric_or_undocumented_code", None),
        ("null", "nonnumeric_or_undocumented_code", None),
        ("1_0", "nonnumeric_or_undocumented_code", None),
        ("1,0", "nonnumeric_or_undocumented_code", None),
        ("１２", "nonnumeric_or_undocumented_code", None),
        ("1junk", "nonnumeric_or_undocumented_code", None),
        ("True", "nonnumeric_or_undocumented_code", None),
        ("0x10", "nonnumeric_or_undocumented_code", None),
    ],
)
def test_lexical_classification_is_not_missing_code_or_assay_inference(token, kind, value):
    result = candidate._number(token)
    assert result.lexical == token
    assert result.kind == kind
    assert result.value == (None if value is None else candidate.Decimal(value))
    assert result.surrounding_whitespace is (
        token != token.strip() and kind in ("finite_decimal", "explicit_nonfinite")
    )


@pytest.mark.parametrize(
    "delimiter,header", [("\t", candidate.CLINICAL_HEADER), (",", candidate.SAMPLE_HEADER)]
)
def test_legal_quotes_embedded_crlf_and_escaped_quote_preserve_tokens(delimiter, header):
    row = ["" for _ in header]
    row[0] = PRIVATE + '\r\n"quoted"' + delimiter + "suffix"
    assert candidate._records(_encode(header, [row], delimiter), header, delimiter) == (tuple(row),)


@pytest.mark.parametrize(
    "suffix",
    [
        'a"b,one,2,x\n',
        '"unterminated,one,2,x',
        '"closed"junk,one,2,x\n',
        "\n",
        "one,two,three\n",
        "one,two,three,four,five\n",
    ],
)
def test_malformed_quote_shape_or_blank_record_fail_without_partial_result(suffix):
    clinical, _ = _good_bytes()
    samples = _encode(candidate.SAMPLE_HEADER, [], ",") + suffix.encode()
    _assert_failed(_audit(clinical, samples), "source_structure")


@pytest.mark.parametrize(
    "mutator",
    [
        lambda header: ["subjectid", *header[1:]],
        lambda header: [header[1], header[0], *header[2:]],
        lambda header: [*header[:-1], header[0]],
    ],
)
def test_header_case_order_or_duplicate_drift_fails_closed(mutator):
    clinical, _ = _good_bytes()
    samples = _encode(mutator(candidate.SAMPLE_HEADER), [], ",")
    _assert_failed(_audit(clinical, samples), "source_header")


def test_repeated_header_is_not_a_clinical_record():
    clinical, _ = _good_bytes()
    samples = _encode(candidate.SAMPLE_HEADER, [candidate.SAMPLE_HEADER], ",")
    _assert_failed(_audit(clinical, samples), "source_structure")


def test_both_pins_precede_decoding_or_any_selected_interpretation(monkeypatch):
    clinical, samples = _good_bytes()
    called = []
    monkeypatch.setattr(candidate, "_records", lambda *args: called.append(True))
    p = _protocol(clinical, samples)
    _assert_failed(
        candidate.preflight_bytes(clinical, samples + b"!", protocol=p), "source_identity"
    )
    assert called == []


@pytest.mark.parametrize("bad", [False, "123", -1])
def test_source_size_requires_strict_nonnegative_integer(bad):
    clinical, samples = _good_bytes()
    p = _protocol(clinical, samples)
    p["source_selection"]["sample_info"]["tree_size_bytes"] = bad
    _assert_failed(candidate.preflight_bytes(clinical, samples, protocol=p), "source_identity")


def test_same_size_wrong_git_blob_fails_before_parse():
    clinical, samples = _good_bytes()
    p = _protocol(clinical, samples)
    changed = samples.replace(b"NaN", b"Inf", 1)
    assert len(changed) == len(samples)
    _assert_failed(candidate.preflight_bytes(clinical, changed, protocol=p), "source_identity")


def test_strict_utf8_invalid_source_remains_blocked():
    clinical, samples = _good_bytes()
    samples += b"\xff"
    _assert_failed(_audit(clinical, samples), "source_encoding")


def test_empirical_route_rejects_synthetic_source_pin_substitutions_before_decode(monkeypatch):
    called = []
    monkeypatch.setattr(candidate, "_records", lambda *args: called.append(True))
    report = _audit(*_good_bytes(), validation_only=False)
    _assert_failed(report, "frozen_contract")
    assert report["validation_only"] is False
    assert report["execution_scope"] == "actual_source_intake_only"
    assert called == []


def test_empirical_contract_accepts_only_complete_frozen_metadata_and_original_pins(monkeypatch):
    assert candidate._contract(PROTOCOL, False) is None
    called = []
    monkeypatch.setattr(candidate, "_records", lambda *args: called.append(True))
    clinical, samples = _good_bytes()
    # No actual source bytes are read: these labeled fixtures cannot impersonate
    # the complete producer files even under the unchanged empirical contract.
    report = candidate.preflight_bytes(
        clinical, samples, protocol=copy.deepcopy(PROTOCOL), validation_only=False
    )
    _assert_failed(report, "source_identity")
    assert called == []


@pytest.mark.parametrize("bad", [0, 1, None, "False", PRIVATE, [], {}])
def test_execution_mode_is_strict_bool_and_never_echoes_untrusted_argument(bad):
    report = _audit(*_good_bytes(), validation_only=bad)
    _assert_failed(report, "frozen_contract")
    assert report["validation_only"] is None
    assert report["execution_scope"] == "invalid_execution_mode"


@pytest.mark.parametrize(
    "change",
    ["source_path", "commit", "rights", "extra_source_key", "root_review", "size_missing"],
)
def test_synthetic_pins_cannot_override_any_other_frozen_metadata(change):
    clinical, samples = _good_bytes()
    p = _protocol(clinical, samples)
    source = p["source_selection"]
    if change == "source_path":
        source["clinical"]["path"] = PRIVATE
    elif change == "commit":
        source["commit"] = "0" * 40
    elif change == "rights":
        source["permission"] = PRIVATE
    elif change == "extra_source_key":
        source["clinical"][PRIVATE] = True
    elif change == "root_review":
        p["root_review"] = PRIVATE
    else:
        source["sample_info"].pop("tree_size_bytes")
    _assert_failed(candidate.preflight_bytes(clinical, samples, protocol=p), "frozen_contract")


def test_source_clone_requires_both_full_byte_hashes_even_when_lengths_match(monkeypatch):
    clinical, samples = _good_bytes()
    changed = clinical.replace(b"VISIT_A", b"VISIT_Z", 1)
    assert len(changed) == len(clinical)
    p = _protocol(clinical, samples)
    called = []
    monkeypatch.setattr(candidate, "_records", lambda *args: called.append(True))
    _assert_failed(candidate.preflight_bytes(changed, samples, protocol=p), "source_identity")
    assert called == []


def test_frozen_protocol_default_path_and_complete_metadata_identity():
    assert candidate.load_frozen_protocol() == PROTOCOL
    assert candidate._canonical_sha256(PROTOCOL) == candidate.FROZEN_CANONICAL_SHA256
    assert (
        hashlib.sha256(candidate.PROTOCOL_PATH.read_bytes()).hexdigest()
        == candidate.PROTOCOL_SHA256
    )


def test_duplicate_json_keys_rejected_even_with_a_matching_test_byte_pin(tmp_path, monkeypatch):
    data = b'{"schema_version":1,"schema_version":1}'
    path = tmp_path / "synthetic-protocol.json"
    path.write_bytes(data)
    monkeypatch.setattr(candidate, "PROTOCOL_SHA256", hashlib.sha256(data).hexdigest())
    with pytest.raises(candidate._FailedStage, match="^frozen_contract$"):
        candidate.load_frozen_protocol(path)


@pytest.mark.parametrize("changed", ["selected_columns", "clinical_permission"])
def test_selection_or_clinical_permission_drift_blocks_before_calculation(changed):
    clinical, samples = _good_bytes()
    p = _protocol(clinical, samples)
    if changed == "selected_columns":
        p["source_selection"]["clinical"]["selected_columns"].append("CollectionDate")
    else:
        p["fixed_scope_flags"]["clinical_likelihood_or_fit_allowed"] = True
    _assert_failed(candidate.preflight_bytes(clinical, samples, protocol=p), "frozen_contract")


def test_record_order_changes_no_aggregate_semantics():
    clinical, samples = _good_bytes()
    crows = candidate._records(clinical, candidate.CLINICAL_HEADER, "\t")
    srows = candidate._records(samples, candidate.SAMPLE_HEADER, ",")
    reordered = _audit(
        _encode(candidate.CLINICAL_HEADER, list(reversed(crows)), "\t"),
        _encode(candidate.SAMPLE_HEADER, list(reversed(srows)), ","),
    )
    original = _audit(clinical, samples)
    for section in SECTIONS[:-1]:
        assert reordered[section] == original[section]


def test_header_only_zero_records_are_structurally_valid_not_repeated_coverage():
    report = _audit(
        _encode(candidate.CLINICAL_HEADER, [], "\t"), _encode(candidate.SAMPLE_HEADER, [], ",")
    )
    assert report["source_audit"]["passed"] is True
    assert report["source_structure"]["clinical"]["source_record_count"] == 0
    assert (
        report["unambiguous_linked_coverage"]["unambiguous_repeated_coordinate_coverage_present"]
        is False
    )


def test_decimal_clocks_do_not_collapse_distinct_values_at_float_resolution():
    specs = [
        {"VisitID": "SYNTHETIC_A", "SubjectID": PRIVATE, "A1C": "1", "GLU": "2", "CL4": ""},
        {"VisitID": "SYNTHETIC_B", "SubjectID": PRIVATE, "A1C": "1", "GLU": "2", "CL4": ""},
    ]
    days = ("1", "1.000000000000000000000000000001")
    assert float(days[0]) == float(days[1])
    clinical = _encode(candidate.CLINICAL_HEADER, _clinical_rows(specs), "\t")
    samples = _encode(
        candidate.SAMPLE_HEADER,
        [[PRIVATE, spec["VisitID"], day, ""] for spec, day in zip(specs, days, strict=True)],
        ",",
    )
    result = _audit(clinical, samples)["unambiguous_linked_coverage"]
    assert (
        result["distinct_subject_label_coordinate_coverage"]["A1C"]["coordinate_coverage"][
            "multiple_distinct_finite_days"
        ]
        == 1
    )
    assert result["same_subject_equal_finite_day_support"]["groups_with_multiple_rows"] == 0


def test_absent_nonfinite_and_undocumented_days_remain_separate():
    days = ("", " ", "INF", PRIVATE)
    specs = [
        {"VisitID": f"SYNTHETIC_{i}", "SubjectID": PRIVATE, "A1C": "0", "GLU": "-1", "CL4": ""}
        for i in range(len(days))
    ]
    clinical = _encode(candidate.CLINICAL_HEADER, _clinical_rows(specs), "\t")
    samples = _encode(
        candidate.SAMPLE_HEADER,
        [[PRIVATE, spec["VisitID"], day, ""] for spec, day in zip(specs, days, strict=True)],
        ",",
    )
    report = _audit(clinical, samples)
    assert report["numeric_token_coverage"]["Days_Since_Start"]["token_classes"] == {
        "empty": 1,
        "whitespace_only": 1,
        "finite_decimal": 0,
        "explicit_nonfinite": 1,
        "nonnumeric_or_undocumented_code": 1,
    }
    linked = report["unambiguous_linked_coverage"]
    assert linked["sample_day_disposition_all_linked_rows"] == {
        "finite": 0,
        "absent": 2,
        "nonfinite": 1,
        "malformed": 1,
    }
    assert linked["unambiguous_repeated_coordinate_coverage_present"] is False
    assert (
        linked["distinct_subject_label_coordinate_coverage"]["A1C"]["coordinate_coverage"][
            "no_finite_day"
        ]
        == 1
    )


def test_all_linked_subjects_reconcile_with_each_no_finite_assay_complement():
    specs = [
        {"VisitID": "NO_ASSAY", "SubjectID": PRIVATE + "_NONE", "A1C": "NA", "GLU": "", "CL4": ""},
        {"VisitID": "A1C_ONLY", "SubjectID": PRIVATE + "_A1C", "A1C": "0", "GLU": "NaN", "CL4": ""},
        {"VisitID": "GLU_ONLY", "SubjectID": PRIVATE + "_GLU", "A1C": " ", "GLU": "-1", "CL4": ""},
        {"VisitID": "BOTH", "SubjectID": PRIVATE + "_BOTH", "A1C": "1", "GLU": "2", "CL4": ""},
    ]
    clinical = _encode(candidate.CLINICAL_HEADER, _clinical_rows(specs), "\t")
    samples = _encode(
        candidate.SAMPLE_HEADER,
        [
            [s["SubjectID"], s["VisitID"], day, ""]
            for s, day in zip(specs, ("0", "", "2", "3"), strict=True)
        ],
        ",",
    )
    report = _audit(clinical, samples)
    assert report["source_audit"]["passed"] is True
    linked = report["unambiguous_linked_coverage"]
    assert linked["total_distinct_unambiguous_linked_subject_labels"] == 4
    expected = {"A1C": (2, 2, 1, 1), "GLU": (2, 2, 0, 2), "either_finite_assay": (3, 1, 1, 2)}
    for name, (finite_assay, no_finite_assay, no_day, one_day) in expected.items():
        coverage = linked["distinct_subject_label_coordinate_coverage"][name]
        assert coverage["denominator_total_distinct_unambiguous_linked_subject_labels"] == 4
        assert (
            coverage["denominator_distinct_linked_subject_labels_with_finite_assay"] == finite_assay
        )
        assert coverage["distinct_linked_subject_labels_with_no_finite_assay"] == no_finite_assay
        assert finite_assay + no_finite_assay == 4
        assert coverage["coordinate_coverage"] == {
            "no_finite_day": no_day,
            "one_distinct_finite_day": one_day,
            "multiple_distinct_finite_days": 0,
        }


@pytest.mark.parametrize(
    "change",
    [
        "numeric_wrong_source_denominator",
        "linkage_denominator",
        "finite_day_denominator",
        "subject_assay_complement",
        "both_assay_bound",
        "union_assay_bound",
        "duplicate_support",
        "numeric_whitespace_bound",
        "bool_count",
        "unknown_export_key",
    ],
)
def test_declared_count_closure_rejects_inconsistent_internal_aggregates(change):
    report = _audit(*_good_bytes())
    result = copy.deepcopy({name: report[name] for name in SECTIONS[:-1]})
    linked = result["unambiguous_linked_coverage"]
    numeric = result["numeric_token_coverage"]["A1C"]
    if change == "numeric_wrong_source_denominator":
        numeric["denominator_rows"] += 1
        numeric["token_classes"]["finite_decimal"] += 1
    elif change == "linkage_denominator":
        result["linkage"]["denominator_clinical_rows"] += 1
    elif change == "finite_day_denominator":
        linked["denominator_linked_rows_with_finite_day"] += 1
    elif change == "subject_assay_complement":
        linked["distinct_subject_label_coordinate_coverage"]["A1C"][
            "distinct_linked_subject_labels_with_no_finite_assay"
        ] += 1
    elif change == "both_assay_bound":
        linked["finite_assay_by_day_disposition"]["both_assays_finite"]["finite"] = 4
    elif change == "union_assay_bound":
        linked["finite_assay_by_day_disposition"]["A1C_finite"]["finite"] = 4
    elif change == "duplicate_support":
        linked["same_subject_equal_finite_day_support"]["rows_in_repeated_groups"] += 1
        linked["same_subject_equal_finite_day_support"]["extra_rows_beyond_one_per_group"] += 1
    elif change == "numeric_whitespace_bound":
        numeric["numeric_surrounding_whitespace_rows"] = (
            numeric["token_classes"]["finite_decimal"] + 1
        )
    elif change == "bool_count":
        numeric["numeric_surrounding_whitespace_rows"] = False
    else:
        result[PRIVATE] = 1
    with pytest.raises(candidate._FailedStage, match="^aggregate_reconciliation$"):
        candidate._reconcile(result)


def test_contract_method_cannot_drift_alongside_matching_synthetic_byte_pins():
    clinical, samples = _good_bytes()
    p = _protocol(clinical, samples)
    p["association_contract"]["method"] = PRIVATE
    _assert_failed(candidate.preflight_bytes(clinical, samples, protocol=p), "frozen_contract")


def test_reviewed_protocol_file_tamper_rejected_without_echo(monkeypatch):
    monkeypatch.setattr(
        Path, "read_bytes", lambda self: ('{"private": "' + PRIVATE + '"}').encode()
    )
    with pytest.raises(candidate._FailedStage, match="^frozen_contract$"):
        candidate.load_frozen_protocol(Path("unused-synthetic.json"))


def test_late_provenance_failure_publishes_no_partial_aggregates(monkeypatch):
    def failed_read(self):
        raise OSError(PRIVATE)

    monkeypatch.setattr(Path, "read_bytes", failed_read)
    _assert_failed(_audit(*_good_bytes()), "success_provenance")


def test_unknown_internal_exception_payload_cannot_become_stage(monkeypatch):
    def failed_summary(*args):
        raise candidate._FailedStage(PRIVATE)

    monkeypatch.setattr(candidate, "_summarize", failed_summary)
    _assert_failed(_audit(*_good_bytes()), "aggregate_reconciliation")
