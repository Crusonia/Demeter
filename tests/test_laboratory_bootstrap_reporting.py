"""Invented aggregate fixtures only; no source records or empirical fitting."""

import copy
import json
from unittest.mock import patch

import numpy as np
import pytest

from demeter.analysis import ipop_a1c as a1c
from demeter.analysis import laboratory_bootstrap_reporting as reporting
from demeter.analysis import laboratory_panel as lab

LEVELS = (0.025, 0.5, 0.975)


def synthetic_bootstrap():
    """Known joint/partial/failure supports, never a scientific bootstrap result."""
    values = [
        [0.1 * (i + 1) for i in range(8)],
        [None, None, 0.3, 0.4, None, None, 0.7, 0.8],
        [0.2, None, 0.4, None, 0.6, 0.7, 0.8, 0.9],
        [0.05 * (i + 1) for i in range(8)],
    ]
    records = []
    for index, vector in enumerate(values):
        detail = {"one_step": {}, "first_only": {}}
        for coordinate, value in zip(reporting.predictive_coordinates(), vector, strict=True):
            key = coordinate["weighting"] + ("_brier" if coordinate["metric"] == "brier" else "")
            detail[coordinate["mode"]][key] = {
                "value": value,
                "status": "finite"
                if value is not None
                else "unavailable_or_nonfinite_difference"
                if coordinate["metric"] == "log_score"
                else "unavailable",
            }
        records.append(
            {
                "replicate": index,
                "failures": {},
                "models": {"adjacent": {"fit_performed": True}},
                "predictive_score_differences_vs_iid": {"adjacent": detail},
                "prediction_status": {
                    "adjacent": "performed_finite"
                    if all(v is not None for v in vector)
                    else "nonfinite_or_unavailable_scores"
                },
            }
        )
    records.extend(
        [
            {
                "replicate": 4,
                "failures": {},
                "models": {"adjacent": {"fit_performed": True}},
                "predictive_score_differences_vs_iid": {
                    "adjacent": {"failure": "numerical_prediction_failure"}
                },
                "prediction_status": {"adjacent": "numerical_prediction_failure"},
            },
            {
                "replicate": 5,
                "failures": {"adjacent": "no_converged_finite_multistart"},
                "models": {"adjacent": {"fit_performed": False}},
                "predictive_score_differences_vs_iid": {},
                "prediction_status": {},
            },
            {
                "replicate": 6,
                "failures": {"iid": "no_post_first_observations"},
                "models": {"adjacent": {"fit_performed": True}},
                "predictive_score_differences_vs_iid": {},
                "prediction_status": {},
            },
        ]
    )
    return {
        "repetitions_requested": 7,
        "repetitions_attempted": 7,
        "failed_draws_redrawn": False,
        "predictive_difference_coordinates": reporting.predictive_coordinates(),
        "replicates": records,
        "predictive_difference_summaries": {
            "adjacent": lab._sample_summary([values[0], values[3]], LEVELS)
        },
    }


def test_partial_brier_support_preserves_original_joint_and_separate_covariances(monkeypatch):
    source = synthetic_bootstrap()
    original = copy.deepcopy(source)

    def forbidden(*args, **kwargs):
        pytest.fail("Aggregate reporting cannot read source records or fit a model")

    monkeypatch.setattr(lab, "fit_ctmc", forbidden)
    monkeypatch.setattr(a1c, "analyze_cache", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    report = reporting.summarize_predictive_bootstrap(source, quantile_levels=LEVELS)
    assert source == original
    model = report["models"]["adjacent"]
    assert (
        model["complete_vector"]["summary"] == source["predictive_difference_summaries"]["adjacent"]
    )
    assert model["complete_vector"]["finite_draws"] == 2
    assert model["complete_vector"]["nominal_contributing_draw_resolution"] == 0.5
    assert model["metric_blocks"]["log_score"]["finite_draws"] == 2
    brier = model["metric_blocks"]["brier"]
    assert brier["coordinate_indices"] == [2, 3, 6, 7]
    assert brier["finite_draws"] == 3
    assert brier["unavailable_draws"] == 4
    assert brier["nominal_contributing_draw_resolution"] == 1 / 3
    rows = np.asarray([[0.3, 0.4, 0.7, 0.8], [0.3, 0.4, 0.7, 0.8], [0.15, 0.2, 0.35, 0.4]])
    assert np.allclose(brier["summary"]["covariance"], np.cov(rows, rowvar=False), atol=1e-15)
    assert np.allclose(brier["summary"]["quantiles"], np.quantile(rows, LEVELS, axis=0))
    assert [row["finite_draws"] for row in model["per_coordinate"]] == [3, 2, 4, 3, 3, 3, 4, 4]
    assert model["per_coordinate"][1]["status_counts"] == {
        "finite": 2,
        "not_scored_fit_unavailable": 1,
        "not_scored_iid_fit_unavailable": 1,
        "numerical_prediction_failure": 1,
        "unavailable_or_nonfinite_difference": 2,
    }
    assert model["fit_status_counts"] == {"performed": 6, "unavailable": 1}
    assert model["covariance_uses_pairwise_deletion"] is False
    assert report["clinical_fit_performed"] is False
    assert report["engine_activation_allowed"] is False


def test_retained_vectors_reconstruct_every_summary_without_private_payloads():
    source = synthetic_bootstrap()
    source["replicates"][0]["PRIVATE_PARTICIPANT_LABEL"] = "PRIVATE_PATH_AND_CLOCK"
    source["replicates"][0]["models"]["adjacent"]["source_rows"] = "PRIVATE_SOURCE_ROWS"
    report = reporting.summarize_predictive_bootstrap(source, quantile_levels=LEVELS)
    vectors = report["replicate_score_vectors"]["adjacent"]
    assert len(vectors) == 7
    assert [row["replicate"] for row in vectors] == list(range(7))
    assert all(len(row["values"]) == len(row["coordinate_status"]) == 8 for row in vectors)
    rebuilt = reporting.summarize_predictive_vectors(vectors, quantile_levels=LEVELS)
    assert rebuilt == report["models"]["adjacent"]
    serialized = json.dumps(report, allow_nan=False)
    assert "PRIVATE_" not in serialized
    assert '"source_rows"' not in serialized
    assert '"rates"' not in serialized


def test_legacy_zero_support_logs_do_not_erase_finite_brier_coordinates():
    settings = a1c.settings_for(a1c.load_protocol(), "adjacent")
    training = (lab.PanelPath((0, 1), (0, 0)),)
    evaluation = (lab.PanelPath((0, 1), (0, 1)),)

    def toy_fit(*args, **kwargs):
        return {
            "kind": "ctmc",
            "structure": "adjacent",
            "fit_performed": True,
            "rates": [0.1] * 4,
            "zero_rate_indices": [],
            "search_cap_indices": [],
            "identification": None,
        }

    with patch.object(lab, "fit_ctmc", toy_fit):
        source = lab.paired_path_bootstrap(
            training,
            {"adjacent": settings},
            repetitions=2,
            seed=0,
            quantile_levels=LEVELS,
            evaluation_paths=evaluation,
        )
    report = reporting.summarize_predictive_bootstrap(source, quantile_levels=LEVELS)
    model = report["models"]["adjacent"]
    assert model["complete_vector"]["finite_draws"] == 0
    assert model["metric_blocks"]["log_score"]["finite_draws"] == 0
    assert model["metric_blocks"]["brier"]["finite_draws"] == 2
    assert model["complete_vector"]["nominal_contributing_draw_resolution"] is None
    assert model["unsupported_log_difference_causes_identified"] is False
    assert model["per_coordinate"][0]["status_counts"] == {"unavailable_or_nonfinite_difference": 2}


def test_one_finite_draw_is_counted_without_fabricated_covariance_or_quantiles():
    source = reporting.summarize_predictive_bootstrap(synthetic_bootstrap(), quantile_levels=LEVELS)
    vectors = copy.deepcopy(source["replicate_score_vectors"]["adjacent"])
    for row in vectors[1:]:
        row.update(
            fit_available=False,
            fit_status="unavailable",
            prediction_status="not_scored_fit_unavailable",
            values=[None] * 8,
            coordinate_status=["not_scored_fit_unavailable"] * 8,
        )
    report = reporting.summarize_predictive_vectors(vectors, quantile_levels=LEVELS)
    for block in [
        report["complete_vector"],
        *report["metric_blocks"].values(),
        *report["per_coordinate"],
    ]:
        assert block["finite_draws"] == 1
        assert block["nominal_contributing_draw_resolution"] == 1
        assert block["summary"]["available"] is False
        assert block["summary"]["covariance"] is None
        assert block["summary"]["quantiles"] is None


@pytest.mark.parametrize("attack", ("support", "finite_nan", "finite_inf", "floor", "fit", "order"))
def test_forged_retained_vector_controls_reject(attack):
    report = reporting.summarize_predictive_bootstrap(synthetic_bootstrap(), quantile_levels=LEVELS)
    vectors = copy.deepcopy(report["replicate_score_vectors"]["adjacent"])
    if attack == "support":
        vectors[1]["prediction_status"] = "performed_finite"
    elif attack == "finite_nan":
        vectors[0]["values"][0] = float("nan")
    elif attack == "finite_inf":
        vectors[0]["values"][0] = float("inf")
    elif attack == "floor":
        vectors[1]["values"][0] = 0.0
    elif attack == "fit":
        vectors[5].update(fit_available=True, fit_status="performed")
    else:
        vectors[1]["replicate"] = 0
    with pytest.raises(ValueError):
        reporting.summarize_predictive_vectors(vectors, quantile_levels=LEVELS)


@pytest.mark.parametrize("attack", ("legacy_summary", "redraw", "count", "coordinate_order"))
def test_legacy_outer_drift_rejects_instead_of_replacing_joint_estimates(attack):
    source = synthetic_bootstrap()
    if attack == "legacy_summary":
        source["predictive_difference_summaries"]["adjacent"]["successful_draws"] += 1
    elif attack == "redraw":
        source["failed_draws_redrawn"] = True
    elif attack == "count":
        source["repetitions_attempted"] = 6
    else:
        source["predictive_difference_coordinates"].reverse()
    with pytest.raises(ValueError):
        reporting.summarize_predictive_bootstrap(source, quantile_levels=LEVELS)
