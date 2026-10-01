"""Source/output immutability and honest persisted failure states."""

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.schema import EvidenceRegistry


@pytest.fixture
def source_fixture(tmp_path, monkeypatch):
    selected = EvidenceRegistry.from_yaml("evidence/parameters.yaml").model_copy(deep=True)
    raw = tmp_path / "raw"
    raw.mkdir()
    evidence = tmp_path / "parameters.yaml"
    spec = selected.datasets["whitehall_fpg_endpoint"]
    spec["protocol_path"] = str(tmp_path / "protocol.json")
    spec["receipts_path"] = str(tmp_path / "receipts.json")
    protected = [evidence, Path(spec["protocol_path"]), Path(spec["receipts_path"])]
    protected += [raw / selected.sources[key].raw_filename for key in spec["source_ids"].values()]
    for path in protected:
        path.write_bytes(b"Synthetic immutable source; no clinical records")

    monkeypatch.setattr("demeter.cli.registry", lambda _path: selected)

    def audit(_registry, _raw, *, working_likelihood):
        return {"source_audit_passed": True, "working_fit_performed": working_likelihood}

    monkeypatch.setattr("demeter.analysis.whitehall_endpoints.audit_whitehall_endpoint", audit)
    args = ["evidence", "whitehall-endpoint", "--raw", str(raw), "--evidence", str(evidence)]
    return args, protected, raw


@pytest.mark.parametrize("index", range(5))
def test_output_cannot_replace_evidence_contract_receipts_or_sources(source_fixture, index):
    args, protected, _ = source_fixture
    before = {path: path.read_bytes() for path in protected}
    result = CliRunner().invoke(app, [*args, "--output", str(protected[index])])
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert {path: path.read_bytes() for path in protected} == before


def test_hardlink_output_cannot_replace_source(source_fixture, tmp_path):
    args, protected, _ = source_fixture
    output = tmp_path / "source-alias.json"
    try:
        os.link(protected[-1], output)
    except OSError:
        pytest.skip("Host cannot create a synthetic hardlink")
    before = protected[-1].read_bytes()
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert protected[-1].read_bytes() == output.read_bytes() == before


def test_sources_directory_is_not_an_output_destination(source_fixture):
    args, _, raw = source_fixture
    output = raw / "new.json"
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert not output.exists()


@pytest.mark.parametrize("descriptive_only", [True, False])
def test_analysis_mode_is_explicit_and_report_is_saved(source_fixture, tmp_path, descriptive_only):
    args, protected, _ = source_fixture
    output = tmp_path / "outputs" / "endpoint.json"
    before = {path: path.read_bytes() for path in protected}
    options = ["--descriptive-only"] if descriptive_only else []
    result = CliRunner().invoke(app, [*args, *options, "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_bytes())["working_fit_performed"] is not descriptive_only
    assert {path: path.read_bytes() for path in protected} == before


def test_failed_source_report_is_saved_and_cli_fails(source_fixture, tmp_path, monkeypatch):
    args, _, _ = source_fixture
    output = tmp_path / "outputs" / "endpoint.json"
    report = {
        "source_audit_passed": False,
        "working_fit_performed": False,
        "failure": "Synthetic source drift",
    }
    monkeypatch.setattr(
        "demeter.analysis.whitehall_endpoints.audit_whitehall_endpoint", lambda *a, **k: report
    )
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert json.loads(output.read_bytes()) == report


def test_unreadable_raw_metadata_still_saves_failure_without_exposing_path(
    source_fixture, tmp_path, monkeypatch
):
    args, _, raw = source_fixture
    original = Path.resolve

    def resolve(path, *a, **k):
        if path == raw:
            raise PermissionError("Untrusted source path marker")
        return original(path, *a, **k)

    monkeypatch.setattr(Path, "resolve", resolve)
    report = {"source_audit_passed": False, "working_fit_performed": False}
    monkeypatch.setattr(
        "demeter.analysis.whitehall_endpoints.audit_whitehall_endpoint", lambda *a, **k: report
    )
    output = tmp_path / "failure.json"
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert json.loads(output.read_bytes()) == report
    assert "Untrusted source path marker" not in result.output


def test_unresolved_source_alias_cannot_replace_existing_output(
    source_fixture, tmp_path, monkeypatch
):
    args, _, raw = source_fixture
    original = Path.resolve

    def resolve(path, *a, **k):
        if path == raw:
            raise PermissionError("Untrusted source path marker")
        return original(path, *a, **k)

    monkeypatch.setattr(Path, "resolve", resolve)
    output = tmp_path / "existing.json"
    output.write_bytes(b"Immutable existing report or source alias")
    before = output.read_bytes()
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_bytes() == before


def test_redirected_metadata_cannot_overwrite_canonical_frozen_record(
    source_fixture, tmp_path, monkeypatch
):
    args, _, _ = source_fixture
    monkeypatch.chdir(tmp_path)
    frozen = tmp_path / "docs/validation/whitehall-fpg-endpoint-protocol-v1.json"
    frozen.parent.mkdir(parents=True)
    frozen.write_bytes(b"Original canonical freeze")
    result = CliRunner().invoke(app, [*args, "--output", str(frozen)])
    assert result.exit_code == 1
    assert frozen.read_bytes() == b"Original canonical freeze"
