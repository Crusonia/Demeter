"""Describe released follow-up arithmetic without choosing a hazard likelihood."""

from __future__ import annotations

import json
import math
from datetime import date
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from demeter.analysis.public_cohort import analyze_cohort, read_workbook
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded, storage_numbers
from demeter.schema import EvidenceRegistry

DATASET = "chen_followup_timing_audit"


def _agrees(value: float | None, published: float, decimals: int) -> bool:
    # Displayed precision is an explicit diagnostic assumption, not a new tolerance.
    return (
        value is not None
        and math.isfinite(value)
        and abs(Decimal(str(value)) - Decimal(str(published))) < Decimal(1).scaleb(-decimals) / 2
    )


def analyze_timing(frame: pd.DataFrame, spec: dict, intake: dict) -> dict:
    """Retain all rows, separate partial sums and test prespecified arithmetic."""
    original = analyze_cohort(frame, intake)
    followup = pd.to_numeric(frame["followup"], errors="coerce")
    valid = followup.notna() & np.isfinite(followup) & followup.gt(0)
    endpoint = pd.to_numeric(frame["endpoint"], errors="coerce")
    endpoint_known = endpoint.isin(intake["binary_codes"])

    def summary(mask: pd.Series) -> dict:
        values = followup.loc[mask & valid]
        count = len(values)
        total = math.fsum(values) if count else None
        return {
            "records": int(mask.sum()),
            "observed_followup": count,
            "missing_or_invalid_followup": int((mask & ~valid).sum()),
            "sum_released_years": total,
            "arithmetic_mean_years": total / count if count else None,
            "ordinary_median_years": float(
                values.quantile(0.5, interpolation=spec["quantile_method"])
            )
            if count
            else None,
            "minimum_years": float(values.min()) if count else None,
            "maximum_years": float(values.max()) if count else None,
            "complete": bool((mask & ~valid).sum() == 0 and count),
        }

    groups = {"all": summary(pd.Series(True, index=frame.index))}
    for code in intake["binary_codes"]:
        groups[f"recorded_endpoint_{code}"] = summary(endpoint.eq(code))
    groups["unclassified_endpoint"] = summary(~endpoint_known)
    all_records = groups["all"]
    complete = all_records["complete"]
    calendar_days = (
        date.fromisoformat(spec["reported_calendar_end_exclusive"])
        - date.fromisoformat(spec["reported_calendar_start_inclusive"])
    ).days
    if calendar_days <= 0:
        raise ValueError("Invalid reported calendar envelope")
    diagnostics = []
    for conversion in spec["diagnostic_days_per_year"]:
        if not math.isfinite(conversion) or conversion <= 0:
            raise ValueError("Invalid diagnostic year convention")
        days = followup.loc[valid].to_numpy() * conversion
        if not np.isfinite(days).all():
            raise ValueError("Follow-up exceeds numerical diagnostic capacity")
        residual = np.abs(days - np.rint(days))
        outside = days > calendar_days + spec["integer_day_absolute_tolerance"]
        diagnostics.append(
            {
                "candidate_days_per_year": conversion,
                "observed": len(days),
                "within_integer_day_tolerance": int(
                    (residual <= spec["integer_day_absolute_tolerance"]).sum()
                ),
                "maximum_integer_day_residual": float(residual.max()) if len(days) else None,
                "reported_calendar_envelope_days": calendar_days,
                "outside_reported_calendar_envelope": int(outside.sum()),
                "conservative_calendar_upper_bound_years": calendar_days / conversion,
                "interpretation": "Conditional conversion diagnostic; counts exceed a conservative calendar bound, not reconstructed visit dates",
            }
        )
    publication_rate = (
        intake["published_diabetes_events"]
        / spec["published_person_years"]
        * spec["crude_incidence_scale"]
    )
    # This is endpoint arithmetic, not an estimate of a model hazard.
    released_rate = (
        int(endpoint.eq(1).sum())
        / all_records["sum_released_years"]
        * spec["crude_incidence_scale"]
        if complete and endpoint_known.all()
        else None
    )
    checks = {
        "complete_followup": complete,
        "published_person_years": complete
        and _agrees(
            all_records["sum_released_years"],
            spec["published_person_years"],
            spec["published_person_years_decimal_places"],
        ),
        "published_median_followup": complete
        and _agrees(
            all_records["ordinary_median_years"],
            spec["published_median_followup_years"],
            spec["published_followup_decimal_places"],
        ),
        "conservative_calendar_bound_under_any_checked_convention": complete
        and any(d["outside_reported_calendar_envelope"] == 0 for d in diagnostics),
        "published_crude_rate_from_release": _agrees(
            released_rate,
            spec["published_crude_incidence_per_1000_person_years"],
            spec["published_crude_incidence_decimal_places"],
        ),
        "published_crude_rate_from_published_counts": _agrees(
            publication_rate,
            spec["published_crude_incidence_per_1000_person_years"],
            spec["published_crude_incidence_decimal_places"],
        ),
    }
    return storage_numbers(
        {
            "groups": groups,
            "original_intake_checks": original["checks"],
            "eligibility_interval_diagnostic": {
                "reported_visit_interval_exclusion_years": spec["published_minimum_followup_years"],
                "observed_durations_below_eligibility_interval": int(
                    (followup.loc[valid] < spec["published_minimum_followup_years"]).sum()
                ),
                "interpretation": "Visit-interval eligibility is not a documented minimum diagnosis-stopping duration; diagnostic only, not a source acceptance check",
            },
            "calendar_and_day_grid_diagnostics": diagnostics,
            "publication_arithmetic": {
                "published_person_years": spec["published_person_years"],
                "published_crude_rate_per_1000_person_years": spec[
                    "published_crude_incidence_per_1000_person_years"
                ],
                "implied_mean_years_from_published_total": spec["published_person_years"]
                / intake["published_records"],
                "implied_crude_rate_from_published_counts": publication_rate,
                "implied_crude_rate_from_complete_release": released_rate,
                "interpretation": "Arithmetic source comparisons; no accepted hazard estimate",
            },
            "diagnostic_hypotheses": {
                "mean_matches_published_median_at_displayed_precision": complete
                and _agrees(
                    all_records["arithmetic_mean_years"],
                    spec["published_median_followup_years"],
                    spec["published_followup_decimal_places"],
                ),
                "interpretation": "A match motivates a possible label-confusion hypothesis; it cannot confirm a correction or pass the median check",
            },
            "checks": checks,
            "source_reproduction_passed": all(checks.values()) and all(original["checks"].values()),
            "sampling_uncertainty": "Not estimated: exact fixed-release diagnostics; selection, measurement and transport unresolved",
        }
    )


def audit_timing(registry: EvidenceRegistry, workbook: Path) -> dict:
    spec = registry.datasets[DATASET]
    protocol_bytes = Path(spec["protocol_path"]).read_bytes()
    amendment_bytes = Path(spec["amendment_path"]).read_bytes()
    protocol = json.loads(protocol_bytes)
    amendment = json.loads(amendment_bytes)
    intake = registry.datasets[protocol["intake_dataset"]]
    source = registry.sources[spec["source_id"]]
    intake_protocol_bytes = Path(intake["protocol_path"]).read_bytes()
    intake_protocol = json.loads(intake_protocol_bytes)
    if spec["model_role"] != "benchmark_only" or intake["model_role"] != "benchmark_only":
        raise ValueError("Timing audit must remain benchmark_only")
    if (
        digest(protocol_bytes) != spec["protocol_sha256"]
        or digest(amendment_bytes) != spec["amendment_sha256"]
        or amendment["parent_protocol_sha256"] != digest(protocol_bytes)
        or amendment["analysis_id"] != protocol["analysis_id"]
        or spec["analysis"] != protocol["analysis"] | amendment["analysis_additions"]
        or digest(encoded(intake)) != spec["intake_definition_sha256"]
        or digest(intake_protocol_bytes) != intake["protocol_sha256"]
        or intake["analysis"] != intake_protocol["analysis"]
        or not source.sha256 == protocol["archive_sha256"] == intake_protocol["archive_sha256"]
        or not spec["source_id"] == protocol["source_id"] == intake["source_id"]
    ):
        raise ValueError("Timing protocol/registry mismatch")
    if digest(workbook.read_bytes()) != source.sha256:
        raise ValueError("Timing workbook checksum mismatch")
    result = analyze_timing(
        read_workbook(workbook, intake["analysis"]), spec["analysis"], intake["analysis"]
    )
    return {
        "schema_version": 1,
        "analysis_id": protocol["analysis_id"],
        "model_role": "benchmark_only",
        "scientific_release_ready": False,
        "assessment": "Public-source timing diagnostics and unresolved observation contract",
        "population": intake["population"],
        "geography": intake["geography"],
        "time_period": intake["time_period"],
        "results": result,
        "observation_decision": protocol["observation_decision"],
        "limitations": protocol["limits"] + amendment["limits"],
        "provenance": {
            "source": source.model_dump(mode="json"),
            "protocol_sha256": digest(protocol_bytes),
            "amendment_sha256": digest(amendment_bytes),
            "intake_definition_sha256": digest(encoded(intake)),
            "definition_sha256": digest(encoded(spec)),
            "transform_sha256": digest(Path(__file__).read_bytes()),
            "reader_sha256": digest(Path("src/demeter/analysis/public_cohort.py").read_bytes()),
            "individual_results_exported": False,
            "raw_redistributed": False,
        },
    }
