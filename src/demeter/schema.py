from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class Uncertainty(StrictModel):
    kind: Literal["fixed", "uniform", "normal", "range", "interval"]
    low: float | None = None
    high: float | None = None
    sd: float | None = Field(default=None, gt=0)
    rationale: str = ""

    @model_validator(mode="after")
    def valid_distribution(self):
        if self.kind in ("uniform", "range", "interval"):
            if self.low is None or self.high is None or self.low >= self.high:
                raise ValueError("interval requires finite low < high")
        if self.kind == "normal" and self.sd is None:
            raise ValueError("normal distribution requires sd")
        if self.kind == "fixed" and not self.rationale:
            raise ValueError("fixed parameter requires rationale")
        return self


class EvidenceSource(StrictModel):
    """Pinned source receipt; article bytes stay in ignored raw storage."""

    url: str
    citation: str
    doi: str
    raw_filename: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: datetime
    license: str
    correction_url: str | None = None
    correction_note: str = ""

    @model_validator(mode="after")
    def safe_artifact(self):
        if Path(self.raw_filename).name != self.raw_filename or self.raw_filename in (
            "",
            ".",
            "..",
        ):
            raise ValueError("source raw_filename must be a filename, not a path")
        if self.retrieved_at.utcoffset() is None:
            raise ValueError("source retrieval time must include timezone")
        return self


class TableExtraction(StrictModel):
    table_index: int = Field(ge=0, strict=True)
    row_label: str
    row_occurrence: int = Field(default=0, ge=0, strict=True)
    column_index: int = Field(ge=1, strict=True)
    scale: float = Field(gt=0)


class EvidenceApplicability(StrictModel):
    """Record why a published estimate cannot yet replace an engine input."""

    candidate_for: list[str] = Field(min_length=1)
    estimand: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    source_population: str = Field(min_length=1)
    transport_status: Literal["benchmark_only"] = "benchmark_only"
    blockers: list[str] = Field(min_length=1)
    extraction: TableExtraction


class EvidenceParameter(StrictModel):
    key: str
    value: float | None
    unit: str
    status: Literal["synthetic", "estimated", "observed", "derived"]
    evidence_grade: Literal["A", "B", "C", "D", "E"]
    source: str
    source_url: str | None = None
    citation: str | None = None
    population: str | None = None
    geography: str | None = None
    time_period: str | None = None
    exposure_definition: str | None = None
    outcome_definition: str | None = None
    uncertainty: Uncertainty | None = None
    transformation: str | None = None
    model_role: Literal["health_model", "benchmark_only"] = "health_model"
    notes: str | None = None
    unresolved: bool = False
    lower_bound: float | None = None
    upper_bound: float | None = None
    source_id: str | None = None
    applicability: EvidenceApplicability | None = None

    @model_validator(mode="after")
    def valid_value(self):
        if self.applicability and (not self.source_id or self.model_role != "benchmark_only"):
            raise ValueError(
                "appraised candidate evidence requires a source and benchmark_only role"
            )
        if self.value is None and not self.unresolved:
            raise ValueError("missing value must be marked unresolved")
        if self.status == "synthetic" and self.evidence_grade != "E":
            raise ValueError("synthetic parameters require evidence grade E")
        values = [self.value]
        if self.uncertainty:
            values += [self.uncertainty.low, self.uncertainty.high]
        for value in values:
            if value is not None and (
                self.lower_bound is not None
                and value < self.lower_bound
                or self.upper_bound is not None
                and value > self.upper_bound
            ):
                raise ValueError(f"{self.key}: value/distribution outside parameter bounds")
        return self


class EvidenceRegistry(StrictModel):
    parameters: dict[str, EvidenceParameter]
    datasets: dict[str, dict] = Field(default_factory=dict)
    scientific_blockers: list[str] = Field(default_factory=list)
    sources: dict[str, EvidenceSource] = Field(default_factory=dict)

    @model_validator(mode="after")
    def keys_match(self):
        for key, parameter in self.parameters.items():
            if key != parameter.key:
                raise ValueError(f"registry key {key!r} does not match parameter.key")
            if parameter.source_id and parameter.source_id not in self.sources:
                raise ValueError(f"{key}: missing source receipt {parameter.source_id}")
            if (
                parameter.source_id
                and parameter.source_url != self.sources[parameter.source_id].url
            ):
                raise ValueError(f"{key}: source URL does not match the pinned receipt")
            if parameter.applicability:
                for target in parameter.applicability.candidate_for:
                    if target not in self.parameters:
                        raise ValueError(f"{key}: unknown candidate target {target}")
        return self

    @classmethod
    def from_yaml(cls, path: str | Path):
        return cls.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    def value(self, key: str) -> float:
        parameter = self.parameters[key]
        if parameter.value is None or parameter.unresolved:
            raise ValueError(f"Unresolved evidence parameter: {key}")
        return parameter.value

    @property
    def contains_synthetic(self) -> bool:
        return any(p.status == "synthetic" for p in self.parameters.values())

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()

    def audit(self) -> dict:
        p = self.parameters
        return {
            "parameter_count": len(p),
            "content_sha256": self.content_hash,
            "status_counts": dict(Counter(v.status for v in p.values())),
            "grade_counts": dict(Counter(v.evidence_grade for v in p.values())),
            "synthetic": [k for k, v in p.items() if v.status == "synthetic"],
            "unresolved": [k for k, v in p.items() if v.unresolved or v.value is None],
            "missing_uncertainty": [k for k, v in p.items() if v.uncertainty is None],
            "missing_provenance": [
                k
                for k, v in p.items()
                if v.status != "synthetic"
                and not all((v.source_url, v.population, v.geography, v.time_period))
            ],
            "scientific_blockers": self.scientific_blockers,
            "benchmark_only": [k for k, v in p.items() if v.model_role == "benchmark_only"],
            "source_receipts": len(self.sources),
            "appraised_candidates": {
                k: v.applicability.model_dump() for k, v in p.items() if v.applicability is not None
            },
        }


class Scenario(StrictModel):
    name: str = Field(min_length=1)
    description: str = ""
    years: int = Field(default=25, ge=1, le=100, strict=True)
    exposures: dict[Literal["upf", "fiber", "fruit_veg"], float]
    baseline_year: Literal[2022, 2023, 2024] = 2024
    sex: Literal["all", "male", "female"] = "all"
    mode: Literal["validation", "scientific"] = "validation"
    allow_extrapolation: bool = False

    @classmethod
    def from_yaml(cls, path: str | Path):
        return cls.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    @model_validator(mode="after")
    def valid_exposures(self):
        if any(v <= 0 for v in self.exposures.values()):
            raise ValueError("exposure multipliers must be positive")
        if any(self.exposures.get(k, 1) != 1 for k in ("fiber", "fruit_veg")):
            raise ValueError(
                "v0.1 changes only UPF; correlated exposure effects are not independently identified"
            )
        return self
