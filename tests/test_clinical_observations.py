"""Registered arbitrary synthetic histories test preservation, not clinical effects."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from demeter.data.clinical_observations import (
    RelativeDayTime,
    preserve_observations,
    summarize_observations,
)
from demeter.schema import EvidenceRegistry

WITNESS = "dpp_observation_software_witness"
COLLECTION_FIELDS = (
    "participants",
    "glucose_observations",
    "diagnosis_observations",
    "treatment_changes",
    "test_reference_ids",
)


@pytest.fixture
def registered_payload():
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = registry.datasets[WITNESS]
    protocol_bytes = Path(spec["protocol_path"]).read_bytes()
    protocol = json.loads(protocol_bytes)
    assert hashlib.sha256(protocol_bytes).hexdigest() == spec["protocol_sha256"]
    assert spec["status"] == "synthetic"
    assert spec["evidence_grade"] == "E"
    assert spec["model_role"] == "benchmark_only"
    assert spec["input"] == protocol["software_witness"]["input"]
    return copy.deepcopy(spec["input"])


def test_preserves_history_measurements_and_distinct_times_without_inference(registered_payload):
    original = copy.deepcopy(registered_payload)
    batch = preserve_observations(registered_payload)
    confirmed, noncase, death = batch.participants
    assert confirmed.events.diagnosed_during_source_followup is True
    assert confirmed.events.prior_diabetes_diagnosis is None
    assert confirmed.events.diabetes_type is None
    diagnosis = confirmed.diagnosis_observations[0]
    assert diagnosis.first_positive_time.day != diagnosis.confirmation_time.day
    assert diagnosis.outcome == "confirmed"
    assert confirmed.glucose_observations[-1].value < confirmed.glucose_observations[0].value
    assert confirmed.events.diagnosed_during_source_followup is True
    assert noncase.events.diagnosed_during_source_followup is False
    assert noncase.events.death_status is None
    assert not noncase.diagnosis_observations
    assert noncase.glucose_observations[0].time.day < 0
    assert noncase.glucose_observations[1].status == "missing"
    assert noncase.glucose_observations[1].value is None
    assert death.events.death_status is True
    assert death.events.diagnosed_during_source_followup is None
    assert death.glucose_observations[0].status == "unknown"
    assert confirmed.follow_up.last_glucose_time != confirmed.follow_up.last_contact_time
    assert confirmed.treatment_changes[0].action == "start"
    assert registered_payload == original


def test_source_years_and_group_codes_are_not_converted(registered_payload):
    batch = preserve_observations(registered_payload)
    for participant, supplied in zip(
        batch.participants, registered_payload["participants"], strict=True
    ):
        events = participant.events
        assert events.source_year_unit == "source_reported_year"
        assert events.source_glucose_endpoint_years == supplied["events"].get(
            "source_glucose_endpoint_years"
        )
        assert events.source_last_visit_years == supplied["events"].get("source_last_visit_years")
        assert events.source_visit_group == supplied["events"].get("source_visit_group")
    report = summarize_observations(batch)
    assert report["unresolved_observations"]["source_year_to_day_conversion_unresolved"]
    assert report["unresolved_observations"]["grouped_visit_interval_unresolved"]
    assert report["source"]["relative_day_unit"] == "relative_day"
    assert report["source"]["source_year_unit"] == "source_reported_year"


def test_death_ordering_uses_only_relative_days_not_source_years(registered_payload):
    participant = registered_payload["participants"][0]
    events = participant["events"]
    events["death_status"] = True
    events["death_time"] = copy.deepcopy(
        registered_payload["participants"][2]["events"]["death_time"]
    )
    before = summarize_observations(preserve_observations(registered_payload))
    assert before["contradictions"]["glucose_collection_after_death"] == 1
    events["source_glucose_endpoint_years"], events["source_last_visit_years"] = (
        events["source_last_visit_years"],
        events["source_glucose_endpoint_years"],
    )
    batch = preserve_observations(registered_payload)
    assert (
        batch.participants[0].events.source_glucose_endpoint_years
        == (events["source_glucose_endpoint_years"])
    )
    assert summarize_observations(batch) == before


def test_aggregate_only_receipt_is_order_insensitive_and_offline(registered_payload, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: pytest.fail("Implicit network"))
    before = summarize_observations(preserve_observations(registered_payload))
    reordered = copy.deepcopy(registered_payload)
    reordered["participants"].reverse()
    for participant in reordered["participants"]:
        for key in ("glucose_observations", "diagnosis_observations", "treatment_changes"):
            participant.get(key, []).reverse()
    assert summarize_observations(preserve_observations(reordered)) == before
    encoded = json.dumps(before)
    assert "record_id" not in encoded
    assert "observation_id" not in encoded
    assert "test_reference_ids" not in encoded
    for participant in registered_payload["participants"]:
        assert participant["record_id"] not in encoded
    assert before["validation_only"]
    assert not before["scientific_release_ready"]
    assert not before["clinical_fit_allowed"]
    assert not before["state_activation_allowed"]
    assert not before["source_importer_certified"]
    assert before["glucose"]["fasting_glucose"]["status"]["observed"]
    assert before["glucose"]["ogtt_2h"]["status"]["missing"]
    assert before["source_events"]["death_status"] == {"no": 1, "unknown": 1, "yes": 1}
    assert before["diagnosis"]["outcome"] == {"confirmed": 1}


def collection_owner(batch, field):
    if field == "participants":
        return batch
    if field == "test_reference_ids":
        return batch.participants[0].diagnosis_observations[0]
    return batch.participants[0]


def wire_collection_owner(payload, field):
    if field == "participants":
        return payload
    if field == "test_reference_ids":
        return payload["participants"][0]["diagnosis_observations"][0]
    return payload["participants"][0]


@pytest.mark.parametrize("field", COLLECTION_FIELDS)
def test_validated_collections_cannot_append_replace_or_assign(registered_payload, field):
    batch = preserve_observations(registered_payload)
    owner = collection_owner(batch, field)
    collection = getattr(owner, field)
    before = summarize_observations(batch)
    assert isinstance(collection, tuple)
    with pytest.raises(AttributeError):
        collection.append(collection[0])
    with pytest.raises(TypeError):
        collection[0] = collection[0]
    with pytest.raises(ValidationError, match="frozen"):
        setattr(owner, field, collection + collection)
    assert summarize_observations(batch) == before


@pytest.mark.parametrize("field", COLLECTION_FIELDS)
def test_wire_list_mutations_do_not_change_validated_histories(registered_payload, field):
    batch = preserve_observations(registered_payload)
    before = batch.model_dump(mode="json")
    summary_before = summarize_observations(batch)
    collection = wire_collection_owner(registered_payload, field)[field]
    collection.append(collection[0])
    supplied = registered_payload["participants"][0]
    supplied["events"]["diagnosed_during_source_followup"] = None
    supplied["glucose_observations"][0]["value"] = supplied["glucose_observations"][-1]["value"]
    supplied["diagnosis_observations"][0]["confirmation_time"]["day"] = supplied[
        "diagnosis_observations"
    ][0]["first_positive_time"]["day"]
    assert batch.model_dump(mode="json") == before
    assert summarize_observations(batch) == summary_before


def test_immutable_collections_preserve_json_array_wire_format(registered_payload):
    batch = preserve_observations(registered_payload)
    wire = batch.model_dump(mode="json")
    assert isinstance(wire["participants"], list)
    participant = wire["participants"][0]
    for field in ("glucose_observations", "diagnosis_observations", "treatment_changes"):
        assert isinstance(participant[field], list)
    assert isinstance(participant["diagnosis_observations"][0]["test_reference_ids"], list)
    assert json.loads(batch.model_dump_json()) == wire
    round_trip = preserve_observations(wire)
    assert round_trip == batch
    assert summarize_observations(round_trip) == summarize_observations(batch)


@pytest.mark.parametrize("field", ["participants", "glucose_observations", "test_reference_ids"])
def test_wire_conversion_does_not_coerce_other_iterables(registered_payload, field):
    owner = wire_collection_owner(registered_payload, field)
    owner[field] = iter(owner[field])
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


def test_empty_histories_and_absent_metadata_remain_unknown(registered_payload):
    registered_payload["participants"] = [{"record_id": "synthetic-empty-history"}]
    batch = preserve_observations(registered_payload)
    participant = batch.participants[0]
    assert participant.events.diagnosed_during_source_followup is None
    assert participant.events.death_status is None
    assert participant.test_history_complete is None
    assert participant.treatment_history_complete is None
    assert participant.follow_up.censoring_reason == "unknown"
    assert participant.follow_up.last_glucose_time.kind == "unknown"
    assert participant.follow_up.last_contact_time.kind == "unknown"
    report = summarize_observations(batch)
    assert report["counts"]["glucose_observations"] == 0
    assert report["source_events"]["death_status"] == {"unknown": 1}
    assert report["unresolved_observations"]["test_history_completeness_unresolved"] == 1


def test_empty_batch_is_explicit_and_never_fit_ready(registered_payload):
    registered_payload["participants"] = []
    report = summarize_observations(preserve_observations(registered_payload))
    assert not any(report["counts"].values())
    assert not report["clinical_fit_allowed"]
    assert report["fit_blockers"]


@pytest.mark.parametrize("value", [0, 1, "false", "true", "0", "1"])
@pytest.mark.parametrize(
    "field", ["diagnosed_during_source_followup", "prior_diabetes_diagnosis", "death_status"]
)
def test_binary_source_codes_are_not_implicitly_imported(registered_payload, field, value):
    registered_payload["participants"][0]["events"][field] = value
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


@pytest.mark.parametrize(
    "field", ["synthetic", "test_history_complete", "treatment_history_complete"]
)
def test_boolean_envelope_and_completeness_fields_are_strict(registered_payload, field):
    target = registered_payload if field == "synthetic" else registered_payload["participants"][0]
    target[field] = "false"
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


@pytest.mark.parametrize("value", [0, 11, True, "2"])
def test_group_code_is_opaque_but_strictly_validated(registered_payload, value):
    registered_payload["participants"][0]["events"]["source_visit_group"] = value
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


@pytest.mark.parametrize("status", ["missing", "unknown"])
def test_unobserved_test_cannot_have_an_invented_zero(registered_payload, status):
    item = registered_payload["participants"][0]["glucose_observations"][0]
    item.update(status=status, value=0)
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


def test_observed_test_requires_value_and_no_missing_code(registered_payload):
    item = registered_payload["participants"][0]["glucose_observations"][0]
    original = item["value"]
    item["value"] = None
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)
    item.update(value=original, source_missing_code="synthetic-refused")
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan"), True, "100"])
def test_laboratory_amounts_are_finite_nonnegative_strict_numbers(registered_payload, value):
    registered_payload["participants"][0]["glucose_observations"][0]["value"] = value
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


def test_opaque_unresolved_units_are_preserved_and_block_interpretation(registered_payload):
    item = registered_payload["participants"][0]["glucose_observations"][0]
    item.update(unit="synthetic-opaque-unit", unit_status="unresolved")
    batch = preserve_observations(registered_payload)
    assert batch.participants[0].glucose_observations[0].unit == "synthetic-opaque-unit"
    report = summarize_observations(batch)
    assert report["unresolved_observations"]["glucose_unit_unresolved"]
    assert not report["clinical_fit_allowed"]
    item.update(unit=None, unit_status="documented")
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


def test_exact_interval_unknown_times_are_preserved_without_boundary_invention(registered_payload):
    diagnosis = registered_payload["participants"][0]["diagnosis_observations"][0]
    lower, upper = diagnosis["first_positive_time"]["day"], diagnosis["confirmation_time"]["day"]
    diagnosis["first_positive_time"] = {"kind": "interval", "lower_day": lower, "upper_day": upper}
    batch = preserve_observations(registered_payload)
    time = batch.participants[0].diagnosis_observations[0].first_positive_time
    assert time.bounds() == (lower, upper)
    assert time.day is None
    assert RelativeDayTime().bounds() is None
    assert summarize_observations(batch)["diagnosis"]["first_positive_time_kind"] == {"interval": 1}


@pytest.mark.parametrize(
    "time",
    [
        {"kind": "exact"},
        {"kind": "unknown", "day": 0},
        {"kind": "interval", "lower_day": 0, "upper_day": 0},
        {"kind": "interval", "lower_day": 1, "upper_day": 0},
        {"kind": "interval", "lower_day": 0},
        {"kind": "exact", "day": 0, "lower_day": 0},
        {"kind": "exact", "day": True},
        {"kind": "exact", "day": "0"},
        {"kind": "exact", "day": float("inf")},
        {"kind": "exact", "day": 0, "unit": "year"},
    ],
)
def test_malformed_times_are_rejected(time):
    with pytest.raises(ValidationError):
        RelativeDayTime.model_validate(time)


def test_negative_screening_allowed_but_negative_death_rejected(registered_payload):
    screening = registered_payload["participants"][1]["glucose_observations"][0]["time"]
    assert (
        preserve_observations(registered_payload).participants[1].glucose_observations[0].time.day
        < 0
    )
    registered_payload["participants"][2]["events"]["death_time"] = copy.deepcopy(screening)
    with pytest.raises(ValidationError, match="Death time cannot precede"):
        preserve_observations(registered_payload)


def test_recorded_death_time_does_not_resolve_unknown_status(registered_payload):
    death = registered_payload["participants"][2]["events"]
    death["death_status"] = None
    batch = preserve_observations(registered_payload)
    assert batch.participants[2].events.death_status is None
    report = summarize_observations(batch)
    assert report["source_events"]["death_status"] == {"no": 1, "unknown": 2}
    assert report["unresolved_observations"]["death_time_without_known_death_status"] == 1


def test_prior_confirmation_is_not_a_source_followup_diagnosis(registered_payload):
    participant = registered_payload["participants"][1]
    screening = copy.deepcopy(participant["glucose_observations"][0]["time"])
    participant["diagnosis_observations"] = [
        {"outcome": "confirmed", "first_positive_time": screening, "confirmation_time": screening}
    ]
    participant["events"]["prior_diabetes_diagnosis"] = True
    batch = preserve_observations(registered_payload)
    assert batch.participants[1].events.diagnosed_during_source_followup is False
    report = summarize_observations(batch)
    assert (
        report["unresolved_observations"]["confirmation_vs_source_followup_scope_unresolved"] == 1
    )
    assert "confirmed_outcome_with_explicit_no_source_diagnosis" not in report["contradictions"]


@pytest.mark.parametrize("mutation", ["participant", "glucose", "reference", "duplicate_reference"])
def test_duplicate_ids_and_invalid_diagnosis_references_are_rejected(registered_payload, mutation):
    participant = registered_payload["participants"][0]
    if mutation == "participant":
        registered_payload["participants"].append(copy.deepcopy(participant))
    elif mutation == "glucose":
        participant["glucose_observations"].append(
            copy.deepcopy(participant["glucose_observations"][0])
        )
    elif mutation == "reference":
        participant["diagnosis_observations"][0]["test_reference_ids"] = ["not-supplied"]
    else:
        refs = participant["diagnosis_observations"][0]["test_reference_ids"]
        refs.append(refs[0])
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


def test_unexpected_source_variables_or_state_fields_are_rejected(registered_payload):
    registered_payload["participants"][0]["physiological_state"] = "healthy"
    with pytest.raises(ValidationError):
        preserve_observations(registered_payload)


def test_conflicting_same_unit_histories_are_reported_not_rewritten(registered_payload):
    participant = registered_payload["participants"][0]
    diagnosis = participant["diagnosis_observations"][0]
    diagnosis["first_positive_time"], diagnosis["confirmation_time"] = (
        diagnosis["confirmation_time"],
        diagnosis["first_positive_time"],
    )
    follow_up = participant["follow_up"]
    follow_up["last_glucose_time"], follow_up["last_contact_time"] = (
        follow_up["last_contact_time"],
        follow_up["last_glucose_time"],
    )
    original = copy.deepcopy(registered_payload)
    batch = preserve_observations(registered_payload)
    report = summarize_observations(batch)
    assert report["contradictions"]["confirmation_before_first_positive"] == 1
    assert report["contradictions"]["last_contact_before_last_glucose"] == 1
    assert not report["clinical_fit_allowed"]
    assert registered_payload == original
