"""Joint treatment/health stocks for an explicitly uncalibrated GLP-1 experiment.

Annual operators preserve original cohorts and treatment history. Response is a
two-phase population approximation, not an individual pharmacokinetic model.
"""

from __future__ import annotations

from math import exp

import numpy as np

from demeter.health.healthspan import CohortTime, lived_within_year
from demeter.health.structure import transitions_for

TREATMENT_STATES = ("never", "on_pending", "on_response", "off_washed_out", "off_response")
GLP1_UNITS = {
    "glp1_eligible_fraction": "fraction",
    "glp1_initiation_rate": "hazard_per_year",
    "glp1_reinitiation_rate": "hazard_per_year",
    "glp1_discontinuation_rate": "hazard_per_year",
    "glp1_discontinuation_t2d_rate": "hazard_per_year",
    "glp1_affordability_scale": "USD_per_month",
    "glp1_low_response_share": "fraction",
    "glp1_low_response_factor": "fraction",
    "glp1_response_lag": "years",
    "glp1_washout_lag": "years",
    "glp1_weight_loss": "fraction_of_initial_weight",
    "glp1_intake_reduction": "fraction_of_reference_intake",
    "glp1_progression_beta": "log_hazard_per_weight_fraction",
    "glp1_recovery_beta": "log_hazard_per_weight_fraction",
}


def validate_glp1(registry):
    for key, unit in GLP1_UNITS.items():
        p = registry.parameters[key]
        value = registry.value(key)
        if p.unit != unit or p.model_role != "health_model" or not np.isfinite(value) or value < 0:
            raise ValueError(f"Invalid GLP-1 input: {key}")
        if (unit.startswith("fraction") and value > 1) or (
            key in ("glp1_affordability_scale", "glp1_response_lag", "glp1_washout_lag")
            and value <= 0
        ):
            raise ValueError(f"Invalid GLP-1 bounds: {key}")
    if max(registry.value(k) for k in ("glp1_progression_beta", "glp1_recovery_beta")) > 50:
        raise ValueError("GLP-1 log effect exceeds supported numerical range")


def access_at(scenario, year):
    steps = [s for s in scenario.glp1.access_schedule if s.start_year <= year]
    return steps[-1] if steps else None


def affordability(registry, step):
    if step is None:
        return 0.0
    scale = registry.value("glp1_affordability_scale")
    return step.access_fraction * (
        step.coverage_fraction * exp(-step.monthly_copay_usd / scale)
        + (1 - step.coverage_fraction) * exp(-step.monthly_price_usd / scale)
    )


class GLP1Cohort(CohortTime):
    """Fixed indication/response strata x five treatment states x health states.

    Indication is a synthetic persistent tag assigned at initialization, including
    future adults. Children cannot initiate; T2D/PreChronic are not BMI eligibility.
    """

    def __init__(self, stocks, states, mover, registry, scenario):
        super().__init__(stocks, states, mover)
        validate_glp1(registry)
        self.registry, self.scenario = registry, scenario
        self.joint = np.zeros((len(stocks), 2, 2, len(TREATMENT_STATES), len(states)))
        eligible = registry.value("glp1_eligible_fraction")
        low = registry.value("glp1_low_response_share")
        for indicated, fraction in enumerate((1 - eligible, eligible)):
            for group, weight in enumerate((low, 1 - low)):
                self.joint[:, indicated, group, 0, :] = stocks * fraction * weight
        self.baseline_adults = float(stocks[int(registry.value("adult_age")) :].sum())
        self.treatment_totals = dict.fromkeys(
            ("initiations", "reinitiations", "discontinuations"), 0.0
        )
        self.last_treatment_flows = self.treatment_totals.copy()
        self.last_plan = None
        self.on_person_years = 0.0
        self.last_deaths = np.zeros_like(stocks)
        self.last_treatment_deaths = np.zeros(len(TREATMENT_STATES))
        self.cumulative_on_deaths = 0.0
        self.last_health_flows = {}

    def plan(self, year, adult):
        """Allocate fixed capacity using the full population, then reuse for tagged cohorts."""
        p = self.registry.value
        step = access_at(self.scenario, year)
        gate = affordability(self.registry, step)
        first = max(0, adult - year + 1)
        eligible = self.joint[first:, 1]
        clinical_continuation = np.array(
            [
                exp(
                    -p(
                        "glp1_discontinuation_t2d_rate"
                        if s == "t2d"
                        else "glp1_discontinuation_rate"
                    )
                )
                for s in self.states
            ]
        )
        continuation = clinical_continuation * gate
        capacity = self.baseline_adults * (step.supply_fraction if step else 0)
        desired_continuers = float((eligible[:, :, 1:3, :] * continuation).sum())
        on = float(eligible[:, :, 1:3, :].sum())
        before_access = float((eligible[:, :, 1:3, :] * clinical_continuation).sum())
        continuation *= min(1.0, capacity / desired_continuers) if desired_continuers else 1.0
        retained = float((eligible[:, :, 1:3, :] * continuation).sum())
        start = -np.expm1(-p("glp1_initiation_rate")) * gate
        restart = -np.expm1(-p("glp1_reinitiation_rate")) * gate
        demand = float(eligible[:, :, 0, :].sum() * start + eligible[:, :, 3:5, :].sum() * restart)
        allocation = min(1.0, max(0.0, capacity - retained) / demand) if demand else 1.0
        return {
            "first_adult_row": first,
            "continuation": continuation,
            "start": start * allocation,
            "restart": restart * allocation,
            "capacity": capacity,
            "access_affordability": gate,
            "unfilled_start_requests": demand * (1 - allocation),
            "discontinuation_by_reason": {
                "underlying_hazard": on - before_access,
                "access_affordability": before_access - desired_continuers,
                "capacity": max(0.0, desired_continuers - retained),
            },
            "access": step.model_dump() if step else None,
        }

    def advance(self, year, hazards, rates, adult, *, plan=None):
        if year != self.last_year + 1:
            raise ValueError("GLP-1 accounting requires consecutive annual steps")
        plan = plan if plan is not None else self.plan(year, adult)
        self.last_plan = plan
        first = plan["first_adult_row"]
        old = self.joint[first:, 1].copy()
        target = self.joint[first:, 1]
        starts = old[:, :, 0, :] * plan["start"]
        restarts = old[:, :, 3:5, :] * plan["restart"]
        stops = old[:, :, 1:3, :] * (1 - plan["continuation"])
        target[:, :, 0, :] -= starts
        target[:, :, 1, :] += starts + restarts[:, :, 0, :] - stops[:, :, 0, :]
        target[:, :, 2, :] += restarts[:, :, 1, :] - stops[:, :, 1, :]
        target[:, :, 3:5, :] += stops - restarts
        self.last_treatment_flows = dict(
            zip(
                self.treatment_totals,
                map(lambda a: float(a.sum()), (starts, restarts, stops)),
                strict=True,
            )
        )
        for key, value in self.last_treatment_flows.items():
            self.treatment_totals[key] += value
        p = self.registry.value
        onset = target[:, :, 1, :] * -np.expm1(-1 / p("glp1_response_lag"))
        washout = target[:, :, 4, :] * -np.expm1(-1 / p("glp1_washout_lag"))
        target[:, :, 1, :] -= onset
        target[:, :, 2, :] += onset
        target[:, :, 4, :] -= washout
        target[:, :, 3, :] += washout
        ages = np.minimum(np.arange(len(self.initial)) + year - 1, len(self.initial) - 1)
        current_hazards = hazards[ages]
        lived = lived_within_year(
            self.joint, np.broadcast_to(current_hazards[:, None, None, None, :], self.joint.shape)
        )
        self.person_years += lived.sum(axis=(1, 2, 3))
        self.on_person_years += float(lived[:, :, :, 1:3, :].sum())
        deaths = self.joint * -np.expm1(-current_hazards[:, None, None, None, :])
        self.last_deaths = deaths.sum(axis=(1, 2, 3))
        self.last_treatment_deaths = deaths.sum(axis=(0, 1, 2, 4))
        self.cumulative_on_deaths += float(self.last_treatment_deaths[1:3].sum())
        survivors = self.joint - deaths
        health_flows = {}
        for indicated in range(2):
            for group, factor in enumerate((p("glp1_low_response_factor"), 1.0)):
                for status in range(5):
                    weight_effect = p("glp1_weight_loss") * factor if status in (2, 4) else 0.0
                    modified = []
                    for rate, edge in zip(rates, transitions_for(self.scenario), strict=True):
                        forward = self.states.index(edge["target"]) > self.states.index(
                            edge["source"]
                        )
                        coefficient = (
                            -p("glp1_progression_beta") if forward else p("glp1_recovery_beta")
                        )
                        modified.append(rate * exp(coefficient * weight_effect))
                    moved, flows = self.mover(
                        survivors[:, indicated, group, status, :], modified, first, by_row=True
                    )
                    self.joint[:, indicated, group, status, :] = moved
                    for name, values in flows["by_row"].items():
                        health_flows.setdefault(name, np.zeros(len(self.initial)))
                        health_flows[name] += values
        for name, values in health_flows.items():
            self.flow_totals.setdefault(name, np.zeros(len(self.initial)))
            self.flow_totals[name] += values
        self.last_health_flows = {k: float(v.sum()) for k, v in health_flows.items()}
        self.stocks = self.joint.sum(axis=(1, 2, 3))
        self.last_year = year
        if self.joint.min() < -1e-8:
            raise ArithmeticError("Negative GLP-1 treatment stock")
        return lived.sum(axis=(0, 1, 2, 3))

    def treatment_report(self):
        counts = self.joint.sum(axis=(0, 1, 2, 4))
        p = self.registry.value
        responding = self.joint[:, :, :, (2, 4), :].sum(axis=(0, 1, 3, 4))
        effective = float(responding @ np.array([p("glp1_low_response_factor"), 1.0]))
        total = float(counts.sum())
        adult = int(p("adult_age"))
        first = max(0, adult - self.last_year)
        return {
            "treatment_stocks": dict(zip(TREATMENT_STATES, map(float, counts), strict=True)),
            "eligible_adults": float(self.joint[first:, 1].sum()),
            "on_treatment": float(counts[1:3].sum()),
            "residual_response_off_treatment": float(counts[4]),
            "flows": self.last_treatment_flows.copy(),
            "cumulative_flows": self.treatment_totals.copy(),
            "on_treatment_person_years": self.on_person_years,
            "deaths_by_treatment": dict(
                zip(TREATMENT_STATES, map(float, self.last_treatment_deaths), strict=True)
            ),
            "cumulative_on_treatment_deaths": self.cumulative_on_deaths,
            "population_mean_weight_reduction_fraction": effective * p("glp1_weight_loss") / total
            if total
            else None,
            "population_mean_intake_reduction_fraction": effective
            * p("glp1_intake_reduction")
            / total
            if total
            else None,
            "response_groups": [
                {
                    "group": name,
                    "population": float(self.joint[:, :, i].sum()),
                    "on_treatment": float(self.joint[:, :, i, 1:3, :].sum()),
                    "response_phase_population": float(responding[i]),
                    "weight_reduction_in_response_phase": p("glp1_weight_loss")
                    * (p("glp1_low_response_factor") if i == 0 else 1.0),
                }
                for i, name in enumerate(("low_response", "high_response"))
            ],
            "allocation": {
                k: v
                for k, v in self.last_plan.items()
                if k not in ("first_adult_row", "continuation")
            }
            if self.last_plan
            else None,
        }

    def report(self):
        result = super().report()
        result["timing"] = (
            "Annual treatment allocation/response first, constant within-year mortality, then year-end health transitions and aging; not subannual pharmacokinetics"
        )
        return result
