"""Exact finite-cohort endpoint bounds, with no sampling or clinical model.

A recorded event may precede death. Unknown endpoints are compatible with either
event status; deaths are not subtracted from them. Survivor bounds require an
explicit complete, same-cohort death-total assumption, never inferred here.
"""

from __future__ import annotations

from fractions import Fraction


def _count(value, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative Python integer")
    return value


def _rational(value: Fraction) -> dict:
    approximation = float(value)
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "display_fraction": approximation,
        "display_underflow": value != 0 and approximation == 0,
    }


def _count_interval(lower: int, upper: int, denominator: int) -> dict:
    return {
        "event_count_bounds": {"lower": lower, "upper": upper},
        "denominator": denominator,
        "event_fraction_bounds": None
        if denominator == 0
        else {
            "lower": _rational(Fraction(lower, denominator)),
            "upper": _rational(Fraction(upper, denominator)),
        },
    }


def endpoint_bounds(
    n: int,
    known_endpoints: int,
    recorded_events: int,
    *,
    cumulative_deaths: int | None = None,
    assume_complete_deaths: bool = False,
) -> dict:
    """Sharp count/fraction bounds for one binary source-recorded endpoint.

    ``known_endpoints`` includes recorded events and known non-events. The
    remaining original cohort members are unknown, never silently negative.
    A supplied death count is an unlinked fact. Only explicit completeness
    permits conditioning on the N-D survivors; no death/event independence is
    assumed. All-dead/empty denominators retain zero count bounds and null ratios.
    Integer/rational outputs are exact; display fractions are approximations.
    """
    n = _count(n, "cohort size")
    known_endpoints = _count(known_endpoints, "known endpoints")
    recorded_events = _count(recorded_events, "recorded events")
    if not recorded_events <= known_endpoints <= n:
        raise ValueError("Counts require 0 <= recorded events <= known endpoints <= N")
    if type(assume_complete_deaths) is not bool:
        raise ValueError("Complete-death-total assumption must be an explicit boolean")
    if cumulative_deaths is not None:
        cumulative_deaths = _count(cumulative_deaths, "cumulative deaths")
        if cumulative_deaths > n:
            raise ValueError("Cumulative deaths cannot exceed the original cohort")
    if assume_complete_deaths and cumulative_deaths is None:
        raise ValueError("A complete-death-total assumption requires a supplied death count")
    unknown = n - known_endpoints
    non_events = known_endpoints - recorded_events
    survivor = allocation = None
    if assume_complete_deaths:
        survivors = n - cumulative_deaths
        survivor = _count_interval(
            max(0, recorded_events - cumulative_deaths),
            min(survivors, recorded_events + unknown),
            survivors,
        )
        allocation = {
            "death_count_bounds": {
                name: {
                    "lower": max(0, cumulative_deaths - (n - count)),
                    "upper": min(cumulative_deaths, count),
                }
                for name, count in (
                    ("known_event", recorded_events),
                    ("known_non_event", non_events),
                    ("unknown_endpoint", unknown),
                )
            },
            "total_deaths": cumulative_deaths,
            "components_coupled": True,
            "constraint": "known_event_deaths + known_non_event_deaths + unknown_endpoint_deaths = total_deaths",
        }
    return {
        "counts": {
            "n": n,
            "known_endpoints": known_endpoints,
            "recorded_events": recorded_events,
            "known_non_events": non_events,
            "unknown_endpoints": unknown,
            "cumulative_deaths": cumulative_deaths,
        },
        "all_assigned": _count_interval(recorded_events, recorded_events + unknown, n),
        "survivor_conditional": survivor,
        "unlinked_death_allocation": allocation,
        "assumptions": {
            "complete_same_cohort_death_total_assumed": assume_complete_deaths,
            "cohort_identity_or_death_completeness_verified_by_math": False,
            "recorded_event_before_death_allowed": True,
            "event_death_independence_assumed": False,
            "unknown_endpoint_imputed_negative": False,
        },
        "interpretation": {
            "finite_cohort_identification_bounds": True,
            "sampling_interval": None,
            "clinical_hazards_identified": False,
            "causal_effect_identified": False,
            "engine_activation_allowed": False,
        },
    }


def _cohort(value, name: str) -> tuple[int, int, int]:
    if type(value) not in (tuple, list) or len(value) != 3:
        raise ValueError(f"{name} requires exactly (N, known endpoints, recorded events)")
    return tuple(value)


def _difference(first: dict | None, second: dict | None) -> dict | None:
    if first is None or second is None or not first["denominator"] or not second["denominator"]:
        return None
    a, b = first["event_count_bounds"], second["event_count_bounds"]
    return {
        "lower": _rational(
            Fraction(a["lower"], first["denominator"]) - Fraction(b["upper"], second["denominator"])
        ),
        "upper": _rational(
            Fraction(a["upper"], first["denominator"]) - Fraction(b["lower"], second["denominator"])
        ),
    }


def endpoint_difference_bounds(
    first: tuple[int, int, int],
    second: tuple[int, int, int],
    *,
    first_deaths: int | None = None,
    second_deaths: int | None = None,
    assume_complete_deaths: bool = False,
) -> dict:
    """Sharp first-minus-second fraction bounds for two disjoint cohorts.

    Unknown-event/death completions can vary separately between cohorts. These
    deterministic extremes require no stochastic independence or causal claim.
    An empty denominator leaves its contrast unavailable, not zero.
    """
    a = endpoint_bounds(
        *_cohort(first, "first cohort"),
        cumulative_deaths=first_deaths,
        assume_complete_deaths=assume_complete_deaths,
    )
    b = endpoint_bounds(
        *_cohort(second, "second cohort"),
        cumulative_deaths=second_deaths,
        assume_complete_deaths=assume_complete_deaths,
    )
    return {
        "direction": "first_minus_second",
        "all_assigned": _difference(a["all_assigned"], b["all_assigned"]),
        "survivor_conditional": _difference(a["survivor_conditional"], b["survivor_conditional"]),
        "distinct_cohorts_required": True,
        "complete_same_cohort_death_totals_assumed": assume_complete_deaths,
        "sampling_interval": None,
        "causal_interpretation": False,
    }


def endpoint_tipping_point(
    first: tuple[int, int, int],
    second: tuple[int, int, int],
    *,
    second_unknown_events: int,
) -> dict:
    """Minimum first-cohort unknown events for nonnegative/positive difference.

    Requires an explicit completion of second-cohort unknown endpoints. Exact
    cross-products distinguish equality from a strictly positive difference.
    An unreachable threshold is null, with its algebraic required count retained.
    This is an all-assigned sensitivity calculation; death is not a non-event.
    """
    a = endpoint_bounds(*_cohort(first, "first cohort"))["counts"]
    b = endpoint_bounds(*_cohort(second, "second cohort"))["counts"]
    second_unknown_events = _count(second_unknown_events, "second unknown events")
    if second_unknown_events > b["unknown_endpoints"]:
        raise ValueError("Second-cohort completion exceeds its unknown endpoint count")
    thresholds = None
    if a["n"] and b["n"]:
        gap = (b["recorded_events"] + second_unknown_events) * a["n"] - a["recorded_events"] * b[
            "n"
        ]
        required = {
            "nonnegative_difference": max(0, -(-gap // b["n"])),
            "positive_difference": max(0, gap // b["n"] + 1),
        }
        thresholds = {
            name: {
                "algebraic_required_count": count,
                "reachable": count <= a["unknown_endpoints"],
                "minimum_first_unknown_events": count if count <= a["unknown_endpoints"] else None,
            }
            for name, count in required.items()
        }
    return {
        "direction": "first_minus_second",
        "estimand": "all_assigned_recorded_endpoint_fraction",
        "second_unknown_events_assumed": second_unknown_events,
        "first_unknown_endpoints": a["unknown_endpoints"],
        "thresholds": thresholds,
        "unavailable_reason": "empty_cohort_denominator" if thresholds is None else None,
        "missing_endpoint_completion_is_observed": False,
        "causal_interpretation": False,
    }
