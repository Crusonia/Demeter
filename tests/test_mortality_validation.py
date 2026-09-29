"""Pre-outcome analytic checks for the frozen temporal mortality evaluator."""

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import t

from demeter.analysis.mortality_validation import (
    PROTOCOL,
    evaluate,
    event_ratio,
    load_protocol,
    read_validation_store,
    survey_mean,
    survey_variance,
)
from demeter.schema import EvidenceRegistry


def design():
    return pd.DataFrame({"SDMVSTRA": [1, 1, 2, 2, 3, 3], "SDMVPSU": [1, 2, 1, 2, 1, 2]})


def test_domain_mean_matches_hand_calculation_including_empty_psus():
    domain = np.array([True, False, True, True, False, False])
    result = survey_mean([1, np.nan, 3, 5, np.nan, np.nan], np.ones(6), domain, design(), 0.95)
    assert result["estimate"] == 3
    assert result["variance"] == pytest.approx(8 / 9)
    assert result["design_degrees_of_freedom"] == 3
    assert result["domain_degrees_of_freedom"] == 1
    assert result["represented_psus"] == 3
    half = t.ppf(0.975, 1) * np.sqrt(8 / 9)
    assert result["interval"] == pytest.approx([3 - half, 3 + half])


def test_event_ratio_is_integrated_intensity_with_hand_checked_log_interval():
    mask = np.array([True, True, True, True, False, False])
    result = event_ratio(
        [1, 0, 1, 0, np.nan, np.nan], np.full(6, 0.25), np.ones(6), mask, design(), 0.95
    )
    assert result["observed_weighted_events"] == 2
    assert result["expected_weighted_event_intensity"] == 1
    assert result["estimate"] == 2
    assert result["variance"] == pytest.approx(2)
    half = t.ppf(0.975, 2) * np.sqrt(2) / 2
    assert result["interval"] == pytest.approx(np.exp(np.log(2) + np.array([-half, half])))


def test_common_weight_scale_and_paired_identity():
    mask = np.ones(6, dtype=bool)
    weight = np.arange(1, 7, dtype=float)
    values = np.array([-1, -4, 0, 3, 4, 1], dtype=float)
    first = survey_mean(values, weight, mask, design(), 0.95)
    second = survey_mean(values, weight * 20, mask, design(), 0.95)
    for key in ("estimate", "variance", "standard_error", "interval"):
        assert first[key] == pytest.approx(second[key])
    assert first["unavailable_reason"] == second["unavailable_reason"]
    ratio = event_ratio([1, 0, 1, 0, 1, 0], weight / 10, weight, mask, design(), 0.95)
    scaled = event_ratio([1, 0, 1, 0, 1, 0], weight / 10, weight * 20, mask, design(), 0.95)
    for key in ("estimate", "variance", "interval"):
        assert ratio[key] == pytest.approx(scaled[key])
    identity = survey_mean(values - values, weight, mask, design(), 0.95)
    assert identity["estimate"] == 0 and identity["interval"] == [0, 0]


def test_unavailable_domains_are_not_false_passes_or_zero_width_certainty():
    empty = np.zeros(6, dtype=bool)
    assert survey_mean(np.zeros(6), np.ones(6), empty, design(), 0.95)["estimate"] is None
    no_events = event_ratio(np.zeros(6), np.ones(6), np.ones(6), ~empty, design(), 0.95)
    assert no_events["estimate"] == 0 and no_events["interval"] is None
    assert no_events["unavailable_reason"] == "no_observed_events"
    single = np.array([True, False, False, False, False, False])
    sparse = survey_mean(np.ones(6), np.ones(6), single, design(), 0.95)
    assert sparse["interval"] is None and sparse["domain_degrees_of_freedom"] == 0
    with pytest.raises(ValueError, match="Singleton"):
        survey_variance([0.0], [True], design().iloc[:1])
    with pytest.raises(ValueError, match="Invalid values"):
        survey_mean([np.nan] * 6, np.ones(6), ~empty, design(), 0.95)
    with pytest.raises(ValueError, match="Negative"):
        event_ratio(np.ones(6), -np.ones(6), np.ones(6), ~empty, design(), 0.95)


def synthetic_frame():
    """Invented software fixture, never a clinical observation or acceptance sample."""
    n = 12
    return pd.DataFrame(
        {
            "SEQN": np.arange(1, n + 1),
            "RIAGENDR": [1, 2] * 6,
            "RIDAGEYR": np.arange(20, 80, 5),
            "RIDEXPRG": np.full(n, 2),
            "SDMVSTRA": np.repeat([1, 2, 3], 4),
            "SDMVPSU": [1, 2, 1, 2] * 3,
            "DIQ010": [2, 2, 1] * 4,
            "LBXGH": [5.0, 6.0, 7.0] * 4,
            "LBXGLU": [90, 110, 130] * 4,
            "WTSAF2YR": np.ones(n),
            "ELIGSTAT": np.ones(n),
            "MORTSTAT": [0, 1] * 6,
            "PERMTH_EXM": np.arange(12, 84, 6),
        }
    )


def test_evaluator_uses_frozen_likelihoods_and_never_calls_a_fitter(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Validation must not fit, download or select models")

    monkeypatch.setattr("demeter.analysis.mortality_development.fit", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    protocol = copy.deepcopy(load_protocol())
    # Constant known annual hazard 0.1 makes expected intensity hand-computable.
    for row in protocol["models"].values():
        row["coefficients"] = [np.log(0.1)] + [0.0] * (len(row["coefficients"]) - 1)
    frame = synthetic_frame()
    result = evaluate(frame, protocol)
    overall = result["models"]["glycemic"]["domains"][0]
    intensity = 0.1 * frame.PERMTH_EXM.to_numpy() / 12
    assert overall["event_intensity_ratio"]["expected_weighted_event_intensity"] == pytest.approx(
        intensity.sum()
    )
    expected_ll = frame.MORTSTAT.to_numpy() * np.log(0.1) - intensity
    assert overall["mean_log_score"]["estimate"] == pytest.approx(expected_ll.mean())
    assert len(result["models"]) == 4 and len(result["comparisons"]) == 4
    for comparison in result["comparisons"].values():
        assert comparison[0]["estimate"] == pytest.approx(0, abs=1e-15)
    assert not result["scientific_release_ready"]
    assert not result["independent_prediction_evaluated"]
    assert result["clinical_acceptance"].startswith("unresolved")


def test_observation_exclusions_conserve_records_and_do_not_impute_missing_death():
    frame = synthetic_frame()
    frame.loc[0, "RIDAGEYR"] = 19
    frame.loc[1, "RIDEXPRG"] = 1
    frame.loc[2, "LBXGH"] = np.nan
    frame.loc[3, ["ELIGSTAT", "MORTSTAT", "PERMTH_EXM"]] = [3, np.nan, np.nan]
    frame.loc[4, "RIDAGEYR"] = 80
    frame.loc[5, "RIAGENDR"] = np.nan
    frame.loc[6, "PERMTH_EXM"] = 0
    report = evaluate(frame, load_protocol())
    counts = report["counts"]
    assert counts["included_n"] == 5
    assert counts["included_n"] + sum(counts["sequential_exclusions"].values()) == len(frame)
    assert set(counts["sequential_exclusions"].values()) == {1}


def test_protocol_detects_parameter_definition_and_source_code_drift(tmp_path):
    protocol = load_protocol()
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    key = protocol["models"]["glycemic"]["coefficient_keys"][0]
    registry.parameters[key].value += 0.01
    with pytest.raises(ValueError, match="coefficient metadata changed"):
        load_protocol(registry=registry)
    registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
    registry.datasets["nhanes_glycemic_prevalence"]["analysis"]["adult_age_min"] += 1
    with pytest.raises(ValueError, match="observation definition changed"):
        load_protocol(registry=registry)
    for path in [PROTOCOL, *map(Path, protocol["protected_files"])]:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    changed = next(iter(protocol["protected_files"]))
    (tmp_path / changed).write_bytes(b"changed implementation")
    with pytest.raises(ValueError, match="Frozen implementation"):
        load_protocol(tmp_path, EvidenceRegistry.from_yaml("evidence/parameters.yaml"))


def test_reserved_source_identity_and_bytes_fail_before_parsing(tmp_path):
    protocol = load_protocol()
    manifest = {"schema_version": 1, "cycle": "2013-2014", "sources": {}}
    for name, row in protocol["sources"].items():
        manifest["sources"][name] = {"url": row["url"], "sha256": "0" * 64}
        (tmp_path / name).write_bytes(b"deliberately corrupted fixture")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="checksum mismatch"):
        read_validation_store(protocol, tmp_path)
    manifest["cycle"] = "2011-2012"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unexpected reserved-cycle"):
        read_validation_store(protocol, tmp_path)
