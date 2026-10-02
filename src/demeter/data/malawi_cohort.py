"""Pinned public Malawi cohort facts; no individual data or latent-state mapping.

I-01/I-05/I-07/I-11/I-12 -> F-04/F-08 -> T-05/T-08. The source is an
observational fasting-glucose cohort with variable follow-up and incomplete tracing.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import math
import re
import xml.etree.ElementTree as ET


SCIENTIFIC_GATES = {
    "clinical_fit_allowed": False,
    "engine_activation_allowed": False,
    "independent_validation_allowed": False,
    "scientific_release_ready": False,
}
SELECTORS = {
    "baseline": "./body/sec[@id='sec002']/sec[@id='sec003']/p[1]",
    "definition": "./body/sec[@id='sec002']/sec[@id='sec005']/sec[@id='sec009']/p[1]",
    "results": "./body/sec[@id='sec011']/p[1]",
    "followup_categories": "./body/sec[@id='sec011']/p[2]",
    "abstract": "./front/article-meta/abstract/p[1]",
    "table_caption": "./body/sec[@id='sec011']/table-wrap[@id='pgph.0001263.t001']/caption/title",
    "table_header": "./body/sec[@id='sec011']/table-wrap[@id='pgph.0001263.t001']/alternatives/table/thead/tr",
}
SECTION_TITLES = {
    "sec002": "Methods",
    "sec003": "Study population",
    "sec005": "Measures",
    "sec009": "Outcome",
    "sec011": "Results",
}
COUNT_NAMES = {
    "cohort_count",
    "traced_count",
    "confirmed_deaths_count",
    "assessed_count",
    "ngt_count",
    "ifg_count",
    "dm_count",
}
FLOAT_NAMES = {
    "baseline_ifg_lower_mmol_l",
    "baseline_ifg_upper_mmol_l",
    "followup_ifg_lower_mmol_l",
    "followup_ifg_upper_mmol_l",
    "followup_ngt_upper_mmol_l",
    "followup_dm_lower_mmol_l",
    "followup_median_years",
    "followup_iqr_lower_years",
    "followup_iqr_upper_years",
    "abstract_person_years",
    "results_person_years",
}
YEAR_NAMES = {
    "baseline_start_year",
    "baseline_end_year",
    "followup_start_year",
    "followup_end_year",
}
CAPTURE_NAMES = COUNT_NAMES | FLOAT_NAMES | YEAR_NAMES
NUMBER_WORDS = {"seven": "7", "Fifteen": "15", "Forty-five": "45"}


def normalized_source_text(element: ET.Element) -> str:
    """Normalize XML whitespace only, preserving source words, punctuation and units."""
    return " ".join("".join(element.itertext()).split())


def _fail(reason: str) -> None:
    # Never include source content, regex captures or caller-provided text in errors.
    raise ValueError(f"Malawi source extraction failed: {reason}")


def _unique(root: ET.Element, xpath: str) -> ET.Element:
    matches = root.findall(xpath)
    if len(matches) != 1:
        _fail("locator is missing or nonunique")
    return matches[0]


def _capture(text: str, specification: dict, kind: str) -> int | float:
    try:
        matches = list(re.finditer(specification["pattern"], text))
        if len(matches) != 1:
            _fail("numeric locator is missing or nonunique")
        token = matches[0].group(specification["group"])
        token = NUMBER_WORDS.get(token, token)
        if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", token) is None:
            _fail("numeric token is unsupported")
        if kind == "int":
            if "." in token:
                _fail("count or calendar year is not integral")
            return int(token)
        number = float(token)
        if not math.isfinite(number):
            _fail("numeric token is nonfinite")
        return number
    except (KeyError, TypeError, IndexError, re.error, OverflowError, ValueError):
        _fail("capture specification is invalid")


def extract_malawi_cohort(content: bytes, protocol: dict) -> dict:
    """Extract the protocol's selected publication aggregates, failing closed.

    Only source XML bytes are accepted. The caller must separately bind the protocol
    to the evidence registry. Returning a count does not authorize a clinical fit.
    """
    if type(content) is not bytes or type(protocol) is not dict:
        _fail("input types are invalid")
    try:
        source = protocol["source"]
        gates = protocol["scientific_gates"]
        if type(gates) is not dict or set(gates) != set(SCIENTIFIC_GATES):
            _fail("scientific gates are invalid")
        if any(value is not False for value in gates.values()):
            _fail("scientific gates must remain closed")
        if type(source["size_bytes"]) is not int or len(content) != source["size_bytes"]:
            _fail("source size does not match its pin")
        digest = sha256(content).hexdigest()
        if digest != source["sha256"]:
            _fail("source hash does not match its pin")
        # JATS declares an external DTD. ElementTree does not fetch it. Internal
        # entities are unnecessary for this source and forbidden before parsing.
        if re.search(rb"<!ENTITY\b", content, re.IGNORECASE):
            _fail("XML entity declarations are forbidden")
        root = ET.fromstring(content)
        if root.tag != "article":
            _fail("document is not a primary article")
        if (
            normalized_source_text(_unique(root, "./front/article-meta/title-group/article-title"))
            != source["article_title"]
        ):
            _fail("primary article title does not match")
        if (
            normalized_source_text(
                _unique(root, "./front/article-meta/article-id[@pub-id-type='doi']")
            )
            != source["doi"]
        ):
            _fail("primary article DOI does not match")
        for section_id, title in SECTION_TITLES.items():
            section = _unique(root, f".//sec[@id='{section_id}']")
            if normalized_source_text(_unique(section, "./title")) != title:
                _fail("source section title does not match")
        table = _unique(root, ".//table-wrap[@id='pgph.0001263.t001']")
        if normalized_source_text(_unique(table, "./label")) != "Table 1":
            _fail("source table label does not match")
        if (
            normalized_source_text(_unique(table, "./object-id[@pub-id-type='doi']"))
            != source["doi"] + ".t001"
        ):
            _fail("source table DOI does not match")
        selectors = protocol["selectors"]
        if type(selectors) is not dict or set(selectors) != set(SELECTORS):
            _fail("selector scope is invalid")
        texts = {}
        for name, xpath in SELECTORS.items():
            specification = selectors[name]
            if specification["xpath"] != xpath:
                _fail("selector ancestry does not match")
            text = normalized_source_text(_unique(root, xpath))
            if sha256(text.encode()).hexdigest() != specification["normalized_text_sha256"]:
                _fail("selected source text does not match")
            parent_xpath, final_tag = xpath.rsplit("/", 1)
            parent = _unique(root, parent_xpath)
            tag = final_tag.split("[", 1)[0]
            if (
                type(specification["sibling_count"]) is not int
                or len(parent.findall(tag)) != specification["sibling_count"]
            ):
                _fail("selected locator sibling count does not match")
            texts[name] = text
        # Independently enforce the selected table's column structure, not merely
        # a concatenated string that could move values to an unrelated column.
        header = _unique(root, SELECTORS["table_header"])
        columns = header.findall("th")
        if len(columns) != 5 or [normalized_source_text(x) for x in columns[:2]] != [
            "Variable",
            "n",
        ]:
            _fail("table header structure does not match")
        captures = protocol["captures"]
        if type(captures) is not list or any(type(item) is not dict for item in captures):
            _fail("capture scope is invalid")
        names = [item["name"] for item in captures]
        if len(names) != len(set(names)) or set(names) != CAPTURE_NAMES:
            _fail("capture names are missing, repeated or out of scope")
        observed, locators = {}, {}
        for specification in captures:
            name = specification["name"]
            kind = "float" if name in FLOAT_NAMES else "int"
            expected = specification["expected"]
            if specification["type"] != kind or type(expected) is not (
                float if kind == "float" else int
            ):
                _fail("capture type is invalid")
            selector = specification["selector"]
            if selector not in SELECTORS:
                _fail("capture selector is out of scope")
            value = _capture(texts[selector], specification, kind)
            if value != expected:
                _fail("observed value does not match its protocol")
            observed[name] = value
            locators[name] = SELECTORS[selector]
            for check in specification.get("corroboration", []):
                if check["selector"] not in SELECTORS:
                    _fail("corroboration selector is out of scope")
                if _capture(texts[check["selector"]], check, kind) != value:
                    _fail("source corroboration disagrees")
        for column, name, prefix in zip(
            columns[2:],
            ("ngt_count", "ifg_count", "dm_count"),
            ("Regressed to NGT", "Remained as IFG", "Progressed to DM"),
            strict=True,
        ):
            if (
                re.fullmatch(
                    re.escape(prefix) + rf" {observed[name]}\([0-9]+(?:\.[0-9]+)?\)",
                    normalized_source_text(column),
                )
                is None
            ):
                _fail("table count is not in the required category column")
        if (
            sum(observed[name] for name in ("ngt_count", "ifg_count", "dm_count"))
            != observed["assessed_count"]
        ):
            _fail("observed categories do not conserve assessed participants")
        if (
            observed["assessed_count"] + observed["confirmed_deaths_count"]
            != observed["traced_count"]
        ):
            _fail("traced participants do not conserve observed and dead counts")
        untraced = observed["cohort_count"] - observed["traced_count"]
        if untraced < 0:
            _fail("traced count exceeds original cohort")
        if (
            not observed["followup_iqr_lower_years"]
            <= observed["followup_median_years"]
            <= observed["followup_iqr_upper_years"]
        ):
            _fail("follow-up summary order is invalid")
        for prefix in ("baseline", "followup"):
            if observed[f"{prefix}_start_year"] > observed[f"{prefix}_end_year"]:
                _fail("calendar period order is invalid")
        return {
            "source_sha256": digest,
            "source_size_bytes": len(content),
            "doi": source["doi"],
            "observed": observed,
            "derived": {"untraced_count": untraced},
            "source_locators": locators,
            "source_discrepancies": {
                "ifg_lower_threshold_mmol_l": {
                    "baseline": observed["baseline_ifg_lower_mmol_l"],
                    "followup": observed["followup_ifg_lower_mmol_l"],
                },
                "person_years": {
                    "abstract": observed["abstract_person_years"],
                    "results": observed["results_person_years"],
                },
            },
            "scientific_gates": deepcopy(SCIENTIFIC_GATES),
        }
    except (KeyError, TypeError, IndexError, AttributeError, ET.ParseError, SyntaxError):
        _fail("protocol or XML structure is invalid")
