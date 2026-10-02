"""Exact finite-cohort source-category bounds with untraced follow-up.

Categories describe people alive at their source follow-up ascertainment, which
may occur at different elapsed times. Confirmed deaths are a separate, disjoint
disposition; this is not a cumulative diagnosis endpoint or a mortality schedule.
Design trace: I-11/I-12 -> F-08 -> T-08.
"""

from __future__ import annotations

from fractions import Fraction

from demeter.analysis.endpoint_bounds import _count, _rational


RESERVED_CATEGORY_KEYS = frozenset({"death", "deaths", "dead", "confirmed_deaths", "untraced"})


def _fractions(lower: int, upper: int, denominator: int) -> dict | None:
    if denominator == 0:
        return None
    return {
        "lower": _rational(Fraction(lower, denominator)),
        "upper": _rational(Fraction(upper, denominator)),
    }


def followup_category_bounds(
    n: int,
    category_counts: dict[str, int],
    confirmed_deaths: int,
    untraced: int,
) -> dict:
    """Sharp coordinate bounds over all integer completions of untraced people.

    Caller declares mutually exclusive, exhaustive alive source categories and a
    disjoint partition N = observed alive + confirmed deaths + wholly untraced.
    Known categories and deaths are held fixed. Every untraced person may belong
    to exactly one alive category or death, with no missingness independence.

    Survivor fractions use each completion's alive denominator. If observed alive
    A>0 and there are at least two categories, extrema for category count c are
    c/(A+U) and (c+U)/(A+U). Different allocations attain those endpoints; they
    are not a joint table. With one exhaustive category, any nonempty survivor
    population belongs entirely to it. If A=0<U, positive-alive completions are
    possible but not guaranteed; bounds explicitly condition on those completions.
    Empty/all-dead denominators yield null fractions, never zero risk.
    """
    n = _count(n, "cohort size")
    confirmed_deaths = _count(confirmed_deaths, "confirmed deaths")
    untraced = _count(untraced, "wholly untraced people")
    if type(category_counts) is not dict or not category_counts:
        raise ValueError("A nonempty dictionary of exhaustive alive categories is required")
    if any(type(key) is not str or not key or key != key.strip() for key in category_counts):
        raise ValueError("Category keys must be unique nonempty named strings")
    if any(key.casefold().replace(" ", "_") in RESERVED_CATEGORY_KEYS for key in category_counts):
        raise ValueError("Alive category keys cannot collide with death or untraced dispositions")
    categories = {
        key: _count(category_counts[key], "category count") for key in sorted(category_counts)
    }
    observed_alive = sum(categories.values())
    if observed_alive + confirmed_deaths + untraced != n:
        raise ValueError("Counts must conserve N = observed alive + confirmed deaths + untraced")
    maximum_alive = observed_alive + untraced
    positive_feasible = maximum_alive > 0
    positive_guaranteed = observed_alive > 0
    survivor_fractions = {}
    for key, count in categories.items():
        if not positive_feasible:
            fractions = None
        elif len(categories) == 1:
            fractions = _fractions(1, 1, 1)
        elif observed_alive == 0:
            fractions = _fractions(0, 1, 1)
        else:
            fractions = _fractions(count, count + untraced, maximum_alive)
        survivor_fractions[key] = fractions
    alive_bounds = {"lower": observed_alive, "upper": maximum_alive}
    return {
        "counts": {
            "n": n,
            "observed_alive": observed_alive,
            "observed_category_counts": categories,
            "confirmed_deaths": confirmed_deaths,
            "untraced": untraced,
        },
        "completion_count_bounds": {
            "category_counts": {
                key: {"lower": count, "upper": count + untraced}
                for key, count in categories.items()
            },
            "death_count": {"lower": confirmed_deaths, "upper": confirmed_deaths + untraced},
            "alive_count": alive_bounds.copy(),
        },
        "all_assigned": {
            "denominator": n,
            "category_fraction_bounds": {
                key: _fractions(count, count + untraced, n) for key, count in categories.items()
            },
            "death_fraction_bounds": _fractions(confirmed_deaths, confirmed_deaths + untraced, n),
        },
        "survivor_conditional": {
            "alive_count_bounds": alive_bounds.copy(),
            "positive_alive_count_feasible": positive_feasible,
            "positive_alive_count_guaranteed": positive_guaranteed,
            "bounds_conditioned_on_positive_alive_count": positive_feasible
            and not positive_guaranteed,
            "positive_alive_count_bounds": {"lower": max(1, observed_alive), "upper": maximum_alive}
            if positive_feasible
            else None,
            "category_fraction_bounds": survivor_fractions,
        },
        "joint_completion_constraint": {
            "untraced_allocation_total": untraced,
            "allocation_equation": "sum(x_category) + x_death = untraced",
            "completion_equation": "sum(completed_category_counts) + completed_deaths = N",
            "allocations_are_nonnegative_integers": True,
            "known_category_and_death_counts_held_fixed": True,
            "coordinate_extrema_are_coupled": True,
            "all_coordinate_extrema_jointly_attainable_claimed": False,
        },
        "assumptions": {
            "alive_categories_mutually_exclusive_and_exhaustive": True,
            "category_death_untraced_partitions_disjoint": True,
            "source_partition_verified_by_math": False,
            "independent_missingness_assumed": False,
            "untraced_people_imputed_alive_or_dead": False,
        },
        "interpretation": {
            "estimand": "Source categories among people alive at their source follow-up ascertainment",
            "ascertainment_clock": "Person-specific source follow-up; mixed elapsed times permitted",
            "count_unit": "people",
            "fraction_unit": "dimensionless",
            "finite_cohort_identification_bounds": True,
            "common_elapsed_horizon_assumed": False,
            "cumulative_diagnosis_endpoint": False,
            "metabolic_health_mapping_inferred": False,
            "clinical_transition_hazards_identified": False,
            "sampling_interval": None,
            "iid_sampling_assumed": False,
            "causal_effect_identified": False,
            "diet_effect_identified": False,
            "engine_activation_allowed": False,
        },
    }
