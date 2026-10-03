"""Synthetic source identities only; never open participant delivery files."""

from dataclasses import FrozenInstanceError, replace
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import zipfile

import pytest

from demeter.data import nhis_source_guard as guard


def sha(content):
    return hashlib.sha256(content).hexdigest()


def archive_bytes(native, *, name="adult25.dat", comment=b"", extra=False, member_comment=b""):
    target = BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo(name)
        info.comment = member_comment
        archive.writestr(info, native)
        if extra:
            archive.writestr("PRIVATE-UNEXPECTED-NAME", b"omitted")
        archive.comment = comment
    return target.getvalue()


def expected(zipped, native, *, records=1):
    with zipfile.ZipFile(BytesIO(zipped)) as package:
        member = package.infolist()[0]
    return guard._DeliveryDefinition(
        sha(zipped),
        len(zipped),
        sha(native),
        len(native),
        member.compress_size,
        member.CRC,
        records,
    )


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    root = tmp_path / "synthetic-checkout"
    source = Path(__file__).resolve().parents[1]
    for name in (*guard._DOCUMENTS, *guard._IMPLEMENTATIONS):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    for name, (module, _) in guard._IMPLEMENTATIONS.items():
        monkeypatch.setattr(module, "__file__", str(root / name))

    def forbidden(*args, **kwargs):
        pytest.fail("Admission must never invoke a selected-value decoder/classifier")

    monkeypatch.setattr(guard.decoder, "decode_native_records", forbidden)
    monkeypatch.setattr(guard.classifier, "classify_reported_diabetes", forbidden)
    payload = b"UNDECODED-SYNTHETIC".ljust(685, b" ")
    native = payload + b"\r\n"
    zipped = archive_bytes(native)
    definition = expected(zipped, native)
    monkeypatch.setattr(guard, "_EXPECTED", definition)
    archive_path = tmp_path / "PRIVATE-ARCHIVE-PATH.zip"
    native_path = tmp_path / "PRIVATE-NATIVE-PATH.dat"
    archive_path.write_bytes(zipped)
    native_path.write_bytes(native)
    return root, archive_path, native_path, zipped, native


def invoke(delivery):
    root, archive, native, *_ = delivery
    return guard.verify_delivery(archive, native, root=root)


def refused(delivery):
    with pytest.raises(ValueError) as error:
        invoke(delivery)
    assert str(error.value) == "Unsupported NHIS verified-delivery contract"
    assert error.value.__cause__ is None and error.value.__suppress_context__ is True
    assert "PRIVATE" not in str(error.value)


def test_success_is_exact_private_immutable_delivery_not_a_decode(delivery):
    value = invoke(delivery)
    assert value.native_bytes == delivery[4]
    assert repr(value) == "<PrivateNHISVerifiedDelivery>"
    with pytest.raises(FrozenInstanceError):
        value.native_bytes = b"changed"
    with pytest.raises(TypeError):
        json.dumps(value)
    report = value.technical_provenance
    assert report["source_delivery_verified"] is True
    assert report["source_admitted"] is False
    assert report["selected_values_projected"] is False
    assert report["empirical_estimate_computed"] is False
    assert report["scientific_gates"] == dict.fromkeys(guard._GATES, False)
    assert "PRIVATE" not in json.dumps(report)
    report["scientific_gates"]["clinical_fit_allowed"] = True
    assert not value.technical_provenance["scientific_gates"]["clinical_fit_allowed"]
    assert delivery[1].read_bytes() == delivery[3]
    assert delivery[2].read_bytes() == delivery[4]


@pytest.mark.parametrize("which", ["archive", "native", "document", "code"])
def test_tampering_fails_before_any_source_projection(delivery, which):
    root, archive, native, *_ = delivery
    target = {
        "archive": archive,
        "native": native,
        "document": root / next(iter(guard._DOCUMENTS)),
        "code": root / next(iter(guard._IMPLEMENTATIONS)),
    }[which]
    original = target.read_bytes()
    target.write_bytes(b"X" + original[1:])
    refused(delivery)


def test_receipt_tampering_with_recomputed_internal_hash_cannot_admit(delivery):
    target = delivery[0] / "docs/validation/nhis2025-native-framing-receipt-v1.json"
    value = json.loads(target.read_bytes())
    value["native"]["sha256"] = sha(b"substitute")
    target.write_text(json.dumps(value), encoding="utf-8")
    refused(delivery)


@pytest.mark.parametrize("origin", [None, "foreign", "same_bytes_foreign"])
def test_loaded_implementation_must_belong_to_checked_checkout(delivery, monkeypatch, origin):
    root = delivery[0]
    if origin == "same_bytes_foreign":
        outside = root.parent / "foreign-code.py"
        outside.write_bytes((root / next(iter(guard._IMPLEMENTATIONS))).read_bytes())
        value = str(outside)
    else:
        value = None if origin is None else str(root.parent / "PRIVATE-FOREIGN-CODE.py")
    monkeypatch.setattr(guard.decoder, "__file__", value)
    refused(delivery)


@pytest.mark.parametrize(
    "content",
    [
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b"[]",
        b"{",
        b"\xff",
        b'{"x":1e999}',
        b'{"x":-1e999}',
        b'{"nested":[1e999]}',
    ],
)
def test_strict_json_refusal_with_synthetic_replaced_pin(delivery, monkeypatch, content):
    name = next(iter(guard._DOCUMENTS))
    (delivery[0] / name).write_bytes(content)
    monkeypatch.setattr(guard, "_DOCUMENTS", guard._DOCUMENTS | {name: sha(content)})
    refused(delivery)


@pytest.mark.parametrize("which", ["archive", "native", "document", "code"])
def test_missing_local_files_refuse_without_paths(delivery, which):
    root, archive, native, *_ = delivery
    target = {
        "archive": archive,
        "native": native,
        "document": root / next(iter(guard._DOCUMENTS)),
        "code": root / next(iter(guard._IMPLEMENTATIONS)),
    }[which]
    target.unlink()  # A known synthetic tmp_path file only.
    refused(delivery)


@pytest.mark.parametrize("which", ["archive", "native"])
def test_source_read_is_bounded_before_materialization(delivery, monkeypatch, which):
    target = delivery[1 if which == "archive" else 2]
    target.write_bytes(target.read_bytes() + b"X")
    original = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == target:
            pytest.fail("Oversized source must refuse before opening it")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    refused(delivery)


def test_documentary_resource_cap_precedes_read(delivery, monkeypatch):
    monkeypatch.setattr(guard, "_MAX_BYTES", 1)

    def forbidden(*args, **kwargs):
        pytest.fail("Oversized documentary artifact must refuse before opening")

    monkeypatch.setattr(Path, "open", forbidden)
    refused(delivery)


@pytest.mark.parametrize("kind", ["other_member", "duplicate", "archive_comment", "member_comment"])
def test_archive_structure_refuses_even_with_synthetic_identity(delivery, monkeypatch, kind):
    native = delivery[4]
    if kind == "other_member":
        zipped = archive_bytes(native, name="PRIVATE-UNEXPECTED-NAME")
    elif kind == "duplicate":
        zipped = archive_bytes(native, extra=True)
    elif kind == "archive_comment":
        zipped = archive_bytes(native, comment=b"PRIVATE-COMMENT")
    else:
        zipped = archive_bytes(native, member_comment=b"PRIVATE-COMMENT")
    delivery[1].write_bytes(zipped)
    monkeypatch.setattr(guard, "_EXPECTED", expected(zipped, native))
    refused(delivery)


def test_zip_crc_is_actually_checked_not_only_copied_from_directory(delivery, monkeypatch):
    corrupted = bytearray(delivery[3])
    # Stored-member payload begins after its local header and literal filename.
    corrupted[30 + len("adult25.dat")] ^= 1
    corrupted = bytes(corrupted)
    delivery[1].write_bytes(corrupted)
    monkeypatch.setattr(guard, "_EXPECTED", replace(guard._EXPECTED, archive_sha256=sha(corrupted)))
    refused(delivery)


@pytest.mark.parametrize("kind", ["encryption", "unsupported_compression", "crc", "size"])
def test_archive_metadata_contract_refuses(delivery, monkeypatch, kind):
    original = zipfile.ZipFile.infolist

    def patched(archive):
        members = original(archive)
        if kind == "encryption":
            members[0].flag_bits |= 1
        elif kind == "unsupported_compression":
            members[0].compress_type = zipfile.ZIP_BZIP2
        elif kind == "crc":
            members[0].CRC ^= 1
        else:
            members[0].file_size += 1
        return members

    monkeypatch.setattr(zipfile.ZipFile, "infolist", patched)
    refused(delivery)


@pytest.mark.parametrize("kind", ["lf", "short", "nonascii", "control", "no_final", "wrong_count"])
def test_framing_independent_of_zip_and_source_identity(delivery, monkeypatch, kind):
    native = delivery[4]
    if kind == "lf":
        native = native[:-2] + b"\n"
    elif kind == "short":
        native = native[1:]
    elif kind == "nonascii":
        native = b"\xff" + native[1:]
    elif kind == "control":
        native = b"\t" + native[1:]
    elif kind == "no_final":
        native = native[:-2]
    zipped = archive_bytes(native)
    delivery[1].write_bytes(zipped)
    delivery[2].write_bytes(native)
    monkeypatch.setattr(
        guard, "_EXPECTED", expected(zipped, native, records=2 if kind == "wrong_count" else 1)
    )
    refused(delivery)


def test_archive_and_separately_pinned_native_must_match(delivery, monkeypatch):
    replacement = b"X" + delivery[4][1:]
    delivery[2].write_bytes(replacement)
    monkeypatch.setattr(
        guard, "_EXPECTED", replace(guard._EXPECTED, native_sha256=sha(replacement))
    )
    refused(delivery)


def test_source_reads_follow_documentary_and_code_verification(delivery, monkeypatch):
    (delivery[0] / next(iter(guard._DOCUMENTS))).write_bytes(b"tampered")
    original = guard._bounded_read

    def no_source_read(path, limit):
        if path in (delivery[1], delivery[2]):
            pytest.fail("Source must not be read before immutable documentary admission")
        return original(path, limit)

    monkeypatch.setattr(guard, "_bounded_read", no_source_read)
    refused(delivery)


def test_no_network_or_source_search(delivery, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Guard must neither acquire nor search for source files")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr(Path, "glob", forbidden)
    monkeypatch.setattr(Path, "rglob", forbidden)
    assert invoke(delivery).native_bytes == delivery[4]


def test_wrong_path_type_sanitized_before_any_read(delivery):
    with pytest.raises(ValueError, match="verified-delivery") as error:
        guard.verify_delivery("PRIVATE-PATH", delivery[2], root=delivery[0])
    assert error.value.__suppress_context__ is True
