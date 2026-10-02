"""Synthetic version-binding audits; never scientific artifacts or v2 evidence.

Fixtures deliberately forge a v2 empirical envelope from the preserved PUBLIC
failed-null v1 aggregate and its public source/selection pins. Toy profile records
exist only to reach profile method guards; they are not likelihood profiles. These
tests exercise registration semantics after refreshing result checksums, without
participant data, cache access, acquisition, or any empirical optimization.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from demeter.analysis import ipop_a1c as a1c
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]
METHOD = "exact_box_quadratic_v2"
RESULT_PATH = "docs/validation/ipop-a1c-working-result-v2.json"
METHOD_LOCATIONS = (
    ("provenance", "numerical_method"),
    ("models", "adjacent", "numerical_method"),
    ("models", "unrestricted", "numerical_method"),
    ("joint_uncertainty", "numerical_method"),
    ("profiles", "adjacent", 0, "numerical_method"),
    ("profiles", "unrestricted", 0, "numerical_method"),
)


@pytest.fixture
def binding_fixture(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Synthetic version binding must not acquire, parse, or optimize source data")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr(a1c, "analyze_cache", forbidden)
    monkeypatch.setattr(a1c, "analyze_bytes", forbidden)
    monkeypatch.setattr(a1c.lab, "fit_ctmc", forbidden)
    for relative in (
        "docs/validation/ipop-a1c-working-result-v1.json",
        "docs/validation/ipop-a1c-numerical-amendment-v2.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    prior_bytes = (tmp_path / "docs/validation/ipop-a1c-working-result-v1.json").read_bytes()
    assert hashlib.sha256(prior_bytes).hexdigest() == a1c.V1_RESULT_SHA256
    report = json.loads(prior_bytes)
    assert report["models"]["adjacent"]["rates"] is None
    assert report["models"]["unrestricted"]["rates"] is None
    # Deliberately synthetic envelope, not a claim that v2 analysis was performed.
    # Immutable public source and selection pins remain copied without alteration.
    report["analysis_id"] = "ipop_a1c_conditional_working_fit_v2"
    report["synthetic_version_binding_fixture_only"] = True
    report["provenance"].update(
        numerical_method=METHOD,
        statistical_selection_changed=False,
        numerical_amendment_sha256=a1c.NUMERICAL_V2_SHA256,
        prior_empirical_result_sha256=a1c.V1_RESULT_SHA256,
    )
    for name in ("adjacent", "unrestricted"):
        report["models"][name]["numerical_method"] = METHOD
        report["profiles"][name] = [
            {"numerical_method": METHOD, "synthetic_profile_method_fixture_only": True}
        ]
    report["joint_uncertainty"]["numerical_method"] = METHOD
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    return tmp_path, registry, report


def _register_rehashed_fixture(root, registry, report):
    registry = copy.deepcopy(registry)
    raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    (root / RESULT_PATH).write_bytes(raw)
    spec = registry.datasets["ipop_a1c_working_fit_v2"]
    spec["working_rate_parameters"]["value"] = None
    spec["working_rate_parameters"]["estimation_status"] = (
        "conditional_analysis_completed_primary_estimate_unresolved"
    )
    # Refresh outer integrity so rejection must come from version semantics.
    spec["result"] = {
        "path": RESULT_PATH,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "estimated_parameters": {
            "primary_rates_per_source_day": None,
            "general_rates_per_source_day": None,
            "iid_followup_band_probabilities": report["models"]["iid"]["probabilities"],
        },
    }
    return registry


@pytest.mark.parametrize("toy_profiles", (False, True))
def test_matching_v2_binding_metadata_control_passes(binding_fixture, toy_profiles):
    root, registry, report = binding_fixture
    if not toy_profiles:
        report["profiles"] = {"adjacent": None, "unrestricted": None}
    registered = _register_rehashed_fixture(root, registry, report)
    a1c._registry_contract(registered, a1c.load_protocol(), root, numerical_method=METHOD)


@pytest.mark.parametrize("location", METHOD_LOCATIONS)
@pytest.mark.parametrize("attack", ("missing", "wrong"))
def test_rehashed_missing_or_v1_method_claim_rejects(binding_fixture, location, attack):
    root, registry, report = binding_fixture
    target = report
    for key in location[:-1]:
        target = target[key]
    if attack == "missing":
        del target[location[-1]]
    else:
        target[location[-1]] = "v1"
    registered = _register_rehashed_fixture(root, registry, report)
    with pytest.raises(ValueError, match="registry_contract"):
        a1c._registry_contract(registered, a1c.load_protocol(), root, numerical_method=METHOD)


def test_rehashed_changed_statistical_selection_claim_rejects(binding_fixture):
    root, registry, report = binding_fixture
    report["provenance"]["statistical_selection_changed"] = True
    registered = _register_rehashed_fixture(root, registry, report)
    with pytest.raises(ValueError, match="registry_contract"):
        a1c._registry_contract(registered, a1c.load_protocol(), root, numerical_method=METHOD)
