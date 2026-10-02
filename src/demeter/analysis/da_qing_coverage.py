"""Literal Da Qing aggregate extraction; no clinical rate or causal fit."""

from __future__ import annotations

import hashlib
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
import re
import json
from pathlib import Path

from demeter.schema import EvidenceRegistry

SOURCE_ID = "da_qing2016_mortality_publication"
DATASET = "da_qing_source_coverage"
SCIENTIFIC_GATES = frozenset(
    (
        "clinical_fit_allowed",
        "engine_activation_allowed",
        "scientific_release_ready",
        "independent_validation",
    )
)
AGES = ("25–59", "60–69", "≥70")
DURATIONS = ("0–5", "5–10", "10–15", "≥15")
GROUPS = {
    "before_diagnosis": "Time before onset of diabetes (years)",
    "after_diagnosis": "Diabetes duration (years)",
}


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            if self.row is not None:
                raise ValueError("Nested source table row")
            self.row = []
        elif tag in ("td", "th"):
            if self.row is None or self.cell is not None:
                raise ValueError("Invalid source table cell")
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            if self.cell is None or self.row is None:
                raise ValueError("Invalid source table end cell")
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr":
            if self.row is None or self.cell is not None:
                raise ValueError("Invalid source table end row")
            self.rows.append(self.row)
            self.row = None


def _section(source: str, identifier: str) -> str:
    parts = re.findall(
        rf'<section\b[^>]*\bid="{re.escape(identifier)}"[^>]*>(.*?)</section>',
        source,
        flags=re.S,
    )
    if len(parts) != 1:
        raise ValueError("Selected source section missing or duplicated")
    return parts[0]


def _rows(source: str, identifier: str, kind: str) -> list[list[str]]:
    section = _section(source, identifier)
    parts = re.findall(rf"<{kind}\b[^>]*>(.*?)</{kind}>", section, flags=re.S)
    if len(parts) != 1:
        raise ValueError("Selected source table structure missing or duplicated")
    parser = _TableParser()
    parser.feed(parts[0])
    parser.close()
    if parser.row is not None or parser.cell is not None:
        raise ValueError("Truncated source table")
    return parser.rows


def _pair(literal: str, locator: str) -> dict:
    # Comma grouping and an integer display are source-format constraints,
    # not a claim that displayed person-years are exact individual exposure.
    match = re.fullmatch(r"(0|[1-9][0-9]*)/([1-9][0-9]{0,2}(?:,[0-9]{3})*|[1-9][0-9]*)", literal)
    if match is None:
        raise ValueError("Selected death/person-year cell has unsupported format")
    return {
        "deaths": int(match[1]),
        "person_years": int(match[2].replace(",", "")),
        "source_literal": literal,
        "source_locator": locator,
    }


def extract_reported(content: bytes, protocol: dict) -> dict:
    """Extract publication-level aggregates only, after verifying exact bytes."""
    pin = protocol["source"]
    if (
        type(content) is not bytes
        or len(content) != pin["size_bytes"]
        or hashlib.sha256(content).hexdigest() != pin["sha256"]
    ):
        raise ValueError("Da Qing source checksum or size mismatch")
    if protocol["source_id"] != SOURCE_ID or pin["doi"] != "10.2337/dc16-0429":
        raise ValueError("Da Qing protocol source identity mismatch")
    source = content.decode("utf8")
    if not re.search(r'<meta\s+name="citation_doi"\s+content="10\.2337/dc16-0429"', source):
        raise ValueError("Da Qing article identity mismatch")
    if (
        "© 2016 by the American Diabetes Association." not in source
        or "the use is educational and not for profit" not in source
    ):
        raise ValueError("Da Qing article rights notice mismatch")
    section = _section(source, "T2")
    if "Death rates (per 1,000 person-years) before and after the onset of diabetes" not in section:
        raise ValueError("Da Qing selected table caption mismatch")
    headers = _rows(source, "T2", "thead")
    if len(headers) != 3 or headers[1][:4] != [*AGES, "All ages"]:
        raise ValueError("Da Qing age-column identity mismatch")
    rows = _rows(source, "T2", "tbody")
    if len(rows) != 12 or any(len(row) != 10 for row in rows):
        raise ValueError("Da Qing selected table row layout mismatch")
    blocks = {}
    for block_index, (key, label) in enumerate(GROUPS.items()):
        base = block_index * 6
        if rows[base][0] != label or rows[base + 5][0] != "Total":
            raise ValueError("Da Qing time-block identity mismatch")
        selected = {}
        for index, duration in enumerate(DURATIONS, start=1):
            row = rows[base + index]
            if row[0] != duration:
                raise ValueError("Da Qing time-row identity mismatch")
            selected[duration] = {
                age: _pair(
                    row[column],
                    f"Table 2 #T2/tbody/tr[{base + index + 1}]/td[{column + 1}]",
                )
                for age, column in zip((*AGES, "All ages"), (1, 3, 5, 7), strict=True)
            }
        totals = {
            age: _pair(
                rows[base + 5][column],
                f"Table 2 #T2/tbody/tr[{base + 6}]/td[{column + 1}]",
            )
            for age, column in zip((*AGES, "All ages"), (1, 3, 5, 7), strict=True)
        }
        blocks[key] = {"source_group_label": label, "rows": selected, "totals": totals}
    cohort_headers = _rows(source, "T1", "thead")
    if len(cohort_headers) != 2 or len(cohort_headers[1]) != 4:
        raise ValueError("Da Qing cohort table layout mismatch")
    cohort = []
    expected = ("0–10", "10–20", ">20 or never")
    for label, cell in zip(expected, cohort_headers[1][:3], strict=True):
        match = re.fullmatch(re.escape(label) + r" \(n = ([0-9]+)\)", cell)
        if match is None:
            raise ValueError("Da Qing diagnosis-time cohort header mismatch")
        cohort.append({"source_label": label, "n": int(match[1])})
    death_rows = [row for row in _rows(source, "T1", "tbody") if row[0] == "Death, n (%)"]
    if len(death_rows) != 1 or len(death_rows[0]) != 5:
        raise ValueError("Da Qing cohort death row missing or duplicated")
    for row, cell in zip(cohort, death_rows[0][1:4], strict=True):
        death = re.fullmatch(r"([0-9]+) \([0-9]+\.[0-9]+\)", cell)
        if death is None:
            raise ValueError("Da Qing cohort death count format mismatch")
        row["deaths"] = int(death[1])
    text = " ".join(unescape(re.sub(r"<[^>]+>", " ", source)).split())
    narrative = re.findall(
        r"participants \(([0-9]+) of ([0-9]+); 79\.0%\) developed type 2 diabetes", text
    )
    if len(narrative) != 1:
        raise ValueError("Da Qing selected incident-diabetes narrative missing or duplicated")
    death_narrative = re.findall(r"and ([0-9]+) died, with an overall death rate", text)
    if len(death_narrative) != 1:
        raise ValueError("Da Qing selected total-deaths narrative missing or duplicated")
    return {
        "source_id": SOURCE_ID,
        "death_exposure_table": blocks,
        "diagnosis_time_cohort_counts": cohort,
        "narrative_incident_diabetes_n": int(narrative[0][0]),
        "narrative_followed_cohort_n": int(narrative[0][1]),
        "narrative_deaths_n": int(death_narrative[0]),
        "narrative_source_locator": "Results, paragraph beginning 'The vital status'; (428 of 542; 79.0%)",
    }


def audit_reported(reported: dict) -> dict:
    """Retain failed checks; descriptive arithmetic never confers admission."""
    if reported["source_id"] != SOURCE_ID:
        raise ValueError("Da Qing observation source identity mismatch")
    checks = []
    blocks = reported["death_exposure_table"]
    if set(blocks) != set(GROUPS):
        raise ValueError("Da Qing extracted blocks missing or duplicated")
    for key in GROUPS:
        block = blocks[key]
        if set(block["rows"]) != set(DURATIONS) or set(block["totals"]) != {*AGES, "All ages"}:
            raise ValueError("Da Qing extracted age/time coverage mismatch")
        for duration in DURATIONS:
            row = block["rows"][duration]
            if set(row) != {*AGES, "All ages"}:
                raise ValueError("Da Qing extracted age cells missing or duplicated")
            for age in (*AGES, "All ages"):
                for field in ("deaths", "person_years"):
                    value = row[age][field]
                    if type(value) is not int or value < (1 if field == "person_years" else 0):
                        raise ValueError("Da Qing count/exposure must be displayed integers")
            for field in ("deaths", "person_years"):
                checks.append(
                    {
                        "id": f"{key}/{duration}/{field}/row_total",
                        "passed": sum(row[age][field] for age in AGES) == row["All ages"][field],
                    }
                )
        for age in (*AGES, "All ages"):
            for field in ("deaths", "person_years"):
                value = block["totals"][age][field]
                if type(value) is not int or value < (1 if field == "person_years" else 0):
                    raise ValueError("Da Qing total count/exposure must be displayed integers")
                checks.append(
                    {
                        "id": f"{key}/{age}/{field}/column_total",
                        "passed": sum(block["rows"][d][age][field] for d in DURATIONS) == value,
                    }
                )
    cohorts = reported["diagnosis_time_cohort_counts"]
    if (
        len(cohorts) != 3
        or [row["source_label"] for row in cohorts] != ["0–10", "10–20", ">20 or never"]
        or any(type(row["n"]) is not int or row["n"] < 1 for row in cohorts)
        or any(
            type(row["deaths"]) is not int or not 0 <= row["deaths"] <= row["n"] for row in cohorts
        )
        or type(reported["narrative_incident_diabetes_n"]) is not int
        or type(reported["narrative_followed_cohort_n"]) is not int
        or type(reported["narrative_deaths_n"]) is not int
    ):
        raise ValueError("Da Qing cohort counts have invalid schema")
    if (
        reported["narrative_followed_cohort_n"] <= 0
        or not 0 <= reported["narrative_incident_diabetes_n"] <= reported["narrative_followed_cohort_n"]
        or not 0 <= reported["narrative_deaths_n"] <= reported["narrative_followed_cohort_n"]
    ):
        raise ValueError("Da Qing narrative counts exceed cohort bounds")
    checks.append(
        {
            "id": "diagnosis_time_cohort_partition",
            "passed": sum(row["n"] for row in cohorts) == reported["narrative_followed_cohort_n"],
        }
    )
    checks.extend(
        [
            {
                "id": "diagnosis_time_cohort_deaths_equal_narrative",
                "passed": sum(row["deaths"] for row in cohorts) == reported["narrative_deaths_n"],
            },
            {
                "id": "before_after_deaths_equal_narrative",
                "passed": sum(blocks[key]["totals"]["All ages"]["deaths"] for key in GROUPS)
                == reported["narrative_deaths_n"],
            },
        ]
    )
    diagnosed_by_twenty = sum(row["n"] for row in cohorts[:2])
    source_discrepancy = {
        "id": "incident_diabetes_narrative_covers_first_two_time_groups",
        "passed": reported["narrative_incident_diabetes_n"] >= diagnosed_by_twenty,
        "narrative_incident_diabetes_n": reported["narrative_incident_diabetes_n"],
        "first_two_time_groups_n": diagnosed_by_twenty,
        "disposition": "Unreconciled source-level count discrepancy; no value corrected or substituted",
    }
    return {
        "kind": "da_qing_literal_aggregate_source_audit",
        "source_id": SOURCE_ID,
        "table_arithmetic_checks": checks,
        "table_arithmetic_passed": all(check["passed"] for check in checks),
        "source_consistency_check": source_discrepancy,
        "source_consistency_passed": all(check["passed"] for check in checks)
        and source_discrepancy["passed"],
        "selected_age_time_cells": len(GROUPS) * len(DURATIONS) * len(AGES),
        "model_role": "benchmark_only",
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "scientific_release_ready": False,
        "independent_validation": False,
        "uncertainty": "No likelihood or independent draws assigned to repeated person-time or clinic clusters",
    }


def verify_registered(
    registry: EvidenceRegistry, root: Path, article_cache: Path | None = None
) -> dict:
    """Verify pinned authored observations and keep source inconsistency visible."""
    spec = registry.datasets[DATASET]
    if (
        spec["model_role"] != "benchmark_only"
        or spec["source_id"] != SOURCE_ID
        or spec["parameter_keys"] != []
        or any(spec.get(key) is not False for key in SCIENTIFIC_GATES - {"independent_validation"})
    ):
        raise ValueError("Da Qing registry observation scope mismatch")
    documents = {}
    for label in ("protocol", "coverage"):
        path = Path(spec[f"{label}_path"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Da Qing artifact path outside project")
        content = (root / path).read_bytes()
        if hashlib.sha256(content).hexdigest() != spec[f"{label}_sha256"]:
            raise ValueError("Da Qing registered artifact checksum mismatch")
        documents[label] = json.loads(content)
    protocol, coverage = documents["protocol"], documents["coverage"]
    source = registry.sources[SOURCE_ID]
    if (
        protocol["source_id"] != SOURCE_ID
        or coverage["source_id"] != SOURCE_ID
        or coverage["protocol_sha256"] != spec["protocol_sha256"]
        or protocol["source"]["sha256"] != source.sha256
        or protocol["source"]["url"] != source.url
        or protocol["source"]["doi"] != source.doi
        or protocol["source"]["pmcid"] != "PMC5001147"
        or datetime.fromisoformat(protocol["source"]["retrieved_at_utc"]) != source.retrieved_at
        or coverage["model_role"] != "benchmark_only"
        or set(protocol["scientific_gates"]) != SCIENTIFIC_GATES
        or any(value is not False for value in protocol["scientific_gates"].values())
    ):
        raise ValueError("Da Qing registered source or scientific scope mismatch")
    receipt = coverage["actual_source_receipt"]
    if (
        receipt["sha256"] != source.sha256
        or receipt["url"] != source.url
        or receipt["bytes"] != protocol["source"]["size_bytes"]
        or receipt["expected_content_verified"] is not True
        or receipt["status"] != 200
        or receipt["content_type"] != "text/html; charset=utf-8"
        or receipt["final_url"] != source.url
        or receipt["doi"] != source.doi
        or receipt["citation"] != source.citation
        or receipt["raw_filename"] != source.raw_filename
        or receipt["license"] != source.license
        or datetime.fromisoformat(receipt["retrieved_at_utc"]) != source.retrieved_at
    ):
        raise ValueError("Da Qing primary acquisition receipt mismatch")
    report = audit_reported(coverage["observations"])
    if report != coverage["audit"]:
        raise ValueError("Da Qing committed audit does not reproduce")
    acquired_reproduction = None
    if article_cache is not None:
        acquired_reproduction = (
            extract_reported(article_cache.read_bytes(), protocol) == coverage["observations"]
        )
        if not acquired_reproduction:
            raise ValueError("Da Qing committed observations differ from pinned article")
    return {
        **report,
        "authored_artifact_verified": True,
        "pinned_article_reproduction_verified": acquired_reproduction,
        "provenance": {
            "registry_sha256": registry.content_hash,
            "protocol_sha256": spec["protocol_sha256"],
            "coverage_sha256": spec["coverage_sha256"],
            "source_sha256": source.sha256,
        },
    }
