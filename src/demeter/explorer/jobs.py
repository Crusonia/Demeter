"""Single cancellable worker, immutable experiment snapshots, recoverable local receipts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import threading
import time
import traceback
from uuid import uuid4

from demeter.explorer.experiments import (
    Experiment,
    compare_payloads,
    reference_scenario,
    registry_for,
    resolve_experiment,
    yaml_text,
)
from demeter.analysis.teaching import guide_for, summary, teaching_content
from demeter.schema import EvidenceRegistry, Scenario

ACTIVE = {"queued", "running"}


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        for attempt in range(20):
            try:
                os.replace(temporary, path)
                break
            except PermissionError as exc:
                # Windows can hold a read handle during a polling request (or
                # antivirus inspection). Keep the old complete JSON until the
                # atomic replacement succeeds; never truncate it in place.
                if getattr(exc, "winerror", None) not in (5, 32, 33) or attempt == 19:
                    raise
                time.sleep(0.05)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def code_fingerprint() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        if "static" not in path.relative_to(root).parts:
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def stage(destination: Path, name: str, **updates) -> None:
    receipt = read_json(destination / "run.json")
    receipt.update(stage=name, **updates)
    write_json(destination / "run.json", receipt)


def render_artifacts(payload: dict, path: Path, records: dict) -> dict:
    from plotly.utils import PlotlyJSONEncoder
    from demeter.analysis.visualization import build_figures, render_report

    figures = build_figures(payload)
    charts = []
    for name, figure in figures.items():
        # Plain arrays rather than Plotly's compact typed-array encoding make Data
        # and CSV views exact, portable and independently inspectable.
        graph = json.loads(json.dumps(figure.to_plotly_json(), cls=PlotlyJSONEncoder))
        charts.append({"id": name, "figure": graph, "guide": guide_for(name, records)})
    render_report(payload, path, teaching_records=records)
    write_json(path / "charts.json", {"charts": charts, "summary": summary(payload)})
    return payload["simulation"]


def worker(root: str, directory: str) -> None:
    from demeter.analysis.observability import observe

    destination = Path(directory)
    try:
        os.chdir(root)
        request = Experiment.model_validate(read_json(destination / "request.json"))
        evidence = EvidenceRegistry.model_validate(read_json(destination / "evidence.json"))
        receipt = read_json(destination / "run.json")
        records = read_json(destination / "teaching.json")["records"]
        settings = receipt["settings"]
        stage(destination, "Calculating reference", status="running")
        if not request.reference_id:
            reference_registry = EvidenceRegistry.model_validate(
                read_json(destination / "reference-evidence.json")
            )
            reference = reference_scenario(request.scenario)
            result = observe(reference_registry, reference, **settings)
            sim = render_artifacts(result, destination / "reference", records)
            write_json(
                destination / "reference-result.json",
                {
                    "scenario": reference.model_dump(),
                    "overrides": {},
                    "code": receipt["code"],
                    "simulation": sim,
                    "label": reference.name,
                },
            )
        stage(destination, "Calculating experiment and uncertainty")
        result = observe(evidence, request.scenario, **settings)
        stage(destination, "Rendering charts and teaching notes")
        sim = render_artifacts(result, destination / "report", records)
        saved = {
            "scenario": request.scenario.model_dump(),
            "overrides": request.model_dump()["overrides"],
            "code": receipt["code"],
            "simulation": sim,
            "label": request.scenario.name,
        }
        write_json(destination / "result.json", saved)
        comparison = compare_payloads(read_json(destination / "reference-result.json"), saved)
        write_json(destination / "comparison.json", comparison)
        stage(destination, "Complete", status="complete", finished_at=now())
    except Exception as exc:
        (destination / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
        stage(destination, "Failed", status="failed", error=str(exc), finished_at=now())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Jobs:
    def __init__(self, root: Path, destination: Path):
        from filelock import FileLock, Timeout

        self.root = root.resolve()
        self.destination = destination.resolve()
        self.destination.mkdir(parents=True, exist_ok=True)
        self.file_lock = FileLock(str(self.destination / ".explorer.lock"))
        try:
            self.file_lock.acquire(timeout=0)
        except Timeout as exc:
            raise ValueError("Another Explorer is using this run directory") from exc
        self.lock = threading.RLock()
        self.process = None
        self.active_id = None
        # Process ownership is exclusive for this run directory. An old in-flight
        # receipt cannot imply success after a shutdown or crash.
        for receipt in self.list():
            if receipt["status"] in ACTIVE:
                stage(
                    self.path(receipt["id"]),
                    "Interrupted by previous shutdown",
                    status="interrupted",
                    finished_at=now(),
                )

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", key):
            raise ValueError("Invalid run identifier")
        path = self.destination / key
        if path.is_symlink() or path.resolve().parent != self.destination:
            raise ValueError("Invalid run directory")
        return path

    def list(self) -> list[dict]:
        output = []
        for path in self.destination.glob("*/run.json"):
            if re.fullmatch(r"[a-f0-9]{32}", path.parent.name) and not path.parent.is_symlink():
                output.append(read_json(path))
        return sorted(output, key=lambda r: r["created_at"], reverse=True)

    def refresh(self) -> None:
        if self.process and not self.process.is_alive():
            self.process.join()
            path = self.path(self.active_id)
            if read_json(path / "run.json")["status"] in ACTIVE:
                stage(path, "Worker stopped unexpectedly", status="failed", finished_at=now())
            self.process.close()
            self.process = None
            self.active_id = None

    def validate(self, request: Experiment) -> tuple[EvidenceRegistry, dict]:
        registry, metadata = resolve_experiment(self.root, request)
        if request.reference_id:
            reference = self.path(request.reference_id)
            if read_json(reference / "run.json")["status"] != "complete":
                raise ValueError("Choose a completed reference run")
            saved = read_json(reference / "result.json")
            from demeter.analysis.experiments import compatible

            compatible(Scenario.model_validate(saved["scenario"]), request.scenario)
            if saved["code"] != code_fingerprint():
                raise ValueError(
                    "Reference was produced by different engine source; run a new reference"
                )
        return registry, metadata

    def start(self, request: Experiment) -> dict:
        with self.lock:
            self.refresh()
            if self.process:
                raise RuntimeError("A calculation is already running. Finish or cancel it first.")
            evidence, metadata = self.validate(request)
            key = uuid4().hex
            path = self.path(key)
            path.mkdir()
            records, content_sha = teaching_content()
            receipt = {
                "id": key,
                "status": "queued",
                "stage": "Queued",
                "created_at": now(),
                "name": request.scenario.name,
                "profile": request.profile,
                "reference_id": request.reference_id,
                "code": code_fingerprint(),
                "commentary_sha256": content_sha,
                "settings": metadata["settings"],
                "catalog": metadata["catalog"],
                "base_evidence_sha256": metadata["base_evidence_sha256"],
                "resolved_evidence_sha256": metadata["resolved_evidence_sha256"],
            }
            from demeter.analysis.historical import provenance

            receipt["provenance"] = provenance()
            write_json(path / "run.json", receipt)
            write_json(path / "request.json", request.model_dump(mode="json"))
            write_json(path / "evidence.json", evidence.model_dump(mode="json"))
            (path / "scenario.yaml").write_text(
                yaml_text(request.scenario.model_dump()), encoding="utf-8"
            )
            write_json(path / "teaching.json", {"records": records, "sha256": content_sha})
            if request.reference_id:
                reference = self.path(request.reference_id)
                write_json(path / "reference-result.json", read_json(reference / "result.json"))
                write_json(
                    path / "reference-charts.json", read_json(reference / "report/charts.json")
                )
            else:
                write_json(
                    path / "reference-evidence.json",
                    registry_for(self.root).model_dump(mode="json"),
                )
            process = multiprocessing.get_context("spawn").Process(
                target=worker, args=(str(self.root), str(path)), daemon=True
            )
            self.active_id = key
            self.process = process
            try:
                process.start()
            except Exception:
                self.process = None
                self.active_id = None
                stage(path, "Worker could not start", status="failed", finished_at=now())
                raise
            return receipt

    def cancel(self, key: str) -> dict:
        with self.lock:
            self.refresh()
            if key != self.active_id or not self.process:
                raise ValueError("Only the active calculation can be cancelled")
            self.process.terminate()
            self.process.join(timeout=10)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
            self.process.close()
            self.process = None
            self.active_id = None
            path = self.path(key)
            # The child may have committed its completed receipt just before the
            # cancellation/shutdown request. Preserve that terminal result.
            if read_json(path / "run.json")["status"] in ACTIVE:
                stage(path, "Cancelled", status="cancelled", finished_at=now())
            return read_json(path / "run.json")

    def close(self) -> None:
        with self.lock:
            self.refresh()
            if self.active_id:
                self.cancel(self.active_id)
            self.file_lock.release()
