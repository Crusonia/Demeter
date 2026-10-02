"""Floating-point race limits; arbitrary inputs are not empirical health rates."""

import numpy as np
import pytest

from demeter.health.structure import move, prechronic_transitions
from demeter.health.transitions import transition_survivors


def competing_race(structure, stocks, recovery, progression, *, adult=0):
    if structure == "legacy":
        return transition_survivors(stocks, 0, recovery, progression, adult, by_row=True)
    return prechronic_transitions(
        stocks, 0, recovery, progression, 0, 0, adult_age=adult, by_row=True
    )


@pytest.mark.parametrize("structure,state_count", [("legacy", 3), ("risk_1", 4)])
@pytest.mark.parametrize("case", ["overflow_sum", "overflow_product", "tiny_product"])
def test_competing_hazards_keep_analytic_partition_and_conservation(structure, state_count, case):
    stocks = np.zeros((2, state_count))
    stocks[:, 1] = [100, 1000]
    maximum = np.finfo(float).max
    if case == "overflow_sum":
        recovery, progression = maximum, maximum
        expected = stocks[:, 1] / 2
    elif case == "overflow_product":
        recovery, progression = maximum / 4, maximum / 4
        expected = stocks[:, 1] / 2
    else:
        recovery = progression = np.sqrt(np.finfo(float).tiny) / 100
        # At this scale 1-exp(-2r) rounds via expm1 to 2r; each cause
        # contribution is stock*r, which is representable without stock*r*r.
        expected = stocks[:, 1] * recovery
    original = stocks.copy()
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        result, flows = competing_race(structure, stocks, recovery, progression)
    assert np.isfinite(result).all()
    assert (result >= 0).all()
    np.testing.assert_allclose(result.sum(axis=1), stocks.sum(axis=1), rtol=1e-15)
    np.testing.assert_allclose(result[:, 0], expected, rtol=1e-14, atol=0)
    np.testing.assert_allclose(result[:, 2], expected, rtol=1e-14, atol=0)
    recovery_key = "ir_to_healthy" if structure == "legacy" else "prechronic_to_healthy"
    progression_key = "ir_to_t2d" if structure == "legacy" else "prechronic_to_prediabetes"
    assert flows[recovery_key] == pytest.approx(float(expected.sum()), rel=1e-14, abs=0)
    assert flows[progression_key] == pytest.approx(float(expected.sum()), rel=1e-14, abs=0)
    np.testing.assert_array_equal(stocks, original)


@pytest.mark.parametrize("structure,state_count", [("legacy", 3), ("risk_1", 4)])
def test_hazard_sum_overflow_retains_unequal_race_proportions(structure, state_count):
    stocks = np.zeros((1, state_count))
    stocks[0, 1] = 100
    maximum = np.finfo(float).max
    result, _ = competing_race(structure, stocks, maximum, maximum / 2)
    assert result[0, 0] == pytest.approx(100 * 2 / 3)
    assert result[0, 2] == pytest.approx(100 / 3)
    assert result[0, 1] == 0


@pytest.mark.parametrize("structure,state_count", [("legacy", 3), ("risk_1", 4)])
@pytest.mark.parametrize("overflow_sum", [False, True])
@pytest.mark.parametrize("small_cause", ["recovery", "progression"])
def test_small_relative_hazard_can_still_have_representable_flow_from_large_stock(
    structure, state_count, overflow_sum, small_cause
):
    maximum, minimum_normal = np.finfo(float).max, np.finfo(float).tiny
    stocks = np.zeros((1, state_count))
    stocks[0, 1] = maximum / 4
    large, small = maximum / 2, np.sqrt(minimum_normal)
    if overflow_sum:
        # Include the sum-overflow path while retaining a much smaller rate:
        # scaling is selected conservatively when a sum can exceed float range.
        large = maximum
    recovery, progression = (small, large) if small_cause == "recovery" else (large, small)
    result, flows = competing_race(structure, stocks, recovery, progression)
    expected = small / (large / stocks[0, 1])
    assert expected > 0
    assert result[0, 0 if small_cause == "recovery" else 2] == pytest.approx(
        expected, rel=1e-14, abs=0
    )
    keys = (
        ("ir_to_healthy", "ir_to_t2d")
        if structure == "legacy"
        else ("prechronic_to_healthy", "prechronic_to_prediabetes")
    )
    assert flows[keys[small_cause != "recovery"]] == pytest.approx(expected, rel=1e-14, abs=0)
    assert np.isfinite(result).all()
    assert (result >= 0).all()


@pytest.mark.parametrize("structure,state_count", [("legacy", 3), ("risk_1", 4)])
def test_extreme_races_retain_adult_boundary_and_same_year_endpoint_semantics(
    structure, state_count
):
    stocks = np.zeros((2, state_count))
    stocks[:, 0] = 100
    maximum = np.finfo(float).max
    rates = (maximum,) * (3 if structure == "legacy" else 5)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        result, flows = move(stocks, rates, 1, structure=structure, by_row=True)
    np.testing.assert_array_equal(result[0], stocks[0])
    assert result[1, 1] == 100
    assert result[1, 2:].sum() == 0  # No second live transition for new entrants.
    assert all(values[0] == 0 for values in flows["by_row"].values())
    assert result.sum() == stocks.sum()


@pytest.mark.parametrize("structure,state_count", [("legacy", 3), ("risk_1", 4)])
def test_zero_races_and_empty_adult_risk_set_have_exact_limits(structure, state_count):
    stocks = np.ones((2, state_count))
    for adult, rate in ((0, 0), (len(stocks), np.finfo(float).max)):
        result, flows = competing_race(structure, stocks, rate, rate, adult=adult)
        np.testing.assert_array_equal(result, stocks)
        assert all(value == 0 for key, value in flows.items() if key != "by_row")
