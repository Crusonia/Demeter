"""Audit public NHANES glycemic/mortality linkage before fitting health hazards.

This is a data feasibility report, not a fitted mortality model. In particular,
the death-certificate DIABETES flag is never used to classify baseline diabetes.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from demeter.data.ingest import BUNDLE, digest
from demeter.data.nhanes import classify, definition as glycemic_definition
from demeter.data.nhanes import encoded, read_xpt, storage_numbers, survey_proportion
from demeter.schema import EvidenceRegistry

STORE = Path("data/sources/nhanes-mortality/2011-2012")
DATASET = "nhanes_linked_mortality"
MORTALITY_FILE = "NHANES_2011_2012_MORT_2019_PUBLIC.dat"
COLUMNS = {
    "DEMO_G.xpt": ["RIAGENDR", "RIDAGEYR", "RIDEXPRG", "SDMVSTRA", "SDMVPSU"],
    "DIQ_G.xpt": ["DIQ010"],
    "GHB_G.xpt": ["LBXGH"],
    "GLU_G.xpt": ["LBXGLU", "WTSAF2YR"],
}
# Official CDC R program: inclusive one-based columns converted to Python slices.
LAYOUT = {
    "SEQN": (0, 6),
    "ELIGSTAT": (14, 15),
    "MORTSTAT": (15, 16),
    "PERMTH_INT": (42, 45),
    "PERMTH_EXM": (45, 48),
}
LIMITATIONS = [
    "Feasibility audit only: no fitted hazards, mortality ratios, or clinical validation.",
    "Baseline glycemic states are not repeated observations; progression and reversal are unidentified.",
    "All-type diabetes is not T2D; normoglycemia is not overall metabolic health.",
    "Public-use follow-up times may be perturbed; vital status is not perturbed.",
    "Missing linkage is not survival. Original fasting weights are not adjusted for linkage ineligibility.",
    "Complete-case selection and linkage eligibility can bias subsequent mortality estimates.",
    "Public age is top-coded at 80; single-age elderly hazards are not identified.",
    "This inspected cycle is development data, not an untouched independent holdout.",
    "Observed follow-up deaths are counts, not age-adjusted, causal or annual mortality rates.",
]


def definition(registry: EvidenceRegistry) -> dict:
    spec = registry.datasets[DATASET]
    if spec["model_role"] != "feasibility_only" or spec["cycle"] != "2011-2012":
        raise ValueError("Invalid linked mortality scope")
    return {"dataset": spec, "glycemic_analysis": glycemic_definition(registry)["analysis"]}


def read_mortality(path: Path) -> pd.DataFrame:
    lines = path.read_text(encoding="ascii").splitlines()
    # CDC omits trailing padding in the final three-character field.
    if not lines or any(len(line) < 46 or line[48:].strip() for line in lines):
        raise ValueError("Invalid mortality fixed-width record length")
    frame = pd.DataFrame(
        {key: [line[start:end].strip() for line in lines] for key, (start, end) in LAYOUT.items()}
    )
    for key in frame:
        frame[key] = pd.to_numeric(frame[key].replace({"": np.nan, ".": np.nan}), errors="raise")
        if ((frame[key].dropna() % 1) != 0).any():
            raise ValueError("Mortality fields must be integers")
    if frame.SEQN.isna().any() or frame.SEQN.duplicated().any() or (frame.SEQN <= 0).any():
        raise ValueError("Missing or duplicate mortality SEQN")
    if not frame.ELIGSTAT.isin([1, 2, 3]).all():
        raise ValueError("Invalid mortality eligibility code")
    eligible = frame.ELIGSTAT == 1
    if not frame.loc[eligible, "MORTSTAT"].isin([0, 1]).all():
        raise ValueError("Eligible mortality records require vital status")
    if frame.loc[~eligible, ["MORTSTAT", "PERMTH_INT", "PERMTH_EXM"]].notna().any().any():
        raise ValueError("Ineligible mortality records must not contain outcomes")
    if frame.loc[eligible, "PERMTH_INT"].isna().any():
        raise ValueError("Eligible mortality records require interview follow-up")
    months = frame[["PERMTH_INT", "PERMTH_EXM"]]
    if (months < 0).any().any() or (frame.PERMTH_EXM > frame.PERMTH_INT).any():
        raise ValueError("Invalid mortality follow-up months")
    return frame


def read_store(source: Path = STORE) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((source / "manifest.json").read_bytes())
    if manifest["schema_version"] != 1 or set(manifest["sources"]) != {*COLUMNS, MORTALITY_FILE}:
        raise ValueError("Unexpected linked mortality source schema")
    for name, receipt in manifest["sources"].items():
        if digest((source / name).read_bytes()) != receipt["sha256"]:
            raise ValueError(f"Linked mortality source checksum mismatch: {name}")
    frame = read_xpt(source / "DEMO_G.xpt", COLUMNS["DEMO_G.xpt"])
    mortality = read_mortality(source / MORTALITY_FILE)
    if set(frame.SEQN) != set(mortality.SEQN):
        raise ValueError("Mortality and demographic cycle IDs do not match")
    frame = frame.merge(mortality, on="SEQN", validate="one_to_one")
    for name, columns in COLUMNS.items():
        if name == "DEMO_G.xpt":
            continue
        table = read_xpt(source / name, columns)
        if not table.SEQN.isin(frame.SEQN).all():
            raise ValueError(f"Unknown cycle ID in {name}")
        frame = frame.merge(table, on="SEQN", how="left", validate="one_to_one")
    return frame, manifest


def audit(frame: pd.DataFrame, spec: dict) -> dict:
    a = spec["glycemic_analysis"]
    sample = frame.loc[np.isfinite(frame.WTSAF2YR) & (frame.WTSAF2YR > 0)].copy()
    # Reuse the estimator only after explicitly aliasing this cycle's fasting weight.
    sample["WTSAFPRP"] = sample.WTSAF2YR
    states = classify(sample, a)
    adult = sample.RIDAGEYR >= a["adult_age_min"]
    pregnant = (sample.RIDEXPRG == 1) & (sample.RIDAGEYR <= a["pregnancy_exclusion_age_max"])
    eligible = adult & ~pregnant
    complete = eligible & states.notna()
    linked = sample.ELIGSTAT == 1
    if (sample.loc[adult, "ELIGSTAT"] == 2).any():
        raise ValueError("Adult participant incorrectly coded as public-use minor")
    domains = []
    for group in a["age_groups"]:
        age = (sample.RIDAGEYR >= group["min"]) & (
            True if group["max"] is None else sample.RIDAGEYR <= group["max"]
        )
        for sex, code in (("all", None), ("male", 1), ("female", 2)):
            domain = complete & age & (True if code is None else sample.RIAGENDR == code)
            for state in ("normoglycemia", "prediabetes", "diabetes_any_type"):
                d = domain & (states == state)
                included = d & linked
                months = sample.loc[included, "PERMTH_EXM"]
                domains.append(
                    {
                        "age_group": group["id"],
                        "sex": sex,
                        "baseline_state": state,
                        "complete_baseline_n": int(d.sum()),
                        "linked_n": int(included.sum()),
                        "ineligible_n": int((d & ~linked).sum()),
                        "deaths_n": int((included & (sample.MORTSTAT == 1)).sum()),
                        "exam_followup_missing_n": int(months.isna().sum()),
                        "exam_followup_zero_n": int((months == 0).sum()),
                        "exam_followup_months_min": float(months.min())
                        if months.notna().any()
                        else None,
                        "exam_followup_months_max": float(months.max())
                        if months.notna().any()
                        else None,
                        "linkage_eligibility": survey_proportion(
                            sample, d, linked, a["confidence_level"]
                        ),
                    }
                )
    return storage_numbers(
        {
            "schema_version": 1,
            "model_role": "feasibility_only",
            "scientific_release_ready": False,
            "independent_holdout": False,
            "analysis": spec,
            "limitations": LIMITATIONS,
            "counts": {
                "source_n": len(frame),
                "positive_fasting_weight_n": len(sample),
                "adult_nonpregnant_n": int(eligible.sum()),
                "missing_glycemic_n": int((eligible & states.isna()).sum()),
                "complete_baseline_n": int(complete.sum()),
                "linked_complete_n": int((complete & linked).sum()),
                "ineligible_complete_n": int((complete & ~linked).sum()),
            },
            "domains": domains,
            "design": {
                "weight": "WTSAF2YR",
                "stratum": "SDMVSTRA",
                "psu": "SDMVPSU",
                "weight_adjusted_for_linkage": False,
            },
        }
    )


def rebuild_linked_mortality(
    registry: EvidenceRegistry, source: Path = STORE, destination: Path = BUNDLE
) -> dict:
    spec = definition(registry)
    frame, sources = read_store(source)
    report = audit(frame, spec)
    report["provenance"] = {
        "dataset_definition_sha256": digest(encoded(spec)),
        "source_manifest_sha256": digest(encoded(sources)),
        "source_sha256": {k: v["sha256"] for k, v in sources["sources"].items()},
        "transform": "demeter.data.linked_mortality.audit",
        "transform_version": 1,
    }
    content = encoded(report)
    manifest = {
        "schema_version": 1,
        "bundle_sha256": digest(content),
        "dataset_definition_sha256": digest(encoded(spec)),
        "sources": sources["sources"],
        "model_role": "feasibility_only",
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "linked_mortality_audit.json").write_bytes(content)
    (destination / "linked_mortality_manifest.json").write_bytes(encoded(manifest))
    return manifest


def load_linked_mortality(registry: EvidenceRegistry, bundle: Path = BUNDLE) -> dict:
    content = (bundle / "linked_mortality_audit.json").read_bytes()
    manifest = json.loads((bundle / "linked_mortality_manifest.json").read_bytes())
    if digest(content) != manifest["bundle_sha256"]:
        raise ValueError("Linked mortality bundle checksum mismatch")
    if digest(encoded(definition(registry))) != manifest["dataset_definition_sha256"]:
        raise ValueError("Linked mortality definition changed; rebuild bundle")
    report = json.loads(content)
    if (
        report["schema_version"] != 1
        or report["model_role"] != "feasibility_only"
        or report["scientific_release_ready"]
        or report["independent_holdout"]
    ):
        raise ValueError("Invalid linked mortality audit scope")
    return report
