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


def calibrate_mortality(rows: list[dict], reference: np.ndarray, ratios: np.ndarray) -> np.ndarray:
    """Solve baseline state hazards so their weighted death probabilities equal source qx.

    Freeze this calibration for subsequent years. Recalibrating to each scenario's
    changing state shares would incorrectly erase the modeled mortality pathway.
    """
    q = np.array([r["qx"] for r in rows[:-1]])
    lo, hi = np.zeros(100), np.full(100, 64.0)
    for _ in range(60):
        middle = (lo + hi) / 2
        predicted = (reference[:-1] * -np.expm1(-middle[:, None] * ratios)).sum(axis=1)
        lo = np.where(predicted < q, middle, lo)
        hi = np.where(predicted >= q, middle, hi)
    hazards = np.empty((101, 3))
    hazards[:-1] = ((lo + hi) / 2)[:, None] * ratios
    # Frozen-state exponential mixture tail: e100 = sum(w_s / h_s).
    terminal_base = np.sum(reference[-1] / ratios) / rows[-1]["ex"]
    hazards[-1] = terminal_base * ratios
    return hazards


def period_outcomes(
    rows: list[dict], shares: np.ndarray, hazards: np.ndarray, *, include_table: bool = False
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
        STATES,
    )
    healthy_years = health[0]["state_years"]["healthy"]
    result = {
        "life_expectancy": table[0].life_expectancy,
        "metabolically_healthy_life_expectancy": float(healthy_years),
        "healthspan": float(healthy_years),
        "t2d_free_life_expectancy": healthy_years + health[0]["state_years"]["insulin_resistant"],
        "state_life_expectancy": health[0]["state_years"],
    }
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
