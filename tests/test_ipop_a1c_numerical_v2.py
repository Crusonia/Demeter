"""Adaptive numerical version contracts; synthetic software validation only."""

import copy
import hashlib
from pathlib import Path

import pytest

from demeter.analysis import ipop_a1c as a1c
from demeter.analysis import laboratory_panel as lab
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
METHOD = "exact_box_quadratic_v2"


def test_v2_policy_pins_the_preserved_failed_attempt(tmp_path):
    policy = a1c.load_numerical_protocol(numerical_method=METHOD)
    prior = ROOT / policy["prior_empirical_result_path"]
    assert hashlib.sha256(prior.read_bytes()).hexdigest() == a1c.V1_RESULT_SHA256
    assert policy["statistical_selection_changed"] is False
    assert policy["scientific_acceptance_changed"] is False
    assert policy["engine_activation_allowed"] is False
    edited = tmp_path / "amendment.json"
    edited.write_bytes(a1c.NUMERICAL_V2_PATH.read_bytes() + b" ")
    with pytest.raises(ValueError, match="frozen_numerical_contract"):
        a1c.load_numerical_protocol(edited, numerical_method=METHOD)
    with pytest.raises(ValueError, match="frozen_numerical_contract"):
        a1c.load_numerical_protocol(numerical_method="unknown")


@pytest.mark.parametrize("field", ["numerical_method", "model_role", "prior_result_sha256"])
def test_v2_registry_drift_precedes_source_cache(field, monkeypatch, tmp_path):
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    registry.datasets["ipop_a1c_working_fit_v2"][field] = "unverified"
    monkeypatch.setattr(EvidenceRegistry, "from_yaml", lambda *args: registry)

    def forbidden(*args, **kwargs):
        pytest.fail("Numerical registry drift must stop before source cache access")

    monkeypatch.setattr("demeter.data.ipop.load_sources", forbidden)
    with pytest.raises(ValueError, match="registry_contract"):
        a1c.analyze_cache(tmp_path, numerical_method=METHOD)


def test_synthetic_v2_propagates_version_without_changing_selection(monkeypatch):
    # Two synthetic singleton paths make all fits explicitly unavailable. The
    # 200 prescribed bootstrap attempts still run; no empirical bytes are used.
    paths = {
        "calibration": (lab.PanelPath((0.0,), (0,)),),
        "evaluation": (lab.PanelPath((0.0,), (1,)),),
    }
    selection = {"synthetic_fixture_only": True}
    monkeypatch.setattr(
        a1c, "_prepare", lambda *args, **kwargs: (paths, copy.deepcopy(selection), {})
    )
    report = a1c.analyze_bytes(b"", b"", protocol=a1c.load_protocol(), numerical_method=METHOD)
    assert report["analysis_completed"] is True, report["failure_stage"]
    assert report["analysis_id"] == "ipop_a1c_conditional_working_fit_v2"
    assert report["selection"] == selection
    assert report["validation_only"] is True
    assert report["provenance"]["acquisition_receipts_verified"] is False
    assert report["provenance"]["numerical_amendment_sha256"] == a1c.NUMERICAL_V2_SHA256
    assert report["provenance"]["statistical_selection_changed"] is False
    for name in ("adjacent", "unrestricted"):
        assert report["models"][name]["numerical_method"] == METHOD
        assert report["models"][name]["rates"] is None
    assert report["joint_uncertainty"]["numerical_method"] == METHOD
    assert report["joint_uncertainty"]["repetitions_attempted"] == 200
    assert report["joint_uncertainty"]["dispositions"]["failed_primary_fits"] == 200
    assert report["clinical_fit_performed"] is False
    assert report["scientific_acceptance_changed"] is False
    assert report["engine_activation_allowed"] is False


def test_v1_numerical_policy_remains_default():
    assert a1c.load_numerical_protocol() == a1c.load_numerical_protocol(numerical_method="v1")
    assert a1c.load_numerical_protocol()["protocol_id"] == "ipop_a1c_numerical_amendment_v1"
