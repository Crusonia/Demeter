"""Audited adapter from the public hazard-module contract to the health engine."""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from pathlib import Path

from demeter.contracts import (
    API_VERSION,
    Axis,
    ModuleSpec,
    ParameterValue,
    Port,
    Quantity,
    Transition,
    TransitionInputs,
    TransitionInterface,
    TransitionModule,
    TimeSeries,
    require_api,
    require_connection,
)
from demeter.health.structure import states_for, transitions_for


def simulation_series(result) -> dict[str, TimeSeries]:
    """Typed annual stocks/interval flows from a SimulationResult, without recalculation."""
    times = tuple(float(r["year"]) for r in result.annual)
    specs = [
        (key, "stock", "point", result.annual)
        for key in ("population", *result.ending_state_shares)
    ] + [
        (key, "flow", "interval_total", result.annual[1:])
        for key in ("deaths", *result.metadata["transition_flows"])
    ]
    output = {}
    for key, kind, temporal, rows in specs:
        port = Port(
            name=key,
            kind=kind,
            unit="people",
            temporal=temporal,
            definition="Living population at boundary"
            if kind == "stock"
            else "People moved during the preceding annual interval",
        )
        output[key] = TimeSeries(
            times_years=times,
            rows=tuple(Quantity(port=port, values=(row[key],)) for row in rows),
            evidence_keys=tuple(result.metadata["active_parameters"]),
            uncertainty="conditional",
        )
    return output


def interface_for(scenario):
    states = states_for(scenario)
    edges = tuple(Transition(**e) for e in transitions_for(scenario))
    return TransitionInterface(
        structure=scenario.health_structure,
        states=states,
        transitions=edges,
        stock_port=Port(
            name="population.health",
            kind="stock",
            unit="people",
            temporal="point",
            axes=(
                Axis(name="age", labels=tuple(map(str, range(100))) + ("100+",)),
                Axis(name="state", labels=states),
            ),
            definition="Start-of-year living population before mortality; adult eligibility is applied by the engine",
        ),
        progression_port=Port(
            name="nutrition.progression",
            kind="auxiliary",
            unit="multiplier",
            temporal="point",
            definition="Current year-end dietary progression hazard multiplier",
        ),
        recovery_port=Port(
            name="nutrition.recovery",
            kind="auxiliary",
            unit="multiplier",
            temporal="point",
            definition="Current year-end dietary recovery hazard multiplier",
        ),
        hazard_port=Port(
            name="health.transition_hazards",
            kind="hazard",
            unit="hazard_per_year",
            temporal="rate",
            axes=(Axis(name="transition", labels=tuple(e.flow for e in edges)),),
            definition="Adult base hazards before GLP-1 modifiers; competing exits handled by engine",
        ),
    )


def load_transition_module(reference: str) -> TransitionModule:
    """Explicit import of a trusted zero-argument factory; never discover plugins."""
    module_name, separator, factory_name = reference.partition(":")
    if (
        not separator
        or not all(s.isidentifier() for s in module_name.split("."))
        or not factory_name.isidentifier()
    ):
        raise ValueError("Module reference must be importable.package:factory")
    module = getattr(importlib.import_module(module_name), factory_name)()
    if not callable(getattr(module, "describe", None)) or not callable(
        getattr(module, "hazards", None)
    ):
        raise TypeError("Factory must return a TransitionModule with describe and hazards methods")
    return module


class BoundTransitionModule:
    def __init__(self, module, registry, scenario):
        self.module = module
        self.interface = interface_for(scenario)
        raw = module.describe(self.interface)
        if not isinstance(raw, ModuleSpec):
            raise TypeError("Module describe must return ModuleSpec")
        self.spec = ModuleSpec.model_validate(raw.model_dump())
        require_api(self.spec.api_version)
        if self.spec.domain != "health" or self.spec.step_years != 1:
            raise ValueError("The current adapter accepts annual health hazard modules only")
        expected = (
            self.interface.stock_port,
            self.interface.progression_port,
            self.interface.recovery_port,
        )
        if self.spec.inputs != expected or self.spec.outputs != (self.interface.hazard_port,):
            raise ValueError("Module ports must match the supplied health transition interface")
        params = []
        for dependency in self.spec.parameters:
            p = registry.parameters.get(dependency.key)
            if p is None or p.unit != dependency.unit or p.model_role != "health_model":
                raise ValueError(f"Invalid module evidence dependency: {dependency.key}")
            if p.uncertainty is None:
                raise ValueError(f"Module parameter needs explicit uncertainty: {dependency.key}")
            params.append(
                ParameterValue(
                    key=p.key,
                    value=registry.value(p.key),
                    unit=p.unit,
                    status=p.status,
                    evidence_grade=p.evidence_grade,
                    evidence_json=p.model_dump_json(),
                )
            )
        self.parameters = tuple(params)
        self.scenario_json = scenario.model_dump_json()
        # The class file is fingerprinted, not an unverified user-provided hash.
        source = inspect.getsourcefile(type(module))
        if not source or not Path(source).is_file():
            raise ValueError("A module must have inspectable Python source for provenance")
        self.provenance = {
            "api_version": API_VERSION,
            "classification": "experimental",
            "spec": self.spec.model_dump(mode="json"),
            "implementation": f"{type(module).__module__}:{type(module).__qualname__}",
            "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
            "evidence_dependencies": [json.loads(p.evidence_json) for p in self.parameters],
            "uncertainty": "One deterministic evaluation conditional on supplied parameter values; no extra sampling inside module",
            "limitations": "Source hash covers the class file, not transitive imports. Preserve source package and locked environment for replay. Extensions do not establish scientific readiness.",
        }

    def rates(self, year, stocks, progression, recovery):
        inputs = TransitionInputs(
            year=year,
            scenario_json=self.scenario_json,
            interface=self.interface,
            stocks=Quantity(port=self.interface.stock_port, values=tuple(stocks.ravel())),
            progression=Quantity(port=self.interface.progression_port, values=(progression,)),
            recovery=Quantity(port=self.interface.recovery_port, values=(recovery,)),
            parameters=self.parameters,
        )
        raw = self.module.hazards(inputs)
        if not isinstance(raw, Quantity):
            raise TypeError("Module hazards must return a Quantity")
        output = Quantity.model_validate(raw.model_dump())
        require_connection(output.port, self.interface.hazard_port)
        return output.values
