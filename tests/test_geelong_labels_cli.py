"""Offline Geelong reproduction, saved failures, and immutable evidence outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.schema import EvidenceRegistry

PRIVATE = "UNTRUSTED_SOURCE_PATH_OR_ERROR"


@pytest.fixture
def protected_fixture(tmp_path, monkeypatch):
    """Synthetic immutable paths exercise guards without touching real sources."""
    selected = EvidenceRegistry.from_yaml("evidence/parameters.yaml").model_copy(deep=True)
    evidence = tmp_path / "parameters.yaml"
    source = tmp_path / "source" / "publication.xml"
    protocol = tmp_path / "protocol.json"
    bundle = tmp_path / "bundle.json"
    spec = selected.datasets["geelong_label_pairs"]
    spec.update(source_path=str(source), protocol_path=str(protocol), bundle_path=str(bundle))
    protected = [evidence, source, protocol, bundle]
    for path in protected:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Synthetic immutable publication/metadata; no participant records")
    monkeypatch.setattr("demeter.cli.registry", lambda _: selected)

    def audit(_registry, _source=None, *, working_likelihood=True):
        return {
            "source_audit_passed": True,
            "working_fit_performed": working_likelihood,
            "scientific_release_ready": False,
            "clinical_transition_fit_performed": False,
            "engine_activation_allowed": False,
        }

    monkeypatch.setattr("demeter.analysis.geelong_labels.audit_geelong_labels", audit)
    args = ["evidence", "geelong-labels", "--evidence", str(evidence)]
    return args, protected, selected


@pytest.mark.parametrize("index", range(4))
def test_output_cannot_replace_registry_source_protocol_or_bundle(protected_fixture, index):
    args, protected, _ = protected_fixture
    before = {path: path.read_bytes() for path in protected}
    result = CliRunner().invoke(app, [*args, "--output", str(protected[index])])
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert {path: path.read_bytes() for path in protected} == before


def test_override_source_and_default_archive_are_both_protected(protected_fixture, tmp_path):
    args, protected, _ = protected_fixture
    override = tmp_path / "override.xml"
    override.write_bytes(b"Synthetic source override")
    before = {path: path.read_bytes() for path in [protected[1], override]}
    for output in before:
        result = CliRunner().invoke(
            app, [*args, "--source", str(override), "--output", str(output)]
        )
        assert result.exit_code == 1
        assert "Output must not overwrite" in result.output
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("kind", ["hardlink", "symlink"])
def test_output_alias_cannot_overwrite_publication(protected_fixture, tmp_path, kind):
    args, protected, _ = protected_fixture
    source = protected[1]
    alias = tmp_path / "alias.json"
    try:
        if kind == "hardlink":
            os.link(source, alias)
        else:
            alias.symlink_to(source)
    except OSError:
        pytest.skip(f"Host cannot create a synthetic {kind}")
    before = source.read_bytes()
    result = CliRunner().invoke(app, [*args, "--output", str(alias)])
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert source.read_bytes() == alias.read_bytes() == before


@pytest.mark.parametrize("folder", ["data", "src/demeter/data/bundled", "docs/validation"])
def test_new_report_cannot_enter_immutable_default_directories(
    protected_fixture, tmp_path, monkeypatch, folder
):
    args, _, _ = protected_fixture
    monkeypatch.chdir(tmp_path)
    output = tmp_path / folder / "new-report.json"
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert not output.exists()


def test_redirected_metadata_still_protects_canonical_freeze(
    protected_fixture, tmp_path, monkeypatch
):
    args, _, _ = protected_fixture
    monkeypatch.chdir(tmp_path)
    canonical = tmp_path / "docs/validation/geelong-label-protocol-v1.json"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"Synthetic original frozen protocol")
    before = canonical.read_bytes()
    result = CliRunner().invoke(app, [*args, "--output", str(canonical)])
    assert result.exit_code == 1
    assert canonical.read_bytes() == before


@pytest.mark.parametrize("alias", [False, True], ids=["canonical-direct", "canonical-hardlink"])
def test_custom_evidence_cannot_overwrite_canonical_registry(tmp_path, monkeypatch, alias):
    """A custom input must not remove the repository's default registry guard."""
    original = Path("evidence/parameters.yaml").read_bytes()
    custom = tmp_path / "custom" / "parameters.yaml"
    canonical = tmp_path / "evidence" / "parameters.yaml"
    for path in (custom, canonical):
        path.parent.mkdir(parents=True)
        path.write_bytes(original)
    # These are valid registry copies, not the opaque path-guard fixture bytes.
    assert "geelong_label_pairs" in EvidenceRegistry.from_yaml(custom).datasets
    output = canonical
    if alias:
        output = tmp_path / "canonical-registry-alias.json"
        try:
            os.link(canonical, output)
        except OSError:
            pytest.skip("Host cannot create a synthetic hardlink")
    monkeypatch.chdir(tmp_path)
    invoked = []

    def audit(*args, **kwargs):
        invoked.append(True)
        return {"source_audit_passed": True, "working_fit_performed": True}

    monkeypatch.setattr("demeter.analysis.geelong_labels.audit_geelong_labels", audit)
    result = CliRunner().invoke(
        app,
        ["evidence", "geelong-labels", "--evidence", str(custom), "--output", str(output)],
    )
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert not invoked
    assert canonical.read_bytes() == custom.read_bytes() == output.read_bytes() == original


@pytest.mark.parametrize("descriptive_only", [False, True])
def test_mode_is_explicit_and_unrelated_existing_report_can_be_updated(
    protected_fixture, tmp_path, descriptive_only
):
    args, protected, _ = protected_fixture
    output = tmp_path / "outputs" / "report.json"
    output.parent.mkdir()
    output.write_bytes(b"Prior unrelated generated report")
    before = {path: path.read_bytes() for path in protected}
    options = ["--descriptive-only"] if descriptive_only else []
    result = CliRunner().invoke(app, [*args, *options, "--output", str(output)])
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_bytes())
    assert report["working_fit_performed"] is not descriptive_only
    assert report["scientific_release_ready"] is False
    assert {path: path.read_bytes() for path in protected} == before


def test_stdout_only_does_not_require_output(protected_fixture):
    args, _, _ = protected_fixture
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["source_audit_passed"] is True


def test_failed_audit_is_saved_with_failing_exit_and_no_partial_fit(
    protected_fixture, tmp_path, monkeypatch
):
    args, _, _ = protected_fixture
    failed = {
        "source_audit_passed": False,
        "working_fit_performed": False,
        "observed_labels": None,
        "working_fit": None,
        "joint_covariance": None,
        "intervals": None,
        "scientific_release_ready": False,
        "failure": {"stage": "selected_source", "code": "synthetic_failure"},
    }
    monkeypatch.setattr(
        "demeter.analysis.geelong_labels.audit_geelong_labels", lambda *a, **k: failed
    )
    output = tmp_path / "outputs" / "failure.json"
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert json.loads(output.read_bytes()) == failed


def test_protected_path_resolution_failure_only_allows_new_output(
    protected_fixture, tmp_path, monkeypatch
):
    args, protected, _ = protected_fixture
    original = Path.resolve

    def resolve(path, *a, **k):
        if path == protected[1]:
            raise PermissionError(PRIVATE)
        return original(path, *a, **k)

    monkeypatch.setattr(Path, "resolve", resolve)
    failed = {"source_audit_passed": False, "working_fit_performed": False}
    monkeypatch.setattr(
        "demeter.analysis.geelong_labels.audit_geelong_labels", lambda *a, **k: failed
    )
    fresh = tmp_path / "fresh.json"
    result = CliRunner().invoke(app, [*args, "--output", str(fresh)])
    assert result.exit_code == 1
    assert json.loads(fresh.read_bytes()) == failed
    assert PRIVATE not in result.output
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"Potential unresolvable source alias")
    before = existing.read_bytes()
    result = CliRunner().invoke(app, [*args, "--output", str(existing)])
    assert result.exit_code == 1
    assert existing.read_bytes() == before
    assert PRIVATE not in result.output


def test_invalid_registry_exception_details_are_not_echoed(protected_fixture, monkeypatch):
    args, _, _ = protected_fixture

    def failure(_):
        raise ValueError(PRIVATE)

    monkeypatch.setattr("demeter.cli.registry", failure)
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert "metadata or output path is invalid" in result.output
    assert PRIVATE not in result.output


@pytest.mark.parametrize("descriptive_only", [False, True])
def test_actual_archived_publication_is_reproducible_offline(tmp_path, descriptive_only):
    output = tmp_path / "geelong.json"
    options = ["--descriptive-only"] if descriptive_only else []
    result = CliRunner().invoke(
        app, ["evidence", "geelong-labels", *options, "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_bytes())
    assert report["source_audit_passed"] is True
    assert report["working_fit_performed"] is not descriptive_only
    assert report["provenance"]["network_used"] is False
    assert report["provenance"]["participant_records_used"] is False
    assert report["scientific_release_ready"] is False
    assert report["engine_activation_allowed"] is False
    assert report["clinical_transition_fit_performed"] is False
    if descriptive_only:
        for key in ("working_fit", "joint_covariance", "intervals"):
            assert report[key] is None


def test_missing_source_sibling_report_persists_sanitized_failure(tmp_path):
    source = tmp_path / f"{PRIVATE}.xml"
    output = tmp_path / "failure.json"
    result = CliRunner().invoke(
        app, ["evidence", "geelong-labels", "--source", str(source), "--output", str(output)]
    )
    assert result.exit_code == 1
    report = json.loads(output.read_bytes())
    assert report["source_audit_passed"] is False
    assert report["observed_labels"] is None
    assert report["working_fit"] is None
    assert PRIVATE not in result.output
    assert PRIVATE not in json.dumps(report)


def test_unreadable_source_failure_is_saved_without_exception_text(tmp_path, monkeypatch):
    source = tmp_path / "unreadable.xml"
    source.write_bytes(b"Synthetic unreadable source")
    original = Path.read_bytes

    def read(path):
        if path == source:
            raise PermissionError(PRIVATE)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    output = tmp_path / "failure.json"
    result = CliRunner().invoke(
        app, ["evidence", "geelong-labels", "--source", str(source), "--output", str(output)]
    )
    assert result.exit_code == 1
    report = json.loads(output.read_bytes())
    assert report["failure"]["stage"] == "selected_source"
    assert report["observed_labels"] is None
    assert PRIVATE not in result.output
    assert PRIVATE not in json.dumps(report)
