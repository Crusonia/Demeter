"""Synthetic CLI regressions preserve frozen inputs and failed audit reports."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import demeter.analysis.paired_remission_sources as module
from demeter.cli import app


PRIVATE = "UNTRUSTED_SOURCE_PATH_OR_TEXT"


@pytest.fixture
def source_fixture(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    evidence = tmp_path / "parameters.yaml"
    spec = {
        "protocol_path": str(tmp_path / "protocol.json"),
        "receipts_path": str(tmp_path / "receipts.json"),
        "amendment_path": str(tmp_path / "amendment.json"),
        "failed_intake_path": str(tmp_path / "failed-intake.json"),
        "source_ids": dict(module.SOURCE_IDS),
    }
    sources = {
        key: SimpleNamespace(raw_filename=f"synthetic-{label}.raw")
        for label, key in module.SOURCE_IDS.items()
    }
    selected = SimpleNamespace(datasets={module.DATASET: spec}, sources=sources)
    protected = [
        evidence,
        *[
            Path(spec[key])
            for key in ("protocol_path", "receipts_path", "amendment_path", "failed_intake_path")
        ],
    ]
    protected += [raw / source.raw_filename for source in sources.values()]
    for path in protected:
        path.write_bytes(b"Synthetic immutable input, no clinical records")
    monkeypatch.setattr("demeter.cli.registry", lambda _path: selected)
    report = {
        "source_audit_passed": True,
        "results": {"scope_conditional": True},
        "clinical_fit_performed": False,
        "engine_parameters_updated": False,
    }
    monkeypatch.setattr(module, "audit_paired_remission", lambda *_: report)
    args = ["evidence", "paired-remission", "--raw", str(raw), "--evidence", str(evidence)]
    return SimpleNamespace(
        args=args, protected=protected, raw=raw, spec=spec, registry=selected, report=report
    )


@pytest.mark.parametrize("index", range(8))
def test_output_cannot_replace_evidence_contract_amendment_receipts_or_three_sources(
    source_fixture, index
):
    before = {path: path.read_bytes() for path in source_fixture.protected}
    result = CliRunner().invoke(
        app, [*source_fixture.args, "--output", str(source_fixture.protected[index])]
    )
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    "constant",
    (
        "PROTOCOL_PATH",
        "RECEIPTS_PATH",
        "AMENDMENT_PATH",
        "FAILURE_PATH",
        "V2_PATH",
        "V2_FAILURE_PATH",
    ),
)
def test_redirected_registry_cannot_overwrite_any_canonical_frozen_record(
    source_fixture, tmp_path, monkeypatch, constant
):
    monkeypatch.chdir(tmp_path)
    frozen = tmp_path / getattr(module, constant)
    frozen.parent.mkdir(parents=True, exist_ok=True)
    frozen.write_bytes(b"Original canonical frozen record")
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(frozen)])
    assert result.exit_code == 1
    assert frozen.read_bytes() == b"Original canonical frozen record"


@pytest.mark.parametrize("protected_index", (0, 3, 4, 7))
def test_hardlink_alias_cannot_replace_registry_amendment_or_source(
    source_fixture, tmp_path, protected_index
):
    source = source_fixture.protected[protected_index]
    output = tmp_path / "input-alias.json"
    try:
        os.link(source, output)
    except OSError:
        pytest.skip("Host cannot create a synthetic hardlink")
    before = source.read_bytes()
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_bytes() == source.read_bytes() == before


def test_raw_directory_is_not_an_output_destination(source_fixture):
    output = source_fixture.raw / "new.json"
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert not output.exists()


def test_raw_symlink_directory_cannot_hide_output_under_sources(source_fixture, tmp_path):
    alias = tmp_path / "raw-alias"
    try:
        alias.symlink_to(source_fixture.raw, target_is_directory=True)
    except OSError:
        pytest.skip("Host cannot create a synthetic directory symlink")
    output = alias / "new.json"
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert not output.exists()


def test_successful_conditional_aggregate_report_is_saved_without_changing_inputs(
    source_fixture, tmp_path
):
    output = tmp_path / "outputs" / "paired.json"
    before = {path: path.read_bytes() for path in source_fixture.protected}
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_bytes()) == source_fixture.report
    assert {path: path.read_bytes() for path in before} == before
    assert PRIVATE not in result.output


def test_stdout_only_success_requires_no_output_file(source_fixture):
    before = set(source_fixture.raw.parent.iterdir())
    result = CliRunner().invoke(app, source_fixture.args)
    assert result.exit_code == 0
    assert '"source_audit_passed": true' in result.output
    assert set(source_fixture.raw.parent.iterdir()) == before


def test_failed_source_audit_is_saved_and_exits_nonzero(source_fixture, tmp_path, monkeypatch):
    report = {
        "source_audit_passed": False,
        "results": None,
        "clinical_fit_performed": False,
        "failure": {"stage": "source_bytes", "code": "observation_contract_not_verified"},
    }
    monkeypatch.setattr(module, "audit_paired_remission", lambda *_: report)
    output = tmp_path / "outputs" / "failed.json"
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert json.loads(output.read_bytes()) == report
    assert PRIVATE not in result.output


def test_unreadable_raw_metadata_still_saves_sanitized_failed_report(
    source_fixture, tmp_path, monkeypatch
):
    original = Path.resolve

    def unreadable(path, *args, **kwargs):
        if path == source_fixture.raw:
            raise PermissionError(PRIVATE)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", unreadable)
    report = {
        "source_audit_passed": False,
        "results": None,
        "failure": {"stage": "source_bytes", "code": "observation_contract_not_verified"},
    }
    monkeypatch.setattr(module, "audit_paired_remission", lambda *_: report)
    output = tmp_path / "failed.json"
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert json.loads(output.read_bytes()) == report
    assert PRIVATE not in result.output


def test_unresolved_source_alias_cannot_replace_existing_output(
    source_fixture, tmp_path, monkeypatch
):
    original = Path.resolve

    def unreadable(path, *args, **kwargs):
        if path == source_fixture.raw:
            raise PermissionError(PRIVATE)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", unreadable)
    output = tmp_path / "existing.json"
    output.write_bytes(b"Existing report or unresolved source alias")
    before = output.read_bytes()
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_bytes() == before
    assert PRIVATE not in result.output


def test_output_path_resolution_failure_is_private_and_saves_nothing(
    source_fixture, tmp_path, monkeypatch
):
    output = tmp_path / "failed.json"
    original = Path.resolve

    def unreadable(path, *args, **kwargs):
        if path == output:
            raise PermissionError(PRIVATE)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", unreadable)
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert not output.exists()
    assert PRIVATE not in result.output


def test_save_failure_is_sanitized_instead_of_reporting_success(
    source_fixture, tmp_path, monkeypatch
):
    output = tmp_path / "failed.json"
    original = Path.open

    def unreadable(path, *args, **kwargs):
        if path == output:
            raise PermissionError(PRIVATE)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", unreadable)
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert "Unable to save" in result.output
    assert PRIVATE not in result.output
    assert not output.exists()


@pytest.mark.parametrize(
    "error", (ValueError(PRIVATE), KeyError(PRIVATE), PermissionError(PRIVATE))
)
def test_registry_errors_do_not_expose_untrusted_details(
    source_fixture, tmp_path, monkeypatch, error
):
    def fail(*args):
        raise error

    monkeypatch.setattr("demeter.cli.registry", fail)
    output = tmp_path / "failed.json"
    result = CliRunner().invoke(app, [*source_fixture.args, "--output", str(output)])
    assert result.exit_code == 1
    assert PRIVATE not in result.output
    assert not output.exists()
