"""Synthetic fixed-column fixtures only; no participant source or field reads."""

from dataclasses import FrozenInstanceError
from decimal import Decimal
from itertools import product
import json

import pytest

from demeter.data.nhis_diagnosis_labels import CATEGORIES, classify_reported_diabetes
from demeter.data.nhis_native_records import decode_native_records


# An independent literal fixed-column fixture, not the decoder's selector map.
_COLUMNS = {
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
    tokens = {
        "RECTYPE": "10",
        "SRVY_YR": "2025",
        "HHX": "K000001",
        "WTFA_A": "  1234.125",
        "PSTRAT": "003",
        "PPSU": "000027",
        "PROXYFLAG_A": "2",
        "HHSTAT_A": "1",
        "SEX_A": "2",
        "AGEP_A": "42",
        "DIBEV_A": "1",
        "DIBTYPE_A": "2",
    } | changes
    payload = bytearray(b" " * 685)
    for name, token in tokens.items():
        start, end = _COLUMNS[name]
        encoded = token.encode("ascii")
        assert len(encoded) == end - start + 1
        payload[start - 1 : end] = encoded
    # Unselected printable text must not be projected or included in a record.
    payload[300:317] = b"PRIVATE-OMITTED!!"
    assert len(payload) == 685
    return bytes(payload) + b"\r\n"


def test_independent_literal_column_oracle_and_distinct_design_fields():
    content = record()
    batch = decode_native_records(content)
    value = batch.records[0]
    assert value.household_key == "K000001"
    assert value.sample_adult_status == "sample_adult"
    assert value.weight == Decimal("1234.125")
    assert value.stratum == 3 and value.psu == 27
    assert value.age_role == "exact_age"
    assert value.exact_age_years == value.age_lower_bound_years == 42
    assert value.sex_role == "female" and value.proxy_role == "proxy_not_used"
    assert value.reported_category == "reported_type2"
    assert value.reader_missing_roles == ()
    expected = tuple(
        (name, content[start - 1 : end].decode("ascii")) for name, (start, end) in _COLUMNS.items()
    )
    assert value.native_tokens == expected
    assert "PRIVATE-OMITTED" not in repr(value.native_tokens)
    assert set(dict(value.native_tokens)) == set(_COLUMNS)
    assert content == record()  # Immutable input was not repaired or recoded.


def expected_category(diagnosis, kind):
    # Independent documented answer truth table; not an adapter call.
    diagnosis = "" if diagnosis in (" ", ".") else diagnosis
    kind = "" if kind in (" ", ".") else kind
    if diagnosis == "1":
        return {"1": "reported_type1", "2": "reported_type2", "3": "reported_other_diabetes"}.get(
            kind, "reported_diabetes_type_unknown"
        )
    if kind:
        return "inconsistent_type_universe"
    return "no_reported_diabetes" if diagnosis == "2" else "diagnosis_unknown"


@pytest.mark.parametrize("diagnosis,kind", list(product("12789 .", "123789 .")))
def test_all_documented_answer_codes_and_reader_missing_conserve(diagnosis, kind):
    batch = decode_native_records(record(DIBEV_A=diagnosis, DIBTYPE_A=kind))
    category = expected_category(diagnosis, kind)
    assert batch.records[0].reported_category == category
    ledger = batch.private_ledger
    assert ledger["category_counts"] == {name: int(name == category) for name in CATEGORIES}
    assert ledger["total_records"] == 1 and ledger["ledger_conserved"] is True
    tokens = dict(batch.records[0].native_tokens)
    assert tokens["DIBEV_A"] == diagnosis and tokens["DIBTYPE_A"] == kind


def test_period_is_reader_missing_not_new_classifier_answer_code():
    with pytest.raises(ValueError):
        classify_reported_diabetes(".", " ")
    blank = decode_native_records(record(DIBEV_A=" ", DIBTYPE_A=" ")).records[0]
    period = decode_native_records(record(DIBEV_A=".", DIBTYPE_A=".")).records[0]
    assert blank.reported_category == period.reported_category == "diagnosis_unknown"
    assert dict(blank.reader_missing_roles) == {"DIBEV_A": "blank", "DIBTYPE_A": "blank"}
    assert dict(period.reader_missing_roles) == {
        "DIBEV_A": "single_period",
        "DIBTYPE_A": "single_period",
    }


@pytest.mark.parametrize("code", ["18", "84", "85", "97", "98", "99", "  ", " ."])
def test_age_topcode_and_unknowns_are_not_point_ages(code):
    value = decode_native_records(record(AGEP_A=code)).records[0]
    if code in ("18", "84"):
        assert value.exact_age_years == value.age_lower_bound_years == int(code)
        assert value.age_role == "exact_age"
    elif code == "85":
        assert value.exact_age_years is None and value.age_lower_bound_years == 85
        assert value.age_role == "85_plus"
    else:
        assert value.exact_age_years is value.age_lower_bound_years is None
        assert value.age_role == {"97": "refused", "98": "not_ascertained", "99": "dont_know"}.get(
            code, "missing"
        )
    assert dict(value.native_tokens)["AGEP_A"] == code


@pytest.mark.parametrize("field", ["SEX_A", "PROXYFLAG_A"])
@pytest.mark.parametrize(
    "code,expected",
    [
        ("7", "refused"),
        ("8", "not_ascertained"),
        ("9", "dont_know"),
        (" ", "missing"),
        (".", "missing"),
    ],
)
def test_unknown_demographic_and_proxy_roles_stay_distinct(field, code, expected):
    value = decode_native_records(record(**{field: code})).records[0]
    assert getattr(value, "sex_role" if field == "SEX_A" else "proxy_role") == expected
    assert dict(value.native_tokens)[field] == code


@pytest.mark.parametrize("code", [" ", "."])
def test_positive_answer_does_not_resolve_missing_adult_universe(code):
    batch = decode_native_records(record(HHSTAT_A=code))
    assert batch.records[0].reported_category == "reported_type2"
    assert batch.records[0].sample_adult_status == "missing"
    assert batch.private_ledger["sample_adult_roles"] == {"sample_adult": 0, "missing": 1}


def test_literal_male_and_proxy_used_are_retained_without_exclusion():
    batch = decode_native_records(record(SEX_A="1", PROXYFLAG_A="1"))
    assert batch.records[0].sex_role == "male"
    assert batch.records[0].proxy_role == "proxy_used"
    assert batch.private_ledger["total_records"] == 1


def test_complete_mixed_answer_partition_retains_all_rows_and_zero_groups():
    pairs = [("2", " "), ("1", "1"), ("1", "2"), ("1", "3"), ("1", "9"), ("9", " "), ("2", "2")]
    batch = decode_native_records(b"".join(record(DIBEV_A=d, DIBTYPE_A=t) for d, t in pairs))
    assert batch.private_ledger["category_counts"] == dict.fromkeys(CATEGORIES, 1)
    assert batch.private_ledger["total_records"] == 7
    assert batch.private_ledger["ledger_conserved"] is True
    assert batch.private_ledger["duplicate_interpreted_household_key_records"] == 6


@pytest.mark.parametrize(
    "token,expected",
    [
        ("      1234", Decimal("1234")),
        ("    1234.5", Decimal("1234.5")),
        ("         0", Decimal(0)),
        ("        -2", Decimal(-2)),
        ("       +.5", Decimal(".5")),
        ("          ", None),
        ("         .", None),
    ],
)
def test_weight_literal_no_implied_decimal_or_filter(token, expected):
    batch = decode_native_records(record(WTFA_A=token))
    assert batch.records[0].weight == expected
    assert dict(batch.records[0].native_tokens)["WTFA_A"] == token
    assert batch.private_ledger["total_records"] == 1
    assert batch.private_ledger["missing_weight_records"] == int(expected is None)
    assert batch.private_ledger["nonpositive_weight_records"] == int(
        expected is not None and expected <= 0
    )


def test_missing_zero_negative_design_is_preserved_not_reassigned():
    batch = decode_native_records(
        record(PSTRAT="  .", PPSU="      ") + record(HHX="K000002", PSTRAT="  0", PPSU="    -2")
    )
    assert batch.records[0].stratum is batch.records[0].psu is None
    assert batch.records[1].stratum == 0 and batch.records[1].psu == -2
    assert batch.private_ledger["missing_design_records"] == 1
    assert batch.private_ledger["total_records"] == 2


def test_missing_duplicate_and_lexical_alias_keys_retained_privately():
    batch = decode_native_records(
        record(HHX=" ABC   ")
        + record(HHX="ABC    ")
        + record(HHX="       ")
        + record(HHX="   .   ")
    )
    assert [value.household_key for value in batch.records] == ["ABC", "ABC", None, None]
    ledger = batch.private_ledger
    assert ledger["total_records"] == 4 and ledger["ledger_conserved"]
    assert ledger["missing_household_key_records"] == 2
    assert ledger["duplicate_interpreted_household_key_records"] == 1
    assert ledger["household_keys_with_lexical_aliases"] == 1
    assert (
        dict(batch.records[0].native_tokens)["HHX"] != dict(batch.records[1].native_tokens)["HHX"]
    )
    assert decode_native_records(record(HHX="001 AB ")).records[0].household_key == "001 AB"


def test_empty_private_batch_conservation_privacy_and_five_false_gates():
    empty = decode_native_records(b"")
    assert empty.records == ()
    assert empty.private_ledger["category_counts"] == dict.fromkeys(CATEGORIES, 0)
    assert empty.private_ledger["total_records"] == 0 and empty.private_ledger["ledger_conserved"]
    batch = decode_native_records(record())
    assert repr(batch) == "<PrivateNHISNativeBatch>"
    assert repr(batch.records[0]) == "<PrivateNHISNativeRecord>"
    with pytest.raises(TypeError):
        json.dumps(batch)
    with pytest.raises(FrozenInstanceError):
        batch.records = ()
    with pytest.raises(FrozenInstanceError):
        batch.records[0].household_key = "changed"
    ledger = batch.private_ledger
    assert all(
        ledger[name] is True
        for name in ["validation_only", "software_witness", "private_aggregate"]
    )
    assert ledger["source_admitted"] is False
    assert ledger["scientific_gates"] == dict.fromkeys(
        [
            "direct_initialization_allowed",
            "clinical_fit_allowed",
            "engine_activation_allowed",
            "sampling_distribution_assumed",
            "scientific_release_ready",
        ],
        False,
    )
    assert "K000001" not in json.dumps(ledger)
    ledger["category_counts"]["reported_type2"] = -1
    assert batch.private_ledger["category_counts"]["reported_type2"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"RECTYPE": "20"},
        {"RECTYPE": "  "},
        {"SRVY_YR": "2024"},
        {"SRVY_YR": "    "},
        {"HHSTAT_A": "2"},
        {"HHSTAT_A": "9"},
        {"AGEP_A": "17"},
        {"AGEP_A": "86"},
        {"AGEP_A": "96"},
        {"SEX_A": "0"},
        {"PROXYFLAG_A": "3"},
        {"DIBEV_A": "0"},
        {"DIBTYPE_A": "4"},
        {"DIBTYPE_A": "6"},
        {"WTFA_A": "       NaN"},
        {"WTFA_A": "       Inf"},
        {"WTFA_A": "       1E2"},
        {"WTFA_A": "     1,000"},
        {"WTFA_A": "        .A"},
        {"PSTRAT": "1.2"},
        {"PPSU": "   1E2"},
    ],
)
def test_unlisted_codes_syntax_and_source_role_contradictions_refuse(changes):
    with pytest.raises(ValueError) as failure:
        decode_native_records(record(**changes))
    assert "K000001" not in str(failure.value)
    assert failure.value.__cause__ is None


@pytest.mark.parametrize(
    "case",
    [
        "short",
        "long",
        "lf",
        "cr",
        "mixed",
        "no_final",
        "empty_line",
        "control_selected",
        "control_unselected",
        "nonascii",
        "bom",
        "not_bytes",
        "mutable",
    ],
)
def test_strict_framing_and_byte_policy_refuses_without_repairs(case):
    content = record()
    if case == "short":
        content = content[:-3] + b"\r\n"
    elif case == "long":
        content = content[:-2] + b" \r\n"
    elif case == "lf":
        content = content[:-2] + b"\n"
    elif case == "cr":
        content = content[:-2] + b"\r"
    elif case == "mixed":
        content += record()[:-2] + b"\n"
    elif case == "no_final":
        content = content[:-2]
    elif case == "empty_line":
        content += b"\r\n"
    elif case == "control_selected":
        content = content[:13] + b"\t" + content[14:]
    elif case == "control_unselected":
        content = content[:300] + b"\x00" + content[301:]
    elif case == "nonascii":
        content = content[:300] + b"\xff" + content[301:]
    elif case == "bom":
        content = b"\xef\xbb\xbf" + content
    elif case == "not_bytes":
        content = content.decode("ascii")
    else:
        content = bytearray(content)
    with pytest.raises(ValueError):
        decode_native_records(content)


def test_later_malformed_record_refuses_whole_call_without_returning_partial_batch():
    content = record() + record(HHX="K000002", DIBTYPE_A="4")
    with pytest.raises(ValueError) as failure:
        decode_native_records(content)
    assert str(failure.value) == "Unsupported synthetic NHIS native lexical or record-role contract"
    assert "K000002" not in str(failure.value)
    assert failure.value.__suppress_context__ is True


def test_resource_cap_before_projection_and_no_file_loader(monkeypatch):
    monkeypatch.setattr("demeter.data.nhis_native_records._MAX_BYTES", 686)

    def no_projection(*args):
        pytest.fail("Resource refusal must precede projection")

    monkeypatch.setattr("demeter.data.nhis_native_records._record", no_projection)
    with pytest.raises(ValueError, match="resource"):
        decode_native_records(record())


def test_pure_decoder_does_not_open_files_or_network(monkeypatch):
    content = record()

    def forbidden(*args, **kwargs):
        pytest.fail("Pure software decoder must not acquire or load source records")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    assert len(decode_native_records(content).records) == 1
