"""Replay two published UPDATE aggregate rows; no clinical model or source refit.

I-11 -> F-08 -> T-08. Source-summary reproduction tests transcription/provenance,
not the Demeter model, disease bridge or an isolated processing effect.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from pypdf import PdfReader

from demeter.schema import EvidenceRegistry

SUMMARY_PATH = "docs/validation/update-public-biomarker-summary-v1.json"
SUMMARY_SHA256 = "c8746886ff1f44b4fec01a155766f5e8e1ebbb410303cfd11b8edc4032cf54b1"
REGISTRY_RECORDS_SHA256 = "380921f2b5342fe77527e8a4e296b0a2b31166479017ec9b66a6f028c91ba668"
DATASET = "update_public_biomarker_benchmark"
SOURCE_ID = "update2025_published_supplement"
GROUPS = ("mpf", "upf", "paired_mpf_minus_upf")
FIELDS = ("n", "mean", "reported_se")
ENDPOINTS = {
    "hba1c": ("HbA1C (%)", "percentage_points"),
    "fasting_glucose": ("Fasting glucose (mmol/L)", "mmol/L"),
}
GATES = {
    "direct_initialization_allowed": False,
    "clinical_fit_allowed": False,
    "engine_activation_allowed": False,
    "sampling_distribution_assumed": False,
    "scientific_release_ready": False,
}


def parameter_key(endpoint: str, group: str, field: str) -> str:
    return f"update_table5_{endpoint}_{group}_{field}"


def parameter_keys() -> list[str]:
    return ["update_table5_followup_weeks"] + [
        parameter_key(endpoint, group, field)
        for endpoint in ENDPOINTS
        for group in GROUPS
        for field in FIELDS
    ]


def registry_records(registry: EvidenceRegistry) -> dict:
    """Bind complete scoped metadata while unrelated registry work stays independent."""
    return {
        "parameters": {
            key: registry.parameters[key].model_dump(mode="json") for key in parameter_keys()
        },
        "source": registry.sources[SOURCE_ID].model_dump(mode="json"),
        "dataset": registry.datasets[DATASET],
    }


def _load_summary(root: Path) -> dict:
    content = (root / SUMMARY_PATH).read_bytes()
    if sha256(content).hexdigest() != SUMMARY_SHA256:
        raise ValueError("UPDATE source-summary checksum mismatch")
    summary = json.loads(content)
    if (
        set(summary["endpoints"]) != set(ENDPOINTS)
        or summary["scientific_gates"] != GATES
        or any(value is not False for value in summary["scientific_gates"].values())
        or summary["comparison"] != "unadjusted_available_pairs_mpf_minus_upf_change"
    ):
        raise ValueError("UPDATE summary scope mismatch")
    for endpoint, (label, unit) in ENDPOINTS.items():
        row = summary["endpoints"][endpoint]
        if row["source_label"] != label or row["unit"] != unit or set(row["groups"]) != set(GROUPS):
            raise ValueError("UPDATE endpoint or unit mismatch")
    return summary


def _selected_rows(page12: str, page13: str, summary: dict) -> dict:
    """Select literal cells, preserving displayed precision and paired source values."""
    page12 = " ".join(page12.split())
    page13 = " ".join(page13.split())
    header = "MPF diet UPF diet MPF diet - UPF diet"
    columns = "N Mean SE p-value N Mean SE p-value N Mean SE p-value"
    footnote = "Unadjusted change from baseline and between diets assessed using paired t-test."
    if (
        page12.count("Supplementary Table 5:") != 1
        or page12.count(header) != 1
        or page12.count(columns) != 1
        or page13.count(footnote) != 1
    ):
        raise ValueError("UPDATE table header or paired-method footnote mismatch")
    # Each source group contains N, mean, SE, p; p-values are not selected/exported.
    cell_pattern = r"([0-9]+) (-?[0-9]+\.[0-9]+) ([0-9]+\.[0-9]+) (?:<?[0-9]+\.[0-9]+)"
    selected = {}
    for endpoint, (label, _) in ENDPOINTS.items():
        matches = list(re.finditer(re.escape(label) + " " + " ".join([cell_pattern] * 3), page12))
        if page12.count(label) != 1 or len(matches) != 1:
            raise ValueError("UPDATE selected row is missing or nonunique")
        tokens = matches[0].groups()
        selected[endpoint] = {}
        for index, group in enumerate(GROUPS):
            display = dict(zip(FIELDS, tokens[index * 3 : index * 3 + 3], strict=True))
            expected = summary["endpoints"][endpoint]["groups"][group]
            if display != expected:
                raise ValueError("UPDATE source cells differ from reviewed summary")
            selected[endpoint][group] = display
    return selected


def replay_source(content: bytes, root: Path) -> dict:
    """Check original public PDF bytes before decoding only the selected table pages."""
    summary = _load_summary(root)
    source = summary["source"]
    if len(content) != source["size_bytes"] or sha256(content).hexdigest() != source["sha256"]:
        raise ValueError("UPDATE original source checksum or size mismatch")
    reader = PdfReader(BytesIO(content), strict=True)
    if reader.is_encrypted or len(reader.pages) != source["page_count"]:
        raise ValueError("UPDATE original PDF scope mismatch")
    return _selected_rows(reader.pages[11].extract_text(), reader.pages[12].extract_text(), summary)


def audit_update_biomarker(
    registry: EvidenceRegistry, root: Path, *, source_pdf: Path | None = None
) -> dict:
    """Offline registry/snapshot replay, optionally checked against original PDF.

    Raw source access is explicit. No network, participant records, statistics,
    imputation, interval construction or model simulation is performed.
    """
    summary = _load_summary(root)
    records = registry_records(registry)
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if sha256(canonical).hexdigest() != REGISTRY_RECORDS_SHA256:
        raise ValueError("UPDATE complete evidence or provenance mismatch")
    rows = {key: deepcopy(row["groups"]) for key, row in summary["endpoints"].items()}
    if source_pdf is not None and replay_source(source_pdf.read_bytes(), root) != rows:
        raise ValueError("UPDATE source replay mismatch")
    endpoints = {}
    for endpoint, row in summary["endpoints"].items():
        groups = {}
        for group, display in row["groups"].items():
            for field in FIELDS:
                parameter = registry.parameters[parameter_key(endpoint, group, field)]
                expected = int(display[field]) if field == "n" else float(display[field])
                if parameter.value != expected or parameter.model_role != "benchmark_only":
                    raise ValueError("UPDATE source-summary and evidence value mismatch")
            groups[group] = {
                "n": int(display["n"]),
                "mean": float(display["mean"]),
                "mean_display": display["mean"],
                "reported_se": float(display["reported_se"]),
                "reported_se_display": display["reported_se"],
                "uncertainty_status": "rounded_reported_se_underlying_uncertainty_unresolved",
                "sampling_distribution": None,
                "confidence_interval": None,
            }
        endpoints[endpoint] = {
            "source_label": row["source_label"],
            "change_unit": row["unit"],
            "source_locator": row["source_locator"],
            "groups": groups,
        }
    return {
        "kind": "published_source_summary_replay_not_model_validation",
        "model_role": "benchmark_only",
        "registered_summary_and_scoped_evidence_verified": True,
        "raw_source_read": source_pdf is not None,
        "source_cells_reproduced": True if source_pdf is not None else None,
        "source_sha256": summary["source"]["sha256"],
        "summary_sha256": SUMMARY_SHA256,
        "registry_records_sha256": REGISTRY_RECORDS_SHA256,
        "network_used": False,
        "participant_records_used": False,
        "clinical_transition_fit_performed": False,
        "followup_weeks": registry.value("update_table5_followup_weeks"),
        "comparison": summary["comparison"],
        "endpoints": endpoints,
        "cross_endpoint_covariance": None,
        "individual_period_histories": None,
        "sequence_period_sensitivity_numerically_implemented": False,
        "scientific_gates": deepcopy(GATES),
        "limitations": summary["limitations"],
    }
