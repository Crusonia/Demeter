"""Synthetic publication XML tests: no restricted or participant data."""

from copy import deepcopy
from hashlib import sha256
import json
import xml.etree.ElementTree as ET

import pytest

from demeter.data.malawi_cohort import (
    CAPTURE_NAMES,
    COUNT_NAMES,
    FLOAT_NAMES,
    SCIENTIFIC_GATES,
    SELECTORS,
    extract_malawi_cohort,
    normalized_source_text,
)


def fixture_publication():
    """Deliberately small synthetic cohort, with source-like XML structure."""
    values = dict.fromkeys(CAPTURE_NAMES, 1)
    values.update(
        cohort_count=30,
        traced_count=24,
        confirmed_deaths_count=15,
        assessed_count=9,
        ngt_count=4,
        ifg_count=2,
        dm_count=3,
        baseline_start_year=2000,
        baseline_end_year=2001,
        followup_start_year=2004,
        followup_end_year=2005,
    )
    values.update(dict.fromkeys(FLOAT_NAMES, 7.0))
    values.update(
        baseline_ifg_lower_mmol_l=6.1,
        followup_ifg_lower_mmol_l=6.0,
        followup_ngt_upper_mmol_l=6.0,
        followup_median_years=4.0,
        followup_iqr_lower_years=3.0,
        followup_iqr_upper_years=5.0,
        abstract_person_years=36.0,
        results_person_years=36.5,
    )
    root = ET.Element("article")
    meta = ET.SubElement(ET.SubElement(root, "front"), "article-meta")
    ET.SubElement(
        ET.SubElement(meta, "title-group"), "article-title"
    ).text = "Synthetic aggregate publication"
    ET.SubElement(meta, "article-id", {"pub-id-type": "doi"}).text = "10.example/synthetic"
    abstract = ET.SubElement(ET.SubElement(meta, "abstract"), "p")
    body = ET.SubElement(root, "body")

    def section(parent, identifier, title):
        element = ET.SubElement(parent, "sec", {"id": identifier})
        ET.SubElement(element, "title").text = title
        return element

    methods = section(body, "sec002", "Methods")
    baseline = ET.SubElement(section(methods, "sec003", "Study population"), "p")
    measures = section(methods, "sec005", "Measures")
    definition = ET.SubElement(section(measures, "sec009", "Outcome"), "p")
    results_section = section(body, "sec011", "Results")
    results = ET.SubElement(results_section, "p")
    categories = ET.SubElement(results_section, "p")
    table = ET.SubElement(results_section, "table-wrap", {"id": "pgph.0001263.t001"})
    ET.SubElement(table, "label").text = "Table 1"
    ET.SubElement(table, "object-id", {"pub-id-type": "doi"}).text = "10.example/synthetic.t001"
    caption = ET.SubElement(ET.SubElement(table, "caption"), "title")
    caption.text = "assessed_count=9"
    table_body = ET.SubElement(ET.SubElement(table, "alternatives"), "table")
    header = ET.SubElement(ET.SubElement(table_body, "thead"), "tr")
    for text in (
        "Variable",
        "n",
        "Regressed to NGT 4(44.4)",
        "Remained as IFG 2(22.2)",
        "Progressed to DM 3(33.3)",
    ):
        ET.SubElement(header, "th").text = text
        header[-1].tail = "\n"
    elements = {
        "baseline": baseline,
        "definition": definition,
        "results": results,
        "abstract": abstract,
    }
    selectors = {}
    captures = []
    for name in sorted(CAPTURE_NAMES):
        if name in {"ngt_count", "ifg_count", "dm_count"}:
            prefix = {
                "ngt_count": "Regressed to NGT",
                "ifg_count": "Remained as IFG",
                "dm_count": "Progressed to DM",
            }[name]
            selector, pattern = "table_header", prefix + r" ([0-9]+)\("
            categories.text = (categories.text or "") + f"{name}={values[name]} "
            checks = [
                {"selector": "followup_categories", "pattern": name + r"=([0-9]+)", "group": 1}
            ]
        else:
            selector = (
                "baseline"
                if name.startswith("baseline") or name == "cohort_count"
                else "definition"
                if name.startswith("followup_ifg")
                or name.startswith("followup_ngt")
                or name.startswith("followup_dm")
                else "abstract"
                if name.startswith("abstract") or "iqr" in name
                else "results"
            )
            elements[selector].text = (elements[selector].text or "") + f"{name}={values[name]} "
            pattern = name + r"=([0-9]+(?:\.[0-9]+)?)"
            checks = []
        specification = {
            "name": name,
            "selector": selector,
            "pattern": pattern,
            "group": 1,
            "type": "float" if name in FLOAT_NAMES else "int",
            "expected": values[name],
        }
        if checks:
            specification["corroboration"] = checks
        captures.append(specification)
    definition.text += "diabetes diagnosis OR current medication OR fasting glucose; fasting-only"
    content = ET.tostring(root)
    for name, xpath in SELECTORS.items():
        parent, tag = xpath.rsplit("/", 1)
        selectors[name] = {
            "xpath": xpath,
            "normalized_text_sha256": sha256(
                normalized_source_text(root.find(xpath)).encode()
            ).hexdigest(),
            "sibling_count": len(root.find(parent).findall(tag.split("[", 1)[0])),
        }
    protocol = {
        "source": {
            "sha256": sha256(content).hexdigest(),
            "size_bytes": len(content),
            "doi": "10.example/synthetic",
            "article_title": "Synthetic aggregate publication",
        },
        "scientific_gates": deepcopy(SCIENTIFIC_GATES),
        "selectors": selectors,
        "captures": captures,
    }
    return content, protocol


def reseal_source(root, protocol, *, text_selectors=()):
    """Synthetic tampering helper; unrelated paragraph pins remain unchanged."""
    content = ET.tostring(root)
    protocol["source"].update(sha256=sha256(content).hexdigest(), size_bytes=len(content))
    for name in text_selectors:
        protocol["selectors"][name]["normalized_text_sha256"] = sha256(
            normalized_source_text(root.find(SELECTORS[name])).encode()
        ).hexdigest()
    return content


def test_extract_conserves_public_partition_and_retains_discrepancies():
    content, protocol = fixture_publication()
    result = extract_malawi_cohort(content, protocol)
    assert result["observed"]["assessed_count"] == 9
    assert sum(result["observed"][name] for name in ("ngt_count", "ifg_count", "dm_count")) == 9
    assert result["derived"] == {"untraced_count": 6}
    assert result["source_discrepancies"] == {
        "ifg_lower_threshold_mmol_l": {"baseline": 6.1, "followup": 6.0},
        "person_years": {"abstract": 36.0, "results": 36.5},
    }
    assert result["scientific_gates"] == SCIENTIFIC_GATES
    assert set(result["observed"]) == CAPTURE_NAMES
    assert set(result["source_locators"]) == CAPTURE_NAMES
    result["scientific_gates"]["clinical_fit_allowed"] = True
    assert protocol["scientific_gates"]["clinical_fit_allowed"] is False


def test_source_or_fingerprint_failure_does_not_print_content():
    content, protocol = fixture_publication()
    with pytest.raises(ValueError, match="source hash") as error:
        extract_malawi_cohort(content.replace(b"OR current", b"NO current"), protocol)
    assert "current" not in str(error.value)


@pytest.mark.parametrize(
    "mutation",
    [
        "title",
        "doi",
        "duplicate_doi",
        "section_title",
        "duplicate_section",
        "wrong_parent",
        "duplicate_paragraph",
        "definition",
        "header_label",
        "table_label",
        "table_doi",
        "duplicate_table",
        "duplicate_column",
        "reordered_columns",
    ],
)
def test_semantic_structure_failures_with_resealed_bytes(mutation):
    content, protocol = fixture_publication()
    root = ET.fromstring(content)
    if mutation == "title":
        root.find(".//article-title").text = "wrong source"
    elif mutation == "doi":
        root.find("./front/article-meta/article-id").text = "wrong DOI"
    elif mutation == "duplicate_doi":
        root.find("./front/article-meta").append(
            deepcopy(root.find("./front/article-meta/article-id"))
        )
    elif mutation == "section_title":
        root.find(".//sec[@id='sec009']/title").text = "wrong section"
    elif mutation == "duplicate_section":
        root.find("./body").append(deepcopy(root.find(".//sec[@id='sec009']")))
    elif mutation == "wrong_parent":
        definition = root.find(".//sec[@id='sec009']")
        root.find(".//sec[@id='sec005']").remove(definition)
        root.find("./body").append(definition)
    elif mutation == "duplicate_paragraph":
        root.find(".//sec[@id='sec003']").append(deepcopy(root.find(SELECTORS["baseline"])))
    elif mutation == "definition":
        root.find(SELECTORS["definition"]).text = root.find(SELECTORS["definition"]).text.replace(
            "OR current", "AND current"
        )
    elif mutation in {"header_label", "duplicate_column", "reordered_columns"}:
        header = root.find(SELECTORS["table_header"])
        if mutation == "header_label":
            header[2].text = header[2].text.replace("NGT", "healthy")
        elif mutation == "duplicate_column":
            header.append(deepcopy(header[2]))
        else:
            header[2], header[3] = header[3], header[2]
    else:
        table = root.find(".//table-wrap")
        if mutation == "table_label":
            table.find("label").text = "Table 2"
        elif mutation == "table_doi":
            table.find("object-id").text = "wrong table DOI"
        else:
            root.find(".//sec[@id='sec011']").append(deepcopy(table))
    resealed = reseal_source(root, protocol)
    with pytest.raises(ValueError, match="Malawi source extraction failed"):
        extract_malawi_cohort(resealed, protocol)


def test_reordered_category_columns_rejected_even_with_resealed_text():
    content, protocol = fixture_publication()
    root = ET.fromstring(content)
    header = root.find(SELECTORS["table_header"])
    header[2], header[3] = header[3], header[2]
    content = reseal_source(root, protocol, text_selectors=("table_header",))
    with pytest.raises(ValueError, match="required category column"):
        extract_malawi_cohort(content, protocol)


def test_same_concatenated_header_cannot_hide_wrong_column_structure():
    content, protocol = fixture_publication()
    root = ET.fromstring(content)
    header = root.find(SELECTORS["table_header"])
    original_text = normalized_source_text(header)
    header[2].text += "\n" + header[3].text
    header.remove(header[3])
    assert normalized_source_text(header) == original_text
    content = reseal_source(root, protocol)
    with pytest.raises(ValueError, match="header structure"):
        extract_malawi_cohort(content, protocol)


def test_repeated_numeric_locator_in_selected_paragraph_is_ambiguous():
    content, protocol = fixture_publication()
    root = ET.fromstring(content)
    results = root.find(SELECTORS["results"])
    results.text += " traced_count=24"
    content = reseal_source(root, protocol, text_selectors=("results",))
    with pytest.raises(ValueError, match="capture specification"):
        extract_malawi_cohort(content, protocol)


@pytest.mark.parametrize("case", ["categories", "traced", "original", "iqr", "years"])
def test_consistency_guards_independent_of_protocol_expected_values(case):
    content, protocol = fixture_publication()
    root = ET.fromstring(content)
    name, value = {
        "categories": ("assessed_count", 10),
        "traced": ("traced_count", 25),
        "original": ("cohort_count", 23),
        "iqr": ("followup_iqr_lower_years", 6.0),
        "years": ("baseline_end_year", 1999),
    }[case]
    specification = next(c for c in protocol["captures"] if c["name"] == name)
    selector = specification["selector"]
    element = root.find(SELECTORS[selector])
    element.text = element.text.replace(f"{name}={specification['expected']}", f"{name}={value}")
    specification["expected"] = value
    content = reseal_source(root, protocol, text_selectors=(selector,))
    with pytest.raises(ValueError, match="Malawi source extraction failed"):
        extract_malawi_cohort(content, protocol)


def test_corroborating_source_paragraph_must_agree():
    content, protocol = fixture_publication()
    root = ET.fromstring(content)
    root.find(SELECTORS["followup_categories"]).text = "ngt_count=5 ifg_count=2 dm_count=3"
    content = reseal_source(root, protocol, text_selectors=("followup_categories",))
    with pytest.raises(ValueError, match="corroboration disagrees"):
        extract_malawi_cohort(content, protocol)


def test_word_number_capture_is_explicit_and_bounded():
    content, protocol = fixture_publication()
    root = ET.fromstring(content)
    results = root.find(SELECTORS["results"])
    results.text = results.text.replace("confirmed_deaths_count=15", "Fifteen confirmed deaths")
    capture = next(c for c in protocol["captures"] if c["name"] == "confirmed_deaths_count")
    capture["pattern"] = r"(Fifteen) confirmed deaths"
    content = reseal_source(root, protocol, text_selectors=("results",))
    assert extract_malawi_cohort(content, protocol)["observed"]["confirmed_deaths_count"] == 15
    results.text = results.text.replace("Fifteen", "Undocumented")
    content = reseal_source(root, protocol, text_selectors=("results",))
    with pytest.raises(ValueError):
        extract_malawi_cohort(content, protocol)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_capture",
        "duplicate_capture",
        "extra_capture",
        "wrong_type",
        "boolean_count",
        "bad_regex",
        "bad_group",
        "wrong_selector",
        "selector_ancestry",
        "empty_gates",
        "open_gate",
        "boolean_size",
        "wrong_size",
    ],
)
def test_protocol_failures_are_closed_and_sanitized(mutation):
    content, protocol = fixture_publication()
    capture = next(c for c in protocol["captures"] if c["name"] in COUNT_NAMES)
    if mutation == "missing_capture":
        protocol["captures"].pop()
    elif mutation == "duplicate_capture":
        protocol["captures"].append(deepcopy(capture))
    elif mutation == "extra_capture":
        extra = deepcopy(capture)
        extra["name"] = "individual_values"
        protocol["captures"].append(extra)
    elif mutation == "wrong_type":
        capture["type"] = "float"
    elif mutation == "boolean_count":
        capture["expected"] = True
    elif mutation == "bad_regex":
        capture["pattern"] = "(secret free text"
    elif mutation == "bad_group":
        capture["group"] = "secret free text"
    elif mutation == "wrong_selector":
        capture["selector"] = "secret free text"
    elif mutation == "selector_ancestry":
        protocol["selectors"]["baseline"]["xpath"] = ".//p"
    elif mutation == "empty_gates":
        protocol["scientific_gates"] = {}
    elif mutation == "open_gate":
        protocol["scientific_gates"]["clinical_fit_allowed"] = True
    elif mutation == "boolean_size":
        protocol["source"]["size_bytes"] = True
    else:
        protocol["source"]["size_bytes"] -= 1
    with pytest.raises(ValueError, match="Malawi source extraction failed") as error:
        extract_malawi_cohort(content, protocol)
    assert "secret" not in str(error.value)
    assert "individual_values" not in str(error.value)


@pytest.mark.parametrize(
    "content",
    [
        b"<secret malformed",
        b"<!DOCTYPE article [<!ENTITY private 'secret'>]><article>&private;</article>",
    ],
)
def test_malformed_or_entity_xml_is_sanitized(content):
    _, protocol = fixture_publication()
    protocol["source"].update(sha256=sha256(content).hexdigest(), size_bytes=len(content))
    with pytest.raises(ValueError, match="Malawi source extraction failed") as error:
        extract_malawi_cohort(content, protocol)
    assert "secret" not in str(error.value)


def test_result_has_only_selected_public_numbers_provenance_and_closed_gates():
    content, protocol = fixture_publication()
    serialized = json.dumps(extract_malawi_cohort(content, protocol))
    for forbidden in (
        "participant_id",
        "hazard",
        "annual_rate",
        "clinical_state",
        "medication_status",
        "diagnosis_time",
    ):
        assert forbidden not in serialized
