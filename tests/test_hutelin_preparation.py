import json
import pytest
from decimal import Decimal
import math
from pathlib import Path
from demeter.data import hutelin_preparation
from demeter.schema import EvidenceRegistry
from demeter.data.hutelin_preparation import classify, diagnostic, replacement_compatible

REPLACEMENT = Decimal.from_float(3 / math.sqrt(2))
HALF = Decimal("0.5")


def row(a, b, c):
    return {"insulin": a, "insulin_w0": b, "insulin_impute": c, "id": "PRIVATE-ID"}


@pytest.mark.parametrize(
    "record,category",
    [
        (row("NA", "0", "2.12"), "native_missing_zero_and_replacement_compatible"),
        (row("NA", "0", "2.120"), "native_missing_other_prepared_pattern"),
        (row("NA", "NA", "NA"), "all_insulin_cells_missing"),
        (row("7.5", "7.5", "7.5"), "native_present_prepared_equal"),
        (row("7.5", "NA", "7.5"), "native_present_prepared_missing"),
        (row("7.5", "7.5", "9"), "native_present_prepared_discrepant"),
        (row("<3", "0", "2.12"), "unclassified_token"),
    ],
)
def test_independent_pattern_examples(record, category):
    assert classify(record, REPLACEMENT, HALF) == category


def test_storage_precision_hypothesis_is_explicit_not_a_widened_tolerance():
    assert replacement_compatible("2.12", REPLACEMENT, HALF)
    assert replacement_compatible("2.121320344", REPLACEMENT, HALF)
    assert not replacement_compatible("2.120", REPLACEMENT, HALF)
    assert not replacement_compatible("0", REPLACEMENT, HALF)


def test_all_records_including_duplicates_and_unknowns_are_accounted_without_identifiers():
    records = [row("NA", "0", "2.12"), row("NA", "0", "2.12"), row("Inf", "NA", "NA")]
    result = diagnostic(records, REPLACEMENT, HALF)
    assert result["records"] == 3
    assert sum(result["exclusive_pattern_counts"].values()) == 3
    assert result["exclusive_pattern_counts"]["native_missing_zero_and_replacement_compatible"] == 2
    assert result["exclusive_pattern_counts"]["unclassified_token"] == 1
    encoded = json.dumps(result)
    assert "PRIVATE-ID" not in encoded and "2.12" not in encoded


@pytest.mark.parametrize("token", ["1_000", "NaN", "Inf", "1e900", "1e-301", "1" * 65])
def test_outside_numeric_policy_retained_as_unknown(token):
    assert classify(row(token, "0", "2.12"), REPLACEMENT, HALF) == "unclassified_token"


def test_decimal_context_does_not_change_compatibility_result():
    from decimal import localcontext

    with localcontext() as context:
        context.prec = 6
        assert replacement_compatible("2.1213203435596424", REPLACEMENT, HALF)


def test_changed_protocol_fails_before_source_access(tmp_path):
    path = tmp_path / "docs/validation/hutelin2026-preparation-pattern-protocol-v1.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    registry = EvidenceRegistry.from_yaml(
        Path(__file__).resolve().parents[1] / "evidence/parameters.yaml"
    )
    with pytest.raises(ValueError, match="protocol differs"):
        hutelin_preparation.audit_preparation(tmp_path / "absent", tmp_path, registry)


def test_changed_registry_scope_fails_before_source_access():
    root = Path(__file__).resolve().parents[1]
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    registry.parameters["hutelin2026_insulin_reported_loq"].value = 9
    with pytest.raises(ValueError, match="registry definitions differ"):
        hutelin_preparation.audit_preparation(root / "does-not-exist", root, registry)


def test_changed_method_document_fails_before_record_interpretation(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    registry = EvidenceRegistry.from_yaml(root / "evidence/parameters.yaml")
    name = registry.sources["hutelin2026_preparation_supplement"].raw_filename
    (tmp_path / name).write_bytes(b"different document")
    monkeypatch.setattr(
        hutelin_preparation,
        "audit_hutelin_preflight",
        lambda *args: {
            "contract_sha256": "8d7caec48404816c0382db08052c5f5a4f55e252e5d0b686d8da7d899ab3d2bf"
        },
    )

    def forbidden(*args):
        raise AssertionError("record interpretation occurred before documentary identity")

    monkeypatch.setattr(hutelin_preparation, "diagnostic", forbidden)
    with pytest.raises(ValueError, match="method document mismatch"):
        hutelin_preparation.audit_preparation(tmp_path, root, registry)
