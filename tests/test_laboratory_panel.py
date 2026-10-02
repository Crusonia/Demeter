"""Synthetic numerical validation; no source records, thresholds or clinical claims."""

from dataclasses import FrozenInstanceError, replace
from itertools import product
import json
from math import exp, fsum, log

import numpy as np
import pytest

from demeter.analysis import laboratory_panel as lab


@pytest.fixture
def settings():
    return lab.FitSettings(
        structure="adjacent",
        initial_rates=((0.1,) * 4, (0.5,) * 4),
        rate_upper_bounds=(4.0,) * 4,
        day_scale=1.0,
        probability_tolerance=1e-12,
        optimizer_maxiter=200,
        optimizer_ftol=1e-10,
        optimizer_gtol=1e-7,
        jacobian_step=1e-5,
        rank_relative_tolerance=1e-8,
    )


@pytest.fixture
def paths():
    # All entry categories, two distinct gaps and observed endpoints. This is a
    # labeled software fixture, not a clinical/source distribution.
    return tuple(
        lab.PanelPath((0.0, gap), (i, j))
        for gap in (1.0, 2.0)
        for i in range(3)
        for j in range(3)
        for _ in range(6 if i == j else 1)
    )


def test_snapshot_and_translation_invariance():
    days, bands = [-7.0, 3.0, 8.0], [0, 1, 2]
    path = lab.PanelPath(days, bands)
    days.append(12)
    bands[1] = 2
    assert path.days == (-7.0, 3.0, 8.0)
    assert path.bands == (0, 1, 2)
    with pytest.raises(FrozenInstanceError):
        path.days = ()
    rates = (0.01, 0.02, 0.03, 0.04)
    original = lab.conditional_log_likelihood(
        [path], rates, "adjacent", probability_tolerance=1e-12
    )
    shifted = lab.conditional_log_likelihood(
        [lab.PanelPath((0, 10, 15), (0, 1, 2))], rates, "adjacent", probability_tolerance=1e-12
    )
    assert shifted == original


@pytest.mark.parametrize(
    "days,bands",
    [
        ([], []),
        ([0, 1], [0]),
        ([0, 0], [0, 1]),
        ([1, 0], [0, 1]),
        ([0, np.inf], [0, 1]),
        ([True], [0]),
        (["0"], [0]),
        ([0], [True]),
        ([0], [1.0]),
        ([0], [np.int64(1)]),
        ([0], [3]),
        ([-1e308, 1e308], [0, 1]),
    ],
)
def test_path_domains(days, bands):
    with pytest.raises(ValueError):
        lab.PanelPath(days, bands)


def test_settings_snapshot_and_domains(settings):
    starts = [[0.1] * 4]
    caps = [4.0] * 4
    snap = replace(settings, initial_rates=starts, rate_upper_bounds=caps)
    starts[0][0] = 3
    caps[0] = 2
    assert snap.initial_rates == ((0.1,) * 4,)
    assert snap.rate_upper_bounds == (4.0,) * 4
    for change in (
        {"initial_rates": []},
        {"initial_rates": ((5.0,) * 4,)},
        {"rate_upper_bounds": (0.0,) * 4},
        {"day_scale": True},
        {"optimizer_maxiter": False},
        {"jacobian_step": 0},
        {"rank_relative_tolerance": 1},
        {"probability_tolerance": 0},
    ):
        with pytest.raises(ValueError):
            replace(settings, **change)


@pytest.mark.parametrize(
    "rates,structure",
    [
        ([0.1] * 3, "adjacent"),
        ([0.1] * 4, "unknown"),
        ([True, 0, 0, 0], "adjacent"),
        ([".1", 0, 0, 0], "adjacent"),
        ([np.inf, 0, 0, 0], "adjacent"),
        ([-1, 0, 0, 0], "adjacent"),
        (np.ma.array([1, 1, 1, 1], mask=[0, 0, 0, 1]), "adjacent"),
    ],
)
def test_generator_domains(rates, structure):
    with pytest.raises(ValueError):
        lab.generator(rates, structure)


def test_generator_and_embedded_two_state_analytic_identity():
    a, b, gap = 0.2, 0.3, 4.0
    q = lab.generator((a, b, 0, 0), "adjacent")
    assert q.tolist() == [[-a, a, 0], [b, -b, 0], [0, 0, 0]]
    p = lab.transition_matrix((a, b, 0, 0), "adjacent", gap, probability_tolerance=1e-12)
    expected = a / (a + b) * (1 - exp(-(a + b) * gap))
    assert p[0, 1] == pytest.approx(expected, abs=1e-14, rel=0)
    assert np.allclose(p.sum(axis=1), 1, atol=1e-14, rtol=0)
    assert p[2].tolist() == [0, 0, 1]
    assert np.array_equal(
        lab.transition_matrix((0, 0, 0, 0), "adjacent", 7, probability_tolerance=1e-12), np.eye(3)
    )


def test_adjacent_endpoints_can_cross_two_bands_and_semigroup():
    rates = (0.1, 0.2, 0.3, 0.4)
    p = lab.transition_matrix(rates, "adjacent", 1, probability_tolerance=1e-12)
    assert p[0, 2] > 0 and p[2, 0] > 0
    p3 = lab.transition_matrix(rates, "adjacent", 3, probability_tolerance=1e-12)
    p2 = lab.transition_matrix(rates, "adjacent", 2, probability_tolerance=1e-12)
    assert np.allclose(p @ p2, p3, atol=1e-14, rtol=0)


def test_normalized_joint_paths_and_single_observation():
    rates = (0.1, 0.2, 0.3, 0.4)
    likelihoods = [
        lab.conditional_log_likelihood(
            [lab.PanelPath((0, 1, 3), (1, j, k))], rates, "adjacent", probability_tolerance=1e-12
        )
        for j, k in product(range(3), repeat=2)
    ]
    assert fsum(exp(value) for value in likelihoods) == pytest.approx(1, abs=1e-14, rel=0)
    assert (
        lab.conditional_log_likelihood(
            [lab.PanelPath((10,), (2,))], rates, "adjacent", probability_tolerance=1e-12
        )
        == 0
    )
    observed = lab.PanelPath((0, 1, 3), (1, 0, 2))
    p1 = lab.transition_matrix(rates, "adjacent", 1, probability_tolerance=1e-12)
    p2 = lab.transition_matrix(rates, "adjacent", 2, probability_tolerance=1e-12)
    assert lab.conditional_log_likelihood(
        [observed], rates, "adjacent", probability_tolerance=1e-12
    ) == pytest.approx(log(p1[1, 0]) + log(p2[0, 2]), abs=1e-14, rel=0)


def test_no_floor_and_underflow_not_impossible(monkeypatch):
    path = lab.PanelPath((0, 1), (0, 2))
    assert (
        lab.conditional_log_likelihood(
            [path], (0, 0, 0, 0), "adjacent", probability_tolerance=1e-12
        )
        == -np.inf
    )
    monkeypatch.setattr(lab, "expm", lambda _: np.eye(3))
    with pytest.raises(ValueError, match="underflow"):
        lab.conditional_log_likelihood(
            [path], (1, 1, 1, 1), "adjacent", probability_tolerance=1e-12
        )


def test_matrix_roundoff_only_not_mass_repair(monkeypatch):
    tiny = np.eye(3)
    tiny[0, 1] = -1e-15
    monkeypatch.setattr(lab, "expm", lambda _: tiny)
    p = lab.transition_matrix((1, 1, 1, 1), "adjacent", 1, probability_tolerance=1e-12)
    assert p[0, 1] == 0
    tiny[0, 1] = -1e-3
    with pytest.raises(ValueError):
        lab.transition_matrix((1, 1, 1, 1), "adjacent", 1, probability_tolerance=1e-12)
    monkeypatch.setattr(lab, "expm", lambda _: np.eye(3) * 0.99)
    with pytest.raises(ValueError, match="conservation"):
        lab.transition_matrix((1, 1, 1, 1), "adjacent", 1, probability_tolerance=1e-12)


def test_summary_preserves_single_paths_and_full_pairs():
    paths = [lab.PanelPath((0,), (0,)), lab.PanelPath((0, 1, 3), (0, 1, 2))]
    summary = lab.transition_summary(paths)
    assert summary["label_paths"] == 2
    assert summary["observations"] == 4
    assert summary["single_observation_paths"] == 1
    assert summary["adjacent_observation_pairs"] == 2
    assert summary["observed_pair_counts"] == [[0, 1, 0], [0, 0, 1], [0, 0, 0]]
    assert summary["gap_range_days"] == [1, 2]
    assert summary["independent_pair_sampling_assumed"] is False


def test_observed_design_rank_and_boundary_stencils(paths, settings):
    result = lab.design_identifiability(paths, (0.2, 0.3, 0.4, 0.5), settings)
    assert result["local_numerical_rank"] == 4
    assert result["distinct_observed_start_band_gap_rows"] == 6
    assert result["difference_schemes"] == ["central"] * 4
    assert result["global_identification_established"] is False
    assert result["practical_identification_established"] is False
    boundary = lab.design_identifiability(paths, (0, 4, 0.4, 0.5), settings)
    assert boundary["difference_schemes"][:2] == [
        "forward_at_or_near_lower_boundary",
        "backward_at_or_near_search_cap",
    ]
    assert all(x > 0 for x in boundary["actual_scaled_difference_denominators"])
    narrow = lab.design_identifiability(
        [lab.PanelPath((0, 1), (0, 0))], (0.2, 0.3, 0.4, 0.5), settings
    )
    assert narrow["local_numerical_rank"] <= 2
    single = lab.design_identifiability([lab.PanelPath((0,), (0,))], (0.2, 0.3, 0.4, 0.5), settings)
    assert single["local_numerical_rank"] == 0


def test_fitted_likelihood_improves_and_nulls_are_distinct(paths, settings):
    fitted = lab.fit_ctmc(paths, settings)
    assert fitted["fit_performed"] is True
    assert (
        fitted["log_likelihood"]["value"]
        >= max(
            lab.conditional_log_likelihood(paths, start, "adjacent", probability_tolerance=1e-12)
            for start in settings.initial_rates
        )
        - 1e-8
    )
    assert fitted["clinical_fit_performed"] is False
    assert fitted["engine_activation_allowed"] is False
    assert len(fitted["multistarts"]) == len(settings.initial_rates)
    iid = lab.fit_iid(paths)
    assert iid["probabilities"] == pytest.approx([1 / 3] * 3, rel=0, abs=1e-14)
    assert iid["log_likelihood"]["value"] == pytest.approx(-len(paths) * log(3), rel=0, abs=1e-12)
    assert (
        lab.no_switching_null(paths)["log_likelihood"]["status"]
        == "negative_infinity_zero_probability"
    )


def test_single_observation_fit_not_fake_identification(settings):
    paths = [lab.PanelPath((0,), (1,))]
    assert lab.fit_ctmc(paths, settings)["failure"] == "no_rate_informative_observation_pairs"
    assert lab.fit_iid(paths)["fit_performed"] is False
    assert lab.no_switching_null(paths)["log_likelihood"]["value"] == 0


def test_failed_multistarts_retain_no_rates_or_private_exception(settings, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("PRIVATE_SOURCE_TOKEN")

    monkeypatch.setattr(lab, "_finite_box_minimize", fail)
    result = lab.fit_ctmc([lab.PanelPath((0, 1), (0, 1))], settings)
    assert result["fit_performed"] is False and result["rates"] is None
    assert len(result["multistarts"]) == 2
    assert "PRIVATE_SOURCE_TOKEN" not in json.dumps(result, allow_nan=False)


def test_forecast_conditioning_and_independent_brier_oracle():
    paths = [lab.PanelPath((0, 1, 2), (0, 1, 1)), lab.PanelPath((0, 2), (2, 0))]
    model = {"kind": "ctmc", "structure": "adjacent", "rates": [0.2, 0.3, 0.4, 0.5]}
    scores = lab.score_predictions(paths, model, probability_tolerance=1e-12)
    one = scores["modes"]["one_step"]
    first = scores["modes"]["first_only"]
    assert one["sum_is_joint_conditional_path_log_likelihood"] is True
    assert first["sum_is_joint_conditional_path_log_likelihood"] is False
    assert one["sum_log_score"]["value"] == pytest.approx(
        lab.conditional_log_likelihood(
            paths, model["rates"], "adjacent", probability_tolerance=1e-12
        ),
        rel=0,
        abs=1e-14,
    )
    p = lab.transition_matrix(model["rates"], "adjacent", 1, probability_tolerance=1e-12)
    p2 = lab.transition_matrix(model["rates"], "adjacent", 2, probability_tolerance=1e-12)
    expected = [
        sum((v - int(i == y)) ** 2 for i, v in enumerate(row))
        for row, y in ((p[0], 1), (p[1], 1), (p2[2], 0))
    ]
    assert one["transition_weighted_mean_brier"] == pytest.approx(
        sum(expected) / 3, rel=0, abs=1e-14
    )
    assert one["equal_label_mean_brier"] == pytest.approx(
        ((expected[0] + expected[1]) / 2 + expected[2]) / 2, rel=0, abs=1e-14
    )
    assert first["sum_log_score"] != one["sum_log_score"]
    impossible = lab.score_predictions(paths, {"kind": "no_switching"}, probability_tolerance=1e-12)
    assert impossible["modes"]["one_step"]["sum_log_score"]["value"] is None
    assert impossible["modes"]["one_step"]["zero_probability_observations"] == 2


def test_profile_reoptimizes_and_discloses_open_boundary(paths, settings):
    fitted = lab.fit_ctmc(paths, settings, identification_diagnostics=False)
    result = lab.profile_rate(paths, fitted, settings, 0, (0, 0.1, 0.2, 1, 4), support_cutoff=3.84)
    assert len(result["points"]) == len({0, 0.1, 0.2, 1, 4, fitted["rates"][0]})
    assert any(p["rate"] == fitted["rates"][0] for p in result["points"])
    assert result["finite_confidence_interval"] is None
    assert result["clinical_confidence_interval"] is False
    assert result["interior_reference_requires_correctly_specified_independent_label_model"] is True
    assert result["points"][0]["converged"] is False
    assert result["structural_zero_probability_grid_points"] == 1
    assert result["points"][0]["structurally_impossible_for_all_nuisance_rates"] is True
    assert result["points"][0]["deviance_status"] == "positive_infinity"


def test_bootstrap_whole_paths_paired_models_and_failures(settings, monkeypatch):
    paths = [
        lab.PanelPath((0, 1, 3), (0, 1, 2)),
        lab.PanelPath((0,), (1,)),
        lab.PanelPath((0, 4), (2, 1)),
    ]
    called, sequence = [], []
    count = 0

    def fake_fit(sample, config, **kwargs):
        nonlocal count
        assert kwargs["identification_diagnostics"] is True
        called.append((config.structure, tuple(id(p) for p in sample)))
        count += 1
        if count == 3:
            return {"fit_performed": False, "failure": "frozen_synthetic_failure"}
        value = sum(len(p.days) for p in sample) / 100
        size = len(lab.EDGES[config.structure])
        rates = [value] * size
        if config.structure == "adjacent":
            sequence.append(rates)
        return {
            "kind": "ctmc",
            "structure": config.structure,
            "fit_performed": True,
            "rates": rates,
            "zero_rate_indices": [],
            "search_cap_indices": [],
        }

    monkeypatch.setattr(lab, "fit_ctmc", fake_fit)
    full = replace(
        settings,
        structure="unrestricted",
        initial_rates=((0.1,) * 6,),
        rate_upper_bounds=(4.0,) * 6,
    )
    report = lab.paired_path_bootstrap(
        paths,
        {"primary": settings, "alternative": full},
        repetitions=4,
        seed=10,
        quantile_levels=(0.025, 0.5, 0.975),
        evaluation_paths=paths,
    )
    assert len(called) == 8
    for left, right in zip(called[::2], called[1::2], strict=False):
        assert left[1] == right[1]
        assert set(left[1]).issubset({id(p) for p in paths})
    assert report["replicates"][1]["failures"] == {"primary": "frozen_synthetic_failure"}
    assert report["joint_rate_summary"]["successful_draws"] == 3
    assert report["per_model_rate_summaries"]["alternative"]["successful_draws"] == 4
    assert report["failed_draws_redrawn"] is False
    assert report["evaluation_resampled_separately_and_paired_across_models"] is True
    assert report["clinical_fit_performed"] is False
    assert report["engine_activation_allowed"] is False
    assert all(len(x["models"]["alternative"]["rates"]) == 6 for x in report["replicates"])
    assert len(report["predictive_difference_coordinates"]) == 8
    assert {x["metric"] for x in report["predictive_difference_coordinates"]} == {
        "log_score",
        "brier",
    }
    json.dumps(report, allow_nan=False)


def test_bootstrap_covariance_independent_outer_product_oracle(settings, monkeypatch):
    paths = [lab.PanelPath((0, 1), (0, 1)), lab.PanelPath((0, 1, 2), (2, 1, 0))]

    def fake_fit(sample, config, **kwargs):
        assert kwargs["identification_diagnostics"] is True
        n = sum(len(p.days) for p in sample)
        return {
            "kind": "ctmc",
            "structure": "adjacent",
            "fit_performed": True,
            "rates": [n, 2 * n, 0, 1],
            "zero_rate_indices": [2],
            "search_cap_indices": [],
            "identification": {
                "available": True,
                "local_numerical_rank": 2,
                "full_column_rank_at_point": False,
                "singular_values": [1, 0.5, 0, 0],
                "difference_schemes": ["central"] * 4,
            },
        }

    monkeypatch.setattr(lab, "fit_ctmc", fake_fit)
    result = lab.paired_path_bootstrap(
        paths,
        {"primary": settings},
        repetitions=6,
        seed=15,
        quantile_levels=(0, 0.5, 1),
        include_iid=False,
    )
    rows = [x["models"]["primary"]["rates"] for x in result["replicates"]]
    means = [sum(r[j] for r in rows) / 6 for j in range(4)]
    expected = [
        [sum((r[i] - means[i]) * (r[j] - means[j]) for r in rows) / 5 for j in range(4)]
        for i in range(4)
    ]
    assert np.allclose(result["joint_rate_summary"]["covariance"], expected, atol=1e-14, rtol=0)
    assert all(x["models"]["primary"]["zero_rate_indices"] == [2] for x in result["replicates"])
    assert all(
        x["models"]["primary"]["identification"]["full_column_rank_at_point"] is False
        for x in result["replicates"]
    )
    assert result["joint_rate_summary"]["successful_draws"] == 6
    assert result["rank_deficient_draws_excluded_from_covariance"] is False


def test_rank_failure_does_not_erase_converged_fit(paths, settings, monkeypatch):
    def unavailable(*args, **kwargs):
        raise ValueError("PRIVATE_DIAGNOSTIC_TOKEN")

    monkeypatch.setattr(lab, "design_identifiability", unavailable)
    result = lab.fit_ctmc(paths, settings)
    assert result["fit_performed"] is True
    assert result["identification"]["available"] is False
    assert result["identification"]["full_column_rank_at_point"] is None
    assert "PRIVATE_DIAGNOSTIC_TOKEN" not in json.dumps(result, allow_nan=False)


def test_bootstrap_numeric_prediction_failures_distinct_from_fit_failures(settings, monkeypatch):
    paths = [lab.PanelPath((0, 1), (0, 1)), lab.PanelPath((0, 1), (1, 2))]

    def fake_fit(*args, **kwargs):
        return {
            "kind": "ctmc",
            "structure": "adjacent",
            "fit_performed": True,
            "rates": [0.1] * 4,
            "zero_rate_indices": [],
            "search_cap_indices": [],
            "identification": None,
        }

    def fail_prediction(*args, **kwargs):
        raise ValueError("PRIVATE_PREDICTION_TOKEN")

    monkeypatch.setattr(lab, "fit_ctmc", fake_fit)
    monkeypatch.setattr(lab, "score_predictions", fail_prediction)
    report = lab.paired_path_bootstrap(
        paths,
        {"primary": settings},
        repetitions=2,
        seed=0,
        quantile_levels=(0.025, 0.975),
        evaluation_paths=paths,
    )
    assert report["joint_rate_summary"]["successful_draws"] == 2
    assert report["predictive_difference_summaries"]["primary"]["successful_draws"] == 0
    assert all(not x["failures"] for x in report["replicates"])
    assert all(
        x["prediction_status"]["primary"] == "numerical_prediction_failure"
        for x in report["replicates"]
    )
    assert "PRIVATE_PREDICTION_TOKEN" not in json.dumps(report, allow_nan=False)


@pytest.mark.parametrize(
    "structure,rates",
    [
        ("adjacent", (0.1, 0.2, 0.3, 0.4)),
        ("unrestricted", (0.1, 0.2, 0.3, 0.4, 0.2, 0.3)),
        ("unrestricted", (1, 0, 1, 0, 0, 1)),
    ],
)
def test_sufficient_likelihood_and_frechet_gradient_against_direct_expm(structure, rates):
    paths = tuple(
        lab.PanelPath((0, gap), (i, j))
        for gap in (0.2, 1, 4)
        for i, j in product(range(3), repeat=2)
    )
    compiled = lab._compile_pairs(paths)
    value, gradient, corrections = lab._compiled_likelihood(rates, structure, compiled, 1e-12)
    direct = lab.conditional_log_likelihood(paths, rates, structure, probability_tolerance=1e-12)
    assert value == pytest.approx(direct, abs=1e-11, rel=0)
    assert corrections["kernel_method"] in (
        "spectral_frechet",
        "hybrid_direct_expm_frechet_fallback",
    )
    for k, rate in enumerate(rates):
        upper, lower = list(rates), list(rates)
        step = 1e-6
        upper[k] += step
        lower[k] -= step if rate > step else 0
        denominator = upper[k] - lower[k]
        difference = (
            lab.conditional_log_likelihood(paths, upper, structure, probability_tolerance=1e-12)
            - lab.conditional_log_likelihood(paths, lower, structure, probability_tolerance=1e-12)
        ) / denominator
        assert gradient[k] == pytest.approx(difference, abs=1e-3 if rate == 0 else 1e-6, rel=0)


def test_defective_generator_direct_fallback_and_repeated_records():
    paths = [lab.PanelPath((0, 2), (0, 2))] * 3
    rates = (1, 0, 1, 0)
    value, gradient, corrections = lab._compiled_likelihood(
        rates, "adjacent", lab._compile_pairs(paths), 1e-12
    )
    # Two successive equal-rate exponential waiting times: Erlang CDF.
    assert value == pytest.approx(3 * log(1 - exp(-2) * (1 + 2)), abs=1e-12, rel=0)
    assert corrections["kernel_method"] == "direct_expm_frechet_fallback"
    assert np.isfinite(gradient).all()
    assert lab._compile_pairs(paths)[1][0, 0, 2] == 3


def test_three_hundred_gap_sufficient_compilation_preserves_path_likelihood():
    paths = tuple(lab.PanelPath((0, k / 10), (k % 3, (k + 1) % 3)) for k in range(1, 301))
    rates = (0.1, 0.2, 0.3, 0.4)
    compiled = lab._compile_pairs(paths)
    assert compiled[0].shape == (300,)
    assert int(compiled[1].sum()) == 300
    fast, _, _ = lab._compiled_likelihood(rates, "adjacent", compiled, 1e-12)
    direct = lab.conditional_log_likelihood(paths, rates, "adjacent", probability_tolerance=1e-12)
    assert fast == pytest.approx(direct, abs=1e-10, rel=0)


def test_structurally_impossible_pair_cannot_gain_spectral_roundoff_support(monkeypatch):
    paths = (lab.PanelPath((0.0, 10.0), (0, 2)),)

    def forbidden(*args):
        pytest.fail("Exact graph impossibility must precede numerical kernels")

    monkeypatch.setattr(lab, "_spectral_kernels", forbidden)
    value, gradient, diagnostic = lab._compiled_likelihood(
        (0.0, 0.0, 0.1, 0.2), "adjacent", lab._compile_pairs(paths), 1e-12
    )
    assert value == -np.inf
    assert np.array_equal(gradient, np.zeros(4))
    assert diagnostic["kernel_method"] == "exact_structural_zero_probability"


def test_fitted_reports_have_explicit_edge_order_and_python_json_booleans(paths, settings):
    result = lab.fit_ctmc(paths, settings)
    assert result["parameter_edges"] == [[0, 1], [1, 0], [1, 2], [2, 1]]
    assert all(type(start["converged"]) is bool for start in result["multistarts"])
    assert all(
        start["direct_likelihood_gradient_verified"]
        for start in result["multistarts"]
        if start["converged"]
    )
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("magnitude", [1e-7, 1e-9, 1e-12])
def test_tiny_reachable_probability_relative_accuracy(magnitude):
    paths = (lab.PanelPath((0.0, 1.0), (0, 2)),)
    rates = tuple(magnitude * k for k in (1, 2, 3, 4))
    value, gradient, diagnostic = lab._compiled_likelihood(
        rates, "adjacent", lab._compile_pairs(paths), 1e-10
    )
    direct = lab.conditional_log_likelihood(paths, rates, "adjacent", probability_tolerance=1e-10)
    assert value == pytest.approx(direct, abs=1e-10, rel=0)
    assert "fallback" in diagnostic["kernel_method"]
    assert np.isfinite(gradient).all()
    # At very small rates, the two required forward switches have log derivatives
    # approaching reciprocal rates; each reverse effect stays finite.
    assert gradient[0] * rates[0] == pytest.approx(1, abs=1e-6, rel=0)
    assert gradient[2] * rates[2] == pytest.approx(1, abs=1e-6, rel=0)


@pytest.mark.parametrize("case", ["rare_switch", "central_band"])
def test_optimizer_cannot_accept_unchanged_nonstationary_start(settings, case):
    if case == "rare_switch":
        paths = [lab.PanelPath((0.0, 1.0), (0, 0))] * 100
        paths += [lab.PanelPath((0.0, 1.0), (0, 1))]
        known_better = (0.01, 0.1, 0.1, 0.1)
    else:
        paths = [lab.PanelPath((0.0, 1.0), (0, 1))] * 100
        paths += [lab.PanelPath((0.0, 1.0), (2, 1))] * 100
        paths += [lab.PanelPath((0.0, 1.0), (1, 0)), lab.PanelPath((0.0, 1.0), (1, 2))]
        known_better = (4.0, 0.01, 0.01, 4.0)
    result = lab.fit_ctmc(paths, replace(settings, optimizer_maxiter=1000))
    assert result["fit_performed"] is True
    assert (
        result["log_likelihood"]["value"]
        >= lab.conditional_log_likelihood(
            paths, known_better, "adjacent", probability_tolerance=settings.probability_tolerance
        )
        - 1e-9
    )
    assert all(
        row["projected_gradient_norm"] <= settings.optimizer_gtol
        for row in result["multistarts"]
        if row["converged"]
    )
    assert all(
        row["rates"] != list(start)
        for row, start in zip(result["multistarts"], settings.initial_rates, strict=True)
        if row["converged"]
    )


def test_boundary_optimum_retains_exact_zero_and_kkt(settings):
    paths = [lab.PanelPath((0.0, 1.0), (i, i)) for i in range(3)]
    result = lab.fit_ctmc(paths, settings)
    assert result["fit_performed"] is True
    assert result["rates"] == [0.0] * 4
    assert result["zero_rate_indices"] == list(range(4))
    assert result["log_likelihood"]["value"] == 0


def test_mixed_scale_eigendecomposition_error_triggers_direct_fallback():
    # A well-conditioned eigensystem can still lose relative precision in
    # extremely small stationary components. All quantities here are synthetic.
    rates = (
        6.088895995813664e-10,
        1.470282811502229e-7,
        0.5669977847731398,
        3.001808973929321e-10,
        7.92922677192857e-5,
        3.4279438324017854e-6,
    )
    gaps = (0.030428930245057568, 24642.559085269484, 5956.564767699134)
    paths = tuple(
        lab.PanelPath((0.0, gap), (i, j)) for gap in gaps for i, j in product(range(3), repeat=2)
    )
    value, gradient, diagnostic = lab._compiled_likelihood(
        rates, "unrestricted", lab._compile_pairs(paths), 1e-10
    )
    direct = lab.conditional_log_likelihood(
        paths, rates, "unrestricted", probability_tolerance=1e-10
    )
    assert value == pytest.approx(direct, abs=1e-10, rel=0)
    assert "fallback" in diagnostic["kernel_method"]
    q = lab.generator(rates, "unrestricted")
    expected = []
    for i, j in lab.EDGES["unrestricted"]:
        direction = np.zeros((3, 3))
        direction[i, j], direction[i, i] = 1, -1
        terms = []
        for gap in gaps:
            matrix = lab.expm(q * gap)
            derivative = lab.expm_frechet(q * gap, direction * gap, compute_expm=False)
            terms.extend((derivative / matrix).ravel())
        expected.append(fsum(terms))
    assert np.allclose(gradient, expected, rtol=1e-10, atol=1e-8)
