"""In-memory current-cycle glycemic observations, never clinical initialization.

Source acquisition, joins, byte identity and execution chronology belong to the
source wrapper. This module accepts a caller's frame and exports aggregates only.
It reuses the historical classifiers and survey equations without changing them.
"""

from __future__ import annotations

from itertools import combinations
from math import fsum

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from demeter.data import nhanes, survey_joint
from demeter.data.partial_observations import possible_categories
from demeter.schema import EvidenceRegistry

DATASET = "nhanes_glycemic_2021_2023"
METHOD = "multivariate_taylor_ratio_current_cycle_v1"
SOURCE_WEIGHT = "WTSAF2YR"
COMPLETE_LABELS = (*nhanes.STATES, "unclassified")
PARTIAL_PATTERNS = tuple(
    pattern
    for size in range(1, len(nhanes.STATES) + 1)
    for pattern in combinations(nhanes.STATES, size)
)
ELIGIBLE_MEMBERSHIPS = tuple(f"complete:{name}" for name in COMPLETE_LABELS) + tuple(
    "partial:" + "|".join(pattern) for pattern in PARTIAL_PATTERNS
)
CONDITIONAL_MEMBERSHIPS = tuple(f"complete:{name}" for name in nhanes.STATES) + (
    "diagnosis:diagnosed",
    "diagnosis:undiagnosed",
)
AGE_IDS = ("20_plus", "20_39", "40_59", "60_plus")
SEX_CODES = (("all", None), ("male", 1), ("female", 2))
TARGET_DOMAINS = (("20_plus", "all"), ("20_plus", "male"), ("20_plus", "female")) + tuple(
    (age, "all") for age in AGE_IDS[1:]
)
TARGET_CATEGORIES = ("total", "diagnosed", "undiagnosed")
GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
REQUIRED = (
    SOURCE_WEIGHT,
    "SDDSRVYR",
    "RIDSTATR",
    "RIDAGEYR",
    "RIAGENDR",
    "RIDEXPRG",
    "DIQ010",
    "LBXGH",
    "LBXGLU",
    survey_joint.STRATUM,
    survey_joint.PSU,
)


def _real(value) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return bool(np.isfinite(float(value)))
    except (OverflowError, ValueError):
        return False


def definition(registry: EvidenceRegistry) -> dict:
    """Refuse altered inherited rules or a current-cycle activation request."""
    spec = registry.datasets[DATASET]
    inherited = nhanes.definition(registry)["analysis"]
    analysis = spec.get("analysis", {})
    source_fields = {"weight_field", "cycle_code", "examined_code", "topcoded_age"}
    if (
        spec.get("model_role") != "benchmark_only"
        or spec.get("method") != METHOD
        or any(spec.get(name) is not False for name in GATES)
        or not isinstance(analysis, dict)
        or analysis.get("weight_field") != SOURCE_WEIGHT
        or type(analysis.get("cycle_code")) is not int
        or analysis["cycle_code"] != 12
        or type(analysis.get("examined_code")) is not int
        or analysis["examined_code"] != 2
        or type(analysis.get("topcoded_age")) is not int
        or analysis["topcoded_age"] != 80
        or {key: value for key, value in analysis.items() if key not in source_fields} != inherited
        or tuple(group["id"] for group in inherited["age_groups"]) != AGE_IDS
    ):
        raise ValueError("Current NHANES requires the inherited benchmark-only source definition")
    targets = spec.get("published_diabetes_targets")
    expected = {
        (age, sex, category) for age, sex in TARGET_DOMAINS for category in TARGET_CATEGORIES
    }
    if not isinstance(targets, list) or len(targets) != len(expected):
        raise ValueError("Current NHANES requires exactly 18 published reference cells")
    seen = set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("Invalid current NHANES published reference cell")
        key = tuple(target.get(name) for name in ("age_group", "sex", "category"))
        if (
            any(not isinstance(value, str) for value in key)
            or key not in expected
            or key in seen
            or type(target.get("n")) is not int
            or target["n"] < 0
            or not _real(target.get("percent"))
            or not 0 <= target["percent"] <= 100
            or not _real(target.get("tolerance_pp"))
            or target["tolerance_pp"] != 0.05
        ):
            raise ValueError("Invalid current NHANES published reference cell")
        seen.add(key)
    return spec


def _numeric(series: pd.Series, *, missing: bool = False) -> np.ndarray:
    if (
        not is_numeric_dtype(series.dtype)
        or is_bool_dtype(series.dtype)
        or is_complex_dtype(series.dtype)
        or (not missing and series.isna().any())
    ):
        raise ValueError("Current NHANES source fields require real numeric coding")
    return series.to_numpy(dtype=float, na_value=np.nan)


def _codes(frame: pd.DataFrame, name: str, allowed, *, missing: bool = False):
    values = _numeric(frame[name], missing=missing)
    known = values[~np.isnan(values)] if missing else values
    if not np.isfinite(known).all() or not np.isin(known, allowed).all():
        raise ValueError("Unsupported current NHANES source coding")


def _sample(frame: pd.DataFrame, spec: dict) -> tuple[pd.DataFrame, dict]:
    analysis = spec["analysis"]
    if (
        not isinstance(frame, pd.DataFrame)
        or frame.empty
        or not frame.columns.is_unique
        or not frame.index.is_unique
        or frame.index.to_frame(index=False).isna().to_numpy().any()
        or any(name not in frame for name in REQUIRED)
        or survey_joint.WEIGHT in frame
    ):
        raise ValueError("Current NHANES requires a unique source frame and only WTSAF2YR")
    if "SEQN" in frame:
        keys = _numeric(frame.SEQN)
        if (
            not np.isfinite(keys).all()
            or (keys <= 0).any()
            or (keys != np.floor(keys)).any()
            or frame.SEQN.duplicated().any()
        ):
            raise ValueError("Invalid private current NHANES linkage keys")
    _codes(frame, "SDDSRVYR", [analysis["cycle_code"]])
    _codes(frame, "RIDSTATR", [1, analysis["examined_code"]])
    _codes(frame, "RIAGENDR", [1, 2])
    _codes(frame, "RIDEXPRG", [1, 2, 3], missing=True)
    _codes(frame, "DIQ010", [1, 2, 3, 7, 9], missing=True)
    ages = _numeric(frame.RIDAGEYR)
    if (
        not np.isfinite(ages).all()
        or (ages < 0).any()
        or (ages > analysis["topcoded_age"]).any()
        or (ages != np.floor(ages)).any()
    ):
        raise ValueError("Invalid public current NHANES age coding")
    for name in ("LBXGH", "LBXGLU"):
        _numeric(frame[name], missing=True)
    weights = _numeric(frame[SOURCE_WEIGHT], missing=True)
    present = weights[~np.isnan(weights)]
    if not np.isfinite(present).all() or (present < 0).any():
        raise ValueError("Invalid current NHANES fasting weight")
    sample = frame.loc[frame[SOURCE_WEIGHT] > 0].copy()
    if sample.empty or not sample.RIDSTATR.eq(analysis["examined_code"]).all():
        raise ValueError("Positive fasting weights require a nonempty examined sample")
    for name in (survey_joint.STRATUM, survey_joint.PSU):
        values = _numeric(sample[name])
        if (
            not np.isfinite(values).all()
            or (values <= 0).any()
            or (values != np.floor(values)).any()
        ):
            raise ValueError("Invalid current NHANES positive-weight survey design")
    # This is an internal adapter, never a claim that the source has the old field.
    sample[survey_joint.WEIGHT] = sample[SOURCE_WEIGHT]
    return sample, {
        "source_n": len(frame),
        "positive_weight_n": len(sample),
        "zero_weight_n": int(frame[SOURCE_WEIGHT].eq(0).sum()),
        "missing_weight_n": int(frame[SOURCE_WEIGHT].isna().sum()),
    }


def _observations(sample: pd.DataFrame, registry: EvidenceRegistry, spec: dict):
    analysis = spec["analysis"]
    state = nhanes.classify(sample, analysis)
    possible = possible_categories(sample, registry, "glycemic")
    resolved = possible.sum(axis=1) == 1
    if not possible.any(axis=1).all():
        raise ValueError("Every observation requires at least one compatible category")
    for name in nhanes.STATES:
        if not (resolved & possible[name]).loc[state == name].all():
            raise ValueError("Partial observations contradict complete-case categories")
    memberships = pd.DataFrame(index=sample.index)
    definitions = []
    for name in COMPLETE_LABELS:
        key = f"complete:{name}"
        memberships[key] = state.fillna("unclassified") == name
        definitions.append({"membership": key, "partition": "complete", "categories": [name]})
    for pattern in PARTIAL_PATTERNS:
        key = "partial:" + "|".join(pattern)
        memberships[key] = possible.loc[:, list(pattern)].all(axis=1) & ~possible.loc[
            :, [name for name in nhanes.STATES if name not in pattern]
        ].any(axis=1)
        definitions.append({"membership": key, "partition": "partial", "categories": list(pattern)})
    diabetes = state == "diabetes_any_type"
    memberships["diagnosis:diagnosed"] = diabetes & sample.DIQ010.eq(1)
    memberships["diagnosis:undiagnosed"] = diabetes & sample.DIQ010.isin([2, 3])
    for name in ("diagnosed", "undiagnosed"):
        definitions.append(
            {"membership": f"diagnosis:{name}", "partition": "complete_diabetes_decomposition"}
        )
    for prefix in ("complete:", "partial:"):
        if (
            not memberships[[name for name in memberships if name.startswith(prefix)]]
            .sum(axis=1)
            .eq(1)
            .all()
        ):
            raise ValueError("Observation memberships must form exhaustive disjoint partitions")
    if (
        not memberships[["diagnosis:diagnosed", "diagnosis:undiagnosed"]]
        .sum(axis=1)
        .eq(diabetes.astype(int))
        .all()
    ):
        raise ValueError("Complete-case diabetes diagnosis decomposition does not conserve")
    adult = sample.RIDAGEYR >= analysis["adult_age_min"]
    pregnancy_range = sample.RIAGENDR.eq(2) & sample.RIDAGEYR.between(
        analysis["adult_age_min"], analysis["pregnancy_exclusion_age_max"]
    )
    pregnant = pregnancy_range & sample.RIDEXPRG.eq(1)
    eligible = adult & ~pregnant
    domains = pd.DataFrame(index=sample.index)
    domain_definitions = []
    for family in ("eligible", "complete_case"):
        for age in analysis["age_groups"]:
            for sex, code in SEX_CODES:
                mask = eligible & (sample.RIDAGEYR >= age["min"])
                if age["max"] is not None:
                    mask &= sample.RIDAGEYR <= age["max"]
                if code is not None:
                    mask &= sample.RIAGENDR == code
                if family == "complete_case":
                    mask &= state.notna()
                key = f"{family}:{age['id']}:{sex}"
                domains[key] = mask
                domain_definitions.append(
                    {"domain": key, "family": family, "age_group": age["id"], "sex": sex}
                )
    masks = {
        "under_adult_minimum": ~adult,
        "adult": adult,
        "known_pregnancy": pregnant,
        "eligible": eligible,
        "complete": eligible & state.notna(),
        "unclassified": eligible & state.isna(),
        "unknown_pregnancy_in_released_age_range": pregnancy_range & sample.RIDEXPRG.eq(3),
        "missing_pregnancy_in_released_age_range": pregnancy_range & sample.RIDEXPRG.isna(),
        "pregnancy_unavailable_outside_released_age_range": adult
        & sample.RIAGENDR.eq(2)
        & ~pregnancy_range,
        "known_diagnosis_unclassified_eligible": eligible & state.isna() & sample.DIQ010.eq(1),
    }
    counts = {f"{name}_n": int(mask.sum()) for name, mask in masks.items()}
    total_weight = _weight_sum(sample, pd.Series(True, index=sample.index))
    coverage = {
        "denominator": "All positive fasting-weight design rows; excludes zero/missing weights",
        "total_weight": total_weight,
        "unit": "weighted_population",
        "groups_overlap": True,
        "groups": {
            name: {
                "n": int(mask.sum()),
                "weight": _weight_sum(sample, mask),
                "fraction_of_positive_weight": _weight_sum(sample, mask) / total_weight,
            }
            for name, mask in masks.items()
        },
        "interpretation": "Record and survey-weight coverage, not pregnancy imputation or correction of selection bias",
    }
    return domains, memberships, definitions, domain_definitions, counts, coverage


def _weight_sum(sample: pd.DataFrame, mask: pd.Series) -> float:
    try:
        result = fsum(float(w) for w in sample.loc[mask, SOURCE_WEIGHT])
    except OverflowError as exc:
        raise ValueError("Unrepresentable current NHANES weighted coverage") from exc
    if not np.isfinite(result):
        raise ValueError("Unrepresentable current NHANES weighted coverage")
    return result


def _selected_joint(raw: dict) -> dict:
    indices = [
        i
        for i, coordinate in enumerate(raw["coordinates"])
        if coordinate["membership"]
        in (
            ELIGIBLE_MEMBERSHIPS
            if coordinate["domain"].startswith("eligible:")
            else CONDITIONAL_MEMBERSHIPS
        )
    ]
    return {
        "coordinates": [raw["coordinates"][i] for i in indices],
        "estimates": [raw["estimates"][i] for i in indices],
        "covariance": [[raw["covariance"][i][j] for j in indices] for i in indices],
        "domains": raw["domains"],
        "design": raw["design"]
        | {
            "weight": SOURCE_WEIGHT,
            "internal_working_weight": survey_joint.WEIGHT,
            "weight_adapter": "Verified WTSAF2YR copied into the unchanged kernel's internal WTSAFPRP slot",
        },
    }


def _bounds(joint: dict, domains: list[dict]) -> dict:
    lookup = {(r["domain"], r["membership"]): i for i, r in enumerate(joint["coordinates"])}
    rows, labels, coordinates = [], [], []
    for domain in domains:
        if domain["family"] != "eligible":
            continue
        for name in nhanes.STATES:
            for endpoint in ("lower", "upper"):
                row = np.zeros(len(lookup))
                for pattern in PARTIAL_PATTERNS:
                    if pattern == (name,) if endpoint == "lower" else name in pattern:
                        row[lookup[(domain["domain"], "partial:" + "|".join(pattern))]] = 1
                rows.append(row)
                labels.append(f"{domain['domain']}:{name}:{endpoint}")
                coordinates.append(
                    {"domain": domain["domain"], "category": name, "endpoint": endpoint}
                )
    result = survey_joint.linear_projection(joint, rows, labels)
    return result | {"coordinates": coordinates, "projection": [row.tolist() for row in rows]}


def _scalar_domains(sample, domains, memberships, spec) -> list[dict]:
    reports = []
    for age in spec["analysis"]["age_groups"]:
        for sex, _ in SEX_CODES:
            suffix = f"{age['id']}:{sex}"
            eligible = domains[f"eligible:{suffix}"]
            complete = domains[f"complete_case:{suffix}"]
            estimates = {
                name: nhanes.survey_proportion(
                    sample,
                    complete,
                    memberships[f"complete:{name}"],
                    spec["analysis"]["confidence_level"],
                )
                for name in nhanes.STATES
            }
            diagnosis = {
                name: nhanes.survey_proportion(
                    sample,
                    complete,
                    memberships[f"diagnosis:{name}"],
                    spec["analysis"]["confidence_level"],
                )
                for name in ("diagnosed", "undiagnosed")
            }
            denominator = _weight_sum(sample, eligible)
            missing_weight = _weight_sum(sample, eligible & ~complete)
            reports.append(
                {
                    "age_group": age["id"],
                    "sex": sex,
                    "eligible_n": int(eligible.sum()),
                    "complete_n": int(complete.sum()),
                    "missing_n": int((eligible & ~complete).sum()),
                    "weighted_eligible": denominator,
                    "weighted_unclassified": missing_weight,
                    "missing_weight_fraction": missing_weight / denominator
                    if denominator
                    else None,
                    "states": estimates,
                    "diagnosis": diagnosis,
                }
            )
    return reports


def _published(domains: list[dict], spec: dict) -> dict:
    lookup = {(row["age_group"], row["sex"]): row for row in domains}
    checks = []
    for target in spec["published_diabetes_targets"]:
        row = lookup[(target["age_group"], target["sex"])]
        estimate = (
            row["states"]["diabetes_any_type"]
            if target["category"] == "total"
            else row["diagnosis"][target["category"]]
        )
        percent = None if estimate["estimate"] is None else 100 * estimate["estimate"]
        n_matches = estimate["n"] == target["n"]
        point_matches = (
            percent is not None and abs(percent - target["percent"]) <= target["tolerance_pp"]
        )
        checks.append(
            {
                "age_group": target["age_group"],
                "sex": target["sex"],
                "category": target["category"],
                "published_n": target["n"],
                "reconstructed_n": estimate["n"],
                "published_percent": target["percent"],
                "reconstructed_percent": percent,
                "tolerance_pp": target["tolerance_pp"],
                "sample_size_matches": n_matches,
                "point_rounding_matches": point_matches,
                "published_ci_percent": target.get("ci_percent"),
                "published_standard_error_percent": target.get("standard_error_percent"),
                "source_table": target.get("table"),
                "reconstructed_interval": estimate["interval"],
                "ci_comparability": "Different interval construction; equality is not a reconstruction requirement",
                "passed": n_matches and point_matches,
            }
        )
    return {
        "locator": "NCHS Data Brief 516, Tables 1–2, crude columns",
        "independent_holdout": False,
        "checks": checks,
        "passed": all(row["passed"] for row in checks),
        "interpretation": "Source-table reconstruction, not clinical calibration; retain complete-case diagnosis even if source denominator differs",
    }


def assess(frame: pd.DataFrame, registry: EvidenceRegistry) -> dict:
    """Return aggregate observations and dependent uncertainty without source admission."""
    spec = definition(registry)
    sample, counts = _sample(frame, spec)
    (
        domains,
        memberships,
        membership_definitions,
        domain_definitions,
        observation_counts,
        coverage,
    ) = _observations(sample, registry, spec)
    raw = survey_joint.joint_proportions(sample, domains, memberships)
    joint = _selected_joint(raw)
    scalar = _scalar_domains(sample, domains, memberships, spec)
    return {
        "schema_version": 1,
        "kind": DATASET,
        "method": METHOD,
        "model_role": "benchmark_only",
        "validation_only": True,
        **{name: False for name in GATES},
        "source_audit_passed": False,
        "source_audit_status": "not_performed_by_in_memory_assessment",
        "population": spec["population"],
        "geography": spec["geography"],
        "time_period": spec["time_period"],
        "unit": "fraction",
        "covariance_unit": "fraction_squared",
        "counts": counts | observation_counts,
        "coverage": coverage,
        "analysis": spec["analysis"],
        "domains": scalar,
        "membership_definitions": membership_definitions,
        "domain_definitions": domain_definitions,
        "joint": joint,
        "bound_endpoints": _bounds(joint, domain_definitions),
        "published_reconstruction": _published(scalar, spec),
        "diagnostics": {
            "selected_coordinates": len(joint["coordinates"]),
            "rectangular_calculation_coordinates": len(raw["coordinates"]),
            "empty_coordinates": sum(value is None for value in joint["estimates"]),
            "matrix_repair_performed": False,
            "expected_singularity": "Partition closure, nested domains and finite PSU support; no ridge or independent draws",
        },
        "denominator_interpretation": "Eligible weight includes unclassified; complete_case conditions on valid interview and both assays. Domains overlap; denominators differ and covariance is joint.",
        "bound_interpretation": "Logical observation-category completion bounds; endpoint covariance is sampling uncertainty, not a simultaneous interval, latent-state allocation or missing-at-random model.",
        "uncertainty": spec["uncertainty"],
        "limitations": spec["limitations"],
    }
