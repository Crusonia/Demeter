from __future__ import annotations

import numpy as np

from demeter.life_table import AgeInterval, period_life_table
from demeter.health.healthspan import sullivan
from demeter.health.transitions import STATES


def age_survivors(stocks: np.ndarray) -> np.ndarray:
    """Age by one year; retain survivors from the 100+ group in the open group."""
    aged = np.zeros_like(stocks)
    aged[1:] = stocks[:-1]
    aged[-1] += stocks[-1]
    return aged


def state_shares(stocks: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    return np.divide(
        stocks,
        stocks.sum(axis=1, keepdims=True),
        out=fallback.copy(),
        where=stocks.sum(axis=1, keepdims=True) > 0,
    )


_CALIBRATION_RTOL = 4096 * np.finfo(float).eps


def _ratio_product(value, numerator, denominator, divisor=1.0):
    """Multiply/divide positive quantities without overflowing intermediate ratios."""
    value_mantissa, value_exponent = np.frexp(value)
    numerator_mantissa, numerator_exponent = np.frexp(numerator)
    denominator_mantissa, denominator_exponent = np.frexp(denominator)
    divisor_mantissa, divisor_exponent = np.frexp(divisor)
    with np.errstate(over="ignore", under="ignore"):
        return np.ldexp(
            value_mantissa * numerator_mantissa / denominator_mantissa / divisor_mantissa,
            value_exponent + numerator_exponent - denominator_exponent - divisor_exponent,
        )


def _solve_scaled_mortality(target, weights, ratios):
    """Bracket a single normalized hazard root; no fixed base-hazard ceiling."""
    active = weights > 0
    scale = float(ratios[active].max())

    def probability(value):
        hazards = _ratio_product(value, ratios[active], scale)
        return float(np.sum(weights[active] * -np.expm1(-hazards)))

    maximum = np.finfo(float).max
    upper = 64.0
    while probability(upper) < target:
        if upper == maximum:
            raise ValueError("Mortality calibration requires nonrepresentable state hazards")
        upper = maximum if upper > maximum / 2 else upper * 2
    while upper / 2 > 0 and probability(upper / 2) >= target:
        upper /= 2
    lower = 0.0
    for _ in range(60):
        middle = lower + (upper - lower) / 2
        if probability(middle) < target:
            lower = middle
        else:
            upper = middle
    return _ratio_product(lower + (upper - lower) / 2, ratios, scale)


def calibrate_mortality(rows: list[dict], reference: np.ndarray, ratios: np.ndarray) -> np.ndarray:
    """Solve baseline state hazards so their weighted death probabilities equal source qx.

    Freeze this calibration for subsequent years. Recalibrating to each scenario's
    changing state shares would incorrectly erase the modeled mortality pathway.
    """
    if isinstance(reference, np.ma.MaskedArray) or isinstance(ratios, np.ma.MaskedArray):
        raise ValueError("Mortality calibration cannot discard missing-input masks")
    try:
        raw_reference = np.asarray(reference)
        raw_ratios = np.asarray(ratios)
        raw_q = np.asarray([r["qx"] for r in rows[:-1]])
        raw_terminal = np.asarray(rows[-1]["ex"])
        ages = np.asarray([r["age"] for r in rows])
        if (
            any(value.dtype.kind not in "iuf" for value in (raw_reference, raw_ratios, raw_q))
            or raw_terminal.ndim != 0
            or raw_terminal.dtype.kind not in "iuf"
        ):
            raise ValueError("Mortality inputs must be real numeric quantities")
        reference = raw_reference.astype(float)
        ratios = raw_ratios.astype(float)
        q = raw_q.astype(float)
        terminal_years = float(raw_terminal)
    except (KeyError, IndexError, TypeError, ValueError, OverflowError) as error:
        raise ValueError("Mortality calibration requires complete numeric source inputs") from error
    if (
        ratios.ndim != 1
        or not len(ratios)
        or reference.shape != (101, len(ratios))
        or q.shape != (100,)
        or not np.array_equal(ages, np.arange(101))
        or not np.isfinite(ratios).all()
        or (ratios <= 0).any()
        or not np.isfinite(reference).all()
        or (reference < 0).any()
        or (reference > 1).any()
        or not np.allclose(reference.sum(axis=1), 1, atol=1e-10, rtol=0)
        or not np.isfinite(q).all()
        or (q < 0).any()
        or (q >= 1).any()
        or not np.isfinite(terminal_years)
        or terminal_years <= 0
    ):
        raise ValueError("Invalid mortality probabilities, state shares, ratios or dimensions")

    # Preserve the established ordinary-case arithmetic, then verify rather
    # than assuming the fixed bracket covered every supported positive ratio.
    lo, hi = np.zeros(100), np.full(100, 64.0)
    for _ in range(60):
        middle = (lo + hi) / 2
        with np.errstate(over="ignore"):
            predicted = (reference[:-1] * -np.expm1(-middle[:, None] * ratios)).sum(axis=1)
        lo = np.where(predicted < q, middle, lo)
        hi = np.where(predicted >= q, middle, hi)
    hazards = np.empty((101, len(ratios)))
    with np.errstate(over="ignore", under="ignore"):
        hazards[:-1] = ((lo + hi) / 2)[:, None] * ratios
    hazards[:-1][q == 0] = 0
    realized = (reference[:-1] * -np.expm1(-hazards[:-1])).sum(axis=1)
    admissible = np.isfinite(hazards[:-1]).all(axis=1) & np.isclose(
        realized, q, rtol=_CALIBRATION_RTOL, atol=0
    )
    for index in np.flatnonzero(~admissible):
        hazards[index] = _solve_scaled_mortality(q[index], reference[index], ratios)

    # Frozen-state exponential mixture tail: e100 = sum(w_s / h_s).
    with np.errstate(over="ignore", under="ignore", divide="ignore", invalid="ignore"):
        terminal_base = np.sum(reference[-1] / ratios) / terminal_years
        hazards[-1] = terminal_base * ratios
        realized_tail = np.sum(reference[-1] / hazards[-1])
    if not np.isfinite(hazards[-1]).all() or not np.isclose(
        realized_tail, terminal_years, rtol=_CALIBRATION_RTOL, atol=0
    ):
        # Evaluate each nonnegative contribution after combining its exponents;
        # ref/ratio may overflow before multiplication by another tiny ratio.
        with np.errstate(over="ignore"):
            hazards[-1] = np.sum(
                _ratio_product(
                    reference[-1][None, :], ratios[:, None], ratios[None, :], terminal_years
                ),
                axis=1,
            )
    if (
        not np.isfinite(hazards).all()
        or (hazards[:-1][q > 0] <= 0).any()
        or (hazards[-1] <= 0).any()
    ):
        raise ValueError("Mortality calibration requires nonrepresentable state hazards")
    realized = (reference[:-1] * -np.expm1(-hazards[:-1])).sum(axis=1)
    with np.errstate(over="ignore", divide="ignore"):
        realized_tail = np.sum(reference[-1] / hazards[-1])
    if not np.allclose(realized, q, rtol=_CALIBRATION_RTOL, atol=0) or not np.isclose(
        realized_tail, terminal_years, rtol=_CALIBRATION_RTOL, atol=0
    ):
        raise ValueError("Mortality calibration failed numerical source-target verification")
    return hazards


def period_outcomes(
    rows: list[dict],
    shares: np.ndarray,
    hazards: np.ndarray,
    *,
    include_table: bool = False,
    states: tuple[str, ...] = STATES,
) -> dict:
    q = (shares * -np.expm1(-hazards)).sum(axis=1)
    terminal_years = float(np.sum(shares[-1] / hazards[-1]))
    intervals = [AgeInterval(r["age"], 1, float(q[i]), r["ax"]) for i, r in enumerate(rows[:-1])]
    intervals.append(AgeInterval(100, None, 1, terminal_person_years_per_survivor=terminal_years))
    table = period_life_table(intervals)
    health = sullivan(
        [r.start_age for r in table],
        [r.survivors for r in table],
        [r.person_years for r in table],
        shares,
        states,
    )
    healthy_years = health[0]["state_years"]["healthy"]
    result = {
        "life_expectancy": table[0].life_expectancy,
        "metabolically_healthy_life_expectancy": float(healthy_years),
        "healthspan": float(healthy_years),
        "t2d_free_life_expectancy": sum(
            v for s, v in health[0]["state_years"].items() if s != "t2d"
        ),
        "state_life_expectancy": health[0]["state_years"],
    }
    if "prechronic" in states:
        result["prechronic_years"] = health[0]["state_years"]["prechronic"]
    if include_table:
        from dataclasses import asdict

        result["life_table"] = [
            {
                **asdict(row),
                "qx": float(q[i]) if i < 100 else 1.0,
                "annual_death_probability": float(q[i]),
                "healthspan": health[i]["state_years"]["healthy"],
                "state_life_expectancy": health[i]["state_years"],
            }
            for i, row in enumerate(table)
        ]
    return result
