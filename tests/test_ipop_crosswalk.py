"""Synthetic byte fixtures only; no participant source files or graph are read."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from demeter.analysis import ipop_crosswalk as crosswalk
from demeter.analysis import ipop_preflight as v1

PROTOCOL = crosswalk.load_frozen_crosswalk_protocol()
PRIVATE = "PRIVATE_SYNTHETIC_TOKEN"
RESULT_SECTIONS = (
    "v1_result",
    "source_structure",
    "numeric_token_coverage",
    "namespace_consistency",
    "linkage",
    "unambiguous_linked_coverage",
    "context_coverage",
    "provenance",
)


def _encode(header, rows, delimiter):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _bytes(clinical, samples):
    crows = []
    for spec in clinical:
        row = {key: PRIVATE + "_EXCLUDED" for key in v1.CLINICAL_HEADER}
        row.update(VisitID="", SubjectID="", A1C="", GLU="", CL4="")
        row.update(spec)
        crows.append([row[key] for key in v1.CLINICAL_HEADER])
    return _encode(v1.CLINICAL_HEADER, crows, "\t"), _encode(v1.SAMPLE_HEADER, samples, ",")


def _pin(data):
    return {
        "tree_size_bytes": len(data),
        "git_blob": hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest(),
    }


def _protocol(clinical, samples):
    protocol = copy.deepcopy(PROTOCOL)
    for role, data in (("clinical", clinical), ("sample_info", samples)):
        protocol["source_selection"][role].update(_pin(data))
    return protocol


def _audit(clinical, samples, **kwargs):
    cbytes, sbytes = _bytes(clinical, samples)
    return crosswalk.preflight_crosswalk_bytes(
        cbytes, sbytes, protocol=_protocol(cbytes, sbytes), **kwargs
    )


def _literal(cbytes, sbytes):
    protocol = v1.load_frozen_protocol()
    for role, data in (("clinical", cbytes), ("sample_info", sbytes)):
        protocol["source_selection"][role].update(_pin(data))
    return v1.preflight_bytes(cbytes, sbytes, protocol=protocol)


def _assert_success(report):
    assert report["source_audit"]["passed"] is True
    assert report["source_audit"]["failure_stage"] is None
    assert report["execution_scope"] == "synthetic_software_validation_only"
    assert report["validation_only"] is True
    assert report["provenance"]["acquisition_receipts_verified"] is False
    assert report["provenance"]["participant_identity_verified"] is False
    assert report["clinical_fit_performed"] is False
    assert report["engine_activation_allowed"] is False
    assert report["scientific_acceptance_changed"] is False


def _assert_failed(report, stage):
    assert report["source_audit"]["passed"] is False
    assert report["source_audit"]["failure_stage"] == stage
    assert all(report[key] is None for key in RESULT_SECTIONS)
    assert PRIVATE not in json.dumps(report, allow_nan=False)
    assert report["clinical_fit_performed"] is False
    assert report["engine_activation_allowed"] is False


def _row(visit, subject, a1c="1", glu="2", context=PRIVATE + "_CONTEXT"):
    return {"VisitID": visit, "SubjectID": subject, "A1C": a1c, "GLU": glu, "CL4": context}


def _degree(report, namespace):
    return report["namespace_consistency"][namespace]["observed_partner_degree"]


def test_disjoint_namespace_bijection_preserves_v1_and_groups_metadata_coordinates():
    clinical = [_row("V1", PRIVATE + "_C"), _row("V1", PRIVATE + "_C"), _row("V2", PRIVATE + "_C")]
    samples = [
        [PRIVATE + "_M", "V1", "1.00", PRIVATE + "_CONTEXT"],
        [PRIVATE + "_M", "V2", "2", PRIVATE + "_CONTEXT"],
    ]
    cbytes, sbytes = _bytes(clinical, samples)
    report = _audit(clinical, samples)
    _assert_success(report)
    assert report["v1_result"] == _literal(cbytes, sbytes)
    assert report["source_structure"] == report["v1_result"]["source_structure"]
    assert report["numeric_token_coverage"] == report["v1_result"]["numeric_token_coverage"]
    assert (
        report["v1_result"]["linkage"]["ordered_partition"][
            "subject_disagreement_in_unique_sample_match"
        ]
        == 3
    )
    assert (
        report["v1_result"]["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"] == 0
    )
    assert report["linkage"]["ordered_partition"][crosswalk.ASSOCIATION_KINDS[-1]] == 3
    assert report["namespace_consistency"]["distinct_possible_subject_pair_edges"] == 1
    assert _degree(report, "clinical_namespace") == {"zero": 0, "one": 1, "multiple": 0}
    assert _degree(report, "metadata_namespace") == {"zero": 0, "one": 1, "multiple": 0}
    coverage = report["unambiguous_linked_coverage"]
    assert coverage["denominator_linked_clinical_rows"] == 3
    assert coverage["same_subject_equal_finite_day_support"] == {
        "groups_with_multiple_rows": 1,
        "rows_in_repeated_groups": 2,
        "extra_rows_beyond_one_per_group": 1,
    }
    assert coverage["distinct_subject_label_coordinate_coverage"]["A1C"]["coordinate_coverage"] == {
        "no_finite_day": 0,
        "one_distinct_finite_day": 0,
        "multiple_distinct_finite_days": 1,
    }
    assert (
        report["context_coverage"]["clinical_CL4"]
        == report["v1_result"]["context_coverage"]["clinical_CL4"]
    )
    assert (
        report["context_coverage"]["linked_context_comparison"]["partition"][
            "both_present_exact_equal"
        ]
        == 3
    )
    assert PRIVATE not in json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("direction", ["split", "merge", "chain"])
def test_conflicts_quarantine_all_rows_without_iterative_rescue(direction):
    if direction == "split":
        subjects = [("C1", "M1"), ("C1", "M2")]
        expected = {"one_one": 0, "one_multiple": 0, "multiple_one": 2, "multiple_multiple": 0}
    elif direction == "merge":
        subjects = [("C1", "M1"), ("C2", "M1")]
        expected = {"one_one": 0, "one_multiple": 2, "multiple_one": 0, "multiple_multiple": 0}
    else:
        subjects = [("C1", "M1"), ("C1", "M2"), ("C2", "M2")]
        expected = {"one_one": 0, "one_multiple": 1, "multiple_one": 1, "multiple_multiple": 1}
    clinical = [_row(f"V{i}", c) for i, (c, _) in enumerate(subjects)]
    samples = [[m, f"V{i}", str(i), ""] for i, (_, m) in enumerate(subjects)]
    report = _audit(clinical, samples)
    _assert_success(report)
    assert report["linkage"]["unique_sample_candidate_degree_combinations"] == expected
    assert report["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"] == 0
    assert report["namespace_consistency"]["distinct_possible_subject_pair_edges"] == len(subjects)
    ordered = report["linkage"]["ordered_partition"]
    assert (
        ordered["clinical_namespace_multiple_partners"]
        == expected["multiple_one"] + expected["multiple_multiple"]
    )
    assert ordered["metadata_namespace_multiple_partners"] == expected["one_multiple"]


@pytest.mark.parametrize("same_ambiguous_partner", [True, False])
def test_ambiguous_right_keys_supply_all_possible_partners_but_never_observations(
    same_ambiguous_partner,
):
    clinical = [_row("Unique", "C1"), _row("Ambiguous", "C1")]
    partners = ["M1", "M1" if same_ambiguous_partner else "M2"]
    samples = [["M1", "Unique", "0", ""], *[[m, "Ambiguous", "1", ""] for m in partners]]
    report = _audit(clinical, samples)
    _assert_success(report)
    graph = report["namespace_consistency"]
    assert graph["clinical_rows_contributing_possible_edges"] == 2
    assert graph["clinical_rows_with_ambiguous_sample_keys_contributing_possible_edges"] == 1
    assert graph["distinct_possible_subject_pair_edges"] == (1 if same_ambiguous_partner else 2)
    ordered = report["linkage"]["ordered_partition"]
    assert ordered["multiple_sample_rows_for_matching_key"] == 1
    assert ordered["mutually_degree_one_unique_sample_association"] == int(same_ambiguous_partner)
    assert ordered["clinical_namespace_multiple_partners"] == int(not same_ambiguous_partner)
    assert report["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"] == int(
        same_ambiguous_partner
    )


def test_ambiguous_partner_can_create_reverse_conflict_on_another_unique_row():
    report = _audit(
        [_row("Unique", "C2"), _row("Ambiguous", "C1")],
        [["M1", "Unique", "0", ""], ["M1", "Ambiguous", "1", ""], ["M2", "Ambiguous", "1", ""]],
    )
    _assert_success(report)
    assert report["namespace_consistency"]["distinct_possible_subject_pair_edges"] == 3
    assert report["linkage"]["unique_sample_candidate_degree_combinations"] == {
        "one_one": 0,
        "one_multiple": 1,
        "multiple_one": 0,
        "multiple_multiple": 0,
    }
    assert report["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"] == 0


@pytest.mark.parametrize(
    "a1c,glu,day", [("", "", ""), ("NA", "null", "bad"), ("NaN", "Inf", "NaN"), ("-1", "0", "-2")]
)
def test_graph_never_prefilters_assay_or_day_eligibility(a1c, glu, day):
    report = _audit(
        [_row("V1", "C1"), _row("V2", "C1", a1c, glu)],
        [["M1", "V1", "0", ""], ["M2", "V2", day, ""]],
    )
    _assert_success(report)
    assert report["namespace_consistency"]["distinct_possible_subject_pair_edges"] == 2
    assert report["linkage"]["ordered_partition"]["clinical_namespace_multiple_partners"] == 2
    assert report["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"] == 0


def test_equal_lexical_subjects_remain_separate_namespaces_and_do_not_bypass_conflict():
    report = _audit(
        [_row("V1", "SAME"), _row("V2", "C2")],
        [["SAME", "V1", "0", ""], ["SAME", "V2", "1", ""]],
    )
    _assert_success(report)
    assert (
        report["v1_result"]["linkage"]["ordered_partition"][
            "unique_sample_match_with_subject_agreement"
        ]
        == 1
    )
    assert report["linkage"]["ordered_partition"]["metadata_namespace_multiple_partners"] == 2
    assert report["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"] == 0
    assert _degree(report, "clinical_namespace") == {"zero": 0, "one": 2, "multiple": 0}
    assert _degree(report, "metadata_namespace") == {"zero": 0, "one": 0, "multiple": 1}


def test_missing_tokens_never_form_edges_and_full_namespace_denominators_include_zero_degree():
    clinical = [
        _row("", "C_empty_visit"),
        _row(" ", "C_white_visit"),
        _row("NoMatch", "C_unused"),
        _row("EmptySubject", ""),
        _row("WhiteSubject", " \t"),
        _row("MissingRightSubject", "C_missing_meta"),
        _row("Good", "C_good"),
    ]
    samples = [
        ["M_unmatched", "Other", "0", ""],
        ["M_empty_key", "", "0", ""],
        ["M_white_key", " ", "0", ""],
        ["M_without_clinical_subject", "EmptySubject", "0", ""],
        ["M_without_clinical_subject2", "WhiteSubject", "0", ""],
        ["", "MissingRightSubject", "0", ""],
        ["M_good", "Good", "0", ""],
    ]
    report = _audit(clinical, samples)
    _assert_success(report)
    assert _degree(report, "clinical_namespace") == {"zero": 4, "one": 1, "multiple": 0}
    assert _degree(report, "metadata_namespace") == {"zero": 5, "one": 1, "multiple": 0}
    assert report["namespace_consistency"]["distinct_possible_subject_pair_edges"] == 1
    assert list(report["linkage"]["ordered_partition"].values()) == [4, 1, 0, 1, 0, 0, 1]


def test_nonempty_whitespace_keys_stay_exact_without_rescue():
    report = _audit(
        [_row(" V1", "C1"), _row("V2", "C2")], [["M1", "V1", "0", ""], [" M2 ", "V2", "1", ""]]
    )
    _assert_success(report)
    assert report["linkage"]["ordered_partition"]["no_exact_sample_key_match"] == 1
    assert _degree(report, "clinical_namespace") == {"zero": 1, "one": 1, "multiple": 0}
    assert (
        report["source_structure"]["sample_info"]["keys"]["SubjectID"][
            "leading_or_trailing_whitespace_rows"
        ]
        == 1
    )


def test_full_linked_subject_denominator_complements_and_exact_decimal_coordinates():
    specs = [
        ("C1", "M1", "NA", "", "0"),
        ("C2", "M2", "0", "NaN", ""),
        ("C3", "M3", " ", "-1", "2"),
        ("C4", "M4", "1", "2", "1"),
        ("C4", "M4", "1", "2", "1.000000000000000000000000000001"),
    ]
    clinical = [_row(f"V{i}", c, a, g) for i, (c, _, a, g, _) in enumerate(specs)]
    samples = [[m, f"V{i}", d, ""] for i, (_, m, _, _, d) in enumerate(specs)]
    report = _audit(clinical, samples)
    _assert_success(report)
    coverage = report["unambiguous_linked_coverage"]
    assert coverage["denominator_linked_clinical_rows"] == 5
    assert coverage["total_distinct_unambiguous_linked_subject_labels"] == 4
    subjects = coverage["distinct_subject_label_coordinate_coverage"]
    assert [
        subjects[key]["distinct_linked_subject_labels_with_no_finite_assay"]
        for key in ("A1C", "GLU", "either_finite_assay")
    ] == [2, 2, 1]
    assert subjects["either_finite_assay"]["coordinate_coverage"] == {
        "no_finite_day": 1,
        "one_distinct_finite_day": 1,
        "multiple_distinct_finite_days": 1,
    }
    assert coverage["unambiguous_repeated_coordinate_coverage_present"] is True
    assert coverage["same_subject_equal_finite_day_support"]["groups_with_multiple_rows"] == 0


def test_ambiguous_matching_rows_without_present_metadata_subject_supply_no_invented_edge():
    report = _audit([_row("V1", "C1")], [["", "V1", "0", ""], [" ", "V1", "1", ""]])
    _assert_success(report)
    assert report["namespace_consistency"]["clinical_rows_contributing_possible_edges"] == 0
    assert (
        report["namespace_consistency"][
            "clinical_rows_with_ambiguous_sample_keys_contributing_possible_edges"
        ]
        == 0
    )
    assert report["linkage"]["ordered_partition"]["multiple_sample_rows_for_matching_key"] == 1
    assert _degree(report, "clinical_namespace") == {"zero": 1, "one": 0, "multiple": 0}


def test_row_permutation_changes_neither_graph_nor_coverage():
    clinical = [_row("V1", "C1"), _row("V2", "C1"), _row("V3", "C2"), _row("V4", "C3")]
    samples = [
        ["M1", "V1", "1", ""],
        ["M2", "V2", "2", ""],
        ["M2", "V3", "3", ""],
        ["M3", "V4", "4", ""],
        ["M3", "V4", "4", ""],
    ]
    original = _audit(clinical, samples)
    reordered = _audit(list(reversed(clinical)), list(reversed(samples)))
    _assert_success(original)
    _assert_success(reordered)
    for key in RESULT_SECTIONS[:-1]:
        if key == "v1_result":
            for nested in (
                "source_structure",
                "numeric_token_coverage",
                "linkage",
                "unambiguous_linked_coverage",
                "context_coverage",
            ):
                assert original[key][nested] == reordered[key][nested]
        else:
            assert original[key] == reordered[key]


def test_header_only_sources_return_explicit_zero_denominators():
    report = _audit([], [])
    _assert_success(report)
    assert report["namespace_consistency"]["distinct_possible_subject_pair_edges"] == 0
    assert report["namespace_consistency"]["denominator_source_clinical_rows"] == 0
    assert _degree(report, "clinical_namespace") == {"zero": 0, "one": 0, "multiple": 0}
    assert _degree(report, "metadata_namespace") == {"zero": 0, "one": 0, "multiple": 0}


@pytest.mark.parametrize("bad", [0, 1, None, PRIVATE, [], {}])
def test_mode_requires_strict_bool_without_echo(bad):
    _assert_failed(_audit([], [], validation_only=bad), "frozen_contract")


def test_empirical_route_accepts_exact_contract_but_rejects_synthetic_pins_before_decode(
    monkeypatch,
):
    assert crosswalk._contract(PROTOCOL, False) is None
    cbytes, sbytes = _bytes([], [])
    called = []
    monkeypatch.setattr(v1, "_records", lambda *args: called.append(True))
    _assert_failed(
        crosswalk.preflight_crosswalk_bytes(
            cbytes, sbytes, protocol=_protocol(cbytes, sbytes), validation_only=False
        ),
        "frozen_contract",
    )
    _assert_failed(
        crosswalk.preflight_crosswalk_bytes(
            cbytes, sbytes, protocol=PROTOCOL, validation_only=False
        ),
        "source_identity",
    )
    assert called == []


@pytest.mark.parametrize(
    "change",
    ["graph", "admission", "partition", "source_path", "extra_source", "scope", "v1_binding"],
)
def test_frozen_semantics_cannot_change_alongside_matching_fixture_pins(change):
    cbytes, sbytes = _bytes([], [])
    protocol = _protocol(cbytes, sbytes)
    if change in ("graph", "admission"):
        protocol["association_contract"][change] = PRIVATE
    elif change == "partition":
        protocol["association_contract"]["clinical_row_partition_order"].reverse()
    elif change == "source_path":
        protocol["source_selection"]["clinical"]["path"] = PRIVATE
    elif change == "extra_source":
        protocol["source_selection"]["sample_info"][PRIVATE] = True
    elif change == "scope":
        protocol["fixed_scope_flags"]["clinical_likelihood_or_fit_allowed"] = True
    else:
        protocol["binding_acquisition_protocol"]["sha256"] = "0" * 64
    _assert_failed(
        crosswalk.preflight_crosswalk_bytes(cbytes, sbytes, protocol=protocol), "frozen_contract"
    )


@pytest.mark.parametrize("role", ["clinical", "sample_info"])
def test_each_complete_byte_identity_precedes_graph_and_parsing(role, monkeypatch):
    cbytes, sbytes = _bytes([_row("V1", "C1")], [["M1", "V1", "1", ""]])
    protocol = _protocol(cbytes, sbytes)
    called = []
    monkeypatch.setattr(v1, "_records", lambda *args: called.append("parse"))
    monkeypatch.setattr(crosswalk, "_summarize_namespace", lambda *args: called.append("graph"))
    if role == "clinical":
        cbytes = cbytes.replace(b"C1", b"C2", 1)
    else:
        sbytes = sbytes.replace(b"M1", b"M2", 1)
    _assert_failed(
        crosswalk.preflight_crosswalk_bytes(cbytes, sbytes, protocol=protocol), "source_identity"
    )
    assert called == []


@pytest.mark.parametrize("bad", [False, "0", -1])
def test_synthetic_byte_size_override_still_requires_strict_valid_identity(bad):
    cbytes, sbytes = _bytes([], [])
    protocol = _protocol(cbytes, sbytes)
    protocol["source_selection"]["sample_info"]["tree_size_bytes"] = bad
    _assert_failed(
        crosswalk.preflight_crosswalk_bytes(cbytes, sbytes, protocol=protocol), "source_identity"
    )


@pytest.mark.parametrize("bad_source", ["encoding", "header", "width"])
def test_source_parse_failures_publish_no_v1_or_namespace_partial_result(bad_source):
    cbytes, sbytes = _bytes([], [])
    if bad_source == "encoding":
        sbytes += b"\xff"
        stage = "source_encoding"
    elif bad_source == "header":
        sbytes = sbytes.replace(b"SubjectID", b"subjectid", 1)
        stage = "source_header"
    else:
        sbytes += (PRIVATE + ",two,three\n").encode()
        stage = "source_structure"
    _assert_failed(
        crosswalk.preflight_crosswalk_bytes(cbytes, sbytes, protocol=_protocol(cbytes, sbytes)),
        stage,
    )


def test_frozen_loader_rejects_changed_file_and_duplicate_keys(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.json"
    data = b'{"schema_version":1,"schema_version":1}'
    path.write_bytes(data)
    with pytest.raises(v1._FailedStage, match="^frozen_contract$"):
        crosswalk.load_frozen_crosswalk_protocol(path)
    monkeypatch.setattr(crosswalk, "PROTOCOL_SHA256", hashlib.sha256(data).hexdigest())
    with pytest.raises(v1._FailedStage, match="^frozen_contract$"):
        crosswalk.load_frozen_crosswalk_protocol(path)


def test_late_implementation_hash_failure_never_publishes_successful_v1_or_coverage(monkeypatch):
    original = Path.read_bytes

    def read(path):
        if path.resolve() == Path(crosswalk.__file__).resolve():
            raise OSError(PRIVATE)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    _assert_failed(_audit([_row("V1", "C1")], [["M1", "V1", "1", ""]]), "success_provenance")


def test_unknown_internal_graph_exception_is_sanitized(monkeypatch):
    def failed(*args):
        raise v1._FailedStage(PRIVATE)

    monkeypatch.setattr(crosswalk, "_summarize_namespace", failed)
    _assert_failed(_audit([], []), "namespace_graph")


@pytest.mark.parametrize(
    "change",
    [
        "degree_closure",
        "edges",
        "candidate_closure",
        "row_edge_closure",
        "ordered_precedence",
        "linked_count",
        "bool_count",
    ],
)
def test_namespace_reconciliation_rejects_inconsistent_aggregate_counts(change):
    cbytes, sbytes = _bytes(
        [_row("V1", "C1"), _row("V2", "C2")], [["M1", "V1", "1", ""], ["M2", "V2", "2", ""]]
    )
    clinical = v1._parse_clinical(v1._records(cbytes, v1.CLINICAL_HEADER, "\t"))
    samples = v1._parse_samples(v1._records(sbytes, v1.SAMPLE_HEADER, ","))
    result = crosswalk._summarize_namespace(clinical, samples)
    graph = result["namespace_consistency"]
    linkage = result["linkage"]
    if change == "degree_closure":
        graph["clinical_namespace"]["observed_partner_degree"]["zero"] += 1
    elif change == "edges":
        graph["distinct_possible_subject_pair_edges"] = 1
    elif change == "candidate_closure":
        linkage["denominator_unique_sample_candidate_rows_with_both_subjects_nonempty"] += 1
    elif change == "row_edge_closure":
        graph["clinical_rows_contributing_possible_edges"] -= 1
    elif change == "ordered_precedence":
        linkage["ordered_partition"]["metadata_namespace_multiple_partners"] = 1
        linkage["ordered_partition"]["mutually_degree_one_unique_sample_association"] = 1
    elif change == "linked_count":
        result["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"] -= 1
    else:
        graph["clinical_rows_with_ambiguous_sample_keys_contributing_possible_edges"] = False
    with pytest.raises(v1._FailedStage, match="^aggregate_reconciliation$"):
        crosswalk._reconcile_namespace(result, {"C1", "C2"}, {"M1", "M2"})
