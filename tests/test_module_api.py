import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from demeter.cli import app
from demeter.contracts import (
    Axis,
    ModuleSpec,
    ParameterDependency,
    Port,
    Quantity,
    TimeSeries,
    require_api,
    require_connection,
)
from demeter.examples.transition_modules import DietaryTransitions, NoDietEffect
from demeter.health.module import interface_for, load_transition_module, simulation_series
from demeter.model import required_units, simulate
from demeter.schema import EvidenceRegistry, Scenario

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def scenario(**kwargs):
    return Scenario(name="module_contract", years=3, exposures={"upf": 0.7}, **kwargs)


def test_labelled_quantity_shape_units_and_immutability():
    port = interface_for(scenario()).stock_port
    quantity = Quantity(port=port, values=(1.0,) * 303)
    assert len(quantity.values) == 303
    with pytest.raises(ValidationError, match="shape"):
        Quantity(port=port, values=(1, 2))
    with pytest.raises(ValidationError, match="nonnegative"):
        Quantity(port=port, values=(-1.0,) * 303)
    with pytest.raises(ValidationError):
        quantity.values = (2.0,) * 303
    with pytest.raises(ValueError, match="Incompatible"):
        require_connection(port, port.model_copy(update={"unit": "thousands_of_people"}))
    with pytest.raises(ValueError, match="Incompatible"):
        require_connection(port, port.model_copy(update={"axes": tuple(reversed(port.axes))}))
    with pytest.raises(ValueError, match="Incompatible"):
        require_connection(
            port, port.model_copy(update={"definition": "A different observed population"})
        )
    with pytest.raises(ValidationError, match="unique"):
        Axis(name="age", labels=("1", "1"))
    with pytest.raises(ValidationError, match="Stocks"):
        Port.model_validate({**port.model_dump(), "temporal": "interval_total"})


def test_time_series_distinguishes_rates_from_interval_totals():
    port = Port(
        name="deaths",
        kind="flow",
        unit="people",
        temporal="interval_total",
        definition="Explicit deaths in interval",
    )
    rows = (Quantity(port=port, values=(2,)), Quantity(port=port, values=(3,)))
    series = TimeSeries(times_years=(0, 1, 2), rows=rows)
    assert TimeSeries.model_validate_json(series.model_dump_json()) == series
    for times in ((1, 2), (0, 0, 2), (0, float("nan"), 2)):
        with pytest.raises(ValidationError):
            TimeSeries(times_years=times, rows=rows)
    with pytest.raises(ValidationError, match="draw identifier"):
        TimeSeries(times_years=(0, 1, 2), rows=rows, uncertainty="sample")
    assert TimeSeries(times_years=(0, 1, 2), rows=rows, uncertainty="sample", draw_id="seed7/draw1")
    with pytest.raises(ValidationError, match="quantity definition"):
        TimeSeries(
            times_years=(0, 1, 2),
            rows=(rows[0], Quantity(port=port.model_copy(update={"unit": "kg"}), values=(3,))),
        )


@pytest.mark.parametrize("version", ["2.0", "1.1", "0.9", "1.-1", "1", "latest"])
def test_incompatible_api_versions_fail(version):
    with pytest.raises(ValueError):
        require_api(version)


@pytest.mark.parametrize("structure", ["legacy", "risk_1", "risk_2"])
@pytest.mark.parametrize("kind", ["legacy", "dynamic"])
def test_reference_extension_reproduces_canonical_arithmetic(structure, kind):
    s = scenario(health_structure=structure, diet_response={"kind": kind})
    normal = simulate(REGISTRY, s, diagnostics=True)
    extended = simulate(REGISTRY, s, transition_module=DietaryTransitions(), diagnostics=True)
    assert normal.cohorts == extended.cohorts
    for a, b in zip(normal.annual, extended.annual, strict=True):
        assert a == {k: v for k, v in b.items() if k != "module_base_hazards_per_year"}
    assert normal.healthspan == extended.healthspan
    assert normal.prechronic == extended.prechronic
    assert extended.diagnostics["structure"]["dependencies"] == []
    assert extended.diagnostics["structure"]["module_contract"]
    p = extended.metadata["transition_module"]
    assert p["classification"] == "experimental"
    assert (
        p["source_sha256"]
        == hashlib.sha256(
            Path("src/demeter/examples/transition_modules.py").read_bytes()
        ).hexdigest()
    )
    assert p["spec"]["api_version"] == "1.0"
    assert extended.validation_only


def test_reference_extension_preserves_glp1_policy_and_tagged_cohort():
    s = Scenario.from_yaml("scenarios/glp1_access.yaml")
    a, b = simulate(REGISTRY, s), simulate(REGISTRY, s, transition_module=DietaryTransitions())
    assert a.cohorts == b.cohorts
    assert a.prechronic == b.prechronic
    assert a.healthspan == b.healthspan


@pytest.mark.parametrize(
    "s",
    [
        scenario(),
        scenario(health_structure="risk_1", diet_response={"kind": "dynamic"}),
        Scenario.from_yaml("scenarios/glp1_access.yaml"),
    ],
)
def test_replacement_metadata_does_not_claim_canonical_dietary_effects(s):
    result = simulate(REGISTRY, s, transition_module=NoDietEffect())
    response = result.metadata["diet_response"]
    assert response["role"] == "inputs_to_replacement_module"
    assert "module-defined" in response["timing"]
    assert "may ignore" in " ".join(response["limitations"])
    assert "UPF response multiplies three" not in " ".join(result.metadata["limitations"])
    if s.glp1:
        treatment = " ".join(result.metadata["glp1"]["limitations"])
        assert "module-defined" in treatment
        assert "combine independently" not in treatment
    for edge in interface_for(s).transitions:
        assert result.annual[-1]["module_base_hazards_per_year"][edge.flow] == REGISTRY.value(
            edge.parameter
        )


@pytest.mark.parametrize("structure", ["legacy", "risk_1", "risk_2"])
def test_null_extension_changes_mechanism_without_changing_accounting(structure):
    s = scenario(health_structure=structure, diet_response={"kind": "dynamic"})
    null = simulate(REGISTRY, s, transition_module=NoDietEffect())
    baseline = simulate(REGISTRY, s.model_copy(update={"exposures": {"upf": 1.0}}))
    assert null.cohorts == baseline.cohorts
    assert null.healthspan == baseline.healthspan
    assert null.cohorts != simulate(REGISTRY, s).cohorts
    assert null.ending_population + null.cumulative_deaths == pytest.approx(
        null.starting_population
    )
    assert (
        REGISTRY.content_hash == EvidenceRegistry.from_yaml("evidence/parameters.yaml").content_hash
    )


class ExtraParameter(DietaryTransitions):
    def describe(self, interface):
        spec = super().describe(interface)
        return spec.model_copy(
            update={
                "parameters": (
                    *spec.parameters,
                    ParameterDependency(key="custom_scale", unit="fraction"),
                )
            }
        )

    def hazards(self, inputs):
        output = super().hazards(inputs)
        return Quantity(
            port=output.port, values=tuple(v * inputs.value("custom_scale") for v in output.values)
        )


class ReplacementRate(DietaryTransitions):
    def describe(self, interface):
        return (
            super()
            .describe(interface)
            .model_copy(
                update={
                    "parameters": (ParameterDependency(key="custom_rate", unit="hazard_per_year"),)
                }
            )
        )

    def hazards(self, inputs):
        return Quantity(
            port=inputs.interface.hazard_port,
            values=tuple(inputs.value("custom_rate") for _ in inputs.interface.transitions),
        )


def test_replacement_hazards_do_not_require_unused_baseline_parameters():
    r = REGISTRY.model_copy(deep=True)
    r.parameters["custom_rate"] = r.parameters["h_to_ir_rate"].model_copy(
        update={"key": "custom_rate"}
    )
    for edge in interface_for(scenario()).transitions:
        r.parameters[edge.parameter].unresolved = True
    with pytest.raises(ValueError, match="Unresolved"):
        simulate(r, scenario())
    result = simulate(r, scenario(), transition_module=ReplacementRate(), diagnostics=True)
    assert "custom_rate" in result.metadata["active_parameters"]
    assert not result.metadata["unresolved_parameters"]
    assert "h_to_ir_rate" not in result.metadata["active_parameters"]
    assert "h_to_ir_rate" in r.audit()["unresolved"]
    assert result.ending_population + result.cumulative_deaths == pytest.approx(
        result.starting_population
    )
    assert all("parameter" not in e for e in result.diagnostics["structure"]["transitions"])


def test_undeclared_parameter_access_and_context_mutation_fail():
    class Undeclared(DietaryTransitions):
        def hazards(self, inputs):
            inputs.value("mortality_t2d_ratio")

    with pytest.raises(KeyError, match="did not declare"):
        simulate(REGISTRY, scenario(), transition_module=Undeclared())

    class Mutates(DietaryTransitions):
        def hazards(self, inputs):
            inputs.parameters[0].value = 0

    with pytest.raises(ValidationError, match="frozen"):
        simulate(REGISTRY, scenario(), transition_module=Mutates())


def extra_registry():
    registry = REGISTRY.model_copy(deep=True)
    parameter = registry.parameters["initial_ir_share"].model_copy(update={"key": "custom_scale"})
    registry.parameters[parameter.key] = parameter
    return registry


def test_new_parameter_dependency_is_validated_and_reported():
    r = extra_registry()
    result = simulate(r, scenario(), transition_module=ExtraParameter())
    assert "custom_scale" in result.metadata["active_parameters"]
    assert "custom_scale" in result.metadata["synthetic_parameters"]
    assert result.metadata["transition_module"]["evidence_dependencies"][-1]["uncertainty"]
    expected = (
        r.value("custom_scale")
        * r.value("h_to_ir_rate")
        * result.annual[1]["applied_progression_multiplier"]
    )
    assert result.annual[1]["module_base_hazards_per_year"]["healthy_to_ir"] == pytest.approx(
        expected
    )
    assert result.metadata["evidence_sha256"] == r.content_hash
    for mutation in ("missing", "unit", "role", "unresolved", "uncertainty"):
        bad = extra_registry()
        if mutation == "missing":
            del bad.parameters["custom_scale"]
        elif mutation == "unit":
            bad.parameters["custom_scale"].unit = "people"
        elif mutation == "role":
            bad.parameters["custom_scale"].model_role = "benchmark_only"
        elif mutation == "unresolved":
            bad.parameters["custom_scale"].unresolved = True
        else:
            bad.parameters["custom_scale"].uncertainty = None
        with pytest.raises(ValueError):
            simulate(bad, scenario(), transition_module=ExtraParameter())
    with pytest.raises(ValueError, match="redefine core parameter units"):
        required_units(scenario(), transition_parameters={"mortality_t2d_ratio": "fraction"})


@pytest.mark.parametrize(
    "change",
    [
        {"api_version": "2.0"},
        {"domain": "agriculture"},
        {"step_years": 0.5},
        {"inputs": ()},
        {"outputs": ()},
    ],
)
def test_adapter_rejects_unsupported_contract_before_calling_equations(change):
    class Invalid(DietaryTransitions):
        def describe(self, interface):
            return super().describe(interface).model_copy(update=change)

        def hazards(self, inputs):
            raise AssertionError("Incompatible module must not execute")

    with pytest.raises(ValueError):
        simulate(REGISTRY, scenario(), transition_module=Invalid())


@pytest.mark.parametrize("bad", ["negative", "nan", "shape", "units", "axis", "untyped"])
def test_adapter_revalidates_returned_values_even_if_model_construct_bypasses_validation(bad):
    class Invalid(DietaryTransitions):
        def hazards(self, inputs):
            value = super().hazards(inputs)
            data = value.model_dump()
            if bad == "negative":
                data["values"] = (-1, 0, 0)
            elif bad == "nan":
                data["values"] = (np.nan, 0, 0)
            elif bad == "shape":
                data["values"] = (0,)
            elif bad == "units":
                data["port"]["unit"] = "probability"
            elif bad == "axis":
                data["port"]["axes"][0]["labels"] = tuple(
                    reversed(data["port"]["axes"][0]["labels"])
                )
            else:
                return data
            return Quantity.model_construct(
                port=Port.model_validate(data["port"]), values=data["values"]
            )

    with pytest.raises((ValueError, TypeError)):
        simulate(REGISTRY, scenario(), transition_module=Invalid())


def test_typed_output_series_preserve_stocks_flows_and_time_intervals():
    result = simulate(REGISTRY, scenario(), transition_module=NoDietEffect())
    series = simulation_series(result)
    assert len(series["population"].rows) == 4
    assert len(series["deaths"].rows) == 3
    assert series["population"].times_years == series["deaths"].times_years == (0, 1, 2, 3)
    population = [q.values[0] for q in series["population"].rows]
    deaths = [q.values[0] for q in series["deaths"].rows]
    assert population[-1] + sum(deaths) == pytest.approx(population[0])
    assert [q.values[0] for q in series["healthy_to_ir"].rows] == [
        r["healthy_to_ir"] for r in result.annual[1:]
    ]
    assert all(s.uncertainty == "conditional" for s in series.values())


def test_routing_and_scientific_gates_do_not_silently_use_custom_equations():
    with pytest.raises(ValueError, match="canonical transition"):
        simulate(
            REGISTRY,
            scenario(),
            transition_module=NoDietEffect(),
            dietary_reference=scenario(),
            dietary_paths=(),
        )
    with pytest.raises(ValueError, match="Scientific mode blocked"):
        simulate(REGISTRY, scenario(mode="scientific"), transition_module=NoDietEffect())


def test_cli_and_library_load_explicit_module_and_keep_example_independent_of_core(tmp_path):
    reference = "demeter.examples.transition_modules:NoDietEffect"
    assert isinstance(load_transition_module(reference), NoDietEffect)
    for bad in ("no_factory", "module:lambda:1", "../file:Class"):
        with pytest.raises(ValueError):
            load_transition_module(bad)
    output = tmp_path / "simulation.json"
    response = CliRunner().invoke(
        app,
        [
            "simulate",
            "scenarios/reduce_upf_30.yaml",
            "--transition-module",
            reference,
            "--output",
            str(output),
        ],
    )
    assert response.exit_code == 0, response.output
    report = json.loads(output.read_text())
    assert report["metadata"]["transition_module"]["spec"]["module_id"] == "example.no_diet_effect"
    assert report["metadata"]["transition_module"]["factory_reference"] == reference
    assert report["validation_only"]
    assert report == json.loads(response.output)
    tree = ast.parse(Path("src/demeter/examples/transition_modules.py").read_text())
    assert all(
        n.module == "demeter.contracts" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
    )
    assert ModuleSpec.model_json_schema()["properties"]["domain"]
