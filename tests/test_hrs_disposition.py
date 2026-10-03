"""Synthetic conservation/refusal tests; no HRS records or clinical estimates."""

import copy
import itertools
import json

import pytest

from demeter.analysis.hrs_disposition import reconcile_dispositions


def run(baseline=(), tracker=(), diagnosis=(), assays=(), **kwargs):
    return reconcile_dispositions(
        baseline, tracker, diagnosis, assays, synthetic_only=kwargs.get("synthetic_only", True)
    )


def diagnosis(key, wave="2016", response=1, universe="unknown"):
    return {"person_id": key, "wave": wave, "response": response, "universe": universe}


def assay(key, wave="2016", selected=True, availability="available", clock="unknown"):
    return {
        "person_id": key,
        "wave": wave,
        "selected": selected,
        "availability": availability,
        "clock": clock,
    }


def marginals(result):
    yield result["tracker_2016_palive"]
    for wave in ("2012", "2016"):
        yield from result["diagnosis_reports"][wave].values()
        yield from result["synthetic_assay_facets"][wave].values()


def test_empty_cohort_returns_zero_counts_without_empirical_claim():
    result = run()
    assert result["cohort_empty"]
    assert result["baseline_count"] == 0
    assert all(set(m.values()) == {0} for m in marginals(result))
    assert result["conservation"]["every_marginal_uses_declared_baseline"]
    assert not any(result["scientific_gates"].values())
    assert not result["interpretation"]["source_audit_passed"]
    assert not result["interpretation"]["empirical_processing_authorized"]
    assert not result["interpretation"]["synthetic_origin_independently_verified"]


def test_unobserved_followup_never_disappears_or_becomes_survival():
    result = run(["a", "b", "c"])
    assert result["tracker_2016_palive"]["no_tracker_observation"] == 3
    assert result["tracker_2016_palive"]["alive_report"] == 0
    assert result["tracker_2016_palive"]["presumed_alive"] == 0
    for wave in ("2012", "2016"):
        assert result["diagnosis_reports"][wave]["response"]["no_diagnosis_record"] == 3
        assert result["synthetic_assay_facets"][wave]["availability"]["no_assay_record"] == 3
    assert all(sum(m.values()) == 3 for m in marginals(result))


def test_observed_blank_and_absent_tracker_row_are_different():
    result = run(["blank", "absent"], [{"person_id": "blank", "palive": None}])
    counts = result["tracker_2016_palive"]
    assert counts["not_in_sample"] == counts["no_tracker_observation"] == 1
    assert not result["interpretation"]["missing_tracker_row_is_observed_native_blank"]


def test_exhaustive_two_person_tracker_accounting_against_independent_oracle():
    states = (1, 2, 5, 6, None, "absent")
    labels = (
        "alive_report",
        "presumed_alive",
        "deceased_this_wave_report",
        "deceased_prior_wave_report",
        "not_in_sample",
        "no_tracker_observation",
    )
    for first, second in itertools.product(range(len(states)), repeat=2):
        rows = [
            {"person_id": key, "palive": states[index]}
            for key, index in zip(("a", "b"), (first, second), strict=True)
            if states[index] != "absent"
        ]
        result = run(["a", "b"], rows)
        expected = {label: int(first == i) + int(second == i) for i, label in enumerate(labels)}
        assert result["tracker_2016_palive"] == expected
        assert all(sum(m.values()) == 2 and min(m.values()) >= 0 for m in marginals(result))


def test_all_diagnosis_codes_and_missing_rows_reconcile_without_latent_mapping():
    codes = (1, 3, 4, 5, 8, 9, None, "absent")
    labels = (
        "affirmative_report",
        "disputed_prior_record_now_condition",
        "disputed_prior_record_now_no_condition",
        "negative_report",
        "unknown_or_not_ascertained",
        "refused",
        "inapplicable_or_partial",
        "no_diagnosis_record",
    )
    for a, b in itertools.product(range(len(codes)), repeat=2):
        rows = [
            diagnosis(key, response=codes[i])
            for key, i in zip(("a", "b"), (a, b), strict=True)
            if codes[i] != "absent"
        ]
        result = run(["a", "b"], diagnosis=rows)
        expected = {label: int(a == i) + int(b == i) for i, label in enumerate(labels)}
        assert result["diagnosis_reports"]["2016"]["response"] == expected
        assert all(sum(m.values()) == 2 for m in marginals(result))
        assert not result["interpretation"]["diabetes_type_identified"]
        assert not result["interpretation"]["remission_identified"]


def test_affirmative_code_does_not_identify_ever_or_carried_or_since_universe():
    rows = [
        diagnosis("a", universe="ever_prompt"),
        diagnosis("b", universe="prior_record_prompt"),
        diagnosis("c", universe="since_last_interview_prompt"),
        diagnosis("d", universe="unknown"),
    ]
    result = run(["a", "b", "c", "d"], diagnosis=rows)
    group = result["diagnosis_reports"]["2016"]
    assert group["response"]["affirmative_report"] == 4
    assert group["universe"] == {
        "ever_prompt": 1,
        "prior_record_prompt": 1,
        "since_last_interview_prompt": 1,
        "unknown": 1,
        "no_diagnosis_record": 0,
    }


def test_disputed_or_negative_later_report_does_not_erase_prior_observation():
    for later in (3, 4, 5, 8, 9, None):
        result = run(
            ["a"],
            diagnosis=[
                diagnosis("a", "2012", 1, "ever_prompt"),
                diagnosis("a", "2016", later, "prior_record_prompt"),
            ],
        )
        assert result["diagnosis_reports"]["2012"]["response"]["affirmative_report"] == 1
        assert sum(result["diagnosis_reports"]["2016"]["response"].values()) == 1
        assert not result["interpretation"]["diagnosis_history_erased"]
        assert not result["interpretation"]["remission_identified"]


def test_death_and_assay_coexist_without_unverified_temporal_priority():
    result = run(
        ["a", "b"],
        [{"person_id": "a", "palive": 5}, {"person_id": "b", "palive": 6}],
        assays=[assay("a"), assay("b", clock="nominal_wave_only")],
    )
    assert result["tracker_2016_palive"]["deceased_this_wave_report"] == 1
    assert result["tracker_2016_palive"]["deceased_prior_wave_report"] == 1
    assert result["synthetic_assay_facets"]["2016"]["availability"]["available"] == 2
    assert not result["interpretation"]["independent_death_ascertainment"]
    assert not result["interpretation"]["specimen_interval_identified"]
    assert not result["interpretation"]["nominal_wave_is_elapsed_time"]


def test_every_valid_two_person_assay_completion_conserves_all_facets():
    options = [
        (s, a, c)
        for s, a, c in itertools.product(
            (True, False, None),
            ("available", "missing", "unknown"),
            ("unknown", "nominal_wave_only"),
        )
        if not (s is False and a == "available")
    ]
    options.append(None)
    for first, second in itertools.product(options, repeat=2):
        rows = [
            assay(key, selected=x[0], availability=x[1], clock=x[2])
            for key, x in zip(("a", "b"), (first, second), strict=True)
            if x is not None
        ]
        result = run(["a", "b"], assays=rows)
        observed = int(first is not None) + int(second is not None)
        group = result["synthetic_assay_facets"]["2016"]
        assert all(counts["no_assay_record"] == 2 - observed for counts in group.values())
        assert all(sum(m.values()) == 2 for m in marginals(result))
        assert group["availability"]["available"] == sum(
            x is not None and x[1] == "available" for x in (first, second)
        )


def test_leading_zero_keys_distinct_inputs_unchanged_order_irrelevant_and_output_private():
    inputs = (
        ["001", "1"],
        [{"person_id": "001", "palive": 1}],
        [diagnosis("1", response=9)],
        [assay("001", availability="missing")],
    )
    snapshot = copy.deepcopy(inputs)
    result = run(*inputs)
    assert inputs == snapshot
    assert result == run(*(list(reversed(part)) for part in inputs))
    assert result["baseline_count"] == 2
    serialized = json.dumps(result)
    assert '"001"' not in serialized and '"1"' not in serialized
    assert "person_id" not in serialized
    assert "aggregate_paths" not in serialized
    assert not result["interpretation"]["joint_histories_exported"]
    result["tracker_2016_palive"]["alive_report"] = 999
    assert run(*inputs)["tracker_2016_palive"]["alive_report"] == 1


@pytest.mark.parametrize("declaration", [False, None, 1, 0, "True"])
def test_synthetic_declaration_requires_explicit_boolean_true(declaration):
    with pytest.raises(ValueError, match="explicit synthetic_only"):
        run(synthetic_only=declaration)


def test_omitted_synthetic_declaration_is_not_implicitly_authorized():
    with pytest.raises(TypeError):
        reconcile_dispositions([], [], [], [])


@pytest.mark.parametrize("keys", [["a", "a"], [1], [True], [None], [""], [" a"], ["a "]])
def test_invalid_baseline_identity_refused_without_key_leak(keys):
    with pytest.raises(ValueError):
        run(keys)


@pytest.mark.parametrize(
    "records",
    [
        ({"person_id": "secret-person", "palive": 1},),
        (),
    ],
)
def test_orphan_empty_cohort_or_valid_empty_tracker(records):
    if records:
        with pytest.raises(ValueError) as exc:
            run([], records)
        assert "secret-person" not in str(exc.value)
    else:
        assert run([], records)["cohort_empty"]


@pytest.mark.parametrize("facet", ["tracker", "diagnosis", "assay"])
def test_duplicate_identical_and_conflicting_records_refused(facet):
    row = {
        "tracker": {"person_id": "secret-person", "palive": 1},
        "diagnosis": diagnosis("secret-person"),
        "assay": assay("secret-person"),
    }[facet]
    args = (
        {"tracker": [row, dict(row)]}
        if facet == "tracker"
        else {"diagnosis" if facet == "diagnosis" else "assays": [row, dict(row)]}
    )
    with pytest.raises(ValueError, match="Duplicate") as exc:
        run(["secret-person"], **args)
    assert "secret-person" not in str(exc.value)
    different = dict(row)
    different[{"tracker": "palive", "diagnosis": "response", "assay": "clock"}[facet]] = {
        "tracker": 2,
        "diagnosis": 9,
        "assay": "nominal_wave_only",
    }[facet]
    args[next(iter(args))][1] = different
    with pytest.raises(ValueError, match="Duplicate"):
        run(["secret-person"], **args)


@pytest.mark.parametrize("code", [True, False, 1.0, "1", 0, 3, 4, 8, 9])
def test_undocumented_tracker_codes_are_not_generalized_to_other_waves(code):
    with pytest.raises(ValueError):
        run(["a"], [{"person_id": "a", "palive": code}])


@pytest.mark.parametrize("code", [True, False, 1.0, "1", 0, 2, 6, 7])
def test_bad_diagnosis_response_codes_refused(code):
    with pytest.raises(ValueError):
        run(["a"], diagnosis=[diagnosis("a", response=code)])


@pytest.mark.parametrize(
    "change",
    [
        {"wave": 2016},
        {"wave": "2014"},
        {"wave": "4 years"},
        {"universe": "confirmed_diagnosis"},
        {"person_id": "orphan"},
    ],
)
def test_bad_diagnosis_inventory_or_orphan_refused(change):
    with pytest.raises(ValueError):
        run(["a"], diagnosis=[{**diagnosis("a"), **change}])


@pytest.mark.parametrize(
    "change",
    [
        {"selected": 1},
        {"selected": 0},
        {"selected": "unknown"},
        {"selected": False},
        {"availability": "normal_glycemia"},
        {"clock": "2016-01-01"},
        {"clock": 4},
        {"wave": "2018"},
        {"person_id": "orphan"},
    ],
)
def test_assay_conflicts_unsupported_clock_or_clinical_tokens_refused(change):
    with pytest.raises(ValueError):
        run(["a"], assays=[{**assay("a"), **change}])


@pytest.mark.parametrize("facet", ["tracker", "diagnosis", "assays"])
def test_added_private_or_undocumented_fields_refused_without_echo(facet):
    row = {
        "tracker": {"person_id": "a", "palive": 1},
        "diagnosis": diagnosis("a"),
        "assays": assay("a"),
    }[facet]
    row["private-secret-assay"] = "secret-value"
    with pytest.raises(ValueError) as exc:
        run(["a"], **{facet: [row]})
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize("part", range(4))
def test_string_or_mapping_cannot_be_silently_iterated_as_record_sequence(part):
    inputs = [[], [], [], []]
    inputs[part] = "a" if part == 0 else {}
    with pytest.raises(ValueError):
        run(*inputs)
