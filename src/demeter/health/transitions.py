from __future__ import annotations

import numpy as np

STATES = ("healthy", "insulin_resistant", "t2d")
# Canonical description of the implemented flows, exported by the engine.
TRANSITIONS = (
    {
        "source": "healthy",
        "target": "insulin_resistant",
        "flow": "healthy_to_ir",
        "parameter": "h_to_ir_rate",
    },
    {
        "source": "insulin_resistant",
        "target": "healthy",
        "flow": "ir_to_healthy",
        "parameter": "ir_to_h_rate",
    },
    {
        "source": "insulin_resistant",
        "target": "t2d",
        "flow": "ir_to_t2d",
        "parameter": "ir_to_t2d_rate",
    },
)


def _split_competing_exits(stocks, rates, *, multiply_first=False):
    """Partition annual exits without losing finite competing contributions.

    Callers validate nonnegative finite inputs. Preserve their ordinary-case
    arithmetic; scale when the hazard sum or stock-times-rate exceeds float
    range, and divide before multiplying when a product would be subnormal.
    A hazard sum beyond float range has exp(-sum) rounded to zero, not a capped
    hazard. These remain endpoint transitions among the original survivors.
    """
    rates = np.asarray(rates, dtype=float)
    scale = float(rates.max(initial=0))
    if scale == 0:
        return tuple(np.zeros_like(stocks) for _ in rates), np.zeros_like(stocks), False
    maximum = np.finfo(float).max
    scaled = scale > maximum / len(rates)
    if scaled:
        relative = rates / scale
        normalizer = float(relative.sum())
        fractions = relative / normalizer
        denominator = scale
        exits = stocks.copy()
    else:
        total = float(rates.sum())
        fractions = rates / total
        denominator, normalizer = total, 1.0
        exits = stocks * -np.expm1(-total)
    largest_exit = float(exits.max(initial=0))
    smallest_positive_exit = float(np.min(exits, where=exits > 0, initial=maximum))
    smallest_normal = np.finfo(float).tiny
    movements = []
    robust = scaled
    for rate, fraction in zip(rates, fractions, strict=True):
        if (
            multiply_first
            and not scaled
            and (rate <= 1 or largest_exit <= maximum / rate)
            and (rate == 0 or rate >= 1 or smallest_positive_exit >= smallest_normal / rate)
        ):
            moved = exits * rate / total
        elif rate > 0 and fraction < smallest_normal:
            # A subnormal/zero fraction can still yield a representable flow
            # from a large stock. Combine binary exponents before rescaling.
            stock_mantissa, stock_exponent = np.frexp(exits)
            rate_mantissa, rate_exponent = np.frexp(rate)
            base_mantissa, base_exponent = np.frexp(denominator)
            moved = np.ldexp(
                stock_mantissa * (rate_mantissa / base_mantissa / normalizer),
                stock_exponent + rate_exponent - base_exponent,
            )
            robust = True
        else:
            moved = exits * fraction
            if multiply_first:
                robust = True
        movements.append(moved)
    return tuple(movements), exits, robust


def transition_survivors(
    stocks: np.ndarray,
    progression: float,
    regression: float,
    diabetes: float,
    adult_age: int,
    *,
    by_row: bool = False,
) -> tuple[np.ndarray, dict]:
    """One-year competing-hazard transitions; state order H, IR, T2D.

    These are hazards per year, not annual probabilities. No T2D remission is assumed.
    """
    rates = np.array([progression, regression, diabetes])
    if not np.isfinite(rates).all() or (rates < 0).any():
        raise ValueError("transition hazards must be finite and nonnegative")
    if not np.isfinite(stocks).all() or (stocks < 0).any():
        raise ValueError("stocks must be finite and nonnegative")
    output = stocks.copy()
    h_ir = stocks[adult_age:, 0] * -np.expm1(-progression)
    (ir_h, ir_t2d), ir_exits, robust = _split_competing_exits(
        stocks[adult_age:, 1], (regression, diabetes), multiply_first=True
    )
    output[adult_age:, 0] += ir_h - h_ir
    output[adult_age:, 1] += h_ir - ir_exits if robust else h_ir - ir_h - ir_t2d
    output[adult_age:, 2] += ir_t2d
    flows = {
        "healthy_to_ir": float(h_ir.sum()),
        "ir_to_healthy": float(ir_h.sum()),
        "ir_to_t2d": float(ir_t2d.sum()),
    }
    if by_row:
        flows["by_row"] = {
            name: np.concatenate((np.zeros(adult_age), values))
            for name, values in zip(
                ("healthy_to_ir", "ir_to_healthy", "ir_to_t2d"), (h_ir, ir_h, ir_t2d), strict=True
            )
        }
    return output, flows
