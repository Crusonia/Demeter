"""Synthetic in-memory NHIS-labelled ratio arithmetic, without source admission."""

from __future__ import annotations

import pandas as pd

from demeter.data.nhis_diagnosis_labels import CATEGORIES, classify_reported_diabetes
from demeter.data.survey_joint import PSU, STRATUM, WEIGHT, joint_proportions

_GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
_FIELDS = ("DIBEV_A", "DIBTYPE_A", "WTFA_A", "PSTRAT", "PPSU")


def assess(frame: pd.DataFrame, domains: pd.DataFrame) -> dict:
    """Return private software-validation ratios and full joint Taylor covariance.

    Caller domains must be aligned Boolean columns. All supplied design rows
    participate, including rows outside every domain. Only the existing kernel's
    positive-weight, multi-PSU full-design method is supported. Refusals express
    software limitations, not producer exclusions or clinical identification.
    No source file, population, survey degrees of freedom or interval is admitted.
    """
    if (
        not isinstance(frame, pd.DataFrame)
        or not frame.columns.is_unique
        or any(name not in frame for name in _FIELDS)
    ):
        raise ValueError("Synthetic NHIS frame requires unique native field columns")
    try:
        categories = [
            classify_reported_diabetes(diagnosis, diabetes_type)
            for diagnosis, diabetes_type in zip(frame.DIBEV_A, frame.DIBTYPE_A, strict=True)
        ]
        memberships = pd.DataFrame(
            {category: [value == category for value in categories] for category in CATEGORIES},
            index=frame.index,
        )
        # Select and copy only these native design fields; never mutate input or
        # allow unrelated legacy aliases to override the supplied native columns.
        design = frame[["WTFA_A", "PSTRAT", "PPSU"]].rename(
            columns={"WTFA_A": WEIGHT, "PSTRAT": STRATUM, "PPSU": PSU}
        )
        joint = joint_proportions(design, domains, memberships)
    except (ValueError, TypeError, OverflowError, KeyError):
        raise ValueError(
            "Unsupported synthetic NHIS input or software method: exact category codes, "
            "aligned Boolean domains, finite positive weights and multi-PSU full-design "
            "strata are required; no rows were silently excluded"
        ) from None
    counts = {category: categories.count(category) for category in CATEGORIES}
    return {
        "kind": "nhis_joint_ratio_software_witness",
        "validation_only": True,
        "software_witness": True,
        "private_aggregate": True,
        "source_admitted": False,
        "scientific_gates": dict.fromkeys(_GATES, False),
        "record_ledger": {
            "unit": "input_records",
            "total_records": len(frame),
            "category_counts": counts,
            "ledger_conserved": sum(counts.values()) == len(frame),
        },
        "joint": {
            "coordinates": joint["coordinates"],
            "ratios": joint["estimates"],
            "covariance": joint["covariance"],
            "ratio_unit": "dimensionless",
            "covariance_unit": "dimensionless_squared",
        },
        "design": {
            "weight": "WTFA_A",
            "stratum": "PSTRAT",
            "psu": "PPSU",
            "input_records": len(frame),
            "strata": joint["design"]["strata"],
            "psus": joint["design"]["psus"],
            "software_method": "full_design_with_replacement_first_stage_taylor",
            "weight_policy": "finite_positive_required_without_trimming",
            "singleton_policy": "full_design_singleton_refused",
        },
        "domains": [
            {
                "domain": row["domain"],
                "input_records": row["n"],
                "represented_psus": row["represented_psus"],
                "represented_strata": row["represented_strata"],
                "status": "ratio_computed" if row["n"] else "empty_domain",
            }
            for row in joint["domains"]
        ],
    }
