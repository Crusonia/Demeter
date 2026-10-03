"""Private full-file NHIS reported-answer ratios, with no execution admission.

The contract predates this bridge. Tests use synthetic delivery only; a future
original invocation needs a separate reviewed code/source admission. No writer,
CLI, clinical state mapping, interval or public statistical release is provided.
Unavailable provenance values are null until the corresponding verification
completes; populated source hashes prove successful delivery verification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import fsum, isfinite
from pathlib import Path
import sys

import pandas as pd

from demeter.data import nhis_diagnosis_labels as classifier
from demeter.data import nhis_native_records as decoder
from demeter.data import nhis_source_guard as guard
from demeter.data import nhis_survey_witness as witness
from demeter.data import survey_joint as kernel

_CONTRACT = "docs/validation/nhis2025-reported-answer-benchmark-contract-v1.json"
_CONTRACT_SHA = "308d7cfb67a88f891bd79f551135e9d1a75e0167e6e7f2ba53232b484c42b267"
_DOCUMENT = "docs/NHIS_REPORTED_ANSWER_BENCHMARK_CONTRACT.md"
_DOCUMENT_SHA = "4fc932b7af10689a66ad2249ea5a443732103f72de4e30267526cb6a0817b1d0"
_MODULES = {
    "src/demeter/data/nhis_source_guard.py": guard,
    "src/demeter/data/nhis_native_records.py": decoder,
    "src/demeter/data/nhis_diagnosis_labels.py": classifier,
    "src/demeter/data/nhis_survey_witness.py": witness,
    "src/demeter/data/survey_joint.py": kernel,
}
_DOMAIN = "full_sample_adult_file"
_GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
_PROVENANCE_KEYS = (
    "archive_sha256",
    "native_sha256",
    "framing_protocol_sha256",
    "framing_receipt_sha256",
    "benchmark_contract_sha256",
    "helper_sha256",
)
_ATTRIBUTION = (
    "CDC/NCHS official sources available without charge; use/link does not imply "
    "CDC, HHS or U.S. government endorsement."
)


@dataclass(frozen=True, slots=True, repr=False)
class PrivateBenchmarkResult:
    """Immutable aggregates only, with fresh accessors; not an anonymity boundary."""

    _private_json: str | None
    _technical_json: str
    _failure_json: str | None

    def __repr__(self) -> str:
        return "<PrivateNHISReportedAnswerBenchmark>"

    @property
    def private_result(self) -> dict | None:
        return json.loads(self._private_json) if self._private_json is not None else None

    @property
    def technical_envelope(self) -> dict:
        return json.loads(self._technical_json)

    @property
    def sanitized_failure(self) -> dict | None:
        return json.loads(self._failure_json) if self._failure_json is not None else None


def _snapshot(value: dict) -> str:
    return json.dumps(value, allow_nan=False, separators=(",", ":"))


def _pinned(root: Path, name: str, expected: str) -> bytes:
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path.stat().st_size > 1024 * 1024:
        raise ValueError
    content = path.read_bytes()
    if len(content) > 1024 * 1024 or hashlib.sha256(content).hexdigest() != expected:
        raise ValueError
    return content


def _independent_preflight(root: Path) -> dict:
    config = json.loads(_pinned(root, _CONTRACT, _CONTRACT_SHA))
    _pinned(root, _DOCUMENT, _DOCUMENT_SHA)
    for name, expected in config["document_sha256"].items():
        _pinned(root, name, expected)
    if set(config["helper_sha256"]) != set(_MODULES):
        raise ValueError
    for name, module in _MODULES.items():
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or Path(origin).resolve() != (root / name).resolve():
            raise ValueError
        _pinned(root, name, config["helper_sha256"][name])
    if (
        witness.classify_reported_diabetes is not classifier.classify_reported_diabetes
        or decoder.classify_reported_diabetes is not classifier.classify_reported_diabetes
        or witness.joint_proportions is not kernel.joint_proportions
        or (witness.WEIGHT, witness.STRATUM, witness.PSU)
        != (kernel.WEIGHT, kernel.STRATUM, kernel.PSU)
    ):
        raise ValueError
    return config


def _ledger(batch: decoder.PrivateNativeBatch) -> dict:
    if type(batch) is not decoder.PrivateNativeBatch:
        raise ValueError
    raw = batch.private_ledger
    names = (
        "unit",
        "total_records",
        "category_counts",
        "ledger_conserved",
        "age_roles",
        "sex_roles",
        "proxy_roles",
        "sample_adult_roles",
        "missing_household_key_records",
        "duplicate_interpreted_household_key_records",
        "household_keys_with_lexical_aliases",
        "missing_weight_records",
        "nonpositive_weight_records",
        "missing_design_records",
    )
    result = {"kind": "nhis_complete_native_record_ledger"} | {name: raw[name] for name in names}
    n = len(batch.records)
    if (
        raw["unit"] != "input_records"
        or raw["total_records"] != n
        or raw["ledger_conserved"] is not True
    ):
        raise ValueError
    vocabularies = {
        "category_counts": classifier.CATEGORIES,
        "age_roles": decoder._AGE_ROLES,
        "sex_roles": decoder._SEX_ROLES,
        "proxy_roles": decoder._PROXY_ROLES,
        "sample_adult_roles": ("sample_adult", "missing"),
    }
    for name, vocabulary in vocabularies.items():
        counts = result[name]
        if (
            set(counts) != set(vocabulary)
            or any(type(x) is not int or x < 0 for x in counts.values())
            or sum(counts.values()) != n
        ):
            raise ValueError
    for name in names[8:]:
        if type(result[name]) is not int or not 0 <= result[name] <= n:
            raise ValueError
    result["response_reader_missingness"] = {}
    for name in ("DIBEV_A", "DIBTYPE_A"):
        counts = dict.fromkeys(("blank", "single_period", "not_missing"), 0)
        for record in batch.records:
            counts[dict(record.reader_missing_roles).get(name, "not_missing")] += 1
        result["response_reader_missingness"][name] = counts
    return result


def _frame(batch: decoder.PrivateNativeBatch, ledger: dict, config: dict) -> pd.DataFrame:
    if (
        len(batch.records) != config["source_identity"]["native"]["reference_records"]
        or not batch.records
        or ledger["sample_adult_roles"]["missing"]
        or any(
            ledger[name]
            for name in (
                "missing_household_key_records",
                "duplicate_interpreted_household_key_records",
                "household_keys_with_lexical_aliases",
                "missing_weight_records",
                "nonpositive_weight_records",
                "missing_design_records",
            )
        )
    ):
        raise ValueError
    rows = []
    support: dict[int, set[int]] = {}
    for record in batch.records:
        if record.weight is None or not record.weight.is_finite() or record.weight <= 0:
            raise ValueError
        weight = float(record.weight)  # Explicit nearest binary64, not implied SAS scaling.
        if not isfinite(weight) or weight <= 0:
            raise ValueError
        if any(type(x) is not int or not 0 < x <= 2**63 - 1 for x in (record.stratum, record.psu)):
            raise ValueError
        tokens = dict(record.native_tokens)
        answers = []
        for name in ("DIBEV_A", "DIBTYPE_A"):
            token = tokens[name].strip(" ")
            answers.append("" if token == "." else token)
        if classifier.classify_reported_diabetes(*answers) != record.reported_category:
            raise ValueError
        rows.append((*answers, weight, record.stratum, record.psu))
        support.setdefault(record.stratum, set()).add(record.psu)
    if any(len(psus) < 2 for psus in support.values()):
        raise ValueError
    return pd.DataFrame(rows, columns=("DIBEV_A", "DIBTYPE_A", "WTFA_A", "PSTRAT", "PPSU"))


def _joint(result: dict, ledger: dict, frame: pd.DataFrame) -> dict:
    if not isinstance(result, dict) or set(result) != {
        "kind",
        "validation_only",
        "software_witness",
        "private_aggregate",
        "source_admitted",
        "scientific_gates",
        "record_ledger",
        "joint",
        "design",
        "domains",
    }:
        raise ValueError
    if (
        result["kind"] != "nhis_joint_ratio_software_witness"
        or any(
            result[name] is not True
            for name in ("validation_only", "software_witness", "private_aggregate")
        )
        or result["source_admitted"] is not False
        or set(result["scientific_gates"]) != set(_GATES)
        or any(value is not False for value in result["scientific_gates"].values())
    ):
        raise ValueError
    strata = int(frame.PSTRAT.nunique())
    psus = len(frame[["PSTRAT", "PPSU"]].drop_duplicates())
    if result["design"] != {
        "weight": "WTFA_A",
        "stratum": "PSTRAT",
        "psu": "PPSU",
        "input_records": len(frame),
        "strata": strata,
        "psus": psus,
        "software_method": "full_design_with_replacement_first_stage_taylor",
        "weight_policy": "finite_positive_required_without_trimming",
        "singleton_policy": "full_design_singleton_refused",
    } or result["domains"] != [
        {
            "domain": _DOMAIN,
            "input_records": len(frame),
            "represented_psus": psus,
            "represented_strata": strata,
            "status": "ratio_computed",
        }
    ]:
        raise ValueError
    if result["record_ledger"] != {
        name: ledger[name]
        for name in ("unit", "total_records", "category_counts", "ledger_conserved")
    }:
        raise ValueError
    joint = result["joint"]
    if set(joint) != {"coordinates", "ratios", "covariance", "ratio_unit", "covariance_unit"}:
        raise ValueError
    expected = [{"domain": _DOMAIN, "membership": name} for name in classifier.CATEGORIES]
    if (
        joint["coordinates"] != expected
        or joint["ratio_unit"] != "dimensionless"
        or joint["covariance_unit"] != "dimensionless_squared"
    ):
        raise ValueError
    p, v = joint["ratios"], joint["covariance"]

    def real(x):
        return type(x) in (int, float) and isfinite(x)

    if (
        not isinstance(p, list)
        or len(p) != 7
        or any(not real(x) or not 0 <= x <= 1 for x in p)
        or abs(fsum(p) - 1) > 32 * sys.float_info.epsilon
        or not isinstance(v, list)
        or len(v) != 7
        or any(
            not isinstance(row, list) or len(row) != 7 or any(not real(x) for x in row) for row in v
        )
        or any(v[i][i] < 0 for i in range(7))
    ):
        raise ValueError
    scale = max(abs(x) for row in v for x in row)
    tolerance = 64 * sys.float_info.epsilon * scale
    if scale > 0 and tolerance == 0:
        raise ValueError
    if any(abs(v[i][j] - v[j][i]) > tolerance for i in range(7) for j in range(7)) or any(
        abs(fsum(values)) > tolerance for values in [*v, *zip(*v, strict=True)]
    ):
        raise ValueError
    return joint | {
        "software_method": "full_design_with_replacement_first_stage_taylor_joint_ratio_covariance"
    }


def benchmark_reported_answers(
    archive: Path, native: Path, *, root: Path
) -> PrivateBenchmarkResult:
    """Normal guarded library flow; original-source invocation is externally admitted.

    Failure retains a complete approved ledger only after decoding/aggregation
    returns. No partial ratio result is exported. A witness returning means
    arithmetic occurred even if subsequent validation fails. Direct construction
    or hostile runtime monkeypatching is outside the reviewed-path integrity claim.
    """
    stage = "independent_preflight"
    verified, projected, projection_status = False, False, "not_attempted"
    attempted, estimated, estimation_status = False, False, "not_attempted"
    ledger, joint, failure = None, None, None
    provenance = dict.fromkeys(_PROVENANCE_KEYS)
    try:
        if not all(isinstance(p, Path) for p in (archive, native, root)):
            raise ValueError
        root = root.resolve()
        config = _independent_preflight(root)
        provenance.update(
            framing_protocol_sha256=config["document_sha256"][
                "docs/validation/nhis2025-native-framing-protocol-v1.json"
            ],
            framing_receipt_sha256=config["document_sha256"][
                "docs/validation/nhis2025-native-framing-receipt-v1.json"
            ],
            benchmark_contract_sha256=_CONTRACT_SHA,
            helper_sha256=config["helper_sha256"],
        )
        stage = "delivery_verification"
        delivery = guard.verify_delivery(archive, native, root=root)
        verified = True
        provenance.update(
            archive_sha256=config["source_identity"]["archive"]["sha256"],
            native_sha256=config["source_identity"]["native"]["sha256"],
        )
        content = delivery.native_bytes
        if type(content) is not bytes:
            raise ValueError
        stage, projected, projection_status = "private_decoding", None, "possibly_partial"
        batch = decoder.decode_native_records(content)
        stage, projected, projection_status = "private_ledger", True, "completed"
        ledger = _ledger(batch)
        stage = "whole_frame_method_preflight"
        frame = _frame(batch, ledger, config)
        domains = pd.DataFrame({_DOMAIN: True}, index=frame.index)
        stage, attempted, estimated, estimation_status = (
            "joint_estimation",
            True,
            None,
            "possibly_partial",
        )
        result = witness.assess(frame, domains)
        stage, estimated, estimation_status = "joint_validation", True, "completed"
        joint = _joint(result, ledger, frame)
    except Exception:
        failure = {"kind": "nhis_reported_answer_benchmark_unavailable", "stage": stage}
    complete = failure is None
    private = (
        None
        if ledger is None
        else {
            "kind": "nhis2025_reported_answer_private_benchmark",
            "schema_version": 1,
            "model_role": "benchmark_only",
            "private_aggregate": True,
            "source_admitted": False,
            "scientific_gates": dict.fromkeys(_GATES, False),
            "record_ledger": ledger,
            "joint": joint,
        }
    )
    technical = {
        "kind": "nhis2025_reported_answer_benchmark_technical",
        "schema_version": 1,
        "status": "completed" if complete else "unavailable",
        "source_delivery_verified": verified,
        "selected_values_projected": projected,
        "projection_status": projection_status,
        "statistical_estimation_attempted": attempted,
        "empirical_estimate_computed": estimated,
        "estimation_status": estimation_status,
        "private_result_complete": complete,
        "source_admitted": False,
        "scientific_gates": dict.fromkeys(_GATES, False),
        "provenance": provenance,
        "attribution": _ATTRIBUTION,
    }
    return PrivateBenchmarkResult(
        _snapshot(private) if private is not None else None,
        _snapshot(technical),
        _snapshot(failure) if failure is not None else None,
    )
