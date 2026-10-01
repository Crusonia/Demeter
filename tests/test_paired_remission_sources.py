"""Synthetic publication wires test source choices; no participant data in CI."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

import demeter.analysis.paired_remission_sources as module
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded


PRIVATE = "UNSELECTED_SYNTHETIC_SOURCE_TEXT"
COUNTS = {
    "itt_n": 10,
    "itt_n_one_year_crosscheck": 10,
    "positive_first_n": 4,
    "positive_second_n": 5,
    "positive_second_itt_denominator": 9,
    "positive_pair_lower_n": 3,
}


class FakePage:
    def __init__(self, text, label, index, reads):
        self.text, self.label, self.index, self.reads = text, label, index, reads

    def extract_text(self):
        self.reads.append((self.label, self.index))
        return self.text


def _readers(protocol, counts, reads):
    readers = {}
    for label, bibliography in protocol["bibliography"].items():
        texts = [PRIVATE for _ in range(bibliography["physical_pages"])]
        texts[0] = f"{bibliography['title_prefix']} {bibliography['doi']}"
        if label == "one_year":
            texts[3] = (
                f"Findings: {counts['itt_n_one_year_crosscheck']} participants per group "
                "comprised the intention-to-treat population. Diabetes remission was achieved in "
                f"{counts['positive_first_n']} (unselected percentage) participants in the "
                f"intervention group. {PRIVATE}"
            )
        else:
            texts[10] = (
                f"intention-to-treat population comprised {counts['itt_n']} participants per group "
                + PRIVATE
            )
            texts[11] = (
                "At 24 months, without imputing missing data and assuming no remission for those "
                "without data, diabetes was in remission in "
                f"{counts['positive_second_n']}/{counts['positive_second_itt_denominator']} "
                f"(unselected percentage) participants in the intervention group. {PRIVATE}"
            )
            texts[12] = (
                "In the intervention group, those maintaining remission between 12 and 24 months "
                f"(n={counts['positive_pair_lower_n']}) {PRIVATE}"
            )
        readers[label] = SimpleNamespace(
            is_encrypted=False,
            pages=[FakePage(text, label, index, reads) for index, text in enumerate(texts)],
        )
    return readers


def _xml(amendment, *, n=10, b=5):
    identity = amendment["selection"]["article_identity"]
    root = ET.Element("PubmedArticleSet")
    article = ET.SubElement(root, "PubmedArticle")
    citation = ET.SubElement(article, "MedlineCitation")
    ET.SubElement(citation, "PMID").text = identity["pmid"]
    abstract = ET.SubElement(ET.SubElement(citation, "Article"), "Abstract")
    ET.SubElement(abstract, "AbstractText", Label="METHODS").text = (
        "The intention-to-treat population was analysed for coprimary outcomes. " + PRIVATE
    )
    ET.SubElement(abstract, "AbstractText", Label="FINDINGS").text = (
        f"The intention-to-treat population consisted of {n} participants per group; "
        f"and {b} (unselected percentage) intervention participants and unselected control "
        f"participants had remission of diabetes; {PRIVATE}"
    )
    ET.SubElement(abstract, "AbstractText", Label="INTERPRETATION").text = PRIVATE
    ids = ET.SubElement(ET.SubElement(article, "PubmedData"), "ArticleIdList")
    ET.SubElement(ids, "ArticleId", IdType="doi").text = identity["doi"]
    return ET.tostring(root, encoding="utf-8")


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    protocol = json.loads(Path(module.PROTOCOL_PATH).read_bytes())
    amendment = json.loads(Path(module.AMENDMENT_PATH).read_bytes())
    failure = json.loads(Path(module.FAILURE_PATH).read_bytes())
    protocol["chronology"] = "Synthetic software fixture, no clinical validation."
    for label in protocol["bibliography"]:
        protocol["bibliography"][label]["doi"] = f"10.0000/synthetic-{label}"
        protocol["bibliography"][label]["title_prefix"] = f"Synthetic {label} publication"
    amendment["selection"]["article_identity"] = {
        "doi": "10.0000/synthetic-two_year",
        "pmid": "synthetic-record",
        "required_article_count": 1,
    }
    amendment["cohort_scope"] = "Synthetic common-cohort assumption, not verified records."
    amendment["source_conflict"] = "Synthetic failed fraction retained, no repair or erratum."
    raw = tmp_path / "raw"
    raw.mkdir()
    reads = []
    readers = _readers(protocol, COUNTS, reads)
    contents = {
        "one_year": b"%PDF-synthetic-one-year",
        "two_year": b"%PDF-synthetic-two-year",
        "published_abstract": _xml(amendment),
    }
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pins, sources = {}, {}
    for label, content in contents.items():
        filename = f"synthetic-{label}." + ("xml" if label == "published_abstract" else "pdf")
        pin = {
            "url": f"https://example.org/{filename}",
            "final_url": f"https://example.org/{filename}",
            "sha256": digest(content),
            "cache_filename": filename,
            "retrieved_utc": now.isoformat(),
            "size_bytes": len(content),
            "distribution": "fetch_only",
        }
        pins[label] = pin
        sources[module.SOURCE_IDS[label]] = SimpleNamespace(
            url=pin["url"],
            sha256=pin["sha256"],
            raw_filename=filename,
            retrieved_at=now,
            doi=amendment["selection"]["article_identity"]["doi"]
            if label == "published_abstract"
            else protocol["bibliography"][label]["doi"],
        )
        (raw / filename).write_bytes(content)
    protocol["source_receipts"] = {label: pins[label] for label in ("one_year", "two_year")}
    receipts = {
        "schema": "synthetic-receipts",
        "sources": copy.deepcopy(protocol["source_receipts"]),
    }
    amendment["published_source"] = pins["published_abstract"]
    failure["counts"] = copy.deepcopy(COUNTS)
    failure["source_checks"]["same_intervention_itt_denominator"] = False
    contracts = {
        "PROTOCOL": protocol,
        "RECEIPTS": receipts,
        "AMENDMENT": amendment,
        "FAILURE": failure,
        "V2": {"scope": "Synthetic superseded selection"},
        "V2_FAILURE": {"scope": "Synthetic retained failed locator"},
    }
    paths = {}
    for name, value in contracts.items():
        path = tmp_path / f"synthetic-{name.lower()}.json"
        content = encoded(value)
        path.write_bytes(content)
        paths[name] = path
        monkeypatch.setattr(module, f"{name}_PATH", str(path))
        monkeypatch.setattr(module, f"{name}_SHA256", digest(content))
    spec = {
        "protocol_path": module.PROTOCOL_PATH,
        "receipts_path": module.RECEIPTS_PATH,
        "protocol_sha256": module.PROTOCOL_SHA256,
        "receipts_sha256": module.RECEIPTS_SHA256,
        "amendment_path": module.AMENDMENT_PATH,
        "amendment_sha256": module.AMENDMENT_SHA256,
        "failed_intake_path": module.FAILURE_PATH,
        "failed_intake_sha256": module.FAILURE_SHA256,
        "source_ids": copy.deepcopy(module.SOURCE_IDS),
        "model_role": "benchmark_only",
        "status": "derived",
        "evidence_grade": "C",
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "parameter_keys": list(module.PARAMETER_FIELDS),
        "analysis": {
            "published_intake_receipt_sha256": module.PUBLISHED_INTAKE_SHA256,
            "same_itt_scope": amendment["cohort_scope"],
            "positive_subgroup_scope": protocol["source_definition_locators"]["pair_subgroup"],
            "synthetic_software_fixture": copy.deepcopy(protocol["software_fixture"]),
        },
    }
    parameters = {}
    for key, field in module.PARAMETER_FIELDS.items():
        label = "one_year" if field == "positive_first_n" else "two_year"
        if field in ("itt_n", "positive_second_n"):
            label = "published_abstract"
        parameters[key] = SimpleNamespace(
            value=COUNTS[field],
            unresolved=False,
            unit="people",
            status="observed",
            model_role="benchmark_only",
            evidence_grade="C",
            source_id=module.SOURCE_IDS[label],
            source_url=sources[module.SOURCE_IDS[label]].url,
            uncertainty=SimpleNamespace(kind="fixed"),
            lower_bound=0,
            population="Synthetic cohort",
            geography="Synthetic geography",
            time_period="Synthetic visits",
        )
    registry = SimpleNamespace(
        datasets={module.DATASET: spec},
        sources=sources,
        parameters=parameters,
        content_hash="synthetic-registry-hash",
    )

    def reader_factory(stream, *, strict):
        assert strict is True
        content = stream.getvalue()
        for label in ("one_year", "two_year"):
            if content == contents[label]:
                return readers[label]
        raise ValueError(PRIVATE)

    monkeypatch.setattr(module, "PdfReader", reader_factory)
    return SimpleNamespace(
        registry=registry,
        spec=spec,
        raw=raw,
        contents=contents,
        paths=paths,
        protocol=protocol,
        receipts=receipts,
        amendment=amendment,
        failure=failure,
        readers=readers,
        reads=reads,
        pins=pins,
    )


def _failed(report, stage):
    assert report["source_audit_passed"] is False
    assert report["results"] is None
    assert report["clinical_fit_performed"] is False
    assert report["engine_parameters_updated"] is False
    assert report["scientific_release_ready"] is False
    assert report["failure"] == {"stage": stage, "code": "observation_contract_not_verified"}
    text = json.dumps(report, allow_nan=False)
    assert PRIVATE not in text
    assert "example.org" not in text


def test_original_frozen_selection_rejects_retained_denominator_conflict(fixture):
    with pytest.raises(ValueError, match="denominators differ"):
        module.extract_paired_counts(
            fixture.contents["one_year"], fixture.contents["two_year"], fixture.protocol
        )
    assert (
        module._extract_paired_count_literals(
            fixture.contents["one_year"], fixture.contents["two_year"], fixture.protocol
        )
        == COUNTS
    )


def test_selected_accepted_fraction_53_over_129_is_not_silently_repaired(fixture):
    # Known selected literals reproduced in a synthetic text wire, never raw source bytes.
    selected = {
        "itt_n": 149,
        "itt_n_one_year_crosscheck": 149,
        "positive_first_n": 68,
        "positive_second_n": 53,
        "positive_second_itt_denominator": 129,
        "positive_pair_lower_n": 48,
    }
    fixture.readers.update(_readers(fixture.protocol, selected, fixture.reads))
    with pytest.raises(ValueError, match="denominators differ"):
        module.extract_paired_counts(
            fixture.contents["one_year"], fixture.contents["two_year"], fixture.protocol
        )
    assert (
        module._extract_paired_count_literals(
            fixture.contents["one_year"], fixture.contents["two_year"], fixture.protocol
        )["positive_second_itt_denominator"]
        == 129
    )


def test_matching_original_denominators_are_crosschecked_without_percentage_arithmetic(fixture):
    counts = {**COUNTS, "positive_second_itt_denominator": 10}
    fixture.readers.update(_readers(fixture.protocol, counts, fixture.reads))
    assert (
        module.extract_paired_counts(
            fixture.contents["one_year"], fixture.contents["two_year"], fixture.protocol
        )
        == counts
    )


def test_amended_audit_keeps_original_failure_and_conditional_scope(fixture):
    before = {path: path.read_bytes() for path in (*fixture.paths.values(), *fixture.raw.iterdir())}
    report = module.audit_paired_remission(fixture.registry, fixture.raw)
    assert report["source_audit_passed"] is True
    results = report["results"]
    assert results["observed_counts"] == COUNTS
    assert results["published_counts"] == {
        "itt_n": 10,
        "positive_second_n": 5,
        "endpoint_specific_denominator_printed": False,
    }
    assert results["source_conflict"]["accepted_literal_fraction"] == {
        "numerator": 5,
        "denominator": 9,
    }
    assert results["source_conflict"]["original_intake_passed"] is False
    assert results["source_conflict"]["author_issued_erratum_verified"] is False
    assert results["source_conflict"]["published_endpoint_denominator_explicit"] is False
    assert results["scope_conditional"] is True
    assert results["same_itt_scope"] == fixture.amendment["cohort_scope"]
    assert results["marginals_only"]["feasible_positive_pair"] == {"lower": 0, "upper": 4}
    assert results["with_reported_positive_subgroup"]["feasible_positive_pair"] == {
        "lower": 3,
        "upper": 4,
    }
    for key in (
        "negative_assessment_partition_verified",
        "independent_evaluation",
        "clinical_retention_or_relapse_parameter_identified",
    ):
        assert results[key] is False
    assert results["diagnosed_t2d_history_retained"] is True
    assert report["clinical_fit_performed"] is False
    assert report["engine_parameters_updated"] is False
    assert report["scientific_release_ready"] is False
    assert report["provenance"]["original_failed_intake_sha256"] == module.FAILURE_SHA256
    assert set(report["provenance"]["source_bytes"]) == set(module.SOURCE_IDS)
    assert PRIVATE not in json.dumps(report, allow_nan=False)
    assert {path: path.read_bytes() for path in before} == before


def test_only_identity_and_frozen_physical_pdf_pages_are_read(fixture):
    assert module.audit_paired_remission(fixture.registry, fixture.raw)["source_audit_passed"]
    assert set(fixture.reads) == {
        ("one_year", 0),
        ("one_year", 3),
        ("two_year", 0),
        ("two_year", 10),
        ("two_year", 11),
        ("two_year", 12),
    }


@pytest.mark.parametrize("label", ("one_year", "two_year"))
@pytest.mark.parametrize("change", ("encrypted", "page_count", "doi", "title"))
def test_pdf_structure_and_identity_are_required(fixture, label, change):
    reader = fixture.readers[label]
    if change == "encrypted":
        reader.is_encrypted = True
    elif change == "page_count":
        reader.pages.pop()
    else:
        reader.pages[0].text = reader.pages[0].text.replace(
            fixture.protocol["bibliography"][label]["doi" if change == "doi" else "title_prefix"],
            PRIVATE,
        )
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "selected_counts")


@pytest.mark.parametrize("content", (b"not-pdf", b"", "%PDF-text", None, bytearray(b"%PDF-")))
def test_pdf_bytes_domain_is_strict(fixture, content):
    with pytest.raises(ValueError, match="Invalid selected PDF"):
        module._pdf(content, "one_year", fixture.protocol)


@pytest.mark.parametrize("choice", tuple(COUNTS))
@pytest.mark.parametrize("change", ("missing", "duplicate"))
def test_selected_count_anchors_must_be_unique(fixture, choice, change):
    selected_key = "itt_n_one_year_crosscheck" if choice == "itt_n_one_year_crosscheck" else choice
    if choice == "positive_second_itt_denominator":
        selected_key = "positive_second_n"
    location = fixture.protocol["selected_counts"][selected_key]
    page = fixture.readers[location["source"]].pages[location["physical_page"] - 1]
    page.text = PRIVATE if change == "missing" else page.text + " " + page.text
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "selected_counts")


@pytest.mark.parametrize(
    "field,value",
    [
        ("itt_n", 0),
        ("positive_first_n", 11),
        ("positive_second_n", 11),
        ("positive_pair_lower_n", 5),
        ("itt_n_one_year_crosscheck", 11),
    ],
)
def test_invalid_or_mismatched_source_counts_block_output(fixture, field, value):
    fixture.readers.update(_readers(fixture.protocol, {**COUNTS, field: value}, fixture.reads))
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "selected_counts")


@pytest.mark.parametrize("n,b", [(0, 0), (10, 11)])
def test_published_count_domain_is_checked(fixture, n, b):
    with pytest.raises(ValueError, match="outside valid domains"):
        module.extract_published_counts(_xml(fixture.amendment, n=n, b=b), fixture.amendment)


def test_published_abstract_extracts_only_declared_field_and_literal_counts(fixture):
    root = ET.fromstring(_xml(fixture.amendment))
    fields = root.findall("./PubmedArticle/MedlineCitation/Article/Abstract/AbstractText")
    fields[-1].text = "The intention-to-treat population consisted of 999 participants per group"
    findings = fields[1]
    findings.text = "The intention-to-treat population consisted of 10 participants per group; and "
    ET.SubElement(findings, "i").text = "5"
    findings[
        -1
    ].tail = " (unknown percentage) intervention participants and unspecified control participants had remission of diabetes"
    assert module.extract_published_counts(ET.tostring(root), fixture.amendment) == {
        "itt_n": 10,
        "positive_second_n": 5,
        "endpoint_specific_denominator_printed": False,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "root",
        "article_missing",
        "article_duplicate",
        "pmid",
        "doi",
        "doi_duplicate",
        "findings_missing",
        "findings_duplicate",
        "findings_case",
        "methods_missing",
        "methods_duplicate",
        "methods_itt_missing",
        "methods_coprimary_missing",
        "n_missing",
        "n_duplicate",
        "b_missing",
        "b_duplicate",
    ],
)
def test_published_identity_field_scope_and_count_anchors_fail_closed(fixture, mutation):
    root = ET.fromstring(_xml(fixture.amendment))
    article = root[0]
    abstract = article.find("./MedlineCitation/Article/Abstract")
    methods, findings = abstract[0], abstract[1]
    doi = article.find("./PubmedData/ArticleIdList/ArticleId")
    if mutation == "root":
        root.tag = "WrongRoot"
    elif mutation == "article_missing":
        root.remove(article)
    elif mutation == "article_duplicate":
        root.append(copy.deepcopy(article))
    elif mutation == "pmid":
        article.find("./MedlineCitation/PMID").text = PRIVATE
    elif mutation == "doi":
        doi.text = PRIVATE
    elif mutation == "doi_duplicate":
        article.find("./PubmedData/ArticleIdList").append(copy.deepcopy(doi))
    elif mutation == "findings_case":
        findings.set("Label", "Findings")
    elif (
        mutation.endswith("_missing")
        and mutation.split("_")[0] in ("findings", "methods")
        and mutation.count("_") == 1
    ):
        abstract.remove(findings if mutation.startswith("findings") else methods)
    elif mutation in ("findings_duplicate", "methods_duplicate"):
        abstract.append(copy.deepcopy(findings if mutation.startswith("findings") else methods))
    elif mutation == "methods_itt_missing":
        methods.text = methods.text.replace("intention-to-treat population", PRIVATE)
    elif mutation == "methods_coprimary_missing":
        methods.text = methods.text.replace("coprimary outcomes", PRIVATE)
    elif mutation == "n_missing":
        findings.text = findings.text.replace("10 participants per group", PRIVATE)
    elif mutation == "b_missing":
        findings.text = findings.text.replace("and 5 (", PRIVATE + " (")
    elif mutation == "n_duplicate":
        findings.text += " The intention-to-treat population consisted of 10 participants per group"
    elif mutation == "b_duplicate":
        findings.text += " and 5 (unknown) intervention participants and unspecified control participants had remission of diabetes"
    else:
        raise AssertionError("Unknown synthetic mutation")
    with pytest.raises(ValueError):
        module.extract_published_counts(ET.tostring(root), fixture.amendment)


@pytest.mark.parametrize("content", (b"", b"<broken", b"<PubmedArticleSet/>"))
def test_malformed_published_xml_does_not_succeed(fixture, content):
    with pytest.raises((ValueError, ET.ParseError)):
        module.extract_published_counts(content, fixture.amendment)


@pytest.mark.parametrize(
    "name", ("PROTOCOL", "RECEIPTS", "AMENDMENT", "FAILURE", "V2", "V2_FAILURE")
)
def test_each_frozen_contract_byte_pin_blocks_tampering(fixture, name):
    fixture.paths[name].write_bytes(b'{"untrusted":"' + PRIVATE.encode() + b'"}')
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "metadata")


@pytest.mark.parametrize(
    "name", ("PROTOCOL", "RECEIPTS", "AMENDMENT", "FAILURE", "V2", "V2_FAILURE")
)
def test_missing_frozen_contract_is_sanitized(fixture, name):
    fixture.paths[name].unlink()
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "metadata")


@pytest.mark.parametrize(
    "field",
    [
        "protocol_path",
        "receipts_path",
        "amendment_path",
        "protocol_sha256",
        "receipts_sha256",
        "amendment_sha256",
        "source_ids",
        "model_role",
        "clinical_fit_allowed",
        "engine_activation_allowed",
        "parameter_keys",
        "failed_intake_path",
        "failed_intake_sha256",
        "status",
        "evidence_grade",
        "analysis",
    ],
)
def test_registry_cannot_redirect_or_coordinately_repin_the_frozen_contract(fixture, field):
    old = fixture.spec[field]
    fixture.spec[field] = True if type(old) is bool else PRIVATE
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "metadata")


def test_duplicate_parameter_key_cannot_pass_set_only_membership_check(fixture):
    fixture.spec["parameter_keys"].append(fixture.spec["parameter_keys"][0])
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "metadata")


@pytest.mark.parametrize(
    "field",
    (
        "published_intake_receipt_sha256",
        "same_itt_scope",
        "positive_subgroup_scope",
        "synthetic_software_fixture",
    ),
)
def test_each_registered_analysis_choice_matches_frozen_selection(fixture, field):
    fixture.spec["analysis"][field] = PRIVATE
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "metadata")


def test_added_analysis_field_is_not_an_unreviewed_model_choice(fixture):
    fixture.spec["analysis"]["unreviewed_hazard"] = PRIVATE
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "metadata")


@pytest.mark.parametrize("label", tuple(module.SOURCE_IDS))
@pytest.mark.parametrize("field", ("url", "sha256", "raw_filename", "retrieved_at", "doi"))
def test_all_source_metadata_fields_are_crosschecked(fixture, label, field):
    source = fixture.registry.sources[module.SOURCE_IDS[label]]
    setattr(
        source,
        field,
        datetime(2026, 2, 1, tzinfo=timezone.utc) if field == "retrieved_at" else PRIVATE,
    )
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "source_bytes")


@pytest.mark.parametrize("label", tuple(module.SOURCE_IDS))
@pytest.mark.parametrize("change", ("missing", "same_size_change", "size_change"))
def test_all_raw_sources_require_exact_size_and_hash(fixture, label, change):
    path = fixture.raw / fixture.pins[label]["cache_filename"]
    if change == "missing":
        path.unlink()
    elif change == "same_size_change":
        original = path.read_bytes()
        path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    else:
        path.write_bytes(path.read_bytes() + b"changed")
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "source_bytes")


def test_repinning_registry_source_hash_does_not_accept_changed_bytes(fixture):
    source = fixture.registry.sources[module.SOURCE_IDS["one_year"]]
    path = fixture.raw / source.raw_filename
    path.write_bytes(path.read_bytes() + b"changed")
    source.sha256 = digest(path.read_bytes())
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "source_bytes")


@pytest.mark.parametrize("operation", ("resolve", "is_dir", "read_bytes"))
def test_unreadable_source_metadata_and_bytes_return_sanitized_failure(
    fixture, monkeypatch, operation
):
    original = getattr(Path, operation)
    source_path = fixture.raw / fixture.pins["one_year"]["cache_filename"]

    def unreadable(path, *args, **kwargs):
        if path == (fixture.raw if operation in ("resolve", "is_dir") else source_path):
            raise PermissionError(PRIVATE)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, operation, unreadable)
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "source_bytes")


def test_raw_input_must_be_a_directory(fixture):
    _failed(
        module.audit_paired_remission(fixture.registry, fixture.paths["PROTOCOL"]), "source_bytes"
    )


def test_source_symlink_cannot_escape_selected_directory(fixture, tmp_path):
    path = fixture.raw / fixture.pins["one_year"]["cache_filename"]
    content = path.read_bytes()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(content)
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Host cannot create a synthetic source symlink")
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "source_bytes")


@pytest.mark.parametrize("field,value", [("itt_n", 11), ("positive_second_n", 4)])
def test_separate_published_literal_counts_must_match_accepted_common_cohort(
    fixture, monkeypatch, field, value
):
    original = module.extract_published_counts

    def changed(*args):
        counts = original(*args)
        return {**counts, field: value}

    monkeypatch.setattr(module, "extract_published_counts", changed)
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "selected_counts")


@pytest.mark.parametrize("key", tuple(module.PARAMETER_FIELDS))
@pytest.mark.parametrize(
    "field,value",
    [
        ("value", -1),
        ("unresolved", True),
        ("unit", "per_year"),
        ("status", "derived"),
        ("model_role", "health_model"),
        ("evidence_grade", "A"),
        ("source_id", PRIVATE),
        ("source_url", PRIVATE),
        ("uncertainty", None),
        ("uncertainty", SimpleNamespace(kind="uniform")),
        ("lower_bound", -1),
        ("population", ""),
        ("geography", ""),
        ("time_period", ""),
    ],
)
def test_each_registered_count_preserves_value_role_units_status_and_source(
    fixture, key, field, value
):
    setattr(fixture.registry.parameters[key], field, value)
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "selected_counts")


def test_constraints_error_returns_no_partial_output_or_untrusted_exception(fixture, monkeypatch):
    def fail(*args):
        raise ValueError(PRIVATE)

    monkeypatch.setattr(module, "paired_remission_bounds", fail)
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "constraints")


def test_frozen_receipts_and_original_failure_semantics_are_checked_even_with_test_pins(
    fixture, monkeypatch
):
    original = module._contract

    def changed(path, expected):
        result = copy.deepcopy(original(path, expected))
        if path == module.FAILURE_PATH:
            result["source_checks"]["same_intervention_itt_denominator"] = True
        return result

    monkeypatch.setattr(module, "_contract", changed)
    _failed(module.audit_paired_remission(fixture.registry, fixture.raw), "selected_counts")


@pytest.mark.parametrize("target", ("receipts", "original_counts"))
def test_internal_receipt_and_original_literal_agreement_are_required(fixture, monkeypatch, target):
    original = module._contract

    def changed(path, expected):
        document = copy.deepcopy(original(path, expected))
        if target == "receipts" and path == module.RECEIPTS_PATH:
            document["sources"]["one_year"]["size_bytes"] += 1
        if target == "original_counts" and path == module.FAILURE_PATH:
            document["counts"]["positive_second_itt_denominator"] += 1
        return document

    monkeypatch.setattr(module, "_contract", changed)
    _failed(
        module.audit_paired_remission(fixture.registry, fixture.raw),
        "metadata" if target == "receipts" else "selected_counts",
    )


def test_no_network_or_source_text_export_is_needed(fixture, monkeypatch):
    import socket
    import urllib.request

    def no_network(*args, **kwargs):
        raise AssertionError("Network use is outside an offline source audit")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    report = module.audit_paired_remission(fixture.registry, fixture.raw)
    assert report["source_audit_passed"] is True
    assert PRIVATE not in encoded(report).decode()
    assert not any(
        "text" in key or "content" in key for key in report["provenance"]["source_bytes"]
    )


def test_real_audit_failure_is_persisted_by_cli_without_exception_path_leak(
    fixture, tmp_path, monkeypatch
):
    from typer.testing import CliRunner

    from demeter.cli import app

    monkeypatch.setattr("demeter.cli.registry", lambda _: fixture.registry)
    original = Path.resolve

    def unreadable(path, *args, **kwargs):
        if path == fixture.raw:
            raise PermissionError(PRIVATE)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", unreadable)
    output = tmp_path / "failed-report.json"
    result = CliRunner().invoke(
        app,
        [
            "evidence",
            "paired-remission",
            "--raw",
            str(fixture.raw),
            "--evidence",
            str(tmp_path / "parameters.yaml"),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 1
    _failed(json.loads(output.read_bytes()), "source_bytes")
    assert PRIVATE not in result.output
