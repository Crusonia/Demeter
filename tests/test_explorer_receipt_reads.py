"""Receipt reader failures remain explicit; transient Windows locks are bounded."""

import json

import pytest

from demeter.explorer import jobs


def sharing_error(code):
    error = PermissionError("Synthetic Windows sharing/access violation")
    error.winerror = code
    return error


class Receipt:
    def __init__(self, *outcomes):
        self.outcomes = outcomes
        self.calls = 0

    def read_bytes(self):
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.mark.parametrize("code", [5, 32, 33])
def test_transient_windows_read_lock_retries_complete_receipt(monkeypatch, code):
    sleeps = []
    monkeypatch.setattr(jobs.time, "sleep", sleeps.append)
    receipt = Receipt(sharing_error(code), sharing_error(code), b'{"status":"complete"}')
    assert jobs.read_json(receipt) == {"status": "complete"}
    assert receipt.calls == 3
    assert sleeps == [0.05, 0.05]


@pytest.mark.parametrize("code", [5, 32, 33])
def test_persistent_windows_read_lock_exhausts_and_preserves_error(monkeypatch, code):
    sleeps = []
    monkeypatch.setattr(jobs.time, "sleep", sleeps.append)
    error = sharing_error(code)
    receipt = Receipt(error)
    with pytest.raises(PermissionError) as caught:
        jobs.read_json(receipt)
    assert caught.value is error
    assert receipt.calls == 20
    assert sleeps == [0.05] * 19


@pytest.mark.parametrize(
    "error",
    [
        PermissionError("Non-Windows permission denied"),
        sharing_error(13),
        sharing_error(2),
        FileNotFoundError("Missing receipt"),
        OSError("Other filesystem failure"),
    ],
)
def test_unrelated_read_errors_are_not_retried(monkeypatch, error):
    sleeps = []
    monkeypatch.setattr(jobs.time, "sleep", sleeps.append)
    receipt = Receipt(error, b'{"status":"complete"}')
    with pytest.raises(type(error)) as caught:
        jobs.read_json(receipt)
    assert caught.value is error
    assert receipt.calls == 1
    assert sleeps == []


@pytest.mark.parametrize("prefix", [(), (sharing_error(32),)])
def test_malformed_json_is_not_retried_after_successful_open(monkeypatch, prefix):
    sleeps = []
    monkeypatch.setattr(jobs.time, "sleep", sleeps.append)
    receipt = Receipt(*prefix, b'{"status":', b'{"status":"complete"}')
    with pytest.raises(json.JSONDecodeError):
        jobs.read_json(receipt)
    assert receipt.calls == len(prefix) + 1
    assert sleeps == [0.05] * len(prefix)


def test_successful_receipt_bytes_are_unchanged(tmp_path):
    path = tmp_path / "run.json"
    content = b'{ "status": "running", "stage": "Calculating" }\r\n'
    path.write_bytes(content)
    assert jobs.read_json(path) == {"status": "running", "stage": "Calculating"}
    assert path.read_bytes() == content
