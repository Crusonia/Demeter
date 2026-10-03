"""Independent receipt/code checks; synthetic spies never decode participants."""

from pathlib import Path

import pytest

from demeter.data import nhanes3_repeat_admission as admission


def poison(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Unadmitted helper or diagnostic invoked")

    monkeypatch.setattr(admission.store, "verify", fail)
    monkeypatch.setattr(admission.calculation, "analyze", fail)
    monkeypatch.setattr(admission.calculation, "public_result", fail)


def test_actual_independent_receipts_and_code_verify_without_calculation():
    source, code = admission.verify_admission()
    assert source["participant_values_decoded_before_admission"] is False
    assert code["empirical_diagnostic_computed_before_code_admission"] is False


@pytest.mark.parametrize("path", [admission.SOURCE_ADMISSION, admission.CODE_ADMISSION])
@pytest.mark.parametrize("missing", [False, True])
def test_receipt_mutation_or_loss_refused_before_helpers(monkeypatch, path, missing):
    poison(monkeypatch)
    read = Path.read_bytes

    def changed(target):
        if target == path:
            if missing:
                raise FileNotFoundError("synthetic missing")
            return b'{"synthetic":"self-repinned"}'
        return read(target)

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="admission checksum|Unavailable independently"):
        admission.report(None)


@pytest.mark.parametrize("name", list(admission.IMPLEMENTATIONS))
@pytest.mark.parametrize("loaded", [False, True])
def test_changed_disk_or_loaded_code_refused_before_helpers(monkeypatch, tmp_path, name, loaded):
    poison(monkeypatch)
    if loaded:
        target = tmp_path / "different.py"
        target.write_bytes(b"# changed synthetic implementation\n")
        monkeypatch.setattr(admission.IMPLEMENTATIONS[name], "__file__", str(target))
    else:
        read = Path.read_bytes

        def changed(target):
            return b"# changed synthetic implementation\n" if target == Path(name) else read(target)

        monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="implementation differs"):
        admission.report(None)


@pytest.mark.parametrize("name", list(admission.IMPLEMENTATIONS))
def test_equivalent_loaded_copy_and_coarse_only_passthrough(monkeypatch, tmp_path, name):
    module = admission.IMPLEMENTATIONS[name]
    equivalent = tmp_path / "same.py"
    equivalent.write_bytes(Path(module.__file__).read_bytes())
    monkeypatch.setattr(module, "__file__", str(equivalent))
    provenance = {"synthetic": "identity"}
    content = {"synthetic": b"no participant records"}
    private = {"synthetic": "private ledger"}
    coarse = {"synthetic": "coarse only"}
    calls = []

    def verify(registry, source_admission, code_admission, source):
        calls.append("verified")
        return content, provenance

    def analyze(actual, definition):
        assert calls == ["verified"] and actual is content
        assert definition is admission.store.DEFINITION
        calls.append("diagnostic")
        return private

    def project(actual, *, provenance, source_audit_passed):
        assert actual is private and source_audit_passed is True
        assert provenance["source_admission_sha256"] == admission.SOURCE_ADMISSION_SHA256
        assert provenance["code_admission_sha256"] == admission.CODE_ADMISSION_SHA256
        calls.append("projection")
        return coarse

    monkeypatch.setattr(admission.store, "verify", verify)
    monkeypatch.setattr(admission.calculation, "analyze", analyze)
    monkeypatch.setattr(admission.calculation, "public_result", project)
    assert admission.report(None) is coarse
    assert calls == ["verified", "diagnostic", "projection"]


@pytest.mark.parametrize("name", list(admission.IMPLEMENTATIONS))
def test_unavailable_loaded_origin_refused_before_helpers(monkeypatch, name):
    poison(monkeypatch)
    monkeypatch.setattr(admission.IMPLEMENTATIONS[name], "__file__", None)
    with pytest.raises(ValueError, match="loaded implementation unavailable"):
        admission.report(None)


@pytest.mark.parametrize("error", [AttributeError, KeyError, TypeError])
def test_malformed_internal_contract_has_sanitized_public_error(monkeypatch, error):
    def malformed(*args, **kwargs):
        raise error("synthetic private detail")

    monkeypatch.setattr(admission.store, "verify", malformed)
    with pytest.raises(ValueError, match="Invalid admitted") as exc:
        admission.report(None)
    assert "private detail" not in str(exc.value)
