"""Pure software witness for reported diagnosis/type categories, not clinical states.

The documented NHIS 2025 codes motivate the categorical contract. This module
does not admit source records, infer diabetes type from treatment or age, or
identify undiagnosed disease. Counts refer only to supplied input records; a
future empirical caller needs a separately reviewed source/observation guard.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


CATEGORIES = (
    "no_reported_diabetes",
    "reported_type1",
    "reported_type2",
    "reported_other_diabetes",
    "reported_diabetes_type_unknown",
    "diagnosis_unknown",
    "inconsistent_type_universe",
)
_DIAGNOSIS_CODES = frozenset({"", " ", "1", "2", "7", "8", "9"})
_TYPE_CODES = frozenset({"", " ", "1", "2", "3", "7", "8", "9"})
_BLANK_CODES = frozenset({"", " "})
_GATE_NAMES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)


def classify_reported_diabetes(diagnosis: str, diabetes_type: str) -> str:
    """Retain the diagnosis/type universe, including contradictions and unknowns.

    Only exact built-in strings are accepted. The empty projected missing token
    and a single native ASCII-space blank have the same missing role. No token
    is stripped or coerced: padded codes, extra spaces and other whitespace fail.
    Unknown diagnosis is distinct from an explicit No. Any non-Yes diagnosis
    accompanied by a nonblank type response is retained as inconsistent.
    """
    if type(diagnosis) is not str or type(diabetes_type) is not str:
        raise ValueError("Diagnosis/type codes require exact string tokens")
    if diagnosis not in _DIAGNOSIS_CODES or diabetes_type not in _TYPE_CODES:
        raise ValueError("Diagnosis/type code or syntax is unsupported")
    if diagnosis == "1":
        return {
            "1": "reported_type1",
            "2": "reported_type2",
            "3": "reported_other_diabetes",
        }.get(diabetes_type, "reported_diabetes_type_unknown")
    if diabetes_type not in _BLANK_CODES:
        return "inconsistent_type_universe"
    return "no_reported_diabetes" if diagnosis == "2" else "diagnosis_unknown"


def partition_reported_diabetes(pairs: Iterable[tuple[str, str]]) -> dict:
    """Return a private, conserved in-memory record ledger for software validation.

    Each pair must be a two-element tuple or list. Input rows and tokens are
    never returned or interpolated into errors. No record-to-person identity,
    source admission, survey estimate, clinical state or public-release policy
    is established by this witness. Empty input retains every zero category.
    """
    if isinstance(pairs, (str, bytes, bytearray, Mapping)):
        raise ValueError("A diagnosis/type pair iterable is required")
    try:
        iterator = iter(pairs)
    except Exception:
        raise ValueError("A diagnosis/type pair iterable is required") from None
    counts = dict.fromkeys(CATEGORIES, 0)
    total = 0
    while True:
        try:
            pair = next(iterator)
        except StopIteration:
            break
        except Exception:
            raise ValueError("Diagnosis/type pair iteration failed") from None
        if type(pair) not in (tuple, list) or len(pair) != 2:
            raise ValueError("Each diagnosis/type pair must contain exactly two codes")
        category = classify_reported_diabetes(pair[0], pair[1])
        counts[category] += 1
        total += 1
    return {
        "kind": "nhis_reported_diagnosis_software_witness",
        "category_counts": counts,
        "total_records": total,
        "ledger_conserved": sum(counts.values()) == total,
        "validation_only": True,
        "software_witness": True,
        "private_aggregate": True,
        "scientific_gates": dict.fromkeys(_GATE_NAMES, False),
    }
