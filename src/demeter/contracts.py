"""Public module API 1.0: explicit units, time, evidence and immutable exchanges."""

from __future__ import annotations

from math import prod
import re
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

API_VERSION = "1.0"
Domain = Literal[
    "population", "health", "nutrition", "economics", "agriculture", "provider", "intervention"
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Axis(Contract):
    name: str = Field(min_length=1)
    labels: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.labels)) != len(self.labels):
            raise ValueError("Axis labels must be unique")
        return self


class Port(Contract):
    name: str = Field(min_length=1)
    kind: Literal["stock", "flow", "hazard", "auxiliary"]
    unit: str = Field(min_length=1)
    axes: tuple[Axis, ...] = ()
    temporal: Literal["point", "rate", "interval_total"]
    definition: str = Field(min_length=1)

    @model_validator(mode="after")
    def semantics(self):
        if len({a.name for a in self.axes}) != len(self.axes):
            raise ValueError("Axis names must be unique")
        if self.kind == "stock" and self.temporal != "point":
            raise ValueError("Stocks are point-in-time quantities")
        if self.kind == "hazard" and self.temporal != "rate":
            raise ValueError("Hazards are rates, not interval probabilities")
        if self.kind == "flow" and self.temporal == "point":
            raise ValueError("Flows require a rate or an interval total")
        return self


def require_connection(producer: Port, consumer: Port) -> None:
    """Exact semantic match; conversions/aggregation require an explicit adapter."""
    if producer != consumer:
        raise ValueError(
            "Incompatible ports: quantity key, definition, kind, units, ordered axes and time basis must match"
        )


class Quantity(Contract):
    port: Port
    values: tuple[float, ...]

    @model_validator(mode="after")
    def shape(self):
        if len(self.values) != prod(len(a.labels) for a in self.port.axes):
            raise ValueError("Values must match the flattened, row-major labelled shape")
        if self.port.kind in ("stock", "hazard") and any(v < 0 for v in self.values):
            raise ValueError("Stocks and hazards must be nonnegative")
        return self


class TimeSeries(Contract):
    """Points use sample times; interval totals use one more boundary than rows."""

    times_years: tuple[float, ...] = Field(min_length=1)
    rows: tuple[Quantity, ...] = Field(min_length=1)
    uncertainty: Literal["fixed", "conditional", "sample"] = "conditional"
    draw_id: str | None = Field(default=None, min_length=1)
    evidence_keys: tuple[str, ...] = ()

    @model_validator(mode="after")
    def aligned(self):
        if any(b <= a for a, b in zip(self.times_years, self.times_years[1:], strict=False)):
            raise ValueError("Time coordinates must be strictly increasing")
        for row in self.rows[1:]:
            if row.port != self.rows[0].port:
                raise ValueError("A time series cannot change its quantity definition")
        extra = int(self.rows[0].port.temporal == "interval_total")
        if len(self.times_years) != len(self.rows) + extra:
            raise ValueError("Time coordinates do not match point/interval rows")
        if (self.uncertainty == "sample") != (self.draw_id is not None):
            raise ValueError("Only sampled series require a draw identifier")
        return self


class ParameterDependency(Contract):
    key: str = Field(min_length=1)
    unit: str = Field(min_length=1)


class ModuleSpec(Contract):
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    api_version: str = Field(default=API_VERSION, pattern=r"^\d+\.\d+$")
    domain: Domain
    step_years: float = Field(gt=0)
    inputs: tuple[Port, ...]
    outputs: tuple[Port, ...]
    parameters: tuple[ParameterDependency, ...]
    equations: str = Field(min_length=1)
    limitations: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_declarations(self):
        for names in (
            [p.name for p in self.inputs],
            [p.name for p in self.outputs],
            [p.key for p in self.parameters],
        ):
            if len(set(names)) != len(names):
                raise ValueError("Module declarations must have unique names")
        return self


def require_api(version: str) -> None:
    if re.fullmatch(r"\d+\.\d+", version) is None:
        raise ValueError("Module API version must be major.minor")
    requested = tuple(map(int, version.split(".")))
    supported = tuple(map(int, API_VERSION.split(".")))
    if len(requested) != 2 or requested[0] != supported[0] or requested[1] > supported[1]:
        raise ValueError(f"Unsupported module API {version}; runtime provides {API_VERSION}")


class Transition(Contract):
    flow: str
    source: str
    target: str
    parameter: str


class TransitionInterface(Contract):
    structure: Literal["legacy", "risk_1", "risk_2"]
    states: tuple[str, ...]
    transitions: tuple[Transition, ...]
    stock_port: Port
    progression_port: Port
    recovery_port: Port
    hazard_port: Port


class ParameterValue(Contract):
    key: str
    value: float
    unit: str
    status: Literal["synthetic", "estimated", "observed", "derived"]
    evidence_grade: Literal["A", "B", "C", "D", "E"]
    evidence_json: str


class TransitionInputs(Contract):
    year: int = Field(ge=1, strict=True)
    step_years: Literal[1.0] = 1.0
    scenario_json: str
    interface: TransitionInterface
    stocks: Quantity
    progression: Quantity
    recovery: Quantity
    parameters: tuple[ParameterValue, ...]

    def value(self, key: str) -> float:
        for p in self.parameters:
            if p.key == key:
                return p.value
        raise KeyError(f"Module did not declare parameter {key}")


class TransitionModule(Protocol):
    """A deterministic, stateless annual hazard equation; the engine owns flows."""

    def describe(self, interface: TransitionInterface) -> ModuleSpec: ...

    def hazards(self, inputs: TransitionInputs) -> Quantity: ...
