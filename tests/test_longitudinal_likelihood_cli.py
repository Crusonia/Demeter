"""Frozen software inputs and safe aggregate-only CLI output, without source intake."""

import json
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import demeter.analysis.longitudinal_likelihood_validation as module
from demeter.cli import app
from demeter.schema import EvidenceRegistry


PRIVATE = "PRIVATE_SYNTHETIC_MARKER"
COMMAND = ["evidence", "longitudinal-likelihood"]


def assert_no_clinical_promotion(report):
    assert report["validation_only"] is True
    assert report["evidence_grade"] == "E"
    assert report["model_role"] == "benchmark_only"
    for field in (
        "source_eligibility_promoted",
        "clinical_fit_performed",
        "clinical_fit_allowed",
        "independent_prediction_performed",
        "engine_activation_allowed",
        "engine_parameters_updated",
        "scientific_release_ready",
    ):
        assert report[field] is False
    assert report["external_human_scientific_review"] == "pending"


@pytest.fixture(scope="module")
def base_registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


@pytest.fixture
def selected(base_registry):
    return base_registry.model_copy(deep=True)


@pytest.fixture(scope="module")
def real_report(base_registry):
    # One evaluation of the committed synthetic fixture; no source observations.
    report = module.likelihood_software_report(base_registry)
    assert report["software_checks_passed"] is True, report
    return report


@pytest.fixture
def no_arithmetic(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("An invalid frozen input reached generator arithmetic")

    monkeypatch.setattr(module, "_generator", forbidden)
    return calls


def assert_blocked_before_arithmetic(selected, no_arithmetic, stage):
    report = module.likelihood_software_report(selected)
    assert report["computational_evaluation_passed"] is False
    assert report["software_checks_passed"] is False
    assert report["failure"]["stage"] == stage
    assert no_arithmetic == []
    assert_no_clinical_promotion(report)
    encoded = json.dumps(report, allow_nan=False)
    assert PRIVATE not in encoded
    assert "contributions" not in report


def test_real_frozen_report_retains_local_scope_and_all_nonpromotion_flags(real_report):
    assert real_report["computational_evaluation_passed"] is True
    assert all(value is True for value in real_report["checks"].values())
    assert_no_clinical_promotion(real_report)
    diagnostics = real_report["local_identification"]
    assert diagnostics["full_design"]["local_numerical_rank"] == 9
    assert diagnostics["scalar_design"]["local_numerical_rank"] == 1
    for design in ("full_design", "scalar_design"):
        assert diagnostics[design]["global_identification_established"] is False
        assert diagnostics[design]["causal_identification_established"] is False
    assert real_report["source_gate"]["default_clinical_fit_eligibility"] is False
    assert "participants" not in real_report
    assert "participant_ids" not in real_report
    json.dumps(real_report, allow_nan=False)
    assert real_report["provenance"]["numerical_amendment_path"] == module.AMENDMENT_PATH
    assert real_report["provenance"]["numerical_amendment_sha256"] == module.AMENDMENT_SHA256


@pytest.mark.parametrize(
    "constant", ["AMENDMENT_PATH", "PRIOR_AMENDMENT_PATH", "PRIOR_REPLAY_PATH"]
)
def test_missing_amendment_is_not_replaced_by_cli_failure_output(tmp_path, monkeypatch, constant):
    missing = tmp_path / "missing-numerical-amendment.json"
    monkeypatch.setattr(module, constant, str(missing))
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(missing)])
    assert result.exit_code == 1
    assert "Output must not replace" in result.output
    assert not missing.exists()


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "extra", "reordered", "tuple"))
def test_changed_parameter_links_block_before_arithmetic(selected, no_arithmetic, mutation):
    spec = selected.datasets[module.DATASET]
    keys = spec["parameter_keys"]
    if mutation == "missing":
        keys.pop()
    elif mutation == "duplicate":
        keys.append(keys[0])
    elif mutation == "extra":
        keys.append(PRIVATE)
    elif mutation == "reordered":
        keys.reverse()
    else:
        spec["parameter_keys"] = tuple(keys)
    assert_blocked_before_arithmetic(selected, no_arithmetic, "registered_inputs")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("protocol_sha256", "0" * 64),
        ("rfc_sha256", "0" * 64),
        ("protocol_path", PRIVATE),
        ("model_role", "health_model"),
        ("status", "observed"),
        ("evidence_grade", "C"),
        ("clinical_fit_allowed", True),
        ("engine_activation_allowed", True),
        ("clinical_fit_allowed", 0),
    ),
)
def test_dataset_pin_and_scope_drift_block_before_arithmetic(selected, no_arithmetic, field, value):
    selected.datasets[module.DATASET][field] = value
    assert_blocked_before_arithmetic(selected, no_arithmetic, "frozen_contract")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("key", PRIVATE),
        ("value", 0.11),
        ("value", "0.10"),
        ("value", float("nan")),
        ("unit", PRIVATE),
        ("status", "estimated"),
        ("evidence_grade", "C"),
        ("model_role", "health_model"),
        ("source_id", PRIVATE),
        ("unresolved", True),
        ("uncertainty", None),
    ),
)
def test_parameter_identity_type_or_role_drift_blocks_before_arithmetic(
    selected, no_arithmetic, field, value
):
    key = "longitudinal_toy_n_to_p_rate"
    selected.parameters[key] = selected.parameters[key].model_copy(update={field: value})
    assert_blocked_before_arithmetic(selected, no_arithmetic, "registered_inputs")


def test_boolean_zero_cannot_masquerade_as_numeric_time_origin(selected, no_arithmetic):
    key = "longitudinal_toy_time_origin_years"
    selected.parameters[key] = selected.parameters[key].model_copy(update={"value": False})
    assert_blocked_before_arithmetic(selected, no_arithmetic, "registered_inputs")


@pytest.mark.parametrize(
    "constant",
    ("PROTOCOL_PATH", "RFC_PATH", "AMENDMENT_PATH", "PRIOR_AMENDMENT_PATH", "PRIOR_REPLAY_PATH"),
)
def test_actual_changed_contract_bytes_fail_safely_before_arithmetic(
    selected, no_arithmetic, tmp_path, monkeypatch, constant
):
    corrupted = tmp_path / "corrupted-contract"
    corrupted.write_text(PRIVATE, encoding="utf-8")
    monkeypatch.setattr(module, constant, str(corrupted))
    assert_blocked_before_arithmetic(selected, no_arithmetic, "frozen_contract")
    assert corrupted.read_text(encoding="utf-8") == PRIVATE


@pytest.fixture
def stub_cli(selected, real_report, monkeypatch):
    # The public wire format uses JSON arrays for immutable library tuples.
    report = json.loads(json.dumps(real_report, allow_nan=False))
    monkeypatch.setattr(module, "load_likelihood_registry", lambda _path: selected)
    monkeypatch.setattr(module, "likelihood_software_report", lambda _registry: report)
    return report


def test_new_aggregate_output_and_stdout_match_without_clinical_promotion(stub_cli, tmp_path):
    output = tmp_path / "new-directory" / "aggregate.json"
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output)])
    assert result.exit_code == 0, result.output
    persisted = json.loads(output.read_bytes())
    assert persisted == json.loads(result.output) == stub_cli
    assert_no_clinical_promotion(persisted)
    assert "participant_ids" not in persisted


def test_failed_check_report_is_saved_and_exits_one(stub_cli, tmp_path):
    stub_cli["software_checks_passed"] = False
    stub_cli["checks"]["linked_forward_matches_enumeration"] = False
    output = tmp_path / "failed-check.json"
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output)])
    assert result.exit_code == 1
    assert json.loads(output.read_bytes()) == stub_cli
    assert_no_clinical_promotion(json.loads(result.output))


def test_real_pin_failure_is_persisted_without_math_or_private_tokens(
    selected, no_arithmetic, tmp_path, monkeypatch
):
    monkeypatch.setattr(module, "PROTOCOL_SHA256", "0" * 64)
    output = tmp_path / "real-pin-failure.json"
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output)])
    assert result.exit_code == 1
    report = json.loads(output.read_bytes())
    assert report["failure"]["stage"] == "registered_registry"
    assert report["software_checks_passed"] is False
    assert no_arithmetic == []
    assert_no_clinical_promotion(report)


def test_real_valid_yaml_loader_and_cli_preserve_registered_fixture(
    base_registry, real_report, tmp_path, monkeypatch
):
    seen = []

    def report_only(selected):
        seen.append(selected.content_hash)
        return real_report

    monkeypatch.setattr(module, "likelihood_software_report", report_only)
    output = tmp_path / "valid-loader.json"
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert seen == [base_registry.content_hash]
    assert_no_clinical_promotion(json.loads(output.read_bytes()))


@pytest.mark.parametrize("invalid", ("missing", "malformed_yaml", "invalid_schema"))
def test_real_invalid_registry_saves_sanitized_blocked_report(tmp_path, no_arithmetic, invalid):
    evidence = tmp_path / f"{PRIVATE}-{invalid}.yaml"
    if invalid == "malformed_yaml":
        evidence.write_text(f"parameters: [\n{PRIVATE}", encoding="utf-8")
    elif invalid == "invalid_schema":
        evidence.write_text(f"parameters: {PRIVATE}\n", encoding="utf-8")
    output = tmp_path / "registry-failure.json"
    result = CliRunner().invoke(
        app, [*COMMAND, "--evidence", str(evidence), "--output", str(output)]
    )
    assert result.exit_code == 1
    report = json.loads(output.read_bytes())
    assert report["failure"]["stage"] == "registered_registry"
    assert report["software_checks_passed"] is False
    assert PRIVATE not in result.output
    assert no_arithmetic == []
    assert_no_clinical_promotion(report)


@pytest.mark.parametrize(
    ("key", "raw_value"),
    (
        ("longitudinal_toy_time_origin_years", False),
        ("longitudinal_toy_n_to_p_rate", "0.10"),
    ),
)
def test_real_yaml_values_cannot_be_coerced_before_scoped_guard(
    tmp_path, no_arithmetic, key, raw_value
):
    raw = yaml.safe_load(Path("evidence/parameters.yaml").read_text(encoding="utf-8"))
    raw["parameters"][key]["value"] = raw_value
    evidence = tmp_path / f"{PRIVATE}-coercion.yaml"
    evidence.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    output = tmp_path / "coercion-failure.json"
    result = CliRunner().invoke(
        app, [*COMMAND, "--evidence", str(evidence), "--output", str(output)]
    )
    assert result.exit_code == 1
    report = json.loads(output.read_bytes())
    assert report["failure"]["stage"] == "registered_registry"
    assert report["computational_evaluation_passed"] is False
    assert report["software_checks_passed"] is False
    assert no_arithmetic == []
    assert PRIVATE not in result.output
    assert_no_clinical_promotion(report)


@pytest.mark.parametrize("field", ("protocol_path", "rfc_path"))
def test_invalid_raw_scalar_cannot_create_failure_report_at_missing_declared_contract(
    tmp_path, no_arithmetic, field
):
    raw = yaml.safe_load(Path("evidence/parameters.yaml").read_text(encoding="utf-8"))
    raw["parameters"]["longitudinal_toy_time_origin_years"]["value"] = False
    protected = tmp_path / "missing-contract-directory" / f"{field}.json"
    raw["datasets"][module.DATASET][field] = str(protected)
    evidence = tmp_path / f"{PRIVATE}-invalid-scalar.yaml"
    evidence.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    result = CliRunner().invoke(
        app, [*COMMAND, "--evidence", str(evidence), "--output", str(protected)]
    )
    assert result.exit_code == 1
    assert "Output must not replace" in result.output
    assert not protected.exists()
    assert no_arithmetic == []
    assert PRIVATE not in result.output


@pytest.fixture
def protected_paths(selected, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = selected.datasets[module.DATASET]
    evidence = tmp_path / "custom" / "registry.yaml"
    spec["protocol_path"] = str(tmp_path / "custom" / "protocol.json")
    spec["rfc_path"] = str(tmp_path / "custom" / "rfc.md")
    paths = [
        tmp_path / "evidence" / "parameters.yaml",
        evidence,
        tmp_path / module.PROTOCOL_PATH,
        tmp_path / module.RFC_PATH,
        Path(spec["protocol_path"]),
        Path(spec["rfc_path"]),
    ]
    monkeypatch.setattr(module, "load_likelihood_registry", lambda _path: selected)

    def forbidden(_registry):
        raise AssertionError("Protected output destination reached the evaluator")

    monkeypatch.setattr(module, "likelihood_software_report", forbidden)
    return evidence, paths


@pytest.mark.parametrize("existing", (True, False))
@pytest.mark.parametrize("index", range(6))
def test_protected_canonical_or_redirected_paths_remain_unchanged_even_if_missing(
    protected_paths, existing, index
):
    evidence, paths = protected_paths
    output = paths[index]
    if existing:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"Immutable synthetic metadata")
    result = CliRunner().invoke(
        app, [*COMMAND, "--evidence", str(evidence), "--output", str(output)]
    )
    assert result.exit_code == 1
    assert "Output must not replace" in result.output
    if existing:
        assert output.read_bytes() == b"Immutable synthetic metadata"
    else:
        assert not output.exists()


def test_existing_unrelated_report_is_not_replaced(stub_cli, tmp_path):
    output = tmp_path / "existing.json"
    output.write_bytes(b"Existing report remains immutable")
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_bytes() == b"Existing report remains immutable"


def test_hardlink_alias_cannot_replace_existing_metadata(stub_cli, tmp_path):
    source = tmp_path / "metadata.json"
    source.write_bytes(b"Immutable synthetic source metadata")
    alias = tmp_path / "alias.json"
    try:
        os.link(source, alias)
    except OSError:
        pytest.skip("Host cannot create a synthetic hardlink")
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(alias)])
    assert result.exit_code == 1
    assert source.read_bytes() == alias.read_bytes() == b"Immutable synthetic source metadata"


@pytest.mark.parametrize("target_exists", (True, False))
def test_existing_or_dangling_symlink_output_is_never_written(stub_cli, tmp_path, target_exists):
    target = tmp_path / "target.json"
    if target_exists:
        target.write_bytes(b"Immutable symlink target")
    alias = tmp_path / "symlink-output.json"
    try:
        alias.symlink_to(target)
    except OSError:
        pytest.skip("Host cannot create a synthetic symlink")
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(alias)])
    assert result.exit_code == 1
    assert alias.is_symlink()
    if target_exists:
        assert target.read_bytes() == b"Immutable symlink target"
    else:
        assert not target.exists()


def test_exclusive_creation_preserves_a_file_created_after_metadata_check(
    selected, real_report, tmp_path, monkeypatch
):
    output = tmp_path / "race.json"
    monkeypatch.setattr(module, "load_likelihood_registry", lambda _path: selected)

    def concurrent_writer(_registry):
        output.write_bytes(b"Another writer owns this file")
        return real_report

    monkeypatch.setattr(module, "likelihood_software_report", concurrent_writer)
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_bytes() == b"Another writer owns this file"


@pytest.mark.parametrize("method", ("resolve", "exists", "is_symlink"))
def test_output_metadata_failure_is_sanitized_without_any_write(
    stub_cli, tmp_path, monkeypatch, method
):
    output = tmp_path / "unresolved-output.json"
    original = getattr(Path, method)

    def inaccessible(path, *args, **kwargs):
        if path == output:
            raise PermissionError(PRIVATE)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, method, inaccessible)
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output)])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert PRIVATE not in result.output
    assert not output.parent.joinpath(output.name).is_file()


def test_output_parent_file_error_does_not_leak_path_or_change_existing_bytes(stub_cli, tmp_path):
    parent = tmp_path / PRIVATE
    parent.write_bytes(b"A file cannot become an output directory")
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(parent / "report.json")])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert PRIVATE not in result.output
    assert parent.read_bytes() == b"A file cannot become an output directory"


@pytest.mark.parametrize("unsupported", ("--raw", "--participants", "--clinical-fit"))
def test_command_does_not_accept_participant_import_or_clinical_fit_options(tmp_path, unsupported):
    output = tmp_path / "not-created.json"
    result = CliRunner().invoke(app, [*COMMAND, "--output", str(output), unsupported])
    assert result.exit_code == 2
    assert not output.exists()
