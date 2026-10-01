"""Exact feasible tables for two source-labelled remission observations.

Counts describe one common cohort, not a latent clinical state or an annual
transition process. A source-coded failure can include an unavailable assessment
or death; neither component is inferred to be an observed clinical relapse.
"""

from __future__ import annotations


def _bounds(lower: int, upper: int) -> dict[str, int]:
    return {"lower": lower, "upper": upper}


def _table(n: int, a: int, b: int, x: int) -> dict[str, int]:
    return {
        "positive_positive": x,
        "positive_failure": a - x,
        "failure_positive": b - x,
        "failure_failure": n - a - b + x,
    }


def paired_remission_bounds(n: int, a: int, b: int, m: int | None = None) -> dict:
    """Return sharp integer bounds and compatible whole extreme tables.

    ``n`` is the common cohort size and ``a``/``b`` its source-positive marginal
    counts at two observations. Optional ``m`` is a lower bound on the number
    positive at both observations, conditional on its supplied cohort membership
    and paired-positive meaning. It is never treated as an exhaustive joint cell.

    All inputs must be ordinary Python integers (not bools or coerced numbers).
    An empty cohort is permitted for software accounting. Conditional shares are
    unavailable when ``a == 0``. Integer bounds are exact; reported shares use
    floating-point ratios. No sampling model or clinical rate is fitted.
    """
    if any(type(value) is not int for value in (n, a, b)):
        raise ValueError("Paired observations require exact Python integer counts")
    if n < 0 or not 0 <= a <= n or not 0 <= b <= n:
        raise ValueError("Paired observations require 0 <= a,b <= N and N >= 0")
    if m is not None and (type(m) is not int or m < 0):
        raise ValueError("Paired positive lower bound must be a nonnegative Python integer")

    lower = max(0, a + b - n)
    upper = min(a, b)
    if m is not None:
        lower = max(lower, m)
    if lower > upper:
        raise ValueError("Paired observation constraints have no feasible joint table")

    failure_lower, failure_upper = a - upper, a - lower
    positive_shares = None if a == 0 else {"lower": lower / a, "upper": upper / a}
    failure_shares = None if a == 0 else {"lower": failure_lower / a, "upper": failure_upper / a}

    return {
        "inputs": {"n": n, "a": a, "b": b, "m": m},
        "feasible_positive_pair": _bounds(lower, upper),
        "joint_cell_bounds": {
            "positive_positive": _bounds(lower, upper),
            "positive_failure": _bounds(failure_lower, failure_upper),
            "failure_positive": _bounds(b - upper, b - lower),
            "failure_failure": _bounds(n - a - b + lower, n - a - b + upper),
        },
        "extreme_tables": {
            "at_lower_positive_pair": _table(n, a, b, lower),
            "at_upper_positive_pair": _table(n, a, b, upper),
        },
        "first_positive_conditional_shares": {
            "denominator_n": a,
            "positive": positive_shares,
            "primary_failure": failure_shares,
        },
        "failure_component_count_bounds": {
            component: _bounds(0, failure_upper)
            for component in ("assessed_nonremission", "unassessed", "death")
        },
        "failure_partition": {
            "total_failure_count_bounds": _bounds(failure_lower, failure_upper),
            "observed_component_counts": None,
            "components_coupled": True,
            "components_mutually_exclusive": True,
            "equation": "second_positive + assessed_nonremission + unassessed + death = a",
            "constraint": "All components are nonnegative integers; second_positive is x.",
            "unassessed_definition": "Unavailable assessment or unknown endpoint criterion, with death excluded within any chosen compatible completion. Actual allocation is unknown.",
            "zero_lower_bound_is_observed_zero": False,
        },
        "interpretation": {
            "scope": "Deterministic feasible sets for supplied source observation labels.",
            "subgroup_constraint_supplied": m is not None,
            "subgroup_scope_requires_source_verification": m is not None,
            "joint_cell_bounds_independently_allocatable": False,
            "sampling_interval": None,
            "share_representation": "Floating ratios of exact integer count bounds.",
            "primary_failure_is_assessed_nonremission": False,
            "prior_diagnosis_erased": False,
            "prior_diagnosis_status": "Not inferred from counts; retain source history separately.",
            "latent_clinical_states_identified": False,
            "sustained_untreated_remission_identified": False,
            "clinical_hazards_identified": False,
            "causal_effect_identified": False,
            "engine_activation_allowed": False,
        },
    }
