from __future__ import annotations

from dataclasses import dataclass
from math import exp

from demeter.schema import EvidenceRegistry, Scenario


STATES = ("healthy", "insulin_resistant", "t2d")


@dataclass(frozen=True)
class SimulationResult:
    scenario: str
    years: int
    validation_only: bool
    starting_population: float
    ending_population: float
    cumulative_deaths: float
    ending_state_shares: dict[str, float]
    annual: list[dict[str, float]]


def _bounded_rate(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def simulate(registry: EvidenceRegistry, scenario: Scenario) -> SimulationResult:
    """Run a transparent closed-cohort validation model.

    This engine intentionally does not claim to be the final Demeter v0.1 health model.
    It proves scenario parsing, evidence lookup, stock/flow conservation, and reproducible
    simulation mechanics while all parameters remain explicitly synthetic.
    """
    population = registry.value("initial_population")
    shares = {
        "healthy": registry.value("initial_healthy_share"),
        "insulin_resistant": registry.value("initial_ir_share"),
        "t2d": registry.value("initial_t2d_share"),
    }

    if abs(sum(shares.values()) - 1.0) > 1e-9:
        raise ValueError("initial health-state shares must sum to 1")

    stocks = {state: population * share for state, share in shares.items()}
    starting_population = sum(stocks.values())
    cumulative_deaths = 0.0
    annual: list[dict[str, float]] = []

    upf = scenario.exposures.get("upf", 1.0)
    fiber = scenario.exposures.get("fiber", 1.0)
    fruit_veg = scenario.exposures.get("fruit_veg", 1.0)

    progression_multiplier = exp(
        registry.value("beta_upf_progression") * (upf - 1.0)
        - registry.value("beta_fiber_progression") * (fiber - 1.0)
        - registry.value("beta_fruit_veg_progression") * (fruit_veg - 1.0)
    )

    for year in range(1, scenario.years + 1):
        deaths = {
            "healthy": stocks["healthy"] * _bounded_rate(registry.value("mortality_healthy")),
            "insulin_resistant": stocks["insulin_resistant"]
            * _bounded_rate(registry.value("mortality_ir")),
            "t2d": stocks["t2d"] * _bounded_rate(registry.value("mortality_t2d")),
        }
        survivors = {state: stocks[state] - deaths[state] for state in STATES}

        h_to_ir = survivors["healthy"] * _bounded_rate(
            registry.value("h_to_ir_rate") * progression_multiplier
        )
        ir_to_h = survivors["insulin_resistant"] * _bounded_rate(registry.value("ir_to_h_rate"))
        ir_to_t2d = survivors["insulin_resistant"] * _bounded_rate(
            registry.value("ir_to_t2d_rate") * progression_multiplier
        )
        t2d_to_ir = survivors["t2d"] * _bounded_rate(registry.value("t2d_to_ir_rate"))

        stocks = {
            "healthy": survivors["healthy"] - h_to_ir + ir_to_h,
            "insulin_resistant": (
                survivors["insulin_resistant"] + h_to_ir - ir_to_h - ir_to_t2d + t2d_to_ir
            ),
            "t2d": survivors["t2d"] + ir_to_t2d - t2d_to_ir,
        }

        year_deaths = sum(deaths.values())
        cumulative_deaths += year_deaths
        alive = sum(stocks.values())

        annual.append(
            {
                "year": float(year),
                "population": alive,
                "deaths": year_deaths,
                "healthy": stocks["healthy"],
                "insulin_resistant": stocks["insulin_resistant"],
                "t2d": stocks["t2d"],
            }
        )

    ending_population = sum(stocks.values())
    ending_state_shares = {
        state: (stocks[state] / ending_population if ending_population else 0.0) for state in STATES
    }

    return SimulationResult(
        scenario=scenario.name,
        years=scenario.years,
        validation_only=registry.contains_synthetic,
        starting_population=starting_population,
        ending_population=ending_population,
        cumulative_deaths=cumulative_deaths,
        ending_state_shares=ending_state_shares,
        annual=annual,
    )
