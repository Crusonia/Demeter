"""Reproduce a paired menu/intake contrast without activating a health effect."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from scipy.stats import t

from demeter.data.ingest import digest
from demeter.data.nhanes import encoded, storage_numbers
from demeter.schema import EvidenceRegistry

DATASET = "food_intake_reproduction"


def mean_interval(values: np.ndarray, confidence: float) -> dict:
    """A participant-level mean and t interval; days are not replicates."""
    n = len(values)
    if n < 2 or not np.isfinite(values).all():
        raise ValueError("At least two finite participant contrasts are required")
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    se = sd / np.sqrt(n)
    critical = float(t.ppf((1 + confidence) / 2, n - 1))
    return {
        "participants": n,
        "mean": mean,
        "standard_error": float(se),
        "sample_sd": sd,
        "degrees_of_freedom": n - 1,
        "confidence_level": confidence,
        "interval": [mean - critical * se, mean + critical * se] if se > 0 else None,
        "two_sided_p_value": float(2 * t.sf(abs(mean / se), n - 1)) if se > 0 else None,
        "interval_note": "Student t interval across participants"
        if se > 0
        else "Zero observed variance; inferential interval and test unavailable",
        "sufficient_statistics": {
            "sum": float(values.sum()),
            "sum_squares": float(values @ values),
        },
    }


def analyze_daily(frame: pd.DataFrame, spec: dict) -> dict:
    """Validate and aggregate an already decoded daily table; return no person rows."""
    required = ["StudyID", "Period", "DietOrder", "Day", "DaysOnDiet", "EI"]
    if not set(required) <= set(frame.columns):
        raise ValueError("Missing daily-intake columns")
    daily = frame[required].copy()
    days = spec["days_per_diet"]
    confidence = spec["confidence_level"]
    diets = spec["diets"]
    sequences = spec["sequences"]
    if (
        not isinstance(days, int)
        or days < 1
        or not 0 < confidence < 1
        or len(diets) != 2
        or len(set(diets)) != 2
        or len(sequences) != 2
        or any(sorted(seq) != sorted(diets) for seq in sequences.values())
        or len({tuple(seq) for seq in sequences.values()}) != 2
    ):
        raise ValueError("Invalid paired crossover analysis definition")
    if daily.isna().any().any() or daily["StudyID"].astype(str).str.strip().eq("").any():
        raise ValueError("Missing observations or participant identifiers; no implicit deletion")
    if (
        not set(daily["Period"]) == set(diets)
        or not set(daily["DietOrder"]) == set(sequences)
        or daily["StudyID"].nunique() != spec["participants"]
        or daily.duplicated(["StudyID", "Day"]).any()
        or daily.duplicated(["StudyID", "Period", "DaysOnDiet"]).any()
    ):
        raise ValueError("Unexpected participant/diet/sequence count or duplicate observations")
    numbers = daily[["Day", "DaysOnDiet", "EI"]].to_numpy(dtype=float)
    if not np.isfinite(numbers).all() or (daily["EI"] < 0).any():
        raise ValueError("Intake and time must be finite; energy cannot be negative")
    pairs = []
    signs = []
    order_labels = []
    diet_means = {diet: [] for diet in diets}
    for _, person in daily.groupby("StudyID", sort=True):
        if person["DietOrder"].nunique() != 1:
            raise ValueError("Inconsistent sequence within a participant")
        order = person["DietOrder"].iloc[0]
        means = {}
        for index, diet in enumerate(sequences[order]):
            group = person[person["Period"] == diet].sort_values("DaysOnDiet")
            expected = np.arange(1, days + 1)
            if (
                len(group) != days
                or not np.array_equal(group["DaysOnDiet"], expected)
                or not np.array_equal(group["Day"], expected + index * days)
            ):
                raise ValueError("Incomplete paired periods or inconsistent diet/day labels")
            means[diet] = float(group["EI"].mean())
            diet_means[diet].append(means[diet])
        pairs.append(means[diets[0]] - means[diets[1]])
        signs.append(1 if sequences[order][1] == diets[0] else -1)
        order_labels.append(order)
    delta = np.asarray(pairs)
    signs = np.asarray(signs)
    order_labels = np.asarray(order_labels)
    primary = mean_interval(delta, confidence)
    by_order = {key: mean_interval(delta[order_labels == key], confidence) for key in sequences}
    design = np.column_stack([np.ones(len(delta)), signs])
    if np.linalg.matrix_rank(design) != design.shape[1]:
        raise ValueError("Period sensitivity requires both randomized sequences")
    beta = np.linalg.lstsq(design, delta, rcond=None)[0]
    residual = delta - design @ beta
    df = len(delta) - design.shape[1]
    covariance = float(residual @ residual) / df * np.linalg.inv(design.T @ design)
    critical = float(t.ppf((1 + confidence) / 2, df))
    terms = {}
    for i, key in enumerate(("diet_contrast", "common_period_effect")):
        se = float(np.sqrt(covariance[i, i]))
        terms[key] = {
            "value": float(beta[i]),
            "standard_error": se,
            "interval": [float(beta[i] - critical * se), float(beta[i] + critical * se)]
            if se > 0
            else None,
        }
    rounding = spec["published_rounding_unit_kcal_per_day"]
    comparisons = []
    for statistic, field in (
        ("mean", "published_difference_kcal_per_day"),
        ("standard_error", "published_standard_error_kcal_per_day"),
    ):
        comparisons.append(
            {
                "statistic": statistic,
                "reproduced": primary[statistic],
                "published": spec[field],
                "agrees_at_reported_precision": abs(primary[statistic] - spec[field])
                < rounding / 2,
            }
        )
    return {
        "status": "estimated",
        "unit": "kcal/day",
        "contrast": f"{diets[0]} minus {diets[1]}",
        "coverage": {
            "participants": len(delta),
            "daily_records": len(daily),
            "days_per_participant_per_diet": days,
            "missing_or_excluded_records": 0,
        },
        "diet_means": {k: float(np.mean(v)) for k, v in diet_means.items()},
        "paired_difference": primary,
        "by_randomized_sequence": by_order,
        "period_sensitivity": {
            "terms": terms,
            "parameter_order": ["diet_contrast", "common_period_effect"],
            "covariance": covariance.tolist(),
            "degrees_of_freedom": df,
            "confidence_level": confidence,
            "design": "paired difference = diet_contrast + common_period_effect * (+1 PROC second, -1 PROC first)",
            "limitation": "Additive common period assumption; differential carryover is not identified",
        },
        "published_comparison": comparisons,
        "published_reproduction_passed": all(
            r["agrees_at_reported_precision"] for r in comparisons
        ),
    }


def reproduce_intake(registry: EvidenceRegistry, archive: Path) -> dict:
    """Read only pinned local bytes; never download, unpack to disk or execute SAS."""
    spec = registry.datasets[DATASET]
    if spec["model_role"] != "benchmark_only":
        raise ValueError("Food intake reproduction must remain benchmark_only")
    protocol_bytes = Path(spec["protocol_path"]).read_bytes()
    if digest(protocol_bytes) != spec["protocol_sha256"]:
        raise ValueError("Food intake reproduction protocol checksum mismatch")
    protocol = json.loads(protocol_bytes)
    source = registry.sources[spec["source_id"]]
    if (
        spec["analysis"] != protocol["analysis"]
        or spec["source_id"] != protocol["source_id"]
        or source.sha256 != protocol["archive_sha256"]
    ):
        raise ValueError("Registry differs from the recorded food intake protocol")
    content = archive.read_bytes()
    if digest(content) != source.sha256:
        raise ValueError("Author archive checksum mismatch; do not substitute another version")
    with ZipFile(BytesIO(content)) as bundle:
        if bundle.namelist().count(protocol["member"]) != 1:
            raise ValueError("Missing or duplicate daily-intake member")
        raw = bundle.read(protocol["member"])
        if (
            digest(raw) != protocol["member_sha256"]
            or digest(bundle.read("ADLDocumentation1.sas")) != protocol["author_code_sha256"]
        ):
            raise ValueError("Daily-intake member or author-code checksum mismatch")
    daily = pd.read_sas(BytesIO(raw), format="sas7bdat", encoding="utf-8")
    result = analyze_daily(daily, spec["analysis"])
    parameter = registry.parameters[spec["estimate_parameter"]]
    primary = storage_numbers(result["paired_difference"])
    if (
        parameter.model_role != "benchmark_only"
        or parameter.status != "estimated"
        or parameter.source_id != spec["source_id"]
        or parameter.unit != result["unit"]
        or parameter.value != primary["mean"]
        or parameter.uncertainty is None
        or parameter.uncertainty.kind != "interval"
        or [parameter.uncertainty.low, parameter.uncertainty.high] != primary["interval"]
    ):
        raise ValueError("Registered benchmark estimate or interval differs from reproduction")
    return storage_numbers(
        {
            "schema_version": 1,
            "analysis_id": protocol["analysis_id"],
            "model_role": spec["model_role"],
            "scientific_release_ready": False,
            "assessment": "Used-data numerical reproduction, not independent validation or an engine effect",
            "population": spec["population"],
            "geography": spec["geography"],
            "time_period": spec["time_period"],
            "results": result,
            "limitations": protocol["limits"] + [protocol["uncertainty"]],
            "provenance": {
                "source": source.model_dump(mode="json"),
                "member": protocol["member"],
                "member_sha256": digest(raw),
                "protocol_sha256": digest(protocol_bytes),
                "definition_sha256": digest(encoded(spec)),
                "estimate_parameter_sha256": digest(encoded(parameter.model_dump(mode="json"))),
                "transform_sha256": digest(Path(__file__).read_bytes()),
                "corrections": protocol["corrections"],
                "raw_redistributed": False,
                "individual_results_exported": False,
            },
        }
    )
