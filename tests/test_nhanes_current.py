"""Synthetic current-cycle observation tests; no public participant data read."""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from demeter.data import nhanes, nhanes_current as current
from demeter.data.partial_observations import possible_categories
from demeter.schema import EvidenceRegistry


@pytest.fixture
def registry():
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml").model_copy(deep=True)
    # Synthetic references test extraction and mismatch accounting, not CDC parity.
    registry.datasets[current.DATASET] = {
        "model_role": "benchmark_only",
        "method": current.METHOD,
        **{name: False for name in current.GATES},
        "analysis": deepcopy(nhanes.definition(registry)["analysis"])
        | {"weight_field": "WTSAF2YR", "cycle_code": 12, "examined_code": 2, "topcoded_age": 80},
        "population": "Synthetic survey fixtures only",
        "geography": "Synthetic",
        "time_period": "Synthetic current-cycle coding",
        "uncertainty": "Synthetic software validation; not source findings",
        "limitations": ["No empirical source calculation"],
        "published_diabetes_targets": [
            {
                "age_group": age,
                "sex": sex,
                "category": category,
                "n": 0,
                "percent": 0,
                "tolerance_pp": 0.05,
                "ci_percent": [0, 100],
                "standard_error_percent": 0,
                "table": 1 if age == "20_plus" else 2,
            }
            for age, sex in current.TARGET_DOMAINS
            for category in current.TARGET_CATEGORIES
        ],
    }
    return registry


def frame():
    return pd.DataFrame(
        {
            "SEQN": range(910001, 910009),
            "WTSAF2YR": [1.0, 2.0, 1.0, 3.0, 2.0, 1.0, 1.0, 2.0],
            "SDDSRVYR": [12] * 8,
            "RIDSTATR": [2] * 8,
            "RIDAGEYR": [25, 25, 45, 45, 65, 65, 17, 80],
            "RIAGENDR": [1, 2, 1, 2, 1, 2, 1, 2],
            "RIDEXPRG": [np.nan, 2, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
            "DIQ010": [2, 1, 2, 3, 1, 9, 2, 2],
            "LBXGH": [5.0, 5.0, 5.7, 6.5, np.nan, 5.0, 5.0, 5.0],
            "LBXGLU": [90.0, 90.0, 100.0, 126.0, 90.0, 90.0, 90.0, 90.0],
            "SDMVSTRA": [1, 1, 1, 1, 2, 2, 2, 2],
            "SDMVPSU": [1, 2, 1, 2, 1, 2, 1, 2],
        }
    )


def coordinate(report, domain, member):
    return next(
        i
        for i, row in enumerate(report["joint"]["coordinates"])
        if row == {"domain": domain, "membership": member}
    )


def test_inherited_contract_and_exact_coordinate_order(registry):
    data = frame()
    before = data.copy(deep=True)
    report = current.assess(data, registry)
    pd.testing.assert_frame_equal(data, before)
    expected = []
    for family, memberships in (
        ("eligible", current.ELIGIBLE_MEMBERSHIPS),
        ("complete_case", current.CONDITIONAL_MEMBERSHIPS),
    ):
        for age in current.AGE_IDS:
            for sex in ("all", "male", "female"):
                expected.extend(
                    {"domain": f"{family}:{age}:{sex}", "membership": m} for m in memberships
                )
    assert report["joint"]["coordinates"] == expected
    protocol = json.loads(
        Path("docs/validation/nhanes-2021-2023-intake-protocol-v1.json").read_text(encoding="utf-8")
    )
    assert report["joint"]["coordinates"] == protocol["coordinate_order"]
    assert len(expected) == 192
    assert report["diagnostics"]["rectangular_calculation_coordinates"] == 24 * 13
    assert report["joint"]["design"]["weight"] == "WTSAF2YR"
    assert report["joint"]["design"]["internal_working_weight"] == "WTSAFPRP"
    assert report["counts"]["positive_weight_n"] == 8
    assert report["counts"]["eligible_n"] == 7
    assert report["counts"]["complete_n"] == 5
    assert report["counts"]["known_diagnosis_unclassified_eligible_n"] == 1
    assert report["source_audit_passed"] is False
    assert all(report[g] is False for g in current.GATES)
    assert report["diagnostics"]["matrix_repair_performed"] is False
    text = json.dumps(report, allow_nan=False)
    assert "SEQN" not in text and "910001" not in text
    assert len(report["published_reconstruction"]["checks"]) == 18


def test_hand_ratios_covariance_and_scalar_parity(registry):
    data = frame().iloc[:4].copy()
    data["WTSAF2YR"] = 1.0
    data["RIDAGEYR"] = 25
    data["SDMVSTRA"] = [1, 1, 2, 2]
    report = current.assess(data, registry)
    joint = report["joint"]
    indices = [
        coordinate(report, "complete_case:20_plus:all", f"complete:{state}")
        for state in nhanes.STATES
    ]
    # Outcomes normal/diagnosed/prediabetic/undiagnosed give (1/4,1/4,1/2).
    assert [joint["estimates"][i] for i in indices] == [0.25, 0.25, 0.5]
    # Independent per-person residual vectors, one row per PSU, denominator4.
    labels = np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0], [0, 0, 1]])
    residual = (labels - np.array([0.25, 0.25, 0.5])) / 4
    hand = np.zeros((3, 3))
    for rows in (residual[:2], residual[2:]):
        centered = rows - rows.mean(axis=0)
        hand += 2 * centered.T @ centered
    actual = np.array([[joint["covariance"][i][k] for k in indices] for i in indices])
    assert actual == pytest.approx(hand)
    scalar = report["domains"][0]
    for state, i in zip(nhanes.STATES, indices, strict=True):
        assert scalar["states"][state]["estimate"] == joint["estimates"][i]
        assert scalar["states"][state]["standard_error"] ** 2 == pytest.approx(
            joint["covariance"][i][i]
        )
    diagnosed = coordinate(report, "complete_case:20_plus:all", "diagnosis:diagnosed")
    undiagnosed = coordinate(report, "complete_case:20_plus:all", "diagnosis:undiagnosed")
    assert joint["estimates"][diagnosed] == joint["estimates"][undiagnosed] == 0.25
    assert sum(joint["estimates"][i] for i in (diagnosed, undiagnosed)) == 0.5


def test_joint_closure_singularity_and_cross_family_dependence(registry):
    report = current.assess(frame(), registry)
    j = report["joint"]
    available = [i for i, value in enumerate(j["estimates"]) if value is not None]
    covariance = np.asarray([[j["covariance"][i][k] for k in available] for i in available])
    assert covariance == pytest.approx(covariance.T, abs=1e-15)
    assert np.linalg.eigvalsh(covariance).min() >= -1e-13
    assert np.linalg.matrix_rank(covariance, tol=1e-12) <= 2  # four PSUs minus two strata
    for prefix, members in (
        ("eligible", current.ELIGIBLE_MEMBERSHIPS[:4]),
        ("eligible", current.ELIGIBLE_MEMBERSHIPS[4:]),
        ("complete_case", current.CONDITIONAL_MEMBERSHIPS[:3]),
    ):
        indices = [coordinate(report, f"{prefix}:20_plus:all", name) for name in members]
        assert sum(j["estimates"][i] for i in indices) == pytest.approx(1)
        for k in available:
            assert sum(j["covariance"][i][k] for i in indices) == pytest.approx(0, abs=1e-15)
    eligible = coordinate(report, "eligible:20_plus:all", "complete:diabetes_any_type")
    conditional = coordinate(report, "complete_case:20_plus:all", "complete:diabetes_any_type")
    assert j["estimates"][eligible] == pytest.approx(5 / 12)
    assert j["estimates"][conditional] == pytest.approx(5 / 9)
    assert j["covariance"][eligible][conditional] != 0
    total = coordinate(report, "complete_case:20_plus:all", "complete:diabetes_any_type")
    diagnosed = coordinate(report, "complete_case:20_plus:all", "diagnosis:diagnosed")
    undiagnosed = coordinate(report, "complete_case:20_plus:all", "diagnosis:undiagnosed")
    for k in available:
        assert j["covariance"][total][k] == pytest.approx(
            j["covariance"][diagnosed][k] + j["covariance"][undiagnosed][k], abs=1e-15
        )


def test_bounds_match_independent_direct_scalar_memberships(registry):
    data = frame()
    report = current.assess(data, registry)
    sample = data.assign(WTSAFPRP=data.WTSAF2YR)
    possible = possible_categories(sample, registry, "glycemic")
    eligible = sample.RIDAGEYR >= 20
    bounds = report["bound_endpoints"]
    assert len(bounds["estimates"]) == 72
    for state in nhanes.STATES:
        for endpoint in ("lower", "upper"):
            membership = (
                possible[state] & possible.sum(axis=1).eq(1)
                if endpoint == "lower"
                else possible[state]
            )
            scalar = nhanes.survey_proportion(sample, eligible, membership, 0.95)
            i = bounds["labels"].index(f"eligible:20_plus:all:{state}:{endpoint}")
            assert bounds["estimates"][i] == pytest.approx(scalar["estimate"])
            assert bounds["covariance"][i][i] == pytest.approx(
                scalar["standard_error"] ** 2, abs=1e-15
            )
    # The missing-assay known diagnosis stays unclassified in the complete family.
    i = bounds["labels"].index("eligible:20_plus:all:diabetes_any_type:lower")
    assert bounds["estimates"][i] == pytest.approx(7 / 12)


def test_source_boundary_priority_invalid_assays_and_interview_unknowns(registry):
    data = pd.concat([frame().iloc[[0]]] * 12, ignore_index=True).drop(columns="SEQN")
    data["DIQ010"] = [2, 2, 2, 2, 2, 1, 1, 3, 7, 9, 2, 2]
    data["LBXGH"] = [5.6, 5.7, 6.5, 5.0, 5.0, 5.0, np.nan, 5.0, 5.0, 5.0, 0.0, np.inf]
    data["LBXGLU"] = [99.0, 99.0, 99.0, 100.0, 126.0, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0, -1.0]
    spec = current.definition(registry)
    sample, _ = current._sample(data, spec)
    _, memberships, _, _, _, _ = current._observations(sample, registry, spec)
    assert [
        next(name for name in current.COMPLETE_LABELS if memberships.loc[i, f"complete:{name}"])
        for i in range(12)
    ] == [
        "normoglycemia",
        "prediabetes",
        "diabetes_any_type",
        "prediabetes",
        "diabetes_any_type",
        "diabetes_any_type",
        "unclassified",
        "normoglycemia",
        "unclassified",
        "unclassified",
        "unclassified",
        "unclassified",
    ]
    assert memberships.loc[6, "partial:diabetes_any_type"]
    assert not memberships.loc[6, "diagnosis:diagnosed"]
    assert memberships.loc[5, "diagnosis:diagnosed"]
    assert memberships.loc[8, "partial:normoglycemia|diabetes_any_type"]
    assert memberships.loc[9, "partial:normoglycemia|diabetes_any_type"]
    assert memberships.loc[11, "partial:normoglycemia|prediabetes|diabetes_any_type"]


def test_weight_scaling_and_out_of_domain_psus_do_not_change_joint_ratios(registry):
    data = frame()
    original = current.assess(data, registry)
    scaled = current.assess(data.assign(WTSAF2YR=data.WTSAF2YR * 100), registry)
    assert scaled["joint"] == original["joint"]
    assert scaled["bound_endpoints"] == original["bound_endpoints"]
    assert (
        scaled["domains"][0]["weighted_eligible"]
        == 100 * original["domains"][0]["weighted_eligible"]
    )
    # Underage row remains in the design, even though it belongs to no adult domain.
    assert original["counts"]["under_adult_minimum_n"] == 1
    assert original["joint"]["design"]["positive_weight_n"] == 8


def test_zero_domains_and_complete_case_absence_remain_unavailable(registry):
    data = frame()
    data["RIDAGEYR"] = 17
    report = current.assess(data, registry)
    assert all(p is None for p in report["joint"]["estimates"])
    assert all(value is None for row in report["joint"]["covariance"] for value in row)
    assert all(p is None for p in report["bound_endpoints"]["estimates"])
    assert report["joint"]["design"]["psus"] == 4
    data["RIDAGEYR"] = 25
    data["LBXGH"] = np.nan
    report = current.assess(data, registry)
    assert report["counts"]["complete_n"] == 0
    assert report["joint"]["estimates"][:11].count(None) == 0
    assert all(p is None for p in report["joint"]["estimates"][132:])


def test_pregnancy_weight_exclusions_and_open_topcode_are_explicit(registry):
    data = frame()
    data.loc[1, "RIDEXPRG"] = 1
    data.loc[3, "RIDAGEYR"] = 44
    data.loc[3, "RIDEXPRG"] = 3
    data.loc[0, "WTSAF2YR"] = 0
    data.loc[4, "WTSAF2YR"] = np.nan
    report = current.assess(data, registry)
    counts = report["counts"]
    assert counts["source_n"] == 8 and counts["positive_weight_n"] == 6
    assert counts["zero_weight_n"] == counts["missing_weight_n"] == 1
    assert counts["known_pregnancy_n"] == counts["unknown_pregnancy_in_released_age_range_n"] == 1
    assert counts["pregnancy_unavailable_outside_released_age_range_n"] == 2
    assert counts["eligible_n"] == 4
    assert report["coverage"]["total_weight"] == 10
    assert report["coverage"]["groups"]["unknown_pregnancy_in_released_age_range"]["weight"] == 3
    assert report["coverage"]["groups"]["known_pregnancy"]["weight"] == 2
    assert (
        next(
            row
            for row in report["domains"]
            if row["age_group"] == "60_plus" and row["sex"] == "female"
        )["eligible_n"]
        == 2
    )


@pytest.mark.parametrize(
    "column,value",
    [
        ("SDDSRVYR", 11),
        ("SDDSRVYR", np.nan),
        ("RIDSTATR", 0),
        ("RIDSTATR", 1),
        ("RIDAGEYR", 81),
        ("RIDAGEYR", 25.5),
        ("RIDAGEYR", np.inf),
        ("RIAGENDR", 3),
        ("RIDEXPRG", 9),
        ("DIQ010", 4),
        ("DIQ010", np.inf),
        ("WTSAF2YR", -1),
        ("WTSAF2YR", np.inf),
        ("SDMVSTRA", np.nan),
        ("SDMVPSU", 1.5),
        ("SDMVPSU", 0),
        ("SEQN", np.nan),
        ("SEQN", 1.5),
    ],
)
def test_corrupt_source_codes_fail_before_any_survey_calculation(
    registry, monkeypatch, column, value
):
    data = frame()
    data[column] = data[column].astype(float)
    data.loc[0, column] = value
    monkeypatch.setattr(
        current.survey_joint,
        "joint_proportions",
        lambda *args: pytest.fail("unsafe source reached covariance"),
    )
    with pytest.raises(ValueError):
        current.assess(data, registry)


@pytest.mark.parametrize("column", current.REQUIRED)
def test_bool_or_string_source_fields_cannot_be_coerced_to_source_codes(registry, column):
    data = frame()
    data[column] = True
    with pytest.raises(ValueError):
        current.assess(data, registry)
    data[column] = "12"
    with pytest.raises(ValueError):
        current.assess(data, registry)


def test_old_weight_duplicates_and_singleton_support_are_rejected(registry):
    data = frame()
    with pytest.raises(ValueError, match="only WTSAF2YR"):
        current.assess(data.assign(WTSAFPRP=data.WTSAF2YR), registry)
    for duplicate in (data.set_axis([0] * len(data)), pd.concat([data, data[["DIQ010"]]], axis=1)):
        with pytest.raises(ValueError):
            current.assess(duplicate, registry)
    data.loc[1, "SEQN"] = data.loc[0, "SEQN"]
    with pytest.raises(ValueError):
        current.assess(data, registry)
    data = frame()
    data["SDMVPSU"] = 1
    with pytest.raises(ValueError, match="Singleton"):
        current.assess(data, registry)


@pytest.mark.parametrize(
    "key,value",
    [
        ("cycle_code", 11),
        ("examined_code", True),
        ("topcoded_age", 85),
        ("weight_field", "WTPH2YR"),
        ("hba1c_diabetes_min", 6.6),
    ],
)
def test_source_contract_or_inherited_definition_cannot_drift(registry, key, value):
    registry.datasets[current.DATASET]["analysis"][key] = value
    with pytest.raises(ValueError, match="inherited benchmark"):
        current.assess(frame(), registry)


@pytest.mark.parametrize("gate", current.GATES)
def test_no_gate_can_be_activated(registry, gate):
    registry.datasets[current.DATASET][gate] = True
    with pytest.raises(ValueError):
        current.assess(frame(), registry)


def test_published_mismatch_diagnostics_preserve_n_point_and_ci_difference(registry):
    report = current.assess(frame(), registry)
    check = report["published_reconstruction"]["checks"][0]
    assert not check["sample_size_matches"] and not check["point_rounding_matches"]
    assert not report["published_reconstruction"]["passed"]
    assert check["published_ci_percent"] == [0, 100]
    assert "Different interval" in check["ci_comparability"]
    target = registry.datasets[current.DATASET]["published_diabetes_targets"][0]
    target["n"] = check["reconstructed_n"]
    target["percent"] = round(check["reconstructed_percent"], 1)
    matched = current.assess(frame(), registry)["published_reconstruction"]["checks"][0]
    assert matched["passed"]
    assert matched["reconstructed_interval"] != matched["published_ci_percent"]
    assert current.assess(frame(), registry)["source_audit_passed"] is False


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "bool_n", "loose_tolerance", "bad_label"]
)
def test_published_target_inventory_is_frozen(registry, change):
    targets = registry.datasets[current.DATASET]["published_diabetes_targets"]
    if change == "missing":
        targets.pop()
    elif change == "duplicate":
        targets[-1] = deepcopy(targets[0])
    elif change == "bool_n":
        targets[0]["n"] = True
    elif change == "loose_tolerance":
        targets[0]["tolerance_pp"] = 1
    else:
        targets[0]["category"] = ["total"]
    with pytest.raises(ValueError):
        current.assess(frame(), registry)
