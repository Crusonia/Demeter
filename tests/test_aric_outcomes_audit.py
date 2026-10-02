"""Integration checks for scoped publication facts, provenance and output safety."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import demeter.analysis.aric_outcomes_audit as module
from demeter.cli import app
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def package(tmp_path):
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    for name in (module.PROTOCOL_PATH, module.REPORT_PATH, *module.TRANSFORMS.values()):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    return registry, tmp_path


def source_facts(root):
    return json.loads((root / module.REPORT_PATH).read_bytes())["source_facts"]


def test_offline_audit_does_not_read_or_fit_sources(package, monkeypatch):
    registry, root = package
    before = registry.model_dump(mode="json")

    def forbidden(*args, **kwargs):
        pytest.fail("Offline audit cannot extract or download sources")

    monkeypatch.setattr(module, "extract_aric_source_records", forbidden)
    result = module.audit_aric_outcomes(registry, root)
    assert registry.model_dump(mode="json") == before
    assert result["registered_artifacts_verified"] is True
    assert result["raw_values_read"] is False
    assert result["source_aggregates_reproduced"] is None
    assert result["network_used"] is False
    assert result["clinical_transition_fit_performed"] is False
    assert result["engine_activation_allowed"] is False
    assert result["scientific_release_ready"] is False
    report = result["report"]
    assert report["scientific_gates"] == module.GATES
    assert report["working_fit_performed"] is False
    assert report["sampling_interval"] is None
    assert report["participant_records_used"] is False
    counts = report["conditional_source_reconstruction"]["counts"]
    assert counts["original_unique_people"] == 3412
    assert counts["selected_unique_people"] == 2497
    assert counts["unrepresented_baseline_margin"] == 915
    assert len(report["conditional_source_reconstruction"]["panels"]) == 2


def test_unknown_membership_and_event_priority_survive_reconstruction(package):
    registry, root = package
    report = module.audit_aric_outcomes(registry, root)["report"]
    assert report["derivation_contract"]["source_subset_identity_declared"] is True
    for key, value in report["derivation_contract"].items():
        if type(value) is bool and key != "source_subset_identity_declared":
            assert value is False
    contrasts = report["source_contrasts"]
    assert contrasts["cumulative_vs_displayed_diabetes"]["cumulative"] == 156
    assert contrasts["cumulative_vs_displayed_diabetes"]["displayed"] == 138
    assert (
        contrasts["cumulative_vs_displayed_diabetes"]["difference_is_diagnosis_before_death_count"]
        is False
    )
    assert contrasts["displayed_vs_previsit_mortality"]["displayed"] == 434
    assert contrasts["displayed_vs_previsit_mortality"]["before_visit6"] == 408
    assert (
        contrasts["displayed_vs_previsit_mortality"]["additional_slots_allocated_to_attenders"]
        is False
    )


def test_original_joint_assays_have_observed_margins_without_followup_pairing(package):
    registry, root = package
    report = module.audit_aric_outcomes(registry, root)["report"]
    joint = report["original_assay_joint_baseline_counts"]
    observations = report["source_facts"]["observed"]
    assert (
        sum(sum(row.values()) for row in joint.values()) == observations["original_analytic_count"]
    )
    assert sum(joint["a1c_prediabetes"].values()) == observations["original_a1c_prediabetes_count"]
    assert (
        sum(row["fg_prediabetes"] for row in joint.values())
        == observations["original_fg_prediabetes_count"]
    )
    assert (
        joint["a1c_prediabetes"]["fg_prediabetes"]
        == observations["original_both_prediabetes_count"]
    )
    assert report["cross_assay_joint_followup_identified"] is False


@pytest.mark.parametrize(
    "path", [module.PROTOCOL_PATH, module.REPORT_PATH, *module.TRANSFORMS.values()]
)
def test_source_or_transform_byte_drift_is_rejected(package, path):
    registry, root = package
    target = root / path
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        module.audit_aric_outcomes(registry, root)


@pytest.mark.parametrize(
    "field,value",
    [
        ("citation", "ALTERED_PROVENANCE"),
        ("source", "ALTERED_PROVENANCE"),
        ("population", "ALTERED_PROVENANCE"),
        ("geography", "ALTERED_PROVENANCE"),
        ("time_period", "ALTERED_PROVENANCE"),
        ("outcome_definition", "ALTERED_PROVENANCE"),
        ("exposure_definition", "ALTERED_PROVENANCE"),
        ("transformation", "ALTERED_PROVENANCE"),
        ("notes", "ALTERED_PROVENANCE"),
        ("value", 1500),
        ("model_role", "health_model"),
        ("status", "estimated"),
        ("unit", "per_year"),
        ("evidence_grade", "B"),
    ],
)
def test_complete_parameter_metadata_is_bound(package, field, value):
    registry, root = package
    setattr(registry.parameters["aric_panel_original_a1c_prediabetes_count"], field, value)
    with pytest.raises(ValueError, match="complete registry"):
        module.audit_aric_outcomes(registry, root)


def test_uncertainty_metadata_and_unused_bounds_are_bound(package):
    registry, root = package
    parameter = registry.parameters["aric_panel_original_a1c_prediabetes_count"]
    before = parameter.uncertainty.rationale
    parameter.uncertainty.rationale = "ALTERED_PROVENANCE"
    with pytest.raises(ValueError, match="complete registry"):
        module.audit_aric_outcomes(registry, root)
    parameter.uncertainty.rationale = before
    parameter.upper_bound = 5000
    with pytest.raises(ValueError, match="complete registry"):
        module.audit_aric_outcomes(registry, root)


@pytest.mark.parametrize("source", ["aric2021_supplement", "aric2021_pubmed_abstract"])
@pytest.mark.parametrize("field", ["citation", "license", "correction_note", "correction_url"])
def test_both_complete_source_receipts_are_bound(package, source, field):
    registry, root = package
    setattr(registry.sources[source], field, "ALTERED_PROVENANCE")
    with pytest.raises(ValueError, match="complete registry"):
        module.audit_aric_outcomes(registry, root)


@pytest.mark.parametrize(
    "field", ["estimand", "scientific_gates", "subset_contract", "report_sha256"]
)
def test_complete_dataset_contract_is_bound(package, field):
    registry, root = package
    registry.datasets[module.DATASET][field] = "ALTERED_PROVENANCE"
    with pytest.raises(ValueError, match="complete registry"):
        module.audit_aric_outcomes(registry, root)


def test_unrelated_record_development_remains_possible(package):
    registry, root = package
    registry.parameters["ir_to_t2d_rate"].notes = "Unrelated future development"
    assert module.audit_aric_outcomes(registry, root)["registered_artifacts_verified"] is True


@pytest.mark.parametrize(
    "mutation",
    [
        lambda facts: facts.update(participant_records=["PRIVATE_MARKER"]),
        lambda facts: facts["observed"].update(unknown_count=1),
        lambda facts: facts["observed"].update(original_analytic_count=3412.0),
        lambda facts: facts["observed"].update(original_analytic_count=3413),
        lambda facts: facts["source_size_bytes"].update(supplement=533032.0),
        lambda facts: facts["source_sha256"].update(pubmed_abstract="0" * 64),
        lambda facts: facts["scientific_gates"].update(clinical_fit_allowed=0),
        lambda facts: facts["source_locators"].update(original_analytic_count="PRIVATE_MARKER"),
    ],
)
def test_pure_report_builder_rejects_scope_identity_and_type_drift(package, mutation):
    _, root = package
    facts = source_facts(root)
    mutation(facts)
    with pytest.raises(ValueError):
        module.build_aric_report(root, facts)


def test_resealed_report_cannot_change_scientific_semantics(package):
    registry, root = package
    report = json.loads((root / module.REPORT_PATH).read_bytes())
    report["scientific_gates"]["clinical_fit_allowed"] = True
    replacement = encoded(report)
    (root / module.REPORT_PATH).write_bytes(replacement)
    registry.datasets[module.DATASET]["report_sha256"] = hashlib.sha256(replacement).hexdigest()
    with pytest.raises(ValueError, match="complete registry"):
        module.audit_aric_outcomes(registry, root)


def test_optional_replay_requires_both_sources_and_compares_full_report(package, monkeypatch):
    registry, root = package
    cache = root / "public-source-cache"
    cache.mkdir()
    protocol = json.loads((root / module.PROTOCOL_PATH).read_bytes())
    source_bytes = {
        "supplement": b"synthetic_public_pdf",
        "pubmed_abstract": b"synthetic_public_xml",
    }
    for name, item in protocol["sources"].items():
        (cache / item["raw_filename"]).write_bytes(source_bytes[name])
    facts = source_facts(root)
    calls = []

    def extract(pdf, xml, received_protocol):
        assert (pdf, xml) == (source_bytes["supplement"], source_bytes["pubmed_abstract"])
        assert received_protocol == protocol
        calls.append(True)
        return deepcopy(facts)

    monkeypatch.setattr(module, "extract_aric_source_records", extract)
    replay = module.audit_aric_outcomes(registry, root, source_cache=cache)
    assert calls == [True]
    assert replay["raw_values_read"] is replay["source_aggregates_reproduced"] is True
    (cache / protocol["sources"]["pubmed_abstract"]["raw_filename"]).unlink()
    with pytest.raises(OSError):
        module.audit_aric_outcomes(registry, root, source_cache=cache)
    assert calls == [True]


def test_cli_reports_offline_scope_and_saves_only_new_output(package):
    registry, root = package
    evidence = root / "registry.yaml"
    evidence.write_bytes((ROOT / "evidence/parameters.yaml").read_bytes())
    output = root / "results" / "audit.json"
    args = [
        "evidence",
        "aric-outcomes",
        "--project",
        str(root),
        "--evidence",
        str(evidence),
        "--output",
        str(output),
    ]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    saved = json.loads(output.read_bytes())
    assert saved["raw_values_read"] is False
    assert saved["report"]["scientific_gates"] == module.GATES
    before = output.read_bytes()
    rejected = CliRunner().invoke(app, args)
    assert rejected.exit_code == 1
    assert output.read_bytes() == before


@pytest.mark.parametrize("folder", ["data", "src", "docs", "evidence", ".git"])
def test_cli_protects_sources_and_frozen_records(package, folder):
    _, root = package
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "aric-outcomes",
            "--project",
            str(root),
            "--evidence",
            str(ROOT / "evidence/parameters.yaml"),
            "--output",
            str(root / folder / "new.json"),
        ],
    )
    assert result.exit_code == 1
    assert not (root / folder / "new.json").exists()


def test_cli_raw_cache_errors_are_sanitized(package):
    _, root = package
    private_cache = root / "PRIVATE_MARKER"
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "aric-outcomes",
            "--project",
            str(root),
            "--evidence",
            str(ROOT / "evidence/parameters.yaml"),
            "--source-cache",
            str(private_cache),
        ],
    )
    assert result.exit_code == 1
    assert "PRIVATE_MARKER" not in result.output
    assert "ARIC source evidence or output is invalid" in result.output
