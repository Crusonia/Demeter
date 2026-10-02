"""Launcher-only synthetic checks; frozen replay is mocked, with no source reads."""

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def launcher(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    module = importlib.import_module("run_ipop_predictive_supplement")

    def forbidden(*args, **kwargs):
        pytest.fail("Launcher tests must not acquire source records or fit a model")

    monkeypatch.setattr(module.frozen_replay, "load_sources", forbidden)
    monkeypatch.setattr(module.frozen_replay.lab, "paired_path_bootstrap", forbidden)
    monkeypatch.setattr(module.frozen_replay, "replay", forbidden)
    return module


def test_default_freeze_creates_missing_parents_and_publishes_toy_aggregate(
    launcher, monkeypatch, tmp_path
):
    output = tmp_path / "missing" / "nested" / "aggregate.json"
    calls = []

    def toy_replay(raw, *, freeze_commit):
        calls.append((raw, freeze_commit))
        assert output.parent.is_dir()
        assert not output.exists()
        assert len(list(output.parent.glob(".ipop-predictive-*"))) == 1
        return {"aggregate_only": True, "engine_activation_allowed": False}

    monkeypatch.setattr(launcher.frozen_replay, "replay", toy_replay)
    assert launcher.main(["--raw", "unread-cache", "--output", str(output)]) == 0
    assert calls == [(Path("unread-cache"), launcher.FROZEN_COMMIT)]
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "aggregate_only": True,
        "engine_activation_allowed": False,
    }
    assert not list(output.parent.glob(".ipop-predictive-*"))


@pytest.mark.parametrize("existing_kind", ("file", "directory"))
def test_existing_output_rejects_before_replay(launcher, tmp_path, existing_kind, capsys):
    output = tmp_path / "existing"
    if existing_kind == "file":
        output.write_text("original evidence", encoding="utf-8")
    else:
        output.mkdir()
    assert launcher.main(["--raw", "unread-cache", "--output", str(output)]) == 1
    if existing_kind == "file":
        assert output.read_text(encoding="utf-8") == "original evidence"
    else:
        assert output.is_dir()
    assert "Supplement unavailable" in capsys.readouterr().out
    assert not list(tmp_path.glob(".ipop-predictive-*"))


def test_invalid_parent_rejects_before_replay(launcher, tmp_path):
    parent = tmp_path / "not-a-directory"
    parent.write_text("preserved", encoding="utf-8")
    assert launcher.main(["--raw", "unread-cache", "--output", str(parent / "result.json")]) == 1
    assert parent.read_text(encoding="utf-8") == "preserved"


def test_unwritable_parent_preflight_has_generic_error(launcher, monkeypatch, tmp_path, capsys):
    def denied(*args, **kwargs):
        raise PermissionError("PRIVATE_SOURCE_TOKEN_AND_PATH")

    monkeypatch.setattr(launcher.tempfile, "mkstemp", denied)
    output = tmp_path / "result.json"
    assert launcher.main(["--raw", "unread-cache", "--output", str(output)]) == 1
    assert not output.exists()
    assert "PRIVATE_" not in capsys.readouterr().out


def test_preflight_write_failure_never_reaches_replay(launcher, monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise OSError("synthetic storage failure")

    monkeypatch.setattr(launcher.os, "fsync", denied)
    output = tmp_path / "result.json"
    assert launcher.main(["--raw", "unread-cache", "--output", str(output)]) == 1
    assert not output.exists()
    assert not list(tmp_path.glob(".ipop-predictive-*"))


def test_unsupported_hard_links_reject_before_replay(launcher, monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise OSError("synthetic destination rejects hard links")

    monkeypatch.setattr(launcher.os, "link", denied)
    output = tmp_path / "result.json"
    assert launcher.main(["--raw", "unread-cache", "--output", str(output)]) == 1
    assert not output.exists()
    assert not list(tmp_path.glob(".ipop-predictive-*"))
    assert not list(tmp_path.glob(".ipop-link-probe-*"))


def test_only_exact_supported_freeze_can_launch(launcher, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        launcher.frozen_replay,
        "replay",
        lambda raw, *, freeze_commit: calls.append(freeze_commit) or {"toy": True},
    )
    output = tmp_path / "result.json"
    assert (
        launcher.main(
            ["--raw", "unread-cache", "--output", str(output), "--freeze-commit", "0" * 40]
        )
        == 1
    )
    assert not output.exists()
    assert calls == []
    assert (
        launcher.main(
            [
                "--raw",
                "unread-cache",
                "--output",
                str(output),
                "--freeze-commit",
                launcher.FROZEN_COMMIT,
            ]
        )
        == 0
    )
    assert calls == [launcher.FROZEN_COMMIT]


def test_output_created_during_replay_is_never_overwritten(launcher, monkeypatch, tmp_path):
    output = tmp_path / "result.json"

    def toy_replay(*args, **kwargs):
        output.write_text("concurrent evidence", encoding="utf-8")
        return {"toy": True}

    monkeypatch.setattr(launcher.frozen_replay, "replay", toy_replay)
    assert launcher.main(["--raw", "unread-cache", "--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == "concurrent evidence"
    assert not list(tmp_path.glob(".ipop-predictive-*"))


@pytest.mark.parametrize("failure", ("replay", "nonfinite_json"))
def test_failed_replay_or_serialization_leaves_no_partial_output(
    launcher, monkeypatch, tmp_path, capsys, failure
):
    def toy_replay(*args, **kwargs):
        if failure == "replay":
            raise ValueError("PRIVATE_SOURCE_TOKEN")
        return {"toy": float("nan")}

    monkeypatch.setattr(launcher.frozen_replay, "replay", toy_replay)
    output = tmp_path / "result.json"
    assert launcher.main(["--raw", "unread-cache", "--output", str(output)]) == 1
    assert not output.exists()
    assert not list(tmp_path.glob(".ipop-predictive-*"))
    assert "PRIVATE_" not in capsys.readouterr().out
