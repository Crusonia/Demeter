"""Paired source assay ranges, with dependent survey uncertainty, never latent states.

The in-memory API is validation-only. The offline wrapper checks the committed
used-source contract, actual loaded code and immutable inputs before parsing.
Only aggregate observations are returned; no private joined records are exported.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from demeter.data import nhanes, nhanes_current as current
from demeter.data import nhanes_current_store as store
from demeter.data import survey_joint
from demeter.schema import EvidenceRegistry

DATASET = "nhanes_assay_observation_2021_2023"
METHOD = "paired_assay_observation_joint_taylor_v1"
PROTOCOL_PATH = Path("docs/validation/nhanes-assay-mapping-protocol-v1.json")
PROTOCOL_SHA256 = "9b520f8b685af1abb58e1d57e05e80229b6ff39db760ec6302b32f74b6a58bd9"
IMPLEMENTATION = "src/demeter/data/nhanes_assay_mapping.py"
GATES = current.GATES


def _protocol() -> dict:
    content = store._read(PROTOCOL_PATH, "paired assay protocol")
    if store.digest(content) != PROTOCOL_SHA256:
        raise ValueError("NHANES paired assay protocol checksum mismatch")
    protocol = store._json(content)
    if (
        protocol.get("dataset") != DATASET
        or protocol.get("kind") != "nhanes_assay_mapping_protocol"
        or protocol.get("model_role") != "benchmark_only"
        or any(protocol.get(name) is not False for name in GATES)
    ):
        raise ValueError("Invalid frozen NHANES paired assay contract")
    return protocol


def definition(registry: EvidenceRegistry) -> dict:
    """Check exact source-range rules, order and gates without reading records."""
    protocol = _protocol()
    spec = registry.datasets.get(DATASET)
    if (
        not isinstance(spec, dict)
        or any(
            nhanes.encoded(spec.get(key)) != nhanes.encoded(value)
            for key, value in protocol["definition_fields"].items()
        )
        or spec.get("protocol_sha256") != PROTOCOL_SHA256
        or any(spec.get(name) is not False for name in GATES)
        or spec.get("analysis") != current.definition(registry)["analysis"]
    ):
        raise ValueError("NHANES paired assay definition differs from frozen observation contract")
    return spec


def _observations(sample: pd.DataFrame, spec: dict):
    analysis = spec["analysis"]
    values = [sample[name].to_numpy(dtype=float) for name in ("LBXGH", "LBXGLU")]
    valid = [np.isfinite(value) & (value > 0) for value in values]
    bands = []
    for value, present, prefix in zip(values, valid, ("hba1c", "glucose"), strict=True):
        low = analysis[f"{prefix}_prediabetes_min"]
        high = analysis[f"{prefix}_diabetes_min"]
        bands.append(
            [
                present & (value < low),
                present & (value >= low) & (value < high),
                present & (value >= high),
            ]
        )
    both = valid[0] & valid[1]
    memberships = pd.DataFrame(index=sample.index)
    for name, mask in zip(
        spec["eligible_memberships"][:4],
        (both, valid[0] & ~valid[1], ~valid[0] & valid[1], ~valid[0] & ~valid[1]),
        strict=True,
    ):
        memberships[name] = mask
    for name, mask in zip(
        spec["eligible_memberships"][4:],
        (
            sample.DIQ010.eq(1),
            sample.DIQ010.eq(2),
            sample.DIQ010.eq(3),
            sample.DIQ010.isin([7, 9]) | sample.DIQ010.isna(),
        ),
        strict=True,
    ):
        memberships[name] = mask
    for i, a1c in enumerate(bands[0]):
        for j, fpg in enumerate(bands[1]):
            memberships[spec["paired_memberships"][3 * i + j]] = a1c & fpg
    if (
        not memberships[spec["eligible_memberships"][:4]].sum(axis=1).eq(1).all()
        or not memberships[spec["eligible_memberships"][4:]].sum(axis=1).eq(1).all()
        or not memberships[spec["paired_memberships"]].sum(axis=1).eq(both.astype(int)).all()
    ):
        raise ValueError("NHANES observation partitions do not conserve their denominators")
    adult = sample.RIDAGEYR >= analysis["adult_age_min"]
    pregnancy_range = sample.RIAGENDR.eq(2) & sample.RIDAGEYR.between(
        analysis["adult_age_min"], analysis["pregnancy_exclusion_age_max"]
    )
    pregnant = pregnancy_range & sample.RIDEXPRG.eq(1)
    eligible = adult & ~pregnant
    paired_no = eligible & both & sample.DIQ010.eq(2)
    domains = pd.DataFrame(index=sample.index)
    for family, base in (("eligible", eligible), ("paired_no", paired_no)):
        for age in analysis["age_groups"]:
            for sex, code in current.SEX_CODES:
                mask = base & (sample.RIDAGEYR >= age["min"])
                if age["max"] is not None:
                    mask &= sample.RIDAGEYR <= age["max"]
                if code is not None:
                    mask &= sample.RIAGENDR.eq(code)
                domains[f"{family}:{age['id']}:{sex}"] = mask
    discordant = memberships[
        [spec["paired_memberships"][3 * i + j] for i in range(3) for j in range(3) if i != j]
    ].any(axis=1)
    masks = {
        "under_adult_minimum": ~adult,
        "known_pregnancy": pregnant,
        "eligible": eligible,
        "paired_no": paired_no,
        "discordant_paired_no": paired_no & discordant,
        "unknown_pregnancy_in_released_age_range": pregnancy_range & sample.RIDEXPRG.eq(3),
        "missing_pregnancy_in_released_age_range": pregnancy_range & sample.RIDEXPRG.isna(),
        "pregnancy_unavailable_outside_released_age_range": adult
        & sample.RIAGENDR.eq(2)
        & ~pregnancy_range,
    }
    return (
        domains,
        memberships,
        discordant,
        {f"{name}_n": int(mask.sum()) for name, mask in masks.items()},
    )


def _selected_joint(raw: dict, spec: dict) -> dict:
    selected = spec["coordinate_selection_indices"]
    coordinates = [raw["coordinates"][i] for i in selected]
    if coordinates != spec["coordinate_order"]:
        raise ValueError("NHANES paired assay coordinate order differs from frozen contract")
    return {
        "coordinates": coordinates,
        "estimates": [raw["estimates"][i] for i in selected],
        "covariance": [[raw["covariance"][i][j] for j in selected] for i in selected],
        "design": raw["design"]
        | {"weight": current.SOURCE_WEIGHT, "internal_working_weight": survey_joint.WEIGHT},
        "domains": raw["domains"],
    }


def assess(frame: pd.DataFrame, registry: EvidenceRegistry) -> dict:
    """Compute validation-only aggregates; source admission is a separate action."""
    spec = definition(registry)
    sample, counts = current._sample(frame, spec)
    domains, memberships, discordant, observation_counts = _observations(sample, spec)
    raw = survey_joint.joint_proportions(sample, domains, memberships)
    joint = _selected_joint(raw, spec)
    projection = [row["coefficients"] for row in spec["discordance_projection"]]
    labels = [row["label"] for row in spec["discordance_projection"]]
    projected = survey_joint.linear_projection(joint, projection, labels)
    equivalence = []
    for age in spec["age_domain_order"]:
        for sex in spec["sex_domain_order"]:
            domain = f"paired_no:{age}:{sex}"
            mask = domains[domain]
            n = int(mask.sum())
            discordant_n = int((mask & discordant).sum())
            scalar = nhanes.survey_proportion(
                sample, mask, discordant, spec["analysis"]["confidence_level"]
            )
            equivalence.append(
                {
                    "domain": domain,
                    "age_group": age,
                    "sex": sex,
                    "n": n,
                    "discordant_n": discordant_n,
                    "status": "not_evaluable"
                    if n == 0
                    else "contradicted_in_observed_sample"
                    if discordant_n
                    else "not_contradicted_in_observed_sample",
                    "scalar": scalar,
                }
            )
    return {
        "schema_version": 1,
        "kind": DATASET,
        "method": METHOD,
        "model_role": "benchmark_only",
        "validation_only": True,
        "source_audit_passed": False,
        "source_audit_status": "not_performed_by_in_memory_assessment",
        **{name: False for name in GATES},
        "population": spec["population"],
        "geography": spec["geography"],
        "time_period": spec["time_period"],
        "unit": spec["unit"],
        "covariance_unit": spec["covariance_unit"],
        "counts": counts | observation_counts,
        "analysis": spec["analysis"],
        "joint": joint,
        "discordance": projected | {"projection": projection},
        "equivalence": equivalence,
        "diagnostics": {
            "selected_coordinates": len(joint["coordinates"]),
            "rectangular_calculation_coordinates": len(raw["coordinates"]),
            "empty_coordinates": sum(value is None for value in joint["estimates"]),
            "matrix_repair_performed": False,
            "expected_singularity": "Separate partitions, nested domains and finite PSU support; no ridge, independent category draws or denominator independence",
        },
        "eligible_partitions": spec["eligible_partitions"],
        "paired_denominator": spec["paired_denominator"],
        "observation_interpretation": spec["observation_interpretation"],
        "equivalence_result_rule": spec["equivalence_result_rule"],
        "uncertainty": spec["uncertainty"],
        "limitations": spec["limitations"],
    }


def _registry_contract(registry: EvidenceRegistry, protocol: dict) -> dict:
    spec = definition(registry)
    values = registry.model_dump(mode="json")
    for group, scope_key in (
        ("parameters", "preserved_parameter_keys"),
        ("sources", "preserved_source_keys"),
    ):
        scope = spec.get(scope_key)
        if (
            not isinstance(scope, list)
            or any(not isinstance(name, str) or not name for name in scope)
            or scope != sorted(set(scope))
            or scope != protocol[scope_key]
            or any(name not in values[group] for name in scope)
        ):
            raise ValueError("NHANES paired assay preserved evidence scope is invalid")
        if (
            store.digest(nhanes.encoded({name: values[group][name] for name in scope}))
            != protocol[f"existing_{group}_sha256"]
        ):
            raise ValueError("NHANES paired assay changed preserved evidence records")
    for name, expected in protocol["existing_definition_sha256"].items():
        if (
            name not in values["datasets"]
            or store.digest(nhanes.encoded(values["datasets"][name])) != expected
        ):
            raise ValueError("NHANES paired assay changed a preserved dataset definition")
    if (
        spec.get("source_manifest_sha256") != protocol["source_manifest_sha256"]
        or spec.get("source_sha256") != protocol["source_sha256"]
    ):
        raise ValueError("NHANES paired assay source admission differs from frozen identities")
    pins = spec.get("implementation_sha256")
    if not isinstance(pins, dict) or set(pins) != {IMPLEMENTATION}:
        raise ValueError("NHANES paired assay implementation must be explicitly admitted")
    if (
        store.digest(store._read(Path(IMPLEMENTATION), "paired assay implementation"))
        != pins[IMPLEMENTATION]
    ):
        raise ValueError("NHANES paired assay implementation checksum mismatch")
    return spec


def report(registry: EvidenceRegistry, source: Path = store.STORE) -> dict:
    """Offline admitted source replay; verify definitions/code/bytes before parsing."""
    protocol = _protocol()
    spec = _registry_contract(registry, protocol)
    for name, pinned in protocol["existing_artifact_sha256"].items():
        if store.digest(store._read(Path(name), "preserved paired assay artifact")) != pinned:
            raise ValueError("NHANES paired assay preserved artifact checksum mismatch")
    old_protocol = store.verify_protocol()
    store._registry_contract(registry, old_protocol)
    loaded = store._loaded_code(protocol, spec)
    manifest_bytes = store._read(source / "manifest.json", "paired assay source manifest")
    if store.digest(manifest_bytes) != protocol["source_manifest_sha256"]:
        raise ValueError("NHANES paired assay source manifest checksum mismatch")
    manifest, blobs = store._manifest(source, old_protocol, manifest_bytes)
    source_pins = {name: row["sha256"] for name, row in manifest["sources"].items()}
    if source_pins != protocol["source_sha256"]:
        raise ValueError("NHANES paired assay raw source checksum mismatch")
    result = assess(store._frame(source, blobs), registry)
    result["source_audit_passed"] = True
    result["source_audit_status"] = "admitted_sources_definitions_and_implementations_verified"
    result["provenance"] = {
        "evidence_sha256": registry.content_hash,
        "protocol_path": PROTOCOL_PATH.as_posix(),
        "protocol_sha256": PROTOCOL_SHA256,
        "used_source": protocol["used_source"],
        "chronology": protocol["chronology"],
        "source_manifest_sha256": store.digest(manifest_bytes),
        "source_sha256": source_pins,
        "current_report_sha256": protocol["current_report_sha256"],
        "existing_artifact_sha256": protocol["existing_artifact_sha256"],
        "existing_definition_sha256": protocol["existing_definition_sha256"],
        "implementation_sha256": spec["implementation_sha256"],
        "loaded_implementation": loaded,
        "definitions": {DATASET: spec},
        "serialization": "Derived floats rounded to 12 significant digits; not measurement precision",
    }
    return nhanes.storage_numbers(result)
