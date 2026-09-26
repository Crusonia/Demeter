from __future__ import annotations

import numpy as np


def transition_survivors(
    stocks: np.ndarray, progression: float, regression: float, diabetes: float, adult_age: int
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
    total = regression + diabetes
    exits = stocks[adult_age:, 1] * -np.expm1(-total)
    ir_h = exits * regression / total if total else np.zeros_like(exits)
    ir_t2d = exits * diabetes / total if total else np.zeros_like(exits)
    output[adult_age:, 0] += ir_h - h_ir
    output[adult_age:, 1] += h_ir - ir_h - ir_t2d
    output[adult_age:, 2] += ir_t2d
    return output, {
        "healthy_to_ir": float(h_ir.sum()),
        "ir_to_healthy": float(ir_h.sum()),
        "ir_to_t2d": float(ir_t2d.sum()),
    }
