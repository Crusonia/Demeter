"""Frozen iPOP namespace-association audit, preserving the literal v1 result.

Only exact source keys form possible edges. A consistent observed bijection is
a conditional association hypothesis, not verified participant identity. This
pure API never acquires sources, exports a crosswalk, or selects a clinical fit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from demeter.analysis import ipop_preflight as v1

PROTOCOL_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs/validation/ipop-namespace-crosswalk-protocol-v2.json"
)
PROTOCOL_SHA256 = "531a521156f40dae687c903b7c902b59cb34ad24014e2957c55141fa923b1ba0"
FROZEN_CANONICAL_SHA256 = "38f7c06ad4f235c24399a221edf45a4d8d36a4aa51943199eab685328c38611b"
VALIDATION_TEMPLATE_SHA256 = "a413c7dcfd9c4dfe438997a96f96a6d95c5bdb2ca1797003146a8cc416f8a085"
ASSOCIATION_KINDS = (
    "missing_clinical_visit_or_subject_key",
    "no_exact_sample_key_match",
    "multiple_sample_rows_for_matching_key",
    "missing_subject_in_unique_sample_match",
    "clinical_namespace_multiple_partners",
    "metadata_namespace_multiple_partners",
    "mutually_degree_one_unique_sample_association",
)
DEGREE_KINDS = ("zero", "one", "multiple")
CANDIDATE_KINDS = ("one_one", "one_multiple", "multiple_one", "multiple_multiple")
FAILURE_STAGES = v1.FAILURE_STAGES | frozenset(("namespace_graph", "v1_preflight"))


def load_frozen_crosswalk_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Load only the exact committed, duplicate-key-free selection."""
    try:
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != PROTOCOL_SHA256:
            raise v1._FailedStage("frozen_contract")
        value = json.loads(data.decode("utf-8"), object_pairs_hook=v1._unique_json)
        _contract(value, False)
        return value
    except Exception:
        raise v1._FailedStage("frozen_contract") from None


def _contract(protocol: dict[str, Any], validation_only: bool) -> None:
    if type(validation_only) is not bool or type(protocol) is not dict:
        raise v1._FailedStage("frozen_contract")
    template = copy.deepcopy(protocol)
    if validation_only:
        for role in v1.SELECTED:
            for field in ("git_blob", "tree_size_bytes"):
                template["source_selection"][role].pop(field)
        expected = VALIDATION_TEMPLATE_SHA256
    else:
        expected = FROZEN_CANONICAL_SHA256
    if v1._canonical_sha256(template) != expected:
        raise v1._FailedStage("frozen_contract")
    if protocol["association_contract"]["clinical_row_partition_order"] != list(ASSOCIATION_KINDS):
        raise v1._FailedStage("frozen_contract")


def _namespace_summary(labels: set[str], partners: dict[str, set[str]]) -> dict[str, Any]:
    counts = Counter(
        "zero" if not partners.get(label) else "one" if len(partners[label]) == 1 else "multiple"
        for label in labels
    )
    return {
        "denominator_distinct_nonempty_source_subject_labels": len(labels),
        "observed_partner_degree": {kind: counts[kind] for kind in DEGREE_KINDS},
    }


def _summarize_namespace(
    clinical: tuple[v1._Clinical, ...], samples: tuple[v1._Sample, ...]
) -> dict[str, Any]:
    right: dict[str, list[v1._Sample]] = defaultdict(list)
    for sample in samples:
        if v1._key_kind(sample.sample) == "nonempty":
            right[sample.sample].append(sample)

    clinical_partners: dict[str, set[str]] = defaultdict(set)
    metadata_partners: dict[str, set[str]] = defaultdict(set)
    rows_with_edges = 0
    ambiguous_rows_with_edges = 0
    # All possible nonempty partners precede quarantine and assay/day filters.
    # Ambiguous sample keys supply edges without expanding observations.
    for row in clinical:
        if v1._key_kind(row.visit) != "nonempty" or v1._key_kind(row.subject) != "nonempty":
            continue
        matches = right.get(row.visit, ())
        possible = {
            sample.subject for sample in matches if v1._key_kind(sample.subject) == "nonempty"
        }
        if possible:
            rows_with_edges += 1
            ambiguous_rows_with_edges += len(matches) > 1
            clinical_partners[row.subject].update(possible)
            for subject in possible:
                metadata_partners[subject].add(row.subject)

    partition = Counter({kind: 0 for kind in ASSOCIATION_KINDS})
    combinations = Counter({kind: 0 for kind in CANDIDATE_KINDS})
    admitted: list[tuple[v1._Clinical, v1._Sample]] = []
    for row in clinical:
        if v1._key_kind(row.visit) != "nonempty" or v1._key_kind(row.subject) != "nonempty":
            kind = ASSOCIATION_KINDS[0]
        elif not right.get(row.visit):
            kind = ASSOCIATION_KINDS[1]
        elif len(right[row.visit]) != 1:
            kind = ASSOCIATION_KINDS[2]
        else:
            sample = right[row.visit][0]
            if v1._key_kind(sample.subject) != "nonempty":
                kind = ASSOCIATION_KINDS[3]
            else:
                clinical_multiple = len(clinical_partners[row.subject]) > 1
                metadata_multiple = len(metadata_partners[sample.subject]) > 1
                combinations[
                    ("multiple" if clinical_multiple else "one")
                    + "_"
                    + ("multiple" if metadata_multiple else "one")
                ] += 1
                if clinical_multiple:
                    kind = ASSOCIATION_KINDS[4]
                elif metadata_multiple:
                    kind = ASSOCIATION_KINDS[5]
                else:
                    kind = ASSOCIATION_KINDS[6]
                    admitted.append((row, sample))
        partition[kind] += 1

    clinical_labels = {row.subject for row in clinical if v1._key_kind(row.subject) == "nonempty"}
    metadata_labels = {row.subject for row in samples if v1._key_kind(row.subject) == "nonempty"}
    # This ephemeral assignment is only the declared coverage grouping. The
    # original clinical tokens, immutable rows, raw bytes and v1 report persist.
    grouped_clinical = tuple(
        v1._Clinical(row.visit, sample.subject, row.a1c, row.glu, row.context)
        for row, sample in admitted
    )
    coverage = v1._summarize(grouped_clinical, samples)
    result = {
        "namespace_consistency": {
            "clinical_namespace": _namespace_summary(clinical_labels, clinical_partners),
            "metadata_namespace": _namespace_summary(metadata_labels, metadata_partners),
            "distinct_possible_subject_pair_edges": sum(
                len(partners) for partners in clinical_partners.values()
            ),
            "denominator_source_clinical_rows": len(clinical),
            "clinical_rows_contributing_possible_edges": rows_with_edges,
            "clinical_rows_with_ambiguous_sample_keys_contributing_possible_edges": ambiguous_rows_with_edges,
        },
        "linkage": {
            "denominator_clinical_rows": len(clinical),
            "ordered_partition": {kind: partition[kind] for kind in ASSOCIATION_KINDS},
            "denominator_unique_sample_candidate_rows_with_both_subjects_nonempty": sum(
                combinations.values()
            ),
            "unique_sample_candidate_degree_combinations": {
                kind: combinations[kind] for kind in CANDIDATE_KINDS
            },
            "right_duplicate_key_support": v1._support(
                Counter({key: len(rows) for key, rows in right.items()})
            ),
            "many_to_many_materialization_performed": False,
            "iterative_edge_removal_performed": False,
            "lexical_subject_equality_bypass_performed": False,
        },
        "unambiguous_linked_coverage": coverage["unambiguous_linked_coverage"],
        "linked_context_comparison": coverage["context_coverage"]["linked_context_comparison"],
    }
    _reconcile_namespace(result, clinical_labels, metadata_labels)
    return result


def _reconcile_namespace(
    result: dict[str, Any], clinical_labels: set[str], metadata_labels: set[str]
) -> None:
    def integer(value: Any) -> int:
        if type(value) is not int or value < 0:
            raise v1._FailedStage("aggregate_reconciliation")
        return value

    def partition(value: dict[str, Any], keys: tuple[str, ...]) -> int:
        if set(value) != set(keys):
            raise v1._FailedStage("aggregate_reconciliation")
        return sum(integer(value[key]) for key in keys)

    graph = result["namespace_consistency"]
    degrees = []
    for name, labels in (
        ("clinical_namespace", clinical_labels),
        ("metadata_namespace", metadata_labels),
    ):
        node = graph[name]
        denominator = integer(node["denominator_distinct_nonempty_source_subject_labels"])
        if (
            denominator != len(labels)
            or partition(node["observed_partner_degree"], DEGREE_KINDS) != denominator
        ):
            raise v1._FailedStage("aggregate_reconciliation")
        degrees.append(node["observed_partner_degree"])
    edges = integer(graph["distinct_possible_subject_pair_edges"])
    for degree in degrees:
        positive = degree["one"] + degree["multiple"]
        if degree["one"] + 2 * degree["multiple"] > edges or ((positive == 0) != (edges == 0)):
            raise v1._FailedStage("aggregate_reconciliation")
    if edges > (degrees[0]["one"] + degrees[0]["multiple"]) * (
        degrees[1]["one"] + degrees[1]["multiple"]
    ):
        raise v1._FailedStage("aggregate_reconciliation")

    linkage = result["linkage"]
    n = integer(linkage["denominator_clinical_rows"])
    rows_with_edges = integer(graph["clinical_rows_contributing_possible_edges"])
    ambiguous_with_edges = integer(
        graph["clinical_rows_with_ambiguous_sample_keys_contributing_possible_edges"]
    )
    ordered = linkage["ordered_partition"]
    combinations = linkage["unique_sample_candidate_degree_combinations"]
    candidates = integer(
        linkage["denominator_unique_sample_candidate_rows_with_both_subjects_nonempty"]
    )
    if (
        integer(graph["denominator_source_clinical_rows"]) != n
        or partition(ordered, ASSOCIATION_KINDS) != n
        or partition(combinations, CANDIDATE_KINDS) != candidates
        or candidates != sum(ordered[kind] for kind in ASSOCIATION_KINDS[4:])
        or ordered[ASSOCIATION_KINDS[4]]
        != combinations["multiple_one"] + combinations["multiple_multiple"]
        or ordered[ASSOCIATION_KINDS[5]] != combinations["one_multiple"]
        or ordered[ASSOCIATION_KINDS[6]] != combinations["one_one"]
        or not 0 <= rows_with_edges <= n
        or rows_with_edges != candidates + ambiguous_with_edges
        or ambiguous_with_edges > ordered[ASSOCIATION_KINDS[2]]
        or ((rows_with_edges == 0) != (edges == 0))
        or result["unambiguous_linked_coverage"]["denominator_linked_clinical_rows"]
        != combinations["one_one"]
        or result["unambiguous_linked_coverage"]["total_distinct_unambiguous_linked_subject_labels"]
        > min(degrees[0]["one"], degrees[1]["one"])
        or result["linked_context_comparison"]["denominator_linked_rows"] != combinations["one_one"]
        or any(
            linkage[name] is not False
            for name in (
                "many_to_many_materialization_performed",
                "iterative_edge_removal_performed",
                "lexical_subject_equality_bypass_performed",
            )
        )
    ):
        raise v1._FailedStage("aggregate_reconciliation")

    def only_counts(value: Any) -> None:
        if type(value) is dict:
            for child in value.values():
                only_counts(child)
        elif type(value) is int:
            integer(value)
        elif type(value) is not bool:
            raise v1._FailedStage("aggregate_reconciliation")

    only_counts(result)


def preflight_crosswalk_bytes(
    clinical_bytes: bytes,
    sample_bytes: bytes,
    *,
    protocol: dict[str, Any],
    validation_only: bool = True,
) -> dict[str, Any]:
    """Publish only atomic aggregate results under the exact v2 selection.

    Receipt verification is the offline wrapper's responsibility. This pure
    function hashes complete byte inputs before parsing and embeds the complete
    unchanged pure v1 report, scoped separately from acquisition provenance.
    """
    execution_scope = (
        "synthetic_software_validation_only"
        if validation_only is True
        else "actual_source_intake_only"
        if validation_only is False
        else "invalid_execution_mode"
    )
    report: dict[str, Any] = {
        "schema_version": 1,
        "execution_scope": execution_scope,
        "validation_only": validation_only if type(validation_only) is bool else None,
        "source_audit": {
            "passed": False,
            "failure_stage": None,
            "frozen_protocol_sha256": PROTOCOL_SHA256,
        },
        "v1_result": None,
        "source_structure": None,
        "numeric_token_coverage": None,
        "namespace_consistency": None,
        "linkage": None,
        "unambiguous_linked_coverage": None,
        "context_coverage": None,
        "provenance": None,
        "clinical_fit_performed": False,
        "clinical_threshold_mapping_performed": False,
        "diagnosis_or_remission_inference_performed": False,
        "death_or_censoring_inference_performed": False,
        "engine_activation_allowed": False,
        "scientific_acceptance_changed": False,
    }
    stage = "frozen_contract"
    try:
        _contract(protocol, validation_only)
        literal_protocol = v1.load_frozen_protocol()
        if validation_only:
            for role in v1.SELECTED:
                for field in ("git_blob", "tree_size_bytes"):
                    literal_protocol["source_selection"][role][field] = protocol[
                        "source_selection"
                    ][role][field]
        stage = "v1_preflight"
        literal_result = v1.preflight_bytes(
            clinical_bytes, sample_bytes, protocol=literal_protocol, validation_only=validation_only
        )
        if literal_result["source_audit"]["passed"] is not True:
            raise v1._FailedStage(literal_result["source_audit"]["failure_stage"])
        stage = "source_structure"
        clinical = v1._parse_clinical(v1._records(clinical_bytes, v1.CLINICAL_HEADER, "\t"))
        samples = v1._parse_samples(v1._records(sample_bytes, v1.SAMPLE_HEADER, ","))
        stage = "namespace_graph"
        result = _summarize_namespace(clinical, samples)
        stage = "success_provenance"
        context = copy.deepcopy(literal_result["context_coverage"])
        context["linked_context_comparison"] = result.pop("linked_context_comparison")
        provenance = {
            "frozen_protocol_sha256": PROTOCOL_SHA256,
            "supplied_protocol_canonical_sha256": v1._canonical_sha256(protocol),
            "validation_semantics_sha256": VALIDATION_TEMPLATE_SHA256,
            "binding_v1_protocol_sha256": v1.PROTOCOL_SHA256,
            "producer_commit": v1.COMMIT,
            "source_bytes": copy.deepcopy(literal_result["provenance"]["source_bytes"]),
            "acquisition_performed": False,
            "acquisition_receipts_verified": False,
            "verification_scope": "complete selected byte identities and conditional namespace-association aggregates only",
            "coverage_grouping_namespace": "SampleInfo.SubjectID under the declared producer sample-association assumption",
            "coverage_group_assignment": "Ephemeral metadata-subject assignment solely for reuse of v1 coverage arithmetic; original clinical tokens, immutable rows and full v1 result unchanged",
            "graph_scope": "all possible nonempty subject partners from every exact sample match, including ambiguous right keys, before eligibility and quarantine",
            "participant_identity_verified": False,
            "namespace_consistency_scope": "observed available associations within pinned records; consistently wrong bijection remains possible",
            "units_rawness_and_specimen_clock_verified": False,
            "sampling_model_selected": False,
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "v1_implementation_sha256": literal_result["provenance"]["implementation_sha256"],
        }
        success = dict(report)
        success.update(result)
        success.update(
            v1_result=literal_result,
            source_structure=copy.deepcopy(literal_result["source_structure"]),
            numeric_token_coverage=copy.deepcopy(literal_result["numeric_token_coverage"]),
            context_coverage=context,
            provenance=provenance,
            source_audit={
                "passed": True,
                "failure_stage": None,
                "frozen_protocol_sha256": PROTOCOL_SHA256,
                "meaning": "source integrity and conditional namespace-association preservation only; no clinical acceptance",
            },
        )
        json.dumps(success, allow_nan=False)
        return success
    except Exception as exc:
        reason = str(exc) if isinstance(exc, v1._FailedStage) else stage
        report["source_audit"]["failure_stage"] = reason if reason in FAILURE_STAGES else stage
        return report
