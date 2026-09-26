from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


ParameterStatus = Literal["synthetic", "estimated", "observed", "derived"]
EvidenceGrade = Literal["A", "B", "C", "D", "E"]


class Uncertainty(BaseModel):
    kind: str
    low: float | None = None
    high: float | None = None
    sd: float | None = None


class EvidenceParameter(BaseModel):
    key: str
    value: float
    unit: str
    status: ParameterStatus
    evidence_grade: EvidenceGrade
    source: str
    source_url: str | None = None
    population: str | None = None
    geography: str | None = None
    time_period: str | None = None
    uncertainty: Uncertainty | None = None
    notes: str | None = None


class EvidenceRegistry(BaseModel):
    parameters: dict[str, EvidenceParameter]

    @model_validator(mode="after")
    def keys_match(self) -> EvidenceRegistry:
        for key, parameter in self.parameters.items():
            if parameter.key != key:
                raise ValueError(f"registry key {key!r} does not match parameter.key {parameter.key!r}")
        return self

    @classmethod
    def from_yaml(cls, path: str | Path) -> EvidenceRegistry:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def value(self, key: str) -> float:
        return self.parameters[key].value

    @property
    def contains_synthetic(self) -> bool:
        return any(p.status == "synthetic" for p in self.parameters.values())


class Scenario(BaseModel):
    name: str
    description: str = ""
    years: int = Field(default=25, ge=1, le=100)
    exposures: dict[str, float]

    @classmethod
    def from_yaml(cls, path: str | Path) -> Scenario:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    @model_validator(mode="after")
    def exposure_values_are_positive(self) -> Scenario:
        bad = {k: v for k, v in self.exposures.items() if v <= 0}
        if bad:
            raise ValueError(f"exposure multipliers must be positive: {bad}")
        return self
