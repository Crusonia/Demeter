"""Pinned ARIC publication counts, preserving selection and endpoint distinctions.

I-01/I-05/I-07/I-11/I-12 -> F-04/F-08 -> T-05/T-08. Two assay panels
describe overlapping participants; they are not independent samples or latent-state
transitions. No individual records, uniform horizon, fit or derived model is returned.
"""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import math
import re
import xml.etree.ElementTree as ET

import pypdf


DOI = "10.1001/jamainternmed.2020.8774"
PMID = "33555311"
SCIENTIFIC_GATES = {
    "clinical_fit_allowed": False,
    "engine_activation_allowed": False,
    "independent_validation_allowed": False,
    "scientific_release_ready": False,
}
PANELS = ("a1c_normal", "a1c_prediabetes", "fg_normal", "fg_prediabetes")
COLUMNS = (
    "baseline_count",
    "followup_normal_count",
    "followup_prediabetes_count",
    "displayed_diabetes_count",
    "displayed_mortality_count",
)
PDF_COUNTS = {
    "original_analytic_count",
    "attended_visit6_count",
    "alive_nonattender_count",
    "died_before_visit6_count",
    "selected_count",
} | {f"{panel}_{column}" for panel in PANELS for column in COLUMNS}
XML_COUNTS = {
    "original_a1c_prediabetes_count",
    "original_fg_prediabetes_count",
    "original_either_prediabetes_count",
    "original_both_prediabetes_count",
    "cumulative_total_diabetes_count",
    "cumulative_mortality_count",
}
PERCENTAGES = {
    "a1c_prediabetes_lower",
    "a1c_prediabetes_upper",
    "diabetes_a1c_threshold",
}
GLUCOSE = {"fg_prediabetes_lower", "fg_prediabetes_upper", "diabetes_fg_threshold"}
YEARS = {
    "baseline_year_start",
    "baseline_year_end",
    "followup_year_start",
    "followup_year_end",
}
DURATIONS = {"maximum_followup_years", "median_followup_years", "minimum_followup_years"}
NAMES = PDF_COUNTS | XML_COUNTS | PERCENTAGES | GLUCOSE | YEARS | DURATIONS
XML_NAMES = XML_COUNTS | {"median_followup_years", "minimum_followup_years"}
PAGE_NUMBERS = {
    "identity": 1,
    "attendance": 3,
    "overall_panels": 4,
    "table2_definition": 5,
    "selection_flowchart": 9,
}
XML_PATHS = {
    "pmid": "./PubmedArticle/MedlineCitation/PMID",
    "article_title": "./PubmedArticle/MedlineCitation/Article/ArticleTitle",
    "doi": "./PubmedArticle/PubmedData/ArticleIdList/ArticleId[@IdType='doi']",
    "results": "./PubmedArticle/MedlineCitation/Article/Abstract/AbstractText[@Label='RESULTS']",
    "design": "./PubmedArticle/MedlineCitation/Article/Abstract/AbstractText[@Label='DESIGN, SETTING, AND PARTICIPANTS']",
    "exposures": "./PubmedArticle/MedlineCitation/Article/Abstract/AbstractText[@Label='EXPOSURES']",
    "outcome_definition": "./PubmedArticle/MedlineCitation/Article/Abstract/AbstractText[@Label='MAIN OUTCOMES AND MEASURES']",
    "erratum_link": "./PubmedArticle/MedlineCitation/CommentsCorrectionsList/CommentsCorrections[@RefType='ErratumIn']",
}


def _fail(reason: str) -> None:
    # Caller/source text, numeric tokens and decoder details never appear in errors.
    raise ValueError(f"ARIC source extraction failed: {reason}") from None


def _normalized(value: str) -> str:
    return " ".join(value.split())


def _check_digest(content: bytes, expected: dict) -> None:
    if type(expected["size_bytes"]) is not int or len(content) != expected["size_bytes"]:
        _fail("source size mismatch")
    if sha256(content).hexdigest() != expected["sha256"]:
        _fail("source hash mismatch")
    if expected["doi"] != DOI:
        _fail("source identity mismatch")


def _check_text(value: str, specification: dict) -> None:
    if sha256(value.encode("utf-8")).hexdigest() != specification["normalized_text_sha256"]:
        _fail("selected text hash mismatch")


def _one_match(value: str, pattern: str) -> re.Match:
    if type(pattern) is not str or len(pattern) > 600:
        _fail("numeric locator is invalid")
    matches = list(re.finditer(pattern, value))
    if len(matches) != 1:
        _fail("numeric locator is missing or nonunique")
    return matches[0]


def _number(value: str, specification: dict, pattern: str | None = None) -> int | float:
    match = _one_match(
        value, pattern or specification.get("pattern", specification.get("row_pattern"))
    )
    token = match.group(specification["group"])
    if len(token) > 24 or re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", token) is None:
        _fail("numeric token is unsupported")
    if specification["type"] == "integer":
        if "." in token:
            _fail("count or definition is not integral")
        result = int(token)
    else:
        result = float(token)
        if not math.isfinite(result):
            _fail("numeric token is nonfinite")
    if result != specification["expected"]:
        _fail("observed value differs from protocol")
    return result


def _check_capture_scope(captures: list[dict]) -> None:
    if type(captures) is not list or len(captures) != len(NAMES):
        _fail("capture scope is invalid")
    if any(type(item) is not dict for item in captures):
        _fail("capture scope is invalid")
    names = [item["name"] for item in captures]
    if len(set(names)) != len(names) or set(names) != NAMES:
        _fail("capture scope is invalid")
    for item in captures:
        name = item["name"]
        if item["source"] != ("pubmed_abstract" if name in XML_NAMES else "supplement"):
            _fail("capture source is invalid")
        expected_type = "decimal" if name in PERCENTAGES | DURATIONS else "integer"
        unit = (
            "%"
            if name in PERCENTAGES
            else "years"
            if name in DURATIONS
            else "calendar_year"
            if name in YEARS
            else "mg/dL"
            if name in GLUCOSE
            else "persons"
        )
        if item["type"] != expected_type or item["unit"] != unit:
            _fail("capture type or unit is invalid")
        expected = item["expected"]
        allowed_type = int if expected_type == "integer" else float
        if type(expected) is not allowed_type or not math.isfinite(expected) or expected < 0:
            _fail("expected numeric value is invalid")
        locator = item["source_locator"]
        if (
            type(locator) is not str
            or not 1 <= len(locator) <= 300
            or "\n" in locator
            or "\r" in locator
        ):
            _fail("source locator is invalid")
        if locator != _canonical_locator(item):
            _fail("source locator or count mapping is invalid")


def _canonical_locator(spec: dict) -> str:
    """Return only approved structural metadata, never caller-authored body text."""
    name = spec["name"]
    if name in XML_NAMES:
        selector = "design" if name in DURATIONS else "results"
        if spec["xml_selector"] != selector or spec["group"] != name:
            _fail("abstract count mapping is invalid")
        return XML_PATHS[selector] + ", unique pattern/group " + name
    if name in PDF_COUNTS:
        for panel in PANELS:
            for column in COLUMNS:
                if name == f"{panel}_{column}":
                    if spec["panel_selector"] != panel or spec["group"] != column:
                        _fail("panel count mapping is invalid")
                    return (
                        f"PDF page4, eTable2, {panel} unique Overall row, ordered {column} column"
                    )
        selector = "overall_panels" if name == "selected_count" else "attendance"
        if spec["selector"] != selector or spec["group"] != name:
            _fail("disposition count mapping is invalid")
        return f"PDF page {PAGE_NUMBERS[selector]}, {selector}, unique selected pattern/group"
    if name in {"a1c_prediabetes_lower", "a1c_prediabetes_upper"}:
        selector = "a1c_thresholds"
    elif name in {"fg_prediabetes_lower", "fg_prediabetes_upper"}:
        selector = "fg_thresholds"
    elif name in {"diabetes_a1c_threshold", "diabetes_fg_threshold"}:
        selector = "dm_thresholds"
    elif name == "maximum_followup_years":
        selector = "maximum_followup"
    elif name in {"baseline_year_start", "baseline_year_end"}:
        selector = "baseline_period"
    else:
        selector = "followup_period"
    if spec["definition_selector"] != selector or spec["group"] != name:
        _fail("numeric definition mapping is invalid")
    return f"{selector} exact frozen scope, named group {name}"


def _check_image(page, guard: dict) -> None:
    resources = page["/Resources"]
    xobjects = resources["/XObject"]
    if len(xobjects) != guard["resource_xobject_count"] or len(xobjects) != 1:
        _fail("figure resource scope mismatch")
    if guard["xobject_path"] != "/Resources/XObject/Im0" or guard["expected_name"] != "/Im0":
        _fail("figure locator mismatch")
    obj = xobjects["/Im0"].get_object()
    if str(obj["/Subtype"]) != "/Image" or guard["subtype"] != "/Image":
        _fail("figure subtype mismatch")
    for field, key in (
        ("width", "/Width"),
        ("height", "/Height"),
        ("bits_per_component", "/BitsPerComponent"),
    ):
        if type(guard[field]) is not int or guard[field] <= 0 or obj[key] != guard[field]:
            _fail("figure dimensions mismatch")
    if str(obj["/Filter"]) != guard["filter"] or guard["filter"] != "/FlateDecode":
        _fail("figure filter mismatch")
    if obj.get("/DecodeParms") is not None or guard["decode_parms"] is not None:
        _fail("figure decode parameters mismatch")
    pixels = obj.get_data()
    _check_image_bytes(pixels, guard, "decoded_stream")
    if guard["bits_per_component"] != 8 or len(pixels) != guard["width"] * guard["height"]:
        _fail("figure pixel dimensions are inconsistent")
    colorspace = obj["/ColorSpace"]
    color_guard = guard["colorspace"]
    if (
        len(colorspace) != 4
        or str(colorspace[0]) != "/Indexed"
        or str(colorspace[1]) != "/DeviceRGB"
    ):
        _fail("figure colorspace mismatch")
    if color_guard["family"] != "/Indexed" or color_guard["base"] != "/DeviceRGB":
        _fail("figure colorspace mismatch")
    if (
        type(color_guard["maximum_index"]) is not int
        or colorspace[2] != color_guard["maximum_index"]
    ):
        _fail("figure palette index mismatch")
    lookup = colorspace[3].get_object()
    if not hasattr(lookup, "get_data"):
        _fail("figure palette stream is invalid")
    palette = lookup.get_data()
    _check_image_bytes(palette, color_guard, "lookup_stream")
    if not 0 <= color_guard["maximum_index"] <= 255 or len(palette) != 3 * (
        color_guard["maximum_index"] + 1
    ):
        _fail("figure palette dimensions are inconsistent")


def _check_image_bytes(content: bytes, guard: dict, prefix: str) -> None:
    if (
        type(guard[f"{prefix}_size_bytes"]) is not int
        or len(content) != guard[f"{prefix}_size_bytes"]
    ):
        _fail("figure stream size mismatch")
    if sha256(content).hexdigest() != guard[f"{prefix}_sha256"]:
        _fail("figure stream hash mismatch")


def _pdf_scopes(content: bytes, protocol: dict) -> tuple[dict[str, str], dict[str, str]]:
    decoder = protocol["decoder"]
    if decoder["library"] != "pypdf" or decoder["version"] != pypdf.__version__:
        _fail("decoder version mismatch")
    if not content.startswith(b"%PDF-"):
        _fail("PDF header is invalid")
    reader = pypdf.PdfReader(BytesIO(content), strict=True)
    if reader.is_encrypted or len(reader.pages) != protocol["sources"]["supplement"]["page_count"]:
        _fail("PDF page scope is invalid")
    selectors = protocol["selectors"]
    if set(selectors) != set(PAGE_NUMBERS):
        _fail("PDF selector scope is invalid")
    texts = {}
    for name, page_number in PAGE_NUMBERS.items():
        spec = selectors[name]
        if type(spec["pdf_page_1based"]) is not int or spec["pdf_page_1based"] != page_number:
            _fail("PDF page locator mismatch")
        value = _normalized(reader.pages[page_number - 1].extract_text())
        _check_text(value, spec)
        if spec["anchor_occurrences"] != 1 or value.count(spec["unique_anchor"]) != 1:
            _fail("PDF title is missing or nonunique")
        texts[name] = value
    identity = texts["identity"].casefold()
    title = protocol["sources"]["supplement"]["article_title"].casefold()
    if title not in identity or identity.count(f"doi:{DOI}") != 1:
        _fail("PDF publication identity mismatch")
    _check_image(reader.pages[8], selectors["selection_flowchart"]["embedded_image"])
    if texts["attendance"].count(protocol["attendance_column_guard"]) != 1:
        _fail("attendance columns are missing or reordered")
    panels = protocol["panel_selectors"]
    if set(panels) != set(PANELS):
        _fail("panel scope is invalid")
    page = texts["overall_panels"]
    scopes = {}
    starts = []
    for name in PANELS:
        heading = panels[name]["unique_section_heading"]
        if page.count(heading) != 1:
            _fail("panel heading is missing or nonunique")
        starts.append(page.index(heading))
    if starts != sorted(starts):
        _fail("panels are reordered")
    for index, name in enumerate(PANELS):
        spec = panels[name]
        if spec["selector"] != "overall_panels" or spec["expected_column_count"] != len(COLUMNS):
            _fail("panel locator is invalid")
        section = page[starts[index] : starts[index + 1] if index + 1 < len(starts) else len(page)]
        end = list(re.finditer(r"\b" + re.escape(spec["section_end"]) + r"\b", section))
        if len(end) != 1 or spec["section_end"] != "Age":
            _fail("panel section boundary is invalid")
        section = section[: end[0].start()].strip()
        prefix = f"{spec['unique_section_heading']} {spec['followup_heading']} {spec['exact_column_header']} Overall "
        if not section.startswith(prefix):
            _fail("panel columns are missing or reordered")
        if spec["overall_row_occurrences_within_section"] != 1 or section.count("Overall ") != 1:
            _fail("overall row is missing or nonunique")
        if spec["selected_percentages"] is not False:
            _fail("percentage scope is unsupported")
        match = _one_match(section, spec["row_pattern"])
        if match.end() != len(section):
            _fail("overall row has unsupported trailing cells")
        scopes[name] = section
    return texts, scopes


def _xml_scopes(content: bytes, protocol: dict) -> dict[str, str]:
    # ElementTree never fetches the source's external NLM DTD. Reject internal
    # declarations outright so re-pinned malicious fixtures cannot expand entities.
    if b"<!ENTITY" in content.upper() or re.search(rb"<!DOCTYPE[^>]*\[", content, re.I):
        _fail("XML entity declarations are unsupported")
    root = ET.fromstring(content)
    if root.tag != "PubmedArticleSet" or len(root.findall("./PubmedArticle")) != 1:
        _fail("PubMed article scope is invalid")
    source = protocol["sources"]["pubmed_abstract"]
    if source["expected_root_tag"] != root.tag or source["expected_pubmed_article_count"] != 1:
        _fail("PubMed protocol identity is invalid")
    selectors = protocol["xml_selectors"]
    if set(selectors) != set(XML_PATHS):
        _fail("XML selector scope is invalid")
    texts = {}
    for name, path in XML_PATHS.items():
        spec = selectors[name]
        if spec["xpath"] != path or spec["expected_occurrences"] != 1:
            _fail("XML locator is invalid")
        matches = root.findall(path)
        if len(matches) != 1:
            _fail("XML section is missing or nonunique")
        value = _normalized("".join(matches[0].itertext()))
        _check_text(value, spec)
        if "expected_text" in spec and value != spec["expected_text"]:
            _fail("XML publication identity mismatch")
        texts[name] = value
    if texts["pmid"] != PMID or texts["doi"] != DOI:
        _fail("XML publication identity mismatch")
    if (
        texts["article_title"]
        != "Risk of Progression to Diabetes Among Older Adults With Prediabetes."
    ):
        _fail("XML title mismatch")
    correction = selectors["erratum_link"]
    if (
        correction["expected_correction_doi"] != "10.1001/jamainternmed.2021.1321"
        or correction["expected_correction_pmid"] != "33818604"
    ):
        _fail("correction association mismatch")
    erratum = root.findall(XML_PATHS["erratum_link"])[0]
    if len(erratum.findall("PMID")) != 1 or erratum.findtext("PMID") != "33818604":
        _fail("correction association mismatch")
    if "10.1001/jamainternmed.2021.1321" not in texts["erratum_link"]:
        _fail("correction association mismatch")
    return texts


def _arithmetic(values: dict[str, int | float]) -> None:
    v = values
    if (
        v["original_analytic_count"]
        != v["attended_visit6_count"] + v["alive_nonattender_count"] + v["died_before_visit6_count"]
    ):
        _fail("original disposition conservation failed")
    if v["selected_count"] != v["attended_visit6_count"] + v["died_before_visit6_count"]:
        _fail("selected disposition count check failed")
    for panel in PANELS:
        if v[f"{panel}_baseline_count"] != sum(v[f"{panel}_{name}"] for name in COLUMNS[1:]):
            _fail("displayed panel conservation failed")
    for assay in ("a1c", "fg"):
        if (
            v[f"{assay}_normal_baseline_count"] + v[f"{assay}_prediabetes_baseline_count"]
            != v["selected_count"]
        ):
            _fail("assay denominator conservation failed")
    for column in ("displayed_diabetes_count", "displayed_mortality_count"):
        a1c = v[f"a1c_normal_{column}"] + v[f"a1c_prediabetes_{column}"]
        fg = v[f"fg_normal_{column}"] + v[f"fg_prediabetes_{column}"]
        if a1c != fg:
            _fail("overlapping assay count corroboration failed")
        if column == "displayed_mortality_count" and a1c != v["cumulative_mortality_count"]:
            _fail("mortality count corroboration failed")
    if (
        v["original_either_prediabetes_count"]
        != v["original_a1c_prediabetes_count"]
        + v["original_fg_prediabetes_count"]
        - v["original_both_prediabetes_count"]
    ):
        _fail("original assay overlap arithmetic failed")
    for assay in ("a1c", "fg"):
        original_pred = v[f"original_{assay}_prediabetes_count"]
        original_normal = v["original_analytic_count"] - original_pred
        if (
            original_pred < v[f"{assay}_prediabetes_baseline_count"]
            or original_normal < v[f"{assay}_normal_baseline_count"]
        ):
            _fail("original and selected margins are incompatible")
    if not v["minimum_followup_years"] <= v["median_followup_years"] <= v["maximum_followup_years"]:
        _fail("variable follow-up descriptors are unordered")
    if (
        not v["baseline_year_start"]
        <= v["baseline_year_end"]
        < v["followup_year_start"]
        <= v["followup_year_end"]
    ):
        _fail("source calendar periods are unordered")
    if not v["a1c_prediabetes_lower"] < v["a1c_prediabetes_upper"] < v["diabetes_a1c_threshold"]:
        _fail("A1c definitions are unordered")
    if not v["fg_prediabetes_lower"] < v["fg_prediabetes_upper"] < v["diabetes_fg_threshold"]:
        _fail("fasting glucose definitions are unordered")


def extract_aric_source_records(supplement: bytes, pubmed_abstract: bytes, protocol: dict) -> dict:
    """Return only the frozen publication observations from both pinned sources.

    The caller must bind the protocol to the evidence registry. Arithmetic checks
    establish published count consistency, not person membership, an observation
    likelihood, a common endpoint clock, or clinical calibration.
    """
    if (
        type(supplement) is not bytes
        or type(pubmed_abstract) is not bytes
        or type(protocol) is not dict
    ):
        _fail("input types are invalid")
    try:
        sources = protocol["sources"]
        if type(sources) is not dict or set(sources) != {"supplement", "pubmed_abstract"}:
            _fail("source scope is invalid")
        gates = protocol["scientific_gates"]
        if (
            type(gates) is not dict
            or set(gates) != set(SCIENTIFIC_GATES)
            or any(value is not False for value in gates.values())
        ):
            _fail("scientific gates are invalid")
        contents = {"supplement": supplement, "pubmed_abstract": pubmed_abstract}
        for name, content in contents.items():
            _check_digest(content, sources[name])
        _check_capture_scope(protocol["captures"])
        pdf, panels = _pdf_scopes(supplement, protocol)
        xml = _xml_scopes(pubmed_abstract, protocol)
        guard = protocol["definition_guard"]
        if (
            guard["selector"] != "table2_definition"
            or pdf["table2_definition"].count(guard["unique_start"]) != 1
        ):
            _fail("source definition locator is invalid")
        definition = pdf["table2_definition"][
            pdf["table2_definition"].index(guard["unique_start"]) :
        ]
        if sha256(definition.encode("utf-8")).hexdigest() != guard["normalized_definition_sha256"]:
            _fail("source definition hash mismatch")
        observed = {}
        locators = {}
        for spec in protocol["captures"]:
            if spec["source"] == "pubmed_abstract":
                value = _number(xml[spec["xml_selector"]], spec)
            elif "panel_selector" in spec:
                key = spec["panel_selector"]
                if spec["group"] not in COLUMNS:
                    _fail("panel count group is invalid")
                value = _number(panels[key], spec, protocol["panel_selectors"][key]["row_pattern"])
            elif "definition_selector" in spec:
                scope = protocol["numeric_definition_selectors"][spec["definition_selector"]]
                component = scope["component"]
                if "panel_selector" in scope:
                    if component not in {
                        "exact_column_header",
                        "unique_section_heading",
                        "followup_heading",
                    }:
                        _fail("definition scope is invalid")
                    selected = protocol["panel_selectors"][scope["panel_selector"]][component]
                elif (
                    component == "definition_guard_from_unique_start"
                    and scope["selector"] == "table2_definition"
                ):
                    selected = definition
                elif component == "normalized_page_text" and scope["selector"] == "overall_panels":
                    selected = pdf["overall_panels"]
                else:
                    _fail("definition scope is invalid")
                value = _number(selected, spec)
            else:
                value = _number(pdf[spec["selector"]], spec)
            observed[spec["name"]] = value
            locators[spec["name"]] = _canonical_locator(spec)
        corroborations = protocol["xml_corroborations"]
        if (
            type(corroborations) is not list
            or {x["observed_name"] for x in corroborations}
            != {"original_analytic_count", "selected_count", "maximum_followup_years"}
            or len(corroborations) != 3
        ):
            _fail("cross-source corroboration scope is invalid")
        for spec in corroborations:
            name = spec["observed_name"]
            kind = "decimal" if name == "maximum_followup_years" else "integer"
            capture = {**spec, "type": kind, "expected": observed[name]}
            _number(xml[spec["xml_selector"]], capture)
        _arithmetic(observed)
        return {
            "source_sha256": {
                name: sha256(content).hexdigest() for name, content in contents.items()
            },
            "source_size_bytes": {name: len(content) for name, content in contents.items()},
            "doi": DOI,
            "observed": observed,
            "source_locators": locators,
            "scientific_gates": dict(SCIENTIFIC_GATES),
        }
    except Exception:
        # Keep parser, XML, regex, PDF, protocol errors free of source content.
        _fail("pinned source or protocol verification failed")
