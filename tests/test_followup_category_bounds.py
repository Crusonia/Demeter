"""Independent finite-cohort completion enumeration; no empirical parameters."""

from fractions import Fraction
from itertools import product

import pytest

from demeter.analysis.followup_category_bounds import followup_category_bounds


def rational(value):
    return Fraction(value["numerator"], value["denominator"])


def completed_tables(counts, deaths, untraced):
    """Enumerate full integer allocations, not the coordinate-bound equations."""
    result = []
    for allocation in product(range(untraced + 1), repeat=len(counts) + 1):
        if sum(allocation) != untraced:
            continue
        categories = tuple(count + allocation[index] for index, count in enumerate(counts))
        result.append((categories, deaths + allocation[-1], sum(categories), allocation))
    return result


def assert_fraction_bounds(actual, possibilities):
    if not possibilities:
        assert actual is None
    else:
        assert rational(actual["lower"]) == min(possibilities)
        assert rational(actual["upper"]) == max(possibilities)


@pytest.mark.parametrize("category_count", [1, 2, 3])
def test_sharp_coordinate_and_alive_bounds_against_full_small_cohort_enumeration(category_count):
    names = tuple(f"category_{index}" for index in range(category_count))
    for counts in product(range(6), repeat=category_count):
        for deaths, untraced in product(range(6), repeat=2):
            n = sum(counts) + deaths + untraced
            if n > 5:
                continue
            tables = completed_tables(counts, deaths, untraced)
            assert tables
            actual = followup_category_bounds(
                n, dict(zip(names, counts, strict=True)), deaths, untraced
            )
            assert all(sum(row[0]) + row[1] == n for row in tables)
            assert all(sum(row[3]) == untraced for row in tables)
            alive = [row[2] for row in tables]
            assert actual["completion_count_bounds"]["alive_count"] == {
                "lower": min(alive),
                "upper": max(alive),
            }
            actual_survivor = actual["survivor_conditional"]
            assert actual_survivor["positive_alive_count_feasible"] is any(
                value > 0 for value in alive
            )
            assert actual_survivor["positive_alive_count_guaranteed"] is all(
                value > 0 for value in alive
            )
            assert actual_survivor["bounds_conditioned_on_positive_alive_count"] is (
                any(value > 0 for value in alive) and not all(value > 0 for value in alive)
            )
            positive_alive = [value for value in alive if value > 0]
            assert actual_survivor["positive_alive_count_bounds"] == (
                {"lower": min(positive_alive), "upper": max(positive_alive)}
                if positive_alive
                else None
            )
            for index, name in enumerate(names):
                possible_counts = [row[0][index] for row in tables]
                assert actual["completion_count_bounds"]["category_counts"][name] == {
                    "lower": min(possible_counts),
                    "upper": max(possible_counts),
                }
                assert_fraction_bounds(
                    actual["all_assigned"]["category_fraction_bounds"][name],
                    [Fraction(count, n) for count in possible_counts] if n else [],
                )
                assert_fraction_bounds(
                    actual_survivor["category_fraction_bounds"][name],
                    [Fraction(row[0][index], row[2]) for row in tables if row[2]],
                )
            death_counts = [row[1] for row in tables]
            assert actual["completion_count_bounds"]["death_count"] == {
                "lower": min(death_counts),
                "upper": max(death_counts),
            }
            assert_fraction_bounds(
                actual["all_assigned"]["death_fraction_bounds"],
                [Fraction(count, n) for count in death_counts] if n else [],
            )


def test_coordinate_extrema_are_not_an_independent_joint_table():
    actual = followup_category_bounds(5, {"first": 1, "second": 1}, 1, 2)
    upper = actual["completion_count_bounds"]
    assert (
        sum(row["upper"] for row in upper["category_counts"].values())
        + upper["death_count"]["upper"]
        > 5
    )
    assert actual["joint_completion_constraint"]["coordinate_extrema_are_coupled"] is True
    assert (
        actual["joint_completion_constraint"]["all_coordinate_extrema_jointly_attainable_claimed"]
        is False
    )
    survivor = actual["survivor_conditional"]["category_fraction_bounds"]
    assert rational(survivor["first"]["upper"]) + rational(survivor["second"]["upper"]) > 1
    tables = completed_tables((1, 1), 1, 2)
    assert all(sum(Fraction(count, row[2]) for count in row[0]) == 1 for row in tables)


def test_untraced_are_not_automatically_alive_or_dead():
    actual = followup_category_bounds(6, {"first": 1, "second": 2}, 1, 2)
    assert actual["completion_count_bounds"]["alive_count"] == {"lower": 3, "upper": 5}
    assert actual["completion_count_bounds"]["death_count"] == {"lower": 1, "upper": 3}
    assert actual["counts"]["untraced"] == 2
    assert actual["assumptions"]["untraced_people_imputed_alive_or_dead"] is False
    assert actual["assumptions"]["independent_missingness_assumed"] is False


def test_all_untraced_survivor_fractions_are_conditional_not_guaranteed():
    actual = followup_category_bounds(3, {"first": 0, "second": 0}, 0, 3)
    survivor = actual["survivor_conditional"]
    assert survivor["positive_alive_count_feasible"] is True
    assert survivor["positive_alive_count_guaranteed"] is False
    assert survivor["bounds_conditioned_on_positive_alive_count"] is True
    assert survivor["alive_count_bounds"] == {"lower": 0, "upper": 3}
    assert survivor["positive_alive_count_bounds"] == {"lower": 1, "upper": 3}
    for bound in survivor["category_fraction_bounds"].values():
        assert rational(bound["lower"]) == 0
        assert rational(bound["upper"]) == 1


@pytest.mark.parametrize("known,untraced", [(2, 0), (2, 3), (0, 3)])
def test_one_exhaustive_category_has_fraction_one_for_any_positive_alive_completion(
    known, untraced
):
    actual = followup_category_bounds(known + 1 + untraced, {"only": known}, 1, untraced)
    bounds = actual["survivor_conditional"]["category_fraction_bounds"]["only"]
    assert rational(bounds["lower"]) == rational(bounds["upper"]) == 1


@pytest.mark.parametrize("deaths", [0, 4])
def test_empty_and_all_dead_cohorts_have_null_survivor_ratios(deaths):
    actual = followup_category_bounds(deaths, {"first": 0, "second": 0}, deaths, 0)
    assert actual["survivor_conditional"]["positive_alive_count_feasible"] is False
    assert actual["survivor_conditional"]["positive_alive_count_guaranteed"] is False
    assert actual["survivor_conditional"]["bounds_conditioned_on_positive_alive_count"] is False
    assert actual["survivor_conditional"]["positive_alive_count_bounds"] is None
    assert all(
        value is None
        for value in actual["survivor_conditional"]["category_fraction_bounds"].values()
    )
    if not deaths:
        assert actual["all_assigned"]["death_fraction_bounds"] is None
        assert all(
            value is None for value in actual["all_assigned"]["category_fraction_bounds"].values()
        )
    else:
        assert rational(actual["all_assigned"]["death_fraction_bounds"]["lower"]) == 1


def test_no_untraced_completion_keeps_exact_observed_fractions():
    actual = followup_category_bounds(5, {"first": 1, "second": 2}, 2, 0)
    for label, count in (("first", 1), ("second", 2)):
        bounds = actual["survivor_conditional"]["category_fraction_bounds"][label]
        assert rational(bounds["lower"]) == rational(bounds["upper"]) == Fraction(count, 3)
        assigned = actual["all_assigned"]["category_fraction_bounds"][label]
        assert rational(assigned["lower"]) == rational(assigned["upper"]) == Fraction(count, 5)


def test_huge_counts_preserve_exact_rationals_and_display_underflow_without_overflow():
    n = 10**400
    actual = followup_category_bounds(n, {"first": 1, "second": n - 1}, 0, 0)
    lower = actual["all_assigned"]["category_fraction_bounds"]["first"]["lower"]
    assert rational(lower) == Fraction(1, n)
    assert lower["display_fraction"] == 0
    assert lower["display_underflow"] is True


@pytest.mark.parametrize("position", range(4))
@pytest.mark.parametrize("value", [True, 1.0, "1", -1, None])
def test_count_types_and_nonnegativity_are_strict(position, value):
    n, count, deaths, untraced = [4, 2, 1, 1]
    counts = [n, count, deaths, untraced]
    counts[position] = value
    with pytest.raises(ValueError):
        followup_category_bounds(counts[0], {"first": counts[1]}, counts[2], counts[3])


@pytest.mark.parametrize(
    "keys",
    [
        {},
        [],
        [("first", 1)],
        {True: 1},
        {1: 1},
        {1.0: 1},
        {None: 1},
        {"": 1},
        {" ": 1},
        {"first ": 1},
        {" first": 1},
    ],
)
def test_category_dictionary_and_keys_cannot_be_coerced(keys):
    with pytest.raises(ValueError):
        followup_category_bounds(1, keys, 0, 0)


@pytest.mark.parametrize(
    "label",
    ["death", "deaths", "dead", "Death", "confirmed_deaths", "confirmed deaths", "untraced"],
)
def test_alive_categories_cannot_collide_with_death_or_untraced_dispositions(label):
    with pytest.raises(ValueError, match="collide"):
        followup_category_bounds(1, {label: 1}, 0, 0)


@pytest.mark.parametrize("n", [0, 2, 4])
def test_inconsistent_partition_totals_fail(n):
    with pytest.raises(ValueError, match="conserve"):
        followup_category_bounds(n, {"first": 1}, 1, 1)


def test_results_snapshot_caller_counts_without_aliases_or_clinical_claims():
    counts = {"second": 2, "first": 1}
    actual = followup_category_bounds(5, counts, 1, 1)
    counts["first"] = 100
    assert actual["counts"]["observed_category_counts"] == {"first": 1, "second": 2}
    actual["completion_count_bounds"]["alive_count"]["lower"] = 99
    assert actual["survivor_conditional"]["alive_count_bounds"]["lower"] == 3
    interpretation = actual["interpretation"]
    assert interpretation["count_unit"] == "people"
    assert interpretation["fraction_unit"] == "dimensionless"
    assert interpretation["sampling_interval"] is None
    for key in (
        "common_elapsed_horizon_assumed",
        "cumulative_diagnosis_endpoint",
        "metabolic_health_mapping_inferred",
        "clinical_transition_hazards_identified",
        "iid_sampling_assumed",
        "causal_effect_identified",
        "diet_effect_identified",
        "engine_activation_allowed",
    ):
        assert interpretation[key] is False
