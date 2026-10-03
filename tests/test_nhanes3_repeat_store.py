"""Source-store checks with invented bytes and temporary protocol identities.

No test acquires or parses participant records. Independent receipt-byte/code
admission belongs to the public wrapper, not this lower-level helper.
"""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from demeter.data import nhanes3_repeat_store as store
from demeter.schema import EvidenceRegistry


@dataclass
class Case:
    registry: EvidenceRegistry
    protocol: dict
    source: Path
    source_admission: dict
    code_admission: dict
    manifest: dict
    prior: Path
    payloads: dict

    def verify(self):
        return store.verify(self.registry, self.source_admission, self.code_admission, self.source)

    def repin_manifest(self):
        content = store.encoded(self.manifest)
        (self.source / "manifest.json").write_bytes(content)
        for admission in (self.source_admission, self.code_admission):
            admission["source_manifest_sha256"] = store.digest(content)


@pytest.fixture(scope="module")
def baseline():
    return (
        EvidenceRegistry.from_yaml("evidence/parameters.yaml"),
        store.read_json(store.PROTOCOL_PATH.read_bytes()),
    )


@pytest.fixture
def case(tmp_path, monkeypatch, baseline):
    registry = baseline[0].model_copy(deep=True)
    protocol = deepcopy(baseline[1])
    prior = tmp_path / "prior-immutable.json"
    prior.write_bytes(b'{"synthetic_prior":true}\n')
    protocol["existing_evidence_preservation"]["prior_frozen_and_source_artifact_sha256"] = {
        prior.as_posix(): store.digest(prior.read_bytes())
    }
    documentation = tmp_path / "documentation.json"
    documentation.write_bytes(b'{"synthetic_documentation":true}\n')
    documentary_sha = store.digest(documentation.read_bytes())
    monkeypatch.setattr(store, "DOCUMENTATION_PATH", documentation)
    monkeypatch.setattr(store, "DOCUMENTATION_SHA256", documentary_sha)
    protocol["documentation_receipts"] = {
        "path": documentation.as_posix(),
        "sha256": documentary_sha,
    }
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_bytes(store.encoded(protocol))
    protocol_sha = store.digest(protocol_path.read_bytes())
    monkeypatch.setattr(store, "PROTOCOL_PATH", protocol_path)
    monkeypatch.setattr(store, "PROTOCOL_SHA256", protocol_sha)

    def no_parser(*args, **kwargs):
        raise AssertionError("Store verification must never invoke the selected-value parser")

    monkeypatch.setattr(store.calculation, "analyze", no_parser)
    source = tmp_path / "source"
    source.mkdir()
    payloads = {
        name: f"invented source bytes for {name}\r\n".encode() for name in store.calculation.LAYOUTS
    }
    for name, content in payloads.items():
        (source / (name + ".DAT")).write_bytes(content)
    source_pins = {name: store.digest(content) for name, content in payloads.items()}
    sizes = {name: len(content) for name, content in payloads.items()}
    manifest = {
        "kind": "nhanes3_repeat_native_source_store",
        "schema_version": 1,
        "protocol_sha256": protocol_sha,
        "sources": {
            name + ".DAT": {
                "url": protocol["source_urls"][name]["url"],
                "component": name,
                "filename": name + ".DAT",
                "sha256": source_pins[name],
                "bytes": sizes[name],
                "size_bytes": sizes[name],
                "retrieved_at": "2026-01-01T00:00:00+00:00",
                "original_bytes_preserved": True,
                "participant_records_decoded": False,
            }
            for name in payloads
        },
    }
    common = {
        "schema_version": 1,
        "model_role": "benchmark_only",
        "used_source": True,
        "scientific_gates": dict.fromkeys(store.calculation.GATES, False),
        "protocol_sha256": protocol_sha,
        "source_sha256": source_pins,
    }
    source_admission = {
        **deepcopy(common),
        "kind": "nhanes3_repeat_source_admission",
        "participant_values_decoded_before_admission": False,
        "source_size_bytes": sizes,
    }
    selected_parameters = {*store.PARAMETERS.values(), "nhanes3_repeat_adult_min_years"}
    code_admission = {
        **deepcopy(common),
        "kind": "nhanes3_repeat_code_admission",
        "empirical_diagnostic_computed_before_code_admission": False,
        "registry_dataset_sha256": store.semantic_sha256(registry.datasets[store.DATASET]),
        "registry_parameter_sha256": {
            name: store.semantic_sha256(registry.parameters[name].model_dump(mode="json"))
            for name in selected_parameters
        },
        "registry_documentary_source_sha256": {
            name: store.semantic_sha256(registry.sources[name].model_dump(mode="json"))
            for name in registry.datasets[store.DATASET]["documentation_source_ids"]
        },
        "implementation_sha256": {"src/demeter/data/nhanes3_repeat.py": "a" * 64},
    }
    result = Case(
        registry, protocol, source, source_admission, code_admission, manifest, prior, payloads
    )
    result.repin_manifest()
    return result


def test_synthetic_verification_returns_exact_bytes_without_parser_or_row_exports(case):
    payloads, provenance = case.verify()
    assert payloads == case.payloads
    assert provenance["source_sha256"] == case.source_admission["source_sha256"]
    assert provenance["evidence_sha256"] == case.registry.content_hash
    assert set(provenance) == {
        "protocol_sha256",
        "source_sha256",
        "implementation_sha256",
        "evidence_sha256",
    }
    assert "SEQN" not in json.dumps(provenance)


@pytest.mark.parametrize("which", ["source_admission", "code_admission"])
@pytest.mark.parametrize("gate", store.calculation.GATES)
def test_each_gate_refuses_before_any_source_read(case, monkeypatch, which, gate):
    getattr(case, which)["scientific_gates"][gate] = True
    monkeypatch.setattr(store, "read", lambda *args: pytest.fail("scope must fail before reads"))
    with pytest.raises(ValueError, match="scope/gates"):
        case.verify()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("model_role", "health_model"),
        ("used_source", False),
        ("protocol_sha256", "0" * 64),
        ("scientific_gates", {}),
    ],
)
def test_admission_scope_shape_rejected(case, field, value):
    case.source_admission[field] = value
    with pytest.raises(ValueError, match="scope/gates"):
        case.verify()


@pytest.mark.parametrize(
    "field,value",
    [
        ("participant_values_decoded_before_admission", True),
        ("source_manifest_sha256", "0" * 64),
        ("source_sha256", {"LAB": "0" * 64}),
    ],
)
def test_source_code_coherence_refused(case, field, value):
    case.source_admission[field] = value
    with pytest.raises(ValueError, match="admissions disagree"):
        case.verify()


def test_code_diagnostic_chronology_must_be_false(case):
    case.code_admission["empirical_diagnostic_computed_before_code_admission"] = True
    with pytest.raises(ValueError, match="admissions disagree"):
        case.verify()


@pytest.mark.parametrize("section", ["parameters", "sources", "datasets"])
@pytest.mark.parametrize("action", ["mutate", "delete"])
def test_every_original_scope_uses_full_frozen_inventory(case, section, action):
    preservation = case.protocol["existing_evidence_preservation"]
    inventory = preservation["preserved_" + section[:-1] + "_keys"]
    assert len(inventory) == {"parameters": 235, "sources": 35, "datasets": 41}[section]
    name = inventory[-1]
    records = getattr(case.registry, section)
    if action == "delete":
        del records[name]
    elif section == "parameters":
        records[name].notes = "synthetic prior parameter drift"
    elif section == "sources":
        records[name].citation = "synthetic prior source drift"
    else:
        records[name]["synthetic_drift"] = True
    with pytest.raises(ValueError, match="Prior.*differ"):
        case.verify()


def test_future_unrelated_additions_do_not_change_preserved_scopes(case):
    old = case.registry.content_hash
    parameter = next(iter(case.registry.parameters.values())).model_copy(deep=True)
    parameter.key = "synthetic_future_parameter"
    case.registry.parameters[parameter.key] = parameter
    source = next(iter(case.registry.sources.values())).model_copy(deep=True)
    case.registry.sources["synthetic_future_source"] = source
    case.registry.datasets["synthetic_future_dataset"] = {"model_role": "benchmark_only"}
    _, provenance = case.verify()
    assert provenance["evidence_sha256"] != old


@pytest.mark.parametrize(
    "name",
    [
        "nhanes3_repeat_adult_min_years",
        "nhanes3_repeat_adult_min_months",
        "nhanes3_repeat_mec_age_topcode",
        "nhanes3_repeat_fasting_min_hours",
        "nhanes3_repeat_fpg_positive_min",
    ],
)
def test_all_five_selected_parameter_records_are_bound_not_only_numeric_values(case, name):
    case.registry.parameters[name].notes = "synthetic metadata drift"
    with pytest.raises(ValueError, match="parameter differs from code admission"):
        case.verify()


@pytest.mark.parametrize(
    "name",
    [
        "nhanes3_repeat_adult_layout",
        "nhanes3_repeat_catalog",
        "nhanes3_repeat_lab_dictionary",
        "nhanes3_repeat_lab_layout",
        "nhanes3_repeat_second_lab_dictionary",
        "nhanes3_repeat_second_lab_layout",
        "nhanes3_repeat_readme",
        "nhanes3_repeat_adult_dictionary",
    ],
)
def test_all_eight_documentary_source_records_bound(case, name):
    case.registry.sources[name].citation = "synthetic source metadata drift"
    with pytest.raises(ValueError, match="documentary source differs"):
        case.verify()


@pytest.mark.parametrize(
    "scope", ["registry_parameter_sha256", "registry_documentary_source_sha256"]
)
def test_incomplete_selected_record_pin_inventory_refused(case, scope):
    case.code_admission[scope].pop(next(iter(case.code_admission[scope])))
    with pytest.raises(ValueError, match="admission shape invalid"):
        case.verify()


def test_dataset_metadata_drift_refused(case):
    case.registry.datasets[store.DATASET]["unit"] = "synthetic changed estimand"
    with pytest.raises(ValueError, match="registry definition differs"):
        case.verify()


def test_coherently_resealed_wrong_numeric_profile_still_refused(case):
    name = store.PARAMETERS["fpg_positive_min"]
    case.registry.parameters[name].value = 125
    case.code_admission["registry_parameter_sha256"][name] = store.semantic_sha256(
        case.registry.parameters[name].model_dump(mode="json")
    )
    with pytest.raises(ValueError, match="fixed definition/role"):
        case.verify()


def test_prior_artifact_byte_drift_refused(case):
    case.prior.write_bytes(b"synthetic changed bytes")
    with pytest.raises(ValueError, match="Prior frozen/source artifact"):
        case.verify()


@pytest.mark.parametrize("artifact", ["PROTOCOL_PATH", "DOCUMENTATION_PATH"])
def test_protocol_and_documentary_exact_bytes_are_independently_bound(case, artifact):
    getattr(store, artifact).write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum mismatch"):
        case.verify()


@pytest.mark.parametrize("component", ["LAB", "ADULT", "LABSE"])
def test_each_original_payload_checksum_drift_fails(case, component):
    path = case.source / (component + ".DAT")
    original = path.read_bytes()
    path.write_bytes(b"X" + original[1:])  # Same size; checksum must still reject.
    with pytest.raises(ValueError, match="original bytes differ"):
        case.verify()


def test_manifest_byte_drift_fails_even_without_semantic_change(case):
    manifest = case.source / "manifest.json"
    manifest.write_bytes(manifest.read_bytes() + b" ")
    with pytest.raises(ValueError, match="manifest differs"):
        case.verify()


@pytest.mark.parametrize("change", ["extra_file", "missing_file", "directory"])
def test_unexpected_missing_or_nonfile_store_components_refused(case, change):
    if change == "extra_file":
        (case.source / "unknown.DAT").write_bytes(b"synthetic")
    elif change == "missing_file":
        (case.source / "LAB.DAT").unlink()
    else:
        (case.source / "LAB.DAT").unlink()
        (case.source / "LAB.DAT").mkdir()
    with pytest.raises(ValueError, match="unsafe components"):
        case.verify()


@pytest.mark.parametrize(
    "field,value",
    [
        ("url", "https://example.org/wrong.dat"),
        ("sha256", "0" * 64),
        ("bytes", 1),
        ("original_bytes_preserved", False),
        ("participant_records_decoded", True),
    ],
)
def test_resealed_manifest_receipt_must_still_agree_with_admission(case, field, value):
    case.manifest["sources"]["LAB.DAT"][field] = value
    case.repin_manifest()
    with pytest.raises(ValueError, match="receipt/layout differs"):
        case.verify()


@pytest.mark.parametrize(
    "value,error",
    [
        ("not-a-date", ValueError),
        ("2026-01-01T00:00:00", ValueError),
        (None, AttributeError),
        (123, AttributeError),
    ],
)
def test_source_timestamp_parse_and_timezone_required(case, value, error):
    # Nonstring synthetic receipts require coherent replacement of the pinned
    # manifest. The preserved internal helper raises AttributeError; the public
    # admission entry point owns sanitized refusal and immutable receipt checks.
    case.manifest["sources"]["LAB.DAT"]["retrieved_at"] = value
    case.repin_manifest()
    with pytest.raises(error):
        case.verify()


@pytest.mark.parametrize("target", ["source_directory", "source_file"])
def test_symlink_source_components_refused_when_platform_supports_symlinks(case, target, tmp_path):
    if target == "source_directory":
        link = tmp_path / "linked-source"
        try:
            link.symlink_to(case.source, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"Platform cannot create symlinks: {type(error).__name__}")
        case.source = link
        message = "plain directory"
    else:
        original = case.source / "LAB.DAT"
        archived = tmp_path / "synthetic-LAB.DAT"
        archived.write_bytes(original.read_bytes())
        original.unlink()
        try:
            original.symlink_to(archived)
        except OSError as error:
            pytest.skip(f"Platform cannot create symlinks: {type(error).__name__}")
        message = "unsafe components"
    with pytest.raises(ValueError, match=message):
        case.verify()


@pytest.mark.parametrize("scope", ["source_sha256", "source_size_bytes"])
def test_source_pin_component_inventory_exhaustive(case, scope):
    case.source_admission[scope].pop("LAB")
    if scope == "source_sha256":
        case.code_admission[scope] = deepcopy(case.source_admission[scope])
    with pytest.raises(ValueError, match="component pins invalid"):
        case.verify()


def test_invalid_size_type_not_coerced(case):
    case.source_admission["source_size_bytes"]["LAB"] = True
    with pytest.raises(ValueError, match="receipt/layout differs"):
        case.verify()


@pytest.mark.parametrize(
    "content",
    [
        b'{"duplicate":1,"duplicate":2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b"[]",
        b"\xff",
        b"{",
    ],
)
def test_json_receipts_reject_duplicates_nonfinite_and_wrong_root(content):
    with pytest.raises(ValueError):
        store.read_json(content)
