import numpy as np
import pytest

from demeter.data.baseline import baseline_validation, population_counts, source_rows
from demeter.health.transitions import transition_survivors
from demeter.model import simulate
from demeter.population.mechanics import age_survivors
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


@pytest.mark.parametrize("sex", ["all", "male", "female"])
@pytest.mark.parametrize("year", [2022, 2023, 2024])
def test_reproduces_authoritative_life_tables_at_every_age(year, sex):
    assert baseline_validation(year, sex)["passed"]
    result = simulate(
        REGISTRY, Scenario(name="baseline", years=1, exposures={}, baseline_year=year, sex=sex)
    )
    assert abs(result.annual[0]["life_expectancy"] - source_rows(year, sex)[0]["ex"]) < 0.001


def test_census_sex_counts_add_to_total():
    np.testing.assert_array_equal(
        population_counts(), population_counts(sex="male") + population_counts(sex="female")
    )


def test_aging_retains_open_group_and_conserves_population():
    stocks = np.zeros((101, 3))
    stocks[0] = [10, 0, 0]
    stocks[99] = [2, 3, 4]
    stocks[100] = [5, 6, 7]
    aged = age_survivors(stocks)
    np.testing.assert_array_equal(aged[1], stocks[0])
    np.testing.assert_array_equal(aged[100], stocks[99] + stocks[100])
    assert aged.sum() == stocks.sum()


def test_competing_hazards_do_not_overdraw_even_at_extreme_rates():
    stocks = np.ones((101, 3)) * 100
    moved, _ = transition_survivors(stocks, 100, 100, 100, 18)
    assert moved.min() >= 0
    assert moved.sum() == pytest.approx(stocks.sum())
    np.testing.assert_array_equal(moved[:18], stocks[:18])


def test_reduced_progression_does_not_increase_same_step_diabetes_flow():
    stocks = np.ones((101, 3)) * 100
    _, base = transition_survivors(stocks, 0.03, 0.02, 0.05, 18)
    _, lower = transition_survivors(stocks, 0.02, 0.02, 0.01, 18)
    assert lower["ir_to_t2d"] < base["ir_to_t2d"]


def test_closed_population_conserved_for_long_horizon():
    result = simulate(REGISTRY, Scenario(name="long", years=100, exposures={"upf": 1}))
    for row in result.annual:
        assert row["population"] + row["cumulative_deaths"] == pytest.approx(
            result.starting_population, abs=1e-5
        )
        assert row["births"] == row["net_migration"] == 0
        assert 0 <= row["metabolically_healthy_life_expectancy"] <= row["life_expectancy"]
    assert all(c[s] >= 0 for c in result.cohorts for s in ("healthy", "insulin_resistant", "t2d"))


def test_exposure_lag_and_no_change_equivalence():
    a = simulate(REGISTRY, Scenario(name="a", years=5, exposures={}))
    b = simulate(
        REGISTRY, Scenario(name="b", years=5, exposures={"upf": 1, "fiber": 1, "fruit_veg": 1})
    )
    assert a.annual == b.annual
    c = simulate(REGISTRY, Scenario(name="c", years=5, exposures={"upf": 0.7}))
    assert a.annual[0] == c.annual[0]
    assert (
        0
        < c.annual[-1]["applied_progression_multiplier"]
        < c.annual[1]["applied_progression_multiplier"]
        < 1
    )
