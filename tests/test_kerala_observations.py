"""Synthetic source-preservation checks; no participant evidence is loaded."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import pytest

from demeter.data.kerala_observations import (
    LABELS,
    build_source_observations,
    public_diagnostics,
)

ABSENT = ("absent", None)


def text_cell(value):
    return ("string", value) if value is not None else ABSENT


def selected_fixture(
    key=("string", "synthetic-opaque-key"),
    *,
    categories=("IFG", "IFG", "NGT"),
    ada=("No", "No", "No"),
    incidence=("No", "No"),
    total="No",
    medications=(None, None, "No", "No"),
    two_hour=(True, True, True),
):
    """Only protocol-selected fields, with fake opaque linkage and typed cells."""
    wide = {
        "participant_id": key,
        "tot_diab_incidence": text_cell(total),
        "tot_diab_incidence1": text_cell(incidence[0]),
        "tot_diab_incidence2": text_cell(incidence[1]),
    }
    for field, value in zip(
        ("diabdrugs_10", "diabdrugs_20", "diabdrugs_1", "diabdrugs_2"),
        medications,
        strict=True,
    ):
        wide[field] = text_cell(value)
    long = []
    for index, label in enumerate(LABELS):
        row = {
            "participant_id": key,
            "timepoint": text_cell(label),
            "arms": text_cell("Control"),
            "cluster": ("string", "synthetic-opaque-cluster"),
            "glycemiaADA": text_cell(categories[index]),
            "diabADA": text_cell(ada[index]),
            "fpgmgdl": ("number", "987654321"),
            "twohrpgmgdl": ("number", "876543219") if two_hour[index] else ABSENT,
        }
        for field in ("arms", "cluster", "glycemiaADA", "diabADA", "fpgmgdl", "twohrpgmgdl"):
            wide[f"{field}{index}"] = row[field]
        long.append(row)
    return [wide], long


def test_number_and_string_keys_remain_distinct_without_coercion():
    numeric_primary, numeric_long = selected_fixture(("number", "1"))
    string_primary, string_long = selected_fixture(("string", "1"))
    subjects = build_source_observations(
        numeric_primary + string_primary, numeric_long + string_long
    )
    assert {subject.opaque_key for subject in subjects} == {("number", "1"), ("string", "1")}
    assert len(subjects) == 2
    assert public_diagnostics(subjects)["unlabeled_observation_pattern_cell_size_histogram"] == {
        2: 1
    }


@pytest.mark.parametrize(
    "invalid",
    [ABSENT, ("empty", ""), ("error", "#N/A"), ("formula_unsupported", "=1"), ("unsupported", "x")],
)
@pytest.mark.parametrize("surface", ["primary", "secondary"])
def test_invalid_linkage_keys_fail_without_echoing_values(invalid, surface):
    primary, long = selected_fixture()
    (primary if surface == "primary" else long)[0]["participant_id"] = invalid
    with pytest.raises(ValueError) as failure:
        build_source_observations(primary, long)
    assert "synthetic-opaque" not in str(failure.value)
    assert "#N/A" not in str(failure.value)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_primary",
        "duplicate_visit",
        "missing_visit",
        "unlinked_key",
        "unknown_visit",
        "typed_visit_mismatch",
    ],
)
def test_nonunique_incomplete_or_incompatible_linkage_fails(mutation):
    primary, long = selected_fixture()
    if mutation == "duplicate_primary":
        primary.append(deepcopy(primary[0]))
    elif mutation == "duplicate_visit":
        long.append(deepcopy(long[1]))
    elif mutation == "missing_visit":
        long.pop()
    elif mutation == "unlinked_key":
        for row in long:
            row["participant_id"] = ("number", "1")
    elif mutation == "unknown_visit":
        long[1]["timepoint"] = text_cell("unapproved visit text")
    else:
        long[1]["timepoint"] = ("number", "12")
    with pytest.raises(ValueError):
        build_source_observations(primary, long)


@pytest.mark.parametrize("surface", ["wide", "long"])
@pytest.mark.parametrize("field", ["arms", "cluster"])
def test_assignment_and_cluster_drift_fail_on_either_copy(surface, field):
    primary, long = selected_fixture()
    alternate = text_cell("Intervention" if field == "arms" else "other-synthetic-cluster")
    if surface == "wide":
        primary[0][f"{field}1"] = alternate
    else:
        long[1][field] = alternate
    with pytest.raises(ValueError, match="drift"):
        build_source_observations(primary, long)


@pytest.mark.parametrize("field", ["glycemiaADA", "diabADA", "fpgmgdl", "twohrpgmgdl"])
def test_selected_clinical_copy_mismatch_fails(field):
    primary, long = selected_fixture()
    long[1][field] = ABSENT
    with pytest.raises(ValueError, match="copies disagree"):
        build_source_observations(primary, long)


def test_uninterpretable_assignment_and_invalid_cluster_fail():
    primary, long = selected_fixture()
    primary[0]["arms0"] = text_cell("unknown private assignment")
    with pytest.raises(ValueError, match="assignment label"):
        build_source_observations(primary, long)
    primary, long = selected_fixture()
    primary[0]["cluster0"] = ABSENT
    with pytest.raises(ValueError, match="cluster linkage"):
        build_source_observations(primary, long)


@pytest.mark.parametrize("later_flag", ["No", None, "unapproved flag text"])
def test_no_blank_or_unrecognized_flag_and_lower_category_never_erase_positive(later_flag):
    primary, long = selected_fixture(
        categories=("IGT", "diabetes", "NGT"),
        ada=("No", "Yes", "No"),
        incidence=("Yes", later_flag),
        total=None,
        two_hour=(True, True, False),
    )
    subject = build_source_observations(primary, long)[0]
    assert [visit.seen_positive_suffix_evidence for visit in subject.visits] == [False, True, True]
    assert subject.visits[2].glycemia.literal == "NGT"
    assert subject.visits[2].prior_ada_positive_evidence is True
    assert subject.prior_clinical_history is None
    assert subject.first_onset_interval is None


def test_horizon_total_positive_is_preserved_without_backdating():
    primary, long = selected_fixture(incidence=(None, None), total="Yes")
    subject = build_source_observations(primary, long)[0]
    assert subject.horizon_total.literal == "Yes"
    assert not any(visit.seen_positive_suffix_evidence for visit in subject.visits)
    assert all(visit.incidence_flag.literal is None for visit in subject.visits)
    assert subject.first_onset_interval is None


def test_second_slot_positive_does_not_create_first_slot_history():
    primary, long = selected_fixture(incidence=("No", "Yes"))
    subject = build_source_observations(primary, long)[0]
    assert [visit.seen_positive_suffix_evidence for visit in subject.visits] == [False, False, True]
    assert subject.first_onset_interval is None


def test_incidence_positive_alone_does_not_trigger_ogtt_policy_check():
    primary, long = selected_fixture(incidence=("Yes", "No"), two_hour=(True, True, True))
    subject = build_source_observations(primary, long)[0]
    assert subject.visits[2].seen_positive_suffix_evidence is True
    assert subject.visits[2].prior_ada_positive_evidence is False
    # No ADA trigger was evaluated: incidence positivity is not that trigger.
    assert (
        public_diagnostics((subject,))[
            "later_two_hour_storage_absent_after_earlier_ada_positive_compatible"
        ]
        is None
    )


@pytest.mark.parametrize("category,flag", [("diabetes", "No"), ("IFG", "Yes")])
def test_earlier_ada_evidence_is_separate_and_stored_later_test_is_incompatible(category, flag):
    primary, long = selected_fixture(categories=("IFG", category, "NGT"), ada=("No", flag, "No"))
    subjects = build_source_observations(primary, long)
    assert subjects[0].visits[2].prior_ada_positive_evidence is True
    assert subjects[0].visits[2].seen_positive_suffix_evidence is False
    report = public_diagnostics(subjects)
    assert report["ada_category_and_flag_agree_where_both_interpretable"] is False
    assert report["later_two_hour_storage_absent_after_earlier_ada_positive_compatible"] is False


def test_absent_later_test_is_compatible_without_inventing_an_individual_reason():
    primary, long = selected_fixture(
        categories=("IGT", "diabetes", None),
        ada=("No", "Yes", None),
        two_hour=(True, True, False),
    )
    subject = build_source_observations(primary, long)[0]
    assert (
        public_diagnostics((subject,))[
            "later_two_hour_storage_absent_after_earlier_ada_positive_compatible"
        ]
        is True
    )
    assert subject.visits[2].absence_reason is None


def test_medication_yes_never_establishes_confirmation_or_treatment_clock():
    primary, long = selected_fixture(medications=(None, None, "Yes", "Yes"))
    subject = build_source_observations(primary, long)[0]
    assert subject.visits[1].medication_flags[0].literal == "Yes"
    assert subject.visits[2].medication_flags[0].literal == "Yes"
    for visit in subject.visits:
        assert visit.clinical_confirmation is None
        assert visit.exact_time is None
        assert visit.death_status is None
        assert visit.absence_reason is None
    assert subject.death_time is None
    assert subject.contact_time is None
    assert subject.prior_clinical_history is None
    assert subject.first_onset_interval is None


def test_private_objects_are_immutable_and_repr_exposes_no_keys_or_path():
    primary, long = selected_fixture()
    subject = build_source_observations(primary, long)[0]
    for obj, field, replacement in (
        (subject, "assignment", "Intervention"),
        (subject.visits[0], "label", "unapproved"),
        (subject.horizon_total, "literal", "Yes"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, replacement)
    rendered = repr(subject) + repr(subject.visits) + repr(subject.horizon_total)
    for forbidden in (
        "synthetic-opaque",
        "opaque_key",
        "opaque_cluster",
        "Baseline",
        "IFG",
        "987654321",
    ):
        assert forbidden not in rendered


def test_unknown_codes_are_sanitized_and_not_promoted_to_clinical_labels():
    unapproved = "unapproved synthetic free text"
    primary, long = selected_fixture(
        categories=(unapproved, "IFG", "NGT"),
        total=unapproved,
        incidence=(unapproved, None),
        medications=(unapproved, None, "No", "No"),
    )
    subjects = build_source_observations(primary, long)
    assert subjects[0].visits[0].glycemia.literal is None
    assert subjects[0].horizon_total.literal is None
    report = public_diagnostics(subjects)
    assert unapproved not in json.dumps(report)
    assert report["visit_marginals"]["Baseline"]["glycemia"] == {"string:uninterpreted_text": 1}
    assert report["visit_marginals"]["24 months"]["incidence_flag"] == {"absent:uninterpreted": 1}


def test_empty_cohort_consistency_is_unassessed_and_not_a_vacuous_pass():
    report = public_diagnostics(())
    assert report["subjects"] == 0
    assert report["nominal_rows"] == 0
    assert report["ada_category_and_flag_agree_where_both_interpretable"] is None
    assert report["later_two_hour_storage_absent_after_earlier_ada_positive_compatible"] is None
    assert report["unlabeled_observation_pattern_cell_size_histogram"] == {}
    assert all(value == 0 for value in report["incidence_flag_algebra"].values())
    assert report["clinical_fit_allowed"] is False


@pytest.mark.parametrize(
    "code", [ABSENT, ("string", "unapproved synthetic label"), ("number", "765432198")]
)
def test_uninterpretable_ada_observations_do_not_manufacture_consistency(code):
    primary, long = selected_fixture(incidence=(None, None), total=None)
    for index, row in enumerate(long):
        for field in ("glycemiaADA", "diabADA"):
            row[field] = code
            primary[0][f"{field}{index}"] = code
    subjects = build_source_observations(primary, long)
    assert not any(visit.prior_ada_positive_evidence for visit in subjects[0].visits)
    report = public_diagnostics(subjects)
    assert report["subjects"] == 1
    assert report["nominal_rows"] == 3
    assert report["ada_category_and_flag_agree_where_both_interpretable"] is None
    assert report["later_two_hour_storage_absent_after_earlier_ada_positive_compatible"] is None
    assert "765432198" not in json.dumps(report)
    assert "unapproved synthetic label" not in json.dumps(report)


def test_scalar_flag_algebra_preserves_unknowns_without_joint_cell_table():
    combinations = [
        (("Yes", "Yes"), "No"),
        (("No", "No"), "Yes"),
        (("Yes", None), None),
        (("No", "No"), "No"),
        (("No", "Yes"), "Yes"),
        ((None, None), "No"),
    ]
    primary, long = [], []
    for index, (incidence, total) in enumerate(combinations):
        wide, rows = selected_fixture(("number", str(index)), incidence=incidence, total=total)
        primary.extend(wide)
        long.extend(rows)
    report = public_diagnostics(build_source_observations(primary, long))
    assert report["subjects"] == 6
    assert report["nominal_rows"] == 18
    assert report["incidence_flag_algebra"] == {
        "fully_interpretable_triples": 4,
        "suffix_positive_union": 3,
        "suffix_positive_overlap": 1,
        "total_negative_with_positive_suffix": 1,
        "total_positive_with_both_suffixes_negative": 1,
        "unknown_total_with_positive_suffix": 1,
    }
    assert report["visit_marginals"]["12 months"]["incidence_flag"] == {
        "absent:uninterpreted": 1,
        "string:No": 3,
        "string:Yes": 2,
    }


def test_public_output_has_only_approved_aggregates_and_histogram_conserves_every_subject():
    primary, long = selected_fixture(("number", "1"))
    wide, rows = selected_fixture(("string", "1"))
    primary.extend(wide)
    long.extend(rows)
    wide, rows = selected_fixture(
        ("string", "different-synthetic-key"), categories=("NGT", "NGT", None)
    )
    primary.extend(wide)
    long.extend(rows)
    report = public_diagnostics(build_source_observations(primary, long))
    histogram = report["unlabeled_observation_pattern_cell_size_histogram"]
    assert histogram == {1: 1, 2: 1}
    assert sum(histogram.values()) == 2
    assert sum(size * cells for size, cells in histogram.items()) == report["subjects"] == 3
    assert set(report) == {
        "subjects",
        "nominal_rows",
        "assignment_marginal",
        "horizon_total_marginal",
        "visit_marginals",
        "incidence_flag_algebra",
        "ada_category_and_flag_agree_where_both_interpretable",
        "later_two_hour_storage_absent_after_earlier_ada_positive_compatible",
        "unlabeled_observation_pattern_cell_size_histogram",
        "individual_death_contact_confirmation_and_first_onset_unknown",
        "clinical_fit_allowed",
        "engine_activation_allowed",
        "independent_validation_allowed",
        "scientific_release_ready",
    }
    serialized = json.dumps(report)
    for forbidden in (
        "synthetic-opaque",
        "different-synthetic-key",
        "987654321",
        "876543219",
        "opaque_key",
        "opaque_cluster",
        "SourceSubject",
        "NominalSourceVisit",
        "aggregate_paths",
        "seen_positive_suffix_evidence",
        "prior_ada_positive_evidence",
    ):
        assert forbidden not in serialized
    for gate in (
        "clinical_fit_allowed",
        "engine_activation_allowed",
        "independent_validation_allowed",
        "scientific_release_ready",
    ):
        assert report[gate] is False
