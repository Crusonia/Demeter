"""Source-linked paired DiRECT observations, with incomplete outcomes preserved.

The feasible sets describe source labels, not clinical hazards. Full publications
are checked read-only in an ignored fetch-only directory; no records are imported.
"""

from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader

from demeter.analysis.paired_remission import paired_remission_bounds
from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

DATASET = "direct_paired_observations"
PROTOCOL_PATH = "docs/validation/direct-paired-observations-protocol-v1.json"
RECEIPTS_PATH = "docs/validation/direct-paired-source-receipts-v1.json"
PROTOCOL_SHA256 = "4fd142053514f20bf9649d3faf8fb8c9ebb23d9eac7c26f5c8055f064ca45ab6"
RECEIPTS_SHA256 = "8b248316a7c5b0736f87ab3a52f0ed7d6a31c6c40f91bcdb7fc463055c3709d1"
AMENDMENT_PATH = "docs/validation/direct-paired-observations-amendment-v3.json"
AMENDMENT_SHA256 = "9a46a50b9d6fb08260fd7f0591a53096249bbfac2a3a92bef27ad7ad4732029b"
FAILURE_PATH = "docs/validation/direct-paired-failed-intake-v1.json"
FAILURE_SHA256 = "90eebf7c8f0e3aecb3f952c4e085abe8b9f457ba60b9003a6c62b0fa62a7e2b7"
V2_PATH = "docs/validation/direct-paired-observations-amendment-v2.json"
V2_SHA256 = "b17d036e8391688023ebbc97445ea955b881537fbd0c90bed8e4b1d4510cbd5b"
V2_FAILURE_PATH = "docs/validation/direct-paired-amendment-v2-failure.json"
V2_FAILURE_SHA256 = "2978dc8ca391a720473781833f11296fe1a3a18ef76cc2b51085b293083d1d10"
PUBLISHED_INTAKE_SHA256 = "e814916728fb5c0db22bb21ea6b9b57212ee637f70c5d8c72f6cbd3ea332b83c"
SOURCE_IDS = {
    "one_year": "direct_one_year_accepted",
    "two_year": "direct_two_year_accepted",
    "published_abstract": "direct_two_year_pubmed",
}
PARAMETER_FIELDS = {
    "direct_intervention_itt_n": "itt_n",
    "direct_intervention_positive_first_n": "positive_first_n",
    "direct_intervention_positive_second_n": "positive_second_n",
    "direct_intervention_positive_pair_subgroup_n": "positive_pair_lower_n",
    "direct_accepted_second_literal_denominator_n": "positive_second_itt_denominator",
}


def _text(text: str) -> str:
    return re.sub(r"(?<=-)\s+", "", " ".join(text.split()))


def _match(pattern: str, text: str) -> tuple[int, ...]:
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError("Selected count anchor missing or ambiguous")
    return tuple(int(value) for value in matches[0].groups())


def _pdf(content: bytes, label: str, protocol: dict) -> PdfReader:
    if type(content) is not bytes or not content.startswith(b"%PDF-"):
        raise ValueError("Invalid selected PDF")
    spec = protocol["bibliography"][label]
    reader = PdfReader(io.BytesIO(content), strict=True)
    if reader.is_encrypted or len(reader.pages) != spec["physical_pages"]:
        raise ValueError("Selected PDF structure differs")
    identity = _text(reader.pages[0].extract_text()).lower()
    if spec["doi"].lower() not in identity or spec["title_prefix"].lower() not in identity:
        raise ValueError("Selected publication identity differs")
    return reader


def _extract_paired_count_literals(
    one_year_pdf: bytes, two_year_pdf: bytes, protocol: dict
) -> dict:
    """Only frozen intervention counts; no percentages, effects or relapse counts."""
    first = _pdf(one_year_pdf, "one_year", protocol)
    second = _pdf(two_year_pdf, "two_year", protocol)
    choices = protocol["selected_counts"]
    texts = {}
    for key, choice in choices.items():
        reader = first if choice["source"] == "one_year" else second
        texts[key] = _text(reader.pages[choice["physical_page"] - 1].extract_text())
    (n,) = _match(
        r"intention-to-treat population comprised ([0-9]+) participants per group",
        texts["itt_n"],
    )
    (cross,) = _match(
        r"([0-9]+) participants per group comprised the intention-to-treat population",
        texts["itt_n_one_year_crosscheck"],
    )
    first_text = texts["positive_first_n"]
    if (
        first_text.count("Findings:") != 1
        or first_text.count("Diabetes remission was achieved in") != 1
    ):
        raise ValueError("First remission source section differs")
    (a,) = _match(
        r"Diabetes remission was achieved in ([0-9]+) \([^)]*\) participants in the intervention group",
        first_text[first_text.index("Findings:") :],
    )
    b, denominator = _match(
        r"At 24 months, without imputing missing data and assuming no remission for those without data, "
        r"diabetes was in remission in ([0-9]+)/([0-9]+) \([^)]*\) participants in the intervention group",
        texts["positive_second_n"],
    )
    (m,) = _match(
        r"In the intervention group, those maintaining remission between 12 and 24 months \(n=([0-9]+)\)",
        texts["positive_pair_lower_n"],
    )
    if n <= 0 or not (0 <= a <= n and 0 <= b <= n and 0 <= m <= min(a, b)):
        raise ValueError("Source observation counts outside valid domains")
    return {
        "itt_n": n,
        "itt_n_one_year_crosscheck": cross,
        "positive_first_n": a,
        "positive_second_n": b,
        "positive_second_itt_denominator": denominator,
        "positive_pair_lower_n": m,
    }


def extract_paired_counts(one_year_pdf: bytes, two_year_pdf: bytes, protocol: dict) -> dict:
    """Original frozen selection: conflicting endpoint denominator must fail."""
    counts = _extract_paired_count_literals(one_year_pdf, two_year_pdf, protocol)
    if (
        not counts["itt_n"]
        == counts["itt_n_one_year_crosscheck"]
        == counts["positive_second_itt_denominator"]
    ):
        raise ValueError("Cross-report intervention denominators differ")
    return counts


def extract_published_counts(content: bytes, amendment: dict) -> dict:
    """Separate literal ITT N and remission numerator; no published fraction exists."""
    root = ET.fromstring(content)
    articles = root.findall("./PubmedArticle")
    if root.tag != "PubmedArticleSet" or len(articles) != 1:
        raise ValueError("Published record article identity differs")
    article = articles[0]
    identity = amendment["selection"]["article_identity"]
    if article.findtext("./MedlineCitation/PMID") != identity["pmid"] or [
        node.text for node in article.findall("./PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
    ] != [identity["doi"]]:
        raise ValueError("Published record DOI/PMID differs")
    fields = article.findall("./MedlineCitation/Article/Abstract/AbstractText[@Label='FINDINGS']")
    methods = article.findall("./MedlineCitation/Article/Abstract/AbstractText[@Label='METHODS']")
    if len(fields) != 1 or len(methods) != 1:
        raise ValueError("Published abstract field missing or ambiguous")
    method = _text("".join(methods[0].itertext())).lower()
    if "intention-to-treat population" not in method or "coprimary outcomes" not in method:
        raise ValueError("Published primary-outcome scope not stated")
    text = _text("".join(fields[0].itertext()))
    (n,) = _match(
        r"The intention-to-treat population consisted of ([0-9]+) participants per group", text
    )
    (b,) = _match(
        r"and ([0-9]+) \([^)]*\) intervention participants and [^;]*? control participants had remission of diabetes",
        text,
    )
    if n <= 0 or not 0 <= b <= n:
        raise ValueError("Published counts outside valid domains")
    return {"itt_n": n, "positive_second_n": b, "endpoint_specific_denominator_printed": False}


def _contract(path: str, expected: str) -> dict:
    content = Path(path).read_bytes()
    if digest(content) != expected:
        raise ValueError("Frozen observation contract differs")
    document = json.loads(content)
    if type(document) is not dict:
        raise ValueError("Invalid observation contract")
    return document


def audit_paired_remission(registry: EvidenceRegistry, raw: Path) -> dict:
    """Save only aggregates and sanitized failure stages; never fit a rate."""
    stage = "metadata"
    report = {
        "schema": "direct-paired-observations-report-v1",
        "source_audit_passed": False,
        "model_role": "benchmark_only",
        "clinical_fit_performed": False,
        "engine_parameters_updated": False,
        "scientific_release_ready": False,
        "status": "Source-label observation constraints only; clinical hazards remain unresolved",
        "results": None,
    }
    try:
        spec = registry.datasets[DATASET]
        if (
            spec["protocol_path"] != PROTOCOL_PATH
            or spec["receipts_path"] != RECEIPTS_PATH
            or spec["protocol_sha256"] != PROTOCOL_SHA256
            or spec["receipts_sha256"] != RECEIPTS_SHA256
            or spec["amendment_path"] != AMENDMENT_PATH
            or spec["amendment_sha256"] != AMENDMENT_SHA256
            or spec["failed_intake_path"] != FAILURE_PATH
            or spec["failed_intake_sha256"] != FAILURE_SHA256
            or spec["source_ids"] != SOURCE_IDS
            or spec["status"] != "derived"
            or spec["evidence_grade"] != "C"
            or spec["model_role"] != "benchmark_only"
            or spec["clinical_fit_allowed"] is not False
            or spec["engine_activation_allowed"] is not False
            or set(spec["parameter_keys"]) != set(PARAMETER_FIELDS)
            or len(spec["parameter_keys"]) != len(PARAMETER_FIELDS)
        ):
            raise ValueError("Observation registry contract differs")
        protocol = _contract(PROTOCOL_PATH, PROTOCOL_SHA256)
        receipts = _contract(RECEIPTS_PATH, RECEIPTS_SHA256)
        amendment = _contract(AMENDMENT_PATH, AMENDMENT_SHA256)
        original_failure = _contract(FAILURE_PATH, FAILURE_SHA256)
        _contract(V2_PATH, V2_SHA256)
        _contract(V2_FAILURE_PATH, V2_FAILURE_SHA256)
        expected_analysis = {
            "published_intake_receipt_sha256": PUBLISHED_INTAKE_SHA256,
            "same_itt_scope": amendment["cohort_scope"],
            "positive_subgroup_scope": protocol["source_definition_locators"]["pair_subgroup"],
            "synthetic_software_fixture": protocol["software_fixture"],
        }
        if encoded(spec["analysis"]) != encoded(expected_analysis):
            raise ValueError("Registered observation analysis differs")
        if encoded(receipts["sources"]) != encoded(protocol["source_receipts"]):
            raise ValueError("Observation source receipts differ")
        stage = "source_bytes"
        source_bytes, checked = {}, {}
        directory = raw.resolve(strict=True)
        if not directory.is_dir():
            raise ValueError("Expected source directory")
        for label, key in SOURCE_IDS.items():
            source = registry.sources[key]
            pin = (
                amendment["published_source"]
                if label == "published_abstract"
                else receipts["sources"][label]
            )
            if (
                source.url != pin["url"]
                or source.sha256 != pin["sha256"]
                or source.raw_filename != pin["cache_filename"]
                or source.retrieved_at.isoformat() != pin["retrieved_utc"]
                or source.doi
                != (
                    amendment["selection"]["article_identity"]["doi"]
                    if label == "published_abstract"
                    else protocol["bibliography"][label]["doi"]
                )
            ):
                raise ValueError("Observation source metadata differs")
            path = (directory / source.raw_filename).resolve(strict=True)
            if not path.is_relative_to(directory):
                raise ValueError("Source file escapes selected directory")
            content = path.read_bytes()
            if len(content) != pin["size_bytes"] or digest(content) != pin["sha256"]:
                raise ValueError("Source bytes differ")
            source_bytes[label] = content
            checked[label] = {"sha256": source.sha256, "size_bytes": len(content)}
        stage = "selected_counts"
        counts = _extract_paired_count_literals(
            source_bytes["one_year"], source_bytes["two_year"], protocol
        )
        if encoded(counts) != encoded(original_failure["counts"]):
            raise ValueError("Original failed intake was not preserved")
        published = extract_published_counts(source_bytes["published_abstract"], amendment)
        if not (
            published["itt_n"] == counts["itt_n"] == counts["itt_n_one_year_crosscheck"]
            and published["positive_second_n"] == counts["positive_second_n"]
            and original_failure["source_checks"]["same_intervention_itt_denominator"] is False
        ):
            raise ValueError("Published/common-cohort source selection differs")
        for key, field in PARAMETER_FIELDS.items():
            parameter = registry.parameters[key]
            label = "one_year" if field == "positive_first_n" else "two_year"
            if field in ("itt_n", "positive_second_n"):
                label = "published_abstract"
            if (
                parameter.value != counts[field]
                or parameter.unresolved
                or parameter.unit != "people"
                or parameter.status != "observed"
                or parameter.model_role != "benchmark_only"
                or parameter.evidence_grade != "C"
                or parameter.source_id != SOURCE_IDS[label]
                or parameter.source_url != registry.sources[SOURCE_IDS[label]].url
                or parameter.uncertainty is None
                or parameter.uncertainty.kind != "fixed"
                or parameter.lower_bound != 0
                or not all((parameter.population, parameter.geography, parameter.time_period))
            ):
                raise ValueError("Registered observation count differs")
        stage = "constraints"
        n, a, b, m = (
            counts[key]
            for key in ("itt_n", "positive_first_n", "positive_second_n", "positive_pair_lower_n")
        )
        results = {
            "observed_counts": counts,
            "published_counts": published,
            "source_conflict": {
                "original_intake_passed": False,
                "accepted_literal_fraction": {
                    "numerator": counts["positive_second_n"],
                    "denominator": counts["positive_second_itt_denominator"],
                },
                "published_endpoint_denominator_explicit": False,
                "author_issued_erratum_verified": False,
                "disposition": amendment["source_conflict"],
            },
            "same_itt_scope": amendment["cohort_scope"],
            "scope_conditional": True,
            "marginals_only": paired_remission_bounds(n, a, b),
            "with_reported_positive_subgroup": paired_remission_bounds(n, a, b, m),
            "subgroup_assumption": protocol["feasible_set"]["conditional_subgroup_constraint"],
            "subgroup_scope_caveat": protocol["source_definition_locators"]["pair_subgroup"],
            "uncertainty": protocol["feasible_set"]["uncertainty"],
            "negative_assessment_partition_verified": False,
            "independent_evaluation": False,
            "diagnosed_t2d_history_retained": True,
            "clinical_retention_or_relapse_parameter_identified": False,
        }
        provenance = {
            "protocol_sha256": PROTOCOL_SHA256,
            "receipts_sha256": RECEIPTS_SHA256,
            "amendment_sha256": AMENDMENT_SHA256,
            "original_failed_intake_sha256": FAILURE_SHA256,
            "superseded_v2_sha256": V2_SHA256,
            "v2_locator_failure_sha256": V2_FAILURE_SHA256,
            "source_bytes": checked,
            "registry_sha256": registry.content_hash,
            "reader": "pypdf.PdfReader read-only selected physical pages",
            "extractor_sha256": digest(Path(__file__).read_bytes()),
            "constraints_sha256": digest(
                Path(__file__).with_name("paired_remission.py").read_bytes()
            ),
            "chronology": protocol["chronology"],
            "amendment_chronology": amendment["chronology"],
            "participant_records_used": False,
            "network_used": False,
        }
        report.update(source_audit_passed=True, results=results, provenance=provenance)
    except Exception:
        # Source text, untrusted filenames and participant material never enter a failure receipt.
        report["failure"] = {"stage": stage, "code": "observation_contract_not_verified"}
    return report
