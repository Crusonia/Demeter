"""Source audit boundaries, including edited and resealed private-field attempts."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from demeter.analysis.kerala_observation_audit import DATASET, SOURCE, audit_kerala_observations
from demeter.cli import app
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_package(tmp_path, monkeypatch):
    actual = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    spec = deepcopy(actual.datasets[DATASET])
    files = [spec[key + "_path"] for key in ("adapter", "protocol", "report")]
    files += [
        "docs/validation/kerala-source-acquisition-receipts-v1.json",
        "docs/validation/kerala-joint-coverage-intake-protocol-v2.json",
    ]
    for filename in files:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / filename).read_bytes())
    registry = SimpleNamespace(
        datasets={
            DATASET: spec,
            "kerala_source_admission": actual.datasets["kerala_source_admission"],
        },
        sources={SOURCE: actual.sources[SOURCE]},
    )
    monkeypatch.setattr(
        "demeter.analysis.kerala_observation_audit.verify_registered",
        lambda *_, **__: {"registered_artifacts_verified": True},
    )
    return tmp_path, registry


def test_real_offline_source_chain_verifies_without_reading_raw_values(monkeypatch):
    def forbidden(*_, **__):
        pytest.fail("Offline metadata audit must not read participant values")

    monkeypatch.setattr(
        "demeter.analysis.kerala_observation_audit.coverage._selected_rows", forbidden
    )
    registry = EvidenceRegistry.from_yaml(ROOT / "evidence/parameters.yaml")
    report = audit_kerala_observations(registry, ROOT)
    assert report["registered_artifacts_verified"] is True
    assert report["raw_values_read"] is False
    assert report["source_aggregates_reproduced"] is None
    assert report["source_likelihood_computed"] is False
    assert report["report"]["source_observation_channel_estimated"] is False


@pytest.mark.parametrize("prefix", ["adapter", "protocol", "report"])
def test_checksum_drift_is_rejected(isolated_package, prefix):
    root, registry = isolated_package
    spec = registry.datasets[DATASET]
    path = root / spec[prefix + "_path"]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin mismatch"):
        audit_kerala_observations(registry, root)


@pytest.mark.parametrize(
    "mutation",
    [
        "private_field",
        "nested_private_field",
        "assay_token",
        "free_text_token",
        "bool_count",
        "negative_count",
        "unbalanced_margin",
        "labeled_histogram",
        "unbalanced_histogram",
        "infer_deaths",
        "inconsistent_union",
        "truthy_gate",
        "wrong_visit_label",
        "unknown_check_string",
        "backdated_baseline_flag",
        "false_known_triples",
        "unevaluable_omission",
    ],
)
def test_resealed_unapproved_diagnostics_are_rejected(isolated_package, mutation):
    root, registry = isolated_package
    spec = registry.datasets[DATASET]
    path = root / spec["report_path"]
    report = json.loads(path.read_bytes())
    diagnostic = report["diagnostics"]
    visits = diagnostic["visit_marginals"]
    if mutation == "private_field":
        diagnostic["aggregate_paths"] = ["PRIVATE_SYNTHETIC_PATH"]
    elif mutation == "nested_private_field":
        visits["Baseline"]["opaque_key"] = "PRIVATE_SYNTHETIC_KEY"
    elif mutation in {"assay_token", "free_text_token"}:
        token = "number:123456789" if mutation == "assay_token" else "PRIVATE_SYNTHETIC_TEXT"
        visits["Baseline"]["glycemia"] = {token: diagnostic["subjects"]}
    elif mutation == "bool_count":
        diagnostic["subjects"] = True
    elif mutation == "negative_count":
        diagnostic["incidence_flag_algebra"]["suffix_positive_overlap"] = -1
    elif mutation == "unbalanced_margin":
        diagnostic["assignment_marginal"]["Control"] += 1
    elif mutation == "labeled_histogram":
        diagnostic["unlabeled_observation_pattern_cell_size_histogram"] = {"NGT:IFG:diabetes": 1}
    elif mutation == "unbalanced_histogram":
        diagnostic["unlabeled_observation_pattern_cell_size_histogram"]["1"] += 1
    elif mutation == "infer_deaths":
        diagnostic["individual_death_contact_confirmation_and_first_onset_unknown"] = False
    elif mutation == "inconsistent_union":
        diagnostic["incidence_flag_algebra"]["suffix_positive_union"] += 1
    elif mutation == "truthy_gate":
        diagnostic["clinical_fit_allowed"] = 0
    elif mutation == "wrong_visit_label":
        visits["exact day 365"] = visits.pop("12 months")
    elif mutation == "backdated_baseline_flag":
        visits["Baseline"]["incidence_flag"] = {"string:Yes": diagnostic["subjects"]}
    elif mutation == "false_known_triples":
        diagnostic["incidence_flag_algebra"]["fully_interpretable_triples"] = 0
    elif mutation == "unevaluable_omission":
        visits["12 months"]["glycemia"] = {"string:NGT": diagnostic["subjects"]}
        visits["12 months"]["ada_diabetes"] = {"string:No": diagnostic["subjects"]}
    else:
        diagnostic["ada_category_and_flag_agree_where_both_interpretable"] = "confirmed"
    path.write_bytes(encoded(report))
    spec["report_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        audit_kerala_observations(registry, root)


def test_raw_replay_failure_is_not_reported_as_reproduction(isolated_package, monkeypatch):
    root, registry = isolated_package

    def fail(*_, **__):
        raise ValueError("Synthetic linkage disagreement")

    monkeypatch.setattr("demeter.analysis.kerala_observation_audit.coverage._selected_rows", fail)
    with pytest.raises(ValueError, match="linkage disagreement"):
        audit_kerala_observations(registry, root, source_cache=root / "private-cache")


def test_cli_writes_exclusively_and_labels_offline_scope(tmp_path):
    output = tmp_path / "observations.json"
    result = CliRunner().invoke(app, ["evidence", "kerala-observations", "--output", str(output)])
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_bytes())
    assert report["raw_values_read"] is False
    before = output.read_bytes()
    result = CliRunner().invoke(app, ["evidence", "kerala-observations", "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_bytes() == before


@pytest.mark.parametrize("folder", ["docs", "data", "src", "evidence"])
def test_cli_protects_frozen_source_folders(folder):
    path = ROOT / folder / "must-not-create-kerala-observation.json"
    result = CliRunner().invoke(app, ["evidence", "kerala-observations", "--output", str(path)])
    assert result.exit_code == 1
    assert not path.exists()


def test_cli_source_error_exposes_no_private_details(monkeypatch):
    def fail(*_, **__):
        raise ValueError("PRIVATE_SYNTHETIC_KEY_AND_ASSAY_PATH")

    monkeypatch.setattr("demeter.analysis.kerala_observation_audit.audit_kerala_observations", fail)
    result = CliRunner().invoke(app, ["evidence", "kerala-observations"])
    assert result.exit_code == 1
    assert "PRIVATE_SYNTHETIC_KEY_AND_ASSAY_PATH" not in result.output
    assert "invalid" in result.output
