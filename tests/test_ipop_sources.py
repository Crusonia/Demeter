"""Synthetic HTTP/source bytes only. No participant source or network access."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from demeter.data import ipop as candidate

PRIVATE = "PRIVATE_SYNTHETIC_SERVER_OR_PATH_MARKER"
ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads(
    (ROOT / "docs/validation/ipop-numerical-preflight-protocol-v1.json").read_bytes()
)
BODIES = {"clinical": b"\xff\x00synthetic-opaque-one", "sample_info": b"synthetic-opaque-two\r\n"}


class Response:
    def __init__(self, content, url, *, status=200, media="text/plain; charset=utf-8", chunk=None):
        self.content = content
        self.url = url
        self.status = status
        self.headers = {"Content-Type": media}
        self.offset = 0
        self.chunk = chunk
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size):
        self.read_sizes.append(size)
        if self.chunk is not None:
            size = min(size, self.chunk)
        data = self.content[self.offset : self.offset + size]
        self.offset += len(data)
        return data


@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network_not_allowed_in_synthetic_tests")

    monkeypatch.setattr(candidate, "build_opener", blocked)


@pytest.fixture
def roots(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    raw = tmp_path / "data" / "raw"
    outputs.mkdir()
    raw.mkdir(parents=True)
    monkeypatch.setattr(candidate, "ALLOWED_ROOTS", (outputs, raw))
    return outputs, raw


def fixture_protocol():
    protocol = copy.deepcopy(FROZEN)
    for role, content in BODIES.items():
        protocol["source_selection"][role]["tree_size_bytes"] = len(content)
        protocol["source_selection"][role]["git_blob"] = candidate._blob(content)
    return protocol


def fake_network(monkeypatch, *, changed=None, factory=None):
    calls = []
    responses = []

    def open_source(url):
        calls.append(url)
        role = next(role for role, pin in candidate.SOURCE_PINS.items() if pin["url"] == url)
        if factory:
            response = factory(role, url)
        else:
            response = Response((changed or BODIES)[role], url)
        responses.append(response)
        return response

    monkeypatch.setattr(candidate, "_open_source", open_source)
    return calls, responses


def acquire(monkeypatch, path, **kwargs):
    fake_network(monkeypatch, **kwargs)
    return candidate.fetch_sources(fixture_protocol(), path, validation_only=True)


def assert_failed(result, stage=None):
    assert result["passed"] is False
    assert result["sources"] is None
    if stage:
        assert result["provenance"]["failure_stage"] == stage
    assert PRIVATE not in json.dumps(result["provenance"], allow_nan=False)


@pytest.mark.parametrize("root_index", [0, 1])
def test_verified_full_bytes_and_offline_replay_are_not_participant_parsing(
    roots, monkeypatch, root_index
):
    path = roots[root_index] / "fresh"
    calls, _ = fake_network(monkeypatch)
    result = candidate.fetch_sources(fixture_protocol(), path, validation_only=True)
    assert result["passed"] is True
    assert result["receipt_saved"] is True
    assert result["sources"] == BODIES  # Invalid UTF-8 proves no participant parser runs.
    assert calls == [pin["url"] for pin in candidate.SOURCE_PINS.values()]
    provenance = result["provenance"]
    assert provenance["validation_only"] is True
    assert provenance["interpretation"] == "synthetic fixture only"
    assert (
        provenance["implementation_sha256"]
        == hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest()
    )
    receipt = json.loads((path / candidate.RECEIPT_FILENAME).read_bytes())
    for role, body in BODIES.items():
        entry = receipt["sources"][role]
        assert entry["full_bytes"] is True
        assert entry["bytes_retained"] is True
        assert entry["size_bytes"] == len(body)
        assert entry["sha256"] == hashlib.sha256(body).hexdigest()
        assert entry["git_blob"] == candidate._blob(body)
        assert entry["content_type"] == "text/plain"
        assert datetime.fromisoformat(entry["retrieved_utc"]).utcoffset().total_seconds() == 0
        assert (path / entry["cache_filename"]).read_bytes() == body
    monkeypatch.setattr(
        candidate, "_open_source", lambda *args: pytest.fail("offline replay fetched")
    )
    replay = candidate.load_sources(path, fixture_protocol(), validation_only=True)
    assert replay["passed"] is True
    assert replay["sources"] == BODIES
    assert replay["provenance"]["verification_mode"] == "local_byte_replay"
    assert replay["provenance"]["sources"] == receipt["sources"]


def test_fixture_pins_cannot_pass_production_or_change_fixed_urls(roots, monkeypatch):
    calls, _ = fake_network(monkeypatch)
    assert_failed(
        candidate.fetch_sources(fixture_protocol(), roots[0] / "a"), "protocol_declarations"
    )
    protocol = fixture_protocol()
    protocol["source_selection"]["clinical"]["url"] = "https://example.org/" + PRIVATE
    assert_failed(
        candidate.fetch_sources(protocol, roots[0] / "b", validation_only=True),
        "protocol_declarations",
    )
    assert calls == []
    assert not (roots[0] / "a").exists()
    assert not (roots[0] / "b").exists()


@pytest.mark.parametrize("bad", [True, "20", 0, -1])
def test_bad_size_declarations_fail_before_network(roots, monkeypatch, bad):
    calls, _ = fake_network(monkeypatch)
    protocol = fixture_protocol()
    protocol["source_selection"]["sample_info"]["tree_size_bytes"] = bad
    assert_failed(
        candidate.fetch_sources(protocol, roots[0] / "fresh", validation_only=True),
        "protocol_declarations",
    )
    assert calls == []


@pytest.mark.parametrize("kind", ["short", "same_size_changed", "oversize"])
def test_bad_second_identity_returns_no_first_source_and_preserves_failed_receipt(
    roots, monkeypatch, kind
):
    changed = dict(BODIES)
    changed["sample_info"] = {
        "short": BODIES["sample_info"][:-1],
        "same_size_changed": b"X" + BODIES["sample_info"][1:],
        "oversize": BODIES["sample_info"] + PRIVATE.encode() * 1000,
    }[kind]
    path = roots[0] / "fresh"
    calls, responses = fake_network(monkeypatch, changed=changed)
    result = candidate.fetch_sources(fixture_protocol(), path, validation_only=True)
    assert_failed(result, "source_identity" if kind == "same_size_changed" else "source_size")
    assert result["receipt_saved"] is True
    assert len(calls) == 2
    assert (path / "clinical_tests.txt").read_bytes() == BODIES["clinical"]
    assert not (path / "SampleInfo.csv").exists()
    receipt = json.loads((path / candidate.RECEIPT_FILENAME).read_bytes())
    assert receipt["sources"]["sample_info"]["bytes_retained"] is False
    if kind == "oversize":
        assert responses[1].offset == len(BODIES["sample_info"]) + 1
        assert receipt["sources"]["sample_info"]["full_bytes"] is False
    assert_failed(
        candidate.load_sources(path, fixture_protocol(), validation_only=True), "receipt_metadata"
    )


def test_fragmented_http_reads_are_complete_not_misclassified(roots, monkeypatch):
    result = acquire(
        monkeypatch,
        roots[0] / "fresh",
        factory=lambda role, url: Response(BODIES[role], url, chunk=2),
    )
    assert result["passed"] is True
    assert result["sources"] == BODIES


@pytest.mark.parametrize("issue", ["redirect", "status", "bool_status", "media", "exception"])
def test_response_failures_disclose_only_constants_and_do_not_retry(roots, monkeypatch, issue):
    def factory(role, url):
        if issue == "exception":
            raise URLError(PRIVATE)
        return Response(
            BODIES[role],
            "https://example.org/?token=" + PRIVATE if issue == "redirect" else url,
            status=True if issue == "bool_status" else 403 if issue == "status" else 200,
            media="text/html; secret=" + PRIVATE if issue == "media" else "text/plain",
        )

    calls, responses = fake_network(monkeypatch, factory=factory)
    path = roots[0] / "fresh"
    result = candidate.fetch_sources(fixture_protocol(), path, validation_only=True)
    expected = {
        "redirect": "redirect_rejected",
        "status": "http_status",
        "bool_status": "http_status",
        "media": "content_type",
        "exception": "network_failure",
    }[issue]
    assert_failed(result, expected)
    assert len(calls) == 1
    assert not (path / "clinical_tests.txt").exists()
    assert result["receipt_saved"] is True
    assert PRIVATE not in (path / candidate.RECEIPT_FILENAME).read_text()
    if responses:
        assert responses[0].read_sizes == []


def test_redirect_handler_rejects_other_and_same_url_without_following():
    url = candidate.SOURCE_PINS["clinical"]["url"]
    for target in (url, "https://example.org/?" + PRIVATE):
        with pytest.raises(candidate._Failure, match="^redirect_rejected$") as caught:
            candidate._NoRedirect().redirect_request(Request(url), None, 302, PRIVATE, {}, target)
        assert caught.value.status == 302


def test_ordinary_opener_receives_exact_frozen_url_and_bounded_timeout(monkeypatch):
    calls = []

    class Opener:
        def open(self, request, **kwargs):
            calls.append((request.full_url, kwargs))
            return "synthetic_response"

    def builder(handler):
        assert isinstance(handler, candidate._NoRedirect)
        return Opener()

    monkeypatch.setattr(candidate, "build_opener", builder)
    url = candidate.SOURCE_PINS["clinical"]["url"]
    assert candidate._open_source(url) == "synthetic_response"
    assert calls == [(url, {"timeout": 30})]


def test_http_error_status_is_retained_without_payload(roots, monkeypatch):
    def denied(*args):
        raise HTTPError("https://example.org/" + PRIVATE, 401, PRIVATE, {}, None)

    monkeypatch.setattr(candidate, "_open_source", denied)
    path = roots[0] / "fresh"
    result = candidate.fetch_sources(fixture_protocol(), path, validation_only=True)
    assert_failed(result, "http_status")
    assert result["provenance"]["sources"]["clinical"]["status"] == 401
    assert PRIVATE not in (path / candidate.RECEIPT_FILENAME).read_text()


def test_existing_destination_and_outside_root_are_never_repurposed(roots, tmp_path, monkeypatch):
    calls, _ = fake_network(monkeypatch)
    existing = roots[0] / "existing"
    existing.mkdir()
    marker = existing / candidate.RECEIPT_FILENAME
    marker.write_bytes(PRIVATE.encode())
    assert_failed(
        candidate.fetch_sources(fixture_protocol(), existing, validation_only=True),
        "destination_not_fresh",
    )
    assert marker.read_bytes() == PRIVATE.encode()
    assert_failed(
        candidate.fetch_sources(fixture_protocol(), tmp_path / "outside", validation_only=True),
        "unsafe_directory",
    )
    assert calls == []
    fresh = roots[0] / "absent_parent" / "fresh"
    result = candidate.fetch_sources(fixture_protocol(), fresh, validation_only=True)
    assert result["passed"]
    assert fresh.is_dir()
    assert len(calls) == 2


def test_raced_raw_hardlink_cannot_overwrite_reserved_receipt(roots, monkeypatch):
    path = roots[0] / "fresh"

    def factory(role, url):
        os.link(path / candidate.RECEIPT_FILENAME, path / "clinical_tests.txt")
        return Response(BODIES[role], url)

    result = acquire(monkeypatch, path, factory=factory)
    assert_failed(result, "raw_write")
    assert result["receipt_saved"] is True
    assert (path / "clinical_tests.txt").read_bytes() == (
        path / candidate.RECEIPT_FILENAME
    ).read_bytes()


def test_partial_raw_write_is_retained_and_explicitly_disclosed(roots, monkeypatch):
    path = roots[0] / "fresh"
    original = Path.open

    class FailedWrite:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()
            return False

        def write(self, content):
            self.stream.write(content[:3])
            self.stream.flush()
            raise OSError(PRIVATE)

    def partial(self, mode="r", *args, **kwargs):
        stream = original(self, mode, *args, **kwargs)
        return FailedWrite(stream) if self.name == "clinical_tests.txt" and mode == "xb" else stream

    monkeypatch.setattr(Path, "open", partial)
    result = acquire(monkeypatch, path)
    assert_failed(result, "raw_write")
    assert result["receipt_saved"] is True
    assert (path / "clinical_tests.txt").read_bytes() == BODIES["clinical"][:3]
    receipt = json.loads((path / candidate.RECEIPT_FILENAME).read_bytes())
    entry = receipt["sources"]["clinical"]
    assert entry["raw_write_failure_may_leave_partial_bytes"] is True
    assert entry["bytes_retained"] is False
    assert entry["size_bytes"] == len(BODIES["clinical"])
    assert "partial_size_bytes" not in entry
    assert_failed(
        candidate.load_sources(path, fixture_protocol(), validation_only=True), "receipt_metadata"
    )


def test_windows_reparse_attribute_rejects_parent_without_junction_api(roots, monkeypatch):
    parent = roots[0] / "reparse_parent"
    parent.mkdir()
    original = Path.lstat

    def reparse(self, *args, **kwargs):
        if self == parent:
            return SimpleNamespace(st_mode=candidate.stat.S_IFDIR, st_file_attributes=0x400)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", reparse)
    calls, _ = fake_network(monkeypatch)
    assert_failed(
        candidate.fetch_sources(fixture_protocol(), parent / "fresh", validation_only=True),
        "unsafe_directory",
    )
    assert calls == []


def test_offline_raw_hardlink_alias_rejected_even_with_matching_fixture_pins(roots, monkeypatch):
    bodies = {"clinical": b"same synthetic bytes", "sample_info": b"same synthetic bytes"}
    protocol = fixture_protocol()
    for role, content in bodies.items():
        protocol["source_selection"][role].update(
            git_blob=candidate._blob(content), tree_size_bytes=len(content)
        )
    fake_network(monkeypatch, changed=bodies)
    path = roots[0] / "fresh"
    assert candidate.fetch_sources(protocol, path, validation_only=True)["passed"] is True
    (path / "SampleInfo.csv").unlink()
    os.link(path / "clinical_tests.txt", path / "SampleInfo.csv")
    assert_failed(candidate.load_sources(path, protocol, validation_only=True), "raw_alias")


@pytest.mark.parametrize(
    "mutation",
    [
        "url",
        "final_url",
        "filename",
        "size",
        "hash",
        "blob",
        "naive_time",
        "full_bytes",
        "status",
        "extra",
        "validation_only",
    ],
)
def test_offline_receipt_tampering_cannot_be_echoed_or_trusted(roots, monkeypatch, mutation):
    path = roots[0] / "fresh"
    assert acquire(monkeypatch, path)["passed"] is True
    receipt_path = path / candidate.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_bytes())
    entry = receipt["sources"]["clinical"]
    if mutation == "validation_only":
        receipt["validation_only"] = False
    else:
        key, value = {
            "url": ("requested_url", "https://example.org/" + PRIVATE),
            "final_url": ("final_url", "https://example.org/" + PRIVATE),
            "filename": ("cache_filename", "../" + PRIVATE),
            "size": ("size_bytes", True),
            "hash": ("sha256", "0" * 64),
            "blob": ("git_blob", "0" * 40),
            "naive_time": ("retrieved_utc", "2026-10-01T12:00:00"),
            "full_bytes": ("full_bytes", False),
            "status": ("status", True),
            "extra": ("secret", PRIVATE),
        }[mutation]
        entry[key] = value
    receipt_path.write_text(json.dumps(receipt))
    result = candidate.load_sources(path, fixture_protocol(), validation_only=True)
    assert_failed(result, "source_identity" if mutation == "hash" else "receipt_metadata")


def test_offline_duplicate_json_keys_rejected_without_private_text(roots, monkeypatch):
    path = roots[0] / "fresh"
    assert acquire(monkeypatch, path)["passed"] is True
    receipt = path / candidate.RECEIPT_FILENAME
    receipt.write_text('{"secret":"' + PRIVATE + '","secret":1}')
    assert_failed(
        candidate.load_sources(path, fixture_protocol(), validation_only=True), "receipt_metadata"
    )


@pytest.mark.parametrize("change", ["missing", "same_size", "oversize"])
def test_offline_changed_or_missing_raw_never_returns_other_verified_source(
    roots, monkeypatch, change
):
    path = roots[0] / "fresh"
    assert acquire(monkeypatch, path)["passed"] is True
    raw = path / "SampleInfo.csv"
    if change == "missing":
        raw.unlink()
    elif change == "same_size":
        raw.write_bytes(b"X" + BODIES["sample_info"][1:])
    else:
        raw.write_bytes(BODIES["sample_info"] + b"X")
    assert_failed(
        candidate.load_sources(path, fixture_protocol(), validation_only=True),
        {"missing": "raw_unavailable", "same_size": "source_identity", "oversize": "source_size"}[
            change
        ],
    )


@pytest.mark.parametrize("method", ["resolve", "is_file", "read_bytes"])
def test_offline_permission_errors_are_sanitized(roots, monkeypatch, method):
    path = roots[0] / "fresh"
    assert acquire(monkeypatch, path)["passed"] is True
    original = getattr(Path, method)

    def denied(self, *args, **kwargs):
        if self.name == ("fresh" if method == "resolve" else candidate.RECEIPT_FILENAME):
            raise PermissionError(PRIVATE)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, method, denied)
    assert_failed(candidate.load_sources(path, fixture_protocol(), validation_only=True))


def test_late_implementation_hash_failure_is_atomic(roots, monkeypatch):
    path = roots[0] / "fresh"
    original = Path.read_bytes

    def denied(self):
        if self == Path(candidate.__file__):
            raise PermissionError(PRIVATE)
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", denied)
    assert_failed(acquire(monkeypatch, path), "implementation_provenance")
    assert_failed(
        candidate.load_sources(path, fixture_protocol(), validation_only=True),
        "implementation_provenance",
    )


def test_symlink_parent_and_raw_path_are_not_followed(roots, tmp_path, monkeypatch):
    link = roots[0] / "linked_parent"
    target = tmp_path / "outside_target"
    target.mkdir()
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Windows symlink privilege unavailable")
    calls, _ = fake_network(monkeypatch)
    assert_failed(
        candidate.fetch_sources(fixture_protocol(), link / "fresh", validation_only=True),
        "unsafe_directory",
    )
    assert calls == []
    path = roots[0] / "fresh"
    assert acquire(monkeypatch, path)["passed"] is True
    (path / "SampleInfo.csv").unlink()
    (path / "SampleInfo.csv").symlink_to(path / "clinical_tests.txt")
    assert_failed(
        candidate.load_sources(path, fixture_protocol(), validation_only=True), "unsafe_directory"
    )
