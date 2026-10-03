"""Library-only selected-field technical inspection; no estimates.

The contract was committed before this implementation. Actual source inspection
requires a separate, reviewed immutable code/source admission, which does not
exist in this increment. That is an external reviewed execution prerequisite;
tests replace the delivery function with synthetic fixtures. No writer, CLI,
participant search or empirical admission is
provided. Integrity claims concern the reviewed call path, not hostile in-memory
replacement of Python functions or direct construction of private objects.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from demeter.data import nhis_diagnosis_labels as classifier
from demeter.data import nhis_native_records as decoder
from demeter.data import nhis_source_guard as guard

_CONTRACT = "docs/validation/nhis2025-selected-field-inspection-contract-v1.json"
_CONTRACT_SHA = "ee9e79b68ef6e47a18e8641bbe521234f4774c5c4386a551321eb2fa555c5477"
_AMENDMENT = "docs/validation/nhis2025-selected-field-provenance-amendment-v2.json"
_AMENDMENT_SHA = "1ec78498c07b25ce0dc1a20c60fe1af6286819dc1f80e05ec95390b075708cb7"
_DOCUMENTS = {
    _CONTRACT: _CONTRACT_SHA,
    "docs/NHIS_SELECTED_FIELD_INSPECTION_CONTRACT.md": "3ad62da97ee31d994d31035201a07295ca6ad7da798dcac876da6fbfcbe77fa0",
    _AMENDMENT: _AMENDMENT_SHA,
    "docs/NHIS_SELECTED_FIELD_PROVENANCE_AMENDMENT.md": "fd5395a22bc1c166fa75f06d9a1311c60776b708932f18e19c8bec25c87deefc",
    "docs/validation/nhis2025-native-framing-protocol-v1.json": "e1738706979b9bb2872389def34ea5b0f20d25584310f4af45288bf887fef25d",
    "docs/validation/nhis2025-native-framing-receipt-v1.json": "d669d2283310f48e29c9aea8a3258f0ab20a6925d082e4affe92f059ef9bc56f",
    "docs/validation/nhis2025-typed-diagnosis-design-receipts-v1.json": "cbb7e50eb970ecdc470607058f6e1df79a9c1cb37b3dcf82e7c3817096e4b889",
    "docs/design/11_NHIS_NATIVE_RECORD_CONTRACT.md": "e2df959321139d927108c6094d4b44e3255c473168de52174558e4024f580d7d",
}
_IMPLEMENTATIONS = {
    "src/demeter/data/nhis_source_guard.py": (
        guard,
        "dcb350b4a604a92c5c80f3f5c18e92c8d2827f1f9ad604f7ce4181633a45725e",
    ),
    "src/demeter/data/nhis_native_records.py": (
        decoder,
        "68042959577ca34bdd8946d8c2b28bf682495a113f79140c35539a7d4bd92511",
    ),
    "src/demeter/data/nhis_diagnosis_labels.py": (
        classifier,
        "0bf79f94ba46acb7efab90922705d226e7a58ae663a95a17a90c776394673d12",
    ),
}
_GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
_PROVENANCE = {
    "archive_sha256": "1981733845c4d6ede66f4756c34d47b356fbe403820c0ed33825d21e4d8f21e4",
    "native_sha256": "48b2d91002c9f30e03e87e33d37041dc991ea43a390674045a9ca60c7d004b95",
    "framing_protocol_sha256": "e1738706979b9bb2872389def34ea5b0f20d25584310f4af45288bf887fef25d",
    "framing_receipt_sha256": "d669d2283310f48e29c9aea8a3258f0ab20a6925d082e4affe92f059ef9bc56f",
    "selected_field_contract_sha256": _AMENDMENT_SHA,
}
_REFERENCE_RECORDS = 24215  # Already disclosed fixed delivery count, not a clinical parameter.
_ATTRIBUTION = (
    "Source: CDC/NCHS. Official files available without charge. "
    "No endorsement by CDC, HHS or the U.S. government."
)
_KIND = "nhis_selected_field_technical_inspection"
_RESPONSE_UNKNOWN = {"7": "refused", "8": "not_ascertained", "9": "dont_know"}


@dataclass(frozen=True, slots=True, repr=False)
class PrivateInspectionResult:
    """Immutable aggregate snapshots only; accessors return fresh dictionaries.

    No native bytes, selected records or exception objects are retained. Private
    aggregates are not a public release or a security boundary against a caller
    deliberately exporting an accessor. Persistence is absent from this API.
    """

    _private_json: str | None
    _technical_json: str
    _failure_json: str | None

    def __repr__(self) -> str:
        return "<PrivateNHISSelectedFieldInspection>"

    @property
    def private_diagnostics(self) -> dict | None:
        return json.loads(self._private_json) if self._private_json is not None else None

    @property
    def technical_envelope(self) -> dict:
        return json.loads(self._technical_json)

    @property
    def sanitized_failure(self) -> dict | None:
        return json.loads(self._failure_json) if self._failure_json is not None else None


def _snapshot(value: dict) -> str:
    return json.dumps(value, allow_nan=False, separators=(",", ":"))


def _pinned_file(root: Path, name: str, expected: str) -> bytes:
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path.stat().st_size > 1024 * 1024:
        raise ValueError
    with path.open("rb") as stream:
        content = stream.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024 or hashlib.sha256(content).hexdigest() != expected:
        raise ValueError
    return content


def _independent_contract_and_code(root: Path) -> dict:
    """Verify literals, disk bytes and loaded origins before invoking a helper."""
    contents = {name: _pinned_file(root, name, expected) for name, expected in _DOCUMENTS.items()}
    for name, (module, expected) in _IMPLEMENTATIONS.items():
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or Path(origin).resolve() != (root / name).resolve():
            raise ValueError
        _pinned_file(root, name, expected)
    return json.loads(contents[_CONTRACT])


def _sign(value) -> str:
    if value is None:
        return "missing"
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def _response(token: str, known: dict[str, str]) -> str:
    literal = token.strip(" ")
    if not literal:
        return "native_blank"
    if literal == ".":
        return "reader_single_period"
    return (known | _RESPONSE_UNKNOWN)[literal]


def _project(batch: decoder.PrivateNativeBatch, config: dict) -> dict:
    """Project all records; overlapping facets never become a larger population."""
    schema = config["fixed_private_success_schema"]
    marginals = {
        name: dict.fromkeys(labels, 0) for name, labels in schema["diagnostic_marginals"].items()
    }
    missingness = {
        field: {"native_blank": 0, "reader_single_period": 0}
        for field in schema["per_selected_field_missingness_field_inventory"]
    }
    ledger = batch.private_ledger
    n = len(batch.records)
    if (
        n != _REFERENCE_RECORDS
        or ledger["total_records"] != n
        or ledger["ledger_conserved"] is not True
    ):
        raise ValueError
    reused = {
        "reported_category": "category_counts",
        "sample_adult_status": "sample_adult_roles",
        "age_role": "age_roles",
        "sex_role": "sex_roles",
        "proxy_role": "proxy_roles",
    }
    for name, key in reused.items():
        if set(ledger[key]) != set(marginals[name]):
            raise ValueError
        marginals[name] = dict(ledger[key])
    design = {}
    both = 0
    for record in batch.records:
        tokens = dict(record.native_tokens)
        diagnosis = tokens["DIBEV_A"].strip(" ")
        kind = tokens["DIBTYPE_A"].strip(" ")
        universe = (
            "unresolved"
            if record.sample_adult_status != "sample_adult" or diagnosis in ("", ".")
            else "known_in_universe"
            if diagnosis == "1"
            else "known_outside_universe"
        )
        prefix = {
            "known_in_universe": "in",
            "known_outside_universe": "outside",
            "unresolved": "unresolved",
        }[universe]
        presence = "blank_or_period" if kind in ("", ".") else "recorded_code"
        values = {
            "diagnosis_response": _response(tokens["DIBEV_A"], {"1": "yes", "2": "no"}),
            "type_response": _response(
                tokens["DIBTYPE_A"], {"1": "type1", "2": "type2", "3": "other"}
            ),
            "type_universe": universe,
            "private_type_universe_and_recorded_response_presence": f"{prefix}_universe_{presence}",
            "weight_sign": _sign(record.weight),
            "stratum_sign": _sign(record.stratum),
            "psu_sign": _sign(record.psu),
            "design_presence": (
                "both_missing"
                if record.stratum is None and record.psu is None
                else "stratum_missing_only"
                if record.stratum is None
                else "psu_missing_only"
                if record.psu is None
                else "both_present"
            ),
        }
        for name, label in values.items():
            marginals[name][label] += 1
        for field, role in record.reader_missing_roles:
            missingness[field]["native_blank" if role == "blank" else "reader_single_period"] += 1
        if record.stratum is not None and record.psu is not None:
            both += 1
            design.setdefault(record.stratum, set()).add(record.psu)
    if any(
        type(count) is not int or count < 0
        for marginal in marginals.values()
        for count in marginal.values()
    ) or any(sum(marginal.values()) != n for marginal in marginals.values()):
        raise ValueError
    support = dict(
        zip(
            schema["private_design_support_scalars"],
            (
                both,
                len(design),
                sum(map(len, design.values())),
                sum(len(labels) == 1 for labels in design.values()),
                sum(len(labels) > 1 for labels in design.values()),
            ),
            strict=True,
        )
    )
    keys = {key: ledger[key] for key in schema["private_key_diagnostic_scalars"]}
    if any(type(count) is not int or not 0 <= count <= n for count in keys.values()):
        raise ValueError
    return marginals | {
        "key_diagnostics": keys,
        "selected_field_missingness": missingness,
        "design_support": support,
    }


def _technical(
    verified: bool,
    projected: bool | None,
    projection_status: str,
    completed: bool,
    provenance: dict,
) -> dict:
    return {
        "schema_version": 1,
        "kind": _KIND,
        "scope": "technical_only_no_diagnostic_counts",
        "status": "completed" if completed else "failed",
        "source_delivery_verified": verified,
        "selected_values_projected": projected,
        "selected_values_projection_status": projection_status,
        "empirical_estimate_computed": False,
        "source_admitted": False,
        "reference_delivery_records": _REFERENCE_RECORDS,
        "all_records_retained": True if completed else None,
        "complete_category_partition_conserved": True if completed else None,
        "every_declared_marginal_conserved": True if completed else None,
        "diagnostic_counts_released": False,
        "provenance": provenance,
        "attribution": _ATTRIBUTION,
        "scientific_gates": dict.fromkeys(_GATES, False),
    }


def inspect_selected_fields(archive: Path, native: Path, *, root: Path) -> PrivateInspectionResult:
    """Return fixed in-memory aggregates or sanitized failure, without estimates.

    Independent contract/helper identities precede any source/field call. Actual
    execution needs a separate reviewed code/source receipt; this API does not
    mint or assert that future admission. Uncertain decoder
    failure preserves possibly-partial projection, and aggregation failure after
    a successful decode retains completed projection. No partial aggregates or
    dynamic errors are returned. Exceptions including private context stay local.
    """
    stage, verified, projected, projection_status = (
        "independent_admission",
        False,
        False,
        "not_attempted",
    )
    provenance = dict(_PROVENANCE)
    try:
        if not all(isinstance(path, Path) for path in (archive, native, root)):
            raise ValueError
        root = root.resolve()
        config = _independent_contract_and_code(root)
        stage = "delivery_verification"
        delivery = guard.verify_delivery(archive, native, root=root)
        verified = True
        content = delivery.native_bytes
        if type(content) is not bytes:
            raise ValueError
        stage, projected, projection_status = "private_decoding", None, "possibly_partial"
        batch = decoder.decode_native_records(content)
        stage, projected, projection_status = "aggregate_projection", True, "completed"
        diagnostics = _project(batch, config)
        private = {
            "schema_version": 1,
            "kind": _KIND,
            "scope": "unweighted_all_delivered_records_private_diagnostics",
            "status": "completed",
            "source_delivery_verified": True,
            "selected_values_projected": True,
            "selected_values_projection_status": "completed",
            "empirical_estimate_computed": False,
            "source_admitted": False,
            "record_accounting": {
                "reference_delivery_records": _REFERENCE_RECORDS,
                "decoded_records": len(batch.records),
                "classified_records": len(batch.records),
                "all_records_retained": True,
                "complete_category_partition_conserved": True,
                "every_declared_marginal_conserved": True,
            },
            "diagnostics": diagnostics,
            "provenance": provenance,
            "scientific_gates": dict.fromkeys(_GATES, False),
        }
        return PrivateInspectionResult(
            _snapshot(private),
            _snapshot(_technical(True, True, "completed", True, provenance)),
            None,
        )
    except Exception:
        failure = {
            "schema_version": 1,
            "kind": _KIND,
            "status": "failed",
            "stage": stage,
            "source_delivery_verified": verified,
            "selected_values_projected": projected,
            "selected_values_projection_status": projection_status,
            "empirical_estimate_computed": False,
            "source_admitted": False,
            "scientific_gates": dict.fromkeys(_GATES, False),
        }
        return PrivateInspectionResult(
            None,
            _snapshot(_technical(verified, projected, projection_status, False, provenance)),
            _snapshot(failure),
        )
