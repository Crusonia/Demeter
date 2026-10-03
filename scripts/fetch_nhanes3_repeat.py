"""Explicit, immutable native NHANES III acquisition; never decode study records."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/validation/nhanes3-repeat-intake-protocol-v1.json"
PROTOCOL_SHA256 = "1728d637312da8fd4911d8152b15275eb70760e351286a2a898e95453786798f"
PROTOCOL_COMMIT = "1393ba9a0efb96aa5747d97f697d838de32bce1b"
STORE = ROOT / "data/sources/nhanes3/1988-1994-repeat"
MAX_BYTES = 128 * 1024 * 1024
SOURCE_URLS = {
    "LAB": "https://wwwn.cdc.gov/nchs/data/nhanes3/1a/lab.dat",
    "ADULT": "https://wwwn.cdc.gov/nchs/data/nhanes3/1a/adult.dat",
    "LABSE": "https://wwwn.cdc.gov/nchs/data/nhanes3/3a/labse.dat",
}
TERMS = {
    "data_user_agreement": "https://www.cdc.gov/nchs/policy/data-user-agreement.html",
    "agency_materials": "https://www.cdc.gov/other/agencymaterials.html",
}
GATES = (
    "direct_initialization_allowed",
    "clinical_fit_allowed",
    "engine_activation_allowed",
    "sampling_distribution_assumed",
    "scientific_release_ready",
)


class AcquisitionError(ValueError):
    """Sanitized acquisition refusal; no response or participant text."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise AcquisitionError("duplicate protocol JSON key")
        result[key] = value
    return result


def _committed_protocol() -> tuple[dict, str]:
    raw = (ROOT / PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise AcquisitionError("protocol byte identity mismatch")
    try:
        protocol = json.loads(raw, object_pairs_hook=_unique)
        committed = subprocess.run(
            ["git", "show", f"HEAD:{PROTOCOL}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        invocation = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            .stdout.decode("ascii")
            .strip()
        )
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise AcquisitionError("committed protocol prerequisite failed") from exc
    if committed != raw:
        raise AcquisitionError("protocol is not committed at this head")
    if re.fullmatch(r"[0-9a-f]{40}", invocation) is None:
        raise AcquisitionError("invalid invocation commit identity")
    if (
        protocol.get("kind") != "nhanes3_repeat_intake_protocol"
        or protocol.get("model_role") != "benchmark_only"
        or protocol.get("validation_only") is not True
        or protocol.get("scientific_gates") != dict.fromkeys(GATES, False)
        or set(protocol.get("source_urls", {})) != set(SOURCE_URLS)
    ):
        raise AcquisitionError("protocol scope mismatch")
    for role, url in SOURCE_URLS.items():
        item = protocol["source_urls"][role]
        if (
            item.get("url") != url
            or item.get("archive_filename") != f"{role}.DAT"
            or item.get("participant_acquisition_permitted_after_protocol_commit") is not True
        ):
            raise AcquisitionError("protocol component identity mismatch")
    return protocol, invocation


def _write_json(path: Path, value: dict) -> None:
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def _allowed_url(url: str, original: str) -> bool:
    actual, expected = urlsplit(url), urlsplit(original)
    return (
        actual.scheme == "https"
        and actual.hostname == expected.hostname
        and actual.port in (None, 443)
        and actual.path.lower() == expected.path.lower()
        and not actual.username
        and not actual.password
        and not actual.query
        and not actual.fragment
    )


class _ProducerRedirects(HTTPRedirectHandler):
    def __init__(self, original: str):
        self.original = original
        self.chain: list[str] = []
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _allowed_url(newurl, self.original):
            raise AcquisitionError("unapproved redirect refused")
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download(url: str, path: Path) -> dict:
    redirects = _ProducerRedirects(url)
    digest = hashlib.sha256()
    size = 0
    prefix = b""
    started = _now()
    # A failed request still leaves an exclusive, reviewable partial original.
    with path.open("xb") as target:
        with build_opener(redirects).open(url, timeout=60) as response:
            if response.status != 200 or not _allowed_url(response.geturl(), url):
                raise AcquisitionError("unexpected source response")
            headers = response.headers
            if not headers.get("Content-Type") or headers.get_content_type() not in (
                "text/plain",
                "application/octet-stream",
            ):
                raise AcquisitionError("unexpected source media type")
            charset = headers.get_content_charset()
            if charset is not None and charset.lower() not in ("ascii", "us-ascii", "utf-8"):
                raise AcquisitionError("unexpected source character encoding")
            if headers.get("Content-Encoding", "identity").lower() != "identity":
                raise AcquisitionError("encoded source response refused")
            declared = headers.get("Content-Length")
            if declared is not None and (not declared.isdecimal() or int(declared) > MAX_BYTES):
                raise AcquisitionError("source length refused")
            while chunk := response.read(1024 * 1024):
                if size + len(chunk) > MAX_BYTES:
                    raise AcquisitionError("source exceeds acquisition bound")
                target.write(chunk)
                digest.update(chunk)
                size += len(chunk)
                prefix = (prefix + chunk)[:256]
                if any(byte > 127 or byte == 0 for byte in chunk):
                    raise AcquisitionError("unexpected native byte encoding")
                if prefix.lstrip().lower().startswith((b"<!doctype", b"<html", b"<?xml")):
                    raise AcquisitionError("document response refused")
            target.flush()
            os.fsync(target.fileno())
            if size == 0 or (declared is not None and size != int(declared)):
                raise AcquisitionError("incomplete source response")
            return {
                "url": url,
                "resolved_url": response.geturl(),
                "redirect_chain": redirects.chain,
                "retrieval_started_at": started,
                "retrieved_at": _now(),
                "sha256": digest.hexdigest(),
                "size_bytes": size,
                "content_type": headers.get_content_type(),
                "charset": charset,
                "content_encoding": "identity",
                "declared_content_length": declared,
                "original_bytes_preserved": True,
                "participant_records_decoded": False,
            }


def fetch(destination: Path = STORE) -> dict:
    """Reserve a new store exclusively; retain partial stores and attempt receipts."""
    _, invocation_commit = _committed_protocol()  # Before reservation or network.
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(destination):
        raise AcquisitionError("source store already exists; no overwrite or repair")
    attempt_parent = (
        ROOT / "outputs/nhanes3-acquisition"
        if destination.resolve().is_relative_to((ROOT / "data").resolve())
        else destination.parent
    )
    attempt_parent.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix=f".{destination.name}.attempt-", dir=attempt_parent))
    _write_json(
        attempt / "attempt.json",
        {
            "started_at": _now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "protocol_authoring_commit": PROTOCOL_COMMIT,
            "invocation_commit": invocation_commit,
            "terms": TERMS,
            "participant_records_decoded": False,
        },
    )
    reserved = False
    try:
        destination.mkdir()  # Exclusive reservation, not whole-store atomic publication.
        reserved = True
        components = {}
        for role, url in SOURCE_URLS.items():
            receipt = _download(url, destination / f"{role}.DAT")
            receipt["filename"] = f"{role}.DAT"
            receipt["component"] = role
            receipt["bytes"] = receipt["size_bytes"]
            components[f"{role}.DAT"] = receipt
            _write_json(attempt / f"{role}-receipt.json", receipt)
        manifest = {
            "kind": "nhanes3_repeat_native_source_store",
            "schema_version": 1,
            "source_vintage": "NHANES III 1988-1994",
            "created_at": _now(),
            "protocol_path": PROTOCOL,
            "protocol_sha256": PROTOCOL_SHA256,
            "protocol_authoring_commit": PROTOCOL_COMMIT,
            "invocation_commit": invocation_commit,
            "sources": components,
            "terms": TERMS,
            "source_acknowledgement": "CDC/NCHS; originals freely available at official URLs",
            "endorsement": "Use or links do not imply CDC, HHS or U.S. government endorsement",
            "rights_policy": "nhanes3_repeat_public",
            "participant_records_decoded": False,
            "publication": "exclusive directory reservation and original-file writes; manifest last",
        }
        _write_json(destination / "manifest.json", manifest)
        result = {
            "source_store": str(destination),
            "attempt_receipts": str(attempt),
            "component_count": len(components),
            "participant_records_decoded": False,
            "manifest_sha256": hashlib.sha256(
                (destination / "manifest.json").read_bytes()
            ).hexdigest(),
        }
        _write_json(attempt / "complete.json", result)
        return result
    except Exception as exc:
        partial = {}
        for role in SOURCE_URLS:
            path = destination / f"{role}.DAT"
            if reserved and path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                partial[role] = {"sha256": digest.hexdigest(), "size_bytes": path.stat().st_size}
        _write_json(
            attempt / "failure.json",
            {
                "failed_at": _now(),
                "status": "acquisition_failed",
                "partial_originals": partial,
                "participant_records_decoded": False,
                "canonical_manifest_published": reserved
                and (destination / "manifest.json").is_file(),
            },
        )
        raise AcquisitionError(
            f"acquisition refused; originals and receipt retained at {attempt}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="explicitly acquire the three public originals"
    )
    parser.add_argument("--destination", type=Path, default=STORE)
    args = parser.parse_args(argv)
    if not args.download:
        parser.error("--download is required; no source request was made")
    try:
        print(json.dumps(fetch(args.destination), sort_keys=True, indent=2))
    except (AcquisitionError, OSError) as exc:
        # Only controlled local refusal messages; never print network response text.
        message = (
            str(exc)
            if isinstance(exc, AcquisitionError)
            else "local acquisition prerequisite failed"
        )
        print(message)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
