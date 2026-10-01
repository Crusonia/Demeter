import copy
from itertools import product
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.data.nhanes import STATES, encoded
from demeter.data.partial_observations import DATASET, assess, partial_report, possible_categories
from demeter.data.prechronic import COLUMNS, DIAGNOSES, classify as risk_classify
from demeter.schema import EvidenceRegistry


@pytest.fixture
def registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def observation(**changes):
    """Synthetic observations, not source records or clinical parameter values."""
    row = {
        "WTSAFPRP": 1.0,
        "SDMVSTRA": 1,
        "SDMVPSU": 1,
        "RIAGENDR": 1,
        "RIDAGEYR": 40,
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
    return row | changes


def options(value, full=(0, 1)):
    return full if value == -1 else (value,)


def row_categories(possible, index=0):
    return set(possible.columns[possible.loc[index].to_numpy()])


def test_exhaustive_glycemic_completions_and_diagnosis_precedence(registry):
    rows, expected = [], []
    for diagnosis, a1c, glucose in product((-1, 0, 1), (-1, 0, 1, 2), (-1, 0, 1, 2)):
        rows.append(
            observation(
                DIQ010={-1: 9, 0: 2, 1: 1}[diagnosis],
                LBXGH={-1: np.nan, 0: 5.0, 1: 6.0, 2: 7.0}[a1c],
                LBXGLU={-1: np.nan, 0: 90.0, 1: 110.0, 2: 140.0}[glucose],
            )
        )
        completed = set()
        for d, a, g in product(
            options(diagnosis), options(a1c, (0, 1, 2)), options(glucose, (0, 1, 2))
        ):
            completed.add(
                "diabetes_any_type"
                if d or a == 2 or g == 2
                else "prediabetes"
                if a == 1 or g == 1
                else "normoglycemia"
            )
        expected.append(completed)
    frame = pd.DataFrame(rows)
    possible = possible_categories(frame, registry, "glycemic")
    for i, target in enumerate(expected):
        assert row_categories(possible, i) == target
    # All other fields can be absent once the reported diagnosis is known.
    missing = observation(DIQ010=1)
    for name in [
        "LBXGH",
        "LBXGLU",
        "BMXWAIST",
        "LBDHDD",
        "LBXTR",
        *DIAGNOSES,
        *COLUMNS["P_BPXO.xpt"],
    ]:
        missing[name] = np.nan
    for key in ("glycemic", "risk_1", "risk_2"):
        assert row_categories(possible_categories(pd.DataFrame([missing]), registry, key)) == {
            "diabetes_any_type"
        }


def test_exhaustive_risk_completions_retain_joint_category_sets(registry):
    rows, completions = [], []
    for diagnosis, *markers in product((-1, 0, 1), repeat=5):
        row = observation(MCQ160B={-1: 9, 0: 2, 1: 1}[diagnosis])
        row.update(
            BMXWAIST={-1: np.nan, 0: 90, 1: 120}[markers[0]],
            LBDHDD={-1: np.nan, 0: 60, 1: 30}[markers[1]],
            LBXTR={-1: np.nan, 0: 100, 1: 200}[markers[2]],
        )
        for j in (1, 2, 3):
            row[f"BPXOSY{j}"] = {-1: np.nan, 0: 110, 1: 150}[markers[3]]
        rows.append(row)
        completions.append(list(product(options(diagnosis), *(options(m) for m in markers))))
    frame = pd.DataFrame(rows)
    for key, minimum in (("risk_1", 1), ("risk_2", 2)):
        possible = possible_categories(frame, registry, key)
        for i, completed in enumerate(completions):
            expected = {
                "other_reported_diagnosis"
                if d
                else "prechronic_candidate"
                if sum(markers) >= minimum
                else "lower_measured_risk"
                for d, *markers in completed
            }
            assert row_categories(possible, i) == expected
    # Complete-case labels agree with the separately implemented original classifier.
    ga = registry.datasets["nhanes_glycemic_prevalence"]["analysis"]
    ra = registry.datasets["nhanes_prechronic_candidates"]["analysis"]
    for key in ra["definitions"]:
        original = risk_classify(frame, ra, ga, key)
        possible = possible_categories(frame, registry, key)
        for i, value in original.dropna().items():
            assert row_categories(possible, i) == {value}


def test_thresholds_priority_and_blood_pressure_coarsening(registry):
    ga = registry.datasets["nhanes_glycemic_prevalence"]["analysis"]
    ra = registry.datasets["nhanes_prechronic_candidates"]["analysis"]
    rows = [
        observation(LBXGH=ga["hba1c_diabetes_min"], LBXGLU=np.nan, DIQ010=9),
        observation(LBXGH=ga["hba1c_prediabetes_min"], MCQ160B=1, BMXWAIST=np.nan),
        observation(
            BMXWAIST=ra["waist_male_cm"],
            LBXTR=ra["triglycerides_mg_dl"],
            LBDHDD=ra["hdl_male_mg_dl"],
        ),
        observation(DIQ010=3),
        observation(BPXOSY1=900.0, BPXOSY2=np.nan),
    ]
    possible = possible_categories(pd.DataFrame(rows), registry, "risk_1")
    assert row_categories(possible, 0) == {"diabetes_any_type"}
    assert row_categories(possible, 1) == {"prediabetes"}
    assert row_categories(possible, 2) == {"lower_measured_risk"}
    assert row_categories(possible, 3) == {"lower_measured_risk"}
    # Coarsening discards partial block information; do not claim sharp bounds.
    assert row_categories(possible, 4) == {"lower_measured_risk", "prechronic_candidate"}


def test_weighted_bounds_and_partition_do_not_allocate_unknown_people(registry):
    frame = pd.DataFrame(
        [
            observation(WTSAFPRP=1, SDMVPSU=1),
            observation(WTSAFPRP=2, SDMVPSU=2, MCQ160B=9),
            observation(WTSAFPRP=3, SDMVSTRA=2, SDMVPSU=1, DIQ010=1, LBXGH=np.nan),
            observation(WTSAFPRP=4, SDMVSTRA=2, SDMVPSU=2, LBXGH=6.0, BMXWAIST=np.nan),
        ]
    )
    report = assess(frame, registry)
    row = next(d for d in report["definitions"] if d["id"] == "risk_1")["domains"][0]
    assert (
        row["complete_case_n"],
        row["resolved_n"],
        row["newly_resolved_n"],
        row["unresolved_n"],
    ) == (1, 3, 2, 1)
    assert row["reported_diabetes_unresolved_n"] == 0
    expected = {
        "lower_measured_risk": (0.1, 0.3),
        "other_reported_diagnosis": (0, 0.2),
        "diabetes_any_type": (0.3, 0.3),
        "prediabetes": (0.4, 0.4),
        "prechronic_candidate": (0, 0),
    }
    for category, (low, high) in expected.items():
        assert row["categories"][category]["compatible_weight_range"] == pytest.approx(
            {"lower": low, "upper": high}
        )
    assert sum(p["sample_n"] for p in row["category_set_partition"]) == 4
    assert sum(
        p["eligible_weight_proportion"]["estimate"] for p in row["category_set_partition"]
    ) == pytest.approx(1)
    assert not report["direct_initialization_allowed"]
    assert not report["scientific_release_ready"]
    assert "t2d" not in row["categories"]


def test_adding_information_only_tightens_categories(registry):
    incomplete = observation(DIQ010=9, LBXGH=np.nan, LBXGLU=np.nan, BMXWAIST=np.nan, MCQ160B=9)
    rows = [
        incomplete,
        incomplete | {"DIQ010": 2},
        incomplete | {"DIQ010": 2, "LBXGH": 5.0, "LBXGLU": 90.0},
        observation(),
    ]
    for key in ("glycemic", "risk_1", "risk_2"):
        possible = possible_categories(pd.DataFrame(rows), registry, key)
        for i in range(1, len(rows)):
            assert row_categories(possible, i) <= row_categories(possible, i - 1)
    all_missing = pd.DataFrame([observation(DIQ010=7, LBXGH=0, LBXGLU=np.inf)])
    assert row_categories(possible_categories(all_missing, registry, "glycemic")) == set(STATES)


def test_unsupported_method_and_initialization_are_rejected(registry):
    registry.datasets[DATASET]["direct_initialization_allowed"] = True
    with pytest.raises(ValueError, match="benchmark-only"):
        possible_categories(pd.DataFrame([observation()]), registry, "glycemic")
    registry.datasets[DATASET]["direct_initialization_allowed"] = False
    registry.datasets[DATASET]["method"] = "impute_healthy"
    with pytest.raises(ValueError, match="benchmark-only"):
        possible_categories(pd.DataFrame([observation()]), registry, "glycemic")


def test_offline_report_and_cli_reproduce_aggregates_without_person_rows(
    registry, monkeypatch, tmp_path
):
    def forbidden(*args, **kwargs):
        pytest.fail("Partial observations must use archived sources offline")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    report = partial_report(registry)
    assert report["counts"]["eligible_n"] == 3769
    for definition in report["definitions"]:
        for row in definition["domains"]:
            assert row["reported_diabetes_unresolved_n"] == 0
            assert row["resolved_n"] + row["unresolved_n"] == row["eligible_n"]
            assert row["resolved_n"] >= row["complete_case_n"]
            assert sum(p["sample_n"] for p in row["category_set_partition"]) == row["eligible_n"]
            if row["eligible_n"]:
                assert sum(
                    p["eligible_weight_proportion"]["estimate"]
                    for p in row["category_set_partition"]
                ) == pytest.approx(1)
                bounds = [r["compatible_weight_range"] for r in row["categories"].values()]
                assert sum(b["lower"] for b in bounds) <= 1 + 1e-10
                assert sum(b["upper"] for b in bounds) >= 1 - 1e-10
                assert all(0 <= b["lower"] <= b["upper"] <= 1 for b in bounds)
    saved = Path("docs/validation/issue-56-partial-observations.json").read_bytes()
    assert report["provenance"]["evidence_sha256"] == registry.content_hash
    replay_payload, saved_payload = copy.deepcopy(report), json.loads(saved)
    replay_payload["provenance"].pop("evidence_sha256")
    saved_payload["provenance"].pop("evidence_sha256")
    assert encoded(replay_payload) == encoded(saved_payload)
    destination = tmp_path / "partial.json"
    run = CliRunner().invoke(
        app, ["evidence", "state-mapping", "--partial", "--output", str(destination)]
    )
    assert run.exit_code == 0, run.output
    assert destination.read_bytes() == encoded(report)
    assert (
        json.loads(destination.read_bytes())["provenance"]["evidence_sha256"]
        == registry.content_hash
    )
    assert "SEQN" not in json.dumps(report)
