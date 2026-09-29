"""One local command owns the static interface, HTTP adapter, and worker lifecycle."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import secrets
import socket
import threading
import time
import webbrowser


def assets(root: Path) -> Path:
    script = root / "scripts/build_explorer.py"
    # Installed wheels use their own compiled assets even when --project points
    # at a full checkout. Editable source launches rebuild that checkout.
    if root.resolve() == Path(__file__).resolve().parents[3] and script.exists():
        spec = importlib.util.spec_from_file_location("explorer_build", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.build(root)
    path = Path(__file__).parent / "static"
    if not (path / "index.html").exists():
        raise ValueError(
            "Frontend assets are missing; run from a source checkout or install a built wheel"
        )
    return path


def launch(root: Path, destination: Path, port: int, open_browser: bool) -> None:
    try:
        import uvicorn
        from demeter.explorer.server import create_app
    except ImportError as exc:
        raise ValueError("Install the interface dependencies with uv sync --extra studio") from exc
    root = root.resolve()
    if not (root / "evidence/parameters.yaml").is_file():
        raise ValueError("Run inside the Demeter source checkout or supply --project PATH")
    static = assets(root)
    os.chdir(root)
    token = secrets.token_urlsafe(32)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))
        sock.listen(128)
        origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
        url = origin + "/#token=" + token
        app = create_app(root, destination.resolve(), static, origin=origin, token=token)
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
        print(
            f"Demeter local learning interface: {url}\nKeep this terminal open. Ctrl+C stops the app.",
            flush=True,
        )
        if open_browser:

            def open_when_ready():
                for _ in range(200):
                    if server.started:
                        webbrowser.open(url)
                        return
                    if server.should_exit:
                        return
                    time.sleep(0.1)

            threading.Thread(target=open_when_ready, daemon=True).start()
        server.run(sockets=[sock])
