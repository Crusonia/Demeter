"""Independent finite-table enumeration using arbitrary software counts only."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from fractions import Fraction
from itertools import product

import numpy as np
import pytest

from demeter.analysis.paired_remission import paired_remission_bounds


CELLS = ("positive_positive", "positive_failure", "failure_positive", "failure_failure")
COMPONENTS = ("assessed_nonremission", "unassessed", "death")


def _joint_tables(n: int) -> list[tuple[int, int, int, int]]:
    # Direct cell enumeration is deliberately independent of the bound formula.
    return [cells for cells in product(range(n + 1), repeat=4) if sum(cells) == n]


def _matching_tables(tables, a: int, b: int, m: int | None):
    return [
        cells
        for cells in tables
        if cells[0] + cells[1] == a and cells[0] + cells[2] == b and (m is None or cells[0] >= m)
    ]


def _assert_extreme_table(table, n: int, a: int, b: int, candidates):
    cells = tuple(table[key] for key in CELLS)
    assert cells in candidates
    assert sum(cells) == n
    assert cells[0] + cells[1] == a
    assert cells[0] + cells[2] == b
    assert all(type(value) is int and value >= 0 for value in cells)


@pytest.mark.parametrize("n", range(7))
def test_sharp_bounds_and_whole_tables_match_independent_enumeration(n):
    tables = _joint_tables(n)
    for a, b in product(range(n + 1), repeat=2):
        for m in (None, *range(min(a, b) + 2)):
            compatible = _matching_tables(tables, a, b, m)
            if not compatible:
                with pytest.raises(ValueError, match="no feasible joint table"):
                    paired_remission_bounds(n, a, b, m)
                continue
            result = paired_remission_bounds(n, a, b, m)
            for index, key in enumerate(CELLS):
                values = [cells[index] for cells in compatible]
                assert result["joint_cell_bounds"][key] == {
                    "lower": min(values),
                    "upper": max(values),
                }
            assert result["feasible_positive_pair"] == result["joint_cell_bounds"][CELLS[0]]
            extremes = result["extreme_tables"]
            for table in extremes.values():
                _assert_extreme_table(table, n, a, b, compatible)
            assert extremes["at_lower_positive_pair"][CELLS[0]] == min(c[0] for c in compatible)
            assert extremes["at_upper_positive_pair"][CELLS[0]] == max(c[0] for c in compatible)
            shares = result["first_positive_conditional_shares"]
            assert shares["denominator_n"] == a
            if a == 0:
                assert shares["positive"] is None and shares["primary_failure"] is None
            else:
                for label, index in (("positive", 0), ("primary_failure", 1)):
                    observed_ratios = [c[index] / a for c in compatible]
                    assert shares[label] == {
                        "lower": min(observed_ratios),
                        "upper": max(observed_ratios),
                    }


@pytest.mark.parametrize("n", range(5))
def test_failure_partition_bounds_are_sharp_but_components_coupled(n):
    tables = _joint_tables(n)
    for a, b in product(range(n + 1), repeat=2):
        for m in (None, *range(min(a, b) + 1)):
            compatible = _matching_tables(tables, a, b, m)
            result = paired_remission_bounds(n, a, b, m)
            partitions = [
                (table[0], *components)
                for table in compatible
                for components in product(range(a + 1), repeat=3)
                if sum(components) == table[1]
            ]
            assert all(sum(partition) == a for partition in partitions)
            for index, key in enumerate(COMPONENTS, start=1):
                values = [partition[index] for partition in partitions]
                assert result["failure_component_count_bounds"][key] == {
                    "lower": min(values),
                    "upper": max(values),
                }
            totals = [sum(partition[1:]) for partition in partitions]
            partition_result = result["failure_partition"]
            assert partition_result["total_failure_count_bounds"] == {
                "lower": min(totals),
                "upper": max(totals),
            }
            assert partition_result["components_coupled"] is True
            assert partition_result["observed_component_counts"] is None
            assert partition_result["zero_lower_bound_is_observed_zero"] is False


def test_registered_arbitrary_fixture_is_validation_only_math():
    # N10/a4/b5/m3 is the frozen arbitrary software fixture, not a source cohort.
    result = paired_remission_bounds(10, 4, 5, 3)
    assert result["feasible_positive_pair"] == {"lower": 3, "upper": 4}
    assert result["extreme_tables"] == {
        "at_lower_positive_pair": dict(zip(CELLS, (3, 1, 2, 4), strict=True)),
        "at_upper_positive_pair": dict(zip(CELLS, (4, 0, 1, 5), strict=True)),
    }
    assert result["first_positive_conditional_shares"] == {
        "denominator_n": 4,
        "positive": {"lower": 0.75, "upper": 1.0},
        "primary_failure": {"lower": 0.0, "upper": 0.25},
    }


@pytest.mark.parametrize("n", range(6))
def test_added_lower_bound_information_only_narrows_compatible_sets(n):
    tables = _joint_tables(n)
    for a, b in product(range(n + 1), repeat=2):
        previous = paired_remission_bounds(n, a, b)
        previous_tables = set(_matching_tables(tables, a, b, None))
        for m in range(min(a, b) + 1):
            current = paired_remission_bounds(n, a, b, m)
            current_tables = set(_matching_tables(tables, a, b, m))
            assert current_tables <= previous_tables
            for cell in CELLS:
                bounds, old = (
                    current["joint_cell_bounds"][cell],
                    previous["joint_cell_bounds"][cell],
                )
                assert old["lower"] <= bounds["lower"] <= bounds["upper"] <= old["upper"]
            previous, previous_tables = current, current_tables


def test_primary_failure_does_not_allocate_missing_death_or_assessed_nonremission():
    result = paired_remission_bounds(10, 4, 5, 3)
    components = result["failure_component_count_bounds"]
    assert components == {key: {"lower": 0, "upper": 1} for key in COMPONENTS}
    # These three mutually distinct allocations are all compatible with x=3.
    for partition in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        assert 3 + sum(partition) == 4
    # Marginal component maxima cannot be allocated simultaneously.
    assert sum(bounds["upper"] for bounds in components.values()) > 1
    assert result["interpretation"]["primary_failure_is_assessed_nonremission"] is False
    assert result["failure_partition"]["observed_component_counts"] is None


def test_unavoidable_primary_failure_still_has_no_observed_component_lower_bound():
    result = paired_remission_bounds(5, 4, 1)
    assert result["failure_partition"]["total_failure_count_bounds"] == {"lower": 3, "upper": 4}
    assert all(bounds["lower"] == 0 for bounds in result["failure_component_count_bounds"].values())
    assert result["failure_partition"]["observed_component_counts"] is None


@pytest.mark.parametrize("b", (0, 1, 5))
def test_zero_first_positive_denominator_remains_unavailable(b):
    result = paired_remission_bounds(5, 0, b)
    assert result["first_positive_conditional_shares"] == {
        "denominator_n": 0,
        "positive": None,
        "primary_failure": None,
    }
    assert result["feasible_positive_pair"] == {"lower": 0, "upper": 0}
    assert all(
        bounds == {"lower": 0, "upper": 0}
        for bounds in result["failure_component_count_bounds"].values()
    )


def test_empty_cohort_has_exact_zero_accounting_and_unknown_conditional_shares():
    result = paired_remission_bounds(0, 0, 0)
    assert all(
        bounds == {"lower": 0, "upper": 0} for bounds in result["joint_cell_bounds"].values()
    )
    assert all(set(table.values()) == {0} for table in result["extreme_tables"].values())
    assert result["first_positive_conditional_shares"]["positive"] is None
    assert result["first_positive_conditional_shares"]["primary_failure"] is None


def test_lower_bound_is_not_asserted_to_be_the_exact_pair_count():
    result = paired_remission_bounds(10, 4, 5, 3)
    assert result["feasible_positive_pair"]["lower"] == 3
    assert result["feasible_positive_pair"]["upper"] == 4
    assert result["interpretation"]["subgroup_scope_requires_source_verification"] is True


def test_none_and_zero_lower_bound_have_same_math_but_distinct_scope_metadata():
    marginal, constrained = paired_remission_bounds(10, 4, 5), paired_remission_bounds(10, 4, 5, 0)
    for key in ("joint_cell_bounds", "extreme_tables", "first_positive_conditional_shares"):
        assert marginal[key] == constrained[key]
    assert marginal["interpretation"]["subgroup_constraint_supplied"] is False
    assert constrained["interpretation"]["subgroup_constraint_supplied"] is True


class _IntegerSubclass(int):
    pass


NON_INTEGERS = (
    True,
    False,
    1.0,
    math.nan,
    math.inf,
    -math.inf,
    "1",
    Decimal(1),
    Fraction(1),
    np.int64(1),
    _IntegerSubclass(1),
    [],
    {},
    None,
)


@pytest.mark.parametrize("position", range(3))
@pytest.mark.parametrize("bad", NON_INTEGERS)
def test_count_inputs_reject_coercion_bool_and_nonfinite(position, bad):
    values = [10, 4, 5]
    values[position] = bad
    with pytest.raises(ValueError, match="exact Python integer"):
        paired_remission_bounds(*values)


@pytest.mark.parametrize("bad", NON_INTEGERS[:-1])
def test_optional_lower_bound_rejects_coercion_bool_and_nonfinite(bad):
    with pytest.raises(ValueError, match="nonnegative Python integer"):
        paired_remission_bounds(10, 4, 5, bad)


@pytest.mark.parametrize("counts", [(-1, 0, 0), (3, -1, 1), (3, 1, -1), (3, 4, 1), (3, 1, 4)])
def test_invalid_marginal_domains_are_rejected(counts):
    with pytest.raises(ValueError, match="0 <= a,b <= N"):
        paired_remission_bounds(*counts)


def test_negative_lower_bound_is_rejected():
    with pytest.raises(ValueError, match="nonnegative Python integer"):
        paired_remission_bounds(10, 4, 5, -1)


@pytest.mark.parametrize("counts", [(10, 4, 5, 5), (0, 0, 0, 1), (5, 0, 4, 1)])
def test_infeasible_lower_bound_is_rejected_without_clipping(counts):
    with pytest.raises(ValueError, match="no feasible joint table"):
        paired_remission_bounds(*counts)


def test_large_integers_keep_exact_count_bounds_and_finite_shares():
    scale = 10**1000
    result = paired_remission_bounds(10 * scale, 4 * scale, 5 * scale, 3 * scale)
    assert result["feasible_positive_pair"] == {"lower": 3 * scale, "upper": 4 * scale}
    assert result["first_positive_conditional_shares"]["positive"] == {"lower": 0.75, "upper": 1.0}
    assert all(
        type(value) is int
        for table in result["extreme_tables"].values()
        for value in table.values()
    )


@pytest.mark.parametrize("counts", [(0, 0, 0), (10, 4, 5), (10, 4, 5, 3), (5, 5, 5, 5)])
def test_result_is_json_safe_and_never_promotes_labels_to_clinical_truth(counts):
    result = paired_remission_bounds(*counts)
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    interpretation = result["interpretation"]
    for key in (
        "primary_failure_is_assessed_nonremission",
        "prior_diagnosis_erased",
        "latent_clinical_states_identified",
        "sustained_untreated_remission_identified",
        "clinical_hazards_identified",
        "causal_effect_identified",
        "engine_activation_allowed",
        "joint_cell_bounds_independently_allocatable",
    ):
        assert interpretation[key] is False
    assert interpretation["sampling_interval"] is None


def test_callers_cannot_mutate_subsequent_results_or_alias_component_bounds():
    first = paired_remission_bounds(10, 4, 5, 3)
    first["failure_component_count_bounds"]["death"]["upper"] = 100
    first["extreme_tables"]["at_lower_positive_pair"]["positive_positive"] = 100
    assert first["failure_component_count_bounds"]["unassessed"]["upper"] == 1
    second = paired_remission_bounds(10, 4, 5, 3)
    assert second["failure_component_count_bounds"]["death"]["upper"] == 1
    assert second["extreme_tables"]["at_lower_positive_pair"]["positive_positive"] == 3
