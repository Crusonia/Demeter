"""Acquire or replay the two frozen public iPOP derivative source files.

The caller validates the complete frozen protocol; this module independently
checks its exact source declarations. No participant parser or report writer is
called here. Returned bytes are internal inputs, never a JSON report field.
Synthetic tests permit only explicitly labeled byte-pin substitutions.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

PROTOCOL_SHA256 = "2d8b53ae10a018fde16bc91108db57d49a788f473fc8fc0dfe65a44e28ac2b89"
COMMIT = "ba55996cb51a8bc4fbe9374633e9cb3223c6ea8c"
TREE = "021c4dfe091d3e554b3173711ab01fc06da15141"
RECEIPT_FILENAME = "acquisition-receipts.json"
ALLOWED_ROOTS = (Path.cwd() / "outputs", Path.cwd() / "data" / "raw")
SOURCE_PINS = {
    "clinical": {
        "path": "data/clinical_tests.txt",
        "url": f"https://raw.githubusercontent.com/gmiaslab/TemporalMultiomicsDiabetes/{COMMIT}/data/clinical_tests.txt",
        "git_blob": "cb01fe38378f8cef951837414e241c3e8d6a8bcc",
        "tree_size_bytes": 231694,
        "cache_filename": "clinical_tests.txt",
    },
    "sample_info": {
        "path": "data/SampleInfo.csv",
        "url": f"https://raw.githubusercontent.com/gmiaslab/TemporalMultiomicsDiabetes/{COMMIT}/data/SampleInfo.csv",
        "git_blob": "342d35d36eb422cf315a9757b7514c45312173e5",
        "tree_size_bytes": 36407,
        "cache_filename": "SampleInfo.csv",
    },
}
_MEDIA = frozenset(
    ("text/plain", "text/csv", "text/tab-separated-values", "application/octet-stream")
)
_MEDIA_HEADER = re.compile(
    r"(text/plain|text/csv|text/tab-separated-values|application/octet-stream)"
    r'(?:\s*;\s*charset\s*=\s*"?(?:utf-8|us-ascii|ascii)"?)?',
    re.ASCII | re.IGNORECASE,
)
_STAGES = frozenset(
    (
        "protocol_declarations",
        "unsafe_directory",
        "directory_unavailable",
        "destination_not_fresh",
        "receipt_write",
        "receipt_metadata",
        "receipt_unavailable",
        "redirect_rejected",
        "http_status",
        "content_type",
        "network_failure",
        "response_read",
        "source_size",
        "source_identity",
        "raw_write",
        "raw_unavailable",
        "unsafe_raw_path",
        "raw_alias",
        "implementation_provenance",
    )
)


class _Failure(ValueError):
    """Only a constant stage is exposed; no server, path or exception payload."""

    def __init__(self, stage: str, status: int | None = None):
        super().__init__(stage)
        self.status = status


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _pins(protocol: dict[str, Any], validation_only: bool) -> dict[str, dict[str, Any]]:
    try:
        if type(validation_only) is not bool or type(protocol) is not dict:
            raise _Failure("protocol_declarations")
        selection = protocol["source_selection"]
        if (
            type(selection) is not dict
            or selection["commit"] != COMMIT
            or selection["tree"] != TREE
            or protocol["protocol_id"] != "ipop_public_numerical_preflight_v1"
        ):
            raise _Failure("protocol_declarations")
        result = {}
        for role, expected in SOURCE_PINS.items():
            source = selection[role]
            if type(source) is not dict:
                raise _Failure("protocol_declarations")
            if source["path"] != expected["path"] or source["url"] != expected["url"]:
                raise _Failure("protocol_declarations")
            size = source["tree_size_bytes"]
            blob = source["git_blob"]
            if (
                type(size) is not int
                or size <= 0
                or type(blob) is not str
                or re.fullmatch(r"[0-9a-f]{40}", blob) is None
            ):
                raise _Failure("protocol_declarations")
            if not validation_only and (
                size != expected["tree_size_bytes"] or blob != expected["git_blob"]
            ):
                raise _Failure("protocol_declarations")
            result[role] = {**expected, "tree_size_bytes": size, "git_blob": blob}
        return result
    except (KeyError, TypeError):
        raise _Failure("protocol_declarations") from None


def _links(path: Path) -> None:
    for node in (path, *path.parents):
        if node.is_symlink() or (hasattr(node, "is_junction") and node.is_junction()):
            raise _Failure("unsafe_directory")
        try:
            attributes = getattr(node.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        # Path.is_junction is unavailable on Python3.11. All Windows reparse
        # points remain prohibited, including junctions and redirected parents.
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise _Failure("unsafe_directory")


def _directory(directory: Path, *, fresh: bool) -> Path:
    try:
        path = Path(directory).absolute()
        if ".." in path.parts:
            raise _Failure("unsafe_directory")
        _links(path)
        resolved = path.resolve(strict=False)
        allowed = False
        for root in ALLOWED_ROOTS:
            _links(root.absolute())
            if resolved.is_relative_to(root.resolve(strict=False)):
                allowed = True
        if not allowed:
            raise _Failure("unsafe_directory")
        if fresh:
            if path.exists():
                raise _Failure("destination_not_fresh")
            path.mkdir(parents=True)  # Only within checked ignored roots; leaf stays exclusive.
        elif not path.is_dir():
            raise _Failure("directory_unavailable")
        return resolved
    except RuntimeError:
        raise _Failure("unsafe_directory") from None
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, _Failure):
            raise
        raise _Failure("directory_unavailable") from None


def _leaf(directory: Path, basename: str, *, must_exist: bool) -> Path:
    try:
        _links(directory)
        path = directory / basename
        _links(path)
        if path.resolve(strict=False).parent != directory:
            raise _Failure("unsafe_raw_path")
        if must_exist and not path.is_file():
            raise _Failure("raw_unavailable")
        if not must_exist and path.exists():
            raise _Failure("raw_write")
        return path
    except RuntimeError:
        raise _Failure("unsafe_raw_path") from None
    except OSError:
        raise _Failure("raw_unavailable" if must_exist else "raw_write") from None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # There is no useful different redirect in the exact two-URL allowlist.
        # A same-URL redirect would repeat the request; no retry is permitted.
        raise _Failure("redirect_rejected", code if type(code) is int else None)


def _open_source(url: str):
    request = Request(url, headers={"User-Agent": "Demeter frozen public-source preflight"})
    return build_opener(_NoRedirect()).open(request, timeout=30)


def _media(value: Any) -> str:
    if type(value) is not str or _MEDIA_HEADER.fullmatch(value.strip()) is None:
        raise _Failure("content_type")
    media = value.strip().split(";", 1)[0].lower()
    if media not in _MEDIA:
        raise _Failure("content_type")
    return media  # No arbitrary server parameter strings enter receipts/reports.


def _read_limited(response, expected_size: int) -> tuple[bytes, bool]:
    chunks = []
    remaining = expected_size + 1
    while remaining:
        chunk = response.read(remaining)
        if type(chunk) is not bytes or len(chunk) > remaining:
            raise _Failure("response_read")
        if not chunk:
            return b"".join(chunks), True
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks), False  # Extra byte proves oversize; discard the prefix.


def _entry(pin: dict[str, Any]) -> dict[str, Any]:
    return {
        "requested_url": pin["url"],
        "final_url": None,
        "retrieved_utc": None,
        "status": None,
        "content_type": None,
        "cache_filename": pin["cache_filename"],
        "size_bytes": None,
        "sha256": None,
        "git_blob": None,
        "full_bytes": False,
        "bytes_retained": False,
        "raw_write_failure_may_leave_partial_bytes": False,
        "source_identity_passed": False,
        "result": "not_requested",
        "failure_stage": None,
    }


def _envelope(pins: dict[str, dict[str, Any]], validation_only: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "frozen_protocol_sha256_reference": PROTOCOL_SHA256,
        "validation_only": validation_only,
        "distribution": "fetch_only",
        "acquisition_passed": False,
        "failure_stage": None,
        "sources": {role: _entry(pin) for role, pin in pins.items()},
    }


def _result(
    envelope: dict[str, Any], sources: dict[str, bytes] | None, *, saved: bool, replay: bool
) -> dict[str, Any]:
    try:
        implementation_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except Exception:
        implementation_sha256 = None
        envelope = {
            **envelope,
            "acquisition_passed": False,
            "failure_stage": "implementation_provenance",
        }
        sources = None
    return {
        "passed": envelope["acquisition_passed"] is True and sources is not None,
        "sources": sources,
        "receipt_saved": saved,
        "provenance": {
            **envelope,
            "verification_mode": "local_byte_replay" if replay else "fresh_acquisition",
            "interpretation": "synthetic fixture only"
            if envelope["validation_only"]
            else "source bytes only; no clinical interpretation",
            "whole_protocol_validation": "caller responsibility; exact source declarations checked here",
            "implementation_sha256": implementation_sha256,
            "bytes_retained_definition": "complete verified bytes saved; raw-write failure may separately leave an unknown partial file",
        },
    }


def fetch_sources(
    frozen_protocol: dict[str, Any], fresh_destination: Path, *, validation_only: bool = False
) -> dict[str, Any]:
    """Fetch only frozen URLs into a fresh ignored directory; no parser or retry.

    On any failure, sources is None. Successfully saved earlier source bytes stay
    immutable, and a failed acquisition receipt remains in the fresh directory.
    Destination/receipt creation failures cannot promise a persisted receipt.
    """
    empty = _envelope(SOURCE_PINS, validation_only is True)
    try:
        pins = _pins(frozen_protocol, validation_only)
        envelope = _envelope(pins, validation_only)
        directory = _directory(fresh_destination, fresh=True)
        receipt_path = _leaf(directory, RECEIPT_FILENAME, must_exist=False)
        receipt_stream = receipt_path.open("x", encoding="utf-8", newline="\n")
    except Exception as exc:
        stage = str(exc) if isinstance(exc, _Failure) else "receipt_write"
        empty["failure_stage"] = stage if stage in _STAGES else "receipt_write"
        return _result(empty, None, saved=False, replay=False)
    sources: dict[str, bytes] = {}
    try:
        for role, pin in pins.items():
            entry = envelope["sources"][role]
            entry["retrieved_utc"] = _utc()
            entry["result"] = "failed"
            stage = "network_failure"
            try:
                with _open_source(pin["url"]) as response:
                    status = response.status
                    if type(status) is not int or not 100 <= status <= 599:
                        raise _Failure("http_status")
                    entry["status"] = status
                    if status != 200:
                        raise _Failure("http_status")
                    if response.geturl() != pin["url"]:
                        raise _Failure("redirect_rejected")
                    entry["final_url"] = pin["url"]
                    entry["content_type"] = _media(response.headers.get("Content-Type"))
                    stage = "response_read"
                    content, complete = _read_limited(response, pin["tree_size_bytes"])
                    entry.update(
                        size_bytes=len(content),
                        sha256=hashlib.sha256(content).hexdigest(),
                        git_blob=_blob(content),
                        full_bytes=complete,
                    )
                    if not complete or len(content) != pin["tree_size_bytes"]:
                        raise _Failure("source_size")
                    if entry["git_blob"] != pin["git_blob"]:
                        raise _Failure("source_identity")
                stage = "raw_write"
                raw_path = _leaf(directory, pin["cache_filename"], must_exist=False)
                with raw_path.open("xb") as stream:
                    stream.write(content)
                entry.update(bytes_retained=True, source_identity_passed=True, result="verified")
                sources[role] = content
            except HTTPError as exc:
                entry["status"] = (
                    exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
                )
                entry["failure_stage"] = "http_status"
            except (URLError, TimeoutError):
                entry["failure_stage"] = "network_failure"
            except Exception as exc:
                reason = str(exc) if isinstance(exc, _Failure) else stage
                if stage == "raw_write":
                    entry["raw_write_failure_may_leave_partial_bytes"] = True
                if (
                    isinstance(exc, _Failure)
                    and type(exc.status) is int
                    and 100 <= exc.status <= 599
                ):
                    entry["status"] = exc.status
                entry["failure_stage"] = reason if reason in _STAGES else stage
            if entry["result"] != "verified":
                envelope["failure_stage"] = entry["failure_stage"]
                break
        envelope["acquisition_passed"] = len(sources) == len(pins)
        # The reserved exclusive stream cannot become an alias overwrite.
        json.dump(envelope, receipt_stream, indent=2, allow_nan=False)
        receipt_stream.write("\n")
        receipt_stream.flush()
        receipt_stream.close()
    except Exception:
        try:
            receipt_stream.close()
        except Exception:
            pass
        envelope["acquisition_passed"] = False
        envelope["failure_stage"] = "receipt_write"
        return _result(envelope, None, saved=False, replay=False)
    return _result(
        envelope, sources if envelope["acquisition_passed"] else None, saved=True, replay=False
    )


def _unique(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            raise _Failure("receipt_metadata")
        value[key] = child
    return value


def _receipt(
    envelope: Any, pins: dict[str, dict[str, Any]], validation_only: bool
) -> dict[str, Any]:
    if (
        type(envelope) is not dict
        or set(envelope) != set(_envelope(pins, validation_only))
        or type(envelope["schema_version"]) is not int
        or envelope["schema_version"] != 1
        or envelope["frozen_protocol_sha256_reference"] != PROTOCOL_SHA256
        or envelope["validation_only"] is not validation_only
        or envelope["distribution"] != "fetch_only"
        or envelope["acquisition_passed"] is not True
        or envelope["failure_stage"] is not None
        or type(envelope["sources"]) is not dict
        or set(envelope["sources"]) != set(pins)
    ):
        raise _Failure("receipt_metadata")
    safe = _envelope(pins, validation_only)
    for role, pin in pins.items():
        entry = envelope["sources"][role]
        if type(entry) is not dict or set(entry) != set(_entry(pin)):
            raise _Failure("receipt_metadata")
        try:
            timestamp = datetime.fromisoformat(entry["retrieved_utc"])
            if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
                raise _Failure("receipt_metadata")
            if (
                entry["requested_url"] != pin["url"]
                or entry["final_url"] != pin["url"]
                or type(entry["status"]) is not int
                or entry["status"] != 200
                or entry["cache_filename"] != pin["cache_filename"]
                or type(entry["size_bytes"]) is not int
                or entry["size_bytes"] != pin["tree_size_bytes"]
                or entry["git_blob"] != pin["git_blob"]
                or type(entry["sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
                or entry["full_bytes"] is not True
                or entry["bytes_retained"] is not True
                or entry["raw_write_failure_may_leave_partial_bytes"] is not False
                or entry["source_identity_passed"] is not True
                or entry["result"] != "verified"
                or entry["failure_stage"] is not None
                or entry["content_type"] not in _MEDIA
            ):
                raise _Failure("receipt_metadata")
        except (ValueError, TypeError, AttributeError):
            raise _Failure("receipt_metadata") from None
        safe["sources"][role] = {**entry}
    safe["acquisition_passed"] = True
    return safe


def load_sources(
    directory: Path, frozen_protocol: dict[str, Any], *, validation_only: bool = False
) -> dict[str, Any]:
    """Verify historical receipts and both local raw files without parsing rows."""
    envelope = _envelope(SOURCE_PINS, validation_only is True)
    stage = "protocol_declarations"
    try:
        pins = _pins(frozen_protocol, validation_only)
        checked_directory = _directory(directory, fresh=False)
        stage = "receipt_unavailable"
        receipt_path = _leaf(checked_directory, RECEIPT_FILENAME, must_exist=True)
        receipt_bytes = receipt_path.read_bytes()
        stage = "receipt_metadata"
        envelope = _receipt(
            json.loads(receipt_bytes.decode("utf-8"), object_pairs_hook=_unique),
            pins,
            validation_only,
        )
        stage = "raw_unavailable"
        paths = {
            role: _leaf(checked_directory, pin["cache_filename"], must_exist=True)
            for role, pin in pins.items()
        }
        all_paths = (receipt_path, *paths.values())
        for index, left in enumerate(all_paths):
            for right in all_paths[index + 1 :]:
                if left.samefile(right):
                    raise _Failure("raw_alias")
        sources = {}
        for role, path in paths.items():
            if path.stat().st_size != pins[role]["tree_size_bytes"]:
                raise _Failure("source_size")
            with path.open("rb") as stream:
                content, complete = _read_limited(stream, pins[role]["tree_size_bytes"])
            entry = envelope["sources"][role]
            if not complete or len(content) != pins[role]["tree_size_bytes"]:
                raise _Failure("source_size")
            if (
                _blob(content) != pins[role]["git_blob"]
                or hashlib.sha256(content).hexdigest() != entry["sha256"]
            ):
                raise _Failure("source_identity")
            sources[role] = content
        return _result(envelope, sources, saved=True, replay=True)
    except Exception as exc:
        reason = str(exc) if isinstance(exc, _Failure) else stage
        # Never return unvalidated receipt fields or partially verified sources.
        failed = _envelope(SOURCE_PINS, validation_only is True)
        failed["failure_stage"] = reason if reason in _STAGES else stage
        return _result(failed, None, saved=False, replay=True)
