"""Joint sampling uncertainty of existing glycemic observations, not engine states."""

from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path

import numpy as np
import pandas as pd

from demeter.data import nhanes, survey_joint
from demeter.data.ingest import digest
from demeter.data.partial_observations import possible_categories
from demeter.schema import EvidenceRegistry

DATASET = "glycemic_joint_uncertainty"
METHOD = "multivariate_taylor_ratio_v1"
PROTOCOL_PATH = Path("docs/validation/joint-glycemic-uncertainty-protocol-v1.json")
PROTOCOL_SHA256 = "dd0e88aadac16cc1d180f5be8adff270cbdbaf46d61a53b80ec20be15723454c"
COMPLETE_LABELS = (*nhanes.STATES, "unclassified")
PARTIAL_PATTERNS = tuple(
    pattern
    for size in range(1, len(nhanes.STATES) + 1)
    for pattern in combinations(nhanes.STATES, size)
)


def _definition(registry: EvidenceRegistry) -> dict:
    spec = registry.datasets[DATASET]
    if (
        spec["model_role"] != "benchmark_only"
        or spec["method"] != METHOD
        or any(
            spec[name] is not False
            for name in (
                "direct_initialization_allowed",
                "clinical_fit_allowed",
                "engine_activation_allowed",
                "sampling_distribution_assumed",
            )
        )
    ):
        raise ValueError("Joint glycemic uncertainty requires the frozen benchmark-only method")
    return spec


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate frozen protocol key")
        value[key] = item
    return value


def _frozen_contract(registry: EvidenceRegistry, source: Path) -> tuple[dict, dict]:
    """Verify immutable definitions and implementations before source parsing or math."""
    spec = _definition(registry)
    if (
        Path(spec["protocol_path"]) != PROTOCOL_PATH
        or spec["protocol_sha256"] != PROTOCOL_SHA256
        or spec["source_store"] != nhanes.STORE.as_posix()
    ):
        raise ValueError("Joint glycemic frozen protocol identity mismatch")
    content = PROTOCOL_PATH.read_bytes()
    if digest(content) != PROTOCOL_SHA256:
        raise ValueError("Joint glycemic frozen protocol checksum mismatch")
    protocol = json.loads(content, object_pairs_hook=_unique_object)
    if (
        type(protocol["schema_version"]) is not int
        or protocol["schema_version"] != 1
        or protocol["kind"] != "joint_glycemic_uncertainty_protocol"
        or protocol["method"] != METHOD
        or protocol["complete_labels"] != list(COMPLETE_LABELS)
        or protocol["source_store"] != nhanes.STORE.as_posix()
        or protocol["model_role"] != "benchmark_only"
        or protocol["clinical_activation_allowed"] is not False
        or protocol["direct_initialization_allowed"] is not False
        or protocol["sampling_distribution_assumed"] is not False
    ):
        raise ValueError("Invalid joint glycemic frozen contract")
    checked = {}
    for name, expected in protocol["existing_artifact_sha256"].items():
        path = (
            source / "manifest.json"
            if name == f"{nhanes.STORE.as_posix()}/manifest.json"
            else Path(name)
        )
        actual = digest(path.read_bytes())
        if actual != expected:
            raise ValueError("Joint glycemic original artifact checksum mismatch")
        checked[name] = actual
    for name, expected in protocol["existing_definition_sha256"].items():
        if digest(nhanes.encoded(registry.datasets[name])) != expected:
            raise ValueError("Joint glycemic original definition checksum mismatch")
    return protocol, checked


def _observations(frame: pd.DataFrame, registry: EvidenceRegistry):
    """Reuse the unchanged complete classifier, compatible sets and eligibility."""
    ga = nhanes.definition(registry)["analysis"]
    mapping = registry.datasets["observation_state_mapping"]
    weights = frame.WTSAFPRP.dropna()
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Invalid survey weight")
    sample = frame.loc[frame.WTSAFPRP > 0].copy()
    if (
        not len(sample)
        or not sample.index.is_unique
        or not np.isfinite(sample.RIDAGEYR).all()
        or (sample.RIDAGEYR < 0).any()
        or (sample.RIDAGEYR > mapping["topcoded_age"]).any()
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
    state = nhanes.classify(sample, ga)
    possible = possible_categories(sample, registry, "glycemic")
    if list(possible.columns) != list(nhanes.STATES) or not possible.any(axis=1).all():
        raise ValueError("Invalid compatible glycemic category set")
    resolved = possible.sum(axis=1) == 1
    for name in nhanes.STATES:
        if not (resolved & possible[name]).loc[state == name].all():
            raise ValueError("Partial categories contradict the unchanged complete classifier")
    memberships = pd.DataFrame(index=sample.index)
    definitions = []
    partition = state.fillna("unclassified")
    for name in COMPLETE_LABELS:
        key = f"complete:{name}"
        memberships[key] = partition == name
        definitions.append({"membership": key, "partition": "complete", "categories": [name]})
    for pattern in PARTIAL_PATTERNS:
        key = "partial:" + "|".join(pattern)
        memberships[key] = possible.loc[:, list(pattern)].all(axis=1) & ~possible.loc[
            :, [name for name in nhanes.STATES if name not in pattern]
        ].any(axis=1)
        definitions.append(
            {"membership": key, "partition": "partial", "possible_categories": list(pattern)}
        )
    for partition_name in ("complete", "partial"):
        keys = [row["membership"] for row in definitions if row["partition"] == partition_name]
        if not memberships[keys].sum(axis=1).eq(1).all():
            raise ValueError("Observed categories must form disjoint exhaustive partitions")
    domains = pd.DataFrame(index=sample.index)
    domain_definitions = []
    for age in ga["age_groups"]:
        for sex, code in (("all", None), ("male", 1), ("female", 2)):
            key = f"{age['id']}:{sex}"
            if key in domains:
                raise ValueError("Duplicate registered glycemic domain")
            domain = eligible & (sample.RIDAGEYR >= age["min"])
            if age["max"] is not None:
                domain &= sample.RIDAGEYR <= age["max"]
            if code is not None:
                domain &= sample.RIAGENDR == code
            domains[key] = domain
            domain_definitions.append({"domain": key, "age_group": age["id"], "sex": sex})
    counts = {
        "source_n": len(frame),
        "positive_weight_n": len(sample),
        "under_adult_minimum_n": int((~adult).sum()),
        "known_pregnancy_n": int((adult & pregnant).sum()),
        "eligible_n": int(eligible.sum()),
    }
    return sample, domains, memberships, definitions, domain_definitions, counts


def _bounds(joint: dict, domains: list[dict]) -> dict:
    lookup = {(row["domain"], row["membership"]): i for i, row in enumerate(joint["coordinates"])}
    rows, coordinates, labels = [], [], []
    for domain in domains:
        for name in nhanes.STATES:
            for endpoint in ("lower", "upper"):
                row = np.zeros(len(lookup))
                for pattern in PARTIAL_PATTERNS:
                    selected = pattern == (name,) if endpoint == "lower" else name in pattern
                    if selected:
                        row[lookup[(domain["domain"], "partial:" + "|".join(pattern))]] = 1.0
                rows.append(row)
                label = f"{domain['domain']}:{name}:{endpoint}"
                labels.append(label)
                coordinates.append(
                    {"domain": domain["domain"], "category": name, "endpoint": endpoint}
                )
    matrix = np.asarray(rows)
    projected = survey_joint.linear_projection(joint, matrix, labels)
    return projected | {"coordinates": coordinates, "projection": matrix.tolist()}


def _diagnostics(joint: dict) -> dict:
    available = [i for i, value in enumerate(joint["estimates"]) if value is not None]
    constraints = []
    for domain in joint["domains"]:
        for partition in ("complete", "partial"):
            indices = [
                i
                for i, row in enumerate(joint["coordinates"])
                if row["domain"] == domain["domain"]
                and row["membership"].startswith(f"{partition}:")
            ]
            constraints.append(
                {
                    "domain": domain["domain"],
                    "partition": partition,
                    "coordinates": len(indices),
                    "available": all(joint["estimates"][i] is not None for i in indices),
                    "constraint": "Partition proportions sum to one; its sum vector is a covariance null direction",
                }
            )
    return {
        "available_coordinates": len(available),
        "unavailable_coordinates": len(joint["estimates"]) - len(available),
        "available_domains": sum(row["status"] != "empty_domain" for row in joint["domains"]),
        "empty_domains": sum(row["status"] == "empty_domain" for row in joint["domains"]),
        "partition_constraints": constraints,
        "covariance_construction": "Sum of stratum-centered PSU influence-vector corrected outer products",
        "expected_singularity": "Partition closure and finite PSU support imply null directions; retain the matrix",
        "matrix_repair_performed": False,
        "interpretation": "Numerical symmetry, PSD and null directions checked in tests with software roundoff tolerances; no platform-sensitive spectral or closure residuals serialized",
    }


def assess(frame: pd.DataFrame, registry: EvidenceRegistry) -> dict:
    """In-memory aggregate assessment; source identity is verified by joint_report."""
    spec = _definition(registry)
    sample, domains, memberships, definitions, domain_definitions, counts = _observations(
        frame, registry
    )
    joint = survey_joint.joint_proportions(sample, domains, memberships)
    return {
        "schema_version": 1,
        "kind": DATASET,
        "method": METHOD,
        "model_role": "benchmark_only",
        "validation_only": True,
        "scientific_release_ready": False,
        "direct_initialization_allowed": False,
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "sampling_distribution_assumed": False,
        "source_audit_passed": False,
        "source_audit_status": "not_performed_by_in_memory_assessment",
        "population": spec["population"],
        "geography": spec["geography"],
        "time_period": spec["time_period"],
        "unit": "fraction",
        "covariance_unit": "fraction_squared",
        "denominator": "All eligible weight in each domain, including unclassified observations",
        "counts": counts,
        "membership_definitions": definitions,
        "domain_definitions": domain_definitions,
        "joint": joint,
        "bound_endpoints": _bounds(joint, domain_definitions),
        "bound_interpretation": "Compatible-category ranges; covariance of endpoints is sampling uncertainty, not a simultaneous interval or a point allocation",
        "diagnostics": _diagnostics(joint),
        "uncertainty": spec["uncertainty"],
        "limitations": spec["limitations"],
    }


def joint_report(registry: EvidenceRegistry, source: Path = nhanes.STORE) -> dict:
    """Verify the frozen offline four-source store and export only aggregates."""
    source = Path(source)
    protocol, checked = _frozen_contract(registry, source)
    frame, receipts = nhanes.read_store(source)
    report = assess(frame, registry)
    report["source_audit_passed"] = True
    report["source_audit_status"] = "passed_frozen_source_and_definition_checks"
    paths = (
        Path("src/demeter/data/glycemic_uncertainty.py"),
        Path("src/demeter/data/survey_joint.py"),
    )
    report["provenance"] = {
        "evidence_sha256": registry.content_hash,
        "protocol_path": PROTOCOL_PATH.as_posix(),
        "protocol_sha256": PROTOCOL_SHA256,
        "used_source": protocol["used_source"],
        "chronology": protocol["chronology"],
        "source_manifest_sha256": digest((source / "manifest.json").read_bytes()),
        "source_sha256": {name: row["sha256"] for name, row in receipts["sources"].items()},
        "existing_artifact_sha256": checked,
        "existing_definition_sha256": protocol["existing_definition_sha256"],
        "implementation_sha256": {path.as_posix(): digest(path.read_bytes()) for path in paths},
        "definitions": {
            DATASET: registry.datasets[DATASET],
            "glycemic": nhanes.definition(registry)["analysis"],
        },
        "serialization": "Derived floats rounded to 12 significant digits; not measurement precision",
    }
    return nhanes.storage_numbers(report)
