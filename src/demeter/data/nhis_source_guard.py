"""Verified local delivery boundary; no selected values or empirical admission.

The contract predates implementation. Real field inspection needs a separately
committed intake/code receipt. This function never invokes the private decoder.
"""

from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import zipfile
import zlib

from demeter.data import nhis_diagnosis_labels as classifier
from demeter.data import nhis_native_records as decoder

_MAX_BYTES = 100 * 1024 * 1024  # Workflow resource policy only.
_GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)
_DOCUMENTS = {
    "docs/validation/nhis2025-native-framing-protocol-v1.json": "e1738706979b9bb2872389def34ea5b0f20d25584310f4af45288bf887fef25d",
    "docs/validation/nhis2025-native-framing-receipt-v1.json": "d669d2283310f48e29c9aea8a3258f0ab20a6925d082e4affe92f059ef9bc56f",
    "docs/validation/nhis2025-typed-diagnosis-design-receipts-v1.json": "cbb7e50eb970ecdc470607058f6e1df79a9c1cb37b3dcf82e7c3817096e4b889",
    "docs/design/11_NHIS_NATIVE_RECORD_CONTRACT.md": "e2df959321139d927108c6094d4b44e3255c473168de52174558e4024f580d7d",
}
_IMPLEMENTATIONS = {
    "src/demeter/data/nhis_native_records.py": (
        decoder,
        "68042959577ca34bdd8946d8c2b28bf682495a113f79140c35539a7d4bd92511",
    ),
    "src/demeter/data/nhis_diagnosis_labels.py": (
        classifier,
        "0bf79f94ba46acb7efab90922705d226e7a58ae663a95a17a90c776394673d12",
    ),
}


@dataclass(frozen=True, slots=True)
class _DeliveryDefinition:
    archive_sha256: str
    archive_size: int
    native_sha256: str
    native_size: int
    compressed_size: int
    crc32: int
    records: int


_EXPECTED = _DeliveryDefinition(
    "1981733845c4d6ede66f4756c34d47b356fbe403820c0ed33825d21e4d8f21e4",
    2837893,
    "48b2d91002c9f30e03e87e33d37041dc991ea43a390674045a9ca60c7d004b95",
    16635705,
    2837773,
    0xA1CC80FF,
    24215,
)


@dataclass(frozen=True, slots=True, repr=False)
class PrivateVerifiedDelivery:
    """Immutable exact bytes, never decoded here; not an anonymity guarantee."""

    native_bytes: bytes

    def __repr__(self) -> str:
        return "<PrivateNHISVerifiedDelivery>"

    @property
    def technical_provenance(self) -> dict:
        return {
            "kind": "nhis_verified_delivery_software_boundary",
            "source_delivery_verified": True,
            "source_admitted": False,
            "selected_values_projected": False,
            "empirical_estimate_computed": False,
            "private_delivery": True,
            "scientific_gates": dict.fromkeys(_GATES, False),
        }


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _bounded_read(path: Path, limit: int) -> bytes:
    cap = min(limit, _MAX_BYTES)
    if path.stat().st_size > cap:
        raise ValueError
    with path.open("rb") as stream:
        content = stream.read(cap + 1)
    if len(content) > cap:
        raise ValueError
    return content


def _under_root(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError
    return path


def _unique(pairs):
    value = {}
    for name, item in pairs:
        if name in value:
            raise ValueError
        value[name] = item
    return value


def _nonfinite(value):
    raise ValueError


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError
    return result


def _object(content: bytes) -> dict:
    value = json.loads(
        content, object_pairs_hook=_unique, parse_constant=_nonfinite, parse_float=_finite_float
    )
    if not isinstance(value, dict):
        raise ValueError
    return value


def _definitions_and_code(root: Path) -> None:
    for name, expected in _DOCUMENTS.items():
        content = _bounded_read(_under_root(root, name), _MAX_BYTES)
        if _sha(content) != expected:
            raise ValueError
        if name.endswith(".json"):
            _object(content)
    for name, (module, expected) in _IMPLEMENTATIONS.items():
        path = _under_root(root, name)
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str) or Path(origin).resolve() != path:
            raise ValueError
        # Read once: the loaded origin and checkout path are exactly the same.
        if _sha(_bounded_read(path, _MAX_BYTES)) != expected:
            raise ValueError


def _archive_and_framing(archive: bytes, native: bytes) -> None:
    expected = _EXPECTED
    with zipfile.ZipFile(BytesIO(archive)) as package:
        members = package.infolist()
        if len(members) != 1 or package.comment:
            raise ValueError
        member = members[0]
        if (
            member.filename != "adult25.dat"
            or member.is_dir()
            or member.flag_bits & 1
            or member.comment
            or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
            or member.file_size != expected.native_size
            or member.compress_size != expected.compressed_size
            or member.CRC != expected.crc32
            or member.file_size > _MAX_BYTES
        ):
            raise ValueError
        with package.open(member) as stream:
            expanded = stream.read(min(expected.native_size, _MAX_BYTES) + 1)
        if expanded != native:
            raise ValueError
    if len(native) != expected.records * 687:
        raise ValueError
    for offset in range(0, len(native), 687):
        if native[offset + 685 : offset + 687] != b"\r\n" or any(
            value < 32 or value > 126 for value in native[offset : offset + 685]
        ):
            raise ValueError


def verify_delivery(archive: Path, native: Path, *, root: Path) -> PrivateVerifiedDelivery:
    """Verify fixed delivery and loaded source identities without field decoding.

    Paths are explicit. No network, disk extraction, export, decoder call or
    clinical inference occurs. A later empirical caller needs separate admission.
    """
    try:
        if not all(isinstance(path, Path) for path in (archive, native, root)):
            raise ValueError
        root = root.resolve()
        _definitions_and_code(root)
        zipped = _bounded_read(archive, _EXPECTED.archive_size)
        content = _bounded_read(native, _EXPECTED.native_size)
        if (
            len(zipped) != _EXPECTED.archive_size
            or _sha(zipped) != _EXPECTED.archive_sha256
            or len(content) != _EXPECTED.native_size
            or _sha(content) != _EXPECTED.native_sha256
        ):
            raise ValueError
        _archive_and_framing(zipped, content)
    except (
        OSError,
        ValueError,
        TypeError,
        AttributeError,
        UnicodeError,
        zipfile.BadZipFile,
        NotImplementedError,
        RuntimeError,
        EOFError,
        zlib.error,
    ):
        raise ValueError("Unsupported NHIS verified-delivery contract") from None
    return PrivateVerifiedDelivery(content)
