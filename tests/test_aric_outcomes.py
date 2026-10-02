"""Synthetic published-table fixtures; no participant or source-cache dependency."""

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)
import pytest

from demeter.data.aric_outcomes import (
    COLUMNS,
    DOI,
    NAMES,
    PANELS,
    SCIENTIFIC_GATES,
    extract_aric_source_records,
)

ROOT = Path(__file__).resolve().parents[1]


def _digest(data):
    return sha256(data).hexdigest()


def _norm(text):
    return " ".join(text.split())


def _pdf(pages, image_width=1):
    """Generate an actual tiny PDF with text and a native indexed image."""
    writer = PdfWriter()
    for number in range(12):
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {
                        NameObject("/F1"): writer._add_object(font),
                    }
                ),
            }
        )
        content = DecodedStreamObject()
        text = pages.get(number + 1, "Unselected synthetic page")
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content.set_data(f"BT /F1 8 Tf 10 750 Td ({escaped}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
        if number == 8:
            lookup = DecodedStreamObject()
            lookup.set_data(b"\x00\x00\x00")
            image = DecodedStreamObject()
            image.set_data(b"\x00" * image_width)
            image = image.flate_encode()
            image.update(
                {
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(image_width),
                    NameObject("/Height"): NumberObject(1),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                    NameObject("/ColorSpace"): ArrayObject(
                        [
                            NameObject("/Indexed"),
                            NameObject("/DeviceRGB"),
                            NumberObject(0),
                            writer._add_object(lookup),
                        ]
                    ),
                }
            )
            page["/Resources"][NameObject("/XObject")] = DictionaryObject(
                {
                    NameObject("/Im0"): writer._add_object(image),
                }
            )
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _image_guard(reader):
    obj = reader.pages[8]["/Resources"]["/XObject"]["/Im0"].get_object()
    palette = obj["/ColorSpace"][3].get_object().get_data()
    pixels = obj.get_data()
    return {
        "xobject_path": "/Resources/XObject/Im0",
        "resource_xobject_count": 1,
        "expected_name": "/Im0",
        "subtype": "/Image",
        "width": int(obj["/Width"]),
        "height": 1,
        "bits_per_component": 8,
        "filter": "/FlateDecode",
        "decode_parms": None,
        "decoded_stream_size_bytes": len(pixels),
        "decoded_stream_sha256": _digest(pixels),
        "colorspace": {
            "family": "/Indexed",
            "base": "/DeviceRGB",
            "maximum_index": 0,
            "lookup_stream_size_bytes": len(palette),
            "lookup_stream_sha256": _digest(palette),
        },
    }


def _seal(pdf, xml, protocol, *, image=False, definition=False):
    protocol = deepcopy(protocol)
    for key, data in (("supplement", pdf), ("pubmed_abstract", xml)):
        protocol["sources"][key]["sha256"] = _digest(data)
        protocol["sources"][key]["size_bytes"] = len(data)
    reader = PdfReader(BytesIO(pdf))
    for spec in protocol["selectors"].values():
        text = _norm(reader.pages[spec["pdf_page_1based"] - 1].extract_text())
        spec["normalized_text_sha256"] = _digest(text.encode())
    if image:
        protocol["selectors"]["selection_flowchart"]["embedded_image"] = _image_guard(reader)
    if definition:
        text = _norm(reader.pages[4].extract_text())
        guard = protocol["definition_guard"]
        text = text[text.index(guard["unique_start"]) :]
        guard["normalized_definition_sha256"] = _digest(text.encode())
    root = ET.fromstring(xml)
    for spec in protocol["xml_selectors"].values():
        matches = root.findall(spec["xpath"])
        if len(matches) == 1:
            text = _norm("".join(matches[0].itertext()))
            spec["normalized_text_sha256"] = _digest(text.encode())
    return protocol


@pytest.fixture
def fixture():
    protocol_path = ROOT / "docs/validation/aric-outcomes-intake-protocol-v1.json"
    protocol = json.loads(protocol_path.read_bytes())
    # Synthetic font uses ASCII >=; its protocol explicitly selects that spelling.
    for capture in protocol["captures"]:
        if "pattern" in capture:
            capture["pattern"] = (
                capture["pattern"].replace("\u00e2\u2030\u00a5", ">=").replace("\u2265", ">=")
            )
    values = {item["name"]: item["expected"] for item in protocol["captures"]}
    pages = {
        1: f"Supplementary Online Content {protocol['sources']['supplement']['article_title']}. doi:{DOI}",
        3: protocol["selectors"]["attendance"]["unique_anchor"]
        + " "
        + protocol["attendance_column_guard"]
        + " N 3412 2089 915 408 Age ignored",
        4: "eTable 2. Cumulative incidence over 6.5 years (maximum) "
        "ARIC Study (2011-2017), n=2497 A1C ",
        5: protocol["selectors"]["table2_definition"]["unique_anchor"]
        + " a Incident total diabetes includes physician diagnosis or medication, "
        "visit 6 A1C >=6.5%, or visit 6 FG >=126 mg/dL.",
        9: "eFigure 1. Participant flow chart",
    }
    for name in PANELS:
        spec = protocol["panel_selectors"][name]
        counts = [values[f"{name}_{column}"] for column in COLUMNS]
        row = " ".join(
            str(value) + ("" if index == 0 else " (0%)") for index, value in enumerate(counts)
        )
        pages[4] += (
            f"{spec['unique_section_heading']} {spec['followup_heading']} "
            f"{spec['exact_column_header']} Overall {row} Age ignored "
        )
    root = ET.Element("PubmedArticleSet")
    article = ET.SubElement(root, "PubmedArticle")
    citation = ET.SubElement(article, "MedlineCitation")
    ET.SubElement(citation, "PMID").text = "33555311"
    pub_article = ET.SubElement(citation, "Article")
    ET.SubElement(
        pub_article, "ArticleTitle"
    ).text = "Risk of Progression to Diabetes Among Older Adults With Prediabetes."
    abstract = ET.SubElement(pub_article, "Abstract")
    abstracts = {
        "RESULTS": "A total of 3412 participants without diabetes; a total of 2497 participants attended the follow-up visit or died. "
        "There were 156 incident total diabetes cases and 434 deaths. "
        "A total of 1490 participants (44%) had HbA1c levels of 5.7% to 6.4%, "
        "1996 (59%) had IFG, 2482 (73%) met the HbA1c or IFG criteria, "
        "and 1004 (29%) met both the HbA1c and IFG criteria.",
        "DESIGN, SETTING, AND PARTICIPANTS": "median [range] follow-up, 5.0 [0.1-6.5] years",
        "EXPOSURES": "Synthetic source native assay definitions",
        "MAIN OUTCOMES AND MEASURES": "Synthetic OR endpoint definition",
    }
    # The frozen regex matches lower-case publication wording.
    abstracts["RESULTS"] = abstracts["RESULTS"].replace("There were", "there were")
    for label, text in abstracts.items():
        ET.SubElement(abstract, "AbstractText", Label=label).text = text
    corrections = ET.SubElement(citation, "CommentsCorrectionsList")
    erratum = ET.SubElement(corrections, "CommentsCorrections", RefType="ErratumIn")
    ET.SubElement(erratum, "RefSource").text = "doi: 10.1001/jamainternmed.2021.1321."
    ET.SubElement(erratum, "PMID").text = "33818604"
    data = ET.SubElement(article, "PubmedData")
    ids = ET.SubElement(data, "ArticleIdList")
    ET.SubElement(ids, "ArticleId", IdType="doi").text = DOI
    xml = ET.tostring(root)
    pdf = _pdf(pages)
    protocol = _seal(pdf, xml, protocol, image=True, definition=True)
    return pdf, xml, protocol, pages


def _reject(pdf, xml, protocol):
    with pytest.raises(ValueError) as caught:
        extract_aric_source_records(pdf, xml, protocol)
    assert (
        str(caught.value)
        == "ARIC source extraction failed: pinned source or protocol verification failed"
    )
    assert caught.value.__suppress_context__


def test_actual_synthetic_pdf_and_xml_extract_only_44_observed_values(fixture):
    pdf, xml, protocol, _ = fixture
    result = extract_aric_source_records(pdf, xml, protocol)
    assert set(result) == {
        "source_sha256",
        "source_size_bytes",
        "doi",
        "observed",
        "source_locators",
        "scientific_gates",
    }
    assert set(result["observed"]) == NAMES
    assert len(result["observed"]) == 44
    assert result["observed"] == {item["name"]: item["expected"] for item in protocol["captures"]}
    assert result["scientific_gates"] == SCIENTIFIC_GATES
    assert set(result["source_locators"]) == NAMES
    assert result["observed"]["cumulative_total_diabetes_count"] == 156
    assert (
        sum(
            result["observed"][f"a1c_{state}_displayed_diabetes_count"]
            for state in ("normal", "prediabetes")
        )
        == 138
    )
    assert result["observed"]["died_before_visit6_count"] == 408
    assert result["observed"]["cumulative_mortality_count"] == 434
    serialized = json.dumps(result)
    for prohibited in (
        "pixel",
        "stream",
        "physician diagnosis or medication",
        "derived",
        "independently_verified_missing",
    ):
        assert prohibited not in serialized


@pytest.mark.parametrize("source", ["supplement", "pubmed_abstract"])
def test_source_bytes_are_required_and_pinned(fixture, source):
    pdf, xml, protocol, _ = fixture
    if source == "supplement":
        pdf += b"x"
    else:
        xml += b"x"
    _reject(pdf, xml, protocol)


@pytest.mark.parametrize(
    "gates",
    [
        {},
        {"clinical_fit_allowed": False},
        {**SCIENTIFIC_GATES, "engine_activation_allowed": 0},
        {**SCIENTIFIC_GATES, "clinical_fit_allowed": True},
    ],
)
def test_gates_require_exact_four_false_booleans(fixture, gates):
    pdf, xml, protocol, _ = fixture
    protocol["scientific_gates"] = gates
    _reject(pdf, xml, protocol)


@pytest.mark.parametrize(
    "change",
    ["remove", "duplicate", "wrongunit", "boolvalue", "wrongsource", "unknownname", "nonfinite"],
)
def test_capture_scope_and_types_fail_closed(fixture, change):
    pdf, xml, protocol, _ = fixture
    if change == "remove":
        protocol["captures"].pop()
    elif change == "duplicate":
        protocol["captures"][-1] = deepcopy(protocol["captures"][0])
    elif change == "wrongunit":
        protocol["captures"][0]["unit"] = "years"
    elif change == "boolvalue":
        protocol["captures"][0]["expected"] = True
    elif change == "wrongsource":
        protocol["captures"][0]["source"] = "pubmed_abstract"
    elif change == "unknownname":
        protocol["captures"][0]["name"] = "PRIVATE_FREE_TEXT"
    else:
        protocol["captures"][-1]["expected"] = float("nan")
    _reject(pdf, xml, protocol)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicateheading",
        "duplicaterow",
        "reordercolumns",
        "reorderpanels",
        "trailingcell",
        "floatcount",
        "negativecount",
        "driftcount",
        "missingheading",
    ],
)
def test_resealed_pdf_structure_cannot_change_selected_semantics(fixture, mutation):
    _, xml, protocol, pages = fixture
    heading = protocol["panel_selectors"]["a1c_normal"]["unique_section_heading"]
    if mutation == "duplicateheading":
        pages[4] += heading
    elif mutation == "duplicaterow":
        pages[4] = pages[4].replace(
            "Overall 1400", "Overall 1400 893 (0%) 239 (0%) 41 (0%) 227 (0%) Overall 1400"
        )
    elif mutation == "reordercolumns":
        pages[4] = pages[4].replace("Total Diabetes a Mortality", "Mortality Total Diabetes a", 1)
    elif mutation == "reorderpanels":
        other = protocol["panel_selectors"]["a1c_prediabetes"]["unique_section_heading"]
        pages[4] = pages[4].replace(heading, "TEMP").replace(other, heading).replace("TEMP", other)
    elif mutation == "trailingcell":
        pages[4] = pages[4].replace("227 (0%) Age", "227 (0%) 99 Age")
    elif mutation == "floatcount":
        pages[4] = pages[4].replace("Overall 1400 ", "Overall 1400.0 ")
    elif mutation == "negativecount":
        pages[4] = pages[4].replace("Overall 1400 ", "Overall -1400 ")
    elif mutation == "driftcount":
        pages[4] = pages[4].replace("Overall 1400 ", "Overall 1401 ")
    else:
        pages[4] = pages[4].replace(heading, "Wrong source heading")
    pdf = _pdf(pages)
    _reject(pdf, xml, _seal(pdf, xml, protocol))


@pytest.mark.parametrize("field", ["width", "subtype", "colorspace", "palettehash", "pixelhash"])
def test_native_image_metadata_and_stream_binding(fixture, field):
    pdf, xml, protocol, _ = fixture
    guard = protocol["selectors"]["selection_flowchart"]["embedded_image"]
    if field == "width":
        guard["width"] = 2
    elif field == "subtype":
        guard["subtype"] = "/Form"
    elif field == "colorspace":
        guard["colorspace"]["base"] = "/DeviceGray"
    elif field == "palettehash":
        guard["colorspace"]["lookup_stream_sha256"] = "0" * 64
    else:
        guard["decoded_stream_sha256"] = "0" * 64
    _reject(pdf, xml, protocol)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicatearticle",
        "duplicateresults",
        "wrongpmid",
        "wrongdoi",
        "wrongtitle",
        "wronglabel",
        "wrongerratum",
    ],
)
def test_resealed_xml_requires_exact_primary_identity_and_unique_sections(fixture, mutation):
    pdf, xml, protocol, _ = fixture
    root = ET.fromstring(xml)
    if mutation == "duplicatearticle":
        root.append(deepcopy(root[0]))
    elif mutation == "duplicateresults":
        abstract = root.find("./PubmedArticle/MedlineCitation/Article/Abstract")
        abstract.append(deepcopy(abstract[0]))
    elif mutation == "wrongpmid":
        root.find("./PubmedArticle/MedlineCitation/PMID").text = "999"
    elif mutation == "wrongdoi":
        root.find("./PubmedArticle/PubmedData/ArticleIdList/ArticleId").text = "10.unknown/private"
    elif mutation == "wrongtitle":
        root.find("./PubmedArticle/MedlineCitation/Article/ArticleTitle").text = "PRIVATE_FREE_TEXT"
    elif mutation == "wronglabel":
        root.find("./PubmedArticle/MedlineCitation/Article/Abstract/AbstractText").set(
            "Label", "OBJECTIVES"
        )
    else:
        root.find(
            "./PubmedArticle/MedlineCitation/CommentsCorrectionsList/CommentsCorrections/PMID"
        ).text = "999"
    xml = ET.tostring(root)
    _reject(pdf, xml, _seal(pdf, xml, protocol))


def test_resealed_entity_declaration_is_rejected_without_resolution(fixture):
    pdf, xml, protocol, _ = fixture
    xml = b'<!DOCTYPE PubmedArticleSet [<!ENTITY leak SYSTEM "file:///private">]>' + xml
    protocol["sources"]["pubmed_abstract"].update(size_bytes=len(xml), sha256=_digest(xml))
    _reject(pdf, xml, protocol)


def test_resealed_change_cannot_hide_disposition_nonconservation(fixture):
    _, xml, protocol, pages = fixture
    pages[3] = pages[3].replace("N 3412 2089 915 408", "N 3412 2089 914 408")
    next(x for x in protocol["captures"] if x["name"] == "alive_nonattender_count")["expected"] = (
        914
    )
    pdf = _pdf(pages)
    _reject(pdf, xml, _seal(pdf, xml, protocol))


def test_resealed_change_cannot_hide_panel_nonconservation(fixture):
    _, xml, protocol, pages = fixture
    pages[4] = pages[4].replace("893 (0%)", "892 (0%)", 1)
    next(x for x in protocol["captures"] if x["name"] == "a1c_normal_followup_normal_count")[
        "expected"
    ] = 892
    pdf = _pdf(pages)
    _reject(pdf, xml, _seal(pdf, xml, protocol))


def test_definition_hash_and_numeric_operator_are_not_silently_repaired(fixture):
    pdf, xml, protocol, _ = fixture
    capture = next(x for x in protocol["captures"] if x["name"] == "diabetes_a1c_threshold")
    capture["pattern"] = capture["pattern"].replace(">=", "\u00e2\u2030\u00a5")
    _reject(pdf, xml, protocol)
    capture["pattern"] = capture["pattern"].replace("\u00e2\u2030\u00a5", ">=")
    protocol["definition_guard"]["normalized_definition_sha256"] = "0" * 64
    _reject(pdf, xml, protocol)


def test_no_decoder_version_or_page_locator_fallback(fixture):
    pdf, xml, protocol, _ = fixture
    protocol["decoder"]["version"] = "unknown"
    _reject(pdf, xml, protocol)
    protocol["decoder"]["version"] = __import__("pypdf").__version__
    protocol["selectors"]["overall_panels"]["pdf_page_1based"] = 5
    _reject(pdf, xml, protocol)


def test_locator_metadata_cannot_export_caller_body_text(fixture):
    pdf, xml, protocol, _ = fixture
    protocol["captures"][0]["source_locator"] = "PRIVATE_FREE_TEXT source body"
    _reject(pdf, xml, protocol)


def test_swapped_count_groups_cannot_pass_conservation(fixture):
    pdf, xml, protocol, _ = fixture
    normal = next(
        x for x in protocol["captures"] if x["name"] == "a1c_normal_followup_normal_count"
    )
    prediabetes = next(
        x for x in protocol["captures"] if x["name"] == "a1c_normal_followup_prediabetes_count"
    )
    normal["group"], prediabetes["group"] = prediabetes["group"], normal["group"]
    normal["expected"], prediabetes["expected"] = prediabetes["expected"], normal["expected"]
    # Swapping labels preserves the row total; semantic column binding must reject.
    _reject(pdf, xml, protocol)


def test_resealed_invalid_pdf_error_never_displays_source_bytes(fixture, caplog, capsys):
    _, xml, protocol, _ = fixture
    pdf = b"PRIVATE_STUDY_SECRET not a PDF"
    protocol["sources"]["supplement"].update(size_bytes=len(pdf), sha256=_digest(pdf))
    _reject(pdf, xml, protocol)
    captured = capsys.readouterr()
    assert "PRIVATE_STUDY_SECRET" not in captured.out + captured.err + caplog.text


def test_caller_protocol_is_unchanged_after_extraction(fixture):
    pdf, xml, protocol, _ = fixture
    before = deepcopy(protocol)
    extract_aric_source_records(pdf, xml, protocol)
    assert protocol == before
