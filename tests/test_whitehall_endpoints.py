"""Synthetic source-wire fixtures and mathematical checks, never clinical fits."""

from __future__ import annotations

import copy
import io
import json
import math
from pathlib import Path

import numpy as np
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from scipy.linalg import expm
from scipy.stats import binom

import demeter.analysis.whitehall_endpoints as module
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry


@pytest.fixture(scope="session")
def registered():
    return EvidenceRegistry.from_yaml("evidence/parameters.yaml")


def _pdf(lines_by_page: list[list[str]], *, rotation: int = 0) -> bytes:
    """Labeled synthetic PDF, not an independent clinical source."""
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for lines in lines_by_page:
        page = writer.add_blank_page(width=850, height=850)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        commands = []
        for index, line in enumerate(lines):
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"BT /F1 12 Tf 1 0 0 1 30 {800 - index * 20} Tm ({escaped}) Tj ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(commands).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
        if rotation:
            page.rotate(rotation)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _source_lines(protocol: dict, counts: dict) -> tuple[list[list[str]], list[list[str]]]:
    y, q = counts["normal_label_n"], counts["nonreversion_label_n"]
    main = [[] for _ in range(protocol["source_structure"]["main_page_count"])]
    main[0] = [protocol["bibliography"]["title"], protocol["bibliography"]["doi"]]
    main[2] = [
        f"FPG criterion Among {y + q} participants with FPG-defined pre- diabetes at baseline, "
        f"{y} (0.0%) reverted to normoglycaemia UNSELECTED_PRIVATE_MAIN_TOKEN"
    ]
    esm = [[] for _ in range(protocol["source_structure"]["supplement_page_count"])]
    esm[0] = [
        "Table 1 synthetic validation-only caption",
        "Reversion N No. events Events per person time",
        "By FPG",
        f"Prediabetes or diabetes {q} PRIVATE_UNSELECTED_EVENT_TOKEN",
        f"Normoglycaemia {y} PRIVATE_UNSELECTED_RATE_TOKEN",
        "By 2hPG",
        "Normoglycaemia PRIVATE_OTHER_CRITERION_TOKEN",
    ]
    return main, esm


@pytest.fixture
def fixture(registered, tmp_path, monkeypatch):
    registry = registered.model_copy(deep=True)
    spec = registry.datasets[module.DATASET]
    protocol = json.loads(Path(spec["protocol_path"]).read_bytes())
    receipts = json.loads(Path(spec["receipts_path"]).read_bytes())
    raw = tmp_path / "raw"
    raw.mkdir()
    lines = _source_lines(protocol, spec["analysis"]["counts"])
    contents = {
        "main_static_pdf": _pdf(lines[0]),
        "supplement_pdf": _pdf(lines[1], rotation=90),
    }
    for label, content in contents.items():
        pin = protocol["source_documents"]["required_source_receipts"][label]
        pin["sha256"], pin["size_bytes"] = digest(content), len(content)
        receipts["required_sources"][label] = copy.deepcopy(pin)
        registry.sources[module.SOURCE_IDS[label]].sha256 = digest(content)
        (raw / pin["cache_filename"]).write_bytes(content)
    for name, content in (("protocol", protocol), ("receipts", receipts)):
        path = tmp_path / f"{name}.json"
        path.write_bytes(encoded(content))
        spec[f"{name}_path"], spec[f"{name}_sha256"] = str(path), digest(path.read_bytes())
        monkeypatch.setattr(module, f"{name.upper()}_SHA256", spec[f"{name}_sha256"])
    return registry, raw, protocol, contents


def _failed(report: dict) -> None:
    assert report["source_audit_passed"] is False
    assert report["working_fit_performed"] is False
    assert report["clinical_transition_fit_performed"] is False
    assert report["engine_activation_allowed"] is False
    assert report["scientific_release_ready"] is False
    assert report["endpoint"] is None
    assert report["working_fit"] is None
    assert report["interval"] is None
    assert report["failure"] is not None
    assert "PRIVATE" not in json.dumps(report, allow_nan=False)


def test_source_reproduction_and_working_likelihood_are_separate(fixture):
    registry, raw, protocol, _ = fixture
    before = registry.model_dump(mode="json")
    report = module.audit_whitehall_endpoint(registry, raw)
    assert registry.model_dump(mode="json") == before
    assert report["source_audit_passed"] is True
    assert report["working_fit_performed"] is True
    assert report["endpoint"]["counts"] == registry.datasets[module.DATASET]["analysis"]["counts"]
    assert report["endpoint"]["main_crosscheck"]["paired_n"] == report["endpoint"]["paired_n"]
    assert report["interval"]["confidence_level"] == protocol["interval_design"]["confidence_level"]
    assert report["working_fit"]["assumptions_empirically_established"] is False
    assert report["clinical_transition_fit_performed"] is False
    assert report["engine_activation_allowed"] is False
    assert report["scope_flags"]["full_issue57_complete"] is False
    assert report["scope_flags"]["full_issue58_complete"] is False
    assert report["provenance"]["network_used"] is False
    assert report["provenance"]["participant_records_used"] is False
    assert "PRIVATE" not in json.dumps(report, allow_nan=False)


def test_descriptive_mode_never_calls_inference(fixture, monkeypatch):
    registry, raw, _, _ = fixture

    def forbidden(*args, **kwargs):
        pytest.fail("Descriptive mode must not evaluate a working likelihood/interval")

    monkeypatch.setattr(module, "clopper_pearson", forbidden)
    monkeypatch.setattr(module, "binomial_log_likelihood", forbidden)
    report = module.audit_whitehall_endpoint(registry, raw, working_likelihood=False)
    assert report["source_audit_passed"] is True
    assert report["working_fit_performed"] is False
    assert report["working_fit"] is None
    assert report["interval"] is None
    assert report["endpoint"]["observed_normal_label_proportion"] == registry.value(
        "whitehall_fpg_normal_label_proportion"
    )


@pytest.mark.parametrize("p", [0.0, 0.2, 0.5, 1.0])
def test_normalized_binomial_probability_mass(p):
    n = 8  # Small synthetic mathematical experiment, not a clinical parameter.
    mass = sum(math.exp(module.binomial_log_likelihood(y, n, p)) for y in range(n + 1))
    assert mass == pytest.approx(1.0)


def test_binomial_boundaries_and_json_safe_impossible_event():
    assert module.binomial_log_likelihood(0, 8, 0) == 0
    assert module.binomial_log_likelihood(8, 8, 1) == 0
    for y, p in ((1, 0), (7, 1)):
        logp = module.binomial_log_likelihood(y, 8, p)
        assert logp == -math.inf
        serialized = module.json_log_likelihood(logp)
        assert serialized == {"value": None, "status": "zero_probability_event"}
        json.dumps(serialized, allow_nan=False)


def test_unrepresentable_numeric_inputs_have_controlled_value_errors():
    enormous = 10**1000
    with pytest.raises(ValueError):
        module.binomial_log_likelihood(3, 8, enormous)
    for function, extra in (
        (module.binomial_log_likelihood, 0.5),
        (module.clopper_pearson, 0.95),
    ):
        with pytest.raises(ValueError):
            function(3, enormous, extra)
    with pytest.raises(ValueError):
        module.toy_normal_endpoint(enormous, 0, 1)


@pytest.mark.parametrize("value", [math.nan, math.inf, True, "PRIVATE", None])
def test_json_log_likelihood_rejects_invalid_numerics(value):
    with pytest.raises(ValueError):
        module.json_log_likelihood(value)


@pytest.mark.parametrize("p", [True, "0.5", None, -0.01, 1.01, math.inf, -math.inf, math.nan])
def test_probability_domain_is_not_coerced(p):
    with pytest.raises(ValueError):
        module.binomial_log_likelihood(3, 8, p)


@pytest.mark.parametrize(
    "y,n",
    [
        (True, 8),
        (3, True),
        (3.0, 8),
        (3, 8.0),
        ("3", 8),
        (3, "8"),
        (-1, 8),
        (9, 8),
        (0, 0),
        (0, -1),
    ],
)
def test_counts_are_strict_integers(y, n):
    for function, extra in ((module.binomial_log_likelihood, 0.5), (module.clopper_pearson, 0.95)):
        with pytest.raises(ValueError):
            function(y, n, extra)


@pytest.mark.parametrize("confidence", [True, "0.95", None, 0, 1, -0.1, 1.1, math.nan, math.inf])
def test_confidence_domain(confidence):
    with pytest.raises(ValueError):
        module.clopper_pearson(3, 8, confidence)


@pytest.mark.parametrize("y", [0, 1, 3, 7, 8])
def test_cp_exact_binomial_tail_inversion_and_boundaries(y):
    confidence = 0.95
    lower, upper = module.clopper_pearson(y, 8, confidence)
    tail = (1 - confidence) / 2
    if y == 0:
        assert lower == 0
    else:
        assert binom.sf(y - 1, 8, lower) == pytest.approx(tail)
    if y == 8:
        assert upper == 1
    else:
        assert binom.cdf(y, 8, upper) == pytest.approx(tail)
    assert lower <= y / 8 <= upper


def test_registered_synthetic_ambiguity_matches_matrix_exponential(registered):
    fixture = registered.datasets[module.DATASET]["analysis"]["synthetic_ambiguity_fixture"]
    first, second = module.synthetic_ambiguity_witness(fixture)
    tolerance = fixture["absolute_tolerance"]
    assert first["a"] != second["a"] and first["b"] != second["b"]
    for witness in (first, second):
        a, b = witness["a"], witness["b"]
        transition = expm(np.array([[-a, a], [b, -b]]) * fixture["time"])
        assert np.all(transition >= 0)
        assert np.allclose(transition.sum(axis=1), 1, atol=tolerance, rtol=0)
        assert transition[1, 0] == pytest.approx(
            fixture["target_endpoint_probability"], abs=tolerance
        )
        assert witness["endpoint_probability"] == pytest.approx(transition[1, 0], abs=tolerance)
        assert witness["source_counts_used"] is False
        assert witness["clinical_rate_interpretation"] is False
    assert module.toy_normal_endpoint(0, 0, fixture["time"]) == 0


@pytest.mark.parametrize(
    "a,b,t", [(-1, 1, 1), (1, -1, 1), (1, 1, 0), (True, 1, 1), (1, math.nan, 1), (1, 1, math.inf)]
)
def test_toy_model_domains(a, b, t):
    with pytest.raises(ValueError):
        module.toy_normal_endpoint(a, b, t)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "observed"),
        ("evidence_grade", "C"),
        ("role", "clinical"),
        ("time_unit", "years"),
        ("total_rates", [0.1, 0.1]),
        ("target_endpoint_probability", True),
        ("target_endpoint_probability", 0.99),
        ("absolute_tolerance", 0),
    ],
)
def test_synthetic_witness_does_not_accept_clinical_or_invalid_fixture(registered, field, value):
    fixture = copy.deepcopy(
        registered.datasets[module.DATASET]["analysis"]["synthetic_ambiguity_fixture"]
    )
    fixture[field] = value
    with pytest.raises(ValueError):
        module.synthetic_ambiguity_witness(fixture)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows.__setitem__(0, "Table 2"),
        lambda rows: rows.append("Table 1 duplicate"),
        lambda rows: rows.__setitem__(1, "Reversion No. events N"),
        lambda rows: rows.__setitem__(1, "Reversion N No. events N"),
        lambda rows: rows.__setitem__(2, "By HbA1c"),
        lambda rows: rows.append("By FPG duplicate"),
        lambda rows: rows.__setitem__(5, "By OTHER"),
        lambda rows: rows.append("By 2hPG duplicate"),
        lambda rows: rows.__setitem__(3, "Prediabetes or diabetes -1 PRIVATE"),
        lambda rows: rows.__setitem__(3, "Prediabetes or diabetes 1.5 PRIVATE"),
        lambda rows: rows.__setitem__(3, "Prediabetes or diabetes true PRIVATE"),
        lambda rows: rows.__setitem__(3, "Prediabetes or diabetes 4_55 PRIVATE"),
        lambda rows: rows.insert(4, rows[3]),
        lambda rows: rows.__setitem__(4, "Normal-label 365 PRIVATE"),
        lambda rows: rows.__setitem__(slice(3, 5), list(reversed(rows[3:5]))),
    ],
)
def test_selected_table_drift_rejected_without_raw_error_text(fixture, mutation):
    registry, _, protocol, contents = fixture
    _, esm = _source_lines(protocol, registry.datasets[module.DATASET]["analysis"]["counts"])
    mutation(esm[0])
    with pytest.raises(ValueError) as error:
        module.extract_reported(contents["main_static_pdf"], _pdf(esm, rotation=90), protocol)
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows.__setitem__(0, rows[0].replace("FPG criterion", "OTHER criterion")),
        lambda rows: rows.append(rows[0]),
        lambda rows: rows.__setitem__(0, rows[0].replace("820", "821")),
        lambda rows: rows.__setitem__(0, rows[0].replace("365", "364")),
        lambda rows: rows.__setitem__(0, rows[0].replace("pre- diabetes", "pre-- diabetes")),
        lambda rows: rows.__setitem__(
            0, rows[0].replace("reverted to normoglycaemia", "progressed to diabetes")
        ),
    ],
)
def test_required_main_binding_and_agreement(fixture, mutation):
    registry, _, protocol, contents = fixture
    main, _ = _source_lines(protocol, registry.datasets[module.DATASET]["analysis"]["counts"])
    mutation(main[2])
    with pytest.raises(ValueError):
        module.extract_reported(_pdf(main), contents["supplement_pdf"], protocol)


def test_main_abstract_decoy_cannot_replace_page_three_crosscheck(fixture):
    registry, _, protocol, contents = fixture
    main, _ = _source_lines(protocol, registry.datasets[module.DATASET]["analysis"]["counts"])
    main[0].append(main[2][0])
    main[2] = ["No selected main crosscheck"]
    with pytest.raises(ValueError):
        module.extract_reported(_pdf(main), contents["supplement_pdf"], protocol)


@pytest.mark.parametrize(
    "case", ["wrong_title", "wrong_doi", "main_pages", "esm_pages", "rotation", "malformed"]
)
def test_document_identity_and_structure(fixture, case):
    registry, _, protocol, contents = fixture
    main, esm = _source_lines(protocol, registry.datasets[module.DATASET]["analysis"]["counts"])
    rotation = 90
    if case == "wrong_title":
        main[0][0] = "Another study"
    if case == "wrong_doi":
        main[0][1] = "10.other/PRIVATE"
    if case == "main_pages":
        main.pop()
    if case == "esm_pages":
        esm.pop()
    if case == "rotation":
        rotation = 0
    a, b = _pdf(main), _pdf(esm, rotation=rotation)
    if case == "malformed":
        a = b"%PDF-malformed PRIVATE"
    with pytest.raises(ValueError):
        module.extract_reported(a, b, protocol)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda spec: spec.__setitem__("model_role", "health_model"),
        lambda spec: spec.__setitem__("clinical_fit_allowed", True),
        lambda spec: spec.__setitem__("engine_activation_allowed", 0),
        lambda spec: spec["source_ids"].__setitem__("other", "PRIVATE"),
        lambda spec: spec["parameter_keys"].append(spec["parameter_keys"][0]),
        lambda spec: spec["analysis"].__setitem__("confidence_level", 0.9),
        lambda spec: spec["analysis"]["confidence_setting"].__setitem__("not_source_estimate", 1),
        lambda spec: spec["analysis"]["confidence_setting"].__setitem__("status", "observed"),
        lambda spec: spec["analysis"]["confidence_setting"].__setitem__("rationale", ""),
        lambda spec: spec["analysis"]["source_structure"].__setitem__(
            "supplement_table_page", True
        ),
        lambda spec: spec["analysis"]["counts"].__setitem__("normal_label_n", True),
    ],
)
def test_dataset_drift_is_failed_before_working_evaluation(fixture, mutation, monkeypatch):
    registry, raw, _, _ = fixture
    mutation(registry.datasets[module.DATASET])

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid source contract must not run inference")

    monkeypatch.setattr(module, "clopper_pearson", forbidden)
    _failed(module.audit_whitehall_endpoint(registry, raw))


@pytest.mark.parametrize(
    "case", ["missing", "tamper", "sha", "url", "doi", "filename", "retrieved"]
)
def test_source_byte_and_metadata_failures_do_not_fit(fixture, case, monkeypatch):
    registry, raw, protocol, _ = fixture
    source = registry.sources[module.SOURCE_IDS["supplement_pdf"]]
    path = (
        raw
        / protocol["source_documents"]["required_source_receipts"]["supplement_pdf"][
            "cache_filename"
        ]
    )
    if case == "missing":
        path.unlink()
    if case == "tamper":
        path.write_bytes(b"PRIVATE_CORRUPT_BYTES")
    if case == "sha":
        source.sha256 = "0" * 64
    if case == "url":
        source.url = "https://example.invalid/PRIVATE"
    if case == "doi":
        source.doi = "10.other/PRIVATE"
    if case == "filename":
        source.raw_filename = "PRIVATE.pdf"
    if case == "retrieved":
        source.retrieved_at = source.retrieved_at.replace(year=2000)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid source must not run inference")

    monkeypatch.setattr(module, "clopper_pearson", forbidden)
    report = module.audit_whitehall_endpoint(registry, raw)
    _failed(report)
    assert report["failure"]["stage"] == "sources"


@pytest.mark.parametrize("name", ["protocol", "receipts"])
def test_coordinated_contract_registry_repins_still_fail(fixture, name):
    registry, raw, _, _ = fixture
    spec = registry.datasets[module.DATASET]
    path = Path(spec[f"{name}_path"])
    path.write_bytes(path.read_bytes() + b" ")
    spec[f"{name}_sha256"] = digest(path.read_bytes())
    _failed(module.audit_whitehall_endpoint(registry, raw))


@pytest.mark.parametrize("kind", ["duplicate", "nonfinite"])
def test_strict_contract_json(fixture, monkeypatch, kind):
    registry, raw, _, _ = fixture
    spec = registry.datasets[module.DATASET]
    path = Path(spec["protocol_path"])
    value = b'{"private":1,"private":2}' if kind == "duplicate" else b'{"private":NaN}'
    path.write_bytes(value)
    spec["protocol_sha256"] = digest(value)
    monkeypatch.setattr(module, "PROTOCOL_SHA256", digest(value))
    _failed(module.audit_whitehall_endpoint(registry, raw))


@pytest.mark.parametrize(
    "field,value",
    [
        ("value", 1),
        ("unit", "annual_rate"),
        ("status", "estimated"),
        ("model_role", "health_model"),
        ("evidence_grade", "B"),
        ("source_id", "whitehall_main2019"),
        ("unresolved", True),
    ],
)
def test_parameter_definition_drift(fixture, field, value):
    registry, raw, _, _ = fixture
    setattr(registry.parameters["whitehall_fpg_normal_label_n"], field, value)
    report = module.audit_whitehall_endpoint(registry, raw)
    _failed(report)
    assert report["failure"]["stage"] == "registry_agreement"


@pytest.mark.parametrize("mode", [0, 1, "false", None])
def test_analysis_mode_is_a_strict_boolean(fixture, mode):
    registry, raw, _, _ = fixture
    report = module.audit_whitehall_endpoint(registry, raw, working_likelihood=mode)
    _failed(report)
    assert report["failure"]["stage"] == "options"


@pytest.mark.parametrize(
    "field,value",
    [
        ("absolute_tolerance", 1e-3),
        ("absolute_tolerance", True),
        ("absolute_tolerance", math.nan),
        ("status", "observed"),
        ("evidence_grade", "C"),
        ("role", "source_precision"),
        ("source_precision_claim", True),
    ],
)
def test_numerical_tolerance_cannot_weaken_source_or_interval_agreement(
    fixture, field, value, monkeypatch
):
    registry, raw, _, _ = fixture
    registry.datasets[module.DATASET]["analysis"]["numerical_comparison"][field] = value

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid tolerance metadata must not evaluate inference")

    monkeypatch.setattr(module, "clopper_pearson", forbidden)
    _failed(module.audit_whitehall_endpoint(registry, raw))


def test_registered_cp_interval_allows_only_declared_numerical_roundoff(fixture):
    registry, raw, _, _ = fixture
    uncertainty = registry.parameters["whitehall_fpg_normal_label_proportion"].uncertainty
    uncertainty.low += 5e-13
    report = module.audit_whitehall_endpoint(registry, raw)
    assert report["source_audit_passed"] is True
    assert report["interval"]["tolerance_is_source_precision"] is False
    assert report["interval"]["registry_agreement_numerical_tolerance"] == 1e-12
    uncertainty.low += 1e-5
    _failed(module.audit_whitehall_endpoint(registry, raw))


@pytest.mark.parametrize(
    "case", ["source_set", "receipt_identity", "status_type", "unsafe_filename"]
)
def test_receipt_metadata_stays_bound_even_with_test_only_contract_repins(
    fixture, monkeypatch, case
):
    registry, raw, protocol, _ = fixture
    spec = registry.datasets[module.DATASET]
    receipts = json.loads(Path(spec["receipts_path"]).read_bytes())
    if case == "source_set":
        receipts["required_sources"]["PRIVATE"] = receipts["required_sources"].pop("supplement_pdf")
    elif case == "receipt_identity":
        receipts["required_sources"]["supplement_pdf"]["url"] = "https://example.invalid/PRIVATE"
    else:
        pin = protocol["source_documents"]["required_source_receipts"]["supplement_pdf"]
        if case == "status_type":
            pin["status"] = 200.0
        else:
            pin["cache_filename"] = "../PRIVATE.pdf"
        receipts["required_sources"]["supplement_pdf"] = copy.deepcopy(pin)
    for name, content in (("protocol", protocol), ("receipts", receipts)):
        path = Path(spec[f"{name}_path"])
        path.write_bytes(encoded(content))
        spec[f"{name}_sha256"] = digest(path.read_bytes())
        monkeypatch.setattr(module, f"{name.upper()}_SHA256", spec[f"{name}_sha256"])
    _failed(module.audit_whitehall_endpoint(registry, raw))


def test_source_symlink_is_not_accepted(fixture, tmp_path):
    registry, raw, protocol, contents = fixture
    filename = protocol["source_documents"]["required_source_receipts"]["supplement_pdf"][
        "cache_filename"
    ]
    external = tmp_path / "external.pdf"
    external.write_bytes(contents["supplement_pdf"])
    selected = raw / filename
    selected.unlink()
    try:
        selected.symlink_to(external)
    except OSError:
        pytest.skip("Host does not permit symbolic links")
    _failed(module.audit_whitehall_endpoint(registry, raw))
