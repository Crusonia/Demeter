"""Independent period life-table arithmetic for age-specific death probabilities.

This calculator does not estimate U.S. mortality. The terminal age group must be open,
with its remaining person-years per terminal survivor provided by a source life table.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from collections.abc import Sequence


@dataclass(frozen=True)
class AgeInterval:
    start_age: int
    years: int | None  # None denotes the final, open age interval
    death_probability: float  # q_x; final interval must equal 1
    average_years_lived_by_decedents: float | None = None  # a_x for closed intervals
    terminal_person_years_per_survivor: float | None = None


@dataclass(frozen=True)
class LifeTableRow:
    start_age: int
    survivors: float  # l_x
    deaths: float  # d_x
    person_years: float  # L_x
    remaining_person_years: float  # T_x
    life_expectancy: float  # e_x


def period_life_table(intervals: Sequence[AgeInterval], radix: float = 100_000) -> list[LifeTableRow]:
    """Calculate l, d, L, T, and e from nonoverlapping contiguous age intervals."""
    if not intervals or intervals[0].start_age != 0 or not isfinite(radix) or radix <= 0:
        raise ValueError("table must begin at birth and have a positive finite radix")
    survivors = radix
    previous_end = 0
    forward: list[tuple[int, float, float, float]] = []
    for index, interval in enumerate(intervals):
        q = interval.death_probability
        if interval.start_age != previous_end or not isfinite(q) or not 0 <= q <= 1:
            raise ValueError("ages must be contiguous and death probabilities finite in [0, 1]")
        if interval.years is None:
            remaining = interval.terminal_person_years_per_survivor
            if index != len(intervals) - 1 or q != 1 or remaining is None or not isfinite(remaining) or remaining < 0:
                raise ValueError("final open interval requires q=1 and finite nonnegative remaining years")
            person_years = survivors * remaining
        else:
            a = interval.average_years_lived_by_decedents
            if interval.years <= 0 or a is None or not isfinite(a) or not 0 <= a <= interval.years:
                raise ValueError("closed interval requires positive width and a_x within that width")
            person_years = interval.years * survivors - (interval.years - a) * survivors * q
            previous_end += interval.years
        deaths = survivors * q
        forward.append((interval.start_age, survivors, deaths, person_years))
        survivors -= deaths
    total = 0.0
    rows = []
    for age, lx, dx, person_years in reversed(forward):
        total += person_years
        rows.append(LifeTableRow(age, lx, dx, person_years, total, total / lx if lx else 0.0))
    return list(reversed(rows))
