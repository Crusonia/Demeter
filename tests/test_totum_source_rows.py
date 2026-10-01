"""Labeled synthetic OOXML fixtures exercise preservation, scope and safe aggregates."""

from __future__ import annotations

import copy
import io
import json
import zipfile
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

import demeter.analysis.totum_source_rows as totum
from demeter.analysis.totum_source_rows import (
    ANALYSIS_SECTIONS,
    DATASET,
    HEADERS,
    SOURCE_IDS,
    PreservedRows,
    RawCell,
    SourceRow,
    audit_totum_source_rows,
    preserve_source_rows,
    summarize_source_rows,
)
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
SECRET = "PRIVATE_UNREVIEWED_TOKEN_8721"


def _text(ref, value):
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def _value(ref, value, kind=None, style=None):
    attrs = f' r="{ref}"'
    if kind is not None:
        attrs += f' t="{kind}"'
    if style is not None:
        attrs += f' s="{style}"'
    return f"<c{attrs}><v>{escape(value)}</v></c>"


def _workbook(body=None, *, dimension="A1:AB14", headers=None, merges="A10:A11", extra=""):
    """Arbitrary software-only records; none of these are empirical clinical data."""
    rows = {}
    for ref, value in (HEADERS if headers is None else headers).items():
        row = int("".join(char for char in ref if char.isdigit()))
        rows.setdefault(row, []).append(_value(ref, "0", "s") if ref == "A1" else _text(ref, value))
    if body is None:
        body = {
            5: _text("A5", "PBO")
            + _text("B5", SECRET)
            + _value("C5", "123.456789")
            + _value("D5", "0")
            + _value("E5", SECRET),
            6: _text("A6", "\u2003T63  TID\u00a0")
            + _text("B6", "")
            + _value("C6", "-2")
            + _value("D6", "NaN"),
            7: _text("A7", SECRET)
            + _text("B7", SECRET + "-status")
            + _value("C7", "2", "s")
            + f'<c r="D7" t="e"><f>{SECRET}</f><v>#REF!</v></c>',
            8: '<c r="A8"/><c r="B8"/>' + _value("C8", "45000", style="1") + _value("D8", "1", "b"),
            10: _text("A10", "PBO") + '<c r="C10"/>' + _value("D10", "#SECRET!", "e"),
            11: '<c r="B11"/>' + _value("C11", "2026-01-01", "d") + _value("D11", "1", "s"),
            12: _text("A12", "pbo")
            + _value("B12", "6")
            + _value("C12", "Infinity")
            + _value("D12", SECRET, "unknown"),
            13: _text("A13", "T63 BID") + _value("C13", SECRET) + _value("D13", "1e309"),
        }
    for row, content in body.items():
        rows.setdefault(row, []).append(content)
    xml_rows = "".join(
        f'<row r="{row}">' + "".join(items) + "</row>" for row, items in sorted(rows.items())
    )
    merge_xml = "" if not merges else f'<mergeCells><mergeCell ref="{merges}"/></mergeCells>'
    selected = (
        f'<worksheet xmlns="{NS}"><dimension ref="{dimension}"/><sheetData>'
        + xml_rows
        + "</sheetData>"
        + merge_xml
        + extra
        + "</worksheet>"
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{NS}" xmlns:r="{REL}">'
            '<sheets><sheet name="Table 4" sheetId="1" r:id="r1"/>'
            '<sheet name="Unselected outcomes" sheetId="2" r:id="r2"/>'
            "</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<Relationships xmlns="{PKG_REL}">'
            f'<Relationship Id="r1" Type="{REL}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="r2" Type="{REL}/worksheet" Target="worksheets/sheet2.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", selected)
        # Deliberately unparsable: another worksheet's contents must never be read.
        archive.writestr("xl/worksheets/sheet2.xml", f"INVALID PRIVATE OUTCOMES {SECRET}")
        archive.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="{NS}">'
            "<si><t>Table 4: Secondary analyses</t></si><si><t></t></si>"
            "<si><t>123.456</t></si>"
            f"<si><t>{SECRET}-unselected-string</t></si></sst>",
        )
        archive.writestr(
            "xl/styles.xml",
            f'<styleSheet xmlns="{NS}"><cellXfs count="2">'
            '<xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>',
        )
    return stream.getvalue()


def _rewrite(workbook, name, transform):
    result = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(workbook)) as source, zipfile.ZipFile(result, "w") as target:
        for item in source.infolist():
            content = source.read(item.filename)
            target.writestr(item.filename, transform(content) if item.filename == name else content)
    return result.getvalue()


@pytest.fixture(scope="session")
def registered():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


@pytest.fixture
def protocol(registered):
    return json.loads(Path(registered.datasets[DATASET]["protocol_path"]).read_bytes())


@pytest.fixture
def fixture(registered, tmp_path, monkeypatch):
    """Repin arbitrary synthetic source bytes, preserving frozen nonclinical definitions."""
    registry = registered.model_copy(deep=True)
    spec = registry.datasets[DATASET]
    protocol = json.loads(Path(spec["protocol_path"]).read_bytes())
    receipts = json.loads(Path(spec["receipts_path"]).read_bytes())
    raw = tmp_path / "raw"
    raw.mkdir()
    workbook = _workbook()
    for label, pin in protocol["source_pins"].items():
        content = workbook if label == "workbook" else f"Synthetic source-only {label}".encode()
        (raw / pin["cache_filename"]).write_bytes(content)
        pin["sha256"], pin["size_bytes"] = digest(content), len(content)
        registry.sources[SOURCE_IDS[label]].sha256 = digest(content)
        receipts["receipts"][label]["sha256"] = digest(content)
        receipts["receipts"][label]["size_bytes"] = len(content)
    receipt_path = tmp_path / "receipts.json"
    receipt_path.write_bytes(encoded(receipts))
    spec["receipts_path"], spec["receipts_sha256"] = (
        str(receipt_path),
        digest(receipt_path.read_bytes()),
    )
    protocol["receipts"]["path"] = spec["receipts_path"]
    protocol["receipts"]["sha256"] = spec["receipts_sha256"]
    path = tmp_path / "protocol.json"
    path.write_bytes(encoded(protocol))
    spec["protocol_path"], spec["protocol_sha256"] = str(path), digest(path.read_bytes())
    # Only synthetic test bytes override the implementation's independently frozen pins.
    monkeypatch.setattr(totum, "PROTOCOL_SHA", spec["protocol_sha256"])
    monkeypatch.setattr(totum, "RECEIPTS_SHA", spec["receipts_sha256"])
    return registry, raw, workbook, protocol


def _repin(fixture, name, mutate):
    registry, _raw, _workbook_bytes, _protocol = fixture
    spec = registry.datasets[DATASET]
    path = Path(spec[f"{name}_path"])
    document = json.loads(path.read_bytes())
    mutate(document)
    path.write_bytes(encoded(document))
    spec[f"{name}_sha256"] = digest(path.read_bytes())
    # The fixture's monkeypatch cleanup restores real pins after each test.
    setattr(totum, "PROTOCOL_SHA" if name == "protocol" else "RECEIPTS_SHA", spec[f"{name}_sha256"])
    if name == "receipts":
        _repin(
            fixture,
            "protocol",
            lambda item: item["receipts"].update(sha256=spec["receipts_sha256"]),
        )
    return document


def test_preservation_and_safe_report_are_distinct_from_clinical_acceptance(fixture):
    registry, raw, workbook, protocol = fixture
    before = registry.model_dump(mode="json")
    preserved = preserve_source_rows(workbook, protocol)
    report = audit_totum_source_rows(registry, raw)
    assert registry.model_dump(mode="json") == before
    assert preserved.workbook_sha256 == digest(workbook)
    assert preserved.scan_last_row == 14
    assert len(preserved.rows) == 10
    assert report["source_audit_passed"] is True
    assert report["clinically_adequate"] is False
    assert report["fit_ready"] is False
    assert report["decision"]["endpoint_distribution_accepted"] is False
    assert not report["scientific_release_ready"]
    assert not report["decision"]["clinical_fit_allowed"]
    assert not report["decision"]["engine_activation_allowed"]
    results = report["results"]
    assert results["all_empty_layout_position_count"] == 2
    assert results["nonempty_source_position_count"] == 8
    assert all(sum(counts.values()) == 10 for counts in results["cell_kind_counts"].values())
    assert sum(results["same_row_C_D_kind_counts"].values()) == 10
    assert results["raw_numeric_fpg_counts"]["C"] == {
        "positive_finite": 1,
        "zero": 0,
        "negative_finite": 1,
        "nonfinite": 1,
    }
    assert results["raw_numeric_fpg_counts"]["D"] == {
        "positive_finite": 1,
        "zero": 1,
        "negative_finite": 0,
        "nonfinite": 1,
    }
    assert results["group_coverage"]["reviewed_text_label_counts"] == {
        "PBO": 2,
        "T63 TID": 1,
        "T63 BID": 1,
    }
    assert results["group_coverage"]["distinct_nonempty_text_token_count"] == 5
    assert results["group_coverage"]["unrecognized_text_cell_count"] == 2
    assert results["group_coverage"]["missing_or_unresolved_group_cell_count"] == 6
    assert results["body_merge_structure_count"] == 1
    assert results["merged_selected_body_cell_count"] == 2
    assert results["verified_participant_count"] is None
    assert results["verified_clinical_pair_count"] is None
    assert results["positive_finite_means_valid_assay"] is False
    assert report["provenance"]["local_bytes_acquisition_time_certified"] is False
    assert set(report["provenance"]["source_checks"]) == set(SOURCE_IDS)
    assert (
        report["provenance"]["historical_acquisition_receipts"]["registration"]["content_type"]
        is None
    )
    assert SECRET not in json.dumps(report)
    assert "123.456" not in json.dumps(report)
    assert "#SECRET!" not in json.dumps(report)
    assert "2026-01-01" not in json.dumps(report)


def test_local_raw_observations_preserve_formulas_types_and_are_immutable(protocol):
    preserved = preserve_source_rows(_workbook(), protocol)
    by_row = {row.worksheet_row: row for row in preserved.rows}
    assert by_row[7].cells[2].kind == "text"
    assert by_row[7].cells[2].text == "123.456"
    formula = by_row[7].cells[3]
    assert formula.kind == "formula" and formula.formula == SECRET
    assert formula.cached_value_present and formula.raw_value == "#REF!"
    assert by_row[8].cells[2].date_formatted and by_row[8].cells[2].kind == "date"
    assert by_row[8].cells[3].kind == "boolean"
    assert by_row[9].cells[0].kind == "absent"
    assert by_row[10].cells[2].kind == "blank"
    assert by_row[11].cells[3].kind == "empty_text"
    assert by_row[13].cells[2].kind == "other_unresolved"
    assert by_row[13].cells[3].numeric_kind == "positive_finite"
    with pytest.raises(FrozenInstanceError):
        formula.raw_value = "0"
    with pytest.raises(FrozenInstanceError):
        preserved.rows = ()
    with pytest.raises(AttributeError):
        preserved.rows.append(by_row[5])
    with pytest.raises(TypeError):
        by_row[5].cells[0] = by_row[6].cells[0]


def test_constructor_collection_inputs_cannot_mutate_preserved_history(protocol):
    original = preserve_source_rows(_workbook(), protocol)
    cells = list(original.rows[0].cells)
    row = SourceRow(5, cells)
    rows, merges = [row], ["A5:A6"]
    preserved = PreservedRows("Table 4", original.workbook_sha256, 5, 5, 5, rows, merges)
    cells.clear()
    rows.clear()
    merges.clear()
    assert len(row.cells) == 4
    assert preserved.rows == (row,)
    assert preserved.body_merges == ("A5:A6",)
    with pytest.raises(AttributeError):
        row.cells.append(original.rows[1].cells[0])
    with pytest.raises(AttributeError):
        preserved.body_merges.append("A6:A7")


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", SECRET),
        ("column", SECRET),
        ("text", [SECRET]),
        ("raw_value", {"private": SECRET}),
        ("formula", [SECRET]),
        ("numeric_kind", SECRET),
        ("row", True),
        ("merged", 1),
        ("style_index", True),
        ("cached_value_present", True),
    ],
)
def test_raw_cell_leaves_reject_unreviewed_labels_and_mutable_or_inconsistent_fields(
    protocol, field, value
):
    cell = preserve_source_rows(_workbook(), protocol).rows[0].cells[0]
    with pytest.raises(ValueError) as error:
        replace(cell, **{field: value})
    assert SECRET not in str(error.value)


def test_mutable_text_constructor_is_rejected_before_safe_summary():
    caller_text = [SECRET]
    with pytest.raises(ValueError):
        RawCell(5, "C", "text", text=caller_text)
    caller_text.append("later mutation")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda cells: cells[:3],
        lambda cells: tuple(reversed(cells)),
        lambda cells: (replace(cells[0], row=6), *cells[1:]),
        lambda cells: (cells[0], cells[0], cells[2], cells[3]),
    ],
)
def test_source_row_requires_exact_four_column_and_row_coordinates(protocol, mutation):
    cells = preserve_source_rows(_workbook(), protocol).rows[0].cells
    with pytest.raises(ValueError):
        SourceRow(5, mutation(cells))


def test_preserved_positions_cannot_duplicate_or_omit_source_rows(protocol):
    original = preserve_source_rows(_workbook(), protocol)
    with pytest.raises(ValueError):
        replace(original, rows=(original.rows[0],) * len(original.rows))
    with pytest.raises(ValueError):
        replace(original, rows=original.rows[1:])


@pytest.mark.parametrize(
    "malformed",
    [
        '<c r="C5"><c r="E5"><v>123</v></c></c>',
        '<c r="C5"><c r="C5"><v>123</v></c></c>',
        '<c r="C5"><foreign:v xmlns:foreign="urn:foreign">123</foreign:v></c>',
        '<c r="C5"><wrapper><v>123</v></wrapper></c>',
        '<c r="C5"><v><wrapper>123</wrapper></v></c>',
        '<c r="C5"><foreign:f xmlns:foreign="urn:foreign">PRIVATE</foreign:f></c>',
        '<c r="C5"><wrapper><f>PRIVATE</f></wrapper></c>',
        '<c r="C5" t="inlineStr"><is><t>PBO</t></is><is><t>PRIVATE</t></is></c>',
        '<c r="C5" t="inlineStr"><is><wrapper><t>PRIVATE</t></wrapper></is></c>',
        '<c r="C5" t="inlineStr"><is><foreign:t xmlns:foreign="urn:foreign">PRIVATE</foreign:t></is></c>',
        '<c r="C5" t="inlineStr"><is><t><t>PRIVATE</t></t></is></c>',
        '<c r="C5" t="inlineStr"><is><t>PRIVATE</t><t>PRIVATE</t></is></c>',
        '<c r="C5"><t>PRIVATE</t></c>',
    ],
)
def test_nested_foreign_wrapped_and_duplicate_cell_nodes_cannot_leak_into_selection(
    protocol, malformed
):
    with pytest.raises(ValueError) as error:
        preserve_source_rows(_workbook({5: malformed}, dimension="A1:D5", merges=""), protocol)
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda xml: xml.replace(b"<sheetData>", b"<wrapper><sheetData>").replace(
            b"</sheetData>", b"</sheetData></wrapper>"
        ),
        lambda xml: xml.replace(b'<row r="5">', b'<wrapper><row r="5">').replace(
            b"</row></sheetData>", b"</row></wrapper></sheetData>"
        ),
        lambda xml: xml.replace(b'<c r="C5">', b'<wrapper><c r="C5">').replace(
            b"</c></row>", b"</c></wrapper></row>"
        ),
        lambda xml: xml.replace(b"<dimension ", b'<foreign:dimension xmlns:foreign="urn:foreign" '),
        lambda xml: xml.replace(
            b'<c r="C5">', b'<foreign:c xmlns:foreign="urn:foreign" r="C5">'
        ).replace(b"</c></row>", b"</foreign:c></row>"),
    ],
)
def test_sheet_metadata_and_cell_paths_are_qualified_and_direct(protocol, mutate):
    workbook = _workbook({5: _value("C5", "123")}, dimension="A1:D5", merges="")
    with pytest.raises(ValueError):
        preserve_source_rows(_rewrite(workbook, "xl/worksheets/sheet1.xml", mutate), protocol)


@pytest.mark.parametrize(
    "replacement",
    [
        f"<si><wrapper><t>{SECRET}</t></wrapper></si>",
        f'<si><foreign:t xmlns:foreign="urn:foreign">{SECRET}</foreign:t></si>',
        f"<si><t><t>{SECRET}</t></t></si>",
        f"<si><si><t>{SECRET}</t></si></si>",
        f'<foreign:si xmlns:foreign="urn:foreign"><t>{SECRET}</t></foreign:si>',
        f"<wrapper><si><t>{SECRET}</t></si></wrapper>",
        f"<si><t>{SECRET}</t><t>{SECRET}</t></si>",
    ],
)
def test_shared_string_item_and_text_ancestry_prevent_index_or_token_contamination(
    protocol, replacement
):
    workbook = _rewrite(
        _workbook(),
        "xl/sharedStrings.xml",
        lambda xml: xml.replace(
            b"<si><t>Table 4: Secondary analyses</t></si>",
            replacement.encode(),
        ),
    )
    with pytest.raises(ValueError) as error:
        preserve_source_rows(workbook, protocol)
    assert SECRET not in str(error.value)


def test_legal_inline_and_shared_rich_text_retains_plain_text_and_excludes_phonetics(protocol):
    rich_group = (
        '<c r="A5" t="inlineStr"><is><r><rPr><b/><color rgb="FF000000"/></rPr>'
        '<t>P</t></r><r><t>BO</t></r><rPh sb="0" eb="3"><t>'
        + SECRET
        + '</t></rPh><phoneticPr fontId="0" type="noConversion"/></is></c>'
    )
    workbook = _workbook({5: rich_group + _value("C5", "2", "s")}, dimension="A1:D5", merges="")
    workbook = _rewrite(
        workbook,
        "xl/sharedStrings.xml",
        lambda xml: xml.replace(
            b"<si><t>123.456</t></si>",
            (
                "<si><r><rPr><i/></rPr><t>opaque </t></r><r><t>text</t></r>"
                '<rPh sb="0" eb="6"><t>' + SECRET + '</t></rPh><phoneticPr fontId="0"/></si>'
            ).encode(),
        ),
    )
    preserved = preserve_source_rows(workbook, protocol)
    assert preserved.rows[0].cells[0].text == "PBO"
    assert preserved.rows[0].cells[2].text == "opaque text"
    report = summarize_source_rows(preserved)
    assert report["group_coverage"]["reviewed_text_label_counts"]["PBO"] == 1
    assert SECRET not in json.dumps(report)


@pytest.mark.parametrize(
    "malformed",
    [
        '<c r="A5" t="inlineStr"><is>UNREVIEWED_RAW_TEXT<t>PBO</t></is></c>',
        '<c r="C5">123</c>',
        '<c r="C5">PRIVATE<v>123</v></c>',
        '<c r="C5"><v>123</v>PRIVATE</c>',
        '<c r="C5" t="inlineStr"><is><r>PRIVATE<t>text</t></r></is></c>',
        '<c r="C5" t="inlineStr"><is><r><rPr>PRIVATE<b/></rPr><t>text</t></r></is></c>',
        '<c r="C5" t="inlineStr"><is><rPh sb="0" eb="1">PRIVATE<t>phonetic</t></rPh></is></c>',
    ],
)
def test_bare_character_data_cannot_be_discarded_as_blank_or_reviewed_label(protocol, malformed):
    with pytest.raises(ValueError) as error:
        preserve_source_rows(_workbook({5: malformed}, dimension="A1:D5", merges=""), protocol)
    assert "PRIVATE" not in str(error.value)
    assert "UNREVIEWED" not in str(error.value)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda xml: xml.replace(b"<sheetData>", b"<sheetData>PRIVATE"),
        lambda xml: xml.replace(b'<row r="5">', b'<row r="5">PRIVATE'),
        lambda xml: xml.replace(
            b'<dimension ref="A1:D5"/>', b'<dimension ref="A1:D5">PRIVATE</dimension>'
        ),
        lambda xml: xml.replace(b"<sheetData>", b"PRIVATE<sheetData>"),
    ],
)
def test_observation_structural_positions_reject_nonwhitespace_text(protocol, mutate):
    workbook = _workbook({5: _value("C5", "123")}, dimension="A1:D5", merges="")
    with pytest.raises(ValueError):
        preserve_source_rows(_rewrite(workbook, "xl/worksheets/sheet1.xml", mutate), protocol)


@pytest.mark.parametrize(
    "replacement",
    [
        "<si>PRIVATE<t>Table 4: Secondary analyses</t></si>",
        "<si><r>PRIVATE<t>Table 4: Secondary analyses</t></r></si>",
        "PRIVATE<si><t>Table 4: Secondary analyses</t></si>",
    ],
)
def test_shared_string_structural_text_cannot_silently_repair_a_header(protocol, replacement):
    workbook = _rewrite(
        _workbook(),
        "xl/sharedStrings.xml",
        lambda xml: xml.replace(
            b"<si><t>Table 4: Secondary analyses</t></si>",
            replacement.encode(),
        ),
    )
    with pytest.raises(ValueError):
        preserve_source_rows(workbook, protocol)


def test_ordinary_xml_indentation_does_not_change_selected_text_or_numeric_types(protocol):
    workbook = _workbook(
        {5: _text("A5", "PBO") + _value("C5", "123")}, dimension="A1:D5", merges=""
    )
    before = summarize_source_rows(preserve_source_rows(workbook, protocol))
    for member in ("xl/worksheets/sheet1.xml", "xl/sharedStrings.xml"):
        workbook = _rewrite(workbook, member, lambda xml: xml.replace(b"><", b"> \n\t<"))
    after = summarize_source_rows(preserve_source_rows(workbook, protocol))
    assert before == after


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", "zero"),
        ("-0", "zero"),
        ("-0.01", "negative_finite"),
        ("9.1", "positive_finite"),
        ("1e9999", "positive_finite"),
        ("NaN", "nonfinite"),
        ("sNaN", "nonfinite"),
        ("-Infinity", "nonfinite"),
        ("Inf", "nonfinite"),
        ("INF", "nonfinite"),
    ],
)
def test_numeric_availability_is_exact_type_classification_not_glucose_validity(
    protocol, value, expected
):
    preserved = preserve_source_rows(
        _workbook({5: _value("C5", value)}, dimension="A1:D5", merges=""), protocol
    )
    cell = preserved.rows[0].cells[2]
    assert cell.kind == "numeric" and cell.numeric_kind == expected
    assert summarize_source_rows(preserved)["positive_finite_means_valid_assay"] is False


@pytest.mark.parametrize(
    "cell,kind",
    [
        ('<c r="C5"/>', "blank"),
        (_text("C5", ""), "empty_text"),
        (_text("C5", "0"), "text"),
        (_text("C5", "-999"), "text"),
        (_value("C5", "0", "b"), "boolean"),
        (_value("C5", "#N/A", "e"), "error"),
        (_value("C5", "2026-01-01", "d"), "date"),
        (_value("C5", "5", style="1"), "date"),
        ('<c r="C5"><f/><v>0</v></c>', "formula"),
        ('<c r="C5" t="d"><f>NA()</f><v>0</v></c>', "formula"),
        (_value("C5", SECRET), "other_unresolved"),
        (_value("C5", "1_23"), "other_unresolved"),
        (_value("C5", "١٢٣"), "other_unresolved"),
        (_value("C5", "\u00a01\u00a0"), "other_unresolved"),
        (_value("C5", "5", "unknown"), "other_unresolved"),
    ],
)
def test_missing_marker_and_precedence_never_imply_zero_or_absence(protocol, cell, kind):
    preserved = preserve_source_rows(_workbook({5: cell}, dimension="A1:D5", merges=""), protocol)
    assert preserved.rows[0].cells[2].kind == kind
    assert sum(summarize_source_rows(preserved)["raw_numeric_fpg_counts"]["C"].values()) == 0


def test_dimension_and_selected_cells_determine_scan_without_other_outcomes(protocol):
    workbook = _workbook(
        {5: _value("E5", SECRET), 8: _text("A8", "PBO")}, dimension="A1:AB6", merges=""
    )
    preserved = preserve_source_rows(workbook, protocol)
    assert preserved.declared_last_row == 6
    assert preserved.selected_last_row == 8
    assert preserved.scan_last_row == 8
    assert summarize_source_rows(preserved)["all_empty_layout_position_count"] == 3


def test_duplicate_source_rows_are_not_deduplicated_and_merges_not_filled(protocol):
    body = {row: _text(f"A{row}", "PBO") + _value(f"C{row}", "5") for row in (5, 6)}
    body[7] = _value("C7", "5")
    preserved = preserve_source_rows(_workbook(body, dimension="A1:D7", merges="A6:A7"), protocol)
    result = summarize_source_rows(preserved)
    assert result["source_position_count"] == 3
    assert result["group_coverage"]["reviewed_text_label_counts"]["PBO"] == 2
    assert preserved.rows[2].cells[0].kind == "absent" and preserved.rows[2].cells[0].merged
    assert result["group_coverage"]["missing_or_unresolved_group_cell_count"] == 1


@pytest.mark.parametrize(
    "transform",
    [
        lambda xml: xml.replace(b"<worksheet ", b"<other ").replace(b"</worksheet>", b"</other>"),
        lambda xml: xml.replace(b"Baseline", SECRET.encode()),
        lambda xml: xml.replace(b'<c r="C5">', b'<c r="C5"><v>9</v>'),
        lambda xml: xml.replace(b'<row r="5">', b'<row r="4">'),
        lambda xml: xml.replace(b'<c r="C5">', b'<c r="C0">'),
        lambda xml: xml.replace(b'<c r="C5">', b'<c r="C1048577">'),
        lambda xml: xml.replace(b'<dimension ref="A1:AB14"/>', b""),
        lambda xml: xml.replace(b'<dimension ref="A1:AB14"/>', b'<dimension ref="A1:AB14"/>' * 2),
        lambda xml: xml.replace(b's="1"', b's="99"'),
        lambda xml: xml.replace(b"<v>0</v>", b"<v>99999</v>", 1),
        lambda xml: b'<!DOCTYPE worksheet [<!ENTITY unsafe "' + SECRET.encode() + b'">]>' + xml,
    ],
)
def test_malformed_selected_xml_fails_without_disclosing_raw_tokens(protocol, transform):
    workbook = _rewrite(_workbook(), "xl/worksheets/sheet1.xml", transform)
    with pytest.raises(ValueError) as error:
        preserve_source_rows(workbook, protocol)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "member,transform",
    [
        ("xl/workbook.xml", lambda xml: xml.replace(b'name="Table 4"', b'name="Other"')),
        (
            "xl/workbook.xml",
            lambda xml: xml.replace(b'name="Unselected outcomes"', b'name="Table 4"'),
        ),
        (
            "xl/_rels/workbook.xml.rels",
            lambda xml: xml.replace(b'Target="worksheets/sheet1.xml"', b'Target="../secret.xml"'),
        ),
        (
            "xl/_rels/workbook.xml.rels",
            lambda xml: xml.replace(b'Id="r1"', b'Id="r1" TargetMode="External"'),
        ),
        (
            "xl/styles.xml",
            lambda xml: xml.replace(b'numFmtId="14"', f'numFmtId="{SECRET}"'.encode()),
        ),
    ],
)
def test_sheet_relationship_and_style_integrity_fail_closed(protocol, member, transform):
    with pytest.raises(ValueError) as error:
        preserve_source_rows(_rewrite(_workbook(), member, transform), protocol)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("selection", "worksheet", "Other"),
        ("selection", "columns", ["A", "B", "C", "E"]),
        ("selection", "first_source_row", True),
        ("selection", "header_rows", [True, 2, 3, 4]),
        ("selection", "no_forward_fill", False),
        ("selection", "no_merged_anchor_resolution", False),
        ("execution_gate", "fit_allowed", True),
        ("execution_gate", "engine_activation_allowed", 0),
        ("execution_gate", "scientific_release_ready", True),
        ("safe_aggregate_outputs", "safe_group_labels", [SECRET]),
    ],
)
def test_repinned_scope_drift_still_rejected(fixture, section, key, value):
    registry, raw, _workbook_bytes, _protocol = fixture
    updated = _repin(fixture, "protocol", lambda item: item[section].update({key: value}))
    registry.datasets[DATASET]["analysis"] = {key: updated[key] for key in ANALYSIS_SECTIONS}
    with pytest.raises(ValueError):
        audit_totum_source_rows(registry, raw)


@pytest.mark.parametrize(
    "key,value",
    [
        ("model_role", "health_model"),
        ("status", "observed"),
        ("evidence_grade", "A"),
        ("clinical_fit_allowed", 0),
        ("engine_activation_allowed", True),
        ("analysis", {}),
        ("source_ids", {"workbook": SOURCE_IDS["workbook"]}),
    ],
)
def test_registry_role_and_analysis_drift_precede_source_processing(
    fixture, monkeypatch, key, value
):
    registry, raw, _workbook_bytes, _protocol = fixture
    registry.datasets[DATASET][key] = value
    monkeypatch.setattr(
        "demeter.analysis.totum_source_rows.preserve_source_rows",
        lambda *_: pytest.fail("Parsed before guard"),
    )
    with pytest.raises(ValueError):
        audit_totum_source_rows(registry, raw)


def test_analysis_boolean_cannot_impersonate_integer_header_row(fixture):
    registry, raw, _workbook_bytes, _protocol = fixture
    registry.datasets[DATASET]["analysis"]["selection"]["header_rows"][0] = True
    with pytest.raises(ValueError):
        audit_totum_source_rows(registry, raw)


@pytest.mark.parametrize("label", list(SOURCE_IDS))
@pytest.mark.parametrize("failure", ["missing", "hash", "source_link", "receipt_link"])
def test_every_companion_source_is_required_before_any_intake(fixture, monkeypatch, label, failure):
    registry, raw, _workbook_bytes, protocol = fixture
    pin = protocol["source_pins"][label]
    if failure == "missing":
        (raw / pin["cache_filename"]).unlink()
    elif failure == "hash":
        (raw / pin["cache_filename"]).write_bytes(SECRET.encode())
    elif failure == "source_link":
        registry.sources[SOURCE_IDS[label]].url = "https://example.org/drift"
    else:
        _repin(
            fixture,
            "receipts",
            lambda item: item["receipts"][label].update(requested_url="https://example.org/drift"),
        )
    monkeypatch.setattr(
        "demeter.analysis.totum_source_rows.preserve_source_rows",
        lambda *_: pytest.fail("Parsed before all pins"),
    )
    with pytest.raises(ValueError) as error:
        audit_totum_source_rows(registry, raw)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("name", ["protocol", "receipts"])
def test_frozen_checksum_and_duplicate_json_key_guards(fixture, name):
    registry, raw, _workbook_bytes, _protocol = fixture
    spec = registry.datasets[DATASET]
    path = Path(spec[f"{name}_path"])
    original = path.read_bytes()
    path.write_bytes(original + b" ")
    with pytest.raises(ValueError):
        audit_totum_source_rows(registry, raw)
    path.write_bytes(b'{"schema_version":1,' + original.lstrip()[1:])
    spec[f"{name}_sha256"] = digest(path.read_bytes())
    setattr(totum, "PROTOCOL_SHA" if name == "protocol" else "RECEIPTS_SHA", spec[f"{name}_sha256"])
    with pytest.raises(ValueError, match="Duplicate"):
        audit_totum_source_rows(registry, raw)


@pytest.mark.parametrize("name", ["protocol", "receipts"])
def test_changing_registry_and_contract_hash_cannot_override_frozen_pin(fixture, name):
    registry, raw, _workbook_bytes, _protocol = fixture
    spec = registry.datasets[DATASET]
    path = Path(spec[f"{name}_path"])
    path.write_bytes(path.read_bytes() + b" ")
    spec[f"{name}_sha256"] = digest(path.read_bytes())
    with pytest.raises(ValueError, match="checksum"):
        audit_totum_source_rows(registry, raw)


@pytest.mark.parametrize(
    "key,value",
    [
        ("http_status", True),
        ("size_bytes", True),
        ("started_at_utc", "2027-01-01T00:00:00+00:00"),
        ("completed_at_utc", "2026-09-30T23:15:53.403318"),
        ("final_url_signed_query_omitted", False),
        ("resolved_url", "https://example.org/?signed=secret"),
    ],
)
def test_historic_receipt_inconsistencies_block_intake(fixture, key, value):
    registry, raw, _workbook_bytes, _protocol = fixture
    _repin(fixture, "receipts", lambda item: item["receipts"]["workbook"].update({key: value}))
    with pytest.raises(ValueError):
        audit_totum_source_rows(registry, raw)


def test_safe_aggregate_is_order_insensitive_and_input_objects_unmodified(protocol):
    before = copy.deepcopy(protocol)
    original = _workbook({5: _text("A5", "PBO") + _value("C5", "1"), 6: _text("A6", "T63 BID")})
    swapped = _workbook({6: _text("A6", "PBO") + _value("C6", "1"), 5: _text("A5", "T63 BID")})
    assert summarize_source_rows(preserve_source_rows(original, protocol)) == summarize_source_rows(
        preserve_source_rows(swapped, protocol)
    )
    assert protocol == before


def test_source_symlink_escape_is_rejected_when_supported(fixture, tmp_path):
    registry, raw, _workbook_bytes, protocol = fixture
    source = raw / protocol["source_pins"]["workbook"]["cache_filename"]
    target = tmp_path / "elsewhere.xlsx"
    source.replace(target)
    try:
        source.symlink_to(target)
    except OSError:
        pytest.skip("Host cannot create symlinks without additional privileges")
    with pytest.raises(ValueError):
        audit_totum_source_rows(registry, raw)
