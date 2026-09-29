import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.nhanes import load_nhanes
from demeter.data.prechronic import DIAGNOSES, load_prechronic
from demeter.data.state_mapping import DATASET, assess, mapping_report
from demeter.schema import EvidenceRegistry


def registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def fixture():
    rows = []
    for i in range(8):
        rows.append(
            {
                "WTSAFPRP": i + 1.0,
                "SDMVSTRA": 1 if i < 4 else 2,
                "SDMVPSU": i % 2 + 1,
                "RIAGENDR": 1,
                "RIDAGEYR": [17, 35, 30, 30, 50, 60, 80, 45][i],
                "RIDEXPRG": np.nan,
                "DIQ010": 2,
                "LBXGH": 5.0,
                "LBXGLU": 90.0,
                "BMXWAIST": 90.0,
                "LBDHDD": 60.0,
                "LBXTR": 100.0,
                **dict.fromkeys(DIAGNOSES, 2),
                **{f"BPXOSY{j}": 110.0 for j in (1, 2, 3)},
                **{f"BPXODI{j}": 70.0 for j in (1, 2, 3)},
            }
        )
    data = pd.DataFrame(rows)
    data.loc[1, ["RIAGENDR", "RIDEXPRG"]] = [2, 1]
    data.loc[3, "BMXWAIST"] = 110.0
    data.loc[4, "LBXGH"] = 6.0
    data.loc[5, "LBXGLU"] = 130.0
    data.loc[6, "DIQ010"] = 1  # Known disease persists below laboratory thresholds.
    data.loc[7, "MCQ160B"] = 9  # Refused diagnosis response is unknown, not healthy.
    return data


def overall(report, definition):
    return next(d for d in report["definitions"] if d["id"] == definition)["domains"][0]


def test_weighted_partition_retains_unknowns_and_does_not_allocate_engine_states():
    report = assess(fixture(), registry())
    assert report["counts"] == {
        "source_n": 8,
        "positive_weight_n": 8,
        "under_adult_minimum_n": 1,
        "known_pregnancy_n": 1,
        "eligible_n": 6,
    }
    row = overall(report, "risk_1")
    assert row["eligible_weight"] == 33
    weights = {
        "lower_measured_risk": 3,
        "prechronic_candidate": 4,
        "prediabetes": 5,
        "diabetes_any_type": 13,
        "other_reported_diagnosis": 0,
        "unclassified": 8,
    }
    for key, numerator in weights.items():
        assert row["categories"][key]["eligible_weight_proportion"]["estimate"] == pytest.approx(
            numerator / 33
        )
    assert row["unclassified_reasons_n"] == {
        "incomplete_glycemic_observation": 0,
        "incomplete_other_risk_or_diagnosis": 1,
    }
    assert row["public_age_topcode_n"] == 1
    assert row["diagnosis_checks_n"]["reported_diabetes_with_subdiabetic_labs"] == 1
    assert not report["direct_initialization_allowed"]
    assert not report["scientific_release_ready"]
    assert "t2d" not in row["categories"]


def test_complete_case_diagnosis_selection_and_alternative_definition_are_visible():
    data = fixture()
    data.loc[6, "LBXGLU"] = np.nan
    report = assess(data, registry())
    row = overall(report, "risk_1")
    assert row["unclassified_n"] == 2
    assert row["diagnosis_checks_n"]["reported_diabetes_but_unclassified"] == 1
    assert row["unclassified_reasons_n"]["incomplete_glycemic_observation"] == 1
    stricter = overall(report, "risk_2")
    assert stricter["categories"]["prechronic_candidate"]["sample_n"] == 0
    assert stricter["categories"]["lower_measured_risk"]["sample_n"] == 2
    for definition in report["definitions"]:
        for domain in definition["domains"]:
            assert sum(x["sample_n"] for x in domain["categories"].values()) == domain["eligible_n"]
            assert sum(domain["unclassified_reasons_n"].values()) == domain["unclassified_n"]


def test_unsupported_initialization_and_invalid_coding_fail_closed():
    evidence = registry()
    evidence.datasets[DATASET]["direct_initialization_allowed"] = True
    with pytest.raises(ValueError, match="without initialization"):
        assess(fixture(), evidence)
    for column, value in [("RIDAGEYR", 85), ("RIAGENDR", 9), ("WTSAFPRP", -1)]:
        data = fixture()
        data.loc[0, column] = value
        with pytest.raises(ValueError):
            assess(data, registry())


def test_offline_mapping_matches_existing_benchmarks_without_changing_denominators(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Mapping report must use archived sources offline")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    evidence = registry()
    report = mapping_report(evidence)
    benchmarks = {"glycemic": load_nhanes(evidence)["domains"]}
    benchmarks.update({d["id"]: d["domains"] for d in load_prechronic(evidence)["definitions"]})
    for definition in report["definitions"]:
        for row, old in zip(definition["domains"], benchmarks[definition["id"]], strict=True):
            assert (row["age_group"], row["sex"]) == (old["age_group"], old["sex"])
            assert row["classified_n"] == old["complete_n"]
            assert row["eligible_n"] == old["eligible_n"]
            unknown = row["categories"]["unclassified"]["eligible_weight_proportion"]["estimate"]
            assert unknown == pytest.approx(old["missing_weight_fraction"], abs=1e-11)
            for state, saved in old["states"].items():
                estimate = saved if definition["id"] == "glycemic" else saved["proportion"]
                actual = row["categories"][state]["eligible_weight_proportion"]["estimate"]
                assert actual == pytest.approx(estimate["estimate"] * (1 - unknown), abs=1e-11)
    assert overall(report, "risk_1")["classified_n"] == 3211
    assert report["counts"]["eligible_n"] == 3769
    assert len(report["provenance"]["source_sha256"]["glycemic"]) == 4
    assert len(report["provenance"]["source_sha256"]["risk"]) == 6


def test_cli_outputs_aggregate_report_with_crosswalk(tmp_path):
    destination = tmp_path / "mapping.json"
    result = CliRunner().invoke(app, ["evidence", "state-mapping", "--output", str(destination)])
    assert result.exit_code == 0, result.output
    report = json.loads(destination.read_bytes())
    assert not report["direct_initialization_allowed"]
    assert all(row["mapping_status"] != "accepted" for row in report["crosswalk"])
    assert "SEQN" not in Path(destination).read_text(encoding="utf-8")
    # CI runs on Linux, macOS and Windows: both storage precision and LF bytes
    # must reproduce the exact checksummed artifact, not just approximate values.
    assert (
        destination.read_bytes() == Path("docs/validation/issue-56-state-mapping.json").read_bytes()
    )
