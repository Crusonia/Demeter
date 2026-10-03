"""Acquisition refusal and immutable publication tests using invented bytes only."""

from email.message import Message
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "fetch_repeat", Path(__file__).resolve().parents[1] / "scripts/fetch_nhanes3_repeat.py"
)
assert SPEC and SPEC.loader
fetcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetcher)


class Response:
    def __init__(self, url, body=b"synthetic native bytes\r\n", **headers):
        self.url, self.body = url, body
        self.status = 200
        self.headers = Message()
        defaults = {"Content-Type": "text/plain", "Content-Length": str(len(body))}
        defaults.update(headers)
        for key, value in defaults.items():
            if value is not None:
                self.headers[key] = value

    def geturl(self):
        return self.url

    def read(self, size):
        value, self.body = self.body[:size], self.body[size:]
        return value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def guarded(monkeypatch):
    monkeypatch.setattr(fetcher, "_committed_protocol", lambda: ({}, "a" * 40))


def mock_source(monkeypatch, factory=Response):
    calls = []

    def open_source(url, timeout):
        calls.append(url)
        assert timeout == 60
        return factory(url)

    monkeypatch.setattr(fetcher, "build_opener", lambda *args: SimpleNamespace(open=open_source))
    return calls


def test_success_preserves_exact_bytes_and_publishes_manifest_last(tmp_path, monkeypatch, guarded):
    calls = mock_source(monkeypatch)
    writes = []
    original = fetcher._write_json

    def record(path, value):
        writes.append(path.name)
        original(path, value)

    monkeypatch.setattr(fetcher, "_write_json", record)
    store = tmp_path / "store"
    result = fetcher.fetch(store)
    manifest = json.loads((store / "manifest.json").read_bytes())
    assert calls == list(fetcher.SOURCE_URLS.values())
    assert result["component_count"] == 3
    assert writes[-2:] == ["manifest.json", "complete.json"]
    for filename, item in manifest["sources"].items():
        raw = (store / filename).read_bytes()
        assert raw == b"synthetic native bytes\r\n"
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()
        assert item["size_bytes"] == len(raw)
        assert item["bytes"] == len(raw)
        assert item["component"] + ".DAT" == filename
        assert item["participant_records_decoded"] is False
    assert manifest["protocol_sha256"] == fetcher.PROTOCOL_SHA256
    assert manifest["invocation_commit"] == "a" * 40
    assert manifest["protocol_authoring_commit"] == fetcher.PROTOCOL_COMMIT


def test_existing_empty_store_refused_without_network(tmp_path, monkeypatch, guarded):
    store = tmp_path / "store"
    store.mkdir()
    calls = mock_source(monkeypatch)
    with pytest.raises(fetcher.AcquisitionError, match="already exists"):
        fetcher.fetch(store)
    assert not calls
    assert not list(store.iterdir())


def test_protected_source_tree_attempt_receipts_are_outside_data(tmp_path, monkeypatch, guarded):
    monkeypatch.setattr(fetcher, "ROOT", tmp_path)
    mock_source(monkeypatch)
    store = tmp_path / "data/sources/nhanes3/1988-1994-repeat"
    result = fetcher.fetch(store)
    attempt = Path(result["attempt_receipts"])
    assert attempt.is_relative_to(tmp_path / "outputs/nhanes3-acquisition")
    assert (attempt / "attempt.json").is_file()
    assert (attempt / "complete.json").is_file()
    assert not list((tmp_path / "data").rglob("*.attempt-*"))
    assert {item.name for item in store.iterdir()} == {
        "LAB.DAT",
        "ADULT.DAT",
        "LABSE.DAT",
        "manifest.json",
    }


def test_protected_source_failure_retains_receipts_outside_data(tmp_path, monkeypatch, guarded):
    monkeypatch.setattr(fetcher, "ROOT", tmp_path)

    def fail(url, path):
        path.write_bytes(b"synthetic partial original")
        raise fetcher.AcquisitionError("synthetic transport failure")

    monkeypatch.setattr(fetcher, "_download", fail)
    store = tmp_path / "data/sources/store"
    with pytest.raises(fetcher.AcquisitionError):
        fetcher.fetch(store)
    attempts = list((tmp_path / "outputs/nhanes3-acquisition").glob("*.attempt-*"))
    assert len(attempts) == 1 and (attempts[0] / "failure.json").is_file()
    assert (store / "LAB.DAT").read_bytes() == b"synthetic partial original"
    assert not (store / "manifest.json").exists()
    assert not list((tmp_path / "data").rglob("*.attempt-*"))


def test_reservation_race_cannot_replace_empty_directory(tmp_path, monkeypatch, guarded):
    store = tmp_path / "store"
    real_mkdir = Path.mkdir
    calls = mock_source(monkeypatch)

    def race(path, *args, **kwargs):
        if path == store:
            real_mkdir(path)
        return real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", race)
    with pytest.raises(fetcher.AcquisitionError, match="retained"):
        fetcher.fetch(store)
    assert store.is_dir() and not list(store.iterdir())
    assert not calls
    failure = next(tmp_path.glob(".store.attempt-*/failure.json"))
    assert json.loads(failure.read_bytes())["partial_originals"] == {}


def test_protocol_failure_precedes_network_and_store_mutation(tmp_path, monkeypatch):
    def reject():
        raise fetcher.AcquisitionError("protocol byte identity mismatch")

    monkeypatch.setattr(fetcher, "_committed_protocol", reject)
    calls = mock_source(monkeypatch)
    with pytest.raises(fetcher.AcquisitionError, match="protocol"):
        fetcher.fetch(tmp_path / "store")
    assert not calls and not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "headers,body",
    [
        ({"Content-Type": "text/html"}, b"not inspected"),
        ({"Content-Type": None}, b"not inspected"),
        ({"Content-Type": "text/plain; charset=latin1"}, b"not inspected"),
        ({"Content-Encoding": "gzip"}, b"not inspected"),
        ({"Content-Length": "oops"}, b"not inspected"),
        ({"Content-Length": "9999999999"}, b"not inspected"),
        ({"Content-Length": "1"}, b"too long"),
        ({}, b""),
        ({}, b"<html>not a native source</html>"),
        ({}, b"unexpected\xffencoding"),
    ],
)
def test_transport_failures_preserve_attempt_no_manifest_and_refuse_rerun(
    tmp_path, monkeypatch, guarded, headers, body
):
    mock_source(monkeypatch, lambda url: Response(url, body, **headers))
    store = tmp_path / "store"
    with pytest.raises(fetcher.AcquisitionError, match="retained"):
        fetcher.fetch(store)
    assert not (store / "manifest.json").exists()
    assert (store / "LAB.DAT").exists()
    failure = json.loads(next(tmp_path.glob(".store.attempt-*/failure.json")).read_bytes())
    assert failure["canonical_manifest_published"] is False
    assert failure["participant_records_decoded"] is False
    with pytest.raises(fetcher.AcquisitionError, match="already exists"):
        fetcher.fetch(store)


def test_stream_bound_checked_without_large_allocations(tmp_path, monkeypatch, guarded):
    monkeypatch.setattr(fetcher, "MAX_BYTES", 8)
    mock_source(monkeypatch, lambda url: Response(url, b"ninebytes", **{"Content-Length": None}))
    with pytest.raises(fetcher.AcquisitionError):
        fetcher.fetch(tmp_path / "store")
    assert not (tmp_path / "store/manifest.json").exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://wwwn.cdc.gov/nchs/data/nhanes3/1a/lab.dat",
        "https://example.org/nchs/data/nhanes3/1a/lab.dat",
        "https://wwwn.cdc.gov/nchs/data/nhanes3/1a/lab.dat?token=secret",
        "https://user:secret@wwwn.cdc.gov/nchs/data/nhanes3/1a/lab.dat",
        "https://wwwn.cdc.gov/nchs/data/nhanes3/1a/adult.dat",
    ],
)
def test_redirect_identity_refused(url):
    assert not fetcher._allowed_url(url, fetcher.SOURCE_URLS["LAB"])
    guard = fetcher._ProducerRedirects(fetcher.SOURCE_URLS["LAB"])
    with pytest.raises(fetcher.AcquisitionError, match="redirect"):
        guard.redirect_request(None, None, 302, "unused", {}, url)


def test_case_only_official_redirect_supported():
    assert fetcher._allowed_url(
        fetcher.SOURCE_URLS["LAB"].replace("lab.dat", "LAB.DAT"), fetcher.SOURCE_URLS["LAB"]
    )


def test_cli_requires_explicit_download_and_sanitizes_network_error(
    tmp_path, monkeypatch, guarded, capsys
):
    calls = mock_source(monkeypatch)
    with pytest.raises(SystemExit):
        fetcher.main([])
    assert not calls

    def fail(url, path):
        raise RuntimeError("secret server body or individual record")

    monkeypatch.setattr(fetcher, "_download", fail)
    assert fetcher.main(["--download", "--destination", str(tmp_path / "store")]) == 1
    assert "secret server" not in capsys.readouterr().out


def test_duplicate_json_key_refused():
    with pytest.raises(fetcher.AcquisitionError, match="duplicate"):
        json.loads('{"same":1,"same":2}', object_pairs_hook=fetcher._unique)


def test_actual_committed_protocol_guard_is_offline():
    protocol, commit = fetcher._committed_protocol()
    assert protocol["model_role"] == "benchmark_only"
    assert len(commit) == 40


def test_modified_protocol_refused_before_git_or_network(tmp_path, monkeypatch):
    protocol = tmp_path / fetcher.PROTOCOL
    protocol.parent.mkdir(parents=True)
    protocol.write_bytes(b"{}")
    monkeypatch.setattr(fetcher, "ROOT", tmp_path)
    with pytest.raises(fetcher.AcquisitionError, match="byte identity"):
        fetcher._committed_protocol()


def test_uncommitted_protocol_refused(monkeypatch):
    def run(command, **kwargs):
        return SimpleNamespace(stdout=b"{}" if command[1] == "show" else b"a" * 40)

    monkeypatch.setattr(fetcher.subprocess, "run", run)
    with pytest.raises(fetcher.AcquisitionError, match="not committed"):
        fetcher._committed_protocol()


def test_missing_authoring_commit_or_nonancestor_does_not_block_pinned_head(monkeypatch):
    commands = []
    raw = (fetcher.ROOT / fetcher.PROTOCOL).read_bytes()

    def run(command, **kwargs):
        commands.append(command)
        if command[1] == "show":
            return SimpleNamespace(stdout=raw)
        if command[1:] == ["rev-parse", "HEAD"]:
            return SimpleNamespace(stdout=b"b" * 40 + b"\n")
        raise AssertionError("Authoring history must not be required in shallow or squash clones")

    monkeypatch.setattr(fetcher.subprocess, "run", run)
    protocol, invocation = fetcher._committed_protocol()
    assert protocol["kind"] == "nhanes3_repeat_intake_protocol"
    assert invocation == "b" * 40
    assert len(commands) == 2
