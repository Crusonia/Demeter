"""Pinned Whitehall FPG labels and an explicitly assumed endpoint likelihood.

Neither the observed proportion nor the working binomial model identifies a
clinical transition rate. Publications remain offline, fetch-only source bytes.
"""

from __future__ import annotations

import io
import json
import math
import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader
from scipy.stats import beta, binom

from demeter.data.ingest import digest
from demeter.data.nhanes import encoded
from demeter.schema import EvidenceRegistry

DATASET = "whitehall_fpg_endpoint"
PROTOCOL_SHA256 = "6452943e6fc9e233946dc4fc3ef155bc2e2ec9583936603ca5d544547ee4d690"
RECEIPTS_SHA256 = "fb3580aeceb37d58ca5212881682d0d5a42455628907e857e72079a595d10a42"
SOURCE_IDS = {
    "main_static_pdf": "whitehall_main2019",
    "supplement_pdf": "whitehall_esm2019",
}
PARAMETER_KEYS = {
    "whitehall_fpg_normal_label_n",
    "whitehall_fpg_nonreversion_label_n",
    "whitehall_fpg_paired_n",
    "whitehall_fpg_normal_label_proportion",
}


def _counts(y: object, n: object) -> None:
    if type(y) is not int or type(n) is not int or not 0 <= y <= n or n <= 0:
        raise ValueError("Whitehall requires integer counts 0 <= y <= N and N > 0")


def _number(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def binomial_log_likelihood(y: int, n: int, p: float) -> float:
    """Normalized log PMF; impossible boundary observations return -infinity."""
    _counts(y, n)
    if not _number(p) or not 0 <= p <= 1:
        raise ValueError("Whitehall probability must be a finite number in [0, 1]")
    try:
        result = float(binom.logpmf(y, n, p))
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("Whitehall binomial numerical domain is unsupported") from exc
    if result != -math.inf and not math.isfinite(result):
        raise ValueError("Whitehall binomial numerical evaluation failed")
    return result


def clopper_pearson(y: int, n: int, confidence_level: float) -> tuple[float, float]:
    """Equal-tail interval within the declared binomial experiment only."""
    _counts(y, n)
    if not _number(confidence_level) or not 0 < confidence_level < 1:
        raise ValueError("Whitehall confidence level must be strictly between zero and one")
    alpha = 1 - confidence_level
    try:
        lower = 0.0 if y == 0 else float(beta.ppf(alpha / 2, y, n - y + 1))
        upper = 1.0 if y == n else float(beta.ppf(1 - alpha / 2, y + 1, n - y))
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("Whitehall interval numerical domain is unsupported") from exc
    if not all(math.isfinite(x) for x in (lower, upper)) or not 0 <= lower <= upper <= 1:
        raise ValueError("Whitehall interval numerical evaluation failed")
    return lower, upper


def json_log_likelihood(value: float) -> dict:
    """Keep the mathematical impossible-event boundary out of JSON numerics."""
    if value == -math.inf:
        return {"value": None, "status": "zero_probability_event"}
    if not _number(value):
        raise ValueError("Invalid Whitehall log likelihood")
    return {"value": value, "status": "finite"}


def toy_normal_endpoint(a: float, b: float, time: float) -> float:
    """Synthetic two-state CTMC starting in P; units are arbitrary toy units."""
    if not all(_number(x) for x in (a, b, time)) or a < 0 or b < 0 or time <= 0:
        raise ValueError("Invalid synthetic two-state domain")
    total = a + b
    if not math.isfinite(total):
        raise ValueError("Invalid synthetic rate total")
    return 0.0 if total == 0 else b / total * -math.expm1(-total * time)


def synthetic_ambiguity_witness(fixture: dict) -> tuple[dict, dict]:
    """Closed-form software witness, never conditioned on Whitehall counts."""
    if (
        fixture.get("status") != "synthetic"
        or fixture.get("evidence_grade") != "E"
        or fixture.get("role") != "software_validation_only"
        or fixture.get("time_unit") != "toy_time_unit"
        or fixture.get("rate_unit") != "per_toy_time_unit"
    ):
        raise ValueError("Unlabeled synthetic ambiguity fixture")
    q, time, tolerance = (
        fixture.get(key) for key in ("target_endpoint_probability", "time", "absolute_tolerance")
    )
    sums = fixture.get("total_rates")
    if (
        not all(_number(x) for x in (q, time, tolerance))
        or not 0 < q < 1
        or time <= 0
        or tolerance <= 0
        or type(sums) is not list
        or len(sums) != 2
        or not all(_number(s) and s > 0 for s in sums)
        or sums[0] == sums[1]
    ):
        raise ValueError("Invalid synthetic ambiguity fixture")
    results = []
    for total in sums:
        fraction = -math.expm1(-total * time)
        if fraction < q:
            raise ValueError("Synthetic target is outside the selected rate-sum domain")
        b = q * total / fraction
        a = total - b
        endpoint = toy_normal_endpoint(a, b, time)
        if abs(endpoint - q) > tolerance:
            raise ValueError("Synthetic closed-form witness failed")
        results.append(
            {
                "a": a,
                "b": b,
                "endpoint_probability": endpoint,
                "time_unit": "toy_time_unit",
                "source_counts_used": False,
                "clinical_rate_interpretation": False,
            }
        )
    return results[0], results[1]


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate Whitehall contract JSON key")
        result[key] = value
    return result


def _invalid_constant(_: str) -> None:
    raise ValueError("Nonfinite Whitehall contract JSON literal")


def _contract(spec: dict, name: str, frozen_hash: str) -> tuple[dict, str]:
    content = Path(spec[f"{name}_path"]).read_bytes()
    actual = digest(content)
    if actual != spec[f"{name}_sha256"] or actual != frozen_hash:
        raise ValueError("Whitehall frozen contract checksum mismatch")
    document = json.loads(
        content, object_pairs_hook=_unique_object, parse_constant=_invalid_constant
    )
    if type(document) is not dict:
        raise ValueError("Whitehall contract must be an object")
    return document, actual


def _equal(left: object, right: object) -> bool:
    """JSON comparison preserves boolean versus integer distinctions."""
    return encoded(left) == encoded(right)


def _pdf(content: bytes, page_count: int) -> PdfReader:
    if type(content) is not bytes or not content.startswith(b"%PDF-"):
        raise ValueError("Invalid Whitehall PDF")
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or len(reader.pages) != page_count:
            raise ValueError("Unexpected Whitehall document structure")
    except Exception:
        raise ValueError("Invalid Whitehall PDF structure") from None
    return reader


def _text(value: str) -> str:
    return " ".join(value.split())


def extract_reported(main_pdf: bytes, supplement_pdf: bytes, protocol: dict) -> dict:
    """Capture only the two selected N cells and required same-source crosscheck.

    The audit verifies frozen bytes before calling this pure extraction helper.
    No values from later event/rate columns or overlapping categories are kept.
    """
    structure = protocol["source_structure"]
    main = _pdf(main_pdf, structure["main_page_count"])
    supplement = _pdf(supplement_pdf, structure["supplement_page_count"])
    identity = _text(main.pages[0].extract_text())
    if (
        protocol["bibliography"]["title"] not in identity
        or protocol["bibliography"]["doi"] not in identity
    ):
        raise ValueError("Whitehall main document identity mismatch")
    page = supplement.pages[structure["supplement_table_page"] - 1]
    if page.rotation != structure["supplement_page_rotation_degrees"]:
        raise ValueError("Whitehall selected table orientation mismatch")
    text = _text(page.extract_text())
    heading = structure["table_heading"]
    start, end = structure["block_start"], structure["block_end"]
    if (
        len(re.findall(r"\b" + re.escape(heading) + r"\b", text)) != 1
        or text.count(start) != 1
        or text.count(end) != 1
        or not text.index(heading) < text.index(start) < text.index(end)
    ):
        raise ValueError("Whitehall selected table/block binding failed")
    header = text[text.index(heading) : text.index(start)]
    expected_header = (
        r"\b"
        + re.escape(structure["selected_column"])
        + r"\s+"
        + re.escape(structure["next_column"])
        + r"\b"
    )
    if len(re.findall(expected_header, header)) != 1 or len(re.findall(r"\bN\b", header)) != 1:
        raise ValueError("Whitehall selected N column/header binding failed")
    body = text[text.index(start) + len(start) : text.index(end)]
    positions = []
    values = []
    for label in structure["source_row_order"]:
        if body.count(label) != 1:
            raise ValueError("Whitehall selected row missing or duplicated")
        positions.append(body.index(label))
        match = re.match(re.escape(label) + r"\s+([0-9]+)(?=\s|$)", body[body.index(label) :])
        if match is None:
            raise ValueError("Whitehall selected N is not an integer literal")
        values.append(int(match.group(1)))
    if positions != sorted(positions) or structure["source_row_order"] != [
        "Prediabetes or diabetes",
        "Normoglycaemia",
    ]:
        raise ValueError("Whitehall selected row order mismatch")
    if len(values) != 2:
        raise ValueError("Whitehall selected count coverage mismatch")
    nonreversion, normal = values
    crosscheck = protocol["required_main_crosscheck"]
    if crosscheck.get("required") is not True:
        raise ValueError("Whitehall main crosscheck must be required")
    paragraph = _text(main.pages[2].extract_text())
    # This is the sole orthographic substitution authorized by the freeze.
    paragraph = paragraph.replace("pre- diabetes", "prediabetes")
    starts = list(re.finditer(r"FPG criterion Among", paragraph))
    if len(starts) != 1:
        raise ValueError("Whitehall unique main prefix binding failed")
    match = re.match(
        crosscheck["prefix_regex_after_explicit_whitespace_and_linehyphen_normalization"],
        paragraph[starts[0].start() :],
    )
    if match is None:
        raise ValueError("Whitehall main crosscheck prefix malformed")
    main_n, main_y = int(match.group("denominator")), int(match.group("normal"))
    paired = normal + nonreversion
    _counts(normal, paired)
    _counts(main_y, main_n)
    if (main_n, main_y) != (paired, normal):
        raise ValueError("Whitehall main/supplement count mismatch")
    return {
        "counts": {"normal_label_n": normal, "nonreversion_label_n": nonreversion},
        "paired_n": paired,
        "main_crosscheck": {"normal_label_n": main_y, "paired_n": main_n},
        "locators": {
            "counts": "ESMTable1/physicalPDFp1/ByFPG/N",
            "main_crosscheck": "main/physicalPDFp3/unique FPG criterion Among prefix",
        },
    }


def _source_bytes(
    registry: EvidenceRegistry, raw: Path, protocol: dict, receipts: dict
) -> tuple[dict, dict]:
    required = protocol["source_documents"]["required_source_receipts"]
    if (
        not _equal(protocol["source_documents"]["required_offline_sources"], list(SOURCE_IDS))
        or set(required) != set(SOURCE_IDS)
        or set(receipts["required_sources"]) != set(SOURCE_IDS)
        or not _equal(required, receipts["required_sources"])
        or not _equal(receipts["required_numerical_source_keys"], list(SOURCE_IDS))
        or receipts["distribution"] != "fetch_only"
        or protocol["source_documents"]["no_network_at_analysis_runtime"] is not True
    ):
        raise ValueError("Whitehall required source/receipt coverage mismatch")
    contents, checks = {}, {}
    for label, source_id in SOURCE_IDS.items():
        pin = required[label]
        source = registry.sources[source_id]
        filename = pin["cache_filename"]
        if (
            type(filename) is not str
            or Path(filename).name != filename
            or "/" in filename
            or "\\" in filename
            or filename in ("", ".", "..")
            or source.raw_filename != filename
            or source.sha256 != pin["sha256"]
            or source.url != pin["url"]
            or source.doi != protocol["bibliography"]["doi"]
            or source.retrieved_at != datetime.fromisoformat(pin["retrieved_utc"])
            or source.retrieved_at.utcoffset() is None
            or pin["status"] != 200
            or type(pin["status"]) is not int
            or pin["content_type"] != "application/pdf"
            or type(pin["size_bytes"]) is not int
            or pin["size_bytes"] <= 0
            or pin["distribution"] != "fetch_only"
        ):
            raise ValueError("Whitehall source metadata mismatch")
        started = datetime.fromisoformat(pin["retrieval_started_utc"])
        if started.utcoffset() is None or started > source.retrieved_at:
            raise ValueError("Whitehall historical receipt chronology mismatch")
        path = raw / filename
        if (
            raw.is_symlink()
            or path.is_symlink()
            or not path.resolve().is_relative_to(raw.resolve())
        ):
            raise ValueError("Whitehall local raw path must not escape through a symlink")
        content = path.read_bytes()
        if digest(content) != pin["sha256"] or len(content) != pin["size_bytes"]:
            raise ValueError("Whitehall local source checksum/size mismatch")
        contents[label] = content
        checks[label] = {"sha256": digest(content), "size_bytes": len(content), "passed": True}
    return contents, checks


def _registry_agreement(registry: EvidenceRegistry, spec: dict, reported: dict) -> None:
    y, q = (reported["counts"][key] for key in ("normal_label_n", "nonreversion_label_n"))
    n = reported["paired_n"]
    expected = {
        "whitehall_fpg_normal_label_n": (y, "people", "observed", "whitehall_esm2019"),
        "whitehall_fpg_nonreversion_label_n": (q, "people", "observed", "whitehall_esm2019"),
        "whitehall_fpg_paired_n": (n, "people", "derived", "whitehall_esm2019"),
        "whitehall_fpg_normal_label_proportion": (
            y / n,
            "proportion",
            "derived",
            "whitehall_esm2019",
        ),
    }
    if not _equal(spec["analysis"]["counts"], reported["counts"]):
        raise ValueError("Whitehall registered literal counts disagree")
    for key, (value, unit, status, source_id) in expected.items():
        parameter = registry.parameters[key]
        if (
            parameter.value != value
            or parameter.unit != unit
            or parameter.status != status
            or parameter.evidence_grade != "C"
            or parameter.model_role != "benchmark_only"
            or parameter.source_id != source_id
            or parameter.source_url != registry.sources[source_id].url
            or parameter.unresolved
            or parameter.uncertainty is None
            or parameter.uncertainty.kind != ("interval" if unit == "proportion" else "fixed")
        ):
            raise ValueError("Whitehall parameter definition/value mismatch")


def audit_whitehall_endpoint(
    registry: EvidenceRegistry, raw_directory: Path, *, working_likelihood: bool = True
) -> dict:
    """Return a JSON-safe aggregate pass or failure; failure never performs a fit."""
    report = {
        "schema_version": 1,
        "analysis_id": DATASET,
        "model_role": "benchmark_only",
        "assessment": "used-source reproduction; not preregistration or independent validation",
        "source_audit_passed": False,
        "working_fit_performed": False,
        "clinical_transition_fit_performed": False,
        "engine_activation_allowed": False,
        "scientific_release_ready": False,
        "source_checks": {},
        "endpoint": None,
        "working_fit": None,
        "interval": None,
        "failure": None,
    }
    stage = "options"
    try:
        if type(working_likelihood) is not bool:
            raise ValueError("Whitehall analysis mode must be a boolean")
        stage = "contract"
        spec = registry.datasets[DATASET]
        protocol, protocol_hash = _contract(spec, "protocol", PROTOCOL_SHA256)
        receipts, receipt_hash = _contract(spec, "receipts", RECEIPTS_SHA256)
        analysis = spec["analysis"]
        confidence_setting = analysis["confidence_setting"]
        numerical = analysis["numerical_comparison"]
        if (
            spec.get("model_role") != "benchmark_only"
            or spec.get("clinical_fit_allowed") is not False
            or spec.get("engine_activation_allowed") is not False
            or not _equal(spec["source_ids"], SOURCE_IDS)
            or type(spec["parameter_keys"]) is not list
            or len(spec["parameter_keys"]) != len(PARAMETER_KEYS)
            or set(spec["parameter_keys"]) != PARAMETER_KEYS
            or not _equal(analysis["source_structure"], protocol["source_structure"])
            or type(analysis["confidence_level"]) is not float
            or analysis["confidence_level"] != protocol["interval_design"]["confidence_level"]
            or confidence_setting.get("status") != "synthetic"
            or confidence_setting.get("evidence_grade") != "E"
            or confidence_setting.get("role") != "analysis_design_choice"
            or confidence_setting.get("not_source_estimate") is not True
            or type(confidence_setting.get("rationale")) is not str
            or not confidence_setting["rationale"].strip()
            or numerical.get("status") != "synthetic"
            or numerical.get("evidence_grade") != "E"
            or numerical.get("role") != "software_numerical_validation"
            or numerical.get("source_precision_claim") is not False
            or type(numerical.get("absolute_tolerance")) is not float
            or numerical["absolute_tolerance"] != 1e-12
            or any(
                v is not False
                for k, v in protocol["failure_and_reporting"]["scope_flags"].items()
                if k not in ("used_source_reproduction",)
            )
        ):
            raise ValueError("Whitehall dataset scope/metadata disagreement")
        stage = "sources"
        contents, source_checks = _source_bytes(registry, Path(raw_directory), protocol, receipts)
        report["source_checks"] = source_checks
        stage = "selected_source_structure"
        reported = extract_reported(
            contents["main_static_pdf"], contents["supplement_pdf"], protocol
        )
        stage = "registry_agreement"
        _registry_agreement(registry, spec, reported)
        y, n = reported["counts"]["normal_label_n"], reported["paired_n"]
        # All source/metadata/label guards precede the optional inferential calculation.
        stage = "working_evaluation"
        interval = None
        working = None
        if working_likelihood:
            lower, upper = clopper_pearson(y, n, analysis["confidence_level"])
            uncertainty = registry.parameters["whitehall_fpg_normal_label_proportion"].uncertainty
            tolerance = numerical["absolute_tolerance"]
            if not all(
                _number(actual) and math.isclose(actual, expected, rel_tol=0, abs_tol=tolerance)
                for actual, expected in (
                    (uncertainty.low, lower),
                    (uncertainty.high, upper),
                )
            ):
                raise ValueError("Whitehall registered working interval disagreement")
            interval = {
                "lower": lower,
                "upper": upper,
                "confidence_level": analysis["confidence_level"],
                "method": "Clopper–Pearson",
                "sidedness": "two_sided_equal_tail",
                "role": "conditional binomial working-model interval, not source-reported",
                "empirical_selection_or_clinical_coverage_established": False,
                "registry_agreement_numerical_tolerance": tolerance,
                "tolerance_is_source_precision": False,
            }
            working = {
                "family": "Binomial",
                "p_hat": y / n,
                "log_likelihood_at_mle": json_log_likelihood(binomial_log_likelihood(y, n, y / n)),
                "assumptions": protocol["working_likelihood"]["assumptions"],
                "assumptions_empirically_established": False,
                "clinical_transition_model": False,
            }
        report.update(
            {
                "source_audit_passed": True,
                "working_fit_performed": working_likelihood,
                "endpoint": {
                    **reported,
                    "observed_normal_label_proportion": y / n,
                    "conditioning": protocol["estimand_and_descriptive_functional"]["definition"],
                },
                "working_fit": working,
                "interval": interval,
                "population_and_observation_definition": protocol[
                    "population_and_observation_definition"
                ],
                "identification_limits": protocol["failure_and_reporting"][
                    "unresolved_consequences"
                ],
                "scope_flags": protocol["failure_and_reporting"]["scope_flags"],
                "provenance": {
                    "protocol_sha256": protocol_hash,
                    "receipts_sha256": receipt_hash,
                    "implementation_sha256": digest(Path(__file__).read_bytes()),
                    "dataset_definition_sha256": digest(encoded(spec)),
                    "registry_sha256": registry.content_hash,
                    "parameter_definitions_sha256": {
                        key: digest(encoded(registry.parameters[key].model_dump(mode="json")))
                        for key in sorted(PARAMETER_KEYS)
                    },
                    "historical_source_receipts": receipts["required_sources"],
                    "local_byte_verification_is_new_acquisition": False,
                    "network_used": False,
                    "participant_records_used": False,
                    "raw_redistributed": False,
                    "registered_working_interval_reproduced": working_likelihood,
                },
            }
        )
    except Exception:
        # Never publish parser diagnostics, source text, untrusted identifiers or paths.
        report["failure"] = {"stage": stage, "code": "whitehall_source_or_contract_failure"}
    return report
