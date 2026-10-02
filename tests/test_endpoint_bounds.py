"""Synthetic finite-cohort completions, with no source records or empirical fit."""

from fractions import Fraction
from itertools import product

import pytest

from demeter.analysis.endpoint_bounds import (
    endpoint_bounds,
    endpoint_difference_bounds,
    endpoint_tipping_point,
)


def rational(value):
    return Fraction(value["numerator"], value["denominator"])


def completions(n, known, events, deaths):
    """Enumerate integer contingency tables, independently of bound formulas."""
    no, unknown = known - events, n - known
    result = []
    for event_dead, no_dead, unknown_dead in product(
        range(events + 1), range(no + 1), range(unknown + 1)
    ):
        if event_dead + no_dead + unknown_dead != deaths:
            continue
        for unknown_alive_event, unknown_dead_event in product(
            range(unknown - unknown_dead + 1), range(unknown_dead + 1)
        ):
            result.append(
                (
                    events + unknown_alive_event + unknown_dead_event,
                    events - event_dead + unknown_alive_event,
                    (event_dead, no_dead, unknown_dead),
                )
            )
    return result


def test_sharp_single_cohort_bounds_and_coupled_allocations_exhaustive():
    for n in range(7):
        for known in range(n + 1):
            for events in range(known + 1):
                for deaths in range(n + 1):
                    tables = completions(n, known, events, deaths)
                    assert tables
                    actual = endpoint_bounds(
                        n, known, events, cumulative_deaths=deaths, assume_complete_deaths=True
                    )
                    for key, index in (("all_assigned", 0), ("survivor_conditional", 1)):
                        counts = [row[index] for row in tables]
                        assert actual[key]["event_count_bounds"] == {
                            "lower": min(counts),
                            "upper": max(counts),
                        }
                        denominator = n if index == 0 else n - deaths
                        assert actual[key]["denominator"] == denominator
                        fractions = actual[key]["event_fraction_bounds"]
                        if denominator == 0:
                            assert fractions is None
                        else:
                            assert rational(fractions["lower"]) == Fraction(
                                min(counts), denominator
                            )
                            assert rational(fractions["upper"]) == Fraction(
                                max(counts), denominator
                            )
                    allocation = actual["unlinked_death_allocation"]
                    for index, key in enumerate(
                        ("known_event", "known_non_event", "unknown_endpoint")
                    ):
                        counts = [row[2][index] for row in tables]
                        assert allocation["death_count_bounds"][key] == {
                            "lower": min(counts),
                            "upper": max(counts),
                        }
                    assert allocation["components_coupled"] is True
                    assert all(sum(row[2]) == deaths for row in tables)


def test_death_fact_does_not_reduce_unknowns_or_assume_complete_survivors():
    ordinary = endpoint_bounds(6, 4, 2)
    reported = endpoint_bounds(6, 4, 2, cumulative_deaths=2)
    assert reported["all_assigned"] == ordinary["all_assigned"]
    assert reported["counts"]["unknown_endpoints"] == 2
    assert reported["survivor_conditional"] is None
    assert reported["unlinked_death_allocation"] is None
    assert reported["assumptions"]["complete_same_cohort_death_total_assumed"] is False


def test_known_event_before_death_remains_in_all_assigned_estimand():
    actual = endpoint_bounds(4, 4, 2, cumulative_deaths=4, assume_complete_deaths=True)
    assert actual["all_assigned"]["event_count_bounds"] == {"lower": 2, "upper": 2}
    assert rational(actual["all_assigned"]["event_fraction_bounds"]["lower"]) == Fraction(1, 2)
    assert actual["survivor_conditional"]["event_count_bounds"] == {"lower": 0, "upper": 0}
    assert actual["survivor_conditional"]["event_fraction_bounds"] is None


def test_empty_cohorts_have_null_ratios_and_contrasts():
    actual = endpoint_bounds(0, 0, 0, cumulative_deaths=0, assume_complete_deaths=True)
    assert actual["all_assigned"]["event_fraction_bounds"] is None
    assert actual["survivor_conditional"]["event_fraction_bounds"] is None
    difference = endpoint_difference_bounds((0, 0, 0), (2, 1, 1))
    assert difference["all_assigned"] is None
    assert difference["survivor_conditional"] is None
    assert (
        endpoint_tipping_point((0, 0, 0), (2, 1, 1), second_unknown_events=0)["thresholds"] is None
    )


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("value", [True, 2.0, "2", -1, None])
def test_count_types_and_nonnegativity_are_not_coerced(index, value):
    counts = [3, 2, 1]
    counts[index] = value
    with pytest.raises(ValueError):
        endpoint_bounds(*counts)


@pytest.mark.parametrize("counts", [(2, 3, 1), (3, 1, 2)])
def test_impossible_endpoint_counts_rejected(counts):
    with pytest.raises(ValueError):
        endpoint_bounds(*counts)


@pytest.mark.parametrize("deaths", [True, -1, 1.0, "1", 4])
def test_invalid_death_counts_rejected(deaths):
    with pytest.raises(ValueError):
        endpoint_bounds(3, 2, 1, cumulative_deaths=deaths)


@pytest.mark.parametrize("complete", [0, 1, "yes", None])
def test_completeness_assumption_must_be_explicit_boolean(complete):
    with pytest.raises(ValueError):
        endpoint_bounds(3, 2, 1, cumulative_deaths=1, assume_complete_deaths=complete)


def test_complete_deaths_require_supplied_count():
    with pytest.raises(ValueError):
        endpoint_bounds(3, 2, 1, assume_complete_deaths=True)


def test_all_unknown_endpoints_keep_full_finite_cohort_range():
    actual = endpoint_bounds(5, 0, 0)
    assert actual["all_assigned"]["event_count_bounds"] == {"lower": 0, "upper": 5}
    assert actual["interpretation"]["sampling_interval"] is None
    assert actual["interpretation"]["causal_effect_identified"] is False


def test_exact_rational_bounds_survive_display_underflow():
    actual = endpoint_bounds(10**400, 10**400, 1)
    lower = actual["all_assigned"]["event_fraction_bounds"]["lower"]
    assert rational(lower) == Fraction(1, 10**400)
    assert lower["display_fraction"] == 0
    assert lower["display_underflow"] is True


def cohorts(max_n):
    return [
        (n, known, events)
        for n in range(1, max_n + 1)
        for known in range(n + 1)
        for events in range(known + 1)
    ]


def test_two_cohort_all_assigned_differences_are_sharp_exhaustive():
    for first, second in product(cohorts(4), repeat=2):
        possible = [
            Fraction(a, first[0]) - Fraction(b, second[0])
            for a in range(first[2], first[2] + first[0] - first[1] + 1)
            for b in range(second[2], second[2] + second[0] - second[1] + 1)
        ]
        actual = endpoint_difference_bounds(first, second)["all_assigned"]
        assert rational(actual["lower"]) == min(possible)
        assert rational(actual["upper"]) == max(possible)


def test_survivor_contrast_has_distinct_denominators_and_sharp_extremes():
    for first, second in product(cohorts(3), repeat=2):
        for first_deaths, second_deaths in product(range(first[0]), range(second[0])):
            a = completions(*first, first_deaths)
            b = completions(*second, second_deaths)
            possible = [
                Fraction(x[1], first[0] - first_deaths) - Fraction(y[1], second[0] - second_deaths)
                for x, y in product(a, b)
            ]
            actual = endpoint_difference_bounds(
                first,
                second,
                first_deaths=first_deaths,
                second_deaths=second_deaths,
                assume_complete_deaths=True,
            )
            assert rational(actual["survivor_conditional"]["lower"]) == min(possible)
            assert rational(actual["survivor_conditional"]["upper"]) == max(possible)
            assert actual["causal_interpretation"] is False


def test_tipping_points_match_all_integer_unknown_completions_exhaustive():
    for first, second in product(cohorts(4), repeat=2):
        for second_unknown in range(second[0] - second[1] + 1):
            actual = endpoint_tipping_point(first, second, second_unknown_events=second_unknown)
            differences = [
                Fraction(first[2] + x, first[0]) - Fraction(second[2] + second_unknown, second[0])
                for x in range(first[0] - first[1] + 1)
            ]
            for name, predicate in (
                ("nonnegative_difference", lambda x: x >= 0),
                ("positive_difference", lambda x: x > 0),
            ):
                feasible = [index for index, value in enumerate(differences) if predicate(value)]
                threshold = actual["thresholds"][name]
                assert threshold["reachable"] is bool(feasible)
                assert threshold["minimum_first_unknown_events"] == (
                    min(feasible) if feasible else None
                )


def test_equal_fraction_is_not_a_strictly_positive_tipping_point():
    actual = endpoint_tipping_point((8, 6, 2), (4, 4, 1), second_unknown_events=0)
    assert actual["thresholds"]["nonnegative_difference"]["minimum_first_unknown_events"] == 0
    assert actual["thresholds"]["positive_difference"]["minimum_first_unknown_events"] == 1


@pytest.mark.parametrize("second_unknown", [True, -1, 1.0, "1", 2])
def test_invalid_tipping_completion_rejected(second_unknown):
    with pytest.raises(ValueError):
        endpoint_tipping_point((3, 2, 1), (3, 2, 1), second_unknown_events=second_unknown)


@pytest.mark.parametrize("cohort", [(), (2, 1), (2, 1, 0, 0), "210", [2, True, 0]])
def test_contrast_and_tipping_validate_cohort_shape_and_counts(cohort):
    with pytest.raises(ValueError):
        endpoint_difference_bounds(cohort, (3, 2, 1))
    with pytest.raises(ValueError):
        endpoint_tipping_point(cohort, (3, 2, 1), second_unknown_events=0)
