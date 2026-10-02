from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kerala_admission_prepared", ROOT / "src/demeter/analysis/kerala_coverage.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
verify_admission = MODULE.verify_admission
read_headers_only = MODULE.read_headers_only


def test_raw_code_visit_labels_preserved_but_private_text_not_released():
    for value in ("Baseline", "12 months", "24 months"):
        assert MODULE._safe_code("string", value) == "string:" + value
    assert MODULE._safe_code("string", "private-household-text") == "string:uninterpreted_text"


def test_typed_keys_are_not_coerced_or_silently_collapsed():
    rows = [
        {"participant_id": ("number", "1")},
        {"participant_id": ("string", "1")},
        {"participant_id": ("string", "1")},
        {"participant_id": ("error", "#N/A")},
    ]
    grouped, missing = MODULE._group_rows(rows)
    assert len(grouped) == 2
    assert len(grouped[("string", "1")]) == 2
    assert missing == 1


def test_literal_source_histories_retain_missing_and_separate_diagnosis():
    protocol = json.loads(
        (ROOT / "docs/validation/kerala-joint-coverage-intake-protocol-v2.json").read_text()
    )
    pf, sf = protocol["minimum_fields_primary"], protocol["minimum_fields_secondary"]
    primary = {key: ("absent", None) for key in pf}
    primary.update(
        participant_id=("string", "private-id"),
        timepoint=("string", "Baseline"),
        arms0=("string", "Control"),
        cluster0=("string", "private-cluster"),
        tot_diab_incidence=("string", "Yes"),
    )
    secondary = []
    for visit, label in zip(
        ("Baseline", "12 months", "24 months"),
        (("string", "IGT"), ("string", "NGT"), ("absent", None)),
        strict=True,
    ):
        row = {key: ("absent", None) for key in sf}
        row.update(
            participant_id=("string", "private-id"),
            timepoint=("string", visit),
            glycemiaADA=label,
            arms=("string", "Control"),
            cluster=("string", "private-cluster"),
        )
        secondary.append(row)
    result = MODULE.aggregate_representation([primary], secondary, pf, sf)
    history = result["source_defined_nominal_visit_label_histories"]
    assert history["included_typed_keys"] == 1
    assert history["aggregate_paths"][0]["nominal_visit_source_labels"] == [
        "string:IGT",
        "string:NGT",
        "absent",
    ]
    assert history["aggregate_paths"][0]["total_recorded_diagnosis_flag"] == "string:Yes"
    assert "private-id" not in json.dumps(result)
    assert result["secondary"]["distinct_timepoint_cardinality_per_key"] == {3: 1}
    secondary[1]["arms"] = ("string", "Intervention")
    drift = MODULE.aggregate_representation([primary], secondary, pf, sf)
    assert drift["source_defined_nominal_visit_label_histories"]["included_typed_keys"] == 0
    assert drift["source_defined_nominal_visit_label_histories"]["excluded_key_reason_counts"] == {
        "linked_assignment_unverified_or_drifted": 1
    }
    assert drift["linked_long_assignment_consistency"]["arms"]["exact_typed_disagreements"] == 1


def test_unsupported_keys_do_not_create_valid_timepoint_pairs():
    protocol = json.loads(
        (ROOT / "docs/validation/kerala-joint-coverage-intake-protocol-v2.json").read_text()
    )
    pf, sf = protocol["minimum_fields_primary"], protocol["minimum_fields_secondary"]
    row = {key: ("absent", None) for key in pf}
    row.update(participant_id=("error", "#N/A"), timepoint=("string", "Baseline"))
    result = MODULE.aggregate_representation([row, row.copy()], [], pf, sf)
    assert result["primary"]["distinct_key_raw_timepoint_pairs"] == 0
    assert result["primary"]["repeated_typed_key_timepoint_pairs"] == 0


@pytest.fixture
def package(tmp_path):
    root = tmp_path / "package"
    target = root / "docs/validation"
    target.mkdir(parents=True)
    for path in (ROOT / "docs/validation").glob("kerala-*.json"):
        shutil.copy2(path, target / path.name)
    return root


def mutate(root, name, callback):
    path = root / "docs/validation" / name
    obj = json.loads(path.read_text())
    callback(obj)
    path.write_text(json.dumps(obj), encoding="utf-8")
    coverage_path = root / "docs/validation/kerala-clinical-contract-schema-coverage-v1.json"
    coverage = json.loads(coverage_path.read_text())
    if name == "kerala-source-acquisition-receipts-v1.json":
        coverage["actual_source_receipts"] = obj["workbook_receipts"]
        coverage["publication_receipt"] = obj["publication_receipt"]
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
    elif name == "kerala-source-headers-v1.json":
        coverage["header_manifest"]["bytes"] = path.stat().st_size
        coverage["header_manifest"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
    elif name == "kerala-joint-coverage-intake-protocol-v2.json":
        translation_path = root / "docs/validation/kerala-source-artifact-translation-v1.json"
        translation = json.loads(translation_path.read_text())
        translation["frozen_protocol_v2"]["bytes"] = path.stat().st_size
        translation["frozen_protocol_v2"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        translation_path.write_text(json.dumps(translation), encoding="utf-8")
    manifest = root / "docs/validation/kerala-source-admission-v2.json"
    package = json.loads(manifest.read_text())
    for item in package["artifacts"]:
        artifact = root / item["path"]
        item["bytes"] = artifact.stat().st_size
        item["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(package), encoding="utf-8")


def test_offline_scope_remains_unresolved():
    result = verify_admission(ROOT)
    assert result["artifact_pins_verified"] is True
    assert result["participant_values_inspected"] is False
    assert result["joint_person_wave_coverage_verified"] is False
    assert result["source_code_semantics_verified"] is False
    assert all(result[key] is False for key in MODULE.GATES)


def test_artifact_corruption_fails(package):
    path = package / "docs/validation/kerala-source-headers-v1.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="byte size"):
        verify_admission(package)


def test_artifact_path_escape_fails(package):
    path = package / "docs/validation/kerala-source-admission-v2.json"
    obj = json.loads(path.read_text())
    obj["artifacts"][0]["path"] = "../outside.json"
    path.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="escapes"):
        verify_admission(package)


@pytest.mark.parametrize(
    "gates",
    [
        {},
        {"clinical_fit_allowed": False},
        {key: False for key in MODULE.GATES} | {"extra": False},
        {key: False for key in MODULE.GATES} | {"clinical_fit_allowed": True},
        {key: False for key in MODULE.GATES} | {"clinical_fit_allowed": 0},
        {key: False for key in MODULE.GATES} | {"clinical_fit_allowed": "false"},
    ],
)
def test_gate_drift_after_repin_fails(package, gates):
    mutate(
        package,
        "kerala-source-appraisal-amendment-v1.json",
        lambda obj: obj.update(scientific_gates=gates),
    )
    with pytest.raises(ValueError, match="scientific gates"):
        verify_admission(package)


def test_after_values_protocol_cannot_be_promoted(package):
    mutate(
        package,
        "kerala-joint-coverage-intake-protocol-v2.json",
        lambda obj: obj["chronology"].update(participant_values_inspected=True),
    )
    with pytest.raises(ValueError, match="before values"):
        verify_admission(package)


def test_unknown_selected_field_fails(package):
    mutate(
        package,
        "kerala-joint-coverage-intake-protocol-v2.json",
        lambda obj: obj["minimum_fields_primary"].append("invented_status"),
    )
    with pytest.raises(ValueError, match="selected fields"):
        verify_admission(package)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("md5", "0" * 32, "MD5"),
        ("bytes", 1, "size"),
        ("source_doi", "10.6084/m9.figshare.5661610.v2", "version DOI"),
        ("final_url", "https://example.org/file?X-Amz-Signature=secret", "query"),
        ("raw_filename", "../escape.xlsx", "file name"),
    ],
)
def test_receipt_drift_after_repin_fails(package, field, value, match):
    mutate(
        package,
        "kerala-source-acquisition-receipts-v1.json",
        lambda obj: obj["workbook_receipts"][0].update({field: value}),
    )
    with pytest.raises(ValueError, match=match):
        verify_admission(package)


def test_direct_identifier_field_stops_admission(package):
    mutate(
        package,
        "kerala-source-headers-v1.json",
        lambda obj: obj[0]["headers"][0].update(label="email_address"),
    )
    with pytest.raises(ValueError, match="direct identifier"):
        verify_admission(package)


def test_nonheader_locator_fails(package):
    mutate(
        package,
        "kerala-source-headers-v1.json",
        lambda obj: obj[0]["headers"][0].update(column="A3"),
    )
    with pytest.raises(ValueError, match="nonheader locator"):
        verify_admission(package)


def test_immutable_prior_protocol_cannot_be_rewritten(package):
    mutate(
        package,
        "kerala-joint-coverage-intake-protocol-v1.json",
        lambda obj: obj.update(conditional_estimand="silently changed"),
    )
    with pytest.raises(ValueError, match="prior protocol bind"):
        verify_admission(package)


def test_raw_scope_pins_bound_to_receipts_after_reseal(package):
    mutate(
        package,
        "kerala-joint-coverage-intake-protocol-v2.json",
        lambda obj: obj["source_scope"]["raw_files"][0].update(sha256="0" * 64),
    )
    with pytest.raises(ValueError, match="raw file pins"):
        verify_admission(package)


def test_original_coverage_pin_bound_through_translation(package):
    mutate(
        package,
        "kerala-joint-coverage-intake-protocol-v2.json",
        lambda obj: obj["source_scope"]["contract_coverage"].update(bytes=1),
    )
    with pytest.raises(ValueError, match="original contract coverage bind"):
        verify_admission(package)


def test_snapshot_arithmetic_failure_preserved(package):
    mutate(
        package,
        "kerala-source-followup-snapshot-amendment-v1.json",
        lambda obj: obj["published_snapshots"]["intervention"]["24_month"].update(other_reasons=3),
    )
    with pytest.raises(ValueError, match="snapshot reason arithmetic"):
        verify_admission(package)


def test_admission_parent_v1_immutable(package):
    path = package / "docs/validation/kerala-source-admission-v1.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="parent bind"):
        verify_admission(package)


def workbook(path, header="participant_id", extra=None):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(path, "w") as book:
        book.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{ns}"><sheets><sheet name="Sheet 1" sheetId="1"/></sheets></workbook>',
        )
        book.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="{ns}"><si><t>{header}</t></si><si><t>PRIVATE_RECORD_SECRET</t></si></sst>',
        )
        book.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{ns}"><sheetData><row r="2"><c r="A2" t="s"><v>0</v></c></row><row r="3"><c r="A3" t="s"><v>1</v></c></row></sheetData></worksheet>',
        )
        if extra:
            book.writestr(extra, "untrusted content")


def test_header_reader_never_returns_record_values(tmp_path):
    path = tmp_path / "synthetic.xlsx"
    workbook(path)
    result = read_headers_only(path)
    assert result == [{"column": "A2", "label": "participant_id"}]
    assert "PRIVATE_RECORD_SECRET" not in json.dumps(result)


def test_header_reader_stops_before_malformed_record_xml(tmp_path):
    path = tmp_path / "synthetic-malformed-record.xlsx"
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(path, "w") as book:
        book.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{ns}"><sheets><sheet name="Sheet 1" sheetId="1"/></sheets></workbook>',
        )
        book.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="{ns}"><si><t>participant_id</t></si><si><malformed></sst>',
        )
        book.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{ns}"><sheetData><row r="2"><c r="A2" t="s"><v>0</v></c></row><row r="3"><malformed></worksheet>',
        )
    assert read_headers_only(path) == [{"column": "A2", "label": "participant_id"}]


@pytest.mark.parametrize(
    "extra", ["xl/vbaProject.bin", "xl/externalLinks/externalLink1.xml", "xl/connections.xml"]
)
def test_active_workbook_parts_rejected(tmp_path, extra):
    path = tmp_path / "synthetic.xlsx"
    workbook(path, extra=extra)
    with pytest.raises(ValueError, match="active or external"):
        read_headers_only(path)


def test_header_reader_direct_identifiers_rejected(tmp_path):
    path = tmp_path / "synthetic.xlsx"
    workbook(path, header="date_of_birth")
    with pytest.raises(ValueError, match="direct identifier"):
        read_headers_only(path)
