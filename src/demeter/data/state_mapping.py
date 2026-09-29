"""Audit survey coverage and the unresolved mapping to engine health states."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from demeter.data.ingest import digest
from demeter.data.nhanes import (
    STATES as GLYCEMIC_STATES,
    classify as classify_glycemic,
    definition as glycemic_definition,
    encoded,
    survey_proportion,
)
from demeter.data.prechronic import (
    STATES as RISK_STATES,
    classify as classify_risk,
    definition as risk_definition,
    read_store,
)
from demeter.schema import EvidenceRegistry

DATASET = "observation_state_mapping"


def assess(frame: pd.DataFrame, registry: EvidenceRegistry) -> dict:
    """Retain unclassified weight in every domain; never initialize engine states."""
    spec = registry.datasets[DATASET]
    if spec["model_role"] != "benchmark_only" or spec["direct_initialization_allowed"] is not False:
        raise ValueError("Observation crosswalk must remain benchmark-only without initialization")
    ga = glycemic_definition(registry)["analysis"]
    ra = risk_definition(registry)["analysis"]
    weights = frame.WTSAFPRP.dropna()
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Invalid survey weight")
    sample = frame.loc[frame.WTSAFPRP > 0].copy()
    if (
        not len(sample)
        or not np.isfinite(sample.RIDAGEYR).all()
        or (sample.RIDAGEYR < 0).any()
        or (sample.RIDAGEYR > spec["topcoded_age"]).any()
        or not sample.RIAGENDR.isin([1, 2]).all()
    ):
        raise ValueError("Empty survey design or invalid public age/sex coding")
    adult = sample.RIDAGEYR >= ga["adult_age_min"]
    pregnant = (
        (sample.RIAGENDR == 2)
        & sample.RIDAGEYR.between(ga["adult_age_min"], ga["pregnancy_exclusion_age_max"])
        & (sample.RIDEXPRG == 1)
    )
    eligible = adult & ~pregnant
    glycemic = classify_glycemic(sample, ga)
    categories = {"glycemic": glycemic}
    categories.update({key: classify_risk(sample, ra, ga, key) for key in ra["definitions"]})
    diagnosed = sample.DIQ010 == 1
    subthreshold = (
        glycemic.notna()
        & (sample.LBXGH < ga["hba1c_diabetes_min"])
        & (sample.LBXGLU < ga["glucose_diabetes_min"])
    )
    definitions = []
    for key, state in categories.items():
        names = (*GLYCEMIC_STATES, "unclassified") if key == "glycemic" else (
            *RISK_STATES,
            "unclassified",
        )
        partition = state.fillna("unclassified")
        if not partition.isin(names).all():
            raise ValueError("Unknown observed category")
        rows = []
        for age in ga["age_groups"]:
            for sex, code in (("all", None), ("male", 1), ("female", 2)):
                domain = eligible & (sample.RIDAGEYR >= age["min"])
                if age["max"] is not None:
                    domain &= sample.RIDAGEYR <= age["max"]
                if code is not None:
                    domain &= sample.RIAGENDR == code
                observed = {}
                for name in names:
                    membership = partition == name
                    observed[name] = {
                        "sample_n": int((domain & membership).sum()),
                        "eligible_weight_proportion": survey_proportion(
                            sample, domain, membership, ga["confidence_level"]
                        ),
                    }
                missing_glycemic = domain & glycemic.isna()
                missing_other = domain & glycemic.notna() & state.isna()
                rows.append(
                    {
                        "age_group": age["id"],
                        "sex": sex,
                        "eligible_n": int(domain.sum()),
                        "classified_n": int((domain & state.notna()).sum()),
                        "unclassified_n": int((domain & state.isna()).sum()),
                        "eligible_weight": float(sample.loc[domain, "WTSAFPRP"].sum()),
                        "public_age_topcode_n": int(
                            (domain & (sample.RIDAGEYR == spec["topcoded_age"])).sum()
                        ),
                        "categories": observed,
                        "unclassified_reasons_n": {
                            "incomplete_glycemic_observation": int(missing_glycemic.sum()),
                            "incomplete_other_risk_or_diagnosis": int(missing_other.sum()),
                        },
                        "diagnosis_checks_n": {
                            "reported_diabetes_with_subdiabetic_labs": int(
                                (domain & diagnosed & subthreshold).sum()
                            ),
                            "reported_diabetes_but_unclassified": int(
                                (domain & diagnosed & state.isna()).sum()
                            ),
                        },
                    }
                )
        definitions.append({"id": key, "domains": rows})
    return {
        "schema_version": 1,
        "kind": DATASET,
        "model_role": "benchmark_only",
        "validation_only": True,
        "scientific_release_ready": False,
        "direct_initialization_allowed": False,
        "population": spec["population"],
        "geography": spec["geography"],
        "time_period": spec["time_period"],
        "unit": spec["unit"],
        "counts": {
            "source_n": len(frame),
            "positive_weight_n": len(sample),
            "under_adult_minimum_n": int((~adult).sum()),
            "known_pregnancy_n": int((adult & pregnant).sum()),
            "eligible_n": int(eligible.sum()),
        },
        "denominator": "All eligible weight in each age/sex domain, including unclassified records",
        "uncertainty": spec["uncertainty"],
        "definitions": definitions,
        "crosswalk": spec["crosswalk"],
        "limitations": spec["limitations"],
    }


def mapping_report(registry: EvidenceRegistry) -> dict:
    """Read the existing immutable stores; return aggregate observations only."""
    frame, receipts = read_store()
    report = assess(frame, registry)
    report["provenance"] = {
        "evidence_sha256": registry.content_hash,
        "source_receipts_sha256": digest(encoded(receipts)),
        "source_sha256": {
            group: {name: row["sha256"] for name, row in receipt["sources"].items()}
            for group, receipt in receipts.items()
        },
        "implementation_sha256": {
            path: digest(Path(path).read_bytes())
            for path in (
                "src/demeter/data/state_mapping.py",
                "src/demeter/data/nhanes.py",
                "src/demeter/data/prechronic.py",
            )
        },
        "definitions": {
            DATASET: registry.datasets[DATASET],
            "glycemic": glycemic_definition(registry)["analysis"],
            "risk": risk_definition(registry)["analysis"],
        },
    }
    return report
