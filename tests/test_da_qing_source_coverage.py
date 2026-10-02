"""Synthetic table parser checks and pinned public aggregate audit replay."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from demeter.analysis import da_qing_coverage as module
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/validation/da-qing-source-audit-protocol-v1.json"
COVERAGE = ROOT / "docs/validation/da-qing-source-coverage-v1.json"


def _synthetic_html() -> bytes:
    """Arbitrary software counts/exposures, not another empirical source."""
    blocks = []
    for label in module.GROUPS.values():
        rows = ["<tr><td>" + escape(label) + "</td>" + "<td></td>" * 9 + "</tr>"]
        for duration in module.DURATIONS:
            cells = [
                duration,
                "1/100",
                "unused",
                "1/100",
                "unused",
                "1/100",
                "unused",
                "3/300",
                "unused",
                "unused",
            ]
            rows.append(
                "<tr>" + "".join("<td>" + escape(cell) + "</td>" for cell in cells) + "</tr>"
            )
        cells = [
            "Total",
            "4/400",
            "unused",
            "4/400",
            "unused",
            "4/400",
            "unused",
            "12/1,200",
            "unused",
            "unused",
        ]
        rows.append("<tr>" + "".join("<td>" + escape(cell) + "</td>" for cell in cells) + "</tr>")
        blocks.extend(rows)
    return (
        '<meta name="citation_doi" content="10.2337/dc16-0429">'
        "© 2016 by the American Diabetes Association. the use is educational and not for profit"
        '<section id="T1"><thead><tr><th></th><th>Time to progression to diabetes (years)</th></tr>'
        "<tr><th>0–10 (n = 10)</th><th>10–20 (n = 15)</th><th>&gt;20 or never (n = 15)</th><th>P value</th></tr></thead>"
        "<tbody><tr><td>Death, n (%)</td><td>8 (80.0)</td><td>8 (53.3)</td><td>8 (53.3)</td><td></td></tr></tbody></section>"
        '<section id="T2"><p>Death rates (per 1,000 person-years) before and after the onset of diabetes</p>'
        "<thead><tr><th>Age-group</th></tr><tr><th>25–59</th><th>60–69</th><th>≥70</th><th>All ages</th></tr>"
        "<tr><th>n/person-years</th></tr></thead><tbody>"
        + "".join(blocks)
        + "</tbody></section><p>participants (30 of 40; 79.0%) developed type 2 diabetes and 24 died, with an overall death rate</p>"
    ).encode("utf8")


def _protocol(content: bytes) -> dict:
    result = json.loads(PROTOCOL.read_bytes())
    result["source"]["size_bytes"] = len(content)
    result["source"]["sha256"] = hashlib.sha256(content).hexdigest()
    return result


def test_committed_source_failures_are_preserved():
    coverage = json.loads(COVERAGE.read_bytes())
    audit = module.audit_reported(coverage["observations"])
    assert audit == coverage["audit"]
    assert audit["selected_age_time_cells"] == 24
    assert audit["table_arithmetic_passed"] is True
    assert audit["source_consistency_passed"] is False
    assert audit["source_consistency_check"]["narrative_incident_diabetes_n"] == 428
    assert audit["source_consistency_check"]["first_two_time_groups_n"] == 437
    assert all(
        audit[key] is False
        for key in (
            "clinical_fit_allowed",
            "engine_activation_allowed",
            "scientific_release_ready",
            "independent_validation",
        )
    )


def test_synthetic_parser_and_arithmetic():
    content = _synthetic_html()
    result = module.extract_reported(content, _protocol(content))
    audit = module.audit_reported(result)
    assert audit["table_arithmetic_passed"] is True
    assert audit["source_consistency_passed"] is True
    assert (
        result["death_exposure_table"]["after_diagnosis"]["totals"]["All ages"]["person_years"]
        == 1200
    )
    selected = result["death_exposure_table"]["before_diagnosis"]["rows"]["0–5"]["25–59"]
    assert selected == {
        "deaths": 1,
        "person_years": 100,
        "source_literal": "1/100",
        "source_locator": "Table 2 #T2/tbody/tr[2]/td[2]",
    }


@pytest.mark.parametrize(
    "before,after,message",
    [
        ("10.2337/dc16-0429", "10.2337/dc16-0428", "article identity"),
        ("25–59", "25–60", "age-column"),
        ("Diabetes duration (years)", "Time since screening (years)", "time-block"),
        ("≥15", "≥16", "time-row"),
        ("1/100", "1/0", "unsupported format"),
        ("1/100", "1/10.0", "unsupported format"),
        ("1/100", "1/1,00", "unsupported format"),
        ("0–10 (n = 10)", "0–11 (n = 10)", "cohort header"),
        ("educational and not for profit", "unrestricted", "rights notice"),
    ],
)
def test_semantic_source_changes_fail_after_outer_repin(before, after, message):
    content = _synthetic_html().decode("utf8").replace(before, after).encode("utf8")
    with pytest.raises(ValueError, match=message):
        module.extract_reported(content, _protocol(content))


def test_source_checksum_changes_are_rejected():
    content = _synthetic_html()
    with pytest.raises(ValueError, match="checksum"):
        module.extract_reported(content + b" ", _protocol(content))


def test_corrupt_source_arithmetic_is_failed_not_repaired():
    content = _synthetic_html().replace(b"3/300", b"4/300", 1)
    reported = module.extract_reported(content, _protocol(content))
    result = module.audit_reported(reported)
    assert result["table_arithmetic_passed"] is False
    assert result["source_consistency_passed"] is False
    assert (
        reported["death_exposure_table"]["before_diagnosis"]["rows"]["0–5"]["All ages"]["deaths"]
        == 4
    )


@pytest.mark.parametrize("bad", [True, -1, 1.5, "1"])
def test_invalid_count_is_not_coerced(bad):
    content = _synthetic_html()
    reported = module.extract_reported(content, _protocol(content))
    reported["death_exposure_table"]["before_diagnosis"]["rows"]["0–5"]["25–59"]["deaths"] = bad
    with pytest.raises(ValueError, match="displayed integers"):
        module.audit_reported(reported)


def test_missing_age_cell_is_not_silent_zero():
    content = _synthetic_html()
    reported = module.extract_reported(content, _protocol(content))
    del reported["death_exposure_table"]["before_diagnosis"]["rows"]["0–5"]["25–59"]
    with pytest.raises(ValueError, match="missing or duplicated"):
        module.audit_reported(reported)


def test_registry_replay_and_gate_boundary():
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    result = module.verify_registered(registry, ROOT)
    assert result["authored_artifact_verified"] is True
    assert result["pinned_article_reproduction_verified"] is None
    assert result["source_consistency_passed"] is False
    altered = copy.deepcopy(registry)
    altered.datasets[module.DATASET]["parameter_keys"] = ["unjustified_clinical_rate"]
    with pytest.raises(ValueError, match="observation scope"):
        module.verify_registered(altered, ROOT)


def test_protocol_timestamp_and_publication_scope():
    protocol = json.loads(PROTOCOL.read_bytes())
    coverage = json.loads(COVERAGE.read_bytes())
    assert coverage["protocol_sha256"] == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert protocol["chronology"].endswith("not preregistration or independent validation")
    assert protocol["source"]["cache_disposition"].startswith("fetch_only")
    assert coverage["actual_source_receipt"]["participant_data"] is False


def _repinned_documents(tmp_path, operation):
    """Test semantic guards even when artifact metadata is coherently rehashed."""
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    protocol = json.loads(PROTOCOL.read_bytes())
    coverage = json.loads(COVERAGE.read_bytes())
    operation(protocol, coverage)
    selected = tmp_path / "docs/validation"
    selected.mkdir(parents=True)
    protocol_bytes = (json.dumps(protocol, ensure_ascii=False) + "\n").encode("utf8")
    coverage["protocol_sha256"] = hashlib.sha256(protocol_bytes).hexdigest()
    coverage_bytes = (json.dumps(coverage, ensure_ascii=False) + "\n").encode("utf8")
    (selected / PROTOCOL.name).write_bytes(protocol_bytes)
    (selected / COVERAGE.name).write_bytes(coverage_bytes)
    registry.datasets[module.DATASET]["protocol_sha256"] = hashlib.sha256(
        protocol_bytes
    ).hexdigest()
    registry.datasets[module.DATASET]["coverage_sha256"] = hashlib.sha256(
        coverage_bytes
    ).hexdigest()
    return registry


@pytest.mark.parametrize(
    "gates",
    [
        {},
        {"clinical_fit_allowed": False},
        {key: 0 for key in module.SCIENTIFIC_GATES},
        {key: "false" for key in module.SCIENTIFIC_GATES},
    ],
)
def test_empty_or_nonboolean_scientific_gates_fail(tmp_path, gates):
    registry = _repinned_documents(tmp_path, lambda p, c: p.update(scientific_gates=gates))
    with pytest.raises(ValueError, match="scientific scope"):
        module.verify_registered(registry, tmp_path)


@pytest.mark.parametrize(
    "key,value",
    [
        ("doi", "10.2337/not-the-selected-paper"),
        ("citation", "Different publication"),
        ("raw_filename", "different-file.html"),
        ("license", "unrestricted"),
        ("retrieved_at_utc", "2026-10-01T14:38:52.750834+00:00"),
        ("bytes", 175380),
        ("content_type", "application/pdf"),
    ],
)
def test_receipt_provenance_mismatch_fails_after_repin(tmp_path, key, value):
    registry = _repinned_documents(
        tmp_path, lambda p, c: c["actual_source_receipt"].update({key: value})
    )
    with pytest.raises(ValueError, match="receipt mismatch"):
        module.verify_registered(registry, tmp_path)


def test_registry_zero_does_not_mean_false():
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    registry.datasets[module.DATASET]["clinical_fit_allowed"] = 0
    with pytest.raises(ValueError, match="observation scope"):
        module.verify_registered(registry, ROOT)


@pytest.mark.parametrize(
    "key,value",
    [
        ("narrative_incident_diabetes_n", -1),
        ("narrative_incident_diabetes_n", 543),
        ("narrative_deaths_n", -1),
        ("narrative_deaths_n", 543),
        ("narrative_followed_cohort_n", 0),
        ("narrative_followed_cohort_n", -1),
    ],
)
def test_impossible_narrative_counts_cannot_pass_source_consistency(key, value):
    reported = json.loads(COVERAGE.read_bytes())["observations"]
    reported[key] = value
    with pytest.raises(ValueError, match="cohort bounds"):
        module.audit_reported(reported)
