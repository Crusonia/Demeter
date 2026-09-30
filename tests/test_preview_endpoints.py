"""Synthetic wire/source fixtures exercise the frozen used-source audit contract."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path

import pytest

from demeter.analysis.preview_endpoints import (
    ARMS,
    CONTEXT_PARAMETERS,
    DATASET,
    SOURCE_IDS,
    _describe,
    audit_preview,
    extract_reported,
)
from demeter.cli import app
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry
from typer.testing import CliRunner


@pytest.fixture(scope="session")
def registered():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def _main(analysis: dict, thresholds: dict) -> bytes:
    """Synthetic HTML reconstruction; it is not a second empirical source."""
    selected = analysis["selected_phase2_cohort_N"]
    clauses = []
    for endpoint in analysis["endpoints"]:
        mp, hp = (endpoint[arm] for arm in ARMS)
        clauses.append(
            f"rate of remission at {endpoint['nominal_year']} years "
            f"1.0% [{mp['normal_count_y']} of {mp['source_endpoint_denominator_n']}] "
            f"vs 2.0% [{hp['normal_count_y']} of {hp['source_endpoint_denominator_n']}]; "
            f"RR {endpoint['published_adjusted_RR_MP_vs_HP']}; "
            f"95% CI {endpoint['published_RR_CI_lower']}, "
            f"{endpoint['published_RR_CI_upper']}; p=0.0"
        )
    return (
        '<h2 id="Sec2">Methods</h2><h3 id="FPar4">Outcomes</h3>'
        "<p>The primary outcome of the current analysis is synthetic text. "
        "Normoglycaemia was defined as normal fasting glucose "
        f"(&lt;{thresholds['fasting_normal_lt_mmol_per_l']} mmol/l) and normal glucose "
        f"tolerance (2 h glucose &lt;{thresholds['ogtt_2hour_normal_lt_mmol_per_l']} mmol/l)."
        '</p><h2 id="Sec3">Results</h2><h3 id="FPar6">Participants</h3>'
        "<p>This secondary analysis included synthetic validation-only source text. "
        f"Of these, {selected['HP_LGI']} were in the high-protein, low-GI group, and "
        f"{selected['MP_MGI']} were in the moderate-protein, moderate-GI group.</p>"
        '<h3 id="FPar8">Prediabetes remission</h3><p>'
        "In the modified intention-to-treat analyses, the moderate-protein, moderate-GI "
        "group had a higher rate of prediabetes remission at the nominal assessments "
        "than the high-protein, low-GI group (" + "; ".join(clauses) + ").</p>"
    ).encode()


@pytest.fixture
def fixture(registered, tmp_path):
    """Repin labeled synthetic bytes while preserving frozen empirical literal definitions."""
    registry = registered.model_copy(deep=True)
    spec = registry.datasets[DATASET]
    protocol = json.loads(Path(spec["protocol_path"]).read_bytes())
    amendment = json.loads(Path(spec["amendment_path"]).read_bytes())
    receipts = json.loads(Path(spec["receipts_path"]).read_bytes())
    context = json.loads(Path(spec["context_path"]).read_bytes())
    raw = tmp_path / "raw"
    raw.mkdir()
    source = _main(spec["analysis"], protocol["scope"]["source_thresholds"])
    for pin in protocol["source_bytes"]:
        label = pin["label"]
        content = source if label == "secondary" else f"Synthetic fixture {label}".encode()
        (raw / pin["file"]).write_bytes(content)
        pin["sha256"], pin["size_bytes"] = digest(content), len(content)
        pin["receipt_path"] = str(tmp_path / "receipts.json")
        registry.sources[SOURCE_IDS[label]].sha256 = digest(content)
        receipt = receipts["receipts"][label]
        receipt["sha256"], receipt["size_bytes"] = digest(content), len(content)
    amendment["parent_protocol"] = str(tmp_path / "protocol.json")
    for name, content in (("protocol", protocol), ("amendment", amendment), ("receipts", receipts)):
        path = tmp_path / f"{name}.json"
        path.write_bytes(encoded(content))
        spec[f"{name}_path"], spec[f"{name}_sha256"] = str(path), digest(path.read_bytes())
    for name in ("protocol", "amendment"):
        context[f"parent_{name}_path"] = spec[f"{name}_path"]
        context[f"parent_{name}_sha256"] = spec[f"{name}_sha256"]
    path = tmp_path / "context.json"
    path.write_bytes(encoded(context))
    spec["context_path"], spec["context_sha256"] = str(path), digest(path.read_bytes())
    return registry, raw, source, protocol


def _repin_contract(registry, name, mutate):
    spec = registry.datasets[DATASET]
    path = Path(spec[f"{name}_path"])
    document = json.loads(path.read_bytes())
    mutate(document)
    path.write_bytes(encoded(document))
    spec[f"{name}_sha256"] = digest(path.read_bytes())


def test_offline_audit_separates_descriptive_effects_and_source_adjustment(fixture):
    registry, raw, _, protocol = fixture
    before = registry.model_dump(mode="json")
    report = audit_preview(registry, raw)
    assert registry.model_dump(mode="json") == before
    assert report["model_role"] == "benchmark_only"
    assert report["results"]["source_reproduction_passed"] is True
    assert set(report["results"]["source_checks"]) == set(SOURCE_IDS)
    assert report["results"]["joint_year_covariance"] is None
    assert report["results"]["pooled_inferential_effect"] is None
    assert not any(report["activation"].values())
    assert report["provenance"]["individual_records_used"] is False
    assert report["provenance"]["raw_redistributed"] is False
    assert report["provenance"]["clinical_fit_performed"] is False
    assert set(report["results"]["registered_source_context"]) == set(CONTEXT_PARAMETERS)
    assert all(
        not item["used_in_calculation"]
        for item in report["results"]["registered_source_context"].values()
    )
    assert all(
        item["frozen_expectation_verified"] and not item["independently_reextracted"]
        for item in report["results"]["registered_source_context"].values()
    )
    assert report["results"]["context_expectations_guard"]["passed"] is True
    assert (
        report["results"]["context_expectations_guard"]["independent_source_byte_extraction"]
        is False
    )
    assert report["provenance"]["context_sha256"] == registry.datasets[DATASET]["context_sha256"]
    completion = report["completion_interpretation"]
    assert completion["death_counts"] is None
    assert completion["death_status_inferred"] is False
    assert completion["unclassified_means_dropout_or_death"] is False
    assert completion["unknown_treatment_among_assessed_expands_N_minus_n"] is False
    assert completion["clinical_alive_and_normal_composite_interpretation_available"] is False
    assert completion["missingness_model"] is None
    for result, endpoint in zip(
        report["results"]["assessments"],
        protocol["allowed_literal_main_cells"]["endpoints"],
        strict=True,
    ):
        for arm in ARMS:
            data = result["arms"][arm]
            assert data["available_endpoint_proportion"] == (
                endpoint[arm]["normal_count_y"] / endpoint[arm]["source_endpoint_denominator_n"]
            )
            assert data["sampling_uncertainty"] is None
            assert data["endpoint_unclassified_N_minus_n"] == (
                data["selected_cohort_N"] - data["available_endpoint_n"]
            )
        assert result["published_adjusted_effect"]["reestimated"] is False
        assert (
            result["published_adjusted_effect"]["raw_proportion_ratio_equivalence_claimed"] is False
        )
        assert (
            result["published_adjusted_effect"]["RR_MP_vs_HP"]
            == (endpoint["published_adjusted_RR_MP_vs_HP"])
        )
        assert result["binary_label_completion_contrast_envelope"]["includes_zero"] is True
        assert (
            result["binary_label_completion_contrast_envelope"]["allows_MP_lower_than_HP"] is True
        )
        assert (
            result["binary_label_completion_contrast_envelope"]["allows_MP_higher_than_HP"] is True
        )


def test_literal_extraction_ignores_rounded_percentages_and_abstract_decoys(fixture):
    registry, _, source, _ = fixture
    decoy = (
        b'<h2 id="Abs1">Abstract</h2><h3>Results</h3>'
        b"<p>rate of remission at 1 year 100% [0 of 1] vs 0% [1 of 1]; "
        b"RR 2; 95% CI 1, 3;</p>"
    )
    report = extract_reported(decoy + source, registry.datasets[DATASET]["analysis"])
    assert report["endpoints"] == registry.datasets[DATASET]["analysis"]["endpoints"]
    assert report["locators"]["selected_N"] == "Sec3/Results/FPar6/Participants"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda content: content.replace(b'id="FPar6"', b'id="wrong"'),
        lambda content: content.replace(b">Participants<", b">Participants changed<"),
        lambda content: content.replace(b'id="Sec3">Results', b'id="Sec3">Discussion'),
        lambda content: content + b'<h3 id="FPar8">Prediabetes remission</h3>',
        lambda content: content + b'<h2 id="Sec3">Results</h2>',
        lambda content: content.replace(
            b"normal fasting glucose (&lt;", b"normal fasting glucose (&gt;"
        ),
        lambda content: content.replace(
            b"and normal glucose tolerance", b"or normal glucose tolerance"
        ),
        lambda content: content.replace(b"[159 of 604]", b"[160 of 604]"),
        lambda content: content.replace(b"[159 of 604]", b"[159.0 of 604]"),
        lambda content: content.replace(
            b"rate of remission at 3 years", b"rate of remission at 1 years"
        ),
        lambda content: content.replace(b"95% CI 1.04, 1.53", b"95% CI 1.53, 1.04"),
        lambda content: content.replace(b"RR 1.26;", b"RR NaN;"),
        lambda content: content.replace(
            b"than the high-protein, low-GI group", b"than the moderate-protein, moderate-GI group"
        ),
        lambda content: content.replace(
            b"the moderate-protein, moderate-GI group had", b"the high-protein, low-GI group had"
        ),
        lambda content: content[:-4],
    ],
)
def test_missing_ambiguous_or_malformed_literals_reject(fixture, mutation):
    registry, _, source, _ = fixture
    with pytest.raises(ValueError):
        extract_reported(mutation(source), registry.datasets[DATASET]["analysis"])


@pytest.mark.parametrize("label", tuple(SOURCE_IDS))
def test_every_source_is_checked_before_arithmetic(fixture, monkeypatch, label):
    registry, raw, _, protocol = fixture
    pin = next(pin for pin in protocol["source_bytes"] if pin["label"] == label)
    (raw / pin["file"]).write_bytes(b"corrupt")
    monkeypatch.setattr(
        "demeter.analysis.preview_endpoints._describe",
        lambda _: pytest.fail("arithmetic before byte verification"),
    )
    with pytest.raises(ValueError, match="checksum/size"):
        audit_preview(registry, raw)


@pytest.mark.parametrize("label", tuple(SOURCE_IDS))
def test_missing_companion_source_is_not_optional(fixture, label):
    registry, raw, _, protocol = fixture
    filename = next(pin["file"] for pin in protocol["source_bytes"] if pin["label"] == label)
    (raw / filename).unlink()
    with pytest.raises(FileNotFoundError):
        audit_preview(registry, raw)


@pytest.mark.parametrize("name", ("protocol", "amendment", "receipts", "context"))
def test_all_contract_bytes_are_pinned(fixture, name):
    registry, raw, _, _ = fixture
    path = Path(registry.datasets[DATASET][f"{name}_path"])
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match=f"{name} checksum"):
        audit_preview(registry, raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda spec: spec.update(model_role="health_model"),
        lambda spec: spec.update(clinical_fit_allowed=True),
        lambda spec: spec.update(engine_activation_allowed=True),
        lambda spec: spec["analysis"]["endpoints"].reverse(),
        lambda spec: spec["parameter_keys"].pop(),
        lambda spec: spec["parameter_keys"].append(spec["parameter_keys"][0]),
        lambda spec: spec["source_ids"].update(esm="preview_original2021"),
    ],
)
def test_dataset_drift_rejects_before_arithmetic(fixture, monkeypatch, mutation):
    registry, raw, _, _ = fixture
    mutation(registry.datasets[DATASET])
    monkeypatch.setattr(
        "demeter.analysis.preview_endpoints._describe",
        lambda _: pytest.fail("arithmetic after contract drift"),
    )
    with pytest.raises(ValueError):
        audit_preview(registry, raw)


@pytest.mark.parametrize(
    "key, field, value",
    [
        ("preview_selected_MP_MGI_n", "value", 1),
        ("preview_y1_MP_MGI_normal_count", "value", 0),
        ("preview_y3_HP_LGI_endpoint_n", "value", 1),
        ("preview_normal_fasting_threshold", "value", 1),
        ("preview_nominal_year1", "value", 2),
        ("preview_y1_adjusted_rr", "model_role", "health_model"),
        ("preview_year1_window_weeks", "unit", "years"),
        ("preview_year3_nominal_week", "source_id", "preview_secondary2025"),
    ],
)
def test_registry_definition_or_literal_drift_rejects(fixture, key, field, value):
    registry, raw, _, _ = fixture
    setattr(registry.parameters[key], field, value)
    with pytest.raises(ValueError):
        audit_preview(registry, raw)


def test_reported_interval_disagreement_rejects_without_overwriting_registry(fixture):
    registry, raw, _, _ = fixture
    registry.parameters["preview_y1_adjusted_rr"].uncertainty.high = 2
    before = registry.model_dump(mode="json")
    with pytest.raises(ValueError, match="adjusted RR disagreement"):
        audit_preview(registry, raw)
    assert registry.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "name, mutation",
    [
        ("amendment", lambda doc: doc.update(parent_protocol="wrong")),
        ("amendment", lambda doc: doc.update(analytical_selection_changed=True)),
        ("receipts", lambda doc: doc["receipts"].pop("esm")),
        ("receipts", lambda doc: doc["receipts"]["secondary"].update(requested_url="wrong")),
        ("receipts", lambda doc: doc["receipts"]["original2021"].update(http_status=500)),
        ("receipts", lambda doc: doc["receipts"]["esm"].update(size_bytes=1)),
        ("receipts", lambda doc: doc.update(participant_records_acquired=True)),
        ("protocol", lambda doc: doc["source_bytes"].append(copy.deepcopy(doc["source_bytes"][0]))),
    ],
)
def test_repinned_metadata_still_requires_consistent_source_contract(fixture, name, mutation):
    registry, raw, _, _ = fixture
    _repin_contract(registry, name, mutation)
    with pytest.raises(ValueError):
        audit_preview(registry, raw)


def test_duplicate_json_keys_are_rejected_even_if_bytes_repin(fixture):
    registry, raw, _, _ = fixture
    spec = registry.datasets[DATASET]
    path = Path(spec["receipts_path"])
    path.write_bytes(b'{"receipts": {}, "receipts": {}}')
    spec["receipts_sha256"] = digest(path.read_bytes())
    with pytest.raises(ValueError, match="Duplicate"):
        audit_preview(registry, raw)


def test_source_iteration_order_does_not_change_results(fixture):
    registry, raw, _, _ = fixture
    before = audit_preview(registry, raw)["results"]
    _repin_contract(registry, "protocol", lambda doc: doc["source_bytes"].reverse())
    _repin_contract(
        registry,
        "context",
        lambda doc: doc.update(
            parent_protocol_sha256=registry.datasets[DATASET]["protocol_sha256"]
        ),
    )
    assert audit_preview(registry, raw)["results"] == before


def test_no_hidden_network_and_no_machine_local_raw_paths(fixture, monkeypatch):
    registry, raw, _, _ = fixture
    monkeypatch.setattr("socket.socket", lambda *_args, **_kwargs: pytest.fail("network attempted"))
    report = audit_preview(registry, raw)
    serialized = json.dumps(report)
    assert str(raw) not in serialized
    assert "participant_id" not in serialized


def test_symlink_source_rejected(fixture):
    registry, raw, _, protocol = fixture
    target = raw / protocol["source_bytes"][0]["file"]
    companion = raw / "linked-target"
    companion.write_bytes(target.read_bytes())
    target.unlink()
    try:
        target.symlink_to(companion)
    except OSError as exc:
        pytest.skip(f"Host does not permit creating symlinks: {exc}")
    with pytest.raises(ValueError, match="symlink"):
        audit_preview(registry, raw)


def _synthetic_endpoint(y_mp=2, n_mp=4, total_mp=5, y_hp=1, n_hp=2, total_hp=4):
    return {
        "selected_phase2_cohort_N": {"MP_MGI": total_mp, "HP_LGI": total_hp},
        "endpoints": [
            {
                "nominal_year": 1,
                "MP_MGI": {"normal_count_y": y_mp, "source_endpoint_denominator_n": n_mp},
                "HP_LGI": {"normal_count_y": y_hp, "source_endpoint_denominator_n": n_hp},
                "published_adjusted_RR_MP_vs_HP": 1,
                "published_RR_CI_lower": 0.5,
                "published_RR_CI_upper": 2,
            }
        ],
    }


def test_completion_envelope_matches_all_extreme_binary_label_assignments():
    """Enumerate a labeled synthetic small cohort, independently of the envelope formula."""
    result = _describe(_synthetic_endpoint())[0]
    mp = [sum([1, 1, 0, 0, *missing]) / 5 for missing in itertools.product((0, 1), repeat=1)]
    hp = [sum([1, 0, *missing]) / 4 for missing in itertools.product((0, 1), repeat=2)]
    contrasts = [p_mp - p_hp for p_mp, p_hp in itertools.product(mp, hp)]
    assert result["available_endpoint_absolute_contrast_MP_minus_HP"] == 0
    envelope = result["binary_label_completion_contrast_envelope"]
    assert (envelope["lower"], envelope["upper"]) == (min(contrasts), max(contrasts))
    assert envelope["includes_zero"] is True
    assert envelope["allows_MP_lower_than_HP"] is True
    assert envelope["allows_MP_higher_than_HP"] is True


def test_no_endpoint_missingness_collapses_completion_envelope():
    result = _describe(_synthetic_endpoint(total_mp=4, total_hp=2))[0]
    assert result["binary_label_completion_contrast_envelope"]["lower"] == 0
    assert result["binary_label_completion_contrast_envelope"]["upper"] == 0
    assert all(arm["endpoint_unclassified_N_minus_n"] == 0 for arm in result["arms"].values())


def test_zero_available_endpoints_is_unknown_not_zero_normality():
    result = _describe(_synthetic_endpoint(y_mp=0, n_mp=0))[0]
    assert result["arms"]["MP_MGI"]["available_endpoint_proportion"] is None
    assert result["available_endpoint_absolute_contrast_MP_minus_HP"] is None
    assert result["arms"]["MP_MGI"]["binary_label_completion_envelope"] == {"lower": 0, "upper": 1}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"y_mp": True},
        {"y_mp": 2.0},
        {"y_mp": -1},
        {"y_mp": 5},
        {"n_mp": 6},
        {"total_mp": 0},
        {"total_mp": -1},
    ],
)
def test_inadmissible_synthetic_denominators_block_arithmetic(kwargs):
    with pytest.raises(ValueError, match="counts require integers"):
        _describe(_synthetic_endpoint(**kwargs))


def test_cli_missing_sources_is_offline_and_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("socket.socket", lambda *_args, **_kwargs: pytest.fail("network attempted"))
    result = CliRunner().invoke(app, ["evidence", "preview-endpoints", "--raw", str(tmp_path)])
    assert result.exit_code == 1
    assert not (tmp_path / "preview-secondary-main-pinned.html").exists()


def test_report_preserves_known_auxiliary_conflicts_without_clinical_acceptance(fixture):
    registry, raw, _, protocol = fixture
    report = audit_preview(registry, raw)
    assert report["results"]["source_reproduction_passed"] is True
    assert report["denominator_reconciliation"] == protocol["denominator_reconciliation"]
    assert report["failure_dispositions"] == protocol["failure_dispositions"]
    consistency = report["source_consistency"]
    assert consistency["main_frozen_count_constraints"] == "passed"
    assert "unresolved" in consistency["auxiliary_completer_denominator_consistency"]
    assert "unresolved" in consistency["original_and_secondary_source_version_consistency"]
    assert consistency["auxiliary_cells_reextracted_or_repaired"] is False
    assert consistency["overall_clinical_acceptance"] is False
    assert report["scientific_release_ready"] is False


def test_cli_persists_the_successful_offline_report(fixture, tmp_path, monkeypatch):
    registry, raw, _, _ = fixture
    output = tmp_path / "reports" / "audit.json"
    monkeypatch.setattr("demeter.cli.registry", lambda _path: registry)
    result = CliRunner().invoke(
        app, ["evidence", "preview-endpoints", "--raw", str(raw), "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert output.exists()
    report = json.loads(output.read_bytes())
    assert report == json.loads(result.stdout)
    assert report["results"]["source_reproduction_passed"] is True
    assert report["source_consistency"]["overall_clinical_acceptance"] is False


@pytest.mark.parametrize(
    "key, changed_value",
    [
        ("preview_reported_confidence_level", 0.90),
        ("preview_year1_nominal_week", 53),
        ("preview_year3_nominal_week", 157),
        ("preview_year1_window_weeks", 3),
        ("preview_later_window_weeks", 5),
        ("preview_run_in_weeks", 9),
    ],
)
def test_all_context_numeric_drift_rejects_before_arithmetic(
    fixture, monkeypatch, key, changed_value
):
    registry, raw, _, _ = fixture
    registry.parameters[key].value = changed_value
    monkeypatch.setattr(
        "demeter.analysis.preview_endpoints._describe",
        lambda _: pytest.fail("arithmetic after context drift"),
    )
    with pytest.raises(ValueError, match="frozen context expectation disagreement"):
        audit_preview(registry, raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda doc: doc.update(schema_version=True),
        lambda doc: doc.update(parent_protocol_path="wrong"),
        lambda doc: doc.update(parent_protocol_sha256="0" * 64),
        lambda doc: doc.update(parent_amendment_path="wrong"),
        lambda doc: doc.update(parent_amendment_sha256="0" * 64),
        lambda doc: doc.update(analytical_selection_changed=True),
        lambda doc: doc.update(clinical_fit_or_activation_allowed=True),
        lambda doc: doc.update(independent_byte_extraction=True),
        lambda doc: doc.update(used_in_endpoint_calculations=True),
        lambda doc: doc["context_parameters"].pop("preview_run_in_weeks"),
        lambda doc: doc["context_parameters"].update(
            extra=doc["context_parameters"]["preview_run_in_weeks"]
        ),
        lambda doc: doc["context_parameters"]["preview_year1_window_weeks"].update(unit="days"),
        lambda doc: doc["context_parameters"]["preview_run_in_weeks"].update(
            source_id="preview_original2021"
        ),
        lambda doc: doc["context_parameters"]["preview_run_in_weeks"].update(source_locator=" "),
        lambda doc: doc["context_parameters"]["preview_reported_confidence_level"].update(
            value="0.95"
        ),
        lambda doc: doc["context_parameters"]["preview_year1_window_weeks"].update(value=True),
        lambda doc: doc["context_parameters"]["preview_run_in_weeks"].update(value=9),
        lambda doc: doc["context_parameters"]["preview_run_in_weeks"].update(extra=True),
        lambda doc: doc["context_parameters"]["preview_reported_confidence_level"].update(
            transformation=" "
        ),
    ],
)
def test_context_schema_and_parent_drift_rejects_even_if_repinned(fixture, monkeypatch, mutation):
    registry, raw, _, _ = fixture
    _repin_contract(registry, "context", mutation)
    monkeypatch.setattr(
        "demeter.analysis.preview_endpoints._describe",
        lambda _: pytest.fail("arithmetic after invalid context amendment"),
    )
    with pytest.raises(ValueError):
        audit_preview(registry, raw)


def test_context_value_disagreement_fails_cli_without_saving_a_success_report(
    fixture, tmp_path, monkeypatch
):
    registry, raw, _, _ = fixture
    registry.parameters["preview_reported_confidence_level"].value = 0.90
    output = tmp_path / "unverified.json"
    monkeypatch.setattr("demeter.cli.registry", lambda _path: registry)
    result = CliRunner().invoke(
        app, ["evidence", "preview-endpoints", "--raw", str(raw), "--output", str(output)]
    )
    assert result.exit_code == 1
    assert "frozen context expectation disagreement" in result.output
    assert not output.exists()
