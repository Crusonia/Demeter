"""Preserve explicit normalized observations without inferring clinical states."""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Nonnegative = Annotated[Finite, Field(ge=0)]
Text = Annotated[str, Field(strict=True, min_length=1)]


class _StrictObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class RelativeDayTime(_StrictObservation):
    """A supplied randomization-relative time; no calendar/year conversion."""

    kind: Literal["exact", "interval", "unknown"] = "unknown"
    day: Finite | None = None
    lower_day: Finite | None = None
    upper_day: Finite | None = None
    unit: Literal["relative_day"] = "relative_day"

    @model_validator(mode="after")
    def consistent_representation(self):
        if self.kind == "exact":
            valid = self.day is not None and self.lower_day is None and self.upper_day is None
        elif self.kind == "interval":
            valid = (
                self.day is None
                and self.lower_day is not None
                and self.upper_day is not None
                and self.lower_day < self.upper_day
            )
        else:
            valid = self.day is None and self.lower_day is None and self.upper_day is None
        if not valid:
            raise ValueError("Time kind must match its explicit exact/interval/unknown values")
        return self

    def bounds(self) -> tuple[float, float] | None:
        if self.kind == "exact":
            return self.day, self.day
        if self.kind == "interval":
            return self.lower_day, self.upper_day
        return None


class SourceEventsSummary(_StrictObservation):
    """Source endpoint summaries keep their units and follow-up-specific meaning."""

    diagnosed_during_source_followup: bool | None = None
    prior_diabetes_diagnosis: bool | None = None
    diabetes_type: Text | None = None
    source_glucose_endpoint_years: Nonnegative | None = None
    source_visit_group: Annotated[int, Field(strict=True, ge=1, le=10)] | None = None
    source_last_visit_years: Nonnegative | None = None
    source_year_unit: Literal["source_reported_year"] = "source_reported_year"
    death_status: bool | None = None
    death_time: RelativeDayTime = Field(default_factory=RelativeDayTime)

    @model_validator(mode="after")
    def death_not_before_randomization(self):
        bounds = self.death_time.bounds()
        if bounds is not None and bounds[0] < 0:
            raise ValueError("Death time cannot precede the explicit randomization origin")
        return self


class GlucoseObservation(_StrictObservation):
    observation_id: Text
    test: Literal["fasting_glucose", "ogtt_2h"]
    time: RelativeDayTime = Field(default_factory=RelativeDayTime)
    status: Literal["observed", "missing", "unknown"] = "unknown"
    value: Nonnegative | None = None
    unit: Text | None = None
    unit_status: Literal["documented", "unresolved"] = "unresolved"
    source_missing_code: Text | None = None
    visit_purpose: Literal[
        "scheduled", "confirmation", "post_confirmed_outcome", "other", "unknown"
    ] = "unknown"

    @model_validator(mode="after")
    def value_and_status_agree(self):
        if (self.status == "observed") != (self.value is not None):
            raise ValueError("Observed tests require a value; missing/unknown tests have no value")
        if self.unit_status == "documented" and self.unit is None:
            raise ValueError("A documented unit must be explicitly supplied")
        if self.status == "observed" and self.source_missing_code is not None:
            raise ValueError("A measured value cannot simultaneously carry a missing-test code")
        return self


class DiagnosisObservation(_StrictObservation):
    """A supplied confirmation outcome, never inferred from glucose or visit purpose."""

    outcome: Literal["confirmed", "not_confirmed", "unknown"] = "unknown"
    first_positive_time: RelativeDayTime = Field(default_factory=RelativeDayTime)
    confirmation_time: RelativeDayTime = Field(default_factory=RelativeDayTime)
    source_definition: Text | None = None
    test_reference_ids: tuple[Text, ...] = ()

    @field_validator("test_reference_ids", mode="before")
    @classmethod
    def accept_wire_list(cls, value):
        return tuple(value) if type(value) is list else value


class TreatmentChange(_StrictObservation):
    treatment: Text
    action: Literal["start", "stop", "change", "unknown"] = "unknown"
    time: RelativeDayTime = Field(default_factory=RelativeDayTime)
    detail: Text | None = None


class FollowUp(_StrictObservation):
    last_glucose_time: RelativeDayTime = Field(default_factory=RelativeDayTime)
    last_contact_time: RelativeDayTime = Field(default_factory=RelativeDayTime)
    censoring_reason: Literal[
        "administrative_end", "lost", "withdrawn", "diagnosis", "death", "unknown"
    ] = "unknown"


class ParticipantObservations(_StrictObservation):
    record_id: Text
    events: SourceEventsSummary = Field(default_factory=SourceEventsSummary)
    glucose_observations: tuple[GlucoseObservation, ...] = ()
    diagnosis_observations: tuple[DiagnosisObservation, ...] = ()
    treatment_changes: tuple[TreatmentChange, ...] = ()
    follow_up: FollowUp = Field(default_factory=FollowUp)
    test_history_complete: bool | None = None
    treatment_history_complete: bool | None = None

    @field_validator(
        "glucose_observations", "diagnosis_observations", "treatment_changes", mode="before"
    )
    @classmethod
    def accept_wire_list(cls, value):
        return tuple(value) if type(value) is list else value

    @model_validator(mode="after")
    def unique_and_valid_test_references(self):
        ids = [observation.observation_id for observation in self.glucose_observations]
        if len(ids) != len(set(ids)):
            raise ValueError("Glucose observation IDs must be unique within each participant")
        for diagnosis in self.diagnosis_observations:
            references = diagnosis.test_reference_ids
            if len(references) != len(set(references)) or not set(references) <= set(ids):
                raise ValueError(
                    "Diagnosis references must name distinct supplied glucose observations"
                )
        return self


class ObservationBatch(_StrictObservation):
    schema_version: Literal["clinical_observations_v1"] = "clinical_observations_v1"
    source_id: Text
    source_version: Text
    synthetic: bool
    relative_day_origin: Literal["randomization"]
    relative_day_unit: Literal["relative_day"]
    participants: tuple[ParticipantObservations, ...]

    @field_validator("participants", mode="before")
    @classmethod
    def accept_wire_list(cls, value):
        # JSON arrays remain the wire format; do not coerce other iterables or deduplicate.
        return tuple(value) if type(value) is list else value

    @model_validator(mode="after")
    def unique_participants(self):
        ids = [participant.record_id for participant in self.participants]
        if len(ids) != len(set(ids)):
            raise ValueError("Participant IDs must be unique in the normalized batch")
        return self


def preserve_observations(payload: dict) -> ObservationBatch:
    """Validate supplied observations in memory; perform no I/O or inference."""
    return ObservationBatch.model_validate(payload)


def _status(value: bool | None) -> str:
    return "yes" if value is True else "no" if value is False else "unknown"


def _before(left: RelativeDayTime, right: RelativeDayTime) -> bool:
    left_bounds, right_bounds = left.bounds(), right.bounds()
    return left_bounds is not None and right_bounds is not None and left_bounds[1] < right_bounds[0]


def summarize_observations(batch: ObservationBatch) -> dict:
    """Aggregate preserved observations; emit no participant IDs or clinical fit."""
    participants = batch.participants
    glucose = [item for p in participants for item in p.glucose_observations]
    diagnosis = [item for p in participants for item in p.diagnosis_observations]
    treatment = [item for p in participants for item in p.treatment_changes]
    issues = Counter()
    contradictions = Counter()
    for p in participants:
        events = p.events
        if events.diagnosed_during_source_followup is None:
            issues["diagnosis_during_followup_unknown"] += 1
        if events.prior_diabetes_diagnosis is None:
            issues["prior_diagnosis_unknown"] += 1
        if events.diabetes_type is None:
            issues["diabetes_type_unknown"] += 1
        if events.death_status is None:
            issues["death_status_unknown"] += 1
            if events.death_time.kind != "unknown":
                issues["death_time_without_known_death_status"] += 1
        if events.death_status is True and events.death_time.kind == "unknown":
            issues["death_time_unknown"] += 1
        if events.death_status is False and events.death_time.kind != "unknown":
            contradictions["death_time_with_explicit_no_death"] += 1
        if any(
            value is not None
            for value in (events.source_glucose_endpoint_years, events.source_last_visit_years)
        ):
            issues["source_year_to_day_conversion_unresolved"] += 1
        if events.source_visit_group is not None:
            issues["grouped_visit_interval_unresolved"] += 1
        if events.source_glucose_endpoint_years is not None and (
            events.diagnosed_during_source_followup is None
        ):
            issues["source_glucose_endpoint_meaning_unknown"] += 1
        if p.test_history_complete is not True:
            issues["test_history_completeness_unresolved"] += 1
        if p.treatment_history_complete is not True:
            issues["treatment_history_completeness_unresolved"] += 1
        if p.follow_up.last_glucose_time.kind == "unknown":
            issues["last_glucose_time_unknown"] += 1
        if p.follow_up.last_contact_time.kind == "unknown":
            issues["last_contact_time_unknown"] += 1
        if p.follow_up.censoring_reason == "unknown":
            issues["censoring_reason_unknown"] += 1
        if _before(p.follow_up.last_contact_time, p.follow_up.last_glucose_time):
            contradictions["last_contact_before_last_glucose"] += 1
        if events.death_status is True and _before(
            events.death_time, p.follow_up.last_glucose_time
        ):
            contradictions["last_glucose_after_death"] += 1
        confirmed = [item for item in p.diagnosis_observations if item.outcome == "confirmed"]
        if events.diagnosed_during_source_followup is True and not confirmed:
            issues["confirmation_observation_unavailable"] += 1
        if events.diagnosed_during_source_followup is False and confirmed:
            issues["confirmation_vs_source_followup_scope_unresolved"] += 1
        for item in p.diagnosis_observations:
            if item.outcome == "unknown":
                issues["confirmation_outcome_unknown"] += 1
            if item.source_definition is None:
                issues["confirmation_definition_unknown"] += 1
            if item.first_positive_time.kind == "unknown":
                issues["first_positive_time_unknown"] += 1
            if item.confirmation_time.kind == "unknown":
                issues["confirmation_time_unknown"] += 1
            if _before(item.confirmation_time, item.first_positive_time):
                contradictions["confirmation_before_first_positive"] += 1
        for item in p.glucose_observations:
            if item.status != "observed":
                issues["glucose_value_unobserved"] += 1
            if item.unit_status != "documented":
                issues["glucose_unit_unresolved"] += 1
            if item.time.kind == "unknown":
                issues["glucose_collection_time_unknown"] += 1
            if item.status == "observed" and _before(p.follow_up.last_glucose_time, item.time):
                contradictions["glucose_collection_after_last_glucose"] += 1
            if events.death_status is True and _before(events.death_time, item.time):
                if item.status == "observed":
                    contradictions["glucose_collection_after_death"] += 1
                else:
                    # A dated unmeasured item does not establish that a specimen
                    # was collected. Preserve the source's unresolved time role.
                    issues["unobserved_glucose_time_after_death_role_unresolved"] += 1
        for item in p.treatment_changes:
            if item.action == "unknown" or item.time.kind == "unknown":
                issues["treatment_change_unresolved"] += 1
            if (
                item.action != "unknown"
                and events.death_status is True
                and _before(events.death_time, item.time)
            ):
                contradictions["treatment_change_after_death"] += 1

    def tally(values) -> dict:
        return dict(sorted(Counter(values).items()))

    return {
        "schema_version": batch.schema_version,
        "kind": "clinical_observation_preservation",
        "model_role": "benchmark_only",
        "validation_only": True,
        "scientific_release_ready": False,
        "clinical_fit_allowed": False,
        "state_activation_allowed": False,
        "source_importer_certified": False,
        "source": {
            "source_id": batch.source_id,
            "source_version": batch.source_version,
            "synthetic": batch.synthetic,
            "relative_day_origin": batch.relative_day_origin,
            "relative_day_unit": batch.relative_day_unit,
            "source_year_unit": "source_reported_year",
        },
        "counts": {
            "participants": len(participants),
            "glucose_observations": len(glucose),
            "diagnosis_observations": len(diagnosis),
            "treatment_changes": len(treatment),
        },
        "source_events": {
            "diagnosed_during_source_followup": tally(
                _status(p.events.diagnosed_during_source_followup) for p in participants
            ),
            "prior_diabetes_diagnosis": tally(
                _status(p.events.prior_diabetes_diagnosis) for p in participants
            ),
            "death_status": tally(_status(p.events.death_status) for p in participants),
            "death_time_kind": tally(p.events.death_time.kind for p in participants),
            "source_glucose_endpoint_years_present": sum(
                p.events.source_glucose_endpoint_years is not None for p in participants
            ),
            "source_last_visit_years_present": sum(
                p.events.source_last_visit_years is not None for p in participants
            ),
            "source_visit_group_present": sum(
                p.events.source_visit_group is not None for p in participants
            ),
        },
        "glucose": {
            test: {
                "status": tally(item.status for item in glucose if item.test == test),
                "time_kind": tally(item.time.kind for item in glucose if item.test == test),
                "unit_status": tally(item.unit_status for item in glucose if item.test == test),
            }
            for test in ("fasting_glucose", "ogtt_2h")
        },
        "visit_purpose": tally(item.visit_purpose for item in glucose),
        "diagnosis": {
            "outcome": tally(item.outcome for item in diagnosis),
            "first_positive_time_kind": tally(item.first_positive_time.kind for item in diagnosis),
            "confirmation_time_kind": tally(item.confirmation_time.kind for item in diagnosis),
        },
        "follow_up": {
            "last_glucose_time_kind": tally(
                p.follow_up.last_glucose_time.kind for p in participants
            ),
            "last_contact_time_kind": tally(
                p.follow_up.last_contact_time.kind for p in participants
            ),
            "censoring_reason": tally(p.follow_up.censoring_reason for p in participants),
        },
        "unresolved_observations": dict(sorted(issues.items())),
        "contradictions": dict(sorted(contradictions.items())),
        "fit_blockers": [
            "No clinical observation likelihood or physiological-state mapping is implemented",
            "Normalized input does not verify a source importer or identify clinical causal rates",
            "Unknown observations and unresolved timing/unit/history issues block dependent fits",
        ],
        "interpretation": (
            "Observation preservation only; no clinical thresholds, year/day conversion, inferred "
            "negative tests, biological onset, remission, engine states or causal effects"
        ),
    }
