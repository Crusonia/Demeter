"""Audit a public aggregate cohort and its coupled ascertainment bounds, offline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from demeter.analysis.followup_category_bounds import followup_category_bounds
from demeter.data.malawi_cohort import extract_malawi_cohort
from demeter.data.nhanes import encoded

DATASET = "malawi_followup_benchmark"
SOURCE = "malawi2023_public_cohort"
PROTOCOL_PATH = "docs/validation/malawi-cohort-intake-protocol-v1.json"
REPORT_PATH = "docs/validation/malawi-cohort-ascertainment-v1.json"
PROTOCOL_SHA256 = "0a1d1b7bbde1bca3f15aecf1b395050b2a0277c9e385f799889a8c6786e5aafb"
GATES = {
    "clinical_fit_allowed": False,
    "engine_activation_allowed": False,
    "independent_validation_allowed": False,
    "scientific_release_ready": False,
}
TRANSFORMS = {
    "extractor": "src/demeter/data/malawi_cohort.py",
    "bounds": "src/demeter/analysis/followup_category_bounds.py",
}


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _artifact(root: Path, name: str, expected: str) -> bytes:
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Malawi artifact path is invalid")
    content = path.read_bytes()
    if _digest(content) != expected:
        raise ValueError("Malawi artifact checksum mismatch")
    return content


def _contract(registry, root: Path) -> tuple[dict, dict]:
    spec = registry.datasets[DATASET]
    if (
        spec["model_role"] != "benchmark_only"
        or spec["source_id"] != SOURCE
        or spec["protocol_path"] != PROTOCOL_PATH
        or spec["report_path"] != REPORT_PATH
        or spec["protocol_sha256"] != PROTOCOL_SHA256
        or spec["scientific_gates"] != GATES
        or any(value is not False for value in spec["scientific_gates"].values())
    ):
        raise ValueError("Malawi frozen benchmark contract mismatch")
    protocol = json.loads(_artifact(root, PROTOCOL_PATH, PROTOCOL_SHA256))
    if protocol["scientific_gates"] != GATES or any(
        value is not False for value in protocol["scientific_gates"].values()
    ):
        raise ValueError("Malawi benchmark cannot permit a scientific gate")
    source = registry.sources[SOURCE]
    if (
        source.doi != protocol["source"]["doi"]
        or source.sha256 != protocol["source"]["sha256"]
        or source.url != protocol["source"]["url"]
        or source.raw_filename != protocol["source"]["raw_filename"]
        or source.license != "CC-BY-4.0"
    ):
        raise ValueError("Malawi source receipt mismatch")
    if set(spec["transforms"]) != set(TRANSFORMS):
        raise ValueError("Malawi transform inventory mismatch")
    for key, name in TRANSFORMS.items():
        transform = spec["transforms"][key]
        if transform["path"] != name:
            raise ValueError("Malawi transform path mismatch")
        _artifact(root, name, transform["sha256"])
    return spec, protocol


def _registered_facts(registry, protocol: dict, observations: dict) -> None:
    """Bind each literal to its registry record without activating engine inputs."""
    if type(observations) is not dict or set(observations) != {
        "source_sha256",
        "source_size_bytes",
        "doi",
        "observed",
        "derived",
        "source_locators",
        "source_discrepancies",
        "scientific_gates",
    }:
        raise ValueError("Malawi source report fields are out of scope")
    if (
        observations["source_sha256"] != protocol["source"]["sha256"]
        or type(observations["source_size_bytes"]) is not int
        or observations["source_size_bytes"] != protocol["source"]["size_bytes"]
        or observations["doi"] != protocol["source"]["doi"]
    ):
        raise ValueError("Malawi source report identity mismatch")
    captures = {capture["name"]: capture for capture in protocol["captures"]}
    if len(captures) != len(protocol["captures"]) or set(observations["observed"]) != set(captures):
        raise ValueError("Malawi observed fact inventory mismatch")
    values = {**observations["observed"], **observations["derived"]}
    if set(observations["derived"]) != {"untraced_count"}:
        raise ValueError("Malawi derived fact inventory mismatch")
    for name, value in values.items():
        parameter = registry.parameters["malawi_" + name]
        derived = name == "untraced_count"
        if (
            type(value) not in (int, float)
            or parameter.value != value
            or parameter.status != ("derived" if derived else "observed")
            or parameter.evidence_grade != "C"
            or parameter.model_role != "benchmark_only"
            or parameter.source_id != SOURCE
            or parameter.source_url != registry.sources[SOURCE].url
            or parameter.unresolved
            or parameter.uncertainty is None
            or parameter.uncertainty.kind != "fixed"
            or parameter.unit != ("people" if derived else captures[name]["unit"])
            or (not derived and value != captures[name]["expected"])
            or (
                not derived
                and type(value) is not (int if captures[name]["type"] == "int" else float)
            )
        ):
            raise ValueError("Malawi fact/registry provenance mismatch")
    observed = observations["observed"]
    expected_locators = {
        name: protocol["selectors"][capture["selector"]]["xpath"]
        for name, capture in captures.items()
    }
    expected_discrepancies = {
        "ifg_lower_threshold_mmol_l": {
            "baseline": observed["baseline_ifg_lower_mmol_l"],
            "followup": observed["followup_ifg_lower_mmol_l"],
        },
        "person_years": {
            "abstract": observed["abstract_person_years"],
            "results": observed["results_person_years"],
        },
    }
    if (
        observations["source_locators"] != expected_locators
        or observations["source_discrepancies"] != expected_discrepancies
    ):
        raise ValueError("Malawi source locator or discrepancy mismatch")
    if (
        any(
            type(observed[key]) is not int or observed[key] < 0
            for key in (
                "cohort_count",
                "traced_count",
                "assessed_count",
                "confirmed_deaths_count",
                "ngt_count",
                "ifg_count",
                "dm_count",
            )
        )
        or observed["traced_count"]
        != observed["assessed_count"] + observed["confirmed_deaths_count"]
        or observed["assessed_count"]
        != sum(observed[key] for key in ("ngt_count", "ifg_count", "dm_count"))
        or type(observations["derived"]["untraced_count"]) is not int
        or observations["derived"]["untraced_count"]
        != observed["cohort_count"] - observed["traced_count"]
    ):
        raise ValueError("Malawi original-cohort conservation mismatch")
    if observations["scientific_gates"] != GATES or any(
        value is not False for value in observations["scientific_gates"].values()
    ):
        raise ValueError("Malawi source extraction cannot authorize a clinical fit")


def build_malawi_report(registry, root: Path, observations: dict) -> dict:
    """Create a source-record benchmark; this function performs no source download."""
    root = root.resolve()
    _, protocol = _contract(registry, root)
    _registered_facts(registry, protocol, observations)
    values = observations["observed"]
    bounds = followup_category_bounds(
        values["cohort_count"],
        {"NGT": values["ngt_count"], "IFG": values["ifg_count"], "DM": values["dm_count"]},
        values["confirmed_deaths_count"],
        observations["derived"]["untraced_count"],
    )
    return {
        "schema_version": 1,
        "report_id": "malawi-public-cohort-ascertainment-v1",
        "status": "BENCHMARK ONLY — SOURCE RECORDS, NOT CLINICAL TRANSITION RATES",
        "protocol_sha256": PROTOCOL_SHA256,
        "source_facts": observations,
        "ascertainment_bounds": bounds,
        "completion_estimand": {
            "target": "Hypothetical completion of source follow-up category/death dispositions",
            "untraced_people_have_observed_ascertainment_dates": False,
            "known_alive_status": "At each recorded assessment only; not through study close",
            "death_bounds": "Disposition-completion fractions, not fixed-horizon mortality",
            "cumulative_diagnosis_including_before_death_identified": False,
        },
        "limitations": protocol["limitations"],
        "scientific_gates": dict(GATES),
        "working_fit_performed": False,
        "sampling_interval": None,
        "participant_records_used": False,
        "dietary_causal_effect_identified": False,
    }


def audit_malawi_cohort(registry, root: Path, *, raw: Path | None = None) -> dict:
    """Check frozen facts offline; optionally reproduce them from pinned public XML."""
    root = root.resolve()
    spec, protocol = _contract(registry, root)
    content = _artifact(root, REPORT_PATH, spec["report_sha256"])
    frozen = json.loads(content)
    rebuilt = build_malawi_report(registry, root, frozen["source_facts"])
    if encoded(rebuilt) != content:
        raise ValueError("Malawi frozen source report or derived bounds mismatch")
    if raw is not None:
        extracted = extract_malawi_cohort(raw.read_bytes(), protocol)
        if encoded(build_malawi_report(registry, root, extracted)) != content:
            raise ValueError("Malawi raw-source reproduction mismatch")
    return {
        "registered_artifacts_verified": True,
        "raw_values_read": raw is not None,
        "source_aggregates_reproduced": True if raw is not None else None,
        "network_used": False,
        "clinical_transition_fit_performed": False,
        "engine_activation_allowed": False,
        "scientific_release_ready": False,
        "report": rebuilt,
    }
