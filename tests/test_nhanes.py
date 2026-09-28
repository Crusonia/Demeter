import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.ingest import BUNDLE
from demeter.data.nhanes import (
    STORE,
    classify,
    definition,
    load_nhanes,
    read_store,
    read_xpt,
    rebuild_nhanes,
    reconstruct,
    survey_proportion,
)
from demeter.schema import EvidenceRegistry

REGISTRY = EvidenceRegistry.from_yaml("evidence/parameters.yaml")


@pytest.fixture(scope="module")
def source_data():
    return read_store()[0]


def test_xport_zero_weights_match_official_codebook():
    data = read_xpt(STORE / "P_GLU.xpt", ["WTSAFPRP"])
    assert len(data) == 5090
    assert (data.WTSAFPRP == 0).sum() == 614
    assert (data.WTSAFPRP > 0).sum() == 4476


def test_classification_boundaries_diagnosis_precedence_and_missing():
    data = pd.DataFrame(
        {
            "DIQ010": [2, 2, 2, 2, 2, 1, 3, 7, 9, 2, 2],
            "LBXGH": [5.6, 5.7, 6.5, 5, 5, 5, 5, 5, 5, np.nan, 5],
            "LBXGLU": [99, 99, 99, 100, 126, 90, 90, 90, 90, 90, np.nan],
        }
    )
    result = classify(data, definition(REGISTRY)["analysis"])
    assert result.iloc[:7].tolist() == [
        "normoglycemia",
        "prediabetes",
        "diabetes_any_type",
        "prediabetes",
        "diabetes_any_type",
        "diabetes_any_type",
        "normoglycemia",
    ]
    assert result.iloc[7:].isna().all()


def survey_fixture():
    # Synthetic analytic fixture: two strata, two PSUs each, equal weights.
    return pd.DataFrame({"WTSAFPRP": [1.0] * 4, "SDMVSTRA": [1, 1, 2, 2], "SDMVPSU": [1, 2, 1, 2]})


def test_taylor_variance_matches_hand_calculation_and_is_scale_invariant():
    d = survey_fixture()
    domain = pd.Series([True] * 4)
    y = pd.Series([0, 1, 0, 1])
    result = survey_proportion(d, domain, y, 0.95)
    assert result["estimate"] == 0.5
    # PSU residuals are (-1/8,+1/8) in each stratum: total variance = 1/8.
    assert result["standard_error"] ** 2 == pytest.approx(0.125)
    assert result["degrees_of_freedom"] == 2
    assert result["interval"]["low"] < 0.5 < result["interval"]["high"]
    d.WTSAFPRP *= 100000
    assert survey_proportion(d, domain, y, 0.95) == result


def test_domain_variance_keeps_out_of_domain_psus():
    d = survey_fixture()
    result = survey_proportion(
        d, pd.Series([True, False, True, True]), pd.Series([1, 0, 0, 0]), 0.95
    )
    assert result["estimate"] == pytest.approx(1 / 3)
    # Stratum 1 includes an empty-domain PSU; dropping it would lose variance.
    assert result["standard_error"] ** 2 == pytest.approx(4 / 81)


def test_empty_boundary_and_invalid_design_do_not_manufacture_intervals():
    d = survey_fixture()
    y = pd.Series([0] * 4)
    assert survey_proportion(d, pd.Series([False] * 4), y, 0.95)["estimate"] is None
    assert survey_proportion(d, pd.Series([True] * 4), y, 0.95)["interval"] is None
    d.loc[1, "SDMVPSU"] = 1
    with pytest.raises(ValueError, match="Singleton"):
        survey_proportion(d, pd.Series([True] * 4), y, 0.95)


def test_all_published_age_sex_cells_reconstructed_and_partition_conserves(source_data):
    report = reconstruct(source_data, definition(REGISTRY))
    assert report["published_reconstruction"]["passed"]
    assert len(report["published_reconstruction"]["checks"]) == 12
    assert report["design"]["positive_weight_n"] == 4476
    assert report["design"]["strata"] == 24
    assert report["design"]["psus"] == 49
    for domain in report["domains"]:
        assert sum(s["estimate"] for s in domain["states"].values()) == pytest.approx(1)
        assert domain["complete_n"] + domain["missing_n"] == domain["eligible_n"]
        assert all(s["standard_error"] > 0 for s in domain["states"].values())
    total = report["domains"][0]
    assert total["eligible_n"] == 3769
    assert total["missing_n"] == 12
    assert not report["scientific_release_ready"]
    assert not report["published_reconstruction"]["independent_holdout"]
    assert report["model_role"] == "benchmark_only"


def test_rebuild_is_offline_and_identical_to_committed_bundle(tmp_path, monkeypatch):
    def no_network(*a, **kw):
        pytest.fail("Reconstruction attempted network access")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    rebuild_nhanes(REGISTRY, destination=tmp_path)
    assert load_nhanes(REGISTRY, tmp_path) == load_nhanes(REGISTRY)
    assert (tmp_path / "nhanes_prevalence.json").read_bytes() == (
        BUNDLE / "nhanes_prevalence.json"
    ).read_bytes()


def test_source_corruption_fails_before_derived_output(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    shutil.copyfile(STORE / "manifest.json", source / "manifest.json")
    # Alphabetically first manifest entry fails before any parser is called.
    (source / "P_DEMO.xpt").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="source checksum"):
        rebuild_nhanes(REGISTRY, source, tmp_path / "derived")
    assert not (tmp_path / "derived").exists()


def test_bundle_corruption_and_definition_drift_are_rejected(tmp_path):
    for name in ("nhanes_prevalence.json", "nhanes_prevalence_manifest.json"):
        shutil.copyfile(BUNDLE / name, tmp_path / name)
    path = tmp_path / "nhanes_prevalence.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="bundle checksum"):
        load_nhanes(REGISTRY, tmp_path)
    changed = REGISTRY.model_copy(deep=True)
    changed.datasets["nhanes_glycemic_prevalence"]["analysis"]["hba1c_prediabetes_min"] = 6.0
    with pytest.raises(ValueError, match="definition changed"):
        load_nhanes(changed)


def test_population_cli_and_scientific_guard(tmp_path):
    output = tmp_path / "population.json"
    result = CliRunner().invoke(app, ["evidence", "population", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_bytes())["model_role"] == "benchmark_only"
    result = CliRunner().invoke(app, ["validate", "--scientific-required"])
    assert result.exit_code == 1
    report = json.loads(result.output)
    assert report["software_checks_passed"]
    assert not report["population_evidence"]["engine_state_mapping_resolved"]


def test_duplicate_ids_and_missing_components_fail(tmp_path, monkeypatch):
    fake = pd.DataFrame({"SEQN": [1, 1], "DIQ010": [1, 2]})
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: fake)
    with pytest.raises(ValueError, match="duplicate"):
        read_xpt(Path("synthetic.xpt"), ["DIQ010"])
