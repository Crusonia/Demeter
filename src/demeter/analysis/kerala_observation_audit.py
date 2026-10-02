"""Replay pinned source-native observations without publishing participant paths."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from demeter.analysis import kerala_coverage as coverage
from demeter.analysis.kerala_registration import verify_registered
from demeter.data.kerala_observations import build_source_observations, public_diagnostics
from demeter.data.nhanes import encoded


DATASET = "kerala_nominal_observations"
SOURCE = "kerala2018_public_trial_v3"
PROTOCOL_ID = "kerala-source-native-nominal-observations-v1"
REPORT_ID = "kerala-source-native-nominal-observation-audit-v1"

ALGEBRA = {
    "fully_interpretable_triples",
    "suffix_positive_union",
    "suffix_positive_overlap",
    "total_negative_with_positive_suffix",
    "total_positive_with_both_suffixes_negative",
    "unknown_total_with_positive_suffix",
}
CHECKS = {
    "ada_category_and_flag_agree_where_both_interpretable",
    "later_two_hour_storage_absent_after_earlier_ada_positive_compatible",
}
KINDS = {"number", "boolean", "absent", "empty", "formula_unsupported", "error", "unsupported"}


def _validate_diagnostics(value):
    """Enforce the publication allowlist even for a resealed edited artifact.

    Pins detect byte drift; this separate shape/vocabulary guard prevents a changed
    report and registry from declaring private paths, keys or assay-value tokens.
    """
    allowed = (
        coverage.GATES
        | CHECKS
        | {
            "subjects",
            "nominal_rows",
            "assignment_marginal",
            "horizon_total_marginal",
            "visit_marginals",
            "incidence_flag_algebra",
            "unlabeled_observation_pattern_cell_size_histogram",
            "individual_death_contact_confirmation_and_first_onset_unknown",
        }
    )
    if type(value) is not dict or set(value) != allowed:
        raise ValueError("Unapproved public diagnostic fields")
    n = value["subjects"]
    if (
        type(n) is not int
        or n < 0
        or type(value["nominal_rows"]) is not int
        or value["nominal_rows"] != 3 * n
    ):
        raise ValueError("Public subject/nominal-row conservation failed")
    coverage._gates({key: value[key] for key in coverage.GATES})
    if value["individual_death_contact_confirmation_and_first_onset_unknown"] is not True:
        raise ValueError("Unknown source clinical observations cannot be inferred")
    if any(value[key] is not None and type(value[key]) is not bool for key in CHECKS):
        raise ValueError("Public consistency checks must be Boolean or unevaluated")

    def margin(counts, tokens):
        if (
            type(counts) is not dict
            or not set(counts).issubset(tokens)
            or any(type(count) is not int or not 0 <= count <= n for count in counts.values())
            or sum(counts.values()) != n
        ):
            raise ValueError("Unapproved public marginal tokens or counts")

    unknown = {f"{kind}:uninterpreted" for kind in KINDS} | {"string:uninterpreted_text"}
    flags = unknown | {"string:Yes", "string:No"}
    categories = unknown | {f"string:{label}" for label in ("NGT", "IFG", "IGT", "diabetes")}
    storage = {f"{kind}:uninterpreted" for kind in KINDS - {"number"}} | {
        "numeric_cell_present",
        "string:uninterpreted",
    }
    margin(value["assignment_marginal"], {"Control", "Intervention"})
    margin(value["horizon_total_marginal"], flags)
    visits = value["visit_marginals"]
    labels = ("Baseline", "12 months", "24 months")
    if type(visits) is not dict or set(visits) != set(labels):
        raise ValueError("Public nominal visit labels differ")
    for index, label in enumerate(labels):
        visit = visits[label]
        if type(visit) is not dict or set(visit) != {
            "glycemia",
            "ada_diabetes",
            "incidence_flag",
            "medication_flags",
            "fasting_storage",
            "two_hour_storage",
        }:
            raise ValueError("Unapproved public visit fields")
        margin(visit["glycemia"], categories)
        for key in ("ada_diabetes", "incidence_flag"):
            margin(visit[key], flags)
        for key in ("fasting_storage", "two_hour_storage"):
            margin(visit[key], storage)
        if type(visit["medication_flags"]) is not list or len(visit["medication_flags"]) != (
            2 if index == 0 else 1
        ):
            raise ValueError("Public medication source fields differ")
        for counts in visit["medication_flags"]:
            margin(counts, flags)
    if visits["Baseline"]["incidence_flag"] != ({"absent:uninterpreted": n} if n else {}):
        raise ValueError("Horizon and suffix flags cannot be backdated to baseline")
    possible_category_pairs = definite_category_pairs = False
    for visit in visits.values():
        category_known = sum(visit["glycemia"].get(token, 0) for token in categories - unknown)
        flag_known = sum(visit["ada_diabetes"].get(token, 0) for token in flags - unknown)
        possible_category_pairs |= min(category_known, flag_known) > 0
        definite_category_pairs |= category_known + flag_known > n
    category_check = value["ada_category_and_flag_agree_where_both_interpretable"]
    if (not possible_category_pairs and category_check is not None) or (
        definite_category_pairs and category_check is None
    ):
        raise ValueError("Category consistency eligibility is misrepresented")
    first_visit = visits["12 months"]
    omission_evaluable = bool(
        first_visit["glycemia"].get("string:diabetes", 0)
        or first_visit["ada_diabetes"].get("string:Yes", 0)
    )
    if (
        value["later_two_hour_storage_absent_after_earlier_ada_positive_compatible"] is None
    ) == omission_evaluable:
        raise ValueError("Omission compatibility eligibility is misrepresented")
    algebra = value["incidence_flag_algebra"]
    if (
        type(algebra) is not dict
        or set(algebra) != ALGEBRA
        or any(type(count) is not int or not 0 <= count <= n for count in algebra.values())
    ):
        raise ValueError("Unapproved public flag algebra")
    first, second = (visits[label]["incidence_flag"].get("string:Yes", 0) for label in labels[1:])
    overlap = algebra["suffix_positive_overlap"]
    if overlap > min(first, second) or algebra["suffix_positive_union"] != first + second - overlap:
        raise ValueError("Public positive-flag algebra conservation failed")
    total = value["horizon_total_marginal"]
    flag_margins = [total, *(visits[label]["incidence_flag"] for label in labels[1:])]
    known = [counts.get("string:Yes", 0) + counts.get("string:No", 0) for counts in flag_margins]
    if not max(0, sum(known) - 2 * n) <= algebra["fully_interpretable_triples"] <= min(known):
        raise ValueError("Interpretable flag triples violate marginal intersection bounds")
    upper_bounds = {
        "total_negative_with_positive_suffix": min(
            total.get("string:No", 0), algebra["suffix_positive_union"]
        ),
        "total_positive_with_both_suffixes_negative": min(
            total.get("string:Yes", 0), *(v.get("string:No", 0) for v in flag_margins[1:])
        ),
        "unknown_total_with_positive_suffix": min(n - known[0], algebra["suffix_positive_union"]),
    }
    if any(algebra[key] > bound for key, bound in upper_bounds.items()):
        raise ValueError("Flag discordance exceeds its source marginal bounds")
    histogram = value["unlabeled_observation_pattern_cell_size_histogram"]
    if type(histogram) is not dict:
        raise ValueError("Unapproved public coverage histogram")
    weighted = 0
    for size, count in histogram.items():
        if (
            type(size) is not str
            or not size.isascii()
            or not size.isdecimal()
            or str(int(size)) != size
        ):
            raise ValueError("Coverage histogram may contain only unlabeled integer sizes")
        if not 1 <= int(size) <= n or type(count) is not int or not 1 <= count <= n:
            raise ValueError("Coverage histogram has invalid counts")
        weighted += int(size) * count
    if weighted != n:
        raise ValueError("Public coverage histogram conservation failed")


def _pin(root, spec, prefix):
    path = (root / spec[prefix + "_path"]).resolve()
    if (
        not path.is_relative_to(root.resolve())
        or coverage._digest(path) != spec[prefix + "_sha256"]
    ):
        raise ValueError("Source-native observation artifact pin mismatch")
    return path


def source_report(root: Path, protocol: dict, diagnostics: dict) -> dict:
    """Protocol-approved source aggregates only; no estimated clinical probabilities."""
    diagnostics = json.loads(json.dumps(diagnostics, allow_nan=False))
    _validate_diagnostics(diagnostics)
    return {
        "schema_version": 1,
        "report_id": REPORT_ID,
        "source_id": SOURCE,
        "source_doi": protocol["source_doi"],
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": coverage._digest(
            root / "docs/validation/kerala-observation-adapter-protocol-v1.json"
        ),
        "parent_representation_sha256": protocol["parent_representation_sha256"],
        "adapter_sha256": coverage._digest(root / "src/demeter/data/kerala_observations.py"),
        "raw_file_sha256": [item["sha256"] for item in protocol["raw_files"]],
        "chronology": protocol["chronology"],
        "interpretation": "Used-source stored observations and flag algebra; not biological transitions, first-onset intervals, clinical remission, sampling probabilities or independent validation.",
        "time_basis": "nominal_visit_index",
        "exact_elapsed_time_inferred": False,
        "diagnostics": diagnostics,
        "participant_keys_cluster_keys_assays_and_paths_exported": False,
        "labeled_multiwave_tuples_exported": False,
        "source_likelihood_computed": False,
        "source_observation_channel_estimated": False,
        "individual_deaths_or_contact_times_inferred": False,
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "independent_validation_allowed": False,
        "scientific_release_ready": False,
    }


def audit_kerala_observations(registry, root: Path, *, source_cache: Path | None = None) -> dict:
    """Verify offline pins; optional private raw replay must reproduce the frozen report.

    Default verification does not read participant values. With a cache, the
    existing source admission/headers/checksums are verified before selected cells
    are adapted in memory. Only the frozen public aggregates leave this function.
    """
    root = root.resolve()
    spec = registry.datasets[DATASET]
    coverage._gates({key: spec[key] for key in coverage.GATES})
    if (
        spec["model_role"] != "benchmark_only"
        or spec["source_id"] != SOURCE
        or spec["parameter_keys"] != []
    ):
        raise ValueError("Source-native observation registry boundary mismatch")
    protocol_path = _pin(root, spec, "protocol")
    report_path = _pin(root, spec, "report")
    adapter_path = _pin(root, spec, "adapter")
    if (
        protocol_path.relative_to(root).as_posix()
        != "docs/validation/kerala-observation-adapter-protocol-v1.json"
        or adapter_path.relative_to(root).as_posix() != "src/demeter/data/kerala_observations.py"
    ):
        raise ValueError("Source-native observation transform identity mismatch")
    protocol, report = json.loads(protocol_path.read_bytes()), json.loads(report_path.read_bytes())
    coverage._gates({key: protocol[key] for key in coverage.GATES})
    if (
        protocol["protocol_id"] != PROTOCOL_ID
        or protocol["source_id"] != SOURCE
        or protocol["source_doi"] != registry.sources[SOURCE].doi
        or protocol["parent_representation_sha256"]
        != registry.datasets["kerala_source_admission"]["representation_sha256"]
    ):
        raise ValueError("Source-native observation protocol boundary mismatch")
    receipts = json.loads(
        (root / "docs/validation/kerala-source-acquisition-receipts-v1.json").read_bytes()
    )
    expected_raw = [
        {key: item[key] for key in ("raw_filename", "bytes", "sha256")}
        for item in receipts["workbook_receipts"]
    ]
    if protocol["raw_files"] != expected_raw:
        raise ValueError("Source-native raw-file identity mismatch")
    admission_protocol = json.loads(
        (root / "docs/validation/kerala-joint-coverage-intake-protocol-v2.json").read_bytes()
    )
    for kind in ("primary", "secondary"):
        fields = protocol[f"selected_{kind}_fields"]
        allowed = admission_protocol[f"minimum_fields_{kind}"]
        if len(fields) != len(set(fields)) or not set(fields).issubset(allowed):
            raise ValueError("Source-native selected fields exceed admission")
    parent = verify_registered(
        registry, root, source_cache, replay_aggregates=source_cache is not None
    )
    if encoded(source_report(root, protocol, report["diagnostics"])) != report_path.read_bytes():
        raise ValueError("Source-native frozen report semantics differ")
    reproduced = None
    if source_cache is not None:
        rows = [
            coverage._selected_rows(
                source_cache / item["raw_filename"], protocol[f"selected_{kind}_fields"]
            )
            for item, kind in zip(protocol["raw_files"], ("primary", "secondary"), strict=True)
        ]
        subjects = build_source_observations(*rows)
        actual = source_report(root, protocol, public_diagnostics(subjects))
        if encoded(actual) != report_path.read_bytes():
            raise ValueError("Source-native raw replay differs from frozen report")
        reproduced = True
    return {
        "registered_artifacts_verified": parent["registered_artifacts_verified"],
        "raw_values_read": source_cache is not None,
        "source_aggregates_reproduced": reproduced,
        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "report": report,
        "source_likelihood_computed": False,
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
    }
