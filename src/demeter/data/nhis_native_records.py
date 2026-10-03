"""Private synthetic native-record decoder; no source loader or admission.

The reviewed contract predates this implementation. A future empirical caller
must independently admit source bytes, definitions and loaded code before use.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
import re

from demeter.data.nhis_diagnosis_labels import CATEGORIES, classify_reported_diabetes

_FIELDS = (
    ("RECTYPE", 1, 2),
    ("SRVY_YR", 3, 6),
    ("HHX", 7, 13),
    ("WTFA_A", 14, 23),
    ("PSTRAT", 26, 28),
    ("PPSU", 29, 34),
    ("PROXYFLAG_A", 36, 36),
    ("HHSTAT_A", 38, 38),
    ("SEX_A", 46, 46),
    ("AGEP_A", 48, 49),
    ("DIBEV_A", 176, 176),
    ("DIBTYPE_A", 187, 187),
)
_GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
_MAX_BYTES = 100 * 1024 * 1024  # Workflow resource policy, not a scientific cutoff.
_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")
_UNKNOWN = {7: "refused", 8: "not_ascertained", 9: "dont_know"}
_AGE_ROLES = ("exact_age", "85_plus", "refused", "not_ascertained", "dont_know", "missing")
_SEX_ROLES = ("male", "female", "refused", "not_ascertained", "dont_know", "missing")
_PROXY_ROLES = (
    "proxy_used",
    "proxy_not_used",
    "refused",
    "not_ascertained",
    "dont_know",
    "missing",
)


@dataclass(frozen=True, slots=True, repr=False)
class PrivateNativeRecord:
    """Selected values remain private; default representation reveals no fields."""

    household_key: str | None
    sample_adult_status: str
    reported_category: str
    age_role: str
    exact_age_years: int | None
    age_lower_bound_years: int | None
    sex_role: str
    proxy_role: str
    weight: Decimal | None
    stratum: int | None
    psu: int | None
    native_tokens: tuple[tuple[str, str], ...]
    reader_missing_roles: tuple[tuple[str, str], ...]

    def __repr__(self) -> str:
        return "<PrivateNHISNativeRecord>"


@dataclass(frozen=True, slots=True, repr=False)
class PrivateNativeBatch:
    """In-memory records and an explicit private software-validation ledger.

    This is not a security boundary against a caller deliberately exporting
    attributes. There is no public record exporter or source-audit claim.
    """

    records: tuple[PrivateNativeRecord, ...]

    def __repr__(self) -> str:
        return "<PrivateNHISNativeBatch>"

    @property
    def private_ledger(self) -> dict:
        def counts(attribute, labels):
            observed = Counter(getattr(record, attribute) for record in self.records)
            return {label: observed[label] for label in labels}

        keys = [record.household_key for record in self.records if record.household_key is not None]
        key_lexemes = defaultdict(set)
        for record in self.records:
            if record.household_key is not None:
                key_lexemes[record.household_key].add(dict(record.native_tokens)["HHX"])
        categories = counts("reported_category", CATEGORIES)
        return {
            "kind": "nhis_native_records_software_witness",
            "unit": "input_records",
            "total_records": len(self.records),
            "category_counts": categories,
            "ledger_conserved": sum(categories.values()) == len(self.records),
            "age_roles": counts("age_role", _AGE_ROLES),
            "sex_roles": counts("sex_role", _SEX_ROLES),
            "proxy_roles": counts("proxy_role", _PROXY_ROLES),
            "sample_adult_roles": counts("sample_adult_status", ("sample_adult", "missing")),
            "missing_household_key_records": len(self.records) - len(keys),
            "duplicate_interpreted_household_key_records": len(keys) - len(set(keys)),
            "household_keys_with_lexical_aliases": sum(
                len(values) > 1 for values in key_lexemes.values()
            ),
            "missing_weight_records": sum(record.weight is None for record in self.records),
            "nonpositive_weight_records": sum(
                record.weight is not None and record.weight <= 0 for record in self.records
            ),
            "missing_design_records": sum(
                record.stratum is None or record.psu is None for record in self.records
            ),
            "validation_only": True,
            "software_witness": True,
            "private_aggregate": True,
            "source_admitted": False,
            "scientific_gates": dict.fromkeys(_GATES, False),
        }


def _interpret(token: str) -> tuple[str | None, str | None]:
    value = token.strip(" ")
    if value == "":
        return None, "blank"
    if value == ".":
        return None, "single_period"
    return value, None


def _integer(value: str | None) -> int | None:
    if value is None:
        return None
    if not _INTEGER.fullmatch(value):
        raise ValueError
    return int(value)


def _role(value: int | None, known: dict[int, str]) -> str:
    if value is None:
        return "missing"
    if value not in known:
        raise ValueError
    return known[value]


def _record(payload: bytes) -> PrivateNativeRecord:
    tokens = {name: payload[start - 1 : end].decode("ascii") for name, start, end in _FIELDS}
    interpreted = {name: _interpret(token) for name, token in tokens.items()}
    values = {name: pair[0] for name, pair in interpreted.items()}
    missing_roles = tuple(
        (name, pair[1]) for name, pair in interpreted.items() if pair[1] is not None
    )
    if _integer(values["RECTYPE"]) != 10 or _integer(values["SRVY_YR"]) != 2025:
        raise ValueError
    if values["HHSTAT_A"] not in (None, "1"):
        raise ValueError
    age = _integer(values["AGEP_A"])
    age_roles = {value: "exact_age" for value in range(18, 85)} | {
        85: "85_plus",
        97: "refused",
        98: "not_ascertained",
        99: "dont_know",
    }
    weight_literal = values["WTFA_A"]
    if weight_literal is not None and not _DECIMAL.fullmatch(weight_literal):
        raise ValueError
    weight = Decimal(weight_literal) if weight_literal is not None else None
    if weight is not None and not weight.is_finite():
        raise ValueError
    # A single period is reader-language missing, not another questionnaire code.
    # The exact native token and missing role are retained independently.
    category = classify_reported_diabetes(values["DIBEV_A"] or "", values["DIBTYPE_A"] or "")
    return PrivateNativeRecord(
        household_key=values["HHX"],
        sample_adult_status="sample_adult" if values["HHSTAT_A"] == "1" else "missing",
        reported_category=category,
        age_role=_role(age, age_roles),
        exact_age_years=age if age is not None and 18 <= age <= 84 else None,
        age_lower_bound_years=age if age is not None and 18 <= age <= 85 else None,
        sex_role=_role(_integer(values["SEX_A"]), {1: "male", 2: "female"} | _UNKNOWN),
        proxy_role=_role(
            _integer(values["PROXYFLAG_A"]), {1: "proxy_used", 2: "proxy_not_used"} | _UNKNOWN
        ),
        weight=weight,
        stratum=_integer(values["PSTRAT"]),
        psu=_integer(values["PPSU"]),
        native_tokens=tuple(tokens.items()),
        reader_missing_roles=missing_roles,
    )


def decode_native_records(content: bytes) -> PrivateNativeBatch:
    """Decode synthetic bytes under the finite reviewed contract, without I/O.

    No trimming, padding, row exclusion, source admission or analysis eligibility
    is inferred. Empty synthetic input returns a conserved zero-record ledger.
    """
    if type(content) is not bytes or len(content) > _MAX_BYTES or len(content) % 687:
        raise ValueError("Unsupported synthetic NHIS native framing or resource limit")
    records = []
    try:
        for offset in range(0, len(content), 687):
            payload = content[offset : offset + 685]
            if content[offset + 685 : offset + 687] != b"\r\n" or any(
                value < 32 or value > 126 for value in payload
            ):
                raise ValueError
            records.append(_record(payload))
    except (ValueError, ArithmeticError, UnicodeError):
        raise ValueError(
            "Unsupported synthetic NHIS native lexical or record-role contract"
        ) from None
    return PrivateNativeBatch(tuple(records))
