"""Numerical calibration limits using pinned mortality and synthetic ratio choices."""

from copy import deepcopy
from decimal import Decimal, localcontext

import numpy as np
import pytest

from demeter.data.baseline import source_rows
from demeter.population.mechanics import calibrate_mortality


@pytest.fixture
def source():
    return deepcopy(source_rows())


@pytest.mark.parametrize("ratio", [1e-10, 1e10, 1e308, np.finfo(float).smallest_subnormal])
def test_single_state_reproduces_independent_log_survival_at_extreme_ratios(source, ratio):
    reference = np.ones((101, 1))
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        hazards = calibrate_mortality(source, reference, np.array([ratio]))
    expected = -np.log1p(-np.array([row["qx"] for row in source[:-1]]))
    np.testing.assert_allclose(hazards[:-1, 0], expected, rtol=1e-13, atol=0)
    assert hazards[-1, 0] == pytest.approx(1 / source[-1]["ex"], rel=1e-13, abs=0)
    assert np.isfinite(hazards).all()
    assert (hazards > 0).all()


def test_two_state_mixture_matches_independent_quadratic_survival_solution(source):
    reference = np.full((101, 2), 0.5)
    ratios = np.array([1e-10, 2e-10])
    original_reference, original_ratios = reference.copy(), ratios.copy()
    original_source = deepcopy(source)
    hazards = calibrate_mortality(source, reference, ratios)
    with localcontext() as context:
        context.prec = 75
        # If y=exp(-h), q=1-(y+y*y)/2. Solve the quadratic in
        # high-precision Decimal independently of the numerical root finder.
        first_hazards = [
            float(-(((Decimal(9) - 8 * Decimal.from_float(row["qx"])).sqrt() - 1) / 2).ln())
            for row in source[:-1]
        ]
    np.testing.assert_allclose(hazards[:-1, 0], first_hazards, rtol=1e-13, atol=0)
    np.testing.assert_allclose(hazards[:-1, 1], np.array(first_hazards) * 2, rtol=1e-13, atol=0)
    np.testing.assert_allclose(hazards[-1], np.array([0.75, 1.5]) / source[-1]["ex"], rtol=1e-14)
    np.testing.assert_array_equal(reference, original_reference)
    np.testing.assert_array_equal(ratios, original_ratios)
    assert source == original_source


@pytest.mark.parametrize("populated_ratio", [1e-10, 1e308])
def test_populated_nonreference_state_calibrates_with_healthy_ratio_fixed_to_one(
    source, populated_ratio
):
    reference = np.tile([0.0, 1.0, 0.0], (101, 1))
    ratios = np.array([1.0, populated_ratio, 1.0])
    hazards = calibrate_mortality(source, reference, ratios)
    target = np.array([row["qx"] for row in source[:-1]])
    np.testing.assert_allclose(-np.expm1(-hazards[:-1, 1]), target, rtol=1e-13, atol=0)
    assert hazards[-1, 1] == pytest.approx(1 / source[-1]["ex"], rel=1e-13)
    assert np.isfinite(hazards).all()
    assert (hazards > 0).all()


def test_zero_and_tiny_positive_targets_do_not_use_absolute_error_acceptance(source):
    source[0]["qx"] = 0
    source[1]["qx"] = np.finfo(float).eps ** 2
    hazards = calibrate_mortality(source, np.ones((101, 1)), np.array([1.0]))
    assert hazards[0, 0] == 0
    assert hazards[1, 0] > 0
    assert -np.expm1(-hazards[1, 0]) == pytest.approx(source[1]["qx"], rel=1e-13, abs=0)


def test_terminal_reciprocal_cancellation_retains_finite_remaining_years(source):
    source[-1]["ex"] = 1e308
    ratio = np.finfo(float).smallest_subnormal
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        hazards = calibrate_mortality(source, np.ones((101, 1)), np.array([ratio]))
    assert hazards[-1, 0] > 0
    assert 1 / hazards[-1, 0] == pytest.approx(source[-1]["ex"], rel=1e-13)


@pytest.mark.parametrize("kind", ["overflow", "underflow"])
def test_unrepresentable_full_state_hazards_fail_instead_of_silently_miscalibrating(source, kind):
    reference = np.tile([1.0, 0.0], (101, 1))
    ratios = (
        np.array([np.finfo(float).smallest_subnormal, 1.0])
        if kind == "overflow"
        else np.array([1e308, np.finfo(float).smallest_subnormal])
    )
    with pytest.raises(ValueError, match="nonrepresentable state hazards"):
        calibrate_mortality(source, reference, ratios)


@pytest.mark.parametrize("ratio", [0, -1, np.nan, np.inf])
def test_invalid_state_ratios_fail_before_calibration(source, ratio):
    with pytest.raises(ValueError, match="Invalid mortality"):
        calibrate_mortality(source, np.ones((101, 1)), np.array([ratio]))


@pytest.mark.parametrize(
    "kind", ["missing_age", "wrong_state_count", "negative", "nan", "sum", "mask"]
)
def test_invalid_reference_partition_is_not_repaired(source, kind):
    reference = np.ones((101, 1))
    if kind == "missing_age":
        reference = reference[:-1]
    elif kind == "wrong_state_count":
        reference = np.ones((101, 2))
    elif kind == "negative":
        reference[0, 0] = -1
    elif kind == "nan":
        reference[0, 0] = np.nan
    elif kind == "sum":
        reference[0, 0] = 0.5
    else:
        reference = np.ma.array(reference, mask=False)
    with pytest.raises(ValueError):
        calibrate_mortality(source, reference, np.array([1.0]))


@pytest.mark.parametrize("qx", [-1, 1, np.nan, np.inf])
def test_invalid_closed_interval_probability_is_not_clipped(source, qx):
    source[0]["qx"] = qx
    with pytest.raises(ValueError, match="Invalid mortality"):
        calibrate_mortality(source, np.ones((101, 1)), np.array([1.0]))


@pytest.mark.parametrize("remaining", [0, -1, np.nan, np.inf])
def test_invalid_terminal_remaining_years_fail(source, remaining):
    source[-1]["ex"] = remaining
    with pytest.raises(ValueError, match="Invalid mortality"):
        calibrate_mortality(source, np.ones((101, 1)), np.array([1.0]))


@pytest.mark.parametrize("field", ["reference", "ratios", "probability", "remaining"])
def test_nonreal_inputs_cannot_silently_discard_an_imaginary_component(source, field):
    reference = np.ones((101, 1))
    ratios = np.array([1.0])
    if field == "reference":
        reference = reference.astype(complex)
        reference[0, 0] += 1j
    elif field == "ratios":
        ratios = np.array([1 + 1j])
    elif field == "probability":
        source[0]["qx"] += 1j
    else:
        source[-1]["ex"] += 1j
    with pytest.raises(ValueError, match="complete numeric source"):
        calibrate_mortality(source, reference, ratios)


@pytest.mark.parametrize("kind", ["duplicate", "reordered"])
def test_source_ages_must_match_the_explicit_single_age_cohorts(source, kind):
    if kind == "duplicate":
        source[1]["age"] = source[0]["age"]
    else:
        source[0], source[1] = source[1], source[0]
    with pytest.raises(ValueError, match="Invalid mortality"):
        calibrate_mortality(source, np.ones((101, 1)), np.array([1.0]))
