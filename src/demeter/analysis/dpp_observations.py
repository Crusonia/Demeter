"""Audit a frozen documentation contract and synthetic observation preservation."""

from __future__ import annotations

import json
from pathlib import Path

from demeter.data.clinical_observations import preserve_observations, summarize_observations
from demeter.data.ingest import digest
from demeter.schema import EvidenceRegistry

DATASET = "dpp_observation_contract"
WITNESS = "dpp_observation_software_witness"


def _contract(registry: EvidenceRegistry) -> tuple[dict, dict]:
    spec = registry.datasets[DATASET]
    witness = registry.datasets[WITNESS]
    path = Path(spec["protocol_path"])
    content = path.read_bytes()
    if digest(content) != spec["protocol_sha256"]:
        raise ValueError("DPP frozen contract checksum mismatch")
    protocol = json.loads(content)
    if (
        spec.get("model_role") != "benchmark_only"
        or spec.get("status") != "derived"
        or spec.get("evidence_grade") != "C"
        or spec.get("clinical_fitting_allowed") is not False
        or spec.get("direct_initialization_allowed") is not False
    ):
        raise ValueError("DPP documentation must remain benchmark-only without clinical fitting")
    ignored = {"schema_version", "chronology", "software_witness", "limits"}
    expected = {key: value for key, value in protocol.items() if key not in ignored}
    if any(spec.get(key) != value for key, value in expected.items()):
        raise ValueError("DPP registry contract differs from frozen documentation definitions")
    if (
        witness.get("protocol_path") != spec["protocol_path"]
        or witness.get("protocol_sha256") != spec["protocol_sha256"]
        or any(witness.get(key) != value for key, value in protocol["software_witness"].items())
        or witness.get("status") != "synthetic"
        or witness.get("evidence_grade") != "E"
        or witness.get("model_role") != "benchmark_only"
        or witness["input"].get("synthetic") is not True
    ):
        raise ValueError("DPP software witness differs from its frozen synthetic definition")
    for source_id, pin in protocol["source_pins"].items():
        source = registry.sources.get(source_id)
        if source is None:
            raise ValueError(f"DPP missing registered documentation source: {source_id}")
        for key, value in pin.items():
            actual = getattr(source, key)
            if key == "retrieved_at":
                actual = actual.isoformat()
            if actual != value:
                raise ValueError(
                    f"DPP documentation source differs from frozen pin: {source_id}/{key}"
                )
    return spec, protocol


def audit_dpp_observations(registry: EvidenceRegistry, raw: Path | None = None) -> dict:
    """Run only a synthetic fixture; optionally check supplied documentation bytes.

    No participant-record path is accepted. The output contains aggregate
    diagnostics and source receipts, never individual observation histories.
    """
    spec, protocol = _contract(registry)
    payload = registry.datasets[WITNESS]["input"]
    batch = preserve_observations(payload)
    first, second, third = batch.participants
    checks = {
        "participant_count": len(batch.participants)
        == protocol["software_witness"]["expected"]["participant_count"],
        "source_units_preserved": (
            first.events.source_glucose_endpoint_years
            == payload["participants"][0]["events"]["source_glucose_endpoint_years"]
            and first.events.source_last_visit_years
            == payload["participants"][0]["events"]["source_last_visit_years"]
            and first.events.source_visit_group
            == payload["participants"][0]["events"]["source_visit_group"]
            and first.events.source_year_unit == "source_reported_year"
            and first.diagnosis_observations[0].first_positive_time.day
            == payload["participants"][0]["diagnosis_observations"][0]["first_positive_time"]["day"]
        ),
        "unknowns_not_replaced": (
            all(p.events.prior_diabetes_diagnosis is None for p in batch.participants)
            and second.events.death_status is None
            and second.glucose_observations[1].value is None
            and second.glucose_observations[1].status == "missing"
            and third.glucose_observations[0].time.kind == "unknown"
        ),
        "confirmation_visit_not_diagnosis": (
            second.glucose_observations[2].visit_purpose == "confirmation"
            and not second.diagnosis_observations
            and second.events.diagnosed_during_source_followup is False
        ),
        "later_low_value_not_remission": (
            first.events.diagnosed_during_source_followup is True
            and first.diagnosis_observations[0].outcome == "confirmed"
            and first.glucose_observations[2].value
            == payload["participants"][0]["glucose_observations"][2]["value"]
            and first.events.diabetes_type is None
        ),
        "glucose_and_contact_censoring_distinct": (
            second.follow_up.last_glucose_time.day
            == payload["participants"][1]["follow_up"]["last_glucose_time"]["day"]
            and second.follow_up.last_contact_time.day
            == payload["participants"][1]["follow_up"]["last_contact_time"]["day"]
            and second.follow_up.last_glucose_time.day != second.follow_up.last_contact_time.day
        ),
        "death_and_diagnosis_history_preserved": (
            third.events.death_status is True
            and third.events.death_time.day
            == payload["participants"][2]["events"]["death_time"]["day"]
            and third.events.diagnosed_during_source_followup is None
            and first.diagnosis_observations[0].confirmation_time.day
            != first.diagnosis_observations[0].first_positive_time.day
        ),
    }
    if set(checks) != set(protocol["software_witness"]["expected"]):
        raise ValueError("DPP software witness expectation keys differ from the frozen contract")
    source_checks = []
    for source_id, pin in protocol["source_pins"].items():
        path = raw / pin["raw_filename"] if raw is not None else None
        actual = digest(path.read_bytes()) if path is not None and path.is_file() else None
        source_checks.append(
            {
                "source_id": source_id,
                "url": pin["url"],
                "sha256": pin["sha256"],
                "retrieved_at": pin["retrieved_at"],
                "local_byte_check": "not_requested"
                if path is None
                else "passed"
                if actual == pin["sha256"]
                else "failed",
                "actual_sha256": actual,
            }
        )
    summary = summarize_observations(batch)
    return {
        "schema_version": "dpp_observation_audit_v1",
        "kind": DATASET,
        "model_role": "benchmark_only",
        "validation_only": True,
        "scientific_release_ready": False,
        "clinical_fitting_allowed": False,
        "direct_initialization_allowed": False,
        "participant_records_acquired": False,
        "chronology": protocol["chronology"],
        "documentation": {
            "source_checks": source_checks,
            "field_contract": spec["field_contract"],
            "source_context": spec["source_context"],
            "unresolved": spec["unresolved"],
        },
        "software_witness": {
            "status": "synthetic",
            "evidence_grade": "E",
            "checks": checks,
            "aggregate_observations": summary,
        },
        "results": {
            "software_witnesses_passed": all(checks.values()),
            "documentation_bytes_checked": raw is not None,
            "documentation_bytes_passed": all(
                row["local_byte_check"] == "passed" for row in source_checks
            )
            if raw is not None
            else None,
        },
        "provenance": {
            "evidence_sha256": registry.content_hash,
            "protocol_sha256": spec["protocol_sha256"],
            "implementation_sha256": {
                p.as_posix(): digest(p.read_bytes())
                for p in (
                    Path("src/demeter/data/clinical_observations.py"),
                    Path("src/demeter/analysis/dpp_observations.py"),
                )
            },
        },
        "interpretation": "Public documentation appraisal and synthetic observation preservation only. Matching bytes do not prove source-record coverage, clinical identification, causal dietary effects or national applicability.",
    }
