from pathlib import Path

from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = EvidenceRegistry.from_yaml(ROOT / "evidence" / "parameters.yaml")
BASELINE = Scenario.from_yaml(ROOT / "scenarios" / "baseline.yaml")
LOWER_UPF = Scenario.from_yaml(ROOT / "scenarios" / "reduce_upf_30.yaml")


def test_initial_shares_sum_to_one() -> None:
    total = (
        REGISTRY.value("initial_healthy_share")
        + REGISTRY.value("initial_ir_share")
        + REGISTRY.value("initial_t2d_share")
    )
    assert abs(total - 1.0) < 1e-12


def test_closed_cohort_conserves_population() -> None:
    result = simulate(REGISTRY, BASELINE)
    accounted_for = result.ending_population + result.cumulative_deaths
    assert abs(result.starting_population - accounted_for) < 1e-6


def test_synthetic_registry_marks_output_validation_only() -> None:
    assert simulate(REGISTRY, BASELINE).validation_only is True


def test_lower_upf_reduces_t2d_share_in_validation_model() -> None:
    baseline = simulate(REGISTRY, BASELINE)
    intervention = simulate(REGISTRY, LOWER_UPF)
    assert intervention.ending_state_shares["t2d"] < baseline.ending_state_shares["t2d"]


def test_state_shares_are_bounded_and_sum_to_one() -> None:
    result = simulate(REGISTRY, BASELINE)
    assert all(0.0 <= value <= 1.0 for value in result.ending_state_shares.values())
    assert abs(sum(result.ending_state_shares.values()) - 1.0) < 1e-12
