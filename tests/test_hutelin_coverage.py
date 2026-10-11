import json
import csv
import io
import pytest
from demeter.data.hutelin_coverage import EXPECTED_HEADER, FIELDS, TIMES, coverage, coverage_csv
from demeter.data import hutelin_coverage
from pathlib import Path


def row(person="PRIVATE-ID", condition="mpf", time="0", value="123.987654"):
    return {"id": person, "condition": condition, "time": time, **dict.fromkeys(FIELDS, value)}


def test_accounting_retains_every_record_and_hides_private_values():
    records = [
        row(),
        row(),
        row(condition="upf"),
        row(person="", condition="UNKNOWN", time="nan", value="NA"),
    ]
    report = coverage(records)
    assert report["physical_rows"] == 4
    assert report["valid_key_rows"] == 3
    assert report["invalid_key_rows"] == 1
    assert report["extra_duplicate_rows"] == 1
    assert report["duplicate_key_count"] == 1
    assert report["paired_condition_participants"] == 1
    assert sum(report["nonexclusive_invalid_reason_counts"].values()) == 3
    encoded = json.dumps(report)
    assert "PRIVATE-ID" not in encoded and "123.987654" not in encoded and "UNKNOWN" not in encoded


def test_literal_missing_does_not_absorb_unclassified_values():
    report = coverage([row(value=v) for v in ["", "NA", "NaN", "Inf", "n/a", "7.0"]])
    for field in FIELDS:
        assert report["assay_token_accounting"][field] == dict(
            literal_missing=2, finite_numeric=1, unclassified=3
        )


def test_recorded_grid_completeness_separate_from_pair_and_duplicates():
    rows = [row(condition=c, time=str(t)) for c in ["mpf", "upf"] for t in TIMES]
    report = coverage(rows)
    assert report["paired_condition_participants"] == 1
    assert all(
        n == 2
        for group in report[
            "reference_grid_coverage_sessions_finite_without_duplicate_keys"
        ].values()
        for n in group.values()
    )
    report = coverage(rows + [row()])
    assert all(
        n == 1
        for group in report[
            "reference_grid_coverage_sessions_finite_without_duplicate_keys"
        ].values()
        for n in group.values()
    )


def test_reference_grids_remain_distinct_without_claiming_observation_clock():
    rows = [row(time=str(t)) for t in TIMES if t != 10]
    report = coverage(rows)
    groups = report["reference_grid_coverage_sessions_finite_without_duplicate_keys"]
    assert groups["code_suffix_grid"]["glucose"] == 0
    assert groups["published_postmeal_grid_with_unverified_source0_baseline"]["glucose"] == 1
    for time, fields in report["valid_key_assay_token_support"]["mpf"].items():
        for counts in fields.values():
            assert sum(counts.values()) == int(time != "10")


def test_unknown_times_remain_invalid_without_exporting_literal():
    report = coverage([row(time="98765"), row(time="1.5"), row(time="bad")])
    assert report["invalid_key_rows"] == 3
    assert report["nonexclusive_invalid_reason_counts"] == dict(unexpected_time=1, malformed_time=2)
    assert "98765" not in json.dumps(report)


def test_empty_input_has_zero_reconciled_counts():
    report = coverage([])
    assert report["physical_rows"] == 0
    assert report["paired_condition_participants"] == 0


def test_nonstandard_numeric_syntax_is_not_silently_normalized():
    report = coverage(
        [row(value="1_000", time="1_0"), row(value="<0.1"), row(value="0"), row(value="1e2")]
    )
    assert report["invalid_key_rows"] == 1
    assert report["assay_token_accounting"]["glucose"] == dict(
        literal_missing=0, finite_numeric=2, unclassified=2
    )


def synthetic_csv(records):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(EXPECTED_HEADER)
    for record in records:
        writer.writerow(
            [record.get(field, "NONSELECTED-PRIVATE-TEXT") for field in EXPECTED_HEADER]
        )
    return buffer.getvalue().encode()


def test_csv_projection_ignores_nonselected_fields_and_matches_hand_count():
    raw = synthetic_csv([row(), row(condition="upf", value="NA")])
    report = coverage_csv(raw)
    assert report["physical_rows"] == 2
    assert report["paired_condition_participants"] == 1
    assert report["assay_token_accounting"]["glucose"] == dict(
        literal_missing=1, finite_numeric=1, unclassified=0
    )
    assert "NONSELECTED-PRIVATE-TEXT" not in json.dumps(report)


@pytest.mark.parametrize(
    "raw",
    [
        b"wrong\n",
        b"\x00",
        b"\xff",
        b"",
        synthetic_csv([]) + b"short,row\n",
        synthetic_csv([]) + b"\n",
        synthetic_csv([row(person="embedded\nnewline")]),
    ],
)
def test_invalid_csv_framing_returns_no_partial_report(raw):
    with pytest.raises((ValueError, UnicodeDecodeError, csv.Error)):
        coverage_csv(raw)


def test_byte_and_record_limits_are_checked_without_silent_truncation():
    raw = synthetic_csv([row(), row(condition="upf")])
    with pytest.raises(ValueError, match="bytes"):
        coverage_csv(raw, max_bytes=10)
    with pytest.raises(ValueError, match="record limit"):
        coverage_csv(raw, max_rows=1)


def test_changed_protocol_fails_before_preflight_or_data_access(tmp_path, monkeypatch):
    protocol = tmp_path / "docs/validation/hutelin2026-blood-coverage-protocol-v1.json"
    protocol.parent.mkdir(parents=True)
    protocol.write_text("{}")

    def forbidden(*args):
        raise AssertionError("source guard invoked before protocol identity")

    monkeypatch.setattr(hutelin_coverage, "audit_hutelin_preflight", forbidden)
    with pytest.raises(ValueError, match="protocol differs"):
        hutelin_coverage.audit_hutelin_coverage(tmp_path / "absent", tmp_path)


def test_changed_archive_fails_before_participant_decoder(tmp_path, monkeypatch):
    (tmp_path / "data-original.zip").write_bytes(b"wrong source")
    monkeypatch.setattr(
        hutelin_coverage,
        "audit_hutelin_preflight",
        lambda *args: {
            "contract_sha256": "8d7caec48404816c0382db08052c5f5a4f55e252e5d0b686d8da7d899ab3d2bf"
        },
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("participant decoder invoked for changed source")

    monkeypatch.setattr(hutelin_coverage, "coverage_csv", forbidden)
    root = Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError, match="source differs"):
        hutelin_coverage.audit_hutelin_coverage(tmp_path, root)


def test_original_aggregate_receipt_reconciles_without_participant_intake():
    root = Path(__file__).resolve().parents[1]
    report = json.loads(
        (root / "docs/validation/hutelin2026-blood-coverage-result-v1.json").read_bytes()
    )
    assert report["physical_rows"] == report["valid_key_rows"] + report["invalid_key_rows"]
    assert report["valid_key_rows"] == report["unique_valid_keys"] + report["extra_duplicate_rows"]
    assert (
        report["participants_with_valid_keys"]
        == report["paired_condition_participants"] + report["single_condition_participants"]
    )
    assert (
        sum(sum(values.values()) for values in report["valid_key_time_support"].values())
        == report["valid_key_rows"]
    )
    for field, counts in report["assay_token_accounting"].items():
        assert sum(counts.values()) == report["physical_rows"]
        for condition, support in report["valid_key_assay_token_support"].items():
            for time, fields in support.items():
                assert (
                    sum(fields[field].values()) == report["valid_key_time_support"][condition][time]
                )
    assert report["protocol_sha256"] == hutelin_coverage.PROTOCOL_SHA256
    assert (
        report["runtime_source_sha256"]
        == hutelin_coverage.hashlib.sha256(Path(hutelin_coverage.__file__).read_bytes()).hexdigest()
    )
    assert report["participant_records_exported"] is False
    assert report["outcome_estimates"] is None
    assert report["clinical_parameters_admitted"] is False
