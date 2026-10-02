"""Pinned additive numerical replay; no empirical observations or fitting."""

from copy import deepcopy
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def verifier():
    namespace = runpy.run_path(str(ROOT / "scripts/verify_longitudinal_probability_contract.py"))
    return namespace["verify"].__globals__


def test_additive_current_code_replay_preserves_fixture_and_closed_gates(verifier):
    report = verifier["verify"]()
    assert report["software_checks_passed"] is True
    assert report["clinical_fit_allowed"] is False
    assert report["engine_activation_allowed"] is False
    assert report["scientific_release_ready"] is False
    assert all(
        contribution["numerical_input_deviations"]["inputs_repaired"] is False
        for contribution in report["contributions"].values()
    )


def test_receipt_byte_hash_is_required(verifier):
    with pytest.raises(ValueError, match="checksum"):
        verifier["_pinned"](verifier["REPLAY_PATH"], "0" * 64)


def test_log_contributions_use_their_separate_registered_numeric_tolerance(verifier):
    expected = {"likelihood": 0.5, "contribution": {"log_likelihood": -10.0}}
    actual = {"likelihood": 0.5, "contribution": {"log_likelihood": -10.00001}}
    assert verifier["_matches"](actual, expected, 1e-12, 1e-4)
    actual["likelihood"] += 1e-8
    assert verifier["_matches"](actual, expected, 1e-12, 1e-4) is False


def test_implementation_drift_fails_before_math(verifier, monkeypatch):
    read = verifier["_pinned"]

    def changed_receipt(path, expected):
        result = read(path, expected)
        if path == verifier["REPLAY_PATH"]:
            result = deepcopy(result)
            for name in result["current_implementation_sha256"]:
                result["current_implementation_sha256"][name] = "0" * 64
        return result

    def forbidden(_registry):
        raise AssertionError("Changed implementation reached arithmetic")

    monkeypatch.setitem(verifier, "_pinned", changed_receipt)
    monkeypatch.setitem(verifier, "likelihood_software_report", forbidden)
    with pytest.raises(ValueError, match="implementation checksum"):
        verifier["verify"]()


def test_registered_provenance_drift_fails_before_math(verifier, monkeypatch):
    registry = verifier["load_likelihood_registry"](ROOT / "evidence/parameters.yaml")
    registry.parameters["longitudinal_toy_n_to_p_rate"].notes = "ALTERED_PROVENANCE"
    monkeypatch.setitem(verifier, "load_likelihood_registry", lambda _: registry)

    def forbidden(_registry):
        raise AssertionError("Changed provenance reached arithmetic")

    monkeypatch.setitem(verifier, "likelihood_software_report", forbidden)
    with pytest.raises(ValueError, match="input provenance"):
        verifier["verify"]()


@pytest.mark.parametrize(
    "actual,expected",
    [
        ({"gate": 0}, {"gate": False}),
        ({"result": 0.5}, {"result": 0.6}),
        ({"result": 0.5, "extra": 1}, {"result": 0.5}),
        ([1, 2], [1]),
        ({"result": float("nan")}, {"result": 0.5}),
    ],
)
def test_comparison_cannot_hide_type_scope_or_numeric_drift(verifier, actual, expected):
    assert verifier["_matches"](actual, expected, 1e-10) is False
