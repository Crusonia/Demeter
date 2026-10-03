"""Independent source-cell fixtures and drift/semantic checks; never patient data."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

import demeter.data.update_biomarker as module
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def package(tmp_path):
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    target = tmp_path / module.SUMMARY_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / module.SUMMARY_PATH).read_bytes())
    return registry, tmp_path


def test_checked_cells_preserve_display_units_pair_counts_and_missing_uncertainty(package):
    registry, root = package
    result = module.audit_update_biomarker(registry, root)
    # Independently visually checked Table 5 PDF12 reference cells, not generated
    # by the parser. Different paired and diet Ns prevent marginal subtraction.
    expected = {
        "hba1c": [(46, "-0.08", "0.0"), (47, "-0.03", "0.0"), (45, "-0.05", "0.0")],
        "fasting_glucose": [(46, "-0.09", "0.1"), (46, "-0.14", "0.1"), (44, "0.04", "0.1")],
    }
    for endpoint, triples in expected.items():
        groups = result["endpoints"][endpoint]["groups"]
        assert [
            (groups[g]["n"], groups[g]["mean_display"], groups[g]["reported_se_display"])
            for g in module.GROUPS
        ] == triples
        for group in groups.values():
            assert group["sampling_distribution"] is None
            assert group["confidence_interval"] is None
    assert result["endpoints"]["hba1c"]["change_unit"] == "percentage_points"
    assert result["endpoints"]["fasting_glucose"]["change_unit"] == "mmol/L"
    glucose = result["endpoints"]["fasting_glucose"]["groups"]
    assert glucose["paired_mpf_minus_upf"]["mean"] != pytest.approx(
        glucose["mpf"]["mean"] - glucose["upf"]["mean"]
    )
    missing = set(registry.audit()["missing_uncertainty"])
    assert {
        key
        for key in module.parameter_keys()
        if not key.endswith("_n") and key != "update_table5_followup_weeks"
    } <= missing


def test_transformations_match_endpoint_and_quantity_units(package):
    registry, _ = package
    for key in module.parameter_keys():
        parameter = registry.parameters[key]
        transformation = parameter.transformation
        if key == "update_table5_followup_weeks":
            assert parameter.unit == "weeks"
            assert "assessment window in weeks" in transformation
            assert "HbA1c" not in transformation
        elif key.endswith("_n"):
            assert parameter.unit == "persons"
            assert "sample-count N in persons" in transformation
            assert "unit conversion" in transformation
            assert "percentage_points" not in transformation
            assert "HbA1c" not in transformation
        elif "fasting_glucose" in key:
            assert parameter.unit == "mmol/L"
            assert "fasting-glucose change value in mmol/L" in transformation
            assert "No unit conversion" in transformation
            assert "HbA1c" not in transformation
            assert "percentage_points" not in transformation
        else:
            assert parameter.unit == "percentage_points"
            assert "HbA1c change unit renamed percentage_points" in transformation


def test_offline_replay_is_nonmutating_and_does_not_access_source_or_network(package, monkeypatch):
    registry, root = package
    before = registry.model_dump(mode="json")

    def forbidden(*args, **kwargs):
        pytest.fail("Offline summary verification cannot acquire or decode sources")

    monkeypatch.setattr(module, "replay_source", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    result = module.audit_update_biomarker(registry, root)
    assert registry.model_dump(mode="json") == before
    assert result["raw_source_read"] is False
    assert result["source_cells_reproduced"] is None
    assert result["cross_endpoint_covariance"] is None
    assert result["scientific_gates"] == module.GATES


@pytest.mark.parametrize(
    "field,value",
    [
        ("value", 999),
        ("unit", "mmol/mol"),
        ("transformation", "wrong endpoint unit conversion"),
        ("source", "wrong group"),
        ("model_role", "health_model"),
        ("population", "United States"),
        ("notes", "zero uncertainty"),
        ("uncertainty", {"kind": "normal", "sd": 1}),
    ],
)
def test_complete_evidence_drift_is_rejected(package, field, value):
    registry, root = package
    raw = registry.model_dump(mode="json")
    key = "update_table5_hba1c_paired_mpf_minus_upf_mean"
    raw["parameters"][key][field] = value
    changed = EvidenceRegistry.model_validate(raw)
    with pytest.raises(ValueError, match="evidence or provenance"):
        module.audit_update_biomarker(changed, root)


def test_changed_summary_and_original_source_fail_before_decode(package, monkeypatch):
    registry, root = package

    def forbidden(*args, **kwargs):
        pytest.fail("Original source bytes must be verified before PDF decoding")

    monkeypatch.setattr(module, "PdfReader", forbidden)
    with pytest.raises(ValueError, match="original source checksum"):
        module.replay_source(b"not the reviewed public PDF", root)
    path = root / module.SUMMARY_PATH
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="source-summary checksum"):
        module.audit_update_biomarker(registry, root)


def _synthetic_pages(summary):
    # In-memory table-shaped fixture; all unselected p columns are synthetic.
    page12 = "Supplementary Table 5: MPF diet UPF diet MPF diet - UPF diet "
    page12 += "N Mean SE p-value N Mean SE p-value N Mean SE p-value "
    for row in summary["endpoints"].values():
        page12 += row["source_label"] + " "
        page12 += (
            " ".join(
                " ".join(row["groups"][g][f] for f in module.FIELDS) + " 0.999"
                for g in module.GROUPS
            )
            + " "
        )
    return page12, "Unadjusted change from baseline and between diets assessed using paired t-test."


@pytest.mark.parametrize(
    "mutation", ["none", "reverse_groups", "duplicate_row", "wrong_unit", "unpaired"]
)
def test_parser_requires_unique_unit_label_ordered_cells_and_paired_footnote(package, mutation):
    _, root = package
    summary = json.loads((root / module.SUMMARY_PATH).read_bytes())
    page12, page13 = _synthetic_pages(summary)
    if mutation == "reverse_groups":
        page12 = page12.replace(
            "MPF diet UPF diet MPF diet - UPF diet", "UPF diet MPF diet UPF diet - MPF diet"
        )
    elif mutation == "duplicate_row":
        page12 += " HbA1C (%) "
    elif mutation == "wrong_unit":
        page12 = page12.replace("HbA1C (%)", "HbA1C (mmol/mol)")
    elif mutation == "unpaired":
        page13 = page13.replace("paired", "unpaired")
    if mutation == "none":
        assert module._selected_rows(page12, page13, summary) == {
            endpoint: deepcopy(row["groups"]) for endpoint, row in summary["endpoints"].items()
        }
    else:
        with pytest.raises(ValueError):
            module._selected_rows(page12, page13, summary)


def test_script_preserves_existing_output_and_returns_sanitized_failure(
    tmp_path, monkeypatch, capsys
):
    spec = importlib.util.spec_from_file_location(
        "verify_update", ROOT / "scripts/verify_update_biomarker.py"
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    path = tmp_path / "existing-result.json"
    path.write_bytes(b"preserved historical result")
    monkeypatch.setattr("sys.argv", ["verify_update_biomarker.py", "--output", str(path)])
    assert script.main() == 1
    assert path.read_bytes() == b"preserved historical result"
    assert capsys.readouterr().out.strip() == "UPDATE public biomarker source-summary replay failed"
