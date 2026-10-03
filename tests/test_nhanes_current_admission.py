"""Independent admission guards; these synthetic tests never parse participants."""

from pathlib import Path

import pytest

from demeter.data import nhanes_current_admission as admission
from demeter.schema import EvidenceRegistry


@pytest.fixture
def registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml").model_copy(deep=True)


def poison_calculation(monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Unadmitted code reached a v1 calculation function")

    for name in ("verify_protocol", "_registry_contract", "_loaded_code", "_frame", "report"):
        monkeypatch.setattr(admission.store, name, unexpected)
    monkeypatch.setattr(admission.calculation, "assess", unexpected)


def test_independent_source_and_report_admissions_pass(registry):
    admission.verify_admission(registry)


@pytest.mark.parametrize("path", [admission.ADMISSION_PATH, admission.REPORT_PATH])
def test_corrupt_or_missing_admission_refused_before_v1_functions(registry, monkeypatch, path):
    poison_calculation(monkeypatch)
    read = Path.read_bytes

    def changed(target):
        return b"synthetic altered receipt" if target == path else read(target)

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="admission artifact checksum"):
        admission.report(registry)

    def missing(target):
        if target == path:
            raise FileNotFoundError("synthetic missing receipt")
        return read(target)

    monkeypatch.setattr(Path, "read_bytes", missing)
    with pytest.raises(ValueError, match="Unavailable independently admitted"):
        admission.report(registry)


@pytest.mark.parametrize("name", list(admission.IMPLEMENTATIONS))
def test_coherent_code_and_registry_self_repin_refused_before_any_v1_function(
    registry, monkeypatch, name
):
    poison_calculation(monkeypatch)
    changed_bytes = b"# Synthetic changed code, no physical source edit\n"
    import hashlib

    registry.datasets[admission.DATASET]["implementation_sha256"][name] = hashlib.sha256(
        changed_bytes
    ).hexdigest()
    read = Path.read_bytes

    def changed(path):
        return changed_bytes if path.resolve() == Path(name).resolve() else read(path)

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="independent frozen admission"):
        admission.report(registry)


@pytest.mark.parametrize("name", list(admission.IMPLEMENTATIONS))
@pytest.mark.parametrize("location", ["disk", "loaded"])
def test_disk_or_loaded_origin_change_refused_before_any_v1_function(
    registry, monkeypatch, tmp_path, name, location
):
    poison_calculation(monkeypatch)
    module = admission.IMPLEMENTATIONS[name]
    altered = tmp_path / "altered.py"
    altered.write_bytes(b"# Unadmitted source\n")
    if location == "loaded":
        monkeypatch.setattr(module, "__file__", str(altered))
    else:
        digest = admission._digest
        monkeypatch.setattr(
            admission, "_digest", lambda path: "0" * 64 if path == Path(name) else digest(path)
        )
    with pytest.raises(ValueError, match="calculation bytes"):
        admission.report(registry)


@pytest.mark.parametrize("name", list(admission.IMPLEMENTATIONS))
def test_equivalent_loaded_copy_and_unchanged_payload_passthrough(
    registry, monkeypatch, tmp_path, name
):
    module = admission.IMPLEMENTATIONS[name]
    copy = tmp_path / "equivalent.py"
    copy.write_bytes(Path(module.__file__).read_bytes())
    monkeypatch.setattr(module, "__file__", str(copy))
    payload = {"synthetic": "exact object", "source_audit_passed": False}
    calls = []

    def replay(actual_registry, source):
        calls.append((actual_registry, source))
        return payload

    monkeypatch.setattr(admission.store, "report", replay)
    source = tmp_path / "custom-source"
    assert admission.report(registry, source) is payload
    assert calls == [(registry, source)]


@pytest.mark.parametrize("gate", admission.GATES)
@pytest.mark.parametrize("value", [True, 0, None])
def test_all_gates_explicit_false_before_v1_functions(registry, monkeypatch, gate, value):
    poison_calculation(monkeypatch)
    registry.datasets[admission.DATASET][gate] = value
    with pytest.raises(ValueError, match="independent frozen admission"):
        admission.report(registry)


@pytest.mark.parametrize("field", ["source_manifest_sha256", "source_sha256", "protocol_sha256"])
def test_registry_source_and_protocol_repin_refused_before_v1_functions(
    registry, monkeypatch, field
):
    poison_calculation(monkeypatch)
    registry.datasets[admission.DATASET][field] = (
        {"DEMO_L.xpt": "0" * 64} if field == "source_sha256" else "0" * 64
    )
    with pytest.raises(ValueError, match="independent frozen admission"):
        admission.report(registry)
