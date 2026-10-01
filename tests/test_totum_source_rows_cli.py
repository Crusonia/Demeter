"""CLI persistence/immutability checks, independent of clinical source values."""

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from demeter.cli import app
from demeter.schema import EvidenceRegistry


@pytest.fixture
def cli_sources(tmp_path, monkeypatch):
    selected = EvidenceRegistry.from_yaml("evidence/parameters.yaml").model_copy(deep=True)
    raw = tmp_path / "raw"
    raw.mkdir()
    evidence = tmp_path / "parameters.yaml"
    evidence.write_bytes(b"Synthetic registry persistence fixture")
    spec = selected.datasets["totum_source_row_adequacy"]
    spec["protocol_path"] = str(tmp_path / "protocol.json")
    spec["receipts_path"] = str(tmp_path / "receipts.json")
    protected = [evidence, Path(spec["protocol_path"]), Path(spec["receipts_path"])]
    protected += [raw / selected.sources[key].raw_filename for key in spec["source_ids"].values()]
    for path in protected[1:]:
        path.write_bytes(b"Synthetic source bytes; not clinical records")

    monkeypatch.setattr("demeter.cli.registry", lambda _path: selected)
    monkeypatch.setattr(
        "demeter.analysis.totum_source_rows.audit_totum_source_rows",
        lambda _registry, _raw: {"source_audit_passed": True, "fit_ready": False},
    )
    args = ["evidence", "totum-source-rows", "--raw", str(raw), "--evidence", str(evidence)]
    return args, protected


@pytest.mark.parametrize("index", range(8))
def test_cli_never_overwrites_registry_contract_receipt_or_any_source(cli_sources, index):
    args, protected = cli_sources
    output = protected[index]
    before = {path: path.read_bytes() for path in protected}
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert {path: path.read_bytes() for path in protected} == before


def test_cli_never_overwrites_source_through_hardlink_alias(cli_sources, tmp_path):
    args, protected = cli_sources
    output = tmp_path / "source-alias.json"
    try:
        os.link(protected[-1], output)
    except OSError:
        pytest.skip("Host cannot create a synthetic hardlink")
    before = protected[-1].read_bytes()
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert "Output must not overwrite" in result.output
    assert protected[-1].read_bytes() == output.read_bytes() == before


def test_cli_saves_only_a_scoped_aggregate_report(cli_sources, tmp_path):
    args, protected = cli_sources
    output = tmp_path / "outputs" / "coverage.json"
    before = {path: path.read_bytes() for path in protected}
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(output.read_bytes()) == {"source_audit_passed": True, "fit_ready": False}
    assert {path: path.read_bytes() for path in protected} == before


def test_cli_contract_failure_does_not_publish_a_success_artifact(
    cli_sources, tmp_path, monkeypatch
):
    args, _ = cli_sources

    def fail(_registry, _raw):
        raise ValueError("Synthetic contract drift")

    monkeypatch.setattr("demeter.analysis.totum_source_rows.audit_totum_source_rows", fail)
    output = tmp_path / "outputs" / "coverage.json"
    result = CliRunner().invoke(app, [*args, "--output", str(output)])
    assert result.exit_code == 1
    assert "Synthetic contract drift" in result.output
    assert not output.exists()
