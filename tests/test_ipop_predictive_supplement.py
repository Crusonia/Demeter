"""Offline aggregate/scope audits; no participant records or source fitting."""

import copy
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def scripts(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    replay = importlib.import_module("replay_ipop_predictive_supplement")
    verify = importlib.import_module("verify_ipop_predictive_supplement")
    return replay, verify


def test_original_contract_is_verified_before_private_cache(scripts, monkeypatch):
    replay, _ = scripts

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid policy must never reach participant cache or fitting")

    monkeypatch.setattr(replay, "digest", lambda path: "invalid")
    monkeypatch.setattr(replay, "load_sources", forbidden)
    monkeypatch.setattr(replay.lab, "paired_path_bootstrap", forbidden)
    with pytest.raises(ValueError, match="policy identity"):
        replay.replay(Path("unread-cache"), freeze_commit="0" * 40)


def test_frozen_code_is_verified_before_private_cache(scripts, monkeypatch):
    replay, _ = scripts

    def forbidden(*args, **kwargs):
        pytest.fail("Unfrozen code must never reach participant cache or fitting")

    monkeypatch.setattr(replay.subprocess, "check_output", lambda *args, **kwargs: b"wrong code")
    monkeypatch.setattr(replay, "load_sources", forbidden)
    monkeypatch.setattr(replay.lab, "paired_path_bootstrap", forbidden)
    with pytest.raises(ValueError, match="frozen commit"):
        replay.replay(Path("unread-cache"), freeze_commit="0" * 40)


@pytest.fixture
def result():
    return json.loads(
        (ROOT / "docs/validation/ipop-a1c-predictive-summary-result-v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_retained_aggregate_summary_reconstructs_without_sources(scripts, result, monkeypatch):
    replay, verify = scripts

    def forbidden(*args, **kwargs):
        pytest.fail("Offline audit must never read participant records or refit")

    monkeypatch.setattr(replay, "load_sources", forbidden)
    monkeypatch.setattr(replay.lab, "paired_path_bootstrap", forbidden)
    proof = verify.assess(result)
    assert proof["passed"] is True
    assert proof["source_records_read"] is False
    assert proof["aggregate_draws_reconciled"] == 200
    assert proof["complete_vector_draws"] == 199
    assert proof["metric_block_draws"] == {"log_score": 199, "brier": 200}
    assert proof["engine_activation_allowed"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        "summary",
        "drop_draw",
        "mask_brier",
        "clinical_gate",
        "seed",
        "source",
        "chronology",
        "floor_log",
        "boolean_index",
        "impossible_brier",
        "private_field",
        "freeze_commit",
    ),
)
def test_rehashed_summary_or_scope_tampering_rejects(scripts, result, mutation):
    _, verify = scripts
    report = copy.deepcopy(result)
    uncertainty = report["predictive_uncertainty"]
    vectors = uncertainty["replicate_score_vectors"]["adjacent"]
    if mutation == "summary":
        uncertainty["models"]["adjacent"]["metric_blocks"]["brier"]["summary"]["quantiles"][0][
            0
        ] += 0.1
    elif mutation == "drop_draw":
        vectors.pop()
    elif mutation == "mask_brier":
        row = next(r for r in vectors if r["prediction_status"] != "performed_finite")
        row["values"][2] = None
        row["coordinate_status"][2] = "unavailable"
    elif mutation == "clinical_gate":
        report["clinical_fit_performed"] = True
    elif mutation == "seed":
        report["provenance"]["bootstrap_seed"] += 1
    elif mutation == "source":
        report["provenance"]["source_bytes"] = {}
    elif mutation == "chronology":
        report["provenance"]["completed_at"] = "2000-01-01T00:00:00+00:00"
    elif mutation == "floor_log":
        row = next(r for r in vectors if r["prediction_status"] != "performed_finite")
        index = next(i for i, v in enumerate(row["values"]) if v is None)
        row["values"][index] = 0.0
    elif mutation == "boolean_index":
        vectors[0]["replicate"] = False
    elif mutation == "impossible_brier":
        row = next(r for r in vectors if r["prediction_status"] != "performed_finite")
        row["values"][2] = 3.0
        # Refresh the outer summary: rejection must follow the metric domain.
        uncertainty["models"]["adjacent"] = verify.reporting.summarize_predictive_vectors(
            vectors, quantile_levels=uncertainty["quantile_levels"]
        )
    elif mutation == "private_field":
        vectors[0]["participant_label"] = "synthetic-private-marker"
    elif mutation == "freeze_commit":
        report["provenance"]["freeze_commit"] = "0" * 40
    with pytest.raises((ValueError, KeyError, TypeError)):
        verify.assess(report)
