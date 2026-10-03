"""Synthetic categorical witnesses only; no participant intake or prevalence."""

from itertools import product

import pytest

from demeter.data.nhis_diagnosis_labels import (
    CATEGORIES,
    classify_reported_diabetes,
    partition_reported_diabetes,
)


DIAGNOSIS_CODES = ("", " ", "1", "2", "7", "8", "9")
TYPE_CODES = ("", " ", "1", "2", "3", "7", "8", "9")
GATES = {
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
}


@pytest.mark.parametrize("diagnosis,diabetes_type", list(product(DIAGNOSIS_CODES, TYPE_CODES)))
def test_entire_documented_code_product_retains_universe(diagnosis, diabetes_type):
    result = classify_reported_diabetes(diagnosis, diabetes_type)
    if diagnosis != "1" and diabetes_type not in ("", " "):
        assert result == "inconsistent_type_universe"
    elif diagnosis == "1" and diabetes_type in ("1", "2", "3"):
        assert (
            result
            == {
                "1": "reported_type1",
                "2": "reported_type2",
                "3": "reported_other_diabetes",
            }[diabetes_type]
        )
    elif diagnosis == "1":
        assert result == "reported_diabetes_type_unknown"
    elif diagnosis == "2":
        assert result == "no_reported_diabetes"
    else:
        assert result == "diagnosis_unknown"


def test_missing_no_and_each_type_are_distinct_and_conserved():
    records = [("2", ""), ("1", "1"), ("1", "2"), ("1", "3"), ("1", "9"), ("9", ""), ("2", "2")]
    result = partition_reported_diabetes(records)
    assert result["category_counts"] == dict.fromkeys(CATEGORIES, 1)
    assert result["total_records"] == 7
    assert result["ledger_conserved"] is True


def test_complete_product_partition_conserves_unknowns_and_contradictions():
    result = partition_reported_diabetes(product(DIAGNOSIS_CODES, TYPE_CODES))
    assert result["category_counts"] == {
        "no_reported_diabetes": 2,
        "reported_type1": 1,
        "reported_type2": 1,
        "reported_other_diabetes": 1,
        "reported_diabetes_type_unknown": 5,
        "diagnosis_unknown": 10,
        "inconsistent_type_universe": 36,
    }
    assert result["total_records"] == len(DIAGNOSIS_CODES) * len(TYPE_CODES)
    assert result["ledger_conserved"] is True


def test_contradictory_positive_and_unknown_type_responses_never_disappear():
    rows = list(product(("", " ", "2", "7", "8", "9"), ("1", "2", "3", "7", "8", "9")))
    result = partition_reported_diabetes(rows)
    assert result["category_counts"]["inconsistent_type_universe"] == len(rows)
    assert sum(result["category_counts"].values()) == len(rows)
    assert result["total_records"] == len(rows)


def test_generator_single_pass_and_empty_input_keep_complete_zero_categories():
    seen = []

    def records():
        for pair in (("1", "2"), ("1", "2"), ("2", "")):
            seen.append(True)
            yield pair

    result = partition_reported_diabetes(records())
    assert len(seen) == 3
    assert result["total_records"] == 3
    assert result["category_counts"]["reported_type2"] == 2
    empty = partition_reported_diabetes(iter(()))
    assert empty["category_counts"] == dict.fromkeys(CATEGORIES, 0)
    assert empty["total_records"] == 0
    assert empty["ledger_conserved"] is True


@pytest.mark.parametrize("token", [None, True, False, 1, 2.0, b"1", [], {}, object()])
@pytest.mark.parametrize("field", ["diagnosis", "diabetes_type"])
def test_no_numeric_boolean_or_other_token_coercion(token, field):
    args = {"diagnosis": "1", "diabetes_type": "2", field: token}
    with pytest.raises(ValueError, match="exact string tokens"):
        classify_reported_diabetes(**args)


class StringSubclass(str):
    pass


def test_exact_native_string_required_not_custom_string_subclass():
    with pytest.raises(ValueError, match="exact string tokens"):
        classify_reported_diabetes(StringSubclass("1"), "2")


@pytest.mark.parametrize(
    "token",
    [
        "0",
        "4",
        "6",
        ".",
        "01",
        "1.0",
        " 1",
        "1 ",
        "  ",
        "\t",
        "\n",
        "\r",
        "\u00a0",
        "\uff12",
        "Type 2",
        "private-token",
    ],
)
@pytest.mark.parametrize("field", ["diagnosis", "diabetes_type"])
def test_unlisted_codes_syntax_and_normalization_refused_without_echo(token, field):
    args = {"diagnosis": "1", "diabetes_type": "2", field: token}
    with pytest.raises(ValueError) as error:
        classify_reported_diabetes(**args)
    assert str(error.value) == "Diagnosis/type code or syntax is unsupported"
    assert "private-token" not in str(error.value)


@pytest.mark.parametrize("value", [None, True, 1, 2.0, "", b"", bytearray(), {}, {"1": "2"}])
def test_invalid_outer_scalars_and_mapping_refused_including_empty(value):
    with pytest.raises(ValueError, match="pair iterable"):
        partition_reported_diabetes(value)


@pytest.mark.parametrize(
    "row",
    [
        None,
        "12",
        {"diagnosis": "1", "type": "2"},
        (),
        ("1",),
        ("1", "2", "extra"),
        ["1"],
        (x for x in ("1", "2")),
    ],
)
def test_invalid_pair_shapes_refuse_without_partial_ledger(row):
    with pytest.raises(ValueError, match="exactly two codes"):
        partition_reported_diabetes([("1", "2"), row])


def test_iteration_failure_sanitized_instead_of_returning_partial_coverage():
    def failed():
        yield ("1", "2")
        raise RuntimeError("private-record-detail")

    with pytest.raises(ValueError) as error:
        partition_reported_diabetes(failed())
    assert str(error.value) == "Diagnosis/type pair iteration failed"
    assert error.value.__suppress_context__ is True


def test_results_are_independent_private_validation_witnesses_with_closed_gates():
    first = partition_reported_diabetes([["1", "2"]])
    assert first["validation_only"] is True and first["software_witness"] is True
    assert first["private_aggregate"] is True
    assert set(first["scientific_gates"]) == GATES
    assert all(value is False for value in first["scientific_gates"].values())
    assert set(first) == {
        "kind",
        "category_counts",
        "total_records",
        "ledger_conserved",
        "validation_only",
        "software_witness",
        "private_aggregate",
        "scientific_gates",
    }
    first["scientific_gates"]["clinical_fit_allowed"] = True
    first["category_counts"]["reported_type2"] = 0
    second = partition_reported_diabetes([("1", "2")])
    assert second["scientific_gates"]["clinical_fit_allowed"] is False
    assert second["category_counts"]["reported_type2"] == 1


def test_insulin_age_and_unlisted_diagnosis_code_cannot_supply_type():
    assert classify_reported_diabetes("1", "") == "reported_diabetes_type_unknown"
    with pytest.raises(TypeError):
        classify_reported_diabetes("1", "", insulin="1", age="70")
    with pytest.raises(ValueError, match="unsupported"):
        classify_reported_diabetes("3", "")
