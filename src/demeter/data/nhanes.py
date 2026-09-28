"""Reload pinned public NHANES files and reconstruct glycemic prevalence.

Survey observations are benchmarks. They never replace the engine's T2D,
insulin-resistance, or healthy-state parameters automatically.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t

from demeter.data.ingest import BUNDLE, digest
from demeter.schema import EvidenceRegistry

STORE = Path("data/sources/nhanes/2017-2020")
DATASET = "nhanes_glycemic_prevalence"
STATES = ("normoglycemia", "prediabetes", "diabetes_any_type")
COLUMNS = {
    "P_DEMO.xpt": ["RIAGENDR", "RIDAGEYR", "RIDEXPRG", "SDMVSTRA", "SDMVPSU"],
    "P_DIQ.xpt": ["DIQ010"],
    "P_GHB.xpt": ["LBXGH"],
    "P_GLU.xpt": ["LBXGLU", "WTSAFPRP"],
}
LIMITATIONS = [
    "Cross-sectional glycemic benchmarks; not clinical diagnoses or causal estimates.",
    "All-type diabetes is not T2D; normoglycemia is not overall metabolic health.",
    "Survey prediabetes is not all insulin resistance or PreChronic.",
    "Adults 20+ in 2017-March 2020 do not identify pediatric or 2024 initial states.",
    "Complete-case analysis; no additional item-nonresponse reweighting or imputation.",
    "Single laboratory measurements do not confirm a clinical diagnosis.",
    "Pregnancy status is only public at ages 20-44; other pregnancy cannot be excluded.",
    "Logit-t intervals differ from published NCHS Korn-Graubard intervals; full NCHS reliability screening is not implemented.",
    "The source flags diabetes prevalence in men 20-39 as unreliable; retain that warning.",
    "Published-table agreement checks extraction, not independent model calibration or a holdout.",
]


def encoded(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def storage_numbers(value):
    """Remove platform-dependent last bits from derived JSON, not evidence hashes.

    Twelve significant digits is a storage convention, not measurement precision.
    Survey calculations and published-target checks run before this rounding.
    """
    if isinstance(value, float):
        return float(format(value, ".12g"))
    if isinstance(value, dict):
        return {key: storage_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [storage_numbers(item) for item in value]
    return value


def definition(registry: EvidenceRegistry) -> dict:
    spec = registry.datasets[DATASET]
    if spec["model_role"] != "benchmark_only":
        raise ValueError("NHANES glycemic observations must remain benchmark_only")
    a = spec["analysis"]
    if not (
        0 < a["hba1c_prediabetes_min"] < a["hba1c_diabetes_min"]
        and 0 < a["glucose_prediabetes_min"] < a["glucose_diabetes_min"]
        and 0 < a["confidence_level"] < 1
        and a["adult_age_min"] <= a["pregnancy_exclusion_age_max"]
        and a["hba1c_unit"] == "percent"
        and a["glucose_unit"] == "mg/dL"
    ):
        raise ValueError("Invalid registered NHANES analysis definition")
    ids = set()
    for group in a["age_groups"]:
        if (
            not isinstance(group["id"], str)
            or group["id"] in ids
            or group["min"] < a["adult_age_min"]
            or group["max"] is not None
            and group["max"] < group["min"]
        ):
            raise ValueError("Invalid NHANES age groups")
        ids.add(group["id"])
    return spec


def read_xpt(path: Path, columns: list[str]) -> pd.DataFrame:
    frame = pd.read_sas(path, format="xport")
    # pandas issue #30051: IBM XPORT zero can decode as exactly 2**-260.
    # This is a file-format correction, not a clinical cutoff or an epsilon filter.
    frame = frame.replace(float.fromhex("0x1p-260"), 0.0)
    frame = frame[["SEQN", *columns]]
    if frame.SEQN.isna().any() or frame.SEQN.duplicated().any():
        raise ValueError(f"Missing or duplicate SEQN in {path.name}")
    return frame


def read_store(source: Path = STORE) -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1 or set(manifest["sources"]) != set(COLUMNS):
        raise ValueError("Unexpected NHANES source-store schema")
    # Check every byte before parsing or producing any derived output.
    for name, receipt in manifest["sources"].items():
        if digest((source / name).read_bytes()) != receipt["sha256"]:
            raise ValueError(f"NHANES source checksum mismatch: {name}")
    tables = {name: read_xpt(source / name, columns) for name, columns in COLUMNS.items()}
    frame = tables.pop("P_DEMO.xpt")
    for name, table in tables.items():
        if not table.SEQN.isin(frame.SEQN).all():
            raise ValueError(f"Unknown SEQN in {name}")
        frame = frame.merge(table, on="SEQN", how="left", validate="one_to_one")
    return frame, manifest


def classify(frame: pd.DataFrame, analysis: dict) -> pd.Series:
    """Complete-case partition. Unknown interview/lab values never mean healthy."""
    valid = (
        frame.DIQ010.isin([1, 2, 3])
        & np.isfinite(frame.LBXGH)
        & (frame.LBXGH > 0)
        & np.isfinite(frame.LBXGLU)
        & (frame.LBXGLU > 0)
    )
    diabetes = (
        (frame.DIQ010 == 1)
        | (frame.LBXGH >= analysis["hba1c_diabetes_min"])
        | (frame.LBXGLU >= analysis["glucose_diabetes_min"])
    )
    prediabetes = (frame.LBXGH >= analysis["hba1c_prediabetes_min"]) | (
        frame.LBXGLU >= analysis["glucose_prediabetes_min"]
    )
    result = pd.Series(None, index=frame.index, dtype=object)
    result.loc[valid] = "normoglycemia"
    result.loc[valid & prediabetes] = "prediabetes"
    result.loc[valid & diabetes] = "diabetes_any_type"
    return result


def survey_proportion(
    frame: pd.DataFrame, domain: pd.Series, outcome: pd.Series, confidence: float
) -> dict:
    """Taylor ratio variance with all positive-weight PSUs, including empty domains.

    e_hi = sum_j w_hij D_hij (Y_hij - p) / sum(wD)
    V(p) = sum_h m_h/(m_h-1) * sum_i (e_hi - mean_h(e))**2
    """
    weight = frame.WTSAFPRP.to_numpy(dtype=float)
    if not 0 < confidence < 1 or not np.isfinite(weight).all() or (weight <= 0).any():
        raise ValueError("Survey estimation needs finite positive weights and valid confidence")
    design = frame[["SDMVSTRA", "SDMVPSU"]]
    if not np.isfinite(design.to_numpy()).all():
        raise ValueError("Missing survey stratum or PSU")
    d = domain.to_numpy(dtype=bool)
    y = outcome.to_numpy(dtype=float)
    if not np.isfinite(y[d]).all() or not np.isin(y[d], [0, 1]).all():
        raise ValueError("Survey proportion requires binary observed outcomes")
    n = int(d.sum())
    if n == 0:
        return {
            "n": 0,
            "estimate": None,
            "standard_error": None,
            "interval": None,
            "degrees_of_freedom": 0,
            "status": "empty_domain",
        }
    weight = weight / weight.max()  # Scale invariance; avoid overflow in weighted sums.
    denominator = float(weight[d].sum())
    # A constant binary domain has an exact boundary estimate and zero Taylor
    # residuals. Dot/sum rounding can otherwise produce 1-epsilon, a fictitious
    # variance and a platform-dependent logit interval at the boundary.
    p = float(y[d][0]) if np.all(y[d] == y[d][0]) else float(np.dot(weight[d], y[d]) / denominator)
    residual = np.zeros(len(frame))
    residual[d] = weight[d] * (y[d] - p) / denominator
    totals = design.assign(residual=residual).groupby(["SDMVSTRA", "SDMVPSU"]).residual.sum()
    variance = 0.0
    for _, values in totals.groupby(level=0):
        m = len(values)
        if m < 2:
            raise ValueError("Singleton survey stratum: variance is unidentified")
        variance += m / (m - 1) * float(((values - values.mean()) ** 2).sum())
    domain_design = design.loc[domain].drop_duplicates()
    df = len(domain_design) - domain_design.SDMVSTRA.nunique()
    se = float(np.sqrt(variance))
    interval = None
    if 0 < p < 1 and se > 0 and df > 0:
        half_width = t.ppf((1 + confidence) / 2, df) * se / (p * (1 - p))
        low, high = expit([logit(p) - half_width, logit(p) + half_width])
        interval = {
            "level": confidence,
            "low": float(low),
            "high": float(high),
            "method": "Taylor-linearized logit-t; domain degrees of freedom",
        }
    return {
        "n": n,
        "estimate": p,
        "standard_error": se,
        "interval": interval,
        "degrees_of_freedom": int(df),
        "status": "estimated" if interval else "boundary_or_insufficient_variance",
    }


def reconstruct(frame: pd.DataFrame, spec: dict) -> dict:
    a = spec["analysis"]
    if (frame.WTSAFPRP.dropna() < 0).any():
        raise ValueError("Negative survey weight")
    # Weight-related exclusions are allowed; retain every positive-weight domain/PSU.
    sample = frame.loc[frame.WTSAFPRP > 0].copy()
    state = classify(sample, a)
    adult = sample.RIDAGEYR >= a["adult_age_min"]
    pregnant = (
        (sample.RIAGENDR == 2)
        & sample.RIDAGEYR.between(a["adult_age_min"], a["pregnancy_exclusion_age_max"])
        & (sample.RIDEXPRG == 1)
    )
    eligible = adult & ~pregnant
    if sample.RIDAGEYR.isna().any() or not sample.RIAGENDR.isin([1, 2]).all():
        raise ValueError("Missing age or unsupported sex code")
    targets = {(r["age_group"], r["sex"]): r for r in spec["published_diabetes_targets"]}
    domains, checks = [], []
    for age in a["age_groups"]:
        for sex, sex_code in (("all", None), ("male", 1), ("female", 2)):
            domain = eligible & (sample.RIDAGEYR >= age["min"])
            if age["max"] is not None:
                domain &= sample.RIDAGEYR <= age["max"]
            if sex_code is not None:
                domain &= sample.RIAGENDR == sex_code
            complete = domain & state.notna()
            weighted_eligible = float(sample.loc[domain, "WTSAFPRP"].sum())
            excluded_weight = float(sample.loc[domain & state.isna(), "WTSAFPRP"].sum())
            estimates = {
                s: survey_proportion(sample, complete, state == s, a["confidence_level"])
                for s in STATES
            }
            target = targets.get((age["id"], sex))
            if target:
                estimate = estimates["diabetes_any_type"]
                checks.append(
                    {
                        "age_group": age["id"],
                        "sex": sex,
                        "published_n": target["n"],
                        "reconstructed_n": estimate["n"],
                        "published_percent": target["percent"],
                        "reconstructed_percent": None
                        if estimate["estimate"] is None
                        else 100 * estimate["estimate"],
                        "passed": estimate["n"] == target["n"]
                        and estimate["estimate"] is not None
                        and round(100 * estimate["estimate"], 1) == target["percent"],
                    }
                )
            domains.append(
                {
                    "age_group": age["id"],
                    "sex": sex,
                    "status": "estimated",
                    "eligible_n": int(domain.sum()),
                    "complete_n": int(complete.sum()),
                    "missing_n": int((domain & state.isna()).sum()),
                    "missing_weight_fraction": excluded_weight / weighted_eligible
                    if weighted_eligible
                    else None,
                    "source_diabetes_reliability_warning": bool(
                        target and target.get("source_reliability_warning")
                    ),
                    "states": estimates,
                }
            )
    return {
        "schema_version": 1,
        "kind": "nhanes_glycemic_prevalence",
        "model_role": "benchmark_only",
        "scientific_release_ready": False,
        "population": spec["population"],
        "time_period": spec["time_period"],
        "unit": "fraction",
        "evidence_grade": spec["evidence_grade"],
        "analysis": a,
        "domains": domains,
        "limitations": LIMITATIONS,
        "design": {
            "weight": "WTSAFPRP",
            "stratum": "SDMVSTRA",
            "psu": "SDMVPSU",
            "positive_weight_n": len(sample),
            "strata": int(sample.SDMVSTRA.nunique()),
            "psus": len(sample[["SDMVSTRA", "SDMVPSU"]].drop_duplicates()),
        },
        "published_reconstruction": {
            "source": spec["definition_sources"]["diabetes"],
            "locator": "Table 8",
            "independent_holdout": False,
            "checks": checks,
            "passed": bool(checks) and all(r["passed"] for r in checks),
        },
    }


def rebuild_nhanes(
    registry: EvidenceRegistry, source: Path = STORE, destination: Path = BUNDLE
) -> dict:
    spec = definition(registry)
    frame, source_manifest = read_store(source)
    report = reconstruct(frame, spec)
    if not report["published_reconstruction"]["passed"]:
        raise ValueError("NHANES reconstruction differs from registered published targets")
    report = storage_numbers(report)
    report["provenance"] = {
        "dataset_definition_sha256": digest(encoded(spec)),
        "source_manifest_sha256": digest(encoded(source_manifest)),
        "source_sha256": {k: v["sha256"] for k, v in source_manifest["sources"].items()},
        "transform": "demeter.data.nhanes.reconstruct",
        "transform_version": 2,
        "serialization": "Derived floats rounded to 12 significant digits; not measurement precision",
    }
    content = encoded(report)
    manifest = {
        "schema_version": 1,
        "bundle_sha256": digest(content),
        "dataset_definition_sha256": digest(encoded(spec)),
        "sources": source_manifest["sources"],
        "source_store": spec["source_store"],
        "transform": "demeter.data.nhanes.rebuild_nhanes",
        "model_role": "benchmark_only",
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "nhanes_prevalence.json").write_bytes(content)
    (destination / "nhanes_prevalence_manifest.json").write_bytes(encoded(manifest))
    return manifest


def load_nhanes(registry: EvidenceRegistry, bundle: Path = BUNDLE) -> dict:
    content = (bundle / "nhanes_prevalence.json").read_bytes()
    manifest = json.loads((bundle / "nhanes_prevalence_manifest.json").read_bytes())
    if digest(content) != manifest["bundle_sha256"]:
        raise ValueError("NHANES bundle checksum mismatch")
    if digest(encoded(definition(registry))) != manifest["dataset_definition_sha256"]:
        raise ValueError("NHANES definition changed; rebuild the pinned survey bundle")
    report = json.loads(content)
    if (
        report["schema_version"] != 1
        or report["model_role"] != "benchmark_only"
        or report["scientific_release_ready"]
    ):
        raise ValueError("Invalid NHANES benchmark bundle")
    return report
