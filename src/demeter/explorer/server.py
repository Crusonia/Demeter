"""Loopback-only HTTP adapter for the optional local learning interface."""

from __future__ import annotations

from contextlib import asynccontextmanager
import hmac
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from demeter.explorer.experiments import (
    Experiment,
    editable_parameters,
    registry_for,
    scenario_catalog,
)
from demeter.explorer.jobs import Jobs, read_json, write_json
from demeter.analysis.teaching import teaching_content
from demeter.schema import Scenario, StrictModel
from pydantic import Field


class Notes(StrictModel):
    text: str = Field(max_length=4000)


def create_app(
    root: Path, destination: Path, static: Path, *, origin: str, token: str | None = None
):
    session_token = token or secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        app.state.jobs = Jobs(root, destination)
        try:
            yield
        finally:
            app.state.jobs.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.token = session_token

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.headers.get("host") != origin.split("://", 1)[1]:
            return JSONResponse({"detail": "Invalid local host"}, status_code=403)
        if request.headers.get("origin") not in (None, origin):
            return JSONResponse(
                {"detail": "Only this local interface may access the service"}, status_code=403
            )
        if request.url.path.startswith("/api/") and not hmac.compare_digest(
            request.headers.get("x-demeter-token", ""), session_token
        ):
            return JSONResponse(
                {"detail": "Open the launcher's browser link to connect"}, status_code=403
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        if isinstance(exc, ValidationError):
            details = [
                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()
            ]
        else:
            details = str(exc)
        return JSONResponse({"detail": details}, status_code=422)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Saved artifact not found"}, status_code=404)

    @app.get("/api/catalog")
    def catalog():
        return {
            "scenarios": scenario_catalog(root),
            "teaching": teaching_content()[0],
            "scenario_schema": Scenario.model_json_schema(),
            "validation_only": True,
        }

    @app.post("/api/parameters")
    def parameters(scenario: Scenario):
        registry = registry_for(root)
        return {
            "editable": editable_parameters(registry, scenario),
            "sources": [
                p.model_dump(mode="json") for p in registry.parameters.values() if p.source_url
            ],
            "exposure_bounds": [
                registry.value("upf_min_multiplier"),
                registry.value("upf_max_multiplier"),
            ],
        }

    @app.post("/api/validate")
    def validate(request: Experiment):
        _, metadata = app.state.jobs.validate(request)
        return {"valid": True, **metadata}

    @app.get("/api/runs")
    def runs():
        with app.state.jobs.lock:
            app.state.jobs.refresh()
            return app.state.jobs.list()

    @app.post("/api/runs", status_code=202)
    def start(request: Experiment):
        try:
            return app.state.jobs.start(request)
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/runs/{key}/cancel")
    def cancel(key: str):
        return app.state.jobs.cancel(key)

    @app.get("/api/runs/{key}")
    def result(key: str):
        with app.state.jobs.lock:
            app.state.jobs.refresh()
            path = app.state.jobs.path(key)
            receipt = read_json(path / "run.json")
            request = read_json(path / "request.json")
            output = {"receipt": receipt, "request": request}
            if (path / "notes.json").exists():
                output["notes"] = read_json(path / "notes.json")["text"]
            if receipt["status"] == "complete":
                output.update(read_json(path / "report/charts.json"))
                output["comparison"] = read_json(path / "comparison.json")
                ref = (
                    "reference-charts.json" if request["reference_id"] else "reference/charts.json"
                )
                output["reference"] = read_json(path / ref)
                output["sources"] = read_json(path / "evidence.json")["parameters"]
            return output

    @app.post("/api/runs/{key}/notes")
    def notes(key: str, request: Notes):
        path = app.state.jobs.path(key)
        read_json(path / "run.json")
        # Notes are a separate annotation; original assumptions/results stay frozen.
        write_json(path / "notes.json", request.model_dump())
        return request.model_dump()

    @app.get("/api/runs/{key}/download/{artifact}")
    def download(key: str, artifact: str):
        path = app.state.jobs.path(key)
        receipt = read_json(path / "run.json")
        if receipt["status"] != "complete":
            raise HTTPException(409, "This run has no completed export")
        files = {
            "report": "report/index.html",
            "diagnostics": "report/diagnostics.json",
            "scenario": "scenario.yaml",
            "evidence": "evidence.json",
            "request": "request.json",
            "comparison": "comparison.json",
        }
        if artifact not in files:
            raise HTTPException(404, "Unknown export")
        target = path / files[artifact]
        return FileResponse(target, filename=f"demeter-{key[:8]}-{target.name}")

    @app.get("/plotly.min.js")
    def plotly():
        from plotly.offline import get_plotlyjs

        return Response(get_plotlyjs(), media_type="text/javascript")

    app.mount("/", StaticFiles(directory=static, html=True), name="interface")
    return app
