"""Synthetic source-integrity tests: no real participant rows are inspected."""

import json
import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from demeter.data import nhanes_current_store as intake


def component(name, keys=(1, 2)):
    result = pd.DataFrame({"SEQN": list(keys)})
    for field in intake.COLUMNS[name]:
        result[field] = 1.0
    if name == "DEMO_L.xpt":
        result.SDDSRVYR = 12
        result.RIDSTATR = 2
    return result


def test_selects_only_approved_fields_and_keeps_lab_missingness(monkeypatch):
    frame = component("GHB_L.xpt")
    frame["UNAPPROVED_FREE_TEXT"] = "private synthetic text"
    frame.loc[1, "LBXGH"] = np.nan
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: frame)
    result = intake.read_xpt(Path("synthetic.xpt"), intake.COLUMNS["GHB_L.xpt"])
    assert result.columns.tolist() == ["SEQN", "LBXGH", "WTPH2YR"]
    assert np.isnan(result.loc[1, "LBXGH"])


@pytest.mark.parametrize(
    "keys",
    [
        (1, 1),
        (1, np.nan),
        (1, 1.5),
        (1, np.inf),
        (0, 1),
        (-1, 1),
        (1, 2**53),
        ("1", "2"),
        (True, False),
        (1 + 0j, 2 + 0j),
    ],
)
def test_invalid_linkage_keys_are_rejected_without_values(monkeypatch, keys):
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: component("DIQ_L.xpt", keys))
    with pytest.raises(ValueError) as error:
        intake.read_xpt(Path("secret-participant-path.xpt"), intake.COLUMNS["DIQ_L.xpt"])
    assert str(error.value) == "NHANES linkage keys must be unique positive exact integers"
    assert "secret" not in str(error.value)


def test_zero_decoding_correction_does_not_round_nearby_values(monkeypatch):
    frame = component("GLU_L.xpt")
    frame.WTSAF2YR = [float.fromhex("0x1p-260"), float.fromhex("0x1.0000000000001p-260")]
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: frame)
    result = intake.read_xpt(Path("synthetic.xpt"), intake.COLUMNS["GLU_L.xpt"])
    assert result.WTSAF2YR.iloc[0] == 0.0
    assert result.WTSAF2YR.iloc[1] == frame.WTSAF2YR.iloc[1]


@pytest.mark.parametrize("name", list(intake.COLUMNS))
def test_physical_old_weight_refused_before_column_selection(monkeypatch, name):
    frame = component(name)
    frame["WTSAFPRP"] = 0.0
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: frame)
    with pytest.raises(ValueError, match="pooled historical weight"):
        intake.read_xpt(Path("synthetic.xpt"), intake.COLUMNS[name])


@pytest.mark.parametrize("failure", ["missing", "duplicate", "parser"])
def test_component_schema_and_parser_failures_are_sanitized(monkeypatch, failure):
    frame = component("DIQ_L.xpt")
    if failure == "missing":
        frame = frame.drop(columns="DIQ010")
    if failure == "duplicate":
        frame = pd.concat([frame, frame.DIQ010], axis=1)

    def parser(*a, **kw):
        if failure == "parser":
            raise RuntimeError("private synthetic assay and path")
        return frame

    monkeypatch.setattr(pd, "read_sas", parser)
    with pytest.raises(ValueError) as error:
        intake.read_xpt(Path("private-path.xpt"), intake.COLUMNS["DIQ_L.xpt"])
    assert "private" not in str(error.value)


def test_join_retains_demographic_order_and_unavailable_components():
    tables = {name: component(name) for name in intake.COLUMNS}
    tables["GHB_L.xpt"] = component("GHB_L.xpt", (2,))
    result = intake._join(tables)
    assert result.SEQN.tolist() == [1, 2]
    assert pd.isna(result.loc[0, "LBXGH"])
    assert result.loc[1, "LBXGH"] == 1.0


@pytest.mark.parametrize("field,value", [("SDDSRVYR", 11), ("RIDSTATR", 3)])
def test_wrong_cycle_or_interview_status_fails(field, value):
    tables = {name: component(name) for name in intake.COLUMNS}
    tables["DEMO_L.xpt"].loc[0, field] = value
    with pytest.raises(ValueError, match="incompatible cycle"):
        intake._join(tables)


def test_orphan_component_keys_cannot_expand_the_population():
    tables = {name: component(name) for name in intake.COLUMNS}
    tables["GLU_L.xpt"] = component("GLU_L.xpt", (3,))
    with pytest.raises(ValueError, match="orphan"):
        intake._join(tables)


@pytest.mark.parametrize("payload", [b"[]", b"null", b"1", b'"text"', b"{} bad", b"\xff"])
def test_json_schema_and_encoding_are_rejected(payload):
    with pytest.raises(ValueError):
        intake._json(payload)


def test_duplicate_json_keys_are_rejected_recursively():
    with pytest.raises(ValueError, match="Duplicate"):
        intake._json(b'{"sources":{"DEMO_L.xpt":{"sha256":"one","sha256":"two"}}}')
    assert intake._json(json.dumps({"schema_version": 1}).encode()) == {"schema_version": 1}


@pytest.mark.parametrize("value", [None, 1, "private text", "2026-10-02T12:00:00"])
def test_receipt_timestamps_require_timezone_and_do_not_echo_input(value):
    with pytest.raises(ValueError) as error:
        intake._timestamp(value)
    assert "private" not in str(error.value)


@pytest.fixture
def synthetic_store(tmp_path, monkeypatch):
    original_dir = tmp_path / "original"
    original_dir.mkdir()
    blobs = {name: intake.XPORT_HEADER + name.encode() for name in intake.COLUMNS}
    original = {
        "url": intake.PUBLIC_BASE + "DEMO_L.xpt",
        "retrieved_at": "2026-09-28T01:20:58+00:00",
        "sha256": intake.digest(blobs["DEMO_L.xpt"]),
        "bytes": len(blobs["DEMO_L.xpt"]),
    }
    original_bytes = json.dumps({"sources": {"DEMO_L.xpt": original}}).encode()
    (original_dir / "manifest.json").write_bytes(original_bytes)
    (original_dir / "DEMO_L.xpt").write_bytes(blobs["DEMO_L.xpt"])
    protocol_path = tmp_path / "protocol.json"
    protocol = {
        "schema_version": 1,
        "kind": "nhanes_2021_2023_intake_protocol",
        "model_role": "benchmark_only",
        "source_store": intake.STORE.as_posix(),
        "created_at": "2026-10-02T10:00:00+00:00",
        "use_terms_url": intake.USE_TERMS,
        "source_urls": {n: intake.PUBLIC_BASE + n for n in intake.COLUMNS},
        "assay_method_sources": {
            n: intake.PUBLIC_BASE + n.replace(".xpt", ".htm") for n in intake.COLUMNS
        },
        "required_columns": {n: ["SEQN", *c] for n, c in intake.COLUMNS.items()},
        "existing_artifact_sha256": {
            (original_dir / "manifest.json").as_posix(): intake.digest(original_bytes),
            (original_dir / "DEMO_L.xpt").as_posix(): intake.digest(blobs["DEMO_L.xpt"]),
        },
        "demographics_reuse": {
            "path": (original_dir / "DEMO_L.xpt").as_posix(),
            "source_manifest": (original_dir / "manifest.json").as_posix(),
            "sha256": original["sha256"],
            "original_retrieved_at": original["retrieved_at"],
            "reuse_is_new_role_not_new_acquisition": True,
        },
        **{
            k: False
            for k in [
                "direct_initialization_allowed",
                "clinical_fit_allowed",
                "engine_activation_allowed",
                "scientific_release_ready",
                "sampling_distribution_assumed",
            ]
        },
    }
    protocol_bytes = json.dumps(protocol).encode()
    protocol_path.write_bytes(protocol_bytes)
    monkeypatch.setattr(intake, "PROTOCOL_PATH", protocol_path)
    monkeypatch.setattr(intake, "PROTOCOL_SHA256", intake.digest(protocol_bytes))
    sources = {}
    for name, content in blobs.items():
        row = {
            "url": protocol["source_urls"][name],
            "codebook_url": protocol["assay_method_sources"][name],
            "use_terms": intake.USE_TERMS,
            "format": "SAS XPORT",
            "model_role": "benchmark_only",
            "publisher": "CDC/NCHS",
            "vintage": "August 2021-August 2023",
            "bytes": len(content),
            "sha256": intake.digest(content),
            "acquisition_kind": "download",
            "retrieved_at": "2026-10-02T11:00:00+00:00",
        }
        if name == "DEMO_L.xpt":
            row.update(
                acquisition_kind="reuse",
                retrieved_at=original["retrieved_at"],
                reused_at="2026-10-02T11:00:00+00:00",
                original_acquisition={
                    "source_store": original_dir.as_posix(),
                    "source_manifest_sha256": intake.digest(original_bytes),
                    **original,
                },
            )
        sources[name] = row
    manifest = {
        "schema_version": 1,
        "protocol_path": protocol_path.as_posix(),
        "protocol_sha256": intake.PROTOCOL_SHA256,
        "source_store": intake.STORE.as_posix(),
        "participant_records_parsed": False,
        "acquisition_started_at": "2026-10-02T10:30:00+00:00",
        "acquisition_finished_at": "2026-10-02T12:00:00+00:00",
        "sources": sources,
    }
    store = tmp_path / "store"
    store.mkdir()
    for name, blob in blobs.items():
        (store / name).write_bytes(blob)
    (store / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def parser(stream, *a, **kw):
        name = stream.getvalue()[len(intake.XPORT_HEADER) :].decode()
        return component(name)

    monkeypatch.setattr(pd, "read_sas", parser)
    return store, manifest, protocol, original_dir, blobs


def save_manifest(store, manifest):
    (store / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_verified_store_is_offline_and_has_only_selected_fields(synthetic_store, monkeypatch):
    store, manifest, *_ = synthetic_store
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: pytest.fail("network attempted"))
    frame, receipt = intake.read_store(store)
    assert receipt == manifest
    assert frame.SEQN.tolist() == [1, 2]
    assert set(frame.columns) == {"SEQN", *(f for cols in intake.COLUMNS.values() for f in cols)}


@pytest.mark.parametrize("name", list(intake.COLUMNS))
def test_every_component_verified_before_any_parser(synthetic_store, monkeypatch, name):
    store, *_ = synthetic_store
    (store / name).write_bytes(b"corrupt private synthetic content")
    monkeypatch.setattr(
        pd, "read_sas", lambda *a, **kw: pytest.fail("parsed before all byte checks")
    )
    with pytest.raises(ValueError, match="checksum or size"):
        intake.read_store(store)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "url",
        "size",
        "terms",
        "cycle",
        "parseflag",
        "naive",
        "early",
        "reuse",
        "original",
    ],
)
def test_manifest_semantics_fail_before_parsing(synthetic_store, monkeypatch, mutation):
    store, manifest, *_ = synthetic_store
    if mutation == "missing":
        manifest["sources"].pop("DIQ_L.xpt")
    if mutation == "extra":
        manifest["sources"]["UNKNOWN.xpt"] = {}
    if mutation == "url":
        manifest["sources"]["GLU_L.xpt"]["url"] = "https://example.com/private"
    if mutation == "size":
        manifest["sources"]["GLU_L.xpt"]["bytes"] += 1
    if mutation == "terms":
        manifest["sources"]["GLU_L.xpt"]["use_terms"] = "unverified"
    if mutation == "cycle":
        manifest["source_store"] = "data/sources/nhanes/2017-2020"
    if mutation == "parseflag":
        manifest["participant_records_parsed"] = 0
    if mutation == "naive":
        manifest["sources"]["DIQ_L.xpt"]["retrieved_at"] = "2026-10-02T11:00:00"
    if mutation == "early":
        manifest["acquisition_started_at"] = "2026-09-01T10:00:00+00:00"
    if mutation == "reuse":
        manifest["sources"]["DEMO_L.xpt"]["acquisition_kind"] = "download"
    if mutation == "original":
        manifest["sources"]["DEMO_L.xpt"]["original_acquisition"]["retrieved_at"] = (
            "2026-10-02T11:00:00+00:00"
        )
    save_manifest(store, manifest)
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed invalid manifest"))
    with pytest.raises(ValueError):
        intake.read_store(store)


def test_protocol_and_old_artifact_corruption_fail_before_new_parsing(synthetic_store, monkeypatch):
    store, _, _, original_dir, _ = synthetic_store
    monkeypatch.setattr(
        pd, "read_sas", lambda *a, **kw: pytest.fail("parsed with broken preservation")
    )
    (original_dir / "manifest.json").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Preserved"):
        intake.read_store(store)
    intake.PROTOCOL_PATH.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="protocol checksum"):
        intake.read_store(store)


def test_duplicate_receipt_keys_cannot_be_last_value_wins(synthetic_store, monkeypatch):
    store, *_ = synthetic_store
    (store / "manifest.json").write_bytes(b'{"sources":{},"sources":{}}')
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed duplicate JSON"))
    with pytest.raises(ValueError, match="Duplicate"):
        intake.read_store(store)


def fetch_module():
    spec = importlib.util.spec_from_file_location(
        "synthetic_nhanes_fetch", Path("scripts/fetch_nhanes_current.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fetch_refuses_existing_destination_before_network(synthetic_store, monkeypatch):
    store, _, _, original_dir, _ = synthetic_store
    fetch = fetch_module()
    monkeypatch.setattr(fetch, "_committed_protocol", lambda: "a" * 40)
    monkeypatch.setattr(
        fetch, "_download", lambda *a: pytest.fail("overwriting acquisition attempted")
    )
    with pytest.raises(ValueError, match="overwrite refused"):
        fetch.fetch(store, original_dir)


def test_fetch_missing_commit_guard_prevents_all_downloads(synthetic_store, monkeypatch, tmp_path):
    _, _, _, original_dir, _ = synthetic_store
    fetch = fetch_module()

    def missing_commit():
        raise ValueError("committed protocol missing")

    monkeypatch.setattr(fetch, "_committed_protocol", missing_commit)
    monkeypatch.setattr(fetch, "_download", lambda *a: pytest.fail("download before commit"))
    with pytest.raises(ValueError, match="committed"):
        fetch.fetch(tmp_path / "new", original_dir)
    assert not (tmp_path / "new").exists()


def test_synthetic_fetch_reuses_demographics_and_writes_receipt_last(
    synthetic_store, monkeypatch, tmp_path
):
    _, _, _, original_dir, blobs = synthetic_store
    fetch = fetch_module()
    destination = tmp_path / "new"
    monkeypatch.setattr(fetch, "DEMO_STORE", original_dir)
    monkeypatch.setattr(fetch, "_committed_protocol", lambda: "a" * 40)
    monkeypatch.setattr(fetch, "_now", lambda: "2026-10-02T11:00:00+00:00")
    downloaded = []

    def download(name):
        assert not (destination / "manifest.json").exists()
        assert name != "DEMO_L.xpt"
        downloaded.append(name)
        return blobs[name]

    monkeypatch.setattr(fetch, "_download", download)
    manifest = fetch.fetch(destination, original_dir)
    assert downloaded == ["DIQ_L.xpt", "GHB_L.xpt", "GLU_L.xpt"]
    assert manifest["sources"]["DEMO_L.xpt"]["retrieved_at"] == "2026-09-28T01:20:58+00:00"
    assert manifest["sources"]["DEMO_L.xpt"]["reused_at"] == "2026-10-02T11:00:00+00:00"
    assert manifest["participant_records_parsed"] is False
    frame, _ = intake.read_store(destination)
    assert len(frame) == 2


def test_download_challenge_and_oversized_content_fail_without_source_text(monkeypatch):
    fetch = fetch_module()

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def geturl(self):
            return intake.PUBLIC_BASE + "DIQ_L.xpt"

        def read(self, size):
            return b"<html>private challenge</html>"

    monkeypatch.setattr(fetch, "urlopen", lambda *a, **kw: Response())
    with pytest.raises(ValueError, match="bounded XPORT") as error:
        fetch._download("DIQ_L.xpt")
    assert "private" not in str(error.value)
    monkeypatch.setattr(fetch, "MAX_DOWNLOAD_BYTES", 1)
    Response.read = lambda self, size: intake.XPORT_HEADER
    with pytest.raises(ValueError, match="bounded XPORT"):
        fetch._download("DIQ_L.xpt")


def test_parser_consumes_verified_snapshots_even_if_source_paths_change(
    synthetic_store, monkeypatch
):
    store, _, _, _, blobs = synthetic_store
    seen = []

    def parser(stream, *a, **kw):
        content = stream.getvalue()
        name = content[len(intake.XPORT_HEADER) :].decode()
        assert content == blobs[name]
        seen.append(name)
        if name == "DEMO_L.xpt":
            for filename in intake.COLUMNS:
                (store / filename).write_bytes(b"mutated unverified synthetic bytes")
        return component(name)

    monkeypatch.setattr(pd, "read_sas", parser)
    frame, _ = intake.read_store(store)
    assert len(frame) == 2
    assert seen == list(intake.COLUMNS)


@pytest.fixture
def registered_synthetic_store(synthetic_store, monkeypatch, tmp_path):
    store, manifest, protocol, *_ = synthetic_store
    preserved = {"historical_synthetic": {"status": "synthetic"}}
    parameters = {
        "original_a": {"value": 1, "status": "synthetic"},
        "original_b": {"value": 2, "status": "synthetic"},
    }
    sources = {
        "original_a": {"citation": "Synthetic fixture A"},
        "original_b": {"citation": "Synthetic fixture B"},
    }
    calculation_path = tmp_path / "implementation-calculation.py"
    calculation_path.write_bytes(b"# synthetic implementation\n")
    implementation_paths = [calculation_path.as_posix(), Path(intake.__file__).as_posix()]
    monkeypatch.setattr(intake, "IMPLEMENTATIONS", tuple(implementation_paths))
    spec = {
        "model_role": "benchmark_only",
        "protocol_path": intake.PROTOCOL_PATH.as_posix(),
        "protocol_sha256": intake.PROTOCOL_SHA256,
        **{
            k: False
            for k in [
                "direct_initialization_allowed",
                "clinical_fit_allowed",
                "engine_activation_allowed",
                "sampling_distribution_assumed",
                "scientific_release_ready",
            ]
        },
    }
    protocol["definition_fields"] = {k: v for k, v in spec.items() if k != "protocol_sha256"}
    protocol["existing_parameters_sha256"] = intake.digest(intake.encoded(parameters))
    protocol["existing_sources_sha256"] = intake.digest(intake.encoded(sources))
    protocol["existing_definition_sha256"] = {
        n: intake.digest(intake.encoded(v)) for n, v in preserved.items()
    }
    protocol["used_source"] = True
    protocol["chronology"] = "Synthetic software fixture, no empirical appraisal."
    spec.update(
        source_manifest_sha256=intake.digest((store / "manifest.json").read_bytes()),
        source_sha256={n: r["sha256"] for n, r in manifest["sources"].items()},
        implementation_sha256={
            n: intake.digest(Path(n).read_bytes()) for n in implementation_paths
        },
        preserved_parameter_keys=sorted(parameters),
        preserved_source_keys=sorted(sources),
    )
    values = {
        "datasets": {**preserved, intake.DATASET: spec},
        "parameters": parameters,
        "sources": sources,
    }
    registry = SimpleNamespace(content_hash="synthetic-registry", model_dump=lambda **kw: values)
    monkeypatch.setattr(intake, "verify_protocol", lambda: protocol)
    called = []

    def assess(frame, registry):
        called.append(True)
        return {
            "kind": intake.DATASET,
            "synthetic_fixture_n": len(frame),
            "scientific_release_ready": False,
            "direct_initialization_allowed": False,
            "clinical_fit_allowed": False,
            "engine_activation_allowed": False,
        }

    monkeypatch.setitem(
        sys.modules,
        "demeter.data.nhanes_current",
        SimpleNamespace(assess=assess, __file__=calculation_path.as_posix()),
    )
    return store, registry, values, protocol, called


def test_report_checks_registered_pins_before_aggregate_assessment(registered_synthetic_store):
    store, registry, _, protocol, called = registered_synthetic_store
    result = intake.report(registry, store)
    assert called == [True]
    assert result["source_audit_passed"] is True
    assert result["provenance"]["protocol_sha256"] == intake.PROTOCOL_SHA256
    assert result["provenance"]["used_source"] is True
    assert result["provenance"]["chronology"] == protocol["chronology"]
    assert result["scientific_release_ready"] is False
    assert "SEQN" not in json.dumps(result)
    for name, row in result["provenance"]["loaded_implementation"].items():
        assert row["admitted_source_path"] == name
        assert row["loaded_file_verified"] is True
        assert row["sha256"] == result["provenance"]["implementation_sha256"][name]


@pytest.mark.parametrize(
    "mutation",
    [
        "manifest",
        "rawpin",
        "implementation",
        "protocol",
        "gate",
        "old_dataset",
        "old_parameter",
        "old_source",
        "deleted_parameter",
        "deleted_source",
        "release_gate",
        "deleted_dataset",
    ],
)
def test_registered_drift_refused_before_parsing_or_math(
    registered_synthetic_store, monkeypatch, mutation
):
    store, registry, values, _, called = registered_synthetic_store
    spec = values["datasets"][intake.DATASET]
    if mutation == "manifest":
        spec["source_manifest_sha256"] = "0" * 64
    if mutation == "rawpin":
        spec["source_sha256"]["DIQ_L.xpt"] = "0" * 64
    if mutation == "implementation":
        spec["implementation_sha256"][intake.IMPLEMENTATIONS[0]] = "0" * 64
    if mutation == "protocol":
        spec["protocol_sha256"] = "0" * 64
    if mutation == "gate":
        spec["clinical_fit_allowed"] = 0
    if mutation == "old_dataset":
        values["datasets"]["historical_synthetic"]["status"] = "observed"
    if mutation == "old_parameter":
        values["parameters"]["original_a"]["value"] = 3
    if mutation == "old_source":
        values["sources"]["original_a"]["citation"] = "Changed fixture"
    if mutation == "deleted_parameter":
        del values["parameters"]["original_a"]
    if mutation == "deleted_source":
        del values["sources"]["original_a"]
    if mutation == "release_gate":
        spec["scientific_release_ready"] = 0
    if mutation == "deleted_dataset":
        del values["datasets"]["historical_synthetic"]
    monkeypatch.setattr(
        pd, "read_sas", lambda *a, **kw: pytest.fail("parsed before admission checks")
    )
    with pytest.raises(ValueError):
        intake.report(registry, store)
    assert called == []


def test_unrelated_evidence_additions_preserve_admission(registered_synthetic_store):
    store, registry, values, _, called = registered_synthetic_store
    values["parameters"]["new_unrelated"] = {"value": 99, "status": "synthetic"}
    values["sources"]["new_unrelated"] = {"citation": "Additional synthetic source"}
    values["datasets"]["new_unrelated"] = {"model_role": "benchmark_only"}
    result = intake.report(registry, store)
    assert called == [True]
    assert result["source_audit_passed"] is True


@pytest.mark.parametrize("scope_key", ["preserved_parameter_keys", "preserved_source_keys"])
@pytest.mark.parametrize(
    "scope",
    [
        None,
        "original_a",
        ("original_a", "original_b"),
        ["original_b", "original_a"],
        ["original_a", "original_a", "original_b"],
        ["original_a", 1],
        ["", "original_a", "original_b"],
        [],
        ["original_a"],
        ["original_a", "replacement"],
    ],
)
def test_invalid_or_incomplete_preservation_scope_refused_before_parsing(
    registered_synthetic_store, monkeypatch, scope_key, scope
):
    store, registry, values, _, called = registered_synthetic_store
    values["datasets"][intake.DATASET][scope_key] = scope
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed invalid scope"))
    with pytest.raises(ValueError, match="preserved evidence"):
        intake.report(registry, store)
    assert called == []


@pytest.mark.parametrize("group", ["parameters", "sources"])
def test_replacement_with_identical_value_still_changes_preserved_identity(
    registered_synthetic_store, monkeypatch, group
):
    store, registry, values, _, called = registered_synthetic_store
    values[group]["replacement"] = values[group].pop("original_a")
    scope_key = "preserved_parameter_keys" if group == "parameters" else "preserved_source_keys"
    values["datasets"][intake.DATASET][scope_key] = ["original_b", "replacement"]
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed replaced identity"))
    with pytest.raises(ValueError, match="changed preserved evidence records"):
        intake.report(registry, store)
    assert called == []


@pytest.mark.parametrize("failure", ["different_bytes", "absent_origin", "unreadable_origin"])
def test_loaded_calculation_must_match_admission_before_parsing(
    registered_synthetic_store, monkeypatch, tmp_path, failure
):
    store, registry, _, _, called = registered_synthetic_store
    module = sys.modules["demeter.data.nhanes_current"]
    alternate = tmp_path / "alternate.py"
    if failure == "different_bytes":
        alternate.write_bytes(b"# other editable checkout\n")
    module.__file__ = None if failure == "absent_origin" else alternate.as_posix()
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed unadmitted code"))
    with pytest.raises(ValueError, match="loaded implementation"):
        intake.report(registry, store)
    assert called == []


def test_equivalent_installed_calculation_bytes_are_verified_and_disclosed(
    registered_synthetic_store, tmp_path
):
    store, registry, values, _, called = registered_synthetic_store
    module = sys.modules["demeter.data.nhanes_current"]
    original = module.__file__
    alternate = tmp_path / "installed-equivalent.py"
    alternate.write_bytes(Path(original).read_bytes())
    module.__file__ = alternate.as_posix()
    result = intake.report(registry, store)
    assert called == [True]
    loaded = result["provenance"]["loaded_implementation"][original]
    assert loaded["admitted_source_path"] == original
    assert loaded["loaded_file_verified"] is True
    assert alternate.as_posix() not in json.dumps(loaded)
    assert loaded["sha256"] == values["datasets"][intake.DATASET]["implementation_sha256"][original]


def test_loaded_preserved_helper_origin_checked_before_parsing(
    registered_synthetic_store, monkeypatch, tmp_path
):
    from demeter.data import partial_observations

    store, registry, _, protocol, called = registered_synthetic_store
    name = "src/demeter/data/partial_observations.py"
    protocol["existing_artifact_sha256"][name] = intake.digest(
        Path(partial_observations.__file__).read_bytes()
    )
    alternate = tmp_path / "unadmitted-helper.py"
    alternate.write_bytes(b"# other helper checkout\n")
    monkeypatch.setattr(partial_observations, "__file__", alternate.as_posix())
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed unadmitted helper"))
    with pytest.raises(ValueError, match="loaded implementation checksum"):
        intake.report(registry, store)
    assert called == []


@pytest.mark.parametrize("scope_key", ["preserved_parameter_keys", "preserved_source_keys"])
def test_absent_preservation_scope_refused_before_parsing(
    registered_synthetic_store, monkeypatch, scope_key
):
    store, registry, values, _, called = registered_synthetic_store
    del values["datasets"][intake.DATASET][scope_key]
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed absent scope"))
    with pytest.raises(ValueError, match="preserved evidence scope"):
        intake.report(registry, store)
    assert called == []


def test_resealed_manifest_cannot_override_registered_admission(
    registered_synthetic_store, monkeypatch
):
    store, registry, _, _, called = registered_synthetic_store
    manifest = json.loads((store / "manifest.json").read_bytes())
    blob = intake.XPORT_HEADER + b"unregistered synthetic DIQ component"
    (store / "DIQ_L.xpt").write_bytes(blob)
    manifest["sources"]["DIQ_L.xpt"].update(sha256=intake.digest(blob), bytes=len(blob))
    save_manifest(store, manifest)
    monkeypatch.setattr(pd, "read_sas", lambda *a, **kw: pytest.fail("parsed resealed source"))
    with pytest.raises(ValueError, match="admitted immutable"):
        intake.report(registry, store)
    assert called == []


@pytest.mark.parametrize(
    "failure", ["download", "partial_write", "manifest", "verification", "publish"]
)
def test_failed_acquisition_preserves_partial_evidence_and_allows_retry(
    synthetic_store, monkeypatch, tmp_path, failure
):
    _, _, _, original_dir, blobs = synthetic_store
    fetch = fetch_module()
    destination = tmp_path / "retry"
    monkeypatch.setattr(fetch, "DEMO_STORE", original_dir)
    monkeypatch.setattr(fetch, "_committed_protocol", lambda: "a" * 40)
    monkeypatch.setattr(fetch, "_now", lambda: "2026-10-02T11:00:00+00:00")
    original_open = Path.open
    original_json = fetch._write_json
    original_verify = intake._manifest
    original_publish = fetch._publish

    def download(name):
        assert not destination.exists()  # No reader can see an unfinished store.
        if failure == "download" and name == "GHB_L.xpt":
            raise ValueError("private download response")
        return blobs[name]

    def write_json(path, value):
        if failure == "manifest" and path.name == "manifest.json":
            raise OSError("synthetic write failure")
        return original_json(path, value)

    def open_file(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        if (
            failure != "partial_write"
            or path.name != "GHB_L.xpt"
            or (args[0] if args else kwargs.get("mode")) != "xb"
        ):
            return stream

        class PartialWrite:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                stream.close()

            def write(self, content):
                stream.write(content[:10])
                raise OSError("synthetic interrupted file write")

        return PartialWrite()

    def verify(*args):
        if failure == "verification":
            raise ValueError("synthetic corrupt byte")
        return original_verify(*args)

    def publish(*args):
        if failure == "publish":
            raise OSError("synthetic publication failure")
        return original_publish(*args)

    monkeypatch.setattr(fetch, "_download", download)
    monkeypatch.setattr(fetch, "_write_json", write_json)
    monkeypatch.setattr(Path, "open", open_file)
    monkeypatch.setattr(intake, "_manifest", verify)
    monkeypatch.setattr(fetch, "_publish", publish)
    with pytest.raises(ValueError, match="partial bytes/receipts retained") as error:
        fetch.fetch(destination, original_dir)
    assert "private download response" not in str(error.value)
    assert not destination.exists()
    attempts = list(tmp_path.glob(".retry.attempt-*"))
    assert len(attempts) == 1
    attempt = attempts[0]
    assert str(attempt) in str(error.value)
    receipt = json.loads((attempt / "failure.json").read_bytes())
    assert receipt["destination_published"] is False
    assert receipt["participant_records_parsed"] is False
    assert (attempt / "source-store/DEMO_L.xpt").read_bytes() == blobs["DEMO_L.xpt"]
    assert (attempt / "source-store/DIQ_L.xpt").read_bytes() == blobs["DIQ_L.xpt"]
    if failure == "partial_write":
        assert (attempt / "source-store/GHB_L.xpt").read_bytes() == blobs["GHB_L.xpt"][:10]
    retained = {p.relative_to(attempt): p.read_bytes() for p in attempt.rglob("*") if p.is_file()}
    monkeypatch.setattr(fetch, "_download", lambda name: blobs[name])
    monkeypatch.setattr(fetch, "_write_json", original_json)
    monkeypatch.setattr(Path, "open", original_open)
    monkeypatch.setattr(intake, "_manifest", original_verify)
    monkeypatch.setattr(fetch, "_publish", original_publish)
    fetch.fetch(destination, original_dir)
    assert destination.is_dir() and (destination / "manifest.json").is_file()
    assert retained == {
        p.relative_to(attempt): p.read_bytes() for p in attempt.rglob("*") if p.is_file()
    }
    assert len(list(tmp_path.glob(".retry.attempt-*"))) == 2


@pytest.mark.parametrize("target_kind", ["empty_directory", "nonempty_directory", "file"])
def test_atomic_publication_refuses_raced_existing_target(tmp_path, target_kind):
    fetch = fetch_module()
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "source").write_bytes(b"synthetic completed bytes")
    target = tmp_path / "target"
    if target_kind == "file":
        target.write_bytes(b"keep")
    else:
        target.mkdir()
        if target_kind == "nonempty_directory":
            (target / "keep").write_bytes(b"keep")
    with pytest.raises(OSError):
        fetch._publish(staging, target)
    assert (staging / "source").read_bytes() == b"synthetic completed bytes"
    if target_kind == "file":
        assert target.read_bytes() == b"keep"
    elif target_kind == "nonempty_directory":
        assert (target / "keep").read_bytes() == b"keep"
    else:
        assert list(target.iterdir()) == []


def test_atomic_publication_moves_complete_directory_on_current_platform(tmp_path):
    fetch = fetch_module()
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "manifest.json").write_bytes(b"synthetic")
    destination = tmp_path / "new"
    fetch._publish(staging, destination)
    assert not staging.exists()
    assert (destination / "manifest.json").read_bytes() == b"synthetic"


@pytest.mark.parametrize(
    "platform,operation,flags", [("linux", "renameat2", 1), ("darwin", "renamex_np", 4)]
)
def test_native_publication_flags_and_errno_are_explicit(monkeypatch, platform, operation, flags):
    fetch = fetch_module()
    calls = []

    class NativeOperation:
        def __call__(self, *args):
            calls.append(args)
            return -1

    native = NativeOperation()
    monkeypatch.setattr(fetch.sys, "platform", platform)
    monkeypatch.setattr(
        fetch.ctypes, "CDLL", lambda *args, **kwargs: SimpleNamespace(**{operation: native})
    )
    monkeypatch.setattr(fetch.ctypes, "get_errno", lambda: 17)
    with pytest.raises(OSError) as error:
        fetch._publish(Path("staging"), Path("destination"))
    assert error.value.errno == 17
    assert calls[0][-1] == flags
    if platform == "linux":
        assert calls[0][0] == calls[0][2] == -100
    assert native.restype is fetch.ctypes.c_int


@pytest.mark.parametrize("platform", ["linux", "darwin", "unsupported"])
def test_missing_exclusive_publication_api_never_falls_back(monkeypatch, platform):
    fetch = fetch_module()
    monkeypatch.setattr(fetch.sys, "platform", platform)
    monkeypatch.setattr(fetch.ctypes, "CDLL", lambda *a, **kw: SimpleNamespace())
    monkeypatch.setattr(fetch.os, "rename", lambda *a: pytest.fail("unsafe rename fallback"))
    with pytest.raises(OSError, match="unavailable"):
        fetch._publish(Path("staging"), Path("destination"))
