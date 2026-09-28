"""Health-state time accounting; definitions do not establish clinical validity."""

from __future__ import annotations

import numpy as np

from demeter.health.transitions import STATES, transition_survivors

METHOD_SOURCE = "https://www.cdc.gov/nchs/data/statnt/statnt21.pdf"


def metric_contract() -> dict:
    return {
        "version": "healthspan-v1",
        "primary": "healthspan",
        "label": "Period years in the modeled healthy state",
        "unit": "years per period life-table survivor at the stated age",
        "method": "Sullivan prevalence weighting",
        "method_source": METHOD_SOURCE,
        "alias": "metabolically_healthy_life_expectancy",
        "interpretation": "Total remaining healthy-state time, not age at first disease or cohort lifespan",
        "states": {
            "healthy": "Synthetic healthy/normoglycemic proxy; not absence of all disease",
            "insulin_resistant": "Synthetic IR/prediabetes proxy; not an observed PreChronic state",
            "t2d": "Modeled T2D stock; entry by IR-to-T2D flow, exit only by mortality",
        },
        "competing_risks": "Death precedes survivor transitions; IR progression/regression compete for the same survivors",
        "multimorbidity": "States are mutually exclusive; other diseases and overlapping diagnoses are not represented",
        "unavailable": {
            "prechronic_years": "No separate PreChronic state yet",
            "all_chronic_disease_free_years": "Only T2D is modeled; T2D-free time includes the IR proxy",
            "diagnosed_chronic_disease_years": "No separate diagnosis/ascertainment model",
            "qaly": "No sourced utility weights or joint-condition valuation",
            "who_hale": "No all-cause disability weights or comorbidity correction",
        },
    }


def sullivan(ages, survivors, person_years, prevalence, states: tuple[str, ...]) -> list[dict]:
    """E_s(x) = sum_{a>=x}(L_a p_as) / l_x, for a mutually exclusive partition.

    A zero-survivor age has undefined conditional expectancy, represented as null.
    Missing inputs are errors, never zero health loss or perfect health.
    """
    ages, lx, lived, shares = map(
        lambda a: np.asarray(a, dtype=float), (ages, survivors, person_years, prevalence)
    )
    n = ages.shape[0] if ages.ndim else 0
    if (
        not n
        or ages.shape != (n,)
        or lx.shape != (n,)
        or lived.shape != (n,)
        or shares.shape != (n, len(states))
        or not states
        or len(set(states)) != len(states)
        or not all(np.isfinite(a).all() for a in (ages, lx, lived, shares))
        or (ages < 0).any()
        or (ages != np.floor(ages)).any()
        or (np.diff(ages) <= 0).any()
        or (lx < 0).any()
        or (np.diff(lx) > 0).any()
        or (lived < 0).any()
        or (lived[lx == 0] != 0).any()
        or (shares < 0).any()
        or (shares > 1).any()
        or not np.allclose(shares.sum(axis=1), 1, rtol=0, atol=1e-10)
    ):
        raise ValueError(
            "Sullivan inputs require ordered ages, valid survivorship/person-years, and a complete state partition"
        )
    state_lived = lived[:, None] * shares
    remaining = np.cumsum(state_lived[::-1], axis=0)[::-1]
    life_remaining = np.cumsum(lived[::-1])[::-1]
    return [
        {
            "age": int(age),
            "life_expectancy": float(life_remaining[i] / lx[i]) if lx[i] else None,
            "state_years": {
                state: float(remaining[i, j] / lx[i]) if lx[i] else None
                for j, state in enumerate(states)
            },
            "interval_state_person_years": {
                state: float(state_lived[i, j]) for j, state in enumerate(states)
            },
        }
        for i, age in enumerate(ages)
    ]


def lived_within_year(stocks: np.ndarray, hazards: np.ndarray) -> np.ndarray:
    """Integrate constant mortality hazards until end-of-year metabolic transitions."""
    stocks, hazards = np.asarray(stocks, dtype=float), np.asarray(hazards, dtype=float)
    if (
        stocks.shape != hazards.shape
        or not np.isfinite(stocks).all()
        or not np.isfinite(hazards).all()
        or (stocks < 0).any()
        or (hazards < 0).any()
    ):
        raise ValueError("Time accounting needs matching finite nonnegative stocks/hazards")
    exposure = np.divide(-np.expm1(-hazards), hazards, out=np.ones_like(hazards), where=hazards > 0)
    return stocks * exposure


class CohortTime:
    """Track original age groups through the unchanged engine's annual operators.

    People reaching 100+ retain their original group here even though the engine
    pools current ages. Time is restricted to the simulated horizon, not lifetime.
    """

    def __init__(self, stocks: np.ndarray):
        self.initial = stocks.sum(axis=1).copy()
        self.stocks = stocks.copy()
        self.person_years = np.zeros_like(stocks)
        self.flow_totals: dict[str, np.ndarray] = {}
        self.last_year = 0

    def advance(
        self, year: int, hazards: np.ndarray, rates: tuple[float, float, float], adult: int
    ):
        if year != self.last_year + 1:
            raise ValueError("Cohort accounting requires consecutive annual steps")
        ages = np.minimum(np.arange(len(self.initial)) + year - 1, len(self.initial) - 1)
        current_hazards = hazards[ages]
        lived = lived_within_year(self.stocks, current_hazards)
        deaths = self.stocks * -np.expm1(-current_hazards)
        self.person_years += lived
        self.stocks, flows = transition_survivors(
            self.stocks - deaths, *rates, max(0, adult - year + 1), by_row=True
        )
        for name, values in flows.pop("by_row").items():
            self.flow_totals.setdefault(name, np.zeros(len(self.initial)))
            self.flow_totals[name] += values
        self.last_year = year
        return lived.sum(axis=0)

    def age_stocks(self) -> np.ndarray:
        result = np.zeros_like(self.stocks)
        ages = np.minimum(np.arange(len(self.initial)) + self.last_year, len(self.initial) - 1)
        np.add.at(result, ages, self.stocks)
        return result

    def report(self) -> dict:
        total_initial = float(self.initial.sum())
        totals = self.person_years.sum(axis=0)
        return {
            "unit": "person-years and years per initial person",
            "horizon_years": self.last_year,
            "interpretation": "Restricted time in the original closed population; death ends accrual; no extrapolation after the horizon",
            "timing": "Constant within-year mortality; metabolic transitions occur at year end, before aging",
            "state_person_years": dict(zip(STATES, map(float, totals), strict=True)),
            "state_years_per_initial_person": {
                s: float(totals[i] / total_initial) if total_initial else None
                for i, s in enumerate(STATES)
            },
            "by_initial_age": [
                {
                    "initial_age": age,
                    "initial_age_is_open": age == len(self.initial) - 1,
                    "initial_population": float(initial),
                    "remaining_population": float(self.stocks[age].sum()),
                    "deaths": float(initial - self.stocks[age].sum()),
                    "state_person_years": {
                        s: float(self.person_years[age, i]) for i, s in enumerate(STATES)
                    },
                    "state_years_per_initial_person": {
                        s: float(self.person_years[age, i] / initial) if initial else None
                        for i, s in enumerate(STATES)
                    },
                    "cumulative_transitions": {
                        name: float(values[age]) for name, values in self.flow_totals.items()
                    },
                }
                for age, initial in enumerate(self.initial)
            ],
        }
