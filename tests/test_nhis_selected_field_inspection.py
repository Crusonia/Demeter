"""Synthetic selected-field inspection only; original delivery never invoked."""

from dataclasses import FrozenInstanceError
import hashlib
from itertools import product
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from demeter.data import nhis_selected_field_inspection as inspection

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / inspection._CONTRACT).read_bytes())
AMENDMENT = json.loads((ROOT / inspection._AMENDMENT).read_bytes())

# Independent producer INPUT-column fixture: never use decoder selector internals.
COLUMNS = {
    "RECTYPE": (1, 2),
    "SRVY_YR": (3, 6),
    "HHX": (7, 13),
    "WTFA_A": (14, 23),
    "PSTRAT": (26, 28),
    "PPSU": (29, 34),
    "PROXYFLAG_A": (36, 36),
    "HHSTAT_A": (38, 38),
    "SEX_A": (46, 46),
    "AGEP_A": (48, 49),
    "DIBEV_A": (176, 176),
    "DIBTYPE_A": (187, 187),
}


def record(**changes):
    values = {
        "RECTYPE": "10",
        "SRVY_YR": "2025",
        "HHX": "SECRET1",
        "WTFA_A": "123.125",
        "PSTRAT": "3",
        "PPSU": "27",
        "PROXYFLAG_A": "2",
        "HHSTAT_A": "1",
        "SEX_A": "2",
        "AGEP_A": "42",
        "DIBEV_A": "1",
        "DIBTYPE_A": "2",
    } | changes
    payload = bytearray(b" " * 685)
    for name, value in values.items():
        start, end = COLUMNS[name]
        token = value.ljust(end - start + 1).encode("ascii")
        assert len(token) == end - start + 1
        payload[start - 1 : end] = token
    payload[300:321] = b"PRIVATE-OMITTED!!!!!!"
    assert len(payload) == 685
    return bytes(payload) + b"\r\n"


def run_synthetic(monkeypatch, content, *, expected=None):
    """Patch source delivery only; admission/code verification and decoder are real."""
    monkeypatch.setattr(
        inspection, "_REFERENCE_RECORDS", len(content) // 687 if expected is None else expected
    )
    calls = []

    def delivery(archive, native, *, root):
        calls.append((archive, native, root))
        return inspection.guard.PrivateVerifiedDelivery(content)

    monkeypatch.setattr(inspection.guard, "verify_delivery", delivery)
    value = inspection.inspect_selected_fields(
        Path("synthetic.zip"), Path("synthetic.dat"), root=ROOT
    )
    assert calls == [(Path("synthetic.zip"), Path("synthetic.dat"), ROOT)]
    return value


def category(diagnosis, kind):
    diagnosis = "" if diagnosis in (" ", ".") else diagnosis
    kind = "" if kind in (" ", ".") else kind
    if diagnosis == "1":
        return {"1": "reported_type1", "2": "reported_type2", "3": "reported_other_diabetes"}.get(
            kind, "reported_diabetes_type_unknown"
        )
    if kind:
        return "inconsistent_type_universe"
    return "no_reported_diabetes" if diagnosis == "2" else "diagnosis_unknown"


def test_all_literal_answer_and_source_universe_combinations(monkeypatch):
    combinations = list(product("1 .", "12789 .", "123789 ."))
    content = b"".join(
        record(HHSTAT_A=status, DIBEV_A=diagnosis, DIBTYPE_A=kind)
        for status, diagnosis, kind in combinations
    )
    value = run_synthetic(monkeypatch, content)
    assert value.sanitized_failure is None
    private = value.private_diagnostics
    schema = CONTRACT["fixed_private_success_schema"]
    assert set(private) == set(schema["top_level_keys"])
    actual = private["diagnostics"]
    expected = {
        name: dict.fromkeys(labels, 0) for name, labels in schema["diagnostic_marginals"].items()
    }
    for status, diagnosis, kind in combinations:
        expected["reported_category"][category(diagnosis, kind)] += 1
        universe = (
            "unresolved"
            if status != "1" or diagnosis in (" ", ".")
            else "known_in_universe"
            if diagnosis == "1"
            else "known_outside_universe"
        )
        expected["type_universe"][universe] += 1
        prefix = {
            "known_in_universe": "in",
            "known_outside_universe": "outside",
            "unresolved": "unresolved",
        }[universe]
        presence = "blank_or_period" if kind in (" ", ".") else "recorded_code"
        expected["private_type_universe_and_recorded_response_presence"][
            f"{prefix}_universe_{presence}"
        ] += 1
        for field, token, mapping in (
            ("diagnosis_response", diagnosis, {"1": "yes", "2": "no"}),
            ("type_response", kind, {"1": "type1", "2": "type2", "3": "other"}),
        ):
            role = (
                {
                    "7": "refused",
                    "8": "not_ascertained",
                    "9": "dont_know",
                    " ": "native_blank",
                    ".": "reader_single_period",
                }
                | mapping
            )[token]
            expected[field][role] += 1
    for field in (
        "reported_category",
        "type_universe",
        "diagnosis_response",
        "type_response",
        "private_type_universe_and_recorded_response_presence",
    ):
        assert actual[field] == expected[field]
    n = len(combinations)
    assert all(sum(actual[field].values()) == n for field in schema["diagnostic_marginals"])
    assert set(actual) == set(schema["diagnostic_object_exact_keys"])
    assert private["record_accounting"] == {
        "reference_delivery_records": n,
        "decoded_records": n,
        "classified_records": n,
        "all_records_retained": True,
        "complete_category_partition_conserved": True,
        "every_declared_marginal_conserved": True,
    }
    assert content == b"".join(
        record(HHSTAT_A=s, DIBEV_A=d, DIBTYPE_A=t) for s, d, t in combinations
    )


@pytest.mark.parametrize("diagnosis", ["7", "8", "9"])
def test_clinical_unknown_is_known_outside_literal_source_predicate(monkeypatch, diagnosis):
    private = run_synthetic(
        monkeypatch, record(DIBEV_A=diagnosis, DIBTYPE_A=" ")
    ).private_diagnostics
    assert private["diagnostics"]["reported_category"]["diagnosis_unknown"] == 1
    assert private["diagnostics"]["type_universe"]["known_outside_universe"] == 1


def test_missing_sample_status_preserves_type_facet_without_universe_claim(monkeypatch):
    data = run_synthetic(monkeypatch, record(HHSTAT_A=".")).private_diagnostics["diagnostics"]
    assert data["reported_category"]["reported_type2"] == 1
    assert data["type_universe"]["unresolved"] == 1
    assert data["sample_adult_status"]["missing"] == 1


def test_unknown_demographic_proxy_weight_design_and_support_retained(monkeypatch):
    rows = [
        record(AGEP_A="85", SEX_A="1", PROXYFLAG_A="1", WTFA_A="0", PSTRAT="-1", PPSU="0"),
        record(AGEP_A="97", SEX_A="7", PROXYFLAG_A="7", WTFA_A="-2", PSTRAT="-1", PPSU="2"),
        record(AGEP_A="98", SEX_A="8", PROXYFLAG_A="8", WTFA_A=".", PSTRAT="0", PPSU="0"),
        record(AGEP_A="99", SEX_A="9", PROXYFLAG_A="9", WTFA_A=" ", PSTRAT=".", PPSU="0"),
        record(AGEP_A=".", SEX_A=".", PROXYFLAG_A=".", PSTRAT="0", PPSU=" "),
        record(AGEP_A=" ", SEX_A=" ", PROXYFLAG_A=" ", PSTRAT=" ", PPSU="."),
    ]
    data = run_synthetic(monkeypatch, b"".join(rows)).private_diagnostics["diagnostics"]
    assert data["age_role"] == {
        "exact_age": 0,
        "85_plus": 1,
        "refused": 1,
        "not_ascertained": 1,
        "dont_know": 1,
        "missing": 2,
    }
    assert data["weight_sign"] == {"positive": 2, "zero": 1, "negative": 1, "missing": 2}
    assert data["stratum_sign"] == {"positive": 0, "zero": 2, "negative": 2, "missing": 2}
    assert data["psu_sign"] == {"positive": 1, "zero": 3, "negative": 0, "missing": 2}
    assert data["design_presence"] == {
        "both_present": 3,
        "stratum_missing_only": 1,
        "psu_missing_only": 1,
        "both_missing": 1,
    }
    assert data["design_support"] == {
        "records_with_both_design_fields": 3,
        "distinct_strata_among_both_present_records": 2,
        "distinct_stratum_psu_pairs_among_both_present_records": 3,
        "strata_with_one_recorded_psu_label": 1,
        "strata_with_multiple_recorded_psu_labels": 1,
    }
    assert data["selected_field_missingness"]["WTFA_A"] == {
        "native_blank": 1,
        "reader_single_period": 1,
    }
    assert data["selected_field_missingness"]["AGEP_A"] == {
        "native_blank": 1,
        "reader_single_period": 1,
    }
    assert data["sex_role"] == {
        "male": 1,
        "female": 0,
        "refused": 1,
        "not_ascertained": 1,
        "dont_know": 1,
        "missing": 2,
    }
    assert data["proxy_role"] == {
        "proxy_used": 1,
        "proxy_not_used": 0,
        "refused": 1,
        "not_ascertained": 1,
        "dont_know": 1,
        "missing": 2,
    }


def test_key_alias_duplicates_missing_and_overlapping_fields_are_not_people(monkeypatch):
    content = b"".join(
        [
            record(HHX=" KEY"),
            record(HHX="KEY"),
            record(HHX="KEY"),
            record(HHX=".", DIBEV_A=".", DIBTYPE_A="."),
        ]
    )
    data = run_synthetic(monkeypatch, content).private_diagnostics["diagnostics"]
    assert data["key_diagnostics"] == {
        "missing_household_key_records": 1,
        "duplicate_interpreted_household_key_records": 2,
        "household_keys_with_lexical_aliases": 1,
    }
    assert sum(x["reader_single_period"] for x in data["selected_field_missingness"].values()) == 3
    assert sum(data["reported_category"].values()) == 4
    assert "KEY" not in json.dumps(data)


def test_empty_and_no_both_present_support(monkeypatch):
    for content in (b"", record(PSTRAT=".", PPSU=".")):
        private = run_synthetic(monkeypatch, content).private_diagnostics
        assert set(private["diagnostics"]["design_support"].values()) == {0}
        assert private["record_accounting"]["all_records_retained"] is True


def test_order_invariance_and_no_row_or_private_tokens_retained(monkeypatch):
    rows = [record(), record(DIBEV_A="9", DIBTYPE_A=" "), record(HHX=".", WTFA_A="-1")]
    first = run_synthetic(monkeypatch, b"".join(rows))
    second = run_synthetic(monkeypatch, b"".join(reversed(rows)))
    assert first.private_diagnostics == second.private_diagnostics
    assert repr(first) == "<PrivateNHISSelectedFieldInspection>"
    for token in ("SECRET1", "UNSELECTED", "123.125"):
        assert token not in repr(first) + json.dumps(first.private_diagnostics) + json.dumps(
            first.technical_envelope
        )
    assert not hasattr(first, "records") and not hasattr(first, "native_bytes")
    assert not hasattr(first, "exception") and not hasattr(first, "write")
    with pytest.raises(FrozenInstanceError):
        first._private_json = "changed"
    with pytest.raises(TypeError):
        json.dumps(first)


def test_fresh_fixed_public_private_and_failure_dictionaries(monkeypatch):
    value = run_synthetic(monkeypatch, record())
    original = value.private_diagnostics
    original["diagnostics"]["reported_category"].clear()
    assert value.private_diagnostics["diagnostics"]["reported_category"]["reported_type2"] == 1
    public = value.technical_envelope
    assert set(public) == set(CONTRACT["fixed_public_technical_schema"]["top_level_keys"])
    assert public["diagnostic_counts_released"] is False
    assert all(flag is False for flag in public["scientific_gates"].values())
    assert set(public["provenance"]) == set(AMENDMENT["current_provenance_exact_keys"])
    assert public["provenance"]["selected_field_contract_sha256"] == inspection._AMENDMENT_SHA
    assert all(len(sha) == 64 for sha in public["provenance"].values())
    assert "diagnostics" not in public and "design_support" not in public
    public["scientific_gates"]["clinical_fit_allowed"] = True
    assert value.technical_envelope["scientific_gates"]["clinical_fit_allowed"] is False


@pytest.mark.parametrize(
    "stage", ["delivery_verification", "private_decoding", "aggregate_projection"]
)
def test_failure_chronology_without_dynamic_context(monkeypatch, stage):
    def fail(*args, **kwargs):
        raise RuntimeError("SECRET1 PRIVATE-ERROR /private/path diagnosis=1")

    monkeypatch.setattr(inspection, "_REFERENCE_RECORDS", 1)
    monkeypatch.setattr(
        inspection.guard,
        "verify_delivery",
        lambda *args, **kwargs: inspection.guard.PrivateVerifiedDelivery(record()),
    )
    target = {
        "delivery_verification": (inspection.guard, "verify_delivery"),
        "private_decoding": (inspection.decoder, "decode_native_records"),
        "aggregate_projection": (inspection, "_project"),
    }[stage]
    monkeypatch.setattr(*target, fail)
    result = inspection.inspect_selected_fields(
        Path("synthetic.zip"), Path("synthetic.dat"), root=ROOT
    )
    failure = result.sanitized_failure
    assert set(failure) == set(CONTRACT["sanitized_failure_schema"]["top_level_keys"])
    assert failure["stage"] == stage
    assert failure["source_delivery_verified"] is (stage != "delivery_verification")
    assert (
        failure["selected_values_projected"]
        is {"delivery_verification": False, "private_decoding": None, "aggregate_projection": True}[
            stage
        ]
    )
    assert (
        failure["selected_values_projection_status"]
        == {
            "delivery_verification": "not_attempted",
            "private_decoding": "possibly_partial",
            "aggregate_projection": "completed",
        }[stage]
    )
    assert result.private_diagnostics is None
    assert result.technical_envelope["all_records_retained"] is None
    assert all(flag is False for flag in failure["scientific_gates"].values())
    assert "PRIVATE-ERROR" not in json.dumps(failure) + json.dumps(result.technical_envelope)
    failure["stage"] = "tampered"
    assert result.sanitized_failure["stage"] == stage


def test_real_partial_decoder_failure_and_post_decode_count_mismatch(monkeypatch):
    value = run_synthetic(monkeypatch, record() + record(DIBEV_A="6"))
    assert value.sanitized_failure["selected_values_projected"] is None
    assert value.sanitized_failure["selected_values_projection_status"] == "possibly_partial"
    value = run_synthetic(monkeypatch, record(), expected=2)
    assert value.sanitized_failure["stage"] == "aggregate_projection"
    assert value.sanitized_failure["selected_values_projected"] is True
    assert value.private_diagnostics is None


@pytest.mark.parametrize("delivery", [object(), SimpleNamespace(native_bytes="PRIVATE")])
def test_malformed_delivery_does_not_claim_decoder_attempt(monkeypatch, delivery):
    monkeypatch.setattr(inspection.guard, "verify_delivery", lambda *a, **k: delivery)

    def forbidden(*args):
        pytest.fail("No decoder invocation before immutable bytes are available")

    monkeypatch.setattr(inspection.decoder, "decode_native_records", forbidden)
    value = inspection.inspect_selected_fields(
        Path("synthetic.zip"), Path("synthetic.dat"), root=ROOT
    )
    assert value.sanitized_failure["source_delivery_verified"] is True
    assert value.sanitized_failure["selected_values_projected"] is False
    assert value.sanitized_failure["selected_values_projection_status"] == "not_attempted"


def test_raising_delivery_accessor_is_still_before_decoder(monkeypatch):
    class BrokenDelivery:
        @property
        def native_bytes(self):
            raise RuntimeError("PRIVATE-ACCESSOR-FAILURE")

    monkeypatch.setattr(inspection.guard, "verify_delivery", lambda *a, **k: BrokenDelivery())

    def forbidden(*args):
        pytest.fail("Decoder must not run when argument retrieval failed")

    monkeypatch.setattr(inspection.decoder, "decode_native_records", forbidden)
    value = inspection.inspect_selected_fields(
        Path("synthetic.zip"), Path("synthetic.dat"), root=ROOT
    )
    assert value.sanitized_failure["source_delivery_verified"] is True
    assert value.sanitized_failure["selected_values_projected"] is False
    assert value.sanitized_failure["selected_values_projection_status"] == "not_attempted"
    assert "PRIVATE-ACCESSOR" not in json.dumps(value.sanitized_failure)


def test_production_reference_full_synthetic_flow_and_small_refusal(monkeypatch):
    # No reference override: the callable public path always requires frozen24215.
    content = record() * 24215
    monkeypatch.setattr(
        inspection.guard,
        "verify_delivery",
        lambda *a, **k: inspection.guard.PrivateVerifiedDelivery(content),
    )
    value = inspection.inspect_selected_fields(
        Path("synthetic.zip"), Path("synthetic.dat"), root=ROOT
    )
    assert value.sanitized_failure is None
    assert value.technical_envelope["reference_delivery_records"] == 24215
    assert value.private_diagnostics["diagnostics"]["reported_category"]["reported_type2"] == 24215
    for small in (record(), b""):
        monkeypatch.setattr(
            inspection.guard,
            "verify_delivery",
            lambda *a, content=small, **k: inspection.guard.PrivateVerifiedDelivery(content),
        )
        value = inspection.inspect_selected_fields(
            Path("synthetic.zip"), Path("synthetic.dat"), root=ROOT
        )
        assert value.sanitized_failure["stage"] == "aggregate_projection"
        assert value.sanitized_failure["selected_values_projected"] is True
        assert value.technical_envelope["reference_delivery_records"] == 24215
        assert value.private_diagnostics is None


@pytest.fixture
def isolated_pins(tmp_path, monkeypatch):
    for name in inspection._DOCUMENTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    modules = {}
    for name, (_, sha) in inspection._IMPLEMENTATIONS.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
        modules[name] = (SimpleNamespace(__file__=str(path)), sha)
    monkeypatch.setattr(inspection, "_IMPLEMENTATIONS", modules)

    def forbidden(*args, **kwargs):
        pytest.fail("No helper may run after failed independent pins")

    monkeypatch.setattr(inspection.guard, "verify_delivery", forbidden)
    monkeypatch.setattr(inspection.decoder, "decode_native_records", forbidden)
    return tmp_path


@pytest.mark.parametrize("name", list(inspection._DOCUMENTS) + list(inspection._IMPLEMENTATIONS))
def test_document_or_code_drift_refuses_before_helpers(isolated_pins, name):
    path = isolated_pins / name
    path.write_bytes(path.read_bytes() + b"\n")
    value = inspection.inspect_selected_fields(
        Path("absent.zip"), Path("absent.dat"), root=isolated_pins
    )
    assert value.sanitized_failure["stage"] == "independent_admission"
    assert value.sanitized_failure["selected_values_projected"] is False


def test_foreign_loaded_copy_even_when_bytes_equal_refuses(isolated_pins):
    name = next(iter(inspection._IMPLEMENTATIONS))
    module, _ = inspection._IMPLEMENTATIONS[name]
    foreign = isolated_pins / "foreign.py"
    foreign.write_bytes((isolated_pins / name).read_bytes())
    module.__file__ = str(foreign)
    value = inspection.inspect_selected_fields(
        Path("absent.zip"), Path("absent.dat"), root=isolated_pins
    )
    assert value.sanitized_failure["stage"] == "independent_admission"


def test_mutable_metadata_self_repin_cannot_override_literal_contract(isolated_pins):
    name = next(iter(inspection._IMPLEMENTATIONS))
    path = isolated_pins / name
    path.write_bytes(path.read_bytes() + b"\n# coherent altered source\n")
    config = json.loads((isolated_pins / inspection._CONTRACT).read_bytes())
    config["existing_invoked_code_pins"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (isolated_pins / inspection._CONTRACT).write_text(json.dumps(config), encoding="utf-8")
    value = inspection.inspect_selected_fields(
        Path("absent.zip"), Path("absent.dat"), root=isolated_pins
    )
    assert value.sanitized_failure["stage"] == "independent_admission"


def test_wrong_path_type_failures_do_not_invoke_helper(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid path must fail first")

    monkeypatch.setattr(inspection.guard, "verify_delivery", forbidden)
    value = inspection.inspect_selected_fields("SECRET/path", Path("absent.dat"), root=ROOT)
    assert value.sanitized_failure["stage"] == "independent_admission"
    assert "SECRET" not in json.dumps(value.technical_envelope)


def test_no_survey_model_network_or_file_write(monkeypatch):
    from demeter.data import nhis_survey_witness, survey_joint
    import socket

    def forbidden(*args, **kwargs):
        pytest.fail("inspection must not estimate, acquire or write")

    monkeypatch.setattr(nhis_survey_witness, "assess", forbidden)
    monkeypatch.setattr(survey_joint, "joint_proportions", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    assert run_synthetic(monkeypatch, record()).sanitized_failure is None
