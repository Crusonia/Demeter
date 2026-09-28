"""Numerical and design checks; all generated individuals are synthetic fixtures."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.integrate import quad
from scipy.optimize._numdiff import approx_derivative

from demeter.analysis.mortality_development import (
    contributions,
    development_report,
    fit,
    integrated_moments,
    survey_covariance,
)
from demeter.schema import EvidenceRegistry

SPEC = EvidenceRegistry.from_yaml("evidence/parameters.yaml").datasets["mortality_development"]


@pytest.mark.parametrize("slope", [0, 1e-12, -1e-12, 0.01, -0.03, 0.15])
def test_analytic_moments_match_independent_quadrature(slope):
    times = np.array([0, 0.5, 5, 15])
    actual = integrated_moments(times, slope, threshold=0.1, terms=24)
    expected = np.array(
        [[quad(lambda u, k=k: u**k * np.exp(slope * u), 0, t)[0] for k in range(3)] for t in times]
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-12)


def test_scores_and_information_match_numerical_derivatives():
    x = np.array([[1, 0, 0], [1, 40, 1], [1, 20, 0]], dtype=float)
    time, event = np.array([2, 5, 8]), np.array([1, 0, 1])
    for age_slope in (0, 0.06, -0.02):
        beta = np.array([-7, age_slope, 0.4])
        _, score, information, _ = contributions(beta, x, time, event, SPEC["integration"])
        numerical_score = approx_derivative(
            lambda b: contributions(b, x, time, event, SPEC["integration"])[0], beta
        )
        numerical_information = -approx_derivative(
            lambda b: contributions(b, x, time, event, SPEC["integration"])[1].sum(axis=0), beta
        )
        np.testing.assert_allclose(score, numerical_score, rtol=1e-6, atol=1e-8)
        np.testing.assert_allclose(information.sum(axis=0), numerical_information, rtol=1e-6)


def fixture():
    rng = np.random.default_rng(421)
    n = 360
    x = np.column_stack([np.ones(n), rng.uniform(0, 59, n), rng.integers(0, 2, n)])
    beta = np.array([-6.5, 0.065, 0.3])
    death_time = np.log1p(-np.log(rng.uniform(size=n)) * beta[1] / np.exp(x @ beta)) / beta[1]
    censor_time = rng.uniform(3, 9, n)
    time = np.minimum(death_time, censor_time)
    event = (death_time <= censor_time).astype(float)
    weights = rng.uniform(1, 5, n)
    design = pd.DataFrame(
        {"SDMVSTRA": np.repeat(np.arange(12), 30), "SDMVPSU": np.tile(np.repeat([1, 2], 15), 12)}
    )
    return x, time, event, weights, design


def test_fit_weight_scale_invariance_and_event_intensity_balance():
    x, time, event, weights, design = fixture()
    domain = np.ones(len(time), dtype=bool)
    first = fit(x, time, event, weights, domain, design, SPEC)
    scaled = fit(x, time, event, weights * 1e6, domain, design, SPEC)
    np.testing.assert_allclose(first["coefficients"], scaled["coefficients"], rtol=1e-8)
    np.testing.assert_allclose(first["covariance"], scaled["covariance"], rtol=1e-8)
    assert first["observed_expected_ratio"] == pytest.approx(1, abs=1e-7)
    assert first["degrees_of_freedom"] == 12
    assert np.linalg.eigvalsh(first["covariance"]).min() > 0


def test_empty_domain_psus_contribute_to_hand_calculated_covariance():
    design = pd.DataFrame({"SDMVSTRA": [1, 1, 2, 2], "SDMVPSU": [1, 2, 1, 2]})
    # First stratum contributes 2*((-1)**2+1**2)=4; second is an empty domain.
    covariance, df = survey_covariance(np.array([[2.0]]), np.array([[-1], [1], [0], [0]]), design)
    assert covariance.item() == 1
    assert df == 2
    with pytest.raises(ValueError, match="Singleton"):
        survey_covariance(np.array([[2.0]]), np.array([[-1], [1], [0]]), design.iloc[:3])


def test_missing_outcomes_zero_followup_and_unidentified_fit_rejected():
    x, time, event, weights, design = fixture()
    domain = np.ones(len(time), dtype=bool)
    with pytest.raises(ValueError, match="No observed deaths"):
        fit(x, time, event * 0, weights, domain, design, SPEC)
    with pytest.raises(ValueError, match="follow-up"):
        fit(x, time * 0, event, weights, domain, design, SPEC)
    with pytest.raises(ValueError, match="vital status"):
        fit(x, time, np.full(len(event), np.nan), weights, domain, design, SPEC)
    with pytest.raises(ValueError, match="unidentified"):
        fit(np.ones_like(x), time, event, weights, domain, design, SPEC)


def test_offline_development_reproduces_registered_estimates_and_exclusions(monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Development rebuild used network or reserved-cycle retrieval")

    monkeypatch.setattr("urllib.request.urlopen", no_network)
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    actual = development_report(registry)
    saved = json.loads(Path("docs/validation/issue-1-mortality-development.json").read_bytes())
    assert actual["source_sha256"] == saved["source_sha256"]
    assert actual["evidence_sha256"] == registry.content_hash
    assert actual["counts"] == saved["counts"]
    counts = actual["counts"]
    assert (
        counts["included_n"] + sum(counts["sequential_exclusions"].values())
        == counts["positive_weight_n"]
    )
    assert not actual["scientific_release_ready"]
    assert not actual["independent_validation_performed"]
    for model, fitted in actual["models"].items():
        np.testing.assert_allclose(
            fitted["covariance"], saved["models"][model]["covariance"], rtol=1e-6, atol=1e-10
        )
        for key, value, interval in zip(
            fitted["coefficient_keys"], fitted["coefficients"], fitted["intervals"], strict=True
        ):
            parameter = registry.parameters[key]
            assert parameter.model_role == "benchmark_only"
            assert parameter.value == pytest.approx(value, rel=1e-6, abs=1e-9)
            np.testing.assert_allclose(
                [parameter.uncertainty.low, parameter.uncertainty.high],
                interval,
                rtol=1e-6,
                atol=1e-9,
            )


def test_iteration_failure_never_returns_estimates():
    x, time, event, weights, design = fixture()
    spec = {**SPEC, "optimizer": {**SPEC["optimizer"], "maximum_iterations": 0}}
    with pytest.raises(ValueError, match="did not converge"):
        fit(x, time, event, weights, np.ones(len(time), dtype=bool), design, spec)
