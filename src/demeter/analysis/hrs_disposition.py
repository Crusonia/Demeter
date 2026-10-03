"""Synthetic baseline reconciliation for orthogonal HRS observation facets.

Contract: docs/design/10_HRS_DISPOSITION_WITNESS.md (frozen before code).
I-01/I-05/I-07/I-11/I-12 -> F-08 -> T-01/T-02/T-05/T-08.
No source loader, empirical authorization, likelihood, bounds or engine update.
"""

from __future__ import annotations

WAVES = ("2012", "2016")
TRACKER_CODES = {
    1: "alive_report",
    2: "presumed_alive",
    5: "deceased_this_wave_report",
    6: "deceased_prior_wave_report",
    None: "not_in_sample",
}
DIAGNOSIS_CODES = {
    1: "affirmative_report",
    3: "disputed_prior_record_now_condition",
    4: "disputed_prior_record_now_no_condition",
    5: "negative_report",
    8: "unknown_or_not_ascertained",
    9: "refused",
    None: "inapplicable_or_partial",
}
UNIVERSES = (
    "ever_prompt",
    "prior_record_prompt",
    "since_last_interview_prompt",
    "unknown",
)
SELECTION_CODES = {True: "selected", False: "not_selected", None: "unknown"}
AVAILABILITIES = ("available", "missing", "unknown")
CLOCKS = ("unknown", "nominal_wave_only")
GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)


def _sequence(value, kind: str) -> tuple:
    if type(value) not in (list, tuple):
        raise ValueError(f"{kind} must be a list or tuple")
    return tuple(value)


def _key(value) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("Person IDs must be nonempty opaque strings without edge whitespace")
    return value


def _row(value, fields: set[str]) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("Record fields must match the declared contract exactly")
    return dict(value)


def _code(value, inventory: dict) -> str:
    if value is not None and type(value) is not int:
        raise ValueError("Native response codes must be Python integers or observed blank None")
    if value not in inventory:
        raise ValueError("Undocumented native response code")
    return inventory[value]


def _token(value, inventory: tuple[str, ...]) -> str:
    if type(value) is not str or value not in inventory:
        raise ValueError("Undeclared categorical token")
    return value


def _insert(store: dict, key, value) -> None:
    if key in store:
        raise ValueError("Duplicate observation record")
    store[key] = value


def _baseline_key(value, baseline: set[str]) -> str:
    key = _key(value)
    if key not in baseline:
        raise ValueError("Observation record lies outside the declared baseline cohort")
    return key


def _marginal(labels, missing: str, n: int) -> dict[str, int]:
    result = dict.fromkeys(labels, 0)
    result[missing] = n
    return result


def _record(marginal: dict[str, int], label: str, missing: str) -> None:
    marginal[missing] -= 1
    marginal[label] += 1


def reconcile_dispositions(
    baseline_ids,
    tracker_records,
    diagnosis_records,
    assay_records,
    *,
    synthetic_only: bool,
) -> dict:
    """Count every declared baseline key in each independent observation facet.

    The required True flag is a caller declaration, not proof of synthetic origin
    or permission to process empirical health records. Tracker means 2016 PALIVE
    only. Missing rows and observed native blanks are different. Wave labels are
    nominal source-question identifiers, never dates or elapsed durations.

    Duplicate/orphan records fail before any aggregate is returned. Inputs are
    unchanged, and neither results nor validation errors disclose person keys.
    Deceased reports and assay availability may coexist: chronology is unknown.
    No labelled joint histories, clinical-state allocation or sampling claims.
    """
    if type(synthetic_only) is not bool or not synthetic_only:
        raise ValueError("An explicit synthetic_only=True caller declaration is required")
    keys = tuple(_key(key) for key in _sequence(baseline_ids, "Baseline IDs"))
    baseline = set(keys)
    if len(baseline) != len(keys):
        raise ValueError("Duplicate baseline person ID")
    n = len(keys)

    tracker = {}
    for supplied in _sequence(tracker_records, "Tracker records"):
        row = _row(supplied, {"person_id", "palive"})
        key = _baseline_key(row["person_id"], baseline)
        _insert(tracker, key, _code(row["palive"], TRACKER_CODES))

    diagnoses = {}
    for supplied in _sequence(diagnosis_records, "Diagnosis records"):
        row = _row(supplied, {"person_id", "wave", "response", "universe"})
        key = _baseline_key(row["person_id"], baseline)
        wave = _token(row["wave"], WAVES)
        response = _code(row["response"], DIAGNOSIS_CODES)
        universe = _token(row["universe"], UNIVERSES)
        _insert(diagnoses, (key, wave), (response, universe))

    assays = {}
    for supplied in _sequence(assay_records, "Assay records"):
        row = _row(supplied, {"person_id", "wave", "selected", "availability", "clock"})
        key = _baseline_key(row["person_id"], baseline)
        wave = _token(row["wave"], WAVES)
        selected = row["selected"]
        if selected is not None and type(selected) is not bool:
            raise ValueError("Synthetic assay selection must be Boolean or unknown None")
        availability = _token(row["availability"], AVAILABILITIES)
        clock = _token(row["clock"], CLOCKS)
        if selected is False and availability == "available":
            raise ValueError("Available assay conflicts with supplied not-selected claim")
        _insert(assays, (key, wave), (SELECTION_CODES[selected], availability, clock))

    tracker_counts = _marginal(TRACKER_CODES.values(), "no_tracker_observation", n)
    for label in tracker.values():
        _record(tracker_counts, label, "no_tracker_observation")

    diagnosis_counts = {}
    assay_counts = {}
    for wave in WAVES:
        responses = _marginal(DIAGNOSIS_CODES.values(), "no_diagnosis_record", n)
        universes = _marginal(UNIVERSES, "no_diagnosis_record", n)
        selections = _marginal(SELECTION_CODES.values(), "no_assay_record", n)
        availabilities = _marginal(AVAILABILITIES, "no_assay_record", n)
        clocks = _marginal(CLOCKS, "no_assay_record", n)
        for (_, observed_wave), (response, universe) in diagnoses.items():
            if observed_wave == wave:
                _record(responses, response, "no_diagnosis_record")
                _record(universes, universe, "no_diagnosis_record")
        for (_, observed_wave), (selection, availability, clock) in assays.items():
            if observed_wave == wave:
                _record(selections, selection, "no_assay_record")
                _record(availabilities, availability, "no_assay_record")
                _record(clocks, clock, "no_assay_record")
        diagnosis_counts[wave] = {"response": responses, "universe": universes}
        assay_counts[wave] = {
            "selection": selections,
            "availability": availabilities,
            "specimen_clock": clocks,
        }

    marginals = [tracker_counts]
    for wave in WAVES:
        marginals.extend(diagnosis_counts[wave].values())
        marginals.extend(assay_counts[wave].values())
    conserved = all(sum(m.values()) == n and min(m.values()) >= 0 for m in marginals)
    if not conserved:
        raise RuntimeError("Internal marginal reconciliation failed")
    return {
        "kind": "synthetic_HRS_observation_disposition_witness",
        "baseline_count": n,
        "cohort_empty": n == 0,
        "tracker_2016_palive": tracker_counts,
        "diagnosis_reports": diagnosis_counts,
        "synthetic_assay_facets": assay_counts,
        "conservation": {"every_marginal_uses_declared_baseline": conserved},
        "interpretation": {
            "validation_only": True,
            "synthetic_only_declared": True,
            "synthetic_origin_independently_verified": False,
            "empirical_processing_authorized": False,
            "source_audit_passed": False,
            "native_tracker_scope": "2016 PALIVE only",
            "missing_tracker_row_is_observed_native_blank": False,
            "independent_death_ascertainment": False,
            "confirmed_clinical_survival": False,
            "diagnosis_history_erased": False,
            "diabetes_type_identified": False,
            "remission_identified": False,
            "specimen_interval_identified": False,
            "nominal_wave_is_elapsed_time": False,
            "paired_weights_supplied": False,
            "orthogonal_marginals_are_disjoint_populations": False,
            "joint_histories_exported": False,
            "clinical_fit_performed": False,
            "population_transport_identified": False,
        },
        "scientific_gates": dict.fromkeys(GATES, False),
    }
