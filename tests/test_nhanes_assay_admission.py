"""Independent admission checks never parse participant records."""

from pathlib import Path

import pytest

from demeter.data import nhanes_assay_admission as admission
from demeter.data import nhanes_assay_mapping as calculation
from demeter.schema import EvidenceRegistry


@pytest.fixture
def registry():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml").model_copy(deep=True)


def test_original_admission_and_loaded_bytes_pass(registry):
    admission.verify_admission(registry)


@pytest.mark.parametrize("mutation", ["receipt", "registry_pin", "code_and_registry", "loaded_copy"])
def test_changed_admission_refused_before_calculation(registry, monkeypatch, mutation, tmp_path):
    def unexpected(*args, **kwargs):
        pytest.fail("Unadmitted calculation reached report/parser")

    monkeypatch.setattr(calculation, "report", unexpected)
    if mutation in {"registry_pin", "code_and_registry", "loaded_copy"}:
        monkeypatch.setattr(calculation, "_protocol", unexpected)
    original_read = admission.store._read
    if mutation in {"registry_pin", "code_and_registry"}:
        registry.datasets[admission.DATASET]["implementation_sha256"] = {
            calculation.IMPLEMENTATION: "0" * 64
        }
    if mutation in {"receipt", "code_and_registry"}:
        target = admission.ADMISSION_PATH if mutation == "receipt" else Path(calculation.IMPLEMENTATION)

        def changed_read(path, label):
            return b"changed bytes" if path == target else original_read(path, label)

        monkeypatch.setattr(admission.store, "_read", changed_read)
    if mutation == "loaded_copy":
        path = tmp_path / "unadmitted.py"
        path.write_bytes(b"changed implementation")
        monkeypatch.setattr(calculation, "__file__", str(path))
    with pytest.raises(ValueError, match="admission"):
        admission.report(registry)


def test_byte_equivalent_loaded_copy_and_exact_payload_passthrough(registry, monkeypatch, tmp_path):
    path = tmp_path / "equivalent.py"
    path.write_bytes(Path(calculation.__file__).read_bytes())
    monkeypatch.setattr(calculation, "__file__", str(path))
    expected = {"frozen": "unchanged", "gates": False}
    calls = []

    def unchanged_report(actual_registry, source):
        calls.append((actual_registry, source))
        return expected

    monkeypatch.setattr(calculation, "report", unchanged_report)
    source = tmp_path / "source"
    assert admission.report(registry, source) is expected
    assert calls == [(registry, source)]
