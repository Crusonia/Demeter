"""Independent source and loaded-code admission before repeat-label diagnostics.

The receipts precede the first empirical calculation. This entry point is a
small reviewable trust boundary, not a defense against arbitrary in-memory code
replacement. It never exports the private paired ledger.
"""

import hashlib
import json
from pathlib import Path

from demeter.data import nhanes3_repeat as calculation
from demeter.data import nhanes3_repeat_store as store
from demeter import schema

DATASET = "nhanes_iii_repeat_fpg_observation"
SOURCE_ADMISSION = Path("docs/validation/nhanes3-repeat-source-admission-v1.json")
SOURCE_ADMISSION_SHA256 = "d05784c3df09957b1a03f0afc10dfd4caafef33f5f8f6735f2bf40bef8fd2a5d"
CODE_ADMISSION = Path("docs/validation/nhanes3-repeat-code-admission-v1.json")
CODE_ADMISSION_SHA256 = "2c8c9f2c054b64cb86a05880743d42e909630be0a5c1ad1cfea62b003aefa587"
IMPLEMENTATIONS = {
    "src/demeter/data/nhanes3_repeat.py": calculation,
    "src/demeter/data/nhanes3_repeat_store.py": store,
    "src/demeter/schema.py": schema,
}


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise ValueError("Unavailable independently admitted NHANES III artifact") from None


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate NHANES III independent receipt key")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("Nonfinite NHANES III independent receipt value")


def _frozen(path: Path, expected: str) -> dict:
    raw = _read(path)
    if _sha(raw) != expected:
        raise ValueError("Independent NHANES III admission checksum mismatch")
    try:
        value = json.loads(raw, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Invalid NHANES III independent receipt encoding") from None
    if not isinstance(value, dict):
        raise ValueError("NHANES III independent receipt must be an object")
    return value


def verify_admission() -> tuple[dict, dict]:
    """Check independent pins and both disk/loaded implementation origins first."""
    source = _frozen(SOURCE_ADMISSION, SOURCE_ADMISSION_SHA256)
    code = _frozen(CODE_ADMISSION, CODE_ADMISSION_SHA256)
    pins = code.get("implementation_sha256")
    if (
        not isinstance(pins, dict)
        or set(pins) != set(IMPLEMENTATIONS)
        or code.get("source_admission_sha256") != SOURCE_ADMISSION_SHA256
    ):
        raise ValueError("Independent NHANES III code admission shape invalid")
    for name, module in IMPLEMENTATIONS.items():
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or Path(origin).suffix != ".py":
            raise ValueError("NHANES III admitted loaded implementation unavailable")
        if _sha(_read(Path(name))) != pins[name] or _sha(_read(Path(origin))) != pins[name]:
            raise ValueError("NHANES III implementation differs from independent code admission")
    return source, code


def report(
    registry: schema.EvidenceRegistry,
    source: Path = Path("data/sources/nhanes3/1988-1994-repeat"),
) -> dict:
    """Return only the fixed coarse public projection after independent admission."""
    source_admission, code_admission = verify_admission()
    try:
        contents, provenance = store.verify(registry, source_admission, code_admission, source)
        provenance["source_admission_sha256"] = SOURCE_ADMISSION_SHA256
        provenance["code_admission_sha256"] = CODE_ADMISSION_SHA256
        private = calculation.analyze(contents, store.DEFINITION)
        return calculation.public_result(private, provenance=provenance, source_audit_passed=True)
    except (AttributeError, KeyError, TypeError):
        raise ValueError("Invalid admitted NHANES III input or diagnostic contract") from None
