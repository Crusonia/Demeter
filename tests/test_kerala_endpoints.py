"""Recorded-endpoint source bindings and source-native observation semantics."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from demeter.analysis import kerala_endpoints as module
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def selected():
    return EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")


def test_real_registered_offline_bounds_are_not_a_clinical_fit(selected):
    report = module.audit_kerala_endpoints(selected, ROOT)
    assert report["source_audit_passed"] is True
    assert report["public_workbook_endpoint_counts_reproduced"] is None
    assert report["publication_text_counts_reproduced"] is None
    for arm, lower, upper, denominator in (
        ("Control", 79, 123, 507),
        ("Intervention", 68, 112, 500),
    ):
        bounds = report["arms"][arm]
        assert bounds["counts"]["unknown_endpoints"] == 44
        assert bounds["all_assigned"]["event_count_bounds"] == {"lower": lower, "upper": upper}
        assert bounds["all_assigned"]["denominator"] == denominator
        assert bounds["survivor_conditional"] is None
    contrast = report["regimen_contrast"]
    assert contrast["all_assigned_direction_unresolved"] is True
    pairs = contrast["missing_endpoint_completions"]
    assert pairs["compatible_aggregate_pairs"] == 2025
    assert pairs["lower_intervention_fraction"] == 1395
    assert pairs["higher_intervention_fraction"] == 630
    assert pairs["equal_fraction"] == 0
    assert pairs["pairs_have_equal_probability"] is False
    for key in (
        "clinical_fit_ready",
        "causal_effect_identified",
        "national_transport_ready",
        "engine_activation_allowed",
        "participant_records_exported",
        "labeled_multiwave_tuples_exported",
    ):
        assert report[key] is False


def test_survivor_estimand_requires_explicit_unverified_assumption(selected):
    report = module.audit_kerala_endpoints(selected, ROOT, assume_complete_deaths=True)
    assert report["reported_deaths"]["complete_ascertainment_verified"] is False
    assert report["complete_death_total_assumption_supplied"] is True
    assert report["arms"]["Control"]["survivor_conditional"]["denominator"] == 506
    assert report["arms"]["Intervention"]["survivor_conditional"]["denominator"] == 498
    assert report["arms"]["Control"]["survivor_conditional"]["event_count_bounds"] == {
        "lower": 78,
        "upper": 123,
    }
    assert report["regimen_contrast"]["fraction_difference"]["survivor_conditional"] is not None


@pytest.mark.parametrize("mutation", ["value", "role", "unit", "source", "gate", "parent"])
def test_registry_mutations_fail_before_source_calculation(selected, mutation):
    parameter = selected.parameters["kerala_control_recorded_events_n"]
    if mutation == "value":
        parameter.value += 1
    elif mutation == "role":
        parameter.model_role = "health_model"
    elif mutation == "unit":
        parameter.unit = "hazards/year"
    elif mutation == "source":
        selected.sources[module.SOURCE].sha256 = "0" * 64
    elif mutation == "gate":
        selected.datasets[module.DATASET]["engine_activation_allowed"] = True
    else:
        selected.datasets["kerala_source_admission"]["representation_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        module.audit_kerala_endpoints(selected, ROOT)


def test_artifact_path_escape_fails(selected):
    selected.datasets[module.DATASET]["bundle_path"] = "../outside.json"
    with pytest.raises(ValueError, match="escapes"):
        module.audit_kerala_endpoints(selected, ROOT)


def test_nonboolean_death_assumption_fails(selected):
    with pytest.raises(ValueError, match="boolean"):
        module.audit_kerala_endpoints(selected, ROOT, assume_complete_deaths=1)


def test_private_typed_rows_only_return_broad_endpoint_counts(monkeypatch):
    rows = [
        {
            "participant_id": ("string", "PRIVATE-A"),
            "arms0": ("string", "Control"),
            "tot_diab_incidence": ("string", "Yes"),
        },
        {
            "participant_id": ("number", "1"),
            "arms0": ("string", "Intervention"),
            "tot_diab_incidence": ("absent", None),
        },
        {
            "participant_id": ("string", "1"),
            "arms0": ("string", "Intervention"),
            "tot_diab_incidence": ("string", "No"),
        },
    ]
    monkeypatch.setattr(module.coverage, "_selected_rows", lambda *_: rows)
    result = module._workbook_counts(Path("unused.xlsx"))
    assert result == {
        "Control": {"assigned": 1, "known_endpoints": 1, "recorded_events": 1},
        "Intervention": {"assigned": 2, "known_endpoints": 1, "recorded_events": 0},
    }
    rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError, match="nonunique"):
        module._workbook_counts(Path("unused.xlsx"))


@pytest.mark.parametrize("flag", [("number", "1"), ("string", "PRIVATE_FLAG"), ("empty", None)])
def test_unknown_endpoint_code_is_not_guessed(monkeypatch, flag):
    monkeypatch.setattr(
        module.coverage,
        "_selected_rows",
        lambda *_: [
            {
                "participant_id": ("string", "PRIVATE"),
                "arms0": ("string", "Control"),
                "tot_diab_incidence": flag,
            }
        ],
    )
    with pytest.raises(ValueError, match="unsupported"):
        module._workbook_counts(Path("unused.xlsx"))


def test_publication_text_reproduction_checks_six_counts_not_figure(monkeypatch, selected):
    counts, _ = module._registered_counts(selected, ROOT)
    text = "1,007 (507 in the control group and 500 in the intervention group) (79/463) of participants in the control group and 14.9% (68/456) of participants in the intervention group"
    page = SimpleNamespace(extract_text=lambda: text)
    monkeypatch.setattr("pypdf.PdfReader", lambda _: SimpleNamespace(pages=[None] * 9 + [page]))
    module._publication_counts(b"synthetic", counts)
    text = text.replace("79/463", "78/463")
    with pytest.raises(ValueError, match="disagreement"):
        module._publication_counts(b"synthetic", counts)
