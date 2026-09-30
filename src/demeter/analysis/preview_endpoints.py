"""Offline reproduction of PREVIEW binary endpoint facts, without clinical fitting."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

DATASET = "preview_endpoint_benchmark"
ARMS = ("MP_MGI", "HP_LGI")
SOURCE_IDS = {
    "secondary": "preview_secondary2025",
    "protocol2017": "preview_protocol2017",
    "esm": "preview_esm2025",
    "original2021": "preview_original2021",
}
CONTEXT_PARAMETERS = {
    "preview_year1_window_weeks": ("weeks", "protocol2017"),
    "preview_later_window_weeks": ("weeks", "protocol2017"),
    "preview_run_in_weeks": ("weeks", "secondary"),
    "preview_year1_nominal_week": ("weeks", "protocol2017"),
    "preview_year3_nominal_week": ("weeks", "protocol2017"),
    "preview_reported_confidence_level": ("proportion", "secondary"),
}


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate PREVIEW contract JSON key")
        result[key] = value
    return result


def _contract(spec: dict, name: str) -> tuple[dict, str]:
    content = Path(spec[f"{name}_path"]).read_bytes()
    actual_hash = digest(content)
    if actual_hash != spec[f"{name}_sha256"]:
        raise ValueError(f"PREVIEW {name} checksum mismatch")
    try:
        result = json.loads(content, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid PREVIEW {name} JSON") from exc
    if not isinstance(result, dict):
        raise ValueError(f"Invalid PREVIEW {name} object")
    return result, actual_hash


class _Article(HTMLParser):
    """Keep paragraph text and exact heading ancestry; ignore abstract lookalikes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[str, str, str, tuple[str, str]]] = []
        self.paragraphs: list[tuple[tuple[str, str], tuple[str, str], str]] = []
        self.section = ("", "")
        self.subsection = ("", "")
        self.capture: tuple[str, str] | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("h2", "h3", "p"):
            if self.capture is not None:
                raise ValueError("Overlapping PREVIEW article text blocks")
            self.capture = (tag, dict(attrs).get("id") or "")
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture is not None:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture is None or tag != self.capture[0]:
            return
        _, identifier = self.capture
        text = " ".join("".join(self.parts).split())
        if tag == "h2":
            self.headings.append((tag, identifier, text, self.section))
            self.section, self.subsection = (identifier, text), ("", "")
        elif tag == "h3":
            self.headings.append((tag, identifier, text, self.section))
            self.subsection = (identifier, text)
        else:
            self.paragraphs.append((self.section, self.subsection, text))
        self.capture = None

    def paragraph(self, section: tuple[str, str], heading: tuple[str, str], lead: str) -> str:
        matches = [
            item for item in self.headings if item == ("h3", heading[0], heading[1], section)
        ]
        identifiers = [item for item in self.headings if item[1] == heading[0]]
        top = [item for item in self.headings if item[:3] == ("h2", *section)]
        top_identifiers = [item for item in self.headings if item[1] == section[0]]
        paragraphs = [
            text
            for parent, child, text in self.paragraphs
            if parent == section and child == heading and text.startswith(lead)
        ]
        if (
            len(matches) != 1
            or len(identifiers) != 1
            or len(top) != 1
            or len(top_identifiers) != 1
            or len(paragraphs) != 1
        ):
            raise ValueError(f"Expected one PREVIEW {heading[1]} paragraph at exact locator")
        return paragraphs[0]


def _one(pattern: str, text: str, label: str) -> tuple[str, ...]:
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f"Expected one complete PREVIEW {label} literal")
    return matches[0].groups()


def _counts(y: object, n: object, total: object) -> None:
    if (
        any(type(value) is not int for value in (y, n, total))
        or not 0 <= y <= n <= total
        or total <= 0
    ):
        raise ValueError("PREVIEW counts require integers 0 <= y <= n <= N and positive N")


def extract_reported(main_html: bytes, analysis: dict) -> dict:
    """Extract only frozen main endpoint cells, definitions and nominal year labels."""
    article = _Article()
    try:
        article.feed(main_html.decode("utf-8"))
        article.close()
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid PREVIEW UTF-8 HTML") from exc
    if article.capture is not None:
        raise ValueError("Incomplete PREVIEW article text block")
    participants = article.paragraph(
        ("Sec3", "Results"), ("FPar6", "Participants"), "This secondary analysis included "
    )
    hp, mp = _one(
        r"Of these, ([0-9]+) were in the high-protein, low-GI group, and "
        r"([0-9]+) were in the moderate-protein, moderate-GI group\.",
        participants,
        "selected-arm totals",
    )
    selected = {"MP_MGI": int(mp), "HP_LGI": int(hp)}
    outcome = article.paragraph(
        ("Sec2", "Methods"),
        ("FPar4", "Outcomes"),
        "The primary outcome of the current analysis ",
    )
    number = r"[0-9]+(?:\.[0-9]+)?"
    fasting, ogtt = _one(
        rf"Normoglycaemia was defined as normal fasting glucose \(<({number}) mmol/l\) "
        rf"and normal glucose tolerance \(2 h glucose <({number}) mmol/l\)",
        outcome,
        "normal fasting AND OGTT definition",
    )
    remission = article.paragraph(
        ("Sec3", "Results"),
        ("FPar8", "Prediabetes remission"),
        "In the modified intention-to-treat analyses, ",
    )
    expected_lead = (
        "In the modified intention-to-treat analyses, the moderate-protein, moderate-GI "
        "group had a higher rate of prediabetes remission"
    )
    if not remission.startswith(expected_lead) or (
        "than the high-protein, low-GI group (rate of remission at " not in remission
    ):
        raise ValueError("PREVIEW endpoint comparison arm labels/order mismatch")
    pattern = (
        rf"rate of remission at ([0-9]+) years? {number}% \[([0-9]+) of ([0-9]+)\] "
        rf"vs {number}% \[([0-9]+) of ([0-9]+)\]; RR ({number}); "
        rf"95% CI ({number}), ({number});"
    )
    cells = list(re.finditer(pattern, remission))
    expected_years = [item["nominal_year"] for item in analysis["endpoints"]]
    if (
        len(set(expected_years)) != len(expected_years)
        or len(cells) != len(expected_years)
        or [int(match.group(1)) for match in cells] != expected_years
    ):
        raise ValueError("PREVIEW endpoint years missing, duplicated or out of order")
    endpoints = []
    for match in cells:
        year, mp_y, mp_n, hp_y, hp_n = map(int, match.groups()[:5])
        rr, low, high = map(float, match.groups()[5:])
        if not all(math.isfinite(x) for x in (rr, low, high)) or not 0 < low <= rr <= high:
            raise ValueError("PREVIEW reported adjusted RR/CI must be finite and positive")
        if low == high:
            raise ValueError("PREVIEW reported CI must not be degenerate")
        endpoint = {
            "nominal_year": year,
            "MP_MGI": {"normal_count_y": mp_y, "source_endpoint_denominator_n": mp_n},
            "HP_LGI": {"normal_count_y": hp_y, "source_endpoint_denominator_n": hp_n},
            "published_adjusted_RR_MP_vs_HP": rr,
            "published_RR_CI_lower": low,
            "published_RR_CI_upper": high,
        }
        for arm in ARMS:
            _counts(
                endpoint[arm]["normal_count_y"],
                endpoint[arm]["source_endpoint_denominator_n"],
                selected[arm],
            )
        endpoints.append(endpoint)
    if selected != analysis["selected_phase2_cohort_N"] or endpoints != analysis["endpoints"]:
        raise ValueError("PREVIEW source literal cells disagree with frozen analysis")
    return {
        "selected_phase2_cohort_N": selected,
        "endpoints": endpoints,
        "source_thresholds": {
            "fasting_normal_lt_mmol_per_l": float(fasting),
            "ogtt_2hour_normal_lt_mmol_per_l": float(ogtt),
        },
        "locators": {
            "selected_N": "Sec3/Results/FPar6/Participants",
            "endpoints": "Sec3/Results/FPar8/Prediabetes remission",
            "thresholds": "Sec2/Methods/FPar4/Outcomes",
        },
    }


def _parameter_definitions(analysis: dict) -> dict[str, tuple[str, str, str]]:
    definitions = {f"preview_selected_{arm}_n": ("people", "observed", "secondary") for arm in ARMS}
    for endpoint in analysis["endpoints"]:
        year = endpoint["nominal_year"]
        for arm in ARMS:
            for suffix in ("normal_count", "endpoint_n"):
                definitions[f"preview_y{year}_{arm}_{suffix}"] = ("people", "observed", "secondary")
        definitions[f"preview_y{year}_adjusted_rr"] = ("risk_ratio", "estimated", "secondary")
        definitions[f"preview_nominal_year{year}"] = ("years", "observed", "secondary")
    for kind in ("fasting", "ogtt"):
        definitions[f"preview_normal_{kind}_threshold"] = ("mmol/L", "observed", "secondary")
    definitions.update(
        {key: (unit, "observed", source) for key, (unit, source) in CONTEXT_PARAMETERS.items()}
    )
    return definitions


def _registry_agreement(registry: EvidenceRegistry, reported: dict) -> None:
    expected = {
        f"preview_selected_{arm}_n": reported["selected_phase2_cohort_N"][arm] for arm in ARMS
    }
    for endpoint in reported["endpoints"]:
        year = endpoint["nominal_year"]
        for arm in ARMS:
            expected[f"preview_y{year}_{arm}_normal_count"] = endpoint[arm]["normal_count_y"]
            expected[f"preview_y{year}_{arm}_endpoint_n"] = endpoint[arm][
                "source_endpoint_denominator_n"
            ]
        expected[f"preview_nominal_year{year}"] = year
        key = f"preview_y{year}_adjusted_rr"
        parameter = registry.parameters[key]
        if (parameter.value, parameter.uncertainty.low, parameter.uncertainty.high) != (
            endpoint["published_adjusted_RR_MP_vs_HP"],
            endpoint["published_RR_CI_lower"],
            endpoint["published_RR_CI_upper"],
        ):
            raise ValueError(f"PREVIEW registry/source adjusted RR disagreement: {key}")
    expected["preview_normal_fasting_threshold"] = reported["source_thresholds"][
        "fasting_normal_lt_mmol_per_l"
    ]
    expected["preview_normal_ogtt_threshold"] = reported["source_thresholds"][
        "ogtt_2hour_normal_lt_mmol_per_l"
    ]
    for key, value in expected.items():
        if registry.parameters[key].value != value:
            raise ValueError(f"PREVIEW registry/source literal disagreement: {key}")


def _describe(reported: dict) -> list[dict]:
    """Deterministic arithmetic on reconciled labels, with no missingness model."""
    results = []
    for endpoint in reported["endpoints"]:
        arms = {}
        for arm in ARMS:
            total = reported["selected_phase2_cohort_N"][arm]
            y, n = (
                endpoint[arm][key] for key in ("normal_count_y", "source_endpoint_denominator_n")
            )
            _counts(y, n, total)
            missing = total - n
            arms[arm] = {
                "normal_count_y": y,
                "available_endpoint_n": n,
                "selected_cohort_N": total,
                "endpoint_unclassified_N_minus_n": missing,
                "available_endpoint_proportion": y / n if n else None,
                "binary_label_completion_envelope": {
                    "lower": y / total,
                    "upper": (y + missing) / total,
                },
                "sampling_uncertainty": None,
            }
        mp, hp = (arms[arm] for arm in ARMS)
        lower = (
            mp["binary_label_completion_envelope"]["lower"]
            - hp["binary_label_completion_envelope"]["upper"]
        )
        upper = (
            mp["binary_label_completion_envelope"]["upper"]
            - hp["binary_label_completion_envelope"]["lower"]
        )
        mp_p, hp_p = (item["available_endpoint_proportion"] for item in (mp, hp))
        results.append(
            {
                "nominal_year": endpoint["nominal_year"],
                "arms": arms,
                "available_endpoint_absolute_contrast_MP_minus_HP": (
                    mp_p - hp_p if mp_p is not None and hp_p is not None else None
                ),
                "contrast_unit": "proportion_points",
                "binary_label_completion_contrast_envelope": {
                    "lower": lower,
                    "upper": upper,
                    "includes_zero": lower <= 0 <= upper,
                    "allows_MP_lower_than_HP": lower < 0,
                    "allows_MP_higher_than_HP": upper > 0,
                    "kind": "deterministic extreme binary-label completions; not a confidence interval",
                },
                "published_adjusted_effect": {
                    "RR_MP_vs_HP": endpoint["published_adjusted_RR_MP_vs_HP"],
                    "CI_lower": endpoint["published_RR_CI_lower"],
                    "CI_upper": endpoint["published_RR_CI_upper"],
                    "CI_level": "source-reported 95%",
                    "unit": "risk_ratio",
                    "model": "published adjusted multilevel modified Poisson",
                    "reestimated": False,
                    "raw_proportion_ratio_equivalence_claimed": False,
                },
            }
        )
    return results


def audit_preview(registry: EvidenceRegistry, raw: Path) -> dict:
    """Verify contracts and all offline source pins before reproducing any arithmetic."""
    if DATASET not in registry.datasets:
        raise ValueError("Missing PREVIEW endpoint benchmark dataset")
    spec = registry.datasets[DATASET]
    try:
        protocol, protocol_hash = _contract(spec, "protocol")
        amendment, amendment_hash = _contract(spec, "amendment")
        receipt_document, receipts_hash = _contract(spec, "receipts")
        if (
            spec["status"] != "derived"
            or spec["evidence_grade"] != "C"
            or spec["model_role"] != "benchmark_only"
            or spec["analysis"] != protocol["allowed_literal_main_cells"]
            or spec["source_ids"] != SOURCE_IDS
            or spec["clinical_fit_allowed"] is not False
            or spec["engine_activation_allowed"] is not False
            or amendment["parent_protocol"] != spec["protocol_path"]
            or amendment["analytical_selection_changed"] is not False
            or amendment["clinical_fit_or_activation_allowed"] is not False
            or any(value is not False for value in protocol["activation"].values())
            or receipt_document["raw_distribution"] != "fetch_only"
            or receipt_document["participant_records_acquired"] is not False
        ):
            raise ValueError("PREVIEW protocol/registry role, analysis or amendment mismatch")
        pins = {pin["label"]: pin for pin in protocol["source_bytes"]}
        receipts = receipt_document["receipts"]
        if (
            len(pins) != len(protocol["source_bytes"])
            or set(pins) != set(SOURCE_IDS)
            or set(receipts) != set(SOURCE_IDS)
        ):
            raise ValueError("PREVIEW exact four-source coverage mismatch")
        definitions = _parameter_definitions(spec["analysis"])
        if sorted(spec["parameter_keys"]) != sorted(definitions):
            raise ValueError("PREVIEW exact parameter coverage mismatch")
        for key, (unit, status, label) in definitions.items():
            parameter = registry.parameters[key]
            if (
                parameter.model_role != "benchmark_only"
                or parameter.status != status
                or parameter.evidence_grade != "C"
                or parameter.unit != unit
                or parameter.source_id != SOURCE_IDS[label]
                or parameter.source_url != registry.sources[SOURCE_IDS[label]].url
                or parameter.value is None
                or parameter.unresolved
                or parameter.value <= 0
                and unit != "people"
                or parameter.uncertainty is None
                or parameter.uncertainty.kind != ("interval" if status == "estimated" else "fixed")
            ):
                raise ValueError(f"Unsupported PREVIEW benchmark parameter definition: {key}")
        contents = {}
        source_checks = {}
        for label, pin in pins.items():
            source = registry.sources[SOURCE_IDS[label]]
            receipt = receipts[label]
            filename = pin["file"]
            if (
                Path(filename).name != filename
                or "/" in filename
                or "\\" in filename
                or filename in ("", ".", "..")
                or pin["receipt_key"] != label
                or pin["receipt_path"] != spec["receipts_path"]
                or source.raw_filename != filename
                or source.sha256 != pin["sha256"]
                or source.url != receipt["requested_url"]
                or source.doi != receipt["doi"]
                or source.retrieved_at != datetime.fromisoformat(receipt["completed_at_utc"])
                or receipt["http_status"] != 200
                or receipt["sha256"] != pin["sha256"]
                or receipt["size_bytes"] != pin["size_bytes"]
                or receipt.get("cache_filename", Path(receipt.get("cache_file", "")).name)
                != filename
            ):
                raise ValueError(f"PREVIEW {label} source definition/receipt mismatch")
            source_path = raw / filename
            if (
                raw.is_symlink()
                or source_path.is_symlink()
                or (not source_path.resolve().is_relative_to(raw.resolve()))
            ):
                raise ValueError("PREVIEW raw source path must be local without symlink escape")
            content = source_path.read_bytes()
            if digest(content) != pin["sha256"] or len(content) != pin["size_bytes"]:
                raise ValueError(f"PREVIEW {label} source checksum/size mismatch")
            contents[label] = content
            source_checks[label] = {
                "sha256": digest(content),
                "size_bytes": len(content),
                "passed": True,
            }
        reported = extract_reported(contents["secondary"], spec["analysis"])
        if reported["source_thresholds"] != {
            key: protocol["scope"]["source_thresholds"][key]
            for key in reported["source_thresholds"]
        }:
            raise ValueError("PREVIEW threshold literal differs from frozen source definition")
        _registry_agreement(registry, reported)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Incomplete or invalid PREVIEW audit contract/registry") from exc
    results = _describe(reported)
    return {
        "schema_version": 1,
        "analysis_id": DATASET,
        "model_role": "benchmark_only",
        "assessment": "used-source reproduction; not preregistration or independent validation",
        "scientific_release_ready": False,
        "population": protocol["scope"]["population"],
        "scope": protocol["scope"],
        "results": {
            "source_reproduction_passed": True,
            "source_checks": source_checks,
            "literal_main_cells": reported,
            "assessments": results,
            "joint_year_covariance": None,
            "pooled_inferential_effect": None,
            "registered_source_context": {
                key: {
                    "value": registry.parameters[key].value,
                    "unit": registry.parameters[key].unit,
                    "source_id": registry.parameters[key].source_id,
                    "independently_reextracted": False,
                    "used_in_calculation": False,
                }
                for key in CONTEXT_PARAMETERS
            },
        },
        "completion_interpretation": {
            "target": "binary source-endpoint label completion for selected phase2 cohort",
            "clinical_alive_and_normal_composite_interpretation_available": False,
            "death_counts": None,
            "death_status_inferred": False,
            "unclassified_means_dropout_or_death": False,
            "unknown_treatment_among_assessed_expands_N_minus_n": False,
            "missingness_model": None,
            "imputation": False,
            "definition": protocol["outputs_after_freeze"]["bounds_definition"],
            "amendment": amendment["clarifications"]["envelope_unknowns"],
        },
        "published_primary_null_context": protocol["null_and_opposing_results"],
        "denominator_reconciliation": protocol["denominator_reconciliation"],
        "failure_dispositions": protocol["failure_dispositions"],
        "source_consistency": {
            "main_frozen_count_constraints": "passed",
            "auxiliary_completer_denominator_consistency": "unresolved source conflict",
            "original_and_secondary_source_version_consistency": "unresolved; separate estimands",
            "auxiliary_cells_reextracted_or_repaired": False,
            "overall_clinical_acceptance": False,
        },
        "identification_limits": protocol["identification_limits"],
        "clarifications": amendment["clarifications"],
        "activation": protocol["activation"],
        "provenance": {
            "sources": {
                label: registry.sources[source_id].model_dump(mode="json")
                for label, source_id in SOURCE_IDS.items()
            },
            "source_receipts": receipts,
            "protocol_sha256": protocol_hash,
            "amendment_sha256": amendment_hash,
            "receipts_sha256": receipts_hash,
            "dataset_definition_sha256": digest(encoded(spec)),
            "parameter_definitions_sha256": {
                key: digest(encoded(registry.parameters[key].model_dump(mode="json")))
                for key in definitions
            },
            "implementation_sha256": digest(Path(__file__).read_bytes()),
            "individual_records_used": False,
            "raw_redistributed": False,
            "clinical_fit_performed": False,
        },
    }
