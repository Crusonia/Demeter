"""Exercise the HTTP adapter against actual canonical calculations and saved artifacts."""

import hashlib
import json
from pathlib import Path
import time

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from demeter.explorer.experiments import (
    Experiment,
    ParameterEdit,
    compare_payloads,
    reference_scenario,
    registry_for,
    resolve_experiment,
    scenario_catalog,
)
from demeter.explorer.jobs import Jobs, code_fingerprint, read_json, worker, write_json
from demeter.explorer.server import create_app
from demeter.analysis.teaching import guide_for, teaching_content
from demeter.model import simulate
from demeter.schema import Scenario

ROOT = Path.cwd()


@pytest.mark.parametrize("persistent", [False, True])
def test_windows_reader_lock_keeps_receipt_atomic(tmp_path, monkeypatch, persistent):
    import demeter.explorer.jobs as module

    target = tmp_path / "run.json"
    write_json(target, {"status": "running"})
    original_replace = module.os.replace
    attempts = 0

    def replace(source, destination):
        nonlocal attempts
        attempts += 1
        assert read_json(target) == {"status": "running"}
        if persistent or attempts < 3:
            error = PermissionError("Simulated Windows sharing violation")
            error.winerror = 32
            raise error
        original_replace(source, destination)

    monkeypatch.setattr(module.os, "replace", replace)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    if persistent:
        with pytest.raises(PermissionError):
            write_json(target, {"status": "complete"})
        assert read_json(target)["status"] == "running"
    else:
        write_json(target, {"status": "complete"})
        assert read_json(target)["status"] == "complete" and attempts == 3
    assert not list(tmp_path.glob("*.tmp"))


def request_for(key="reduce_upf_30", **changes):
    entry = next(r for r in scenario_catalog(ROOT) if r["id"].endswith("/" + key))
    scenario = entry["scenario"]
    scenario.update(changes)
    return Experiment(catalog_id=entry["id"], scenario=Scenario.model_validate(scenario))


@pytest.fixture
def client(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("local interface")
    app = create_app(
        ROOT, tmp_path / "runs", static, origin="http://127.0.0.1:8000", token="test-token"
    )
    with TestClient(
        app, base_url="http://127.0.0.1:8000", headers={"X-Demeter-Token": "test-token"}
    ) as browser:
        yield browser


@pytest.mark.parametrize(
    "name", ["baseline", "prechronic_reduce_upf_30", "diet_dynamics", "glp1_access"]
)
def test_each_family_resolves_without_changing_canonical_results(name):
    request = request_for(name)
    evidence, meta = resolve_experiment(ROOT, request)
    canonical = simulate(registry_for(ROOT), request.scenario)
    assert simulate(evidence, request.scenario).annual == canonical.annual
    assert meta["base_evidence_sha256"] == meta["resolved_evidence_sha256"]
    assert meta["settings"] == {"draws": 4, "samples": 8, "seed": 42}
    reference = reference_scenario(request.scenario)
    assert reference.glp1 is None and reference.exposures == {"upf": 1.0}
    assert reference.health_structure == request.scenario.health_structure


def test_advanced_edits_preserve_source_and_do_not_silently_shift_distribution():
    source = ROOT / "evidence/parameters.yaml"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    request = request_for(years=2)
    request.overrides = {"beta_upf_progression": ParameterEdit(value=0.5)}
    registry, meta = resolve_experiment(ROOT, request)
    p = registry.parameters["beta_upf_progression"]
    assert p.value == 0.5 and p.status == "synthetic" and p.evidence_grade == "E"
    assert p.uncertainty == registry_for(ROOT).parameters[p.key].uncertainty
    assert meta["base_evidence_sha256"] != meta["resolved_evidence_sha256"]
    assert before == hashlib.sha256(source.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "edits,match",
    [
        ({"beta_upf_progression": {"value": 4}}, "sampling range"),
        ({"beta_upf_progression": {"value": 0.5, "low": 0.2}}, "both bounds"),
        ({"diet_lag_years": {"value": 2, "low": 0, "high": 4}}, "positive"),
        ({"initial_healthy_share": {"value": 0.9}}, "sum to 1"),
        ({"upf_min_multiplier": {"value": 0}}, "only active synthetic"),
        ({"observed_prediabetes_65_plus": {"value": 0.2}}, "only active synthetic"),
        ({"glp1_initiation_rate": {"value": 0.5}}, "only active synthetic"),
    ],
)
def test_invalid_or_inapplicable_overrides_fail(edits, match):
    request = request_for(years=2)
    request.overrides = {key: ParameterEdit(**value) for key, value in edits.items()}
    with pytest.raises(ValueError, match=match):
        resolve_experiment(ROOT, request)


def test_http_boundaries_and_validation(client):
    assert client.get("/api/catalog").status_code == 200
    assert client.get("/api/catalog", headers={"X-Demeter-Token": "wrong"}).status_code == 403
    assert client.get("/api/catalog", headers={"Origin": "https://example.com"}).status_code == 403
    assert client.get("/api/catalog", headers={"Host": "evil.test"}).status_code == 403
    request = request_for(years=2).model_dump()
    assert client.post("/api/validate", json=request).status_code == 200
    request["scenario"]["mode"] = "scientific"
    assert client.post("/api/validate", json=request).status_code == 422
    request["scenario"]["mode"] = "validation"
    request["scenario"]["exposures"]["upf"] = 0.1
    assert client.post("/api/validate", json=request).status_code == 422
    assert client.get("/api/runs/not-a-run").status_code == 422
    assert client.get("/api/runs/" + "0" * 32).status_code == 404


@pytest.mark.parametrize(
    "family,key,nominal,high",
    [
        ("glp1_access", "glp1_response_lag", 0.5, 1.5),
        ("diet_dynamics", "diet_improvement_lag_years", 1.5, 3.0),
    ],
)
def test_interval_endpoints_use_active_module_validators(family, key, nominal, high):
    request = request_for(family)
    request.overrides = {key: ParameterEdit(value=nominal, low=0, high=high)}
    with pytest.raises(ValueError, match="bounds|positive"):
        resolve_experiment(ROOT, request)


@pytest.fixture(scope="module")
def completed(tmp_path_factory):
    destination = tmp_path_factory.mktemp("explorer-jobs")
    jobs = Jobs(ROOT, destination)
    receipt = jobs.start(request_for(years=2))
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        jobs.refresh()
        saved = read_json(jobs.path(receipt["id"]) / "run.json")
        if saved["status"] not in ("queued", "running"):
            break
        time.sleep(0.1)
    jobs.close()
    assert saved["status"] == "complete", saved
    return destination, receipt["id"]


def test_worker_parity_reference_charts_and_saved_metadata(completed):
    destination, key = completed
    path = destination / key
    request = Experiment.model_validate(read_json(path / "request.json"))
    evidence, _ = resolve_experiment(ROOT, request)
    result = read_json(path / "result.json")
    assert (
        result["simulation"]["annual"]
        == simulate(evidence, request.scenario, diagnostics=True).to_dict()["annual"]
    )
    comparison = read_json(path / "comparison.json")
    assert comparison["validation_only"]
    assert comparison["outcomes"][0]["absolute_delta"] == pytest.approx(
        result["simulation"]["annual"][-1]["life_expectancy"]
        - read_json(path / "reference-result.json")["simulation"]["annual"][-1]["life_expectancy"]
    )
    charts = read_json(path / "report/charts.json")["charts"]
    stocks = next(c for c in charts if c["id"] == "stocks")
    assert isinstance(stocks["figure"]["data"][0]["y"], list)
    assert "no births or migration" in stocks["guide"]["mechanism"].lower()
    assert "Why it happens in this model" in (path / "report/index.html").read_text(
        encoding="utf-8"
    )
    assert read_json(path / "run.json")["commentary_sha256"] == teaching_content()[1]


def test_reopen_notes_exports_and_immutable_inputs(completed, tmp_path):
    destination, key = completed
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("test")
    path = destination / key
    before = (path / "request.json").read_bytes()
    app = create_app(ROOT, destination, static, origin="http://127.0.0.1:8000", token="test")
    with TestClient(
        app, base_url="http://127.0.0.1:8000", headers={"X-Demeter-Token": "test"}
    ) as client:
        assert client.get(f"/api/runs/{key}").json()["receipt"]["status"] == "complete"
        assert (
            client.post(f"/api/runs/{key}/notes", json={"text": "Revisit the lag"}).status_code
            == 200
        )
        assert client.get(f"/api/runs/{key}").json()["notes"] == "Revisit the lag"
        for artifact in ("report", "diagnostics", "scenario", "evidence", "request", "comparison"):
            assert client.get(f"/api/runs/{key}/download/{artifact}").status_code == 200
        assert client.get(f"/api/runs/{key}/download/error.log").status_code == 404
        assert client.post(f"/api/runs/{key}/cancel", json={}).status_code == 422
        candidate = request_for(years=3).model_dump()
        candidate["reference_id"] = key
        assert client.post("/api/validate", json=candidate).status_code == 422
    assert (path / "request.json").read_bytes() == before


def test_cancel_busy_and_interrupted_receipts(tmp_path):
    jobs = Jobs(ROOT, tmp_path)
    try:
        receipt = jobs.start(request_for())
        with pytest.raises(RuntimeError, match="already running"):
            jobs.start(request_for())
        cancelled = jobs.cancel(receipt["id"])
        assert cancelled["status"] == "cancelled"
        with pytest.raises(ValueError, match="Another Explorer"):
            Jobs(ROOT, tmp_path)
        saved = jobs.path(receipt["id"]) / "run.json"
        raw = read_json(saved)
        raw["status"] = "running"
        saved.write_text(json.dumps(raw))
    finally:
        jobs.close()
    reopened = Jobs(ROOT, tmp_path)
    try:
        assert reopened.list()[0]["status"] == "interrupted"
    finally:
        reopened.close()


def test_worker_errors_are_not_completed_results(tmp_path):
    path = tmp_path / "run"
    path.mkdir()
    (path / "run.json").write_text('{"status":"queued"}')
    (path / "request.json").write_text('{"invalid":true}')
    worker(str(ROOT), str(path))
    assert read_json(path / "run.json")["status"] == "failed"
    assert (path / "error.log").exists()


def test_teaching_families_and_comparison_guards(completed):
    records, digest = teaching_content()
    assert len(digest) == 64
    for name in (
        "stocks",
        "flows",
        "dependencies",
        "cohort_t2d",
        "uncertainty_life_expectancy",
        "sensitivity",
        "parameter_diet_lag_years",
        "history_test",
        "diet_memory",
        "glp1_flows",
        "lx",
    ):
        assert set(guide_for(name, records)) == {"question", "read", "mechanism", "try", "limit"}
    directory, key = completed
    right = read_json(directory / key / "result.json")
    left = read_json(directory / key / "reference-result.json")
    left["code"] = "other"
    assert right["code"] == code_fingerprint()
    with pytest.raises(ValueError, match="fingerprint"):
        compare_payloads(left, right)


def test_bundled_data_changes_invalidate_the_engine_fingerprint(tmp_path):
    bundle = tmp_path / "data/bundled/baseline.json"
    bundle.parent.mkdir(parents=True)
    bundle.write_text('{"population": 1}')
    before = code_fingerprint(tmp_path)
    bundle.write_text('{"population": 2}')
    assert code_fingerprint(tmp_path) != before


def test_saved_reference_rejects_a_changed_source_registry(completed, monkeypatch):
    import demeter.explorer.experiments as module

    directory, key = completed
    base = registry_for(ROOT).model_dump()
    base["parameters"]["beta_upf_progression"]["value"] = 0.5
    changed = module.EvidenceRegistry.model_validate(base)
    monkeypatch.setattr(module, "registry_for", lambda _: changed)
    request = request_for(years=2)
    request.reference_id = key
    jobs = Jobs(ROOT, directory)
    try:
        with pytest.raises(ValueError, match="different source evidence"):
            jobs.validate(request)
    finally:
        jobs.close()
