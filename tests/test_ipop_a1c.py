"""Synthetic selected-source fixtures only; never inspect real participant files."""

import copy
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from demeter.analysis import ipop_a1c as fit
from demeter.analysis import ipop_crosswalk as v2
from demeter.analysis import ipop_preflight as v1
from demeter.schema import EvidenceRegistry

PROTOCOL = fit.load_protocol()
PRIVATE = "PRIVATE_SYNTHETIC_LABEL"


def _encode(header, rows, delimiter):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode()


def _sources(records, extra_samples=()):
    clinical, samples = [], []
    for index, (subject, day, assay) in enumerate(records):
        values = {key: PRIVATE + "_OPAQUE" for key in v1.CLINICAL_HEADER}
        values.update(
            VisitID=f"VISIT_{index}",
            SubjectID="CLINICAL_" + subject,
            A1C=assay,
            GLU="UNKNOWN",
            CL4=PRIVATE,
        )
        clinical.append([values[key] for key in v1.CLINICAL_HEADER])
        samples.append([subject, f"VISIT_{index}", day, PRIVATE])
    samples.extend(extra_samples)
    cbytes, sbytes = (
        _encode(v1.CLINICAL_HEADER, clinical, "\t"),
        _encode(v1.SAMPLE_HEADER, samples, ","),
    )
    protocol = v2.load_frozen_crosswalk_protocol()
    for role, data in (("clinical", cbytes), ("sample_info", sbytes)):
        protocol["source_selection"][role].update(
            tree_size_bytes=len(data),
            git_blob=hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
        )
    return cbytes, sbytes, protocol


def _prepare(records, extra_samples=()):
    clinical, samples, crosswalk = _sources(records, extra_samples)
    return fit._prepare(
        clinical, samples, PROTOCOL, validation_only=True, crosswalk_protocol=crosswalk
    )


def _label(partition):
    return next(
        PRIVATE + str(i)
        for i in range(1000)
        if fit._partition(PRIVATE + str(i), PROTOCOL) == partition
    )


def test_frozen_contract_rejects_bytes_and_semantic_edits(tmp_path):
    raw = Path(fit.PROTOCOL_PATH).read_bytes()
    edited = tmp_path / "changed.json"
    edited.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="frozen_contract"):
        fit.load_protocol(edited)
    for section, field, value in (
        ("measurement", "thresholds", [5.6, 6.5]),
        ("allocation", "salt", "different"),
        ("numerics", "rate_cap_per_source_day", 2),
        ("activation", "engine_activation_allowed", True),
    ):
        protocol = copy.deepcopy(PROTOCOL)
        protocol[section][field] = value
        with pytest.raises(ValueError, match="frozen_contract"):
            fit._contract(protocol)


def test_exact_decimal_thresholds_no_rounding_and_fractional_elapsed_days():
    label = _label("calibration")
    paths, coverage, _ = _prepare(
        [
            (label, "1000.00", "5.6999999999999999999999"),
            (label, "1000.25", "5.7"),
            (label, "1000.5", "6.4999999999999999999"),
            (label, "1001.75", "6.5"),
        ]
    )
    path = paths["calibration"][0]
    assert path.days == (0.0, 0.25, 0.5, 1.75)
    assert path.bands == (0, 1, 1, 2)
    assert coverage["eligible_band_counts"] == [1, 2, 1]
    assert PRIVATE not in json.dumps(coverage)


def test_source_origin_subtracted_before_float_and_originals_preserved():
    label = _label("calibration")
    paths, coverage, _ = _prepare(
        [
            (label, "10000000000000000000000000000000000000", "5"),
            (label, "10000000000000000000000000000000000000.25", "6"),
        ]
    )
    assert paths["calibration"][0].days == (0.0, 0.25)
    assert coverage["denominator_admitted_rows"] == 2


def test_conversion_loss_quarantines_whole_label_without_merging_days():
    label = _label("calibration")
    paths, coverage, _ = _prepare(
        [
            (label, "0", "5"),
            (label, "10000000000000000000", "6"),
            (label, "10000000000000000001", "7"),
        ]
    )
    assert paths["calibration"] == ()
    assert (
        coverage["partitions"]["calibration"]["label_partition"]["coordinate_conversion_loss"] == 1
    )
    assert coverage["eligible_band_counts"] == [1, 1, 1]


def test_decimal_overflow_quarantines_only_the_unrepresentable_label():
    bad = _label("calibration")
    good = _label("evaluation")
    paths, coverage, _ = _prepare(
        [(bad, "-2e1000000", "5"), (bad, "-1e1000000", "6"), (good, "0", "5"), (good, "1", "6")]
    )
    assert paths["calibration"] == ()
    assert len(paths["evaluation"]) == 1
    assert (
        coverage["partitions"]["calibration"]["label_partition"]["coordinate_conversion_loss"] == 1
    )
    assert coverage["denominator_admitted_rows"] == 4


@pytest.mark.parametrize("assays", [("5", "5"), ("5", "7")])
def test_equal_time_quarantines_label_including_identical_bands(assays):
    label = _label("calibration")
    paths, coverage, _ = _prepare(
        [(label, "1.0", assays[0]), (label, "1.00", assays[1]), (label, "2", "6")]
    )
    assert paths["calibration"] == ()
    assert coverage["partitions"]["calibration"]["label_partition"]["repeated_eligible_time"] == 1
    assert coverage["denominator_admitted_rows"] == 3


def test_partition_before_eligibility_unknowns_preserved_no_imputation():
    calibration, evaluation = _label("calibration"), _label("evaluation")
    paths, coverage, _ = _prepare(
        [
            (calibration, "1", "5"),
            (calibration, "2", "NA"),
            (calibration, "3", "-1"),
            (calibration, "bad", "6"),
            (evaluation, "1", "NaN"),
            (evaluation, "2", ""),
        ]
    )
    assert len(paths["calibration"]) == 1
    assert paths["evaluation"] == ()
    assert coverage["admitted_row_partition"] == {
        "unusable_day": 1,
        "unavailable_assay": 3,
        "outside_percent_range": 1,
        "eligible_assay_day": 1,
    }
    assert coverage["partitions"]["evaluation"]["admitted_labels"] == 1
    assert coverage["partitions"]["evaluation"]["label_partition"]["no_eligible_observation"] == 1
    assert sum(coverage["admitted_assay_token_categories"].values()) == 6


def test_full_ambiguous_graph_before_assay_filter_prevents_false_bijection():
    label = _label("calibration")
    other = PRIVATE + "OTHER"
    paths, coverage, _ = _prepare(
        [(label, "1", "5"), (label, "2", "NA")], [[other, "VISIT_1", "2", PRIVATE]]
    )
    assert paths["calibration"] == ()
    assert coverage["denominator_admitted_rows"] == 0
    assert (
        coverage["full_source_linkage"]["ordered_partition"]["clinical_namespace_multiple_partners"]
        == 1
    )
    assert (
        coverage["full_source_linkage"]["ordered_partition"][
            "multiple_sample_rows_for_matching_key"
        ]
        == 1
    )


@pytest.mark.parametrize("mode", [False, None, 1, "false"])
def test_synthetic_bytes_cannot_be_promoted_or_execution_mode_coerced(mode):
    clinical, samples, protocol = _sources([(_label("calibration"), "1", "5")])
    report = fit.analyze_bytes(
        clinical, samples, protocol=PROTOCOL, crosswalk_protocol=protocol, validation_only=mode
    )
    assert not report["analysis_completed"]
    assert report["selection"] is None
    assert PRIVATE not in json.dumps(report)
    assert report["engine_activation_allowed"] is False


def test_empty_split_retained_not_reassigned_to_obtain_a_fit():
    clinical, samples, protocol = _sources(
        [(_label("calibration"), "1", "5"), (_label("calibration"), "2", "6")]
    )
    report = fit.analyze_bytes(clinical, samples, protocol=PROTOCOL, crosswalk_protocol=protocol)
    assert report["failure_stage"] == "empty_calibration_or_evaluation_partition"
    assert report["models"] is None


def test_invalid_identity_stops_before_any_source_parser(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unverified source must never reach participant parsing")

    monkeypatch.setattr(v1, "_records", forbidden)
    report = fit.analyze_bytes(b"bad", b"bad", protocol=PROTOCOL, validation_only=False)
    assert not report["analysis_completed"]
    assert report["failure_stage"] == "source_selection"


def test_frozen_numerical_settings_and_units():
    for structure, count in (("adjacent", 4), ("unrestricted", 6)):
        settings = fit.settings_for(PROTOCOL, structure)
        assert len(settings.initial_rates) == 6
        assert len(settings.rate_upper_bounds) == count
        assert settings.rate_upper_bounds == (1.0,) * count
        assert settings.day_scale == 100
    assert PROTOCOL["time_and_paths"]["unit"] == "source_day"
    assert PROTOCOL["joint_uncertainty"]["bootstrap_replicates"] == 200


def test_wrapper_requires_receipts_and_preserves_sanitized_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "demeter.data.ipop.load_sources",
        lambda *args: {
            "passed": False,
            "receipt_saved": False,
            "provenance": {"failure": "constant"},
        },
    )
    report = fit.analyze_cache(tmp_path)
    assert report["failure_stage"] == "acquisition_receipts_or_cached_bytes"
    assert report["acquisition_audit"]["passed"] is False
    assert report["selection"] is None


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d.update(protocol_sha256="0" * 64),
        lambda d: d.update(engine_activation_allowed=True),
        lambda d: d.update(source_ids=["unverified"]),
        lambda d: d.update(model_role="health_model"),
        lambda d: d["observation_parameters"]["lower_band_cutoff"].update(value=5.6),
        lambda d: d["observation_parameters"]["upper_band_cutoff"].update(unit="fraction"),
        lambda d: d["working_rate_parameters"].update(value=[1, 2, 3, 4]),
    ],
)
def test_registry_semantic_drift_stops_before_cache_access(edit, monkeypatch, tmp_path):
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    edit(registry.datasets["ipop_a1c_working_fit"])
    monkeypatch.setattr(EvidenceRegistry, "from_yaml", lambda *args: registry)

    def forbidden(*args):
        pytest.fail("Registry drift must precede source cache access")

    monkeypatch.setattr("demeter.data.ipop.load_sources", forbidden)
    with pytest.raises(ValueError, match="registry_contract"):
        fit.analyze_cache(tmp_path)


def test_registry_complete_source_identity_cannot_drift():
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    registry.sources["ipop2022_clinical_tests"].sha256 = "0" * 64
    with pytest.raises(ValueError, match="registry_contract"):
        fit._registry_contract(registry, PROTOCOL, Path.cwd())


def test_numerical_amendment_is_exactly_pinned_before_fitting(tmp_path):
    policy = fit.load_numerical_protocol()
    assert policy["parent_protocol_sha256"] == fit.PROTOCOL_SHA256
    edited = tmp_path / "edited-policy.json"
    edited.write_bytes(Path(fit.NUMERICAL_PROTOCOL_PATH).read_bytes() + b" ")
    with pytest.raises(ValueError, match="frozen_numerical_contract"):
        fit.load_numerical_protocol(edited)
