"""Pinned paired Geelong labels and an explicitly assumed categorical likelihood.

The probabilities describe the publication's assessed-pair timing mixture.
They are not clinical transition rates or an engine parameterization.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
from scipy.stats import beta

from demeter.data.ingest import digest
from demeter.data.nhanes import encoded, storage_numbers
from demeter.schema import EvidenceRegistry

DATASET = "geelong_label_pairs"
SOURCE_ID = "geelong2025_label_publication"
PROTOCOL_SHA256 = "8f78812f4bfee128bdf1fc463095b940edd7c952d1f4b02c31a84f8002fae6da"
ROWS = ("normal_start", "ifg_ada_start")
DESTINATIONS = ("normoglycaemia", "ifg_ada", "source_diabetes")
COHORT_KEYS = ("paired_assessed_n", "baseline_diabetes_n", "progression_analysis_n")
PARAMETER_KEYS = frozenset(
    [
        f"geelong_{row}_{label}_{suffix}"
        for row in ROWS
        for label in DESTINATIONS
        for suffix in ("n", "probability")
    ]
    + [f"geelong_{row}_n" for row in ROWS]
    + [f"geelong_{key}" for key in COHORT_KEYS]
)


def _text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def _number(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _section(root: ET.Element, identifier: str, title: str) -> ET.Element:
    sections = root.findall(f"./body//sec[@id='{identifier}']")
    if len(sections) != 1:
        raise ValueError("Geelong selected source section missing or duplicated")
    titles = sections[0].findall("title")
    if len(titles) != 1 or _text(titles[0]) != title:
        raise ValueError("Geelong selected source heading mismatch")
    return sections[0]


def _source_tree(content: bytes, protocol: dict) -> ET.Element:
    pin = protocol["source"]
    if (
        type(content) is not bytes
        or len(content) != pin["size_bytes"]
        or digest(content) != pin["sha256"]
    ):
        raise ValueError("Geelong source checksum or size mismatch")
    if b"<!DOCTYPE" in content or b"<!ENTITY" in content:
        raise ValueError("Unsupported Geelong XML declarations")
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        raise ValueError("Invalid Geelong source XML") from None
    if root.tag != "article" or len(root.findall("front/article-meta")) != 1:
        raise ValueError("Geelong source article structure mismatch")
    bibliography = protocol["bibliography"]
    for kind, expected in (("doi", bibliography["doi"]), ("pmcid", bibliography["pmcid"])):
        values = root.findall(f"front/article-meta/article-id[@pub-id-type='{kind}']")
        if len(values) != 1 or _text(values[0]) != expected:
            raise ValueError("Geelong article identity mismatch")
    titles = root.findall("front/article-meta/title-group/article-title")
    if len(titles) != 1 or _text(titles[0]) != bibliography["title"]:
        raise ValueError("Geelong article title mismatch")
    licenses = root.findall("front/article-meta/permissions/license")
    copyrights = root.findall("front/article-meta/permissions/copyright-statement")
    license_text = (
        "This is an open access article under the terms of the Creative Commons Attribution License, "
        "which permits use, distribution and reproduction in any medium, provided the original work is properly cited."
    )
    if (
        len(licenses) != 1
        or _text(licenses[0]) != license_text
        or len(copyrights) != 1
        or _text(copyrights[0])
        != "Copyright © 2025 Jacob W. Harland et al. Journal of Diabetes Research published by John Wiley & Sons Ltd."
    ):
        raise ValueError("Geelong source rights notice mismatch")
    return root


def extract_reported(content: bytes, protocol: dict) -> dict:
    """Capture only the six selected counts and required literal denominators.

    Percentages, WHO outcomes, incidence/person-time and baseline-diabetes
    destinations are never returned or converted into observations.
    """
    root = _source_tree(content, protocol)
    selection = protocol["selection"]
    if selection["row_order"] != list(ROWS) or selection["destination_labels"] != list(
        DESTINATIONS
    ):
        raise ValueError("Geelong selected label coverage mismatch")
    section = _section(root, selection["count_section_id"], selection["count_section_title"])
    paragraphs = [_text(p) for p in section.findall("p")]
    prefix, stop = selection["selected_paragraph_prefix"], selection["selected_paragraph_stop"]
    selected = [p for p in paragraphs if prefix in p]
    if (
        len(selected) != 1
        or selected[0].count(prefix) != 1
        or selected[0].count(stop) != 1
        or not selected[0].startswith(prefix)
    ):
        raise ValueError("Geelong selected count paragraph missing or duplicated")
    body = selected[0].split(stop)[0].strip()
    integer = r"[0-9]+"
    annotation = r"\([^()]*\)"
    normal_pattern = (
        rf"Most men with normoglycaemia at baseline remained in that category \(n = (?P<normal>{integer}), [^()]*\), "
        rf"(?P<ifg>{integer}) {annotation} men progressed to IFG-ADA and (?P<diabetes>{integer}) {annotation} men progressed to diabetes\. "
    )
    ifg_pattern = (
        rf"Of (?P<ifg_total>{integer}) men with IFG-ADA at study baseline, approximately half regressed to normoglycaemia "
        rf"\(n = (?P<normal>{integer}), [^()]*\), (?P<ifg>{integer}) men {annotation} remained with IFG-ADA "
        rf"and (?P<diabetes>{integer}) {annotation} progressed to diabetes\."
    )
    normal = re.match(normal_pattern, body)
    if normal is None:
        raise ValueError("Geelong normal-start semantic count binding failed")
    ifg = re.fullmatch(ifg_pattern, body[normal.end() :])
    if ifg is None:
        raise ValueError("Geelong IFG-start semantic count binding failed")
    counts = {
        row: {
            label: int(match.group(name))
            for label, name in zip(DESTINATIONS, ("normal", "ifg", "diabetes"), strict=True)
        }
        for row, match in zip(ROWS, (normal, ifg), strict=True)
    }
    if not paragraphs:
        raise ValueError("Geelong literal denominator paragraph missing")
    denominator_pattern = (
        rf"Of (?P<paired>{integer}) participants with sufficient data to determine diabetes status at the 15-year follow-up visit, "
        rf"(?P<normal>{integer}) {annotation} had normoglycaemia, (?P<ifg>{integer}) {annotation} had IFG-ADA, "
        rf"[^;]*? had IFG-WHO and (?P<diabetes>{integer}) {annotation} had diabetes at study baseline \(Figure 3\)\."
    )
    denominator_matches = [re.match(denominator_pattern, p) for p in paragraphs]
    denominator_matches = [m for m in denominator_matches if m is not None]
    if len(denominator_matches) != 1 or re.match(denominator_pattern, paragraphs[0]) is None:
        raise ValueError("Geelong literal row/cohort denominator binding failed")
    denominators = denominator_matches[0]
    methods = _section(root, "sec2.2", "2.2. Study Population")
    methods_text = [_text(p) for p in methods.findall("p")]
    methods_prefix = "Of these, "
    methods_matches = [p for p in methods_text if methods_prefix in p]
    if len(methods_matches) != 1 or methods_matches[0].count(methods_prefix) != 1:
        raise ValueError("Geelong independent cohort crosscheck missing or duplicated")
    methods_pattern = (
        rf"Of these, (?P<paired>{integer}) provided sufficient information to determine glycaemia status at the 15-year follow-up visit; "
        rf"(?P<diabetes>{integer}) men had diabetes at baseline and thus were excluded from progression to diabetes analysis\. "
        r"Progression to diabetes was defined as a participant classified as having normoglycaemia/IFG at study baseline "
        r"and then classified as having diabetes at the 15-year follow-up visit; "
        rf"(?P<progression>{integer}) men were included in this analysis\."
    )
    method = re.match(
        methods_pattern, methods_matches[0][methods_matches[0].index(methods_prefix) :]
    )
    if method is None:
        raise ValueError("Geelong independent denominator semantic binding failed")
    row_totals = {
        "normal_start": int(denominators.group("normal")),
        "ifg_ada_start": int(denominators.group("ifg")),
    }
    cohort = {
        "paired_assessed_n": int(denominators.group("paired")),
        "baseline_diabetes_n": int(denominators.group("diabetes")),
        "progression_analysis_n": int(method.group("progression")),
    }
    if (
        any(n <= 0 for n in row_totals.values())
        or any(sum(counts[row].values()) != row_totals[row] for row in ROWS)
        or int(ifg.group("ifg_total")) != row_totals["ifg_ada_start"]
        or int(method.group("paired")) != cohort["paired_assessed_n"]
        or int(method.group("diabetes")) != cohort["baseline_diabetes_n"]
        or sum(row_totals.values()) != cohort["progression_analysis_n"]
        or cohort["progression_analysis_n"] + cohort["baseline_diabetes_n"]
        != cohort["paired_assessed_n"]
    ):
        raise ValueError("Geelong selected row/cohort denominator disagreement")
    return {
        "counts": counts,
        "row_totals": row_totals,
        "cohort_crosscheck": cohort,
        "locators": {
            "counts": "sec3.4/unique Most men with normoglycaemia paragraph before Of those with IFG-WHO",
            "row_totals": "sec3.4/first paragraph and IFG-ADA row prefix",
            "cohort_crosscheck": "sec2.2/unique Of these assessed-pair and progression-analysis paragraph",
        },
    }


def _vector(values: object, name: str) -> tuple:
    if isinstance(values, np.ma.MaskedArray):
        raise ValueError(f"Geelong {name} must not contain a mask")
    if isinstance(values, np.ndarray):
        if values.ndim != 1:
            raise ValueError(f"Geelong {name} must be a flat vector")
        values = tuple(values)
    elif type(values) in (list, tuple):
        values = tuple(values)
    else:
        raise ValueError(f"Geelong {name} must be a flat vector")
    if len(values) < 2:
        raise ValueError(f"Geelong {name} requires at least two categories")
    return values


def _counts(values: object) -> tuple[int, ...]:
    result = _vector(values, "counts")
    if any(
        isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)) or x < 0
        for x in result
    ):
        raise ValueError("Geelong counts must be nonnegative integers")
    return tuple(int(x) for x in result)


def multinomial_log_likelihood(
    counts: object,
    probabilities: object,
    *,
    probability_sum_absolute_tolerance: float = 1e-12,
) -> float:
    """Normalized row log PMF, with strict simplex validation and no repair.

    Zero counts contribute no logarithm at zero probability. An impossible
    positive count returns negative infinity; a zero-size experiment returns
    log probability zero. Numerical overflow remains an unsupported domain.
    """
    observed, probabilities = _counts(counts), _vector(probabilities, "probabilities")
    tolerance = probability_sum_absolute_tolerance
    if (
        not _number(tolerance)
        or not 0 <= tolerance < 1
        or len(observed) != len(probabilities)
        or any(not _number(p) or not 0 <= p <= 1 for p in probabilities)
    ):
        raise ValueError("Invalid Geelong probability/simplex domain")
    try:
        probability_sum = math.fsum(float(p) for p in probabilities)
    except (OverflowError, ValueError):
        raise ValueError("Unsupported Geelong simplex numerical domain") from None
    if abs(probability_sum - 1) > tolerance:
        raise ValueError("Geelong row probabilities must sum to one")
    if any(
        count > 0 and probability == 0
        for count, probability in zip(observed, probabilities, strict=True)
    ):
        return -math.inf
    try:
        total = sum(observed)
        coefficient = math.lgamma(total + 1) - math.fsum(math.lgamma(x + 1) for x in observed)
        result = math.fsum(
            [coefficient]
            + [
                count * math.log(probability)
                for count, probability in zip(observed, probabilities, strict=True)
                if count
            ]
        )
    except (OverflowError, TypeError, ValueError):
        raise ValueError("Unsupported Geelong multinomial numerical domain") from None
    if not math.isfinite(result) or result > 0:
        raise ValueError("Geelong multinomial numerical evaluation failed")
    return float(result)


def clopper_pearson(count: int, total: int, confidence_level: float) -> tuple[float, float]:
    """Equal-tail cell interval under the declared binomial marginal model."""
    if (
        type(count) is not int
        or type(total) is not int
        or not 0 <= count <= total
        or total <= 0
        or not _number(confidence_level)
        or not 0 < confidence_level < 1
    ):
        raise ValueError("Invalid Geelong cell interval domain")
    alpha = 1 - confidence_level
    try:
        lower = 0.0 if count == 0 else float(beta.ppf(alpha / 2, count, total - count + 1))
        upper = 1.0 if count == total else float(beta.ppf(1 - alpha / 2, count + 1, total - count))
    except (OverflowError, TypeError, ValueError):
        raise ValueError("Unsupported Geelong interval numerical domain") from None
    if not all(math.isfinite(x) for x in (lower, upper)) or not 0 <= lower <= upper <= 1:
        raise ValueError("Geelong interval numerical evaluation failed")
    return lower, upper


def _json_log(value: float) -> dict:
    if value == -math.inf:
        return {"value": None, "status": "zero_probability_event"}
    if not _number(value):
        raise ValueError("Invalid Geelong likelihood value")
    return {"value": float(value), "status": "finite"}


def _reported_structure(reported: dict) -> None:
    if (
        type(reported) is not dict
        or any(
            type(reported.get(key)) is not dict
            for key in ("counts", "row_totals", "cohort_crosscheck")
        )
        or set(reported["counts"]) != set(ROWS)
        or set(reported["row_totals"]) != set(ROWS)
        or set(reported["cohort_crosscheck"]) != set(COHORT_KEYS)
    ):
        raise ValueError("Geelong observed table coverage mismatch")
    for row in ROWS:
        cells = reported["counts"][row]
        total = reported["row_totals"][row]
        if (
            type(cells) is not dict
            or set(cells) != set(DESTINATIONS)
            or any(type(cells[label]) is not int or cells[label] < 0 for label in DESTINATIONS)
            or type(total) is not int
            or total <= 0
            or sum(cells.values()) != total
        ):
            raise ValueError("Geelong explicit categorical row disagreement")
    cohort = reported["cohort_crosscheck"]
    if (
        any(type(n) is not int or n < 0 for n in cohort.values())
        or sum(reported["row_totals"].values()) != cohort["progression_analysis_n"]
        or cohort["progression_analysis_n"] + cohort["baseline_diabetes_n"]
        != cohort["paired_assessed_n"]
    ):
        raise ValueError("Geelong observed cohort reconciliation failed")


def analyze_labels(reported: dict, protocol: dict, *, working_likelihood: bool = True) -> dict:
    """Describe the paired labels and optionally evaluate the frozen working model.

    This pure numerical API does not establish source or clinical eligibility.
    The separate audit verifies provenance and permits only the declared
    observed-label working model, with no clinical parameter activation.
    """
    if type(working_likelihood) is not bool:
        raise ValueError("Geelong working-likelihood mode must be a boolean")
    _reported_structure(reported)
    working = protocol["working_likelihood"]
    confidence, tolerance = (
        working[key] for key in ("confidence_level", "probability_sum_absolute_tolerance")
    )
    if (
        working["family"] != "conditional_row_multinomial"
        or working["assumptions_empirically_established"] is not False
        or not _number(confidence)
        or not 0 < confidence < 1
        or not _number(tolerance)
        or not 0 <= tolerance < 1
    ):
        raise ValueError("Geelong working-model settings disagreement")
    probabilities = {
        row: {
            label: reported["counts"][row][label] / reported["row_totals"][row]
            for label in DESTINATIONS
        }
        for row in ROWS
    }
    result = {
        "observed_labels": {
            "counts": reported["counts"],
            "row_totals": reported["row_totals"],
            "cohort_crosscheck": reported["cohort_crosscheck"],
            "probabilities": probabilities,
            "locators": reported.get("locators", {}),
            "estimand": protocol["estimand"],
            "rate_or_causal_interpretation": False,
        },
        "working_fit": None,
        "joint_covariance": None,
        "intervals": None,
    }
    if not working_likelihood:
        return result
    coordinates = [{"row": row, "destination": label} for row in ROWS for label in DESTINATIONS]
    covariance = [[0.0 for _ in coordinates] for _ in coordinates]
    row_log_likelihoods = {}
    for row_index, row in enumerate(ROWS):
        p = [probabilities[row][label] for label in DESTINATIONS]
        n = reported["row_totals"][row]
        row_log_likelihoods[row] = multinomial_log_likelihood(
            [reported["counts"][row][label] for label in DESTINATIONS],
            p,
            probability_sum_absolute_tolerance=tolerance,
        )
        for j, pj in enumerate(p):
            for k, pk in enumerate(p):
                covariance[row_index * len(DESTINATIONS) + j][row_index * len(DESTINATIONS) + k] = (
                    (pj if j == k else 0.0) - pj * pk
                ) / n
    if any(not math.isfinite(x) for row in covariance for x in row):
        raise ValueError("Geelong covariance numerical evaluation failed")
    cell_confidence = 1 - (1 - confidence) / len(coordinates)
    bounds = [
        list(
            clopper_pearson(
                reported["counts"][c["row"]][c["destination"]],
                reported["row_totals"][c["row"]],
                cell_confidence,
            )
        )
        for c in coordinates
    ]
    joint_log = math.fsum(row_log_likelihoods.values())
    result["working_fit"] = {
        "family": working["family"],
        "probabilities_at_mle": probabilities,
        "row_log_likelihood_at_mle": {
            row: _json_log(value) for row, value in row_log_likelihoods.items()
        },
        "joint_log_likelihood_at_mle": _json_log(joint_log),
        "normalization": "Both row multinomial coefficients are retained",
        "assumptions": working["assumptions"],
        "assumptions_empirically_established": False,
        "conditional_row_totals": True,
        "clinical_transition_model": False,
    }
    result["joint_covariance"] = {
        "coordinates": coordinates,
        "covariance": covariance,
        "unit": "probability_squared",
        "method": "Plug-in conditional row-multinomial covariance",
        "cross_row_independence_assumed": True,
        "singularity_preserved": True,
        "matrix_repair_performed": False,
        "selection_measurement_transport_uncertainty_included": False,
    }
    result["intervals"] = {
        "coordinates": coordinates,
        "bounds": bounds,
        "simultaneous_confidence_level": confidence,
        "effective_cell_confidence_level": cell_confidence,
        "multiplicity": len(coordinates),
        "method": "Bonferroni Clopper-Pearson",
        "sidedness": "two_sided_equal_tail",
        "coverage_scope": "Simultaneous coverage under the declared conditional working model only",
        "selection_measurement_transport_uncertainty_included": False,
    }
    return result


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate Geelong contract JSON key")
        result[key] = value
    return result


def _invalid_constant(_: str) -> None:
    raise ValueError("Nonfinite Geelong contract JSON literal")


def _json(content: bytes) -> dict:
    document = json.loads(
        content, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
    )
    if type(document) is not dict:
        raise ValueError("Geelong contract must be an object")
    return document


def _equal(left: object, right: object) -> bool:
    """Type-exact JSON comparison retains boolean/integer distinctions."""
    return encoded(left) == encoded(right)


def _contract(spec: dict) -> tuple[dict, str]:
    content = Path(spec["protocol_path"]).read_bytes()
    actual = digest(content)
    if actual != PROTOCOL_SHA256 or actual != spec["protocol_sha256"]:
        raise ValueError("Geelong frozen protocol checksum mismatch")
    protocol = _json(content)
    if (
        protocol["schema"] != "demeter-geelong-label-protocol-v1"
        or protocol["source"]["source_id"] != SOURCE_ID
        or protocol["selection"]["start_labels"] != ["normoglycaemia", "ifg_ada"]
        or protocol["scientific_disposition"][
            "observed_label_working_fit_allowed_after_source_reproduction"
        ]
        is not True
        or any(
            value is not False
            for key, value in protocol["scientific_disposition"].items()
            if key != "observed_label_working_fit_allowed_after_source_reproduction"
        )
    ):
        raise ValueError("Geelong frozen source/clinical scope mismatch")
    return protocol, actual


def _registry_metadata(registry: EvidenceRegistry, spec: dict, protocol: dict) -> None:
    pin = protocol["source"]
    source = registry.sources[SOURCE_ID]
    if (
        spec["status"] != "derived"
        or spec["evidence_grade"] != "C"
        or spec["model_role"] != "benchmark_only"
        or spec["source_id"] != SOURCE_ID
        or spec["source_sha256"] != pin["sha256"]
        or type(spec["source_size_bytes"]) is not int
        or spec["source_size_bytes"] != pin["size_bytes"]
        or spec["source_path"] != pin["intended_archive_path"]
        or type(spec["parameter_keys"]) is not list
        or len(spec["parameter_keys"]) != len(PARAMETER_KEYS)
        or set(spec["parameter_keys"]) != PARAMETER_KEYS
        or not _equal(spec["working_likelihood"], protocol["working_likelihood"])
        or spec["clinical_fit_allowed"] is not False
        or spec["engine_activation_allowed"] is not False
        or source.url != pin["url"]
        or source.doi != protocol["bibliography"]["doi"]
        or source.sha256 != pin["sha256"]
        or source.raw_filename != Path(pin["intended_archive_path"]).name
        or source.retrieved_at != datetime.fromisoformat(pin["retrieved_utc"])
        or source.license != pin["rights"]
    ):
        raise ValueError("Geelong registry/source metadata mismatch")


def _registry_agreement(
    registry: EvidenceRegistry, spec: dict, protocol: dict, reported: dict
) -> None:
    selected = {key: reported[key] for key in ("counts", "row_totals", "cohort_crosscheck")}
    if not _equal(spec["analysis"], selected):
        raise ValueError("Geelong registered source observations disagree")
    bundle_bytes = Path(spec["bundle_path"]).read_bytes()
    if digest(bundle_bytes) != spec["bundle_sha256"]:
        raise ValueError("Geelong selected aggregate bundle checksum mismatch")
    bundle = _json(bundle_bytes)
    if (
        any(not _equal(bundle[key], value) for key, value in selected.items())
        or bundle["provenance"]["protocol_sha256"] != PROTOCOL_SHA256
        or bundle["provenance"]["source_sha256"] != protocol["source"]["sha256"]
    ):
        raise ValueError("Geelong selected aggregate bundle disagreement")
    expected = {}
    for row in ROWS:
        n = reported["row_totals"][row]
        expected[f"geelong_{row}_n"] = (n, "people", "observed")
        for label in DESTINATIONS:
            count = reported["counts"][row][label]
            expected[f"geelong_{row}_{label}_n"] = (count, "people", "observed")
            expected[f"geelong_{row}_{label}_probability"] = (
                count / n,
                protocol["estimand"]["unit"],
                "derived",
            )
    expected.update(
        {
            f"geelong_{key}": (value, "people", "observed")
            for key, value in reported["cohort_crosscheck"].items()
        }
    )
    for key, (value, unit, status) in expected.items():
        parameter = registry.parameters[key]
        if (
            parameter.key != key
            or not _number(parameter.value)
            or (
                not _equal(storage_numbers(parameter.value), storage_numbers(value))
                if status == "derived"
                else parameter.value != value
            )
            or parameter.unit != unit
            or parameter.status != status
            or parameter.evidence_grade != "C"
            or parameter.model_role != "benchmark_only"
            or parameter.source_id != SOURCE_ID
            or parameter.source_url != protocol["source"]["url"]
            or parameter.population != protocol["estimand"]["population"]
            or parameter.geography != protocol["estimand"]["geography"]
            or parameter.time_period != protocol["estimand"]["time_period"]
            or parameter.unresolved
            or parameter.uncertainty is None
            or parameter.uncertainty.kind != ("interval" if status == "derived" else "fixed")
        ):
            raise ValueError("Geelong registered parameter definition/value mismatch")


def audit_geelong_labels(
    registry: EvidenceRegistry,
    source_path: Path | None = None,
    *,
    working_likelihood: bool = True,
) -> dict:
    """Return aggregate source reproduction and optional working-model results.

    The offline source, frozen selection, aggregate bundle and registry must
    agree before a working evaluation can be accepted. Failures expose no
    source text, counts, probabilities or untrusted exception details.
    """
    report = {
        "schema_version": 1,
        "analysis_id": DATASET,
        "model_role": "benchmark_only",
        "assessment": "Used-source paired observed-label analysis; not independent clinical validation",
        "source_audit_passed": False,
        "source_audit": {"passed": False},
        "working_fit_performed": False,
        "clinical_transition_fit_performed": False,
        "clinical_fit_allowed": False,
        "engine_activation_allowed": False,
        "annual_generator_identified": False,
        "dietary_effect_identified": False,
        "diagnosed_remission_identified": False,
        "independent_validation": False,
        "scientific_release_ready": False,
        "observed_labels": None,
        "working_fit": None,
        "joint_covariance": None,
        "intervals": None,
        "failure": None,
    }
    stage = "options"
    try:
        if type(working_likelihood) is not bool:
            raise ValueError("Geelong working-likelihood mode must be a boolean")
        stage = "frozen_contract"
        spec = registry.datasets[DATASET]
        protocol, protocol_hash = _contract(spec)
        stage = "registered_metadata"
        _registry_metadata(registry, spec, protocol)
        stage = "selected_source"
        path = Path(spec["source_path"]) if source_path is None else Path(source_path)
        content = path.read_bytes()
        reported = extract_reported(content, protocol)
        stage = "registered_observations"
        _registry_agreement(registry, spec, protocol, reported)
        stage = "working_evaluation"
        results = analyze_labels(reported, protocol, working_likelihood=working_likelihood)
        if working_likelihood:
            for coordinate, bounds in zip(
                results["intervals"]["coordinates"], results["intervals"]["bounds"], strict=True
            ):
                key = f"geelong_{coordinate['row']}_{coordinate['destination']}_probability"
                uncertainty = registry.parameters[key].uncertainty
                if not _equal(
                    storage_numbers([uncertainty.low, uncertainty.high]), storage_numbers(bounds)
                ):
                    raise ValueError("Geelong registered working interval disagreement")
        report.update(results)
        report.update(
            {
                "source_audit_passed": True,
                "source_audit": {
                    "passed": True,
                    "selected_literals_reproduced": True,
                    "same_source_denominators_reconciled": True,
                    "registry_bundle_agreement": True,
                },
                "working_fit_performed": working_likelihood,
                "scientific_disposition": protocol["scientific_disposition"],
                "retained_full_requirements": protocol["retained_full_requirements"],
                "chronology": protocol["chronology"],
                "provenance": {
                    "protocol_sha256": protocol_hash,
                    "source_sha256": digest(content),
                    "source_size_bytes": len(content),
                    "source_id": SOURCE_ID,
                    "bundle_sha256": spec["bundle_sha256"],
                    "implementation_sha256": digest(Path(__file__).read_bytes()),
                    "dataset_definition_sha256": digest(encoded(spec)),
                    "registry_sha256": registry.content_hash,
                    "parameter_definitions_sha256": {
                        key: digest(encoded(registry.parameters[key].model_dump(mode="json")))
                        for key in sorted(PARAMETER_KEYS)
                    },
                    "historical_acquisition": {
                        key: protocol["source"][key]
                        for key in ("url", "retrieved_utc", "sha256", "size_bytes")
                    },
                    "local_byte_check_is_new_acquisition": False,
                    "network_used": False,
                    "participant_records_used": False,
                    "participant_records_exported": False,
                    "registered_working_intervals_reproduced": working_likelihood,
                    "interval_registry_comparison": "Canonical repository storage_numbers precision; not source precision or a clinical tolerance",
                    "derived_report_storage": "Twelve significant digits for portable derived JSON; calculations and source/registry checks precede storage normalization",
                },
            }
        )
    except Exception:
        # Never return exception messages, source snippets, participant identifiers
        # or partial count/fit results from a failed audit.
        report["failure"] = {"stage": stage, "code": "geelong_source_or_contract_failure"}
    return storage_numbers(report)
