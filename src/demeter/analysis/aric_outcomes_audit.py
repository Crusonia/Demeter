"""Audit overlapping public ARIC source panels without fitting clinical hazards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from demeter.analysis.source_panel_reconstruction import reconstruct_source_panels
from demeter.data.aric_outcomes import extract_aric_source_records
from demeter.data.nhanes import encoded

DATASET = "aric_outcomes_benchmark"
PROTOCOL_PATH = "docs/validation/aric-outcomes-intake-protocol-v1.json"
REPORT_PATH = "docs/validation/aric-outcomes-reconstruction-v1.json"
PROTOCOL_SHA256 = "00ddb6d4f74d859c28a7c7b716a1bfa4c08c80612e3335a6c22a80ac1cdb9a78"
# Bind complete typed parameter/source records and the dataset, including provenance.
REGISTRY_RECORDS_SHA256 = "fdcaa913fc371d7fe75fff180ddf884f3fa8c2e0b34035cce372b2844362e408"
TRANSFORMS = {
    "extractor": "src/demeter/data/aric_outcomes.py",
    "reconstruction": "src/demeter/analysis/source_panel_reconstruction.py",
}
GATES = {
    "clinical_fit_allowed": False,
    "engine_activation_allowed": False,
    "independent_validation_allowed": False,
    "scientific_release_ready": False,
}


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _artifact(root: Path, name: str, expected: str) -> bytes:
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("ARIC artifact path is invalid")
    content = path.read_bytes()
    if _digest(content) != expected:
        raise ValueError("ARIC artifact checksum mismatch")
    return content


def _protocol(root: Path) -> dict:
    protocol = json.loads(_artifact(root, PROTOCOL_PATH, PROTOCOL_SHA256))
    if protocol["scientific_gates"] != GATES or any(
        value is not False for value in protocol["scientific_gates"].values()
    ):
        raise ValueError("ARIC source contract cannot permit scientific activation")
    return protocol


def registry_records(registry, protocol: dict) -> dict:
    """Complete scoped records; unrelated future evidence may change separately."""
    names = ["aric_panel_" + item["name"] for item in protocol["captures"]]
    names += ["aric_panel_" + item["name"] for item in protocol["derived_parameters"]]
    return {
        "parameters": {name: registry.parameters[name].model_dump(mode="json") for name in names},
        "sources": {
            item["source_id"]: registry.sources[item["source_id"]].model_dump(mode="json")
            for item in protocol["sources"].values()
        },
        "dataset": registry.datasets[DATASET],
    }


def _contract(registry, root: Path) -> tuple[dict, dict]:
    protocol = _protocol(root)
    spec = registry.datasets[DATASET]
    canonical = json.dumps(
        registry_records(registry, protocol),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    if _digest(canonical) != REGISTRY_RECORDS_SHA256:
        raise ValueError("ARIC complete registry records or provenance mismatch")
    if (
        spec["model_role"] != "benchmark_only"
        or spec["protocol_path"] != PROTOCOL_PATH
        or spec["protocol_sha256"] != PROTOCOL_SHA256
        or spec["report_path"] != REPORT_PATH
        or spec["scientific_gates"] != GATES
        or any(value is not False for value in spec["scientific_gates"].values())
        or set(spec["transforms"]) != set(TRANSFORMS)
    ):
        raise ValueError("ARIC frozen benchmark contract mismatch")
    for name, path in TRANSFORMS.items():
        transform = spec["transforms"][name]
        if transform["path"] != path:
            raise ValueError("ARIC transform path mismatch")
        _artifact(root, path, transform["sha256"])
    for source in protocol["sources"].values():
        receipt = registry.sources[source["source_id"]]
        if (
            receipt.doi != source["doi"]
            or receipt.sha256 != source["sha256"]
            or receipt.url != source["url"]
            or receipt.raw_filename != source["raw_filename"]
            or receipt.license != source["license"]
        ):
            raise ValueError("ARIC source receipt mismatch")
    return spec, protocol


def _facts(protocol: dict, observations: dict) -> dict:
    if type(observations) is not dict or set(observations) != {
        "source_sha256",
        "source_size_bytes",
        "doi",
        "observed",
        "source_locators",
        "scientific_gates",
    }:
        raise ValueError("ARIC source facts are out of scope")
    sources = protocol["sources"]
    if (
        observations["doi"] != sources["supplement"]["doi"]
        or observations["source_sha256"] != {key: item["sha256"] for key, item in sources.items()}
        or type(observations["source_size_bytes"]) is not dict
        or observations["source_size_bytes"]
        != {key: item["size_bytes"] for key, item in sources.items()}
        or any(type(value) is not int for value in observations["source_size_bytes"].values())
        or observations["scientific_gates"] != GATES
        or any(value is not False for value in observations["scientific_gates"].values())
    ):
        raise ValueError("ARIC source identity or gates mismatch")
    captures = {item["name"]: item for item in protocol["captures"]}
    observed = observations["observed"]
    if (
        type(observed) is not dict
        or len(captures) != len(protocol["captures"])
        or set(observed) != set(captures)
        or observations["source_locators"]
        != {name: capture["source_locator"] for name, capture in captures.items()}
    ):
        raise ValueError("ARIC source fact inventory or locator mismatch")
    for name, capture in captures.items():
        expected_type = int if capture["type"] == "integer" else float
        if type(observed[name]) is not expected_type or observed[name] != capture["expected"]:
            raise ValueError("ARIC source literal mismatch")
    return observed


def build_aric_report(root: Path, observations: dict) -> dict:
    """Source-only arithmetic; source scope is fixed before any registry operation."""
    root = root.resolve()
    protocol = _protocol(root)
    values = _facts(protocol, observations)
    panels = {}
    for assay in ("a1c", "fg"):
        panels[assay] = {}
        for row in ("normal", "prediabetes"):
            prefix = assay + "_" + row + "_"
            panels[assay][row] = {
                "baseline_count": values[prefix + "baseline_count"],
                "normal": values[prefix + "followup_normal_count"],
                "prediabetes": values[prefix + "followup_prediabetes_count"],
                "total_diabetes": values[prefix + "displayed_diabetes_count"],
                "mortality": values[prefix + "displayed_mortality_count"],
            }
    reconstructed = reconstruct_source_panels(
        values["original_analytic_count"],
        {assay: values["original_" + assay + "_prediabetes_count"] for assay in panels},
        panels,
        source_subset_identity_declared=protocol["derivation_contract"][
            "source_subset_identity_declared"
        ],
    )
    derived = {
        "selected_from_dispositions_count": (
            values["attended_visit6_count"] + values["died_before_visit6_count"]
        ),
        "displayed_diabetes_count": sum(row["total_diabetes"] for row in panels["a1c"].values()),
        "displayed_mortality_count": sum(row["mortality"] for row in panels["a1c"].values()),
    }
    for assay, panel in reconstructed["panels"].items():
        derived["original_" + assay + "_normal_count"] = panel["rows"]["normal"][
            "original_baseline_count"
        ]
        for row, reconstructed_row in panel["rows"].items():
            derived[assay + "_" + row + "_unrepresented_baseline_margin"] = reconstructed_row[
                "source_partition_counts"
            ]["unrepresented_baseline_margin"]
    derived.update(
        {
            "cumulative_minus_displayed_diabetes_count": (
                values["cumulative_total_diabetes_count"] - derived["displayed_diabetes_count"]
            ),
            "displayed_minus_previsit_mortality_count": (
                derived["displayed_mortality_count"] - values["died_before_visit6_count"]
            ),
            "original_a1c_only_prediabetes_count": (
                values["original_a1c_prediabetes_count"] - values["original_both_prediabetes_count"]
            ),
            "original_fg_only_prediabetes_count": (
                values["original_fg_prediabetes_count"] - values["original_both_prediabetes_count"]
            ),
            "original_neither_prediabetes_count": (
                values["original_analytic_count"] - values["original_either_prediabetes_count"]
            ),
        }
    )
    if (
        set(derived) != {item["name"] for item in protocol["derived_parameters"]}
        or derived["selected_from_dispositions_count"] != values["selected_count"]
        or reconstructed["counts"]["selected_unique_people"] != values["selected_count"]
        or reconstructed["counts"]["unrepresented_baseline_margin"]
        != values["alive_nonattender_count"]
        or derived["displayed_diabetes_count"]
        != sum(row["total_diabetes"] for row in panels["fg"].values())
        or derived["displayed_mortality_count"]
        != sum(row["mortality"] for row in panels["fg"].values())
        or derived["displayed_mortality_count"] != values["cumulative_mortality_count"]
        or any(type(value) is not int or value < 0 for value in derived.values())
        or values["original_a1c_prediabetes_count"]
        + values["original_fg_prediabetes_count"]
        - values["original_both_prediabetes_count"]
        != values["original_either_prediabetes_count"]
    ):
        raise ValueError("ARIC source partitions or derived inventory mismatch")
    original_joint = {
        "a1c_normal": {
            "fg_normal": derived["original_neither_prediabetes_count"],
            "fg_prediabetes": derived["original_fg_only_prediabetes_count"],
        },
        "a1c_prediabetes": {
            "fg_normal": derived["original_a1c_only_prediabetes_count"],
            "fg_prediabetes": values["original_both_prediabetes_count"],
        },
    }
    return {
        "schema_version": 1,
        "report_id": "aric-public-outcomes-reconstruction-v1",
        "status": "BENCHMARK ONLY — PUBLIC SOURCE PARTITIONS, NOT CLINICAL TRANSITIONS",
        "protocol_sha256": PROTOCOL_SHA256,
        "source_facts": observations,
        "derived_counts": derived,
        "conditional_source_reconstruction": reconstructed,
        "original_assay_joint_baseline_counts": original_joint,
        "derivation_contract": protocol["derivation_contract"],
        "source_contrasts": {
            "cumulative_vs_displayed_diabetes": {
                "cumulative": values["cumulative_total_diabetes_count"],
                "displayed": derived["displayed_diabetes_count"],
                "difference_is_diagnosis_before_death_count": False,
            },
            "displayed_vs_previsit_mortality": {
                "displayed": derived["displayed_mortality_count"],
                "before_visit6": values["died_before_visit6_count"],
                "additional_slots_allocated_to_attenders": False,
            },
        },
        "limitations": protocol["limitations"],
        "scientific_gates": dict(GATES),
        "working_fit_performed": False,
        "sampling_interval": None,
        "participant_records_used": False,
        "cross_assay_joint_followup_identified": False,
        "dietary_causal_effect_identified": False,
    }


def audit_aric_outcomes(registry, root: Path, *, source_cache: Path | None = None) -> dict:
    """Audit frozen aggregates offline; optional replay requires both public sources."""
    root = root.resolve()
    spec, protocol = _contract(registry, root)
    content = _artifact(root, REPORT_PATH, spec["report_sha256"])
    frozen = json.loads(content)
    rebuilt = build_aric_report(root, frozen["source_facts"])
    if encoded(rebuilt) != content:
        raise ValueError("ARIC frozen source report or reconstruction mismatch")
    captures = {item["name"]: item for item in protocol["captures"]}
    for name, value in {
        **rebuilt["source_facts"]["observed"],
        **rebuilt["derived_counts"],
    }.items():
        parameter = registry.parameters["aric_panel_" + name]
        observed = name in captures
        source_id = protocol["sources"][captures[name]["source"]]["source_id"] if observed else None
        if (
            parameter.value != value
            or parameter.status != ("observed" if observed else "derived")
            or parameter.model_role != "benchmark_only"
            or parameter.evidence_grade != "C"
            or parameter.unresolved
            or parameter.uncertainty is None
            or parameter.uncertainty.kind != "fixed"
            or parameter.unit != (captures[name]["unit"] if observed else "persons")
            or (observed and parameter.source_id != source_id)
        ):
            raise ValueError("ARIC fact and registry mismatch")
    if source_cache is not None:
        raw = {
            name: (source_cache / item["raw_filename"]).read_bytes()
            for name, item in protocol["sources"].items()
        }
        observations = extract_aric_source_records(
            raw["supplement"], raw["pubmed_abstract"], protocol
        )
        if encoded(build_aric_report(root, observations)) != content:
            raise ValueError("ARIC public sources do not reproduce the frozen report")
    return {
        "registered_artifacts_verified": True,
        "raw_values_read": source_cache is not None,
        "source_aggregates_reproduced": True if source_cache is not None else None,
        "network_used": False,
        "clinical_transition_fit_performed": False,
        "engine_activation_allowed": False,
        "scientific_release_ready": False,
        "report": rebuilt,
    }
