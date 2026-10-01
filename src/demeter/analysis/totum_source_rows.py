"""Offline, aggregate-only TOTUM source-layout adequacy; no clinical interpretation."""

from __future__ import annotations

import io
import json
import posixpath
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
from xml.parsers import expat

from openpyxl.styles.numbers import BUILTIN_FORMATS, is_date_format

from demeter.data.ingest import digest
from demeter.schema import EvidenceRegistry

DATASET = "totum_source_row_adequacy"
PROTOCOL_SHA = "fe9b70d246b1584aeec732ec8b2a97d4faf1a8d0121df916a01739e1c774d52f"
RECEIPTS_SHA = "dfcbe2b29c1c6bdeb811d024a932f638d49a2fbe7581369cf24b12aa004d8457"
SOURCE_IDS = {
    "metadata": "totum_metadata2026",
    "methods": "totum_methods2026",
    "reporting_summary": "totum_reporting_summary2026",
    "registration": "totum_registration2026",
    "workbook": "totum_workbook2026",
}
COLUMNS = ("A", "B", "C", "D")
HEADERS = {
    "A1": "Table 4: Secondary analyses",
    "A2": "Glycemic parameters",
    "C3": "Baseline",
    "D3": "6 months",
    "A4": "Group",
    "B4": "Glycemic status",
    "C4": "FPG (mg/dL)",
    "D4": "FPG (mg/dL)",
}
SAFE_GROUP_LABELS = ("PBO", "T63 TID", "T63 BID")
KINDS = (
    "absent",
    "blank",
    "empty_text",
    "numeric",
    "text",
    "formula",
    "error",
    "date",
    "boolean",
    "other_unresolved",
)
NUMERIC_KINDS = ("positive_finite", "zero", "negative_finite", "nonfinite")
ANALYSIS_SECTIONS = (
    "selection",
    "expected_headers",
    "raw_cell_preservation",
    "safe_aggregate_outputs",
)
_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


@dataclass(frozen=True)
class RawCell:
    """Local immutable source observation. Raw content must never enter public reports."""

    row: int
    column: str
    kind: str
    xml_type: str | None = None
    raw_value: str | None = None
    text: str | None = None
    has_formula: bool = False
    formula: str | None = None
    cached_value_present: bool = False
    style_index: int | None = None
    date_formatted: bool = False
    numeric_kind: str | None = None
    merged: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.row) is not int
            or not 1 <= self.row <= 1048576
            or type(self.column) is not str
            or self.column not in COLUMNS
            or type(self.kind) is not str
            or self.kind not in KINDS
            or any(
                value is not None and type(value) is not str
                for value in (
                    self.xml_type,
                    self.raw_value,
                    self.text,
                    self.formula,
                    self.numeric_kind,
                )
            )
            or any(
                type(value) is not bool
                for value in (
                    self.has_formula,
                    self.cached_value_present,
                    self.date_formatted,
                    self.merged,
                )
            )
            or self.style_index is not None
            and (type(self.style_index) is not int or self.style_index < 0)
            or self.has_formula != (self.kind == "formula")
            or self.cached_value_present
            and (not self.has_formula or self.raw_value is None)
            or self.numeric_kind is not None
            and self.numeric_kind not in NUMERIC_KINDS
            or (self.kind == "numeric") != (self.numeric_kind is not None)
            or self.kind in ("text", "empty_text")
            and self.text is None
            or self.kind == "empty_text"
            and self.text != ""
        ):
            raise ValueError("Invalid immutable TOTUM raw-cell fields")


@dataclass(frozen=True)
class SourceRow:
    """A worksheet position, never a verified participant or clinical pair."""

    worksheet_row: int
    cells: tuple[RawCell, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cells", tuple(self.cells))
        if (
            type(self.worksheet_row) is not int
            or not 1 <= self.worksheet_row <= 1048576
            or len(self.cells) != 4
            or any(type(cell) is not RawCell for cell in self.cells)
            or tuple(cell.column for cell in self.cells) != COLUMNS
            or any(cell.row != self.worksheet_row for cell in self.cells)
        ):
            raise ValueError("SourceRow requires immutable raw observations")


@dataclass(frozen=True)
class PreservedRows:
    worksheet: str
    workbook_sha256: str
    declared_last_row: int
    selected_last_row: int
    scan_last_row: int
    rows: tuple[SourceRow, ...]
    body_merges: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "body_merges", tuple(self.body_merges))
        if (
            self.worksheet != "Table 4"
            or type(self.workbook_sha256) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", self.workbook_sha256)
            or any(
                type(value) is not int or not 1 <= value <= 1048576
                for value in (
                    self.declared_last_row,
                    self.selected_last_row,
                    self.scan_last_row,
                )
            )
            or self.scan_last_row != max(self.declared_last_row, self.selected_last_row)
            or any(type(row) is not SourceRow for row in self.rows)
            or tuple(row.worksheet_row for row in self.rows)
            != tuple(range(5, self.scan_last_row + 1))
            or any(type(ref) is not str for ref in self.body_merges)
        ):
            raise ValueError("PreservedRows requires immutable rows and merge references")
        for ref in self.body_merges:
            _range(ref)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate TOTUM contract JSON key")
        result[key] = value
    return result


def _json(content: bytes) -> dict:
    try:
        result = json.loads(content, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid TOTUM contract JSON") from exc
    if not isinstance(result, dict):
        raise ValueError("Invalid TOTUM contract object")
    return result


def _exact_json(left: object, right: object) -> bool:
    """JSON equality keeps booleans distinct from numerical schema values."""
    try:
        return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
            right, sort_keys=True, allow_nan=False
        )
    except (TypeError, ValueError):
        return False


def _linked(path: Path) -> bool:
    return any(item.is_symlink() for item in (path, *path.parents))


def _read(path: Path) -> bytes:
    if _linked(path):
        raise ValueError("TOTUM source/contract paths must not contain symlinks")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError("TOTUM required local source/contract unavailable") from exc


def _contract(spec: dict, name: str) -> tuple[dict, str]:
    content = _read(Path(spec[f"{name}_path"]))
    sha = digest(content)
    expected = PROTOCOL_SHA if name == "protocol" else RECEIPTS_SHA
    if sha != spec[f"{name}_sha256"] or sha != expected:
        raise ValueError("TOTUM frozen contract checksum mismatch")
    return _json(content), sha


def _scope(protocol: dict) -> None:
    """Fail closed if a repinned fixture/contract changes the implemented observation surface."""
    selection = protocol["selection"]
    if (
        type(protocol["schema_version"]) is not int
        or protocol["schema_version"] != 1
        or protocol["dataset"] != DATASET
        or protocol["model_role"] != "benchmark_only"
        or protocol["source_ids"] != SOURCE_IDS
        or selection["worksheet"] != "Table 4"
        or selection["columns"] != list(COLUMNS)
        or not _exact_json(selection["header_rows"], [1, 2, 3, 4])
        or type(selection["first_source_row"]) is not int
        or selection["first_source_row"] != 5
        or protocol["expected_headers"] != HEADERS
        or any(
            selection[key] is not True
            for key in (
                "no_cross_sheet_join",
                "no_cross_block_join",
                "no_record_deduplication",
                "no_forward_fill",
                "no_merged_anchor_resolution",
            )
        )
        or protocol["safe_aggregate_outputs"]["safe_group_labels"] != list(SAFE_GROUP_LABELS)
        or protocol["raw_cell_preservation"]["kind_precedence"]
        != [
            "formula",
            "error",
            "date",
            "boolean",
            "blank_or_absent",
            "numeric",
            "text",
            "other_unresolved",
        ]
        or any(
            protocol["execution_gate"][key] is not False
            for key in (
                "fit_allowed",
                "engine_activation_allowed",
                "scientific_release_ready",
                "independent_expert_review",
                "numeric_outcome_rows_already_inspected",
                "outcome_arithmetic_already_performed",
            )
        )
        or protocol["execution_gate"]["root_review_and_committed_freeze_required"] is not True
        or protocol["source_choice_and_possible_future_estimand"][
            "next_analysis_requires_separate_freeze"
        ]
        is not True
    ):
        raise ValueError("TOTUM frozen scope/header/clinical-gate mismatch")


def _coordinate(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", value)
    if not match:
        raise ValueError("Invalid TOTUM worksheet coordinate")
    column = 0
    for char in match[1]:
        column = column * 26 + ord(char) - ord("A") + 1
    row = int(match[2])
    if column > 16384 or row > 1048576:
        raise ValueError("TOTUM worksheet coordinate outside OOXML limits")
    return column, row


def _range(value: str) -> tuple[int, int, int, int]:
    parts = value.split(":")
    if len(parts) not in (1, 2):
        raise ValueError("Invalid TOTUM worksheet range")
    c1, r1 = _coordinate(parts[0])
    c2, r2 = _coordinate(parts[-1])
    if c2 < c1 or r2 < r1:
        raise ValueError("Invalid TOTUM worksheet range ordering")
    return c1, r1, c2, r2


def _xml(content: bytes) -> ET.Element:
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("TOTUM OOXML must not contain document entities")
    try:
        return ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("Invalid TOTUM OOXML metadata") from exc


def _stream(content: bytes, start, end, text) -> None:
    parser = expat.ParserCreate(namespace_separator="}")
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text

    def reject(*_args):
        raise ValueError("TOTUM OOXML must not contain document entities")

    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    try:
        parser.Parse(content, True)
    except expat.ExpatError as exc:
        raise ValueError("Invalid TOTUM selected OOXML") from exc


def _date_styles(content: bytes | None) -> tuple[bool, ...]:
    if content is None:
        return (False,)
    root = _xml(content)
    if root.tag != f"{{{_NS}}}styleSheet":
        raise ValueError("Invalid TOTUM styles metadata")
    custom = {}
    for item in root.findall(f"{{{_NS}}}numFmts/{{{_NS}}}numFmt"):
        key = int(item.attrib["numFmtId"])
        if key in custom:
            raise ValueError("Duplicate TOTUM number format")
        custom[key] = item.attrib["formatCode"]
    formats = root.findall(f"{{{_NS}}}cellXfs/{{{_NS}}}xf")
    if not formats:
        raise ValueError("Missing TOTUM style definitions")
    result = []
    for item in formats:
        key = int(item.attrib.get("numFmtId", "0"))
        if key not in custom and key not in BUILTIN_FORMATS:
            # Undefined/nonstandard formats are not silently called glucose.
            raise ValueError("Unresolved TOTUM number format")
        result.append(is_date_format(custom.get(key, BUILTIN_FORMATS.get(key, ""))))
    return tuple(result)


class _RichText:
    """Validate CT_Rst ancestry; capture only requested plain/rich text, never phonetics."""

    def __init__(self, root: str, capture: bool):
        self.root = root
        self.capture = capture
        self.frames: list[tuple[str, Counter]] = []
        self.parts: list[str] = []

    def start(self, name: str) -> None:
        local = name.rsplit("}", 1)[-1]
        if name != f"{_NS}}}{local}":
            raise ValueError("Foreign TOTUM string node")
        if not self.frames:
            if local != self.root:
                raise ValueError("Invalid TOTUM string root")
        else:
            parent, counts = self.frames[-1]
            font = {
                "rFont",
                "charset",
                "family",
                "b",
                "i",
                "strike",
                "outline",
                "shadow",
                "condense",
                "extend",
                "color",
                "sz",
                "u",
                "vertAlign",
                "scheme",
            }
            allowed = (
                {"t", "r", "rPh", "phoneticPr"}
                if parent == self.root
                else {"rPr", "t"}
                if parent == "r"
                else font
                if parent == "rPr"
                else {"t"}
                if parent == "rPh"
                else set()
            )
            if local not in allowed:
                raise ValueError("Invalid TOTUM string ancestry")
            counts[local] += 1
            if local not in ("r", "rPh") and counts[local] > 1:
                raise ValueError("Duplicate TOTUM string node")
            if parent == self.root and counts["t"] and counts["r"]:
                raise ValueError("Mixed TOTUM plain/rich string representation")
        self.frames.append((local, Counter()))

    def text(self, value: str) -> None:
        if self.frames[-1][0] != "t":
            if value.strip(" \t\r\n"):
                raise ValueError("Unexpected TOTUM string structural text")
        elif self.capture and not any(tag == "rPh" for tag, _counts in self.frames):
            self.parts.append(value)

    def end(self, name: str) -> None:
        if name != f"{_NS}}}{self.frames[-1][0]}":
            raise ValueError("Invalid TOTUM string closure")
        self.frames.pop()


def _selected_sheet(content: bytes) -> tuple[dict, int, tuple[str, ...]]:
    """Qualified direct cell children only; discard all unselected value text."""
    cells, merges, dimensions = {}, [], []
    stack = []
    current = wire = rich = None
    row = None
    row_seen, cell_seen = set(), set()
    sheet_data_count = 0
    prefix = (f"{_NS}}}worksheet",)
    row_path = prefix + (f"{_NS}}}sheetData", f"{_NS}}}row")
    cell_path = row_path + (f"{_NS}}}c",)
    structural = {
        "worksheet",
        "sheetData",
        "dimension",
        "row",
        "c",
        "v",
        "f",
        "is",
        "t",
        "r",
        "rPr",
        "rPh",
        "phoneticPr",
        "mergeCells",
        "mergeCell",
    }

    def start(name, attrs):
        nonlocal current, wire, rich, row, sheet_data_count
        stack.append(name)
        path = tuple(stack)
        local = name.rsplit("}", 1)[-1]
        if rich is not None:
            rich.start(name)
            return
        if local in structural and name != f"{_NS}}}{local}":
            raise ValueError("Foreign TOTUM worksheet observation node")
        if len(stack) == 1:
            if path != prefix:
                raise ValueError("Invalid TOTUM selected worksheet root")
        elif local == "dimension":
            if path != prefix + (name,):
                raise ValueError("Invalid TOTUM dimension ancestry")
            dimensions.append(_range(attrs["ref"])[3])
        elif local == "sheetData":
            if path != prefix + (name,):
                raise ValueError("Invalid TOTUM sheetData ancestry")
            sheet_data_count += 1
        elif local == "row":
            if path != row_path:
                raise ValueError("Invalid TOTUM row ancestry")
            value = attrs.get("r", "")
            if not re.fullmatch(r"[1-9][0-9]*", value):
                raise ValueError("Invalid TOTUM worksheet row metadata")
            row = int(value)
            if row > 1048576 or row in row_seen:
                raise ValueError("Duplicate/out-of-range TOTUM worksheet row")
            row_seen.add(row)
        elif local == "c":
            if path != cell_path or wire is not None:
                raise ValueError("Invalid/nested TOTUM cell ancestry")
            column, cell_row = _coordinate(attrs["r"])
            if row != cell_row or (cell_row, column) in cell_seen:
                raise ValueError("Duplicate or inconsistent TOTUM cell coordinate")
            cell_seen.add((cell_row, column))
            wire = {"v": False, "f": False, "is": False}
            if column <= 4:
                key = (cell_row, COLUMNS[column - 1])
                current = {
                    "key": key,
                    "type": attrs.get("t"),
                    "style": attrs.get("s"),
                    "v": None,
                    "f": None,
                    "v_seen": False,
                    "f_seen": False,
                    "inline": [],
                    "inline_seen": False,
                }
                cells[key] = current
        elif local in ("v", "f", "is"):
            if path != cell_path + (name,) or wire is None or wire[local]:
                raise ValueError("Invalid/duplicate TOTUM cell child ancestry")
            wire[local] = True
            if local == "is":
                rich = _RichText("is", current is not None)
                rich.start(name)
                if current is not None:
                    current["inline_seen"] = True
            elif current is not None:
                current[f"{local}_seen"], current[local] = True, ""
        elif local == "mergeCells":
            if path != prefix + (name,):
                raise ValueError("Invalid TOTUM merge ancestry")
        elif local == "mergeCell":
            if path != prefix + (f"{_NS}}}mergeCells", name):
                raise ValueError("Invalid TOTUM merge-cell ancestry")
            ref = attrs["ref"]
            c1, _r1, c2, r2 = _range(ref)
            if c1 <= 4 and c2 >= 1 and r2 >= 5:
                if ref in merges:
                    raise ValueError("Duplicate TOTUM selected merge")
                merges.append(ref)
        elif local in structural or wire is not None:
            raise ValueError("Invalid TOTUM observation-node ancestry")

    def text(value):
        if rich is not None:
            rich.text(value)
        elif stack[-1] in (f"{_NS}}}v", f"{_NS}}}f"):
            if current is not None:
                current[stack[-1].rsplit("}", 1)[-1]] += value
        elif (
            wire is not None
            or stack[-1]
            in {
                f"{_NS}}}{tag}"
                for tag in (
                    "worksheet",
                    "sheetData",
                    "row",
                    "dimension",
                    "mergeCells",
                    "mergeCell",
                )
            }
        ) and value.strip(" \t\r\n"):
            raise ValueError("Unexpected TOTUM worksheet structural text")

    def end(name):
        nonlocal current, wire, rich, row
        if rich is not None:
            rich.end(name)
            if not rich.frames:
                if current is not None:
                    current["inline"] = rich.parts
                rich = None
        elif name == f"{_NS}}}c":
            current = wire = None
        elif name == f"{_NS}}}row":
            row = None
        stack.pop()

    _stream(content, start, end, text)
    if len(dimensions) != 1 or sheet_data_count != 1:
        raise ValueError("Expected one TOTUM worksheet dimension/sheetData")
    return cells, dimensions[0], tuple(merges)


def _strings(content: bytes | None, wanted: set[int]) -> dict[int, str]:
    if not wanted:
        return {}
    if content is None:
        raise ValueError("Missing TOTUM selected shared strings")
    result, stack = {}, []
    index = -1
    rich = None
    root = f"{_NS}}}sst"

    def start(name, _attrs):
        nonlocal index, rich
        stack.append(name)
        local = name.rsplit("}", 1)[-1]
        if rich is not None:
            rich.start(name)
        elif len(stack) == 1:
            if name != root:
                raise ValueError("Invalid TOTUM shared-string root")
        elif local == "si":
            if tuple(stack) != (root, f"{_NS}}}si"):
                raise ValueError("Invalid TOTUM shared-string item ancestry")
            index += 1
            rich = _RichText("si", index in wanted)
            rich.start(name)
        elif local in ("sst", "t", "r", "rPr", "rPh", "phoneticPr", "v", "f", "is", "c"):
            raise ValueError("Invalid TOTUM shared-string ancestry")

    def text(value):
        if rich is not None:
            rich.text(value)
        elif stack[-1] == root and value.strip(" \t\r\n"):
            raise ValueError("Unexpected TOTUM shared-string structural text")

    def end(name):
        nonlocal rich
        if rich is not None:
            rich.end(name)
            if not rich.frames:
                if index in wanted:
                    result[index] = "".join(rich.parts)
                rich = None
        stack.pop()

    _stream(content, start, end, text)
    if set(result) != wanted:
        raise ValueError("Unresolved TOTUM selected shared string")
    return result


def _cell(item: dict, shared: dict[int, str], styles: tuple[bool, ...], merged: bool) -> RawCell:
    row, column = item["key"]
    xml_type, value = item["type"], item["v"]
    style = item["style"]
    if style is not None:
        if not re.fullmatch(r"[0-9]+", style) or int(style) >= len(styles):
            raise ValueError("Unresolved TOTUM selected cell style")
        style = int(style)
    date = styles[style or 0]
    text, numeric_kind = None, None
    if xml_type == "s":
        if value is None or not re.fullmatch(r"[0-9]+", value):
            raise ValueError("Invalid TOTUM selected shared-string reference")
        text = shared[int(value)]
    elif xml_type == "inlineStr":
        text = "".join(item["inline"])
    elif xml_type == "str":
        text = value
    if item["f_seen"]:
        kind = "formula"
    elif xml_type == "e":
        kind = "error"
    elif xml_type == "d" or (xml_type in (None, "n") and date and value is not None):
        kind = "date"
    elif xml_type == "b":
        kind = "boolean"
    elif xml_type in (None, "n") and value is None:
        kind = "blank"
    elif xml_type in ("s", "str", "inlineStr") and text is not None:
        kind = "empty_text" if not text else "text"
    elif xml_type in (None, "n") and value is not None:
        try:
            # Use ASCII OOXML number spellings, not Decimal's permissive underscore/digit cleanup.
            token = value.strip(" \t\r\n")
            if not re.fullmatch(
                r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
                r"|(?:NaN|sNaN|Infinity|Inf|INF))",
                token,
            ):
                raise InvalidOperation
            number = Decimal(token)
        except InvalidOperation:
            kind = "other_unresolved"
        else:
            kind = "numeric"
            numeric_kind = (
                "nonfinite"
                if not number.is_finite()
                else "positive_finite"
                if number > 0
                else "negative_finite"
                if number < 0
                else "zero"
            )
    else:
        kind = "other_unresolved"
    return RawCell(
        row,
        column,
        kind,
        xml_type,
        value,
        text,
        item["f_seen"],
        item["f"],
        item["v_seen"] and item["f_seen"],
        style,
        date,
        numeric_kind,
        merged,
    )


def preserve_source_rows(workbook: bytes, protocol: dict) -> PreservedRows:
    """Read only frozen A:D cells. Returned raw observations are local, not exportable rows."""
    try:
        _scope(protocol)
        with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any(
                name.startswith("/") or ".." in PurePosixPath(name).parts or "\\" in name
                for name in names
            ):
                raise ValueError("Invalid TOTUM OOXML package paths")
            root = _xml(archive.read("xl/workbook.xml"))
            if root.tag != f"{{{_NS}}}workbook":
                raise ValueError("Invalid TOTUM workbook root")
            sheets = root.findall(f"{{{_NS}}}sheets/{{{_NS}}}sheet")
            selected = [sheet for sheet in sheets if sheet.attrib.get("name") == "Table 4"]
            if len(selected) != 1:
                raise ValueError("Expected one TOTUM selected worksheet")
            relation = selected[0].attrib[f"{{{_REL}}}id"]
            relationships = _xml(archive.read("xl/_rels/workbook.xml.rels"))
            if relationships.tag != f"{{{_PACKAGE_REL}}}Relationships":
                raise ValueError("Invalid TOTUM workbook relationships root")
            matches = [
                item
                for item in relationships.findall(f"{{{_PACKAGE_REL}}}Relationship")
                if item.attrib.get("Id") == relation
            ]
            if (
                len(matches) != 1
                or matches[0].attrib.get("TargetMode") == "External"
                or matches[0].attrib.get("Type") != f"{_REL}/worksheet"
            ):
                raise ValueError("Invalid TOTUM selected worksheet relationship")
            target = matches[0].attrib["Target"]
            if "\\" in target or ".." in PurePosixPath(target).parts:
                raise ValueError("Invalid TOTUM selected worksheet path")
            path = target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target)
            if not path.startswith("xl/worksheets/"):
                raise ValueError("Invalid TOTUM selected worksheet scope")
            cells, declared_last, merges = _selected_sheet(archive.read(path))
            wanted = set()
            for item in cells.values():
                if item["type"] == "s":
                    if item["v"] is None or not re.fullmatch(r"[0-9]+", item["v"]):
                        raise ValueError("Invalid TOTUM selected shared-string reference")
                    wanted.add(int(item["v"]))
            shared = _strings(
                archive.read("xl/sharedStrings.xml") if "xl/sharedStrings.xml" in names else None,
                wanted,
            )
            styles = _date_styles(
                archive.read("xl/styles.xml") if "xl/styles.xml" in names else None
            )
            merge_ranges = [_range(ref) for ref in merges]
            observations = {}
            for key, item in cells.items():
                row, col = key
                column = COLUMNS.index(col) + 1
                merged = any(
                    c1 <= column <= c2 and r1 <= row <= r2 for c1, r1, c2, r2 in merge_ranges
                )
                observations[key] = _cell(item, shared, styles, merged)
            for coordinate, expected in HEADERS.items():
                column, row = _coordinate(coordinate)
                cell = observations.get((row, COLUMNS[column - 1]))
                if cell is None or cell.kind != "text" or cell.text != expected:
                    raise ValueError("TOTUM selected header mismatch")
            selected_last = max((row for row, _col in cells), default=4)
            last = max(declared_last, selected_last)
            rows = tuple(
                SourceRow(
                    row,
                    tuple(
                        observations.get(
                            (row, col),
                            RawCell(
                                row,
                                col,
                                "absent",
                                merged=any(
                                    c1 <= index <= c2 and r1 <= row <= r2
                                    for c1, r1, c2, r2 in merge_ranges
                                ),
                            ),
                        )
                        for index, col in enumerate(COLUMNS, 1)
                    ),
                )
                for row in range(5, last + 1)
            )
    except (
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        zipfile.BadZipFile,
        ET.ParseError,
        OverflowError,
        ValueError,
    ):
        raise ValueError("Invalid or incomplete TOTUM selected OOXML/contract") from None
    return PreservedRows(
        "Table 4", digest(workbook), declared_last, selected_last, last, rows, merges
    )


def summarize_source_rows(preserved: PreservedRows) -> dict:
    """Only type/layout counts; do not publish raw tokens or any laboratory arithmetic."""
    if type(preserved) is not PreservedRows:
        raise ValueError("TOTUM summary requires validated immutable source rows")
    kinds = {col: Counter({kind: 0 for kind in KINDS}) for col in COLUMNS}
    numeric = {col: Counter({kind: 0 for kind in NUMERIC_KINDS}) for col in ("C", "D")}
    combinations, groups = Counter(), Counter({label: 0 for label in SAFE_GROUP_LABELS})
    group_tokens, status_tokens = set(), set()
    layout = unresolved_groups = unknown_text_groups = merged_cells = 0
    empty = {"absent", "blank", "empty_text"}
    for row in preserved.rows:
        if all(cell.kind in empty for cell in row.cells):
            layout += 1
        for cell in row.cells:
            kinds[cell.column][cell.kind] += 1
            merged_cells += int(cell.merged)
            if cell.column in numeric and cell.numeric_kind is not None:
                numeric[cell.column][cell.numeric_kind] += 1
        a, b, c, d = row.cells
        combinations[f"{c.kind}|{d.kind}"] += 1
        if a.kind == "text":
            token = " ".join(a.text.split())
            if token:
                group_tokens.add(token)
            if token in groups:
                groups[token] += 1
            else:
                unknown_text_groups += 1
                unresolved_groups += 1
        else:
            unresolved_groups += 1
        if b.kind == "text" and b.text:
            status_tokens.add(b.text)
    if (
        any(sum(counts.values()) != len(preserved.rows) for counts in kinds.values())
        or sum(combinations.values()) != len(preserved.rows)
        or any(sum(numeric[col].values()) != kinds[col]["numeric"] for col in numeric)
    ):
        raise ValueError("TOTUM selected-cell accounting mismatch")
    return {
        "source_position_count": len(preserved.rows),
        "all_empty_layout_position_count": layout,
        "nonempty_source_position_count": len(preserved.rows) - layout,
        "cell_kind_counts": {col: dict(counts) for col, counts in kinds.items()},
        "raw_numeric_fpg_counts": {col: dict(counts) for col, counts in numeric.items()},
        "same_row_C_D_kind_counts": dict(sorted(combinations.items())),
        "body_merge_structure_count": len(preserved.body_merges),
        "merged_selected_body_cell_count": merged_cells,
        "group_coverage": {
            "reviewed_text_label_counts": dict(groups),
            "distinct_nonempty_text_token_count": len(group_tokens),
            "unrecognized_text_cell_count": unknown_text_groups,
            "missing_or_unresolved_group_cell_count": unresolved_groups,
            "merged_group_cell_count": sum(row.cells[0].merged for row in preserved.rows),
            "forward_fill_performed": False,
            "merged_anchor_resolution_performed": False,
        },
        "opaque_status_coverage": {"distinct_nonempty_text_token_count": len(status_tokens)},
        "verified_participant_count": None,
        "verified_clinical_pair_count": None,
        "positive_finite_means_valid_assay": False,
    }


def audit_totum_source_rows(registry: EvidenceRegistry, raw_directory: Path) -> dict:
    """Check every offline pin and frozen receipt before any selected-cell/type counting."""
    try:
        spec = registry.datasets[DATASET]
        protocol, protocol_hash = _contract(spec, "protocol")
        receipt_document, receipts_hash = _contract(spec, "receipts")
        _scope(protocol)
        if (
            spec["status"] != "derived"
            or spec["evidence_grade"] != "C"
            or spec["model_role"] != "benchmark_only"
            or spec["source_ids"] != SOURCE_IDS
            or not _exact_json(spec["analysis"], {key: protocol[key] for key in ANALYSIS_SECTIONS})
            or spec["clinical_fit_allowed"] is not False
            or spec["engine_activation_allowed"] is not False
            or protocol["receipts"]["path"] != spec["receipts_path"]
            or protocol["receipts"]["sha256"] != receipts_hash
            or type(receipt_document["schema_version"]) is not int
            or receipt_document["schema_version"] != 1
            or receipt_document["raw_distribution"] != "fetch_only"
            or receipt_document["participant_rows_redistributed"] is not False
            or set(protocol["source_pins"]) != set(SOURCE_IDS)
            or set(receipt_document["receipts"]) != set(SOURCE_IDS)
        ):
            raise ValueError("TOTUM registry/receipt role, analysis or source-set mismatch")
        access = protocol["access"]
        if (
            access["public_release"] is not True
            or access["download_enabled"] is not True
            or any(
                access[key] is not False
                for key in (
                    "confidential",
                    "embargo",
                    "credentials_or_application_used",
                    "author_contact_allowed",
                )
            )
            or access["workbook_release_license"] != "CC BY4.0"
        ):
            raise ValueError("TOTUM public-access metadata mismatch")
        contents, checks, historical_receipts = {}, {}, {}
        raw = Path(raw_directory)
        for label in SOURCE_IDS:
            pin, receipt = protocol["source_pins"][label], receipt_document["receipts"][label]
            source = registry.sources[SOURCE_IDS[label]]
            filename = pin["cache_filename"]
            started = datetime.fromisoformat(receipt["started_at_utc"])
            completed = datetime.fromisoformat(receipt["completed_at_utc"])
            expected_doi = (
                protocol["source_identity"]["release_doi"]
                if label in ("metadata", "workbook")
                else "No DOI; ClinicalTrials.govNCT04423302"
                if label == "registration"
                else protocol["source_identity"]["publication_doi"]
            )
            if (
                not isinstance(filename, str)
                or Path(filename).name != filename
                or any(char in filename for char in ("/", "\\"))
                or filename in ("", ".", "..")
                or pin["receipt_key"] != label
                or source.raw_filename != filename
                or source.sha256 != pin["sha256"]
                or receipt["sha256"] != pin["sha256"]
                or source.doi != expected_doi
                or receipt["cache_filename"] != filename
                or type(pin["size_bytes"]) is not int
                or pin["size_bytes"] <= 0
                or type(receipt["size_bytes"]) is not int
                or receipt["size_bytes"] != pin["size_bytes"]
                or source.url != pin["requested_url"]
                or source.url != receipt["requested_url"]
                or source.retrieved_at != completed
                or started.utcoffset() is None
                or completed.utcoffset() is None
                or started > completed
                or type(receipt["http_status"]) is not int
                or receipt["http_status"] != 200
                or not re.fullmatch(r"[0-9a-f]{64}", receipt["ignored_raw_receipt_sha256"])
                or receipt["final_url_signed_query_omitted"] is not (label == "workbook")
                or label == "workbook"
                and ("?" in receipt["resolved_url"] or "CC BY4.0" not in source.license)
                or receipt["content_type"] is not None
                and not isinstance(receipt["content_type"], str)
            ):
                raise ValueError("TOTUM source/receipt identity, units or provenance mismatch")
            path = raw / filename
            if _linked(raw) or _linked(path) or not path.resolve().is_relative_to(raw.resolve()):
                raise ValueError("TOTUM raw source paths must be local without symlink escape")
            content = _read(path)
            if len(content) != pin["size_bytes"] or digest(content) != pin["sha256"]:
                raise ValueError("TOTUM local source checksum/size mismatch")
            contents[label] = content
            checks[label] = {"sha256": digest(content), "size_bytes": len(content), "passed": True}
            historical_receipts[label] = {
                key: receipt[key]
                for key in (
                    "requested_url",
                    "resolved_url",
                    "started_at_utc",
                    "completed_at_utc",
                    "http_status",
                    "content_type",
                    "ignored_raw_receipt_sha256",
                    "final_url_signed_query_omitted",
                )
            }
        preserved = preserve_source_rows(contents["workbook"], protocol)
    except (KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("Incomplete or invalid TOTUM registry/contract") from exc
    return {
        "schema_version": 1,
        "analysis_id": DATASET,
        "model_role": "benchmark_only",
        "assessment": "frozen source-row/type adequacy; no clinical endpoint acceptance",
        "source_audit_passed": True,
        "clinically_adequate": False,
        "fit_ready": False,
        "scientific_release_ready": False,
        "scope": {
            "worksheet": "Table 4",
            "columns": list(COLUMNS),
            "first_source_row": 5,
            "declared_last_row": preserved.declared_last_row,
            "selected_last_row": preserved.selected_last_row,
            "scan_last_row": preserved.scan_last_row,
            "unit": "source worksheet position; not verified participant",
            "C_nominal_assessment": "Baseline",
            "D_nominal_assessment": "6 months",
            "source_fpg_unit": "mg/dL",
            "actual_times": "unknown",
            "nominal_planned_schedule_used_as_actual_interval": False,
        },
        "results": summarize_source_rows(preserved),
        "decision": {
            "integrity_and_selected_headers_passed": True,
            "source_layout_preserved": True,
            "clinical_adequacy": "unresolved",
            "clinical_fit_allowed": False,
            "engine_activation_allowed": False,
            "endpoint_distribution_accepted": False,
            "unknown_requirements": protocol["source_row_contract"]["clinical_unknowns"],
        },
        "source_conflicts": protocol["source_conflicts"],
        "failure_dispositions": protocol["failure_dispositions"],
        "provenance": {
            "protocol_sha256": protocol_hash,
            "receipts_sha256": receipts_hash,
            "source_checks": checks,
            "historical_acquisition_receipts": historical_receipts,
            "local_bytes_acquisition_time_certified": False,
            "historical_ignored_raw_receipt_files_required": False,
            "implementation_sha256": digest(Path(__file__).read_bytes()),
            "raw_redistributed": False,
            "rows_or_individual_values_exported": False,
            "clinical_fit_performed": False,
            "outcome_arithmetic_performed": False,
            "numeric_type_coverage_counting_performed": True,
            "trial_preregistration": False,
            "independent_validation": False,
        },
    }
