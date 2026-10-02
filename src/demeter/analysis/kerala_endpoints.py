"""Source-native recorded-endpoint completion; no clinical hazard or causal fit."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from demeter.analysis import kerala_coverage as coverage
from demeter.analysis.endpoint_bounds import (
    endpoint_bounds,
    endpoint_difference_bounds,
    endpoint_tipping_point,
)
from demeter.analysis.kerala_registration import verify_registered

DATASET = "kerala_endpoint_bounds"
SOURCE = "kerala2018_primary_publication"
ARMS = ("Control", "Intervention")
QUANTITIES = ("assigned", "known_endpoints", "recorded_events", "reported_cumulative_deaths")


def _load(root: Path, spec: dict, prefix: str) -> dict:
    path = (root / spec[prefix + "_path"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Endpoint artifact path escapes project")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != spec[prefix + "_sha256"]:
        raise ValueError("Endpoint artifact checksum mismatch")
    return json.loads(content)


def _registered_counts(registry, root: Path) -> tuple[dict, dict]:
    spec = registry.datasets[DATASET]
    keys = {f"kerala_{arm.lower()}_{quantity}_n" for arm in ARMS for quantity in QUANTITIES}
    if (
        spec["model_role"] != "benchmark_only"
        or spec["source_id"] != SOURCE
        or set(spec["parameter_keys"]) != keys
    ):
        raise ValueError("Endpoint registry scope mismatch")
    coverage._gates({key: spec[key] for key in coverage.GATES})
    protocol = _load(root, spec, "protocol")
    amendment = _load(root, spec, "amendment")
    bundle = _load(root, spec, "bundle")
    if (
        protocol["protocol_id"] != "kerala-recorded-endpoint-bounds-v1"
        or amendment["protocol_id"] != protocol["protocol_id"]
        or protocol["source_id"] != SOURCE
        or bundle["source_id"] != SOURCE
        or bundle["source_sha256"] != registry.sources[SOURCE].sha256
        or protocol["source_sha256"] != bundle["source_sha256"]
        or bundle["death_counts_complete_for_assigned_cohort_verified"] is not False
        or any(
            protocol[key] is not False
            for key in (
                "clinical_fit_ready",
                "causal_effect_identified",
                "national_transport_ready",
                "engine_activation_allowed",
            )
        )
    ):
        raise ValueError("Endpoint source or scientific boundary mismatch")
    parent = registry.datasets["kerala_source_admission"]
    if protocol["parent_representation_sha256"] != parent["representation_sha256"]:
        raise ValueError("Endpoint parent representation mismatch")
    counts = bundle["counts"]
    if set(counts) != set(ARMS):
        raise ValueError("Endpoint assignment labels mismatch")
    for arm, values in counts.items():
        if set(values) != set(QUANTITIES) or any(
            type(v) is not int or v < 0 for v in values.values()
        ):
            raise ValueError("Endpoint counts must be exact nonnegative integers")
        for quantity, value in values.items():
            parameter = registry.parameters[f"kerala_{arm.lower()}_{quantity}_n"]
            if (
                parameter.value != value
                or parameter.unresolved
                or parameter.status != "observed"
                or parameter.evidence_grade != "C"
                or parameter.model_role != "benchmark_only"
                or parameter.unit != "people"
                or parameter.source_id != SOURCE
                or parameter.source_url != registry.sources[SOURCE].url
                or parameter.uncertainty is None
                or parameter.uncertainty.kind != "fixed"
            ):
                raise ValueError("Endpoint parameter/source transcription mismatch")
    return counts, spec


def _publication_counts(content: bytes, counts: dict) -> None:
    """Reproduce six textual source counts; Figure 1 is an image, not parsed death text."""
    from io import BytesIO
    from pypdf import PdfReader

    text = " ".join(PdfReader(BytesIO(content)).pages[9].extract_text().split())
    assigned = re.findall(
        r"1,007 \((\d+) in the control group and (\d+) in the intervention group\)", text
    )
    events = re.findall(
        r"\((\d+)/(\d+)\) of participants in the control group and [\d.]+% "
        r"\((\d+)/(\d+)\) of participants in the intervention group",
        text,
    )
    expected_assigned = tuple(str(counts[arm]["assigned"]) for arm in ARMS)
    expected_events = tuple(
        str(counts[arm][q]) for arm in ARMS for q in ("recorded_events", "known_endpoints")
    )
    if assigned != [expected_assigned] or events != [expected_events]:
        raise ValueError("Endpoint primary publication transcription disagreement")


def _workbook_counts(path: Path) -> dict:
    fields = ["participant_id", "arms0", "tot_diab_incidence"]
    rows = coverage._selected_rows(path, fields)
    grouped, missing = coverage._group_rows(rows)
    if missing or any(len(records) != 1 for records in grouped.values()):
        raise ValueError("Endpoint source linkage is missing or nonunique")
    cells = {arm: Counter() for arm in ARMS}
    for records in grouped.values():
        row = records[0]
        arm, flag = row["arms0"], row["tot_diab_incidence"]
        if arm not in {("string", value) for value in ARMS}:
            raise ValueError("Endpoint assignment label is unsupported")
        if flag not in {("string", "Yes"), ("string", "No"), ("absent", None)}:
            raise ValueError("Endpoint flag is unsupported")
        cells[arm[1]][flag] += 1
    return {
        arm: {
            "assigned": sum(values.values()),
            "known_endpoints": values[("string", "Yes")] + values[("string", "No")],
            "recorded_events": values[("string", "Yes")],
        }
        for arm, values in cells.items()
    }


def _contrast_and_tipping(counts: dict, *, assume_complete_deaths: bool) -> dict:
    control, intervention = (counts[arm] for arm in ARMS)
    nc, ni = control["assigned"], intervention["assigned"]
    yc, yi = control["recorded_events"], intervention["recorded_events"]
    uc, ui = nc - control["known_endpoints"], ni - intervention["known_endpoints"]
    if not nc or not ni:
        return {"risk_difference": None, "missing_endpoint_completions": None}
    first, second = (ni, intervention["known_endpoints"], yi), (nc, control["known_endpoints"], yc)
    difference = endpoint_difference_bounds(
        first,
        second,
        first_deaths=intervention["reported_cumulative_deaths"],
        second_deaths=control["reported_cumulative_deaths"],
        assume_complete_deaths=assume_complete_deaths,
    )
    signs = Counter()
    for c in range(uc + 1):
        for i in range(ui + 1):
            cross_product = (yi + i) * nc - (yc + c) * ni
            signs["lower" if cross_product < 0 else "higher" if cross_product > 0 else "equal"] += 1
    return {
        "direction": "Intervention minus Control",
        "fraction_difference": difference,
        "all_assigned_direction_unresolved": difference["all_assigned"]["lower"]["numerator"]
        <= 0
        <= difference["all_assigned"]["upper"]["numerator"],
        "tipping_sensitivities": {
            "control_unknown_all_negative": endpoint_tipping_point(
                first, second, second_unknown_events=0
            ),
            "control_unknown_all_positive": endpoint_tipping_point(
                first, second, second_unknown_events=uc
            ),
        },
        "missing_endpoint_completions": {
            "lower_intervention_fraction": signs["lower"],
            "higher_intervention_fraction": signs["higher"],
            "equal_fraction": signs["equal"],
            "compatible_aggregate_pairs": (uc + 1) * (ui + 1),
            "pairs_have_equal_probability": False,
            "interpretation": "Counts of aggregate missing-positive-count pairs, not participant assignments, probabilities, posterior weights or sampling intervals.",
        },
    }


def audit_kerala_endpoints(
    registry,
    root: Path,
    *,
    source_cache: Path | None = None,
    publication: Path | None = None,
    assume_complete_deaths: bool = False,
) -> dict:
    """Calculate feasible completions offline; optionally cross-check exact public sources."""
    if type(assume_complete_deaths) is not bool:
        raise ValueError("Complete-death assumption must be explicitly boolean")
    counts, spec = _registered_counts(registry, root)
    parent = verify_registered(
        registry, root, source_cache, replay_aggregates=source_cache is not None
    )
    source_reproduced = publication_reproduced = None
    if source_cache is not None:
        receipt = json.loads(
            (root / "docs/validation/kerala-source-acquisition-receipts-v1.json").read_bytes()
        )
        actual = _workbook_counts(source_cache / receipt["workbook_receipts"][0]["raw_filename"])
        expected = {arm: {q: values[q] for q in QUANTITIES[:3]} for arm, values in counts.items()}
        if actual != expected:
            raise ValueError("Endpoint workbook/publication denominator disagreement")
        source_reproduced = True
    if publication is not None:
        content = publication.read_bytes()
        if hashlib.sha256(content).hexdigest() != registry.sources[SOURCE].sha256:
            raise ValueError("Endpoint publication checksum mismatch")
        _publication_counts(content, counts)
        publication_reproduced = True
    arms = {
        arm: endpoint_bounds(
            values["assigned"],
            values["known_endpoints"],
            values["recorded_events"],
            cumulative_deaths=values["reported_cumulative_deaths"],
            assume_complete_deaths=assume_complete_deaths,
        )
        for arm, values in counts.items()
    }
    return {
        "schema_version": 1,
        "source_id": SOURCE,
        "source_sha256": registry.sources[SOURCE].sha256,
        "protocol_sha256": spec["protocol_sha256"],
        "amendment_sha256": spec["amendment_sha256"],
        "bundle_sha256": spec["bundle_sha256"],
        "interpretation": "Used-source recorded-endpoint finite-cohort bounds; not clinical hazards, confidence intervals, isolated food effects or independent validation.",
        "source_audit_passed": True,
        "registered_parent_verified": parent["registered_artifacts_verified"],
        "public_workbook_endpoint_counts_reproduced": source_reproduced,
        "publication_text_counts_reproduced": publication_reproduced,
        "reported_deaths": {
            "source_locator": "Figure 1, PDF page 11",
            "automatically_extracted_from_figure": False,
            "complete_ascertainment_verified": False,
            "unlinked_to_endpoint_records": True,
        },
        "complete_death_total_assumption_supplied": assume_complete_deaths,
        "arms": arms,
        "regimen_contrast": _contrast_and_tipping(
            counts, assume_complete_deaths=assume_complete_deaths
        ),
        "participant_records_exported": False,
        "labeled_multiwave_tuples_exported": False,
        "clinical_fit_ready": False,
        "causal_effect_identified": False,
        "national_transport_ready": False,
        "engine_activation_allowed": False,
    }
