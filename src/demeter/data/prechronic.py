"""Candidate earlier-risk definitions, not clinical PreChronic diagnoses."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

from demeter.data.ingest import BUNDLE, digest
from demeter.data.nhanes import (
    classify as glycemic_classify,
    encoded,
    read_store as read_glycemic,
    read_xpt,
    storage_numbers,
    survey_proportion,
)
from demeter.schema import EvidenceRegistry

STORE = Path("data/sources/nhanes-risk/2017-2020")
DATASET = "nhanes_prechronic_candidates"
DIAGNOSES = ["BPQ020", "BPQ080", "MCQ160B", "MCQ160C", "MCQ160D", "MCQ160E", "MCQ160F", "MCQ220"]
COLUMNS = {
    "P_BMX.xpt": ["BMXWAIST"],
    "P_BPXO.xpt": [f"BPXO{kind}{i}" for kind in ("SY", "DI") for i in (1, 2, 3)],
    "P_HDL.xpt": ["LBDHDD"],
    "P_TRIGLY.xpt": ["LBXTR"],
    "P_BPQ.xpt": DIAGNOSES[:2],
    "P_MCQ.xpt": DIAGNOSES[2:],
}
STATES = (
    "lower_measured_risk",
    "prechronic_candidate",
    "prediabetes",
    "diabetes_any_type",
    "other_reported_diagnosis",
)


def definition(registry: EvidenceRegistry) -> dict:
    spec = registry.datasets[DATASET]
    a = spec["analysis"]
    if spec["model_role"] != "benchmark_only" or a["diagnosis_columns"] != DIAGNOSES:
        raise ValueError("Invalid PreChronic candidate role or diagnosis definition")
    for key in (
        "waist_male_cm",
        "waist_female_cm",
        "systolic_mmhg",
        "diastolic_mmhg",
        "hdl_male_mg_dl",
        "hdl_female_mg_dl",
        "triglycerides_mg_dl",
    ):
        if not np.isfinite(a[key]) or a[key] <= 0:
            raise ValueError("Invalid candidate risk threshold")
    if not a["definitions"] or any(
        type(n) is not int or not 1 <= n <= 4 for n in a["definitions"].values()
    ):
        raise ValueError("Candidate definitions require 1–4 non-glycemic markers")
    return spec


def read_store(source: Path = STORE) -> tuple[pd.DataFrame, dict]:
    frame, glycemic_receipt = read_glycemic()
    receipt = json.loads((source / "manifest.json").read_bytes())
    if receipt["schema_version"] != 1 or set(receipt["sources"]) != set(COLUMNS):
        raise ValueError("Invalid risk source manifest")
    for name, record in receipt["sources"].items():
        if digest((source / name).read_bytes()) != record["sha256"]:
            raise ValueError(f"Risk source checksum mismatch: {name}")
    for name, columns in COLUMNS.items():
        frame = frame.merge(
            read_xpt(source / name, columns), on="SEQN", how="left", validate="one_to_one"
        )
    return frame, {"glycemic": glycemic_receipt, "risk": receipt}


def classify(
    frame: pd.DataFrame, analysis: dict, glycemic_analysis: dict, definition_id: str
) -> pd.Series:
    """Disjoint complete-case categories with known-diagnosis priority over risk."""
    minimum = analysis["definitions"][definition_id]
    glycemic = glycemic_classify(frame, glycemic_analysis)
    measurements = ["BMXWAIST", "LBDHDD", "LBXTR", *COLUMNS["P_BPXO.xpt"]]
    values = frame[measurements]
    valid = (np.isfinite(values) & (values > 0)).all(axis=1)
    valid &= frame[DIAGNOSES].isin([1, 2]).all(axis=1) & glycemic.notna()
    valid &= frame.RIAGENDR.isin([1, 2])
    male = frame.RIAGENDR == 1
    waist = np.where(male, analysis["waist_male_cm"], analysis["waist_female_cm"])
    hdl = np.where(male, analysis["hdl_male_mg_dl"], analysis["hdl_female_mg_dl"])
    systolic = frame[[f"BPXOSY{i}" for i in (1, 2, 3)]].mean(axis=1)
    diastolic = frame[[f"BPXODI{i}" for i in (1, 2, 3)]].mean(axis=1)
    markers = pd.DataFrame(
        {
            "waist": frame.BMXWAIST > waist,
            "blood_pressure": (systolic >= analysis["systolic_mmhg"])
            | (diastolic >= analysis["diastolic_mmhg"]),
            "hdl": frame.LBDHDD < hdl,
            "triglycerides": frame.LBXTR > analysis["triglycerides_mg_dl"],
        }
    ).sum(axis=1)
    result = pd.Series(None, index=frame.index, dtype=object)
    result.loc[valid] = "lower_measured_risk"
    result.loc[valid & (markers >= minimum)] = "prechronic_candidate"
    result.loc[valid & frame[DIAGNOSES].eq(1).any(axis=1)] = "other_reported_diagnosis"
    result.loc[valid & (glycemic == "prediabetes")] = "prediabetes"
    result.loc[valid & (glycemic == "diabetes_any_type")] = "diabetes_any_type"
    return result


def survey_count(frame: pd.DataFrame, selected: pd.Series, confidence: float) -> dict:
    """Design-based weighted total for the observed complete-case subpopulation."""
    design = frame[["SDMVSTRA", "SDMVPSU"]]
    weight = frame.WTSAFPRP.to_numpy(dtype=float)
    if (
        not np.isfinite(design.to_numpy()).all()
        or not np.isfinite(weight).all()
        or (weight <= 0).any()
    ):
        raise ValueError("Invalid survey design or weights")
    totals = (
        design.assign(value=weight * selected.to_numpy(dtype=bool))
        .groupby(["SDMVSTRA", "SDMVPSU"])
        .value.sum()
    )
    variance = 0.0
    for _, v in totals.groupby(level=0):
        if len(v) < 2:
            raise ValueError("Singleton survey stratum")
        variance += len(v) / (len(v) - 1) * float(((v - v.mean()) ** 2).sum())
    df = len(totals) - totals.index.get_level_values(0).nunique()
    estimate, se = float(totals.sum()), float(np.sqrt(variance))
    interval = None
    if se > 0 and df > 0:
        half = float(t.ppf((1 + confidence) / 2, df)) * se
        interval = {"low": max(0.0, estimate - half), "high": estimate + half, "level": confidence}
    return {
        "estimate": estimate,
        "standard_error": se,
        "interval": interval,
        "degrees_of_freedom": df,
        "unit": "people",
        "scope": "Survey-weighted classified respondents; no item-nonresponse adjustment",
        "status": "estimated" if interval else "boundary_or_insufficient_variance",
    }


def reconstruct(frame: pd.DataFrame, registry: EvidenceRegistry) -> dict:
    spec = definition(registry)
    a = spec["analysis"]
    ga = registry.datasets["nhanes_glycemic_prevalence"]["analysis"]
    if (frame.WTSAFPRP.dropna() < 0).any():
        raise ValueError("Negative survey weight")
    sample = frame.loc[frame.WTSAFPRP > 0].copy()
    if sample.RIDAGEYR.isna().any() or not sample.RIAGENDR.isin([1, 2]).all():
        raise ValueError("Missing age or invalid sex")
    eligible = (sample.RIDAGEYR >= ga["adult_age_min"]) & ~(
        (sample.RIAGENDR == 2)
        & sample.RIDAGEYR.between(ga["adult_age_min"], ga["pregnancy_exclusion_age_max"])
        & (sample.RIDEXPRG == 1)
    )
    definitions = []
    for key in a["definitions"]:
        state = classify(sample, a, ga, key)
        domains = []
        for age in ga["age_groups"]:
            for sex, code in (("all", None), ("male", 1), ("female", 2)):
                domain = eligible & (sample.RIDAGEYR >= age["min"])
                if age["max"] is not None:
                    domain &= sample.RIDAGEYR <= age["max"]
                if code is not None:
                    domain &= sample.RIAGENDR == code
                complete = domain & state.notna()
                denominator = float(sample.loc[domain, "WTSAFPRP"].sum())
                domains.append(
                    {
                        "age_group": age["id"],
                        "sex": sex,
                        "eligible_n": int(domain.sum()),
                        "complete_n": int(complete.sum()),
                        "missing_weight_fraction": float(
                            sample.loc[domain & state.isna(), "WTSAFPRP"].sum()
                        )
                        / denominator
                        if denominator
                        else None,
                        "states": {
                            s: {
                                "proportion": survey_proportion(
                                    sample, complete, state == s, ga["confidence_level"]
                                ),
                                "count": survey_count(
                                    sample, complete & (state == s), ga["confidence_level"]
                                ),
                            }
                            for s in STATES
                        },
                    }
                )
        definitions.append(
            {"id": key, "minimum_markers": a["definitions"][key], "domains": domains}
        )
    return {
        "schema_version": 1,
        "model_role": "benchmark_only",
        "scientific_release_ready": False,
        "population": spec["population"],
        "definitions": definitions,
        "analysis": a,
        "limitations": spec["limitations"],
        "design": {"weight": "WTSAFPRP", "stratum": "SDMVSTRA", "psu": "SDMVPSU"},
    }


def rebuild_prechronic(
    registry: EvidenceRegistry, source: Path = STORE, destination: Path = BUNDLE
) -> dict:
    spec = definition(registry)
    frame, receipts = read_store(source)
    report = storage_numbers(reconstruct(frame, registry))
    definitions_hash = digest(
        encoded(
            {DATASET: spec, "glycemic": registry.datasets["nhanes_glycemic_prevalence"]["analysis"]}
        )
    )
    report["provenance"] = {
        "definition_sha256": definitions_hash,
        "sources": receipts,
        "transform": "demeter.data.prechronic.reconstruct",
        "transform_version": 1,
    }
    content = encoded(report)
    manifest = {
        "schema_version": 1,
        "bundle_sha256": digest(content),
        "definition_sha256": definitions_hash,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "prechronic_prevalence.json").write_bytes(content)
    (destination / "prechronic_manifest.json").write_bytes(encoded(manifest))
    return manifest


def load_prechronic(registry: EvidenceRegistry, bundle: Path = BUNDLE) -> dict:
    content = (bundle / "prechronic_prevalence.json").read_bytes()
    manifest = json.loads((bundle / "prechronic_manifest.json").read_bytes())
    spec = definition(registry)
    expected = digest(
        encoded(
            {DATASET: spec, "glycemic": registry.datasets["nhanes_glycemic_prevalence"]["analysis"]}
        )
    )
    if digest(content) != manifest["bundle_sha256"] or expected != manifest["definition_sha256"]:
        raise ValueError("PreChronic bundle or definition checksum mismatch")
    result = json.loads(content)
    if result["model_role"] != "benchmark_only" or result["scientific_release_ready"]:
        raise ValueError("Invalid PreChronic benchmark role")
    return result
