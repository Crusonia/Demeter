"""Conservative category sets for incomplete NHANES observations, not latent states."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from demeter.data.ingest import digest
from demeter.data.nhanes import STATES, definition as glycemic_definition, encoded
from demeter.data.nhanes import classify as glycemic_classify
from demeter.data.nhanes import storage_numbers, survey_proportion
from demeter.data.prechronic import COLUMNS, DIAGNOSES, STATES as RISK_STATES
from demeter.data.prechronic import definition as risk_definition, read_store
from demeter.data.prechronic import classify as risk_classify
from demeter.data.state_mapping import assess as complete_assess
from demeter.schema import EvidenceRegistry

DATASET = "observation_partial_mapping"


def possible_categories(frame: pd.DataFrame, registry: EvidenceRegistry, key: str) -> pd.DataFrame:
    """One Boolean per compatible category; missing information never means low risk."""
    spec = registry.datasets[DATASET]
    if (
        spec["model_role"] != "benchmark_only"
        or spec["direct_initialization_allowed"] is not False
        or spec["method"] != "compatible_categories_v1"
    ):
        raise ValueError("Partial observations require the registered benchmark-only method")
    ga = glycemic_definition(registry)["analysis"]
    ra = risk_definition(registry)["analysis"]
    if key not in ("glycemic", *ra["definitions"]):
        raise ValueError("Unknown observation definition")
    if not frame.index.is_unique or not frame.RIAGENDR.isin([1, 2]).all():
        raise ValueError("Observation rows require unique indices and valid sex coding")
    codes = spec["interview_codes"]
    known_diagnosis = frame.DIQ010 == codes["yes"]
    known_negative = frame.DIQ010.isin(codes["no_diabetes_diagnosis"])
    # Ordered glycemic bands: 0=normal, 1=prediabetes, 2=any-type diabetes.
    lower = np.zeros(len(frame), dtype=int)
    upper = np.zeros(len(frame), dtype=int)
    for column, prefix in (("LBXGH", "hba1c"), ("LBXGLU", "glucose")):
        values = frame[column]
        valid = np.isfinite(values) & (values > 0)
        band = (values >= ga[f"{prefix}_prediabetes_min"]).astype(int) + (
            values >= ga[f"{prefix}_diabetes_min"]
        ).astype(int)
        lower = np.maximum(lower, np.where(valid, band, 0))
        upper = np.maximum(upper, np.where(valid, band, 2))
    glycemic = pd.DataFrame(
        {
            name: (lower <= i) & (upper >= i) & ~known_diagnosis
            if i < len(STATES) - 1
            else (upper >= i) | ~known_negative
            for i, name in enumerate(STATES)
        },
        index=frame.index,
    )
    if key == "glycemic":
        return glycemic

    male = frame.RIAGENDR == 1
    marker_min, marker_max = np.zeros(len(frame), dtype=int), np.zeros(len(frame), dtype=int)
    waist = np.where(male, ra["waist_male_cm"], ra["waist_female_cm"])
    hdl = np.where(male, ra["hdl_male_mg_dl"], ra["hdl_female_mg_dl"])
    for column, positive in (
        ("BMXWAIST", frame.BMXWAIST > waist),
        ("LBDHDD", frame.LBDHDD < hdl),
        ("LBXTR", frame.LBXTR > ra["triglycerides_mg_dl"]),
    ):
        valid = np.isfinite(frame[column]) & (frame[column] > 0)
        marker_min += (valid & positive).to_numpy(dtype=int)
        marker_max += (~valid | positive).to_numpy(dtype=int)
    # Deliberate block coarsening: do not silently average fewer BP readings.
    bp = frame[COLUMNS["P_BPXO.xpt"]]
    valid_bp = (np.isfinite(bp) & (bp > 0)).all(axis=1)
    bp_positive = (bp[[f"BPXOSY{i}" for i in (1, 2, 3)]].mean(axis=1) >= ra["systolic_mmhg"]) | (
        bp[[f"BPXODI{i}" for i in (1, 2, 3)]].mean(axis=1) >= ra["diastolic_mmhg"]
    )
    marker_min += (valid_bp & bp_positive).to_numpy(dtype=int)
    marker_max += (~valid_bp | bp_positive).to_numpy(dtype=int)
    diagnosis_present = frame[DIAGNOSES].eq(codes["yes"]).any(axis=1)
    diagnosis_possible = ~frame[DIAGNOSES].eq(codes["no"]).all(axis=1)
    normal = glycemic.normoglycemia
    minimum = ra["definitions"][key]
    return pd.DataFrame(
        {
            "lower_measured_risk": normal & ~diagnosis_present & (marker_min < minimum),
            "prechronic_candidate": normal & ~diagnosis_present & (marker_max >= minimum),
            "prediabetes": glycemic.prediabetes,
            "diabetes_any_type": glycemic.diabetes_any_type,
            "other_reported_diagnosis": normal & diagnosis_possible,
        },
        index=frame.index,
    )


def assess(frame: pd.DataFrame, registry: EvidenceRegistry) -> dict:
    """Account for resolved and unresolved observations on the original denominator."""
    original = complete_assess(frame, registry)
    spec = registry.datasets[DATASET]
    ga = glycemic_definition(registry)["analysis"]
    sample = frame.loc[frame.WTSAFPRP > 0].copy()
    eligible = (sample.RIDAGEYR >= ga["adult_age_min"]) & ~(
        (sample.RIAGENDR == 2)
        & sample.RIDAGEYR.between(ga["adult_age_min"], ga["pregnancy_exclusion_age_max"])
        & (sample.RIDEXPRG == 1)
    )
    definitions = []
    for previous in original["definitions"]:
        key = previous["id"]
        possible = possible_categories(sample, registry, key)
        count = possible.sum(axis=1)
        if (count < 1).any():
            raise ValueError("Every observation must retain at least one possible category")
        resolved = count == 1
        complete = (
            glycemic_classify(sample, ga)
            if key == "glycemic"
            else risk_classify(sample, risk_definition(registry)["analysis"], ga, key)
        )
        for name in possible:
            previous_members = complete == name
            if not (resolved & possible[name]).loc[previous_members].all():
                raise ValueError("Partial observations contradict the complete-case definition")
        patterns = possible.apply(
            lambda row, columns=possible.columns: tuple(columns[row.to_numpy()]), axis=1
        )
        rows = []
        for before in previous["domains"]:
            age = next(a for a in ga["age_groups"] if a["id"] == before["age_group"])
            domain = eligible & (sample.RIDAGEYR >= age["min"])
            if age["max"] is not None:
                domain &= sample.RIDAGEYR <= age["max"]
            sex_code = {"all": None, "male": 1, "female": 2}[before["sex"]]
            if sex_code is not None:
                domain &= sample.RIAGENDR == sex_code
            bounds = {}
            for name in STATES if key == "glycemic" else RISK_STATES:
                definite, compatible = possible[name] & resolved, possible[name]
                endpoints = {
                    label: survey_proportion(sample, domain, membership, ga["confidence_level"])
                    for label, membership in (("lower", definite), ("upper", compatible))
                }
                bounds[name] = {
                    "definite_n": int((domain & definite).sum()),
                    "possible_n": int((domain & compatible).sum()),
                    "compatible_weight_range": {k: v["estimate"] for k, v in endpoints.items()},
                    "endpoint_sampling": endpoints,
                }
            partition = []
            for pattern in sorted(set(patterns.loc[domain])):
                membership = patterns.map(lambda value, target=pattern: value == target)
                partition.append(
                    {
                        "possible_categories": list(pattern),
                        "sample_n": int((domain & membership).sum()),
                        "eligible_weight_proportion": survey_proportion(
                            sample, domain, membership, ga["confidence_level"]
                        ),
                    }
                )
            resolved_n = int((domain & resolved).sum())
            rows.append(
                {
                    "age_group": before["age_group"],
                    "sex": before["sex"],
                    "eligible_n": before["eligible_n"],
                    "eligible_weight": before["eligible_weight"],
                    "complete_case_n": before["classified_n"],
                    "resolved_n": resolved_n,
                    "newly_resolved_n": resolved_n - before["classified_n"],
                    "unresolved_n": before["eligible_n"] - resolved_n,
                    "unresolved_weight_proportion": survey_proportion(
                        sample, domain, ~resolved, ga["confidence_level"]
                    ),
                    "reported_diabetes_unresolved_n": int(
                        (
                            domain & (sample.DIQ010 == spec["interview_codes"]["yes"]) & ~resolved
                        ).sum()
                    ),
                    "categories": bounds,
                    "category_set_partition": partition,
                }
            )
        definitions.append({"id": key, "domains": rows})
    return {
        "schema_version": 1,
        "kind": DATASET,
        "method": spec["method"],
        "model_role": "benchmark_only",
        "validation_only": True,
        "scientific_release_ready": False,
        "direct_initialization_allowed": False,
        "population": original["population"],
        "geography": original["geography"],
        "time_period": original["time_period"],
        "counts": original["counts"],
        "denominator": original["denominator"],
        "unit": original["unit"],
        "uncertainty": spec["uncertainty"],
        "limitations": spec["limitations"],
        "complete_case_comparison_limitations": original["limitations"],
        "definitions": definitions,
    }


def partial_report(registry: EvidenceRegistry) -> dict:
    """Read the existing checksummed source store and export aggregates only."""
    frame, receipts = read_store()
    report = assess(frame, registry)
    paths = ("partial_observations.py", "state_mapping.py", "nhanes.py", "prechronic.py")
    report["provenance"] = {
        "evidence_sha256": registry.content_hash,
        "source_receipts_sha256": digest(encoded(receipts)),
        "source_sha256": {
            group: {name: row["sha256"] for name, row in receipt["sources"].items()}
            for group, receipt in receipts.items()
        },
        "implementation_sha256": {
            path.as_posix(): digest(path.read_bytes())
            for path in (Path("src/demeter/data") / p for p in paths)
        },
        "definitions": {
            DATASET: registry.datasets[DATASET],
            "glycemic": glycemic_definition(registry)["analysis"],
            "risk": risk_definition(registry)["analysis"],
            "complete_case": registry.datasets["observation_state_mapping"],
        },
    }
    return storage_numbers(report)
