import pytest
from pydantic import ValidationError

from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


@pytest.mark.parametrize(
    "exposures",
    [{"unknown": 1}, {"upf": float("nan")}, {"upf": float("inf")}, {"upf": 0}, {"fiber": 1.2}],
)
def test_invalid_or_unidentified_exposures_fail(exposures):
    with pytest.raises(ValidationError):
        Scenario(name="invalid", exposures=exposures)


def test_missing_and_wrong_unit_parameters_fail():
    for change in ("missing", "unit"):
        raw = REGISTRY.model_dump()
        if change == "missing":
            del raw["parameters"]["h_to_ir_rate"]
        else:
            raw["parameters"]["h_to_ir_rate"]["unit"] = "people"
        with pytest.raises(ValueError, match="Missing parameter or wrong units"):
            simulate(EvidenceRegistry.model_validate(raw), Scenario(name="test", exposures={}))


def test_unknown_fields_and_nonfinite_evidence_fail():
    raw = REGISTRY.model_dump()
    raw["parameters"]["h_to_ir_rate"]["value"] = float("nan")
    with pytest.raises(ValidationError):
        EvidenceRegistry.model_validate(raw)
    with pytest.raises(ValidationError):
        Scenario(name="x", exposures={}, typo=3)


def test_invalid_shares_fail_before_simulation():
    raw = REGISTRY.model_dump()
    raw["parameters"]["initial_healthy_share"]["value"] = 0.9
    with pytest.raises(ValueError, match="sum to 1"):
        simulate(EvidenceRegistry.model_validate(raw), Scenario(name="x", exposures={}))


def test_scientific_mode_cannot_run_synthetic_parameters():
    with pytest.raises(ValueError, match="Scientific mode blocked"):
        simulate(REGISTRY, Scenario(name="x", exposures={}, mode="scientific"))


def test_extrapolation_is_opt_in_and_reported():
    with pytest.raises(ValueError, match="outside the registered envelope"):
        simulate(REGISTRY, Scenario(name="x", exposures={"upf": 0.3}))
    result = simulate(
        REGISTRY, Scenario(name="x", years=1, exposures={"upf": 0.3}, allow_extrapolation=True)
    )
    assert result.metadata["extrapolation"]
    assert result.validation_only


def test_evidence_hash_changes_when_a_parameter_changes():
    updated = REGISTRY.model_copy(deep=True)
    updated.parameters["h_to_ir_rate"].value = 0.04
    assert updated.content_hash != REGISTRY.content_hash
    assert "observed_prediabetes_65_plus" in REGISTRY.audit()["missing_uncertainty"]


def test_unresolved_value_never_runs():
    raw = REGISTRY.model_dump()
    raw["parameters"]["h_to_ir_rate"].update(value=None, unresolved=True)
    with pytest.raises(ValueError, match="Unresolved evidence"):
        simulate(EvidenceRegistry.model_validate(raw), Scenario(name="x", exposures={}))
