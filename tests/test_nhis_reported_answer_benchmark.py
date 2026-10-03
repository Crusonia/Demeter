"""Synthetic-only source-to-method checks; never invoke original NHIS delivery."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from fractions import Fraction
import hashlib
from itertools import combinations
import json
from pathlib import Path

import numpy as np
import pytest

from demeter.data import nhis_reported_answer_benchmark as bridge

ROOT = Path(__file__).resolve().parents[1]


def native_row(key, diagnosis, diabetes_type, weight, stratum, psu, **changes):
    # Independent literal producer-column oracle, not decoder._FIELDS.
    fields = {
        (1, 2): "10",
        (3, 6): "2025",
        (7, 13): key,
        (14, 23): str(weight),
        (26, 28): str(stratum),
        (29, 34): str(psu),
        (36, 36): "2",
        (38, 38): "1",
        (46, 46): "1",
        (48, 49): "45",
        (176, 176): diagnosis,
        (187, 187): diabetes_type,
    }
    names = {"age": (48, 49), "sex": (46, 46), "proxy": (36, 36), "adult": (38, 38)}
    fields.update({names[name]: value for name, value in changes.items()})
    row = bytearray(b" " * 685)
    for (start, end), value in fields.items():
        encoded = value.encode("ascii")
        assert len(encoded) <= end - start + 1
        row[start - 1 : end] = encoded.rjust(end - start + 1, b" ")
    return bytes(row) + b"\r\n"


def fixture_bytes():
    answers = [
        ("2", ""),
        ("1", "1"),
        ("1", "2"),
        ("1", "3"),
        ("1", "7"),
        ("9", ""),
        ("2", "2"),
        ("1", "2"),
    ]
    design = [(1, 1), (1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 2), (2, 3)]
    return b"".join(
        native_row(str(i + 1), *answer, i + 1, *pair)
        for i, (answer, pair) in enumerate(zip(answers, design, strict=True))
    )


@pytest.fixture
def run(monkeypatch):
    actual_preflight = bridge._independent_preflight
    delivery = {"content": fixture_bytes(), "reference": 8}

    def synthetic_preflight(root):
        config = actual_preflight(root)  # Actual 15 disk/loaded pin checks still run.
        config["source_identity"]["native"]["reference_records"] = delivery["reference"]
        # Explicit fixture-only source identity: never claim frozen original
        # files were verified through the patched synthetic delivery boundary.
        for name, content in (
            ("archive", b"synthetic archive boundary fixture"),
            ("native", delivery["content"]),
        ):
            config["source_identity"][name]["sha256"] = hashlib.sha256(content).hexdigest()
            config["source_identity"][name]["size_bytes"] = len(content)
        return config

    monkeypatch.setattr(bridge, "_independent_preflight", synthetic_preflight)
    monkeypatch.setattr(
        bridge.guard,
        "verify_delivery",
        lambda *args, **kw: bridge.guard.PrivateVerifiedDelivery(delivery["content"]),
    )

    def invoke(content=None, reference=None):
        if content is not None:
            delivery["content"] = content
        if reference is not None:
            delivery["reference"] = reference
        return bridge.benchmark_reported_answers(
            Path("synthetic.zip"), Path("synthetic.dat"), root=ROOT
        )

    return invoke


def oracle():
    labels = list(bridge.classifier.CATEGORIES) + ["reported_type2"]
    w = list(map(Fraction, range(1, 9)))
    design = [(1, 1), (1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 2), (2, 3)]
    pairs = sorted(set(design))
    total = sum(w)
    p = [
        sum(x for x, label in zip(w, labels, strict=True) if label == category) / total
        for category in bridge.classifier.CATEGORIES
    ]
    scores = [
        {
            key: sum(
                x * (int(label == category) - ratio) / total
                for x, label, row in zip(w, labels, design, strict=True)
                if row == key
            )
            for key in pairs
        }
        for category, ratio in zip(bridge.classifier.CATEGORIES, p, strict=True)
    ]
    v = [[Fraction(0) for _ in p] for _ in p]
    for stratum in (1, 2):
        keys = [key for key in pairs if key[0] == stratum]
        for a, b in combinations(keys, 2):
            for i in range(7):
                for j in range(7):
                    v[i][j] += (
                        (scores[i][a] - scores[i][b])
                        * (scores[j][a] - scores[j][b])
                        / (len(keys) - 1)
                    )
    return list(map(float, p)), [[float(x) for x in row] for row in v]


def test_full_joint_independent_oracle_and_partition(run):
    result = run()
    private = result.private_result
    assert result.technical_envelope["status"] == "completed"
    assert (
        result.technical_envelope["provenance"]["native_sha256"]
        == hashlib.sha256(fixture_bytes()).hexdigest()
    )
    assert (
        result.technical_envelope["provenance"]["archive_sha256"]
        == hashlib.sha256(b"synthetic archive boundary fixture").hexdigest()
    )
    p, v = oracle()
    np.testing.assert_allclose(private["joint"]["ratios"], p, rtol=2e-15, atol=0)
    np.testing.assert_allclose(private["joint"]["covariance"], v, rtol=4e-15, atol=2e-18)
    ledger = private["record_ledger"]
    assert ledger["category_counts"] == dict.fromkeys(bridge.classifier.CATEGORIES, 1) | {
        "reported_type2": 2
    }
    assert ledger["total_records"] == 8 and ledger["ledger_conserved"] is True
    assert np.min(private["joint"]["covariance"]) < 0
    assert set(private) == {
        "kind",
        "schema_version",
        "model_role",
        "private_aggregate",
        "source_admitted",
        "scientific_gates",
        "record_ledger",
        "joint",
    }
    assert all(value is False for value in private["scientific_gates"].values())
    encoded = json.dumps(result.technical_envelope)
    assert all(
        word not in encoded
        for word in [
            '"record_ledger"',
            '"ratios"',
            '"covariance"',
            '"degrees_of_freedom"',
            '"confidence_interval"',
        ]
    )


def test_unknown_demographics_period_and_blank_never_filter(run):
    content = b"".join(
        [
            native_row("a", ".", ".", 1, 1, 1, age="97", sex="7", proxy="9"),
            native_row("b", "", "", 2, 1, 2, age="85", sex="", proxy="1"),
        ]
    )
    result = run(content, 2)
    assert result.technical_envelope["status"] == "completed"
    ledger = result.private_result["record_ledger"]
    assert ledger["total_records"] == 2 and ledger["category_counts"]["diagnosis_unknown"] == 2
    assert ledger["age_roles"]["85_plus"] == 1 and ledger["age_roles"]["refused"] == 1
    assert ledger["response_reader_missingness"]["DIBEV_A"] == {
        "blank": 1,
        "single_period": 1,
        "not_missing": 0,
    }
    assert result.private_result["joint"]["ratios"] == [0, 0, 0, 0, 0, 1, 0]
    assert result.private_result["joint"]["covariance"] == [[0] * 7 for _ in range(7)]


@pytest.mark.parametrize(
    "change",
    [
        "weight_zero",
        "weight_negative",
        "weight_missing",
        "design_zero",
        "design_negative",
        "design_missing",
        "singleton",
        "adult_missing",
        "key_missing",
        "key_duplicate",
        "key_alias",
        "reference_mismatch",
    ],
)
def test_method_refusal_retains_complete_ledger_without_trimming(run, change):
    kwargs = {}
    key = "a"
    weight = "1"
    stratum = "1"
    psu = "1"
    second = "b"
    second_psu = "2"
    if change == "weight_zero":
        weight = "0"
    if change == "weight_negative":
        weight = "-1"
    if change == "weight_missing":
        weight = "."
    if change == "design_zero":
        psu = "0"
    if change == "design_negative":
        psu = "-1"
    if change == "design_missing":
        psu = ""
    if change == "singleton":
        second_psu = "1"
    if change == "adult_missing":
        kwargs["adult"] = ""
    if change == "key_missing":
        key = ""
    if change == "key_duplicate":
        second = key
    if change == "key_alias":
        key = "a "
        second = "a"
    content = native_row(key, "1", "2", weight, stratum, psu, **kwargs) + native_row(
        second, "2", "", 1, 1, second_psu
    )
    result = run(content, 3 if change == "reference_mismatch" else 2)
    assert result.private_result["record_ledger"]["total_records"] == 2
    assert result.private_result["joint"] is None
    envelope = result.technical_envelope
    assert (
        envelope["selected_values_projected"] is True
        and envelope["empirical_estimate_computed"] is False
    )
    assert envelope["status"] == "unavailable" and envelope["estimation_status"] == "not_attempted"


def test_scale_order_and_nearest_decimal_rounding(run):
    first = run().private_result["joint"]
    content = fixture_bytes()
    rows = [content[i : i + 687] for i in range(0, len(content), 687)]
    assert run(b"".join(reversed(rows))).private_result["joint"] == first
    content = b"".join(
        native_row(str(i + 1), *answer, Decimal(i + 1) * Decimal("0.1"), *pair)
        for i, (answer, pair) in enumerate(
            zip(
                [
                    ("2", ""),
                    ("1", "1"),
                    ("1", "2"),
                    ("1", "3"),
                    ("1", "7"),
                    ("9", ""),
                    ("2", "2"),
                    ("1", "2"),
                ],
                [(1, 1), (1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 2), (2, 3)],
                strict=True,
            )
        )
    )
    result = run(content)
    assert result.technical_envelope["status"] == "completed"
    np.testing.assert_allclose(
        result.private_result["joint"]["ratios"], first["ratios"], rtol=2e-15
    )
    np.testing.assert_allclose(
        result.private_result["joint"]["covariance"], first["covariance"], rtol=4e-15, atol=2e-18
    )


@pytest.mark.parametrize("weight", [Decimal("1e999"), Decimal("1e-999")])
def test_decimal_binary64_nonfinite_underflow_refusal(run, monkeypatch, weight):
    decode = bridge.decoder.decode_native_records

    def synthetic(content):
        batch = decode(content)
        return bridge.decoder.PrivateNativeBatch(
            (replace(batch.records[0], weight=weight), *batch.records[1:])
        )

    monkeypatch.setattr(bridge.decoder, "decode_native_records", synthetic)
    result = run()
    assert result.private_result["record_ledger"]["total_records"] == 8
    assert (
        result.private_result["joint"] is None
        and result.technical_envelope["empirical_estimate_computed"] is False
    )


def test_empty_and_bad_decoder_projection_chronology(run):
    empty = run(b"", 0)
    assert empty.private_result["record_ledger"]["total_records"] == 0
    assert empty.technical_envelope["empirical_estimate_computed"] is False
    bad = run(b"secret malformed record", 1)
    assert bad.private_result is None
    assert bad.technical_envelope["selected_values_projected"] is None
    assert bad.technical_envelope["projection_status"] == "possibly_partial"
    assert "secret" not in repr(bad) + json.dumps(bad.sanitized_failure)


@pytest.mark.parametrize("failure", ["delivery", "estimation", "returned_invalid"])
def test_call_failure_flags_and_no_partial_joint(run, monkeypatch, failure):
    def fail(*args, **kwargs):
        raise ValueError("secret household path weight")

    if failure == "delivery":
        monkeypatch.setattr(bridge.guard, "verify_delivery", fail)
    elif failure == "estimation":
        monkeypatch.setattr(bridge.witness, "assess", fail)
    else:
        monkeypatch.setattr(bridge.witness, "assess", lambda *a, **kw: {"bad": "secret"})
    result = run()
    envelope = result.technical_envelope
    assert envelope["status"] == "unavailable"
    assert (
        envelope["empirical_estimate_computed"]
        == {"delivery": False, "estimation": None, "returned_invalid": True}[failure]
    )
    if failure == "delivery":
        assert result.private_result is None and envelope["provenance"]["archive_sha256"] is None
    else:
        assert (
            result.private_result["joint"] is None and envelope["selected_values_projected"] is True
        )
    assert "secret" not in json.dumps(envelope) + json.dumps(result.sanitized_failure)


@pytest.mark.parametrize("mismatch", ["contract", "origin", "classifier_binding", "kernel_binding"])
def test_independent_refusal_before_delivery(run, monkeypatch, mismatch):
    called = []
    monkeypatch.setattr(bridge.guard, "verify_delivery", lambda *a, **kw: called.append(1))
    if mismatch == "contract":
        monkeypatch.setattr(bridge, "_CONTRACT_SHA", "0" * 64)
    if mismatch == "origin":
        monkeypatch.setattr(bridge.witness, "__file__", str(ROOT / "elsewhere.py"))
    if mismatch == "classifier_binding":
        monkeypatch.setattr(
            bridge.witness, "classify_reported_diabetes", lambda *a: "reported_type2"
        )
    if mismatch == "kernel_binding":
        monkeypatch.setattr(bridge.witness, "joint_proportions", lambda *a: {})
    result = run()
    assert not called
    assert all(value is None for value in result.technical_envelope["provenance"].values())
    assert (
        result.private_result is None
        and result.technical_envelope["selected_values_projected"] is False
    )


def test_small_scale_bad_covariance_and_underflow_not_absolute_floor(run, monkeypatch):
    assess = bridge.witness.assess
    for bad in ("relative_error", "underflow"):

        def corrupted(*args, _bad=bad, **kwargs):
            result = assess(*args, **kwargs)
            v = result["joint"]["covariance"]
            result["joint"]["covariance"] = [[value * 1e-100 for value in row] for row in v]
            if _bad == "relative_error":
                result["joint"]["covariance"][0][0] += 1e-110
            else:
                result["joint"]["covariance"] = [[0.0] * 7 for _ in range(7)]
                result["joint"]["covariance"][0][0] = 5e-324
            return result

        monkeypatch.setattr(bridge.witness, "assess", corrupted)
        result = run()
        assert result.private_result["joint"] is None
        assert result.technical_envelope["empirical_estimate_computed"] is True


def test_constant_repr_fresh_accessors_and_technical_fixed_schema(run):
    result = run()
    assert repr(result) == "<PrivateNHISReportedAnswerBenchmark>"
    with pytest.raises(FrozenInstanceError):
        result._technical_json = "{}"
    expected = deepcopy(result.private_result)
    result.private_result["record_ledger"]["category_counts"].clear()
    assert result.private_result == expected
    result.technical_envelope["provenance"].clear()
    assert result.technical_envelope["provenance"]
    config = json.loads((ROOT / bridge._CONTRACT).read_bytes())
    assert set(result.technical_envelope) == set(config["technical_schema"]["keys"])
    assert set(result.private_result["record_ledger"]) == set(
        config["private_schema"]["record_ledger"]["keys"]
    )
    assert result.sanitized_failure is None


@pytest.mark.parametrize(
    "bad",
    [
        "kind",
        "extra",
        "gate",
        "design",
        "domains",
        "ledger",
        "coordinate",
        "nan",
        "boolean_ratio",
        "negative_variance",
    ],
)
def test_returned_witness_schema_refused_without_false_no_estimate_claim(run, monkeypatch, bad):
    assess = bridge.witness.assess

    def malformed(*args, **kwargs):
        result = assess(*args, **kwargs)
        if bad == "kind":
            result["kind"] = "clinical_initializer"
        if bad == "extra":
            result["private_key"] = "synthetic secret"
        if bad == "gate":
            result["scientific_gates"]["clinical_fit_allowed"] = True
        if bad == "design":
            result["design"]["degrees_of_freedom"] = 4
        if bad == "domains":
            result["domains"][0]["domain"] = "age_restricted"
        if bad == "ledger":
            result["record_ledger"]["total_records"] = 7
        if bad == "coordinate":
            result["joint"]["coordinates"][0]["membership"] = "latent_healthy"
        if bad == "nan":
            result["joint"]["ratios"][0] = float("nan")
        if bad == "boolean_ratio":
            result["joint"]["ratios"][0] = True
        if bad == "negative_variance":
            result["joint"]["covariance"][0][0] = -1
        return result

    monkeypatch.setattr(bridge.witness, "assess", malformed)
    result = run()
    assert result.private_result["joint"] is None
    assert result.private_result["record_ledger"]["total_records"] == 8
    assert result.technical_envelope["empirical_estimate_computed"] is True
    assert result.technical_envelope["estimation_status"] == "completed"
    assert "synthetic secret" not in json.dumps(result.technical_envelope)


def test_decoder_batch_unchanged_by_method_and_source_reference_not_globally_patched(
    run, monkeypatch
):
    decode = bridge.decoder.decode_native_records
    batches = []

    def observe(content):
        batch = decode(content)
        batches.append((batch, deepcopy(batch.private_ledger), batch.records))
        return batch

    monkeypatch.setattr(bridge.decoder, "decode_native_records", observe)
    assert run().technical_envelope["status"] == "completed"
    batch, ledger, records = batches[0]
    assert batch.private_ledger == ledger and batch.records == records
    config = json.loads((ROOT / bridge._CONTRACT).read_bytes())
    assert config["source_identity"]["native"]["reference_records"] == 24215


@pytest.mark.parametrize("bad_delivery", ["missing", "accessor", "mutable"])
def test_delivery_materialization_failure_precedes_decoder_attempt(run, monkeypatch, bad_delivery):
    class BrokenAccessor:
        @property
        def native_bytes(self):
            raise ValueError("private source path")

    delivery = {
        "missing": object(),
        "accessor": BrokenAccessor(),
        "mutable": bridge.guard.PrivateVerifiedDelivery(bytearray(b"mutable")),
    }[bad_delivery]
    monkeypatch.setattr(bridge.guard, "verify_delivery", lambda *a, **kw: delivery)
    called = []
    monkeypatch.setattr(bridge.decoder, "decode_native_records", lambda *a: called.append(1))
    result = run()
    assert not called and result.private_result is None
    envelope = result.technical_envelope
    assert envelope["selected_values_projected"] is False
    assert envelope["projection_status"] == "not_attempted"
    assert envelope["empirical_estimate_computed"] is False
    assert "private source path" not in json.dumps(result.sanitized_failure)
