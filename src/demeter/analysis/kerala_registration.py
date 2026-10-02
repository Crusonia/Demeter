"""Bind the Kerala source appraisal to the evidence registry; replay counts only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from demeter.analysis import kerala_coverage as coverage

DATASET = "kerala_source_admission"
SOURCE = "kerala2018_public_trial_v3"


def _pinned(root: Path, spec: dict, prefix: str) -> Path:
    path = (root / spec[prefix + "_path"]).resolve()
    coverage._require(path.is_relative_to(root.resolve()), "registered artifact path escapes root")
    coverage._require(
        hashlib.sha256(path.read_bytes()).hexdigest() == spec[prefix + "_sha256"],
        "registered " + prefix + " checksum mismatch",
    )
    return path


def verify_registered(
    registry, root: Path, source_cache: Path | None = None, *, replay_aggregates: bool = False
) -> dict:
    """Verify immutable metadata offline; optional raw replay needs no author Git history.

    Replaying a frozen selected-field aggregate is distinct from first authorship.
    It cannot rewrite the report, establish clinical meaning or supply a new fit.
    Historical signed-query originals are optional and their absence is explicit.
    """
    root = root.resolve()
    spec = registry.datasets[DATASET]
    coverage._require(
        spec["model_role"] == "benchmark_only"
        and spec["source_id"] == SOURCE
        and spec["parameter_keys"] == [],
        "registered source observation scope mismatch",
    )
    coverage._gates({key: spec[key] for key in coverage.GATES})
    admission = _pinned(root, spec, "admission")
    coverage._require(
        admission.name == "kerala-source-admission-v2.json", "active admission version"
    )
    guard = coverage.verify_admission(root)
    receipts = json.loads(
        (root / "docs/validation/kerala-source-acquisition-receipts-v1.json").read_bytes()
    )
    selected = [
        (
            SOURCE,
            dict(
                receipts["metadata_receipt"],
                doi=receipts["release_metadata"]["doi"],
                raw_filename="figshare5661610-metadata.json",
            ),
        ),
        ("kerala2018_primary_publication", receipts["publication_receipt"]),
        ("kerala2013_trial_protocol", receipts["supporting_document_receipts"][0]),
        ("kerala2023_followup_protocol", receipts["supporting_document_receipts"][1]),
    ]
    coverage._require(
        set(spec["source_ids"]) == {key for key, _ in selected}, "registered source inventory"
    )
    for key, receipt in selected:
        registered = registry.sources[key]
        for field in ("url", "doi", "raw_filename", "sha256"):
            coverage._require(
                getattr(registered, field) == receipt[field], "registered source receipt mismatch"
            )
        coverage._require(
            registered.retrieved_at == coverage._time(receipt["retrieved_at_utc"]),
            "registered source chronology",
        )
    report = json.loads(_pinned(root, spec, "representation").read_bytes())
    coverage._require(
        report["report_id"] == "kerala-selected-source-representation-v2"
        and report["source_id"] == SOURCE,
        "registered representation identity",
    )
    coverage._require(
        report["admission_sha256"] == spec["admission_sha256"], "report admission identity"
    )
    coverage._gates(report["scientific_gates"])
    redaction = report["publication_redaction_protocol"]
    coverage._require(
        redaction["path"] == "docs/validation/kerala-longitudinal-output-redaction-protocol-v2.json"
        and coverage._digest(root / redaction["path"]) == redaction["sha256"],
        "publication redaction protocol checksum",
    )
    redaction_protocol = json.loads((root / redaction["path"]).read_bytes())
    coverage._gates(redaction_protocol["scientific_gates"])
    coverage._require(
        redaction_protocol["protocol_id"] == "kerala-longitudinal-output-redaction-protocol-v2"
        and redaction_protocol["source_id"] == SOURCE
        and redaction_protocol["parent_representation"]
        == report["run_chronology"]["prior_published_representation"],
        "publication redaction parent identity",
    )
    withdrawal = json.loads(_pinned(root, spec, "withdrawal_receipt").read_bytes())
    coverage._gates(withdrawal["scientific_gates"])
    coverage._require(
        withdrawal["artifact_id"] == "kerala-selected-source-representation-v1-withdrawal-receipt"
        and withdrawal["source_id"] == SOURCE
        and withdrawal["redaction_protocol"] == redaction
        and withdrawal["withdrawn_original"] == redaction_protocol["parent_representation"]
        and withdrawal["replacement_path"] == spec["representation_path"]
        and withdrawal["replacement_sha256"] == spec["representation_sha256"]
        and withdrawal["existing_git_history_remains_accessible"] is True
        and withdrawal["git_history_rewritten"] is False
        and withdrawal["labeled_multiwave_tuples_in_current_artifact"] is False,
        "publication withdrawal identity",
    )
    _verify_public_histories(report["aggregate_representation"], envelope=withdrawal)
    _verify_public_histories(report["aggregate_representation"], envelope=report)
    expected_code = {
        "module": "src/demeter/analysis/kerala_coverage.py",
        "script": "scripts/verify_kerala_source_coverage.py",
    }
    coverage._require(
        set(report["execution_code_pins"]) == set(expected_code), "execution code inventory"
    )
    for key, expected_path in expected_code.items():
        pin = report["execution_code_pins"][key]
        coverage._require(pin["path"] == expected_path, "execution code path")
        coverage._require(
            coverage._digest(root / expected_path) == pin["sha256"], "execution code checksum"
        )
    for key in (
        "record_rows_collapsed",
        "raw_numeric_code_meanings_inferred",
        "participant_records_exported",
        "joint_clinical_category_paths_verified",
        "death_loss_joint_allocation_verified",
        "source_specific_observation_model_fitted",
    ):
        coverage._require(report[key] is False, "registered representation scientific boundary")
    expected_files = [
        {key: receipt[key] for key in ("file_id", "raw_filename", "bytes", "sha256", "md5")}
        for receipt in receipts["workbook_receipts"]
    ]
    coverage._require(
        report["source_files"] == expected_files, "registered representation source pins"
    )
    headers_reproduced = aggregates_reproduced = historical_projection = None
    if source_cache is not None:
        source_cache = source_cache.resolve()
        headers = json.loads((root / "docs/validation/kerala-source-headers-v1.json").read_bytes())
        header_by_id = {item["file_id"]: item for item in headers}
        for receipt in receipts["workbook_receipts"]:
            header = header_by_id[receipt["file_id"]]
            raw = (source_cache / receipt["raw_filename"]).resolve()
            coverage._require(raw.is_relative_to(source_cache), "source path escapes cache")
            coverage._require(
                raw.stat().st_size == receipt["bytes"]
                and coverage._digest(raw) == receipt["sha256"]
                and hashlib.md5(raw.read_bytes()).hexdigest() == receipt["md5"],
                "public source cache pins mismatch",
            )
            coverage._require(
                coverage.read_headers_only(raw) == header["headers"],
                "public source headers mismatch",
            )
        headers_reproduced = True
        translation = json.loads(
            (root / "docs/validation/kerala-source-artifact-translation-v1.json").read_bytes()
        )
        # Original private acquisition signatures are not required to replay public workbooks.
        original = source_cache / translation["original_coverage"]["original_path"]
        if original.is_file():
            coverage.verify_admission(root, source_cache)
            historical_projection = True
        if replay_aggregates:
            protocol = json.loads(
                (
                    root / "docs/validation/kerala-joint-coverage-intake-protocol-v2.json"
                ).read_bytes()
            )
            p_fields, s_fields = (
                protocol["minimum_fields_primary"],
                protocol["minimum_fields_secondary"],
            )
            files = receipts["workbook_receipts"]
            actual = coverage.aggregate_representation(
                coverage._selected_rows(source_cache / files[0]["raw_filename"], p_fields),
                coverage._selected_rows(source_cache / files[1]["raw_filename"], s_fields),
                p_fields,
                s_fields,
            )
            _verify_public_histories(json.loads(json.dumps(actual)))
            coverage._require(
                json.loads(json.dumps(actual)) == report["aggregate_representation"],
                "registered aggregate replay mismatch",
            )
            aggregates_reproduced = True
    else:
        coverage._require(
            not replay_aggregates, "aggregate replay requires exact public source cache"
        )
    return {
        "registered_artifacts_verified": True,
        "source_id": SOURCE,
        "authored_admission": guard,
        "public_workbook_headers_reproduced": headers_reproduced,
        "historical_redirect_projection_reproduced": historical_projection,
        "registered_aggregate_reproduction": aggregates_reproduced,
        "participant_records_exported": False,
        "scientific_gates": {key: False for key in sorted(coverage.GATES)},
    }


def _verify_public_histories(aggregate: dict, *, envelope: dict | None = None) -> None:
    """Keep labeled multiwave paths private, including non-singleton cells."""
    forbidden = {
        "aggregate_paths",
        "assigned_arm_label",
        "nominal_visit_source_labels",
        "total_recorded_diagnosis_flag",
    }

    def inspect(value):
        if isinstance(value, dict):
            coverage._require(not (set(value) & forbidden), "labeled multiwave export prohibited")
            for nested in value.values():
                inspect(nested)
        elif isinstance(value, list):
            for nested in value:
                inspect(nested)

    inspect(aggregate if envelope is None else envelope)
    history = aggregate["source_defined_nominal_visit_label_histories"]
    allowed = {
        "nominal_visit_labels",
        "retained_internal_typed_keys",
        "included_typed_keys",
        "excluded_key_reason_counts",
        "distinct_unlabeled_history_cells",
        "unlabeled_history_cell_size_histogram",
        "labeled_multiwave_tuples_exported",
        "interpretation",
    }
    coverage._require(set(history) == allowed, "public history fields mismatch")
    coverage._require(
        history["nominal_visit_labels"] == ["Baseline", "12 months", "24 months"],
        "public nominal visit labels mismatch",
    )
    coverage._require(isinstance(history["interpretation"], str), "history interpretation shape")
    coverage._require(
        history["labeled_multiwave_tuples_exported"] is False, "labeled history export"
    )
    histogram = history["unlabeled_history_cell_size_histogram"]
    coverage._require(isinstance(histogram, dict), "history histogram shape")
    for size, frequency in histogram.items():
        coverage._require(
            isinstance(size, str)
            and size.isdecimal()
            and str(int(size)) == size
            and int(size) > 0
            and type(frequency) is int
            and frequency > 0,
            "history histogram count bounds",
        )
    for name in (
        "included_typed_keys",
        "retained_internal_typed_keys",
        "distinct_unlabeled_history_cells",
    ):
        coverage._require(type(history[name]) is int and history[name] >= 0, "history total bounds")
    exclusions = history["excluded_key_reason_counts"]
    coverage._require(isinstance(exclusions, dict), "history exclusion shape")
    coverage._require(
        all(type(value) is int and value >= 0 for value in exclusions.values()),
        "history exclusion bounds",
    )
    coverage._require(
        sum(histogram.values()) == history["distinct_unlabeled_history_cells"],
        "history cell conservation",
    )
    coverage._require(
        sum(int(size) * frequency for size, frequency in histogram.items())
        == history["included_typed_keys"],
        "history people conservation",
    )
    coverage._require(
        history["included_typed_keys"] + sum(exclusions.values())
        == history["retained_internal_typed_keys"],
        "history inclusion conservation",
    )
