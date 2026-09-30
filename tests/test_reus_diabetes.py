"""Synthetic XML fixtures exercise extraction contracts, not clinical estimates."""

import copy
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from demeter.analysis.reus_diabetes import DATASET, _interval, audit_reus, extract_reported
from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry, Uncertainty


def xml_fixture(analysis, corrected):
    root = ET.Element("article")
    table = ET.SubElement(
        root, "table-wrap", id=analysis["correction_table_id" if corrected else "original_table_id"]
    )
    ET.SubElement(table, "label").text = analysis[
        "correction_table_label" if corrected else "original_table_label"
    ]
    content = ET.SubElement(table, "table")
    head = ET.SubElement(ET.SubElement(content, "thead"), "tr")
    # Source order deliberately differs from the sorted JSON object order.
    arms = ["voo", "nuts", "combined"]
    for label in ["", *(analysis["arm_headers"][arm] for arm in arms)]:
        ET.SubElement(head, "th").text = label
    body = ET.SubElement(content, "tbody")
    values = {
        "original": ["0.6 (0.3, 1.2)", "0.7 (0.4–1.1)", "0.8 (0.5, 1.3)"],
        "corrected": ["0.9 (0.6, 1.2)", "1.1 (0.8−1.4)", "1.2 (0.9, 1.5)"],
    }
    models = (
        analysis["correction_rows"] if corrected else {"original": analysis["original_report_row"]}
    )
    for model, label in models.items():
        row = ET.SubElement(body, "tr")
        ET.SubElement(row, "td").text = label
        for value in values[model]:
            ET.SubElement(row, "td").text = value
    row = ET.SubElement(body, "tr")
    ET.SubElement(row, "td").text = "Unselected subgroup"
    for value in ["0.1 (0.01, 0.2)"] * 3:
        ET.SubElement(row, "td").text = value
    return ET.tostring(root, encoding="utf-8")


def analysis_fixture():
    return copy.deepcopy(
        EvidenceRegistry.from_yaml("evidence/parameters.yaml").datasets[DATASET]["analysis"]
    )


def audit_fixture(tmp_path, monkeypatch):
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    spec = registry.datasets[DATASET]
    protocol = json.loads(Path(spec["protocol_path"]).read_bytes())
    paths = {}
    for name, source_id in [
        ("original", spec["original_source_id"]),
        ("correction", spec["source_id"]),
    ]:
        content = xml_fixture(spec["analysis"], corrected=name == "correction")
        paths[name] = tmp_path / registry.sources[source_id].raw_filename
        paths[name].write_bytes(content)
        registry.sources[source_id].sha256 = digest(content)
        protocol["source_pins"][name]["sha256"] = digest(content)
    protocol_path = tmp_path / "synthetic-protocol.json"
    protocol_path.write_bytes(encoded(protocol))
    spec.update(
        protocol_path=str(protocol_path), protocol_sha256=digest(protocol_path.read_bytes())
    )
    extracted = extract_reported(
        paths["correction"].read_bytes(), paths["original"].read_bytes(), spec["analysis"]
    )
    for model, arms in extracted["models"].items():
        for arm, (point, low, high) in arms.items():
            parameter = registry.parameters[f"reus_{model}_{arm}_diabetes_hr"]
            parameter.value = point
            parameter.uncertainty = Uncertainty(
                kind="interval", low=low, high=high, rationale="Synthetic source fixture"
            )
    monkeypatch.setattr(
        "demeter.analysis.pathway_compatibility.audit_compatibility",
        lambda r: {"results": {"software_witnesses_passed": True}, "clinical_effect_used": False},
    )
    return registry, paths


def test_exact_arm_labels_prevent_column_swaps_and_keep_null_intervals():
    analysis = analysis_fixture()
    result = extract_reported(xml_fixture(analysis, True), xml_fixture(analysis, False), analysis)
    assert result["models"]["original"]["voo"] == (0.6, 0.3, 1.2)
    assert result["models"]["original"]["nuts"] == (0.7, 0.4, 1.1)
    assert result["models"]["corrected"]["combined"] == (1.2, 0.9, 1.5)
    assert sum(len(arms) for arms in result["models"].values()) == 6
    assert all(result["original_report_agreement"].values())


@pytest.mark.parametrize(
    "cell",
    [
        "0 (0, 1)",
        "-1 (0.1, 1)",
        "nan (0.1, 1)",
        "1 (2, 3)",
        "1 (1, 1)",
        "1 [0.1, 2]",
        "1e300 (0.1, 2)",
    ],
)
def test_malformed_or_invalid_intervals_rejected(cell):
    with pytest.raises(ValueError):
        _interval(cell)


@pytest.mark.parametrize(
    "change",
    ["duplicate_table", "duplicate_row", "missing_row", "header", "label", "malformed_xml"],
)
def test_source_shape_drift_cannot_reproduce(change):
    analysis = analysis_fixture()
    content = xml_fixture(analysis, True)
    root = ET.fromstring(content)
    body = root.find(".//tbody")
    if change == "duplicate_table":
        root.append(copy.deepcopy(root[0]))
    elif change == "duplicate_row":
        body.append(copy.deepcopy(body[0]))
    elif change == "missing_row":
        body.remove(body[0])
    elif change == "header":
        root.find(".//thead/tr")[1].text = "Wrong comparison"
    elif change == "label":
        root.find(".//label").text = "Wrong table"
    content = b"<broken" if change == "malformed_xml" else ET.tostring(root)
    with pytest.raises(ValueError):
        extract_reported(content, xml_fixture(analysis, False), analysis)


def test_audit_preserves_scoped_results_and_does_not_invent_difference_uncertainty(
    tmp_path, monkeypatch
):
    registry, paths = audit_fixture(tmp_path, monkeypatch)
    before = registry.model_dump(mode="json")
    report = audit_reus(registry, paths["correction"])
    assert report["results"]["source_reproduction_passed"]
    assert report["model_role"] == "benchmark_only"
    assert not report["scientific_release_ready"]
    assert not report["support_decision"]["engine_activation_permitted"]
    assert all(
        value["difference_uncertainty"] is None
        for value in report["results"]["original_corrected_changes"].values()
    )
    assert all(
        value["reported_interval_includes_ratio_null"]
        for arms in report["results"]["benchmarks"].values()
        for value in arms.values()
    )
    assert registry.model_dump(mode="json") == before


def test_original_article_disagreement_is_retained_as_failed_source_check(tmp_path, monkeypatch):
    registry, paths = audit_fixture(tmp_path, monkeypatch)
    content = paths["original"].read_bytes().replace(b"0.6 (0.3, 1.2)", b"0.5 (0.3, 1.2)")
    paths["original"].write_bytes(content)
    spec = registry.datasets[DATASET]
    registry.sources[spec["original_source_id"]].sha256 = digest(content)
    protocol_path = Path(spec["protocol_path"])
    protocol = json.loads(protocol_path.read_bytes())
    protocol["source_pins"]["original"]["sha256"] = digest(content)
    protocol_path.write_bytes(encoded(protocol))
    spec["protocol_sha256"] = digest(protocol_path.read_bytes())
    report = audit_reus(registry, paths["correction"])
    assert not report["results"]["source_reproduction_passed"]
    assert not report["results"]["original_report_agreement"]["voo"]


@pytest.mark.parametrize(
    "change",
    [
        "protocol",
        "analysis",
        "source",
        "raw_bytes",
        "missing_parameter",
        "parameter_role",
        "parameter_coverage",
        "parameter_value",
    ],
)
def test_contract_drift_is_rejected_or_failed_never_silently_rewritten(
    tmp_path, monkeypatch, change
):
    registry, paths = audit_fixture(tmp_path, monkeypatch)
    spec = registry.datasets[DATASET]
    if change == "protocol":
        Path(spec["protocol_path"]).write_bytes(b"{}")
    elif change == "analysis":
        spec["analysis"]["ratio_null"] = 0
    elif change == "source":
        registry.sources[spec["source_id"]].sha256 = "0" * 64
    elif change == "raw_bytes":
        paths["correction"].write_bytes(b"<changed/>")
    elif change == "missing_parameter":
        del registry.parameters["reus_corrected_voo_diabetes_hr"]
    elif change == "parameter_role":
        registry.parameters["reus_corrected_voo_diabetes_hr"].model_role = "health_model"
    elif change == "parameter_coverage":
        spec["parameter_keys"].pop()
    elif change == "parameter_value":
        registry.parameters["reus_corrected_voo_diabetes_hr"].value = 0.8
        report = audit_reus(registry, paths["correction"])
        assert not report["results"]["source_reproduction_passed"]
        assert registry.parameters["reus_corrected_voo_diabetes_hr"].value == 0.8
        return
    with pytest.raises(ValueError):
        audit_reus(registry, paths["correction"])


def test_cli_missing_source_does_not_download(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: pytest.fail("Implicit download"))
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "reus-diabetes",
            "--correction",
            str(tmp_path / "missing.xml"),
            "--original",
            str(tmp_path / "original.xml"),
        ],
    )
    assert result.exit_code == 1
    assert "missing.xml" in result.output


@pytest.mark.parametrize("passed", [True, False])
def test_cli_writes_source_receipt_before_exit(tmp_path, monkeypatch, passed):
    report = {
        "results": {"source_reproduction_passed": passed},
        "compatibility_diagnostic": {"results": {"software_witnesses_passed": True}},
    }
    monkeypatch.setattr("demeter.analysis.reus_diabetes.audit_reus", lambda *a: report)
    output = tmp_path / "report.json"
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "reus-diabetes",
            "--correction",
            "correction.xml",
            "--original",
            "original.xml",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == (0 if passed else 1)
    assert json.loads(output.read_bytes()) == report


def test_offline_compatibility_cli_runs_without_source_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: pytest.fail("Implicit download"))
    output = tmp_path / "compatibility.json"
    result = CliRunner().invoke(app, ["evidence", "pathway-compatibility", "--output", str(output)])
    assert result.exit_code == 0
    report = json.loads(output.read_bytes())
    assert report["results"]["software_witnesses_passed"]
    assert not report["results"]["clinical_effect_used"]
