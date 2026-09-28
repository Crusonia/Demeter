"""Build static Next.js assets once; reusable from the launcher and wheel/sdist hook."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    paths = []
    for directory, subdirs, files in os.walk(root / "web"):
        subdirs[:] = [name for name in subdirs if name not in {"node_modules", ".next", "out"}]
        paths.extend(Path(directory) / name for name in files)
    for path in sorted(paths):
        if path.name == "next-env.d.ts" or path.suffix == ".tsbuildinfo":
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def build(root: Path) -> Path:
    root = root.resolve()
    target = root / "src/demeter/explorer/static"
    marker = target / "build.json"
    digest = fingerprint(root)
    if marker.exists() and (target / "index.html").exists():
        if json.loads(marker.read_bytes()).get("source_sha256") == digest:
            return target
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError(
            "Install Node.js 24 LTS (includes npm), reopen the terminal, then retry. "
            "See docs/EXPLORER.md. Packaged builds already include frontend assets."
        )
    environment = {**os.environ, "NEXT_TELEMETRY_DISABLED": "1"}
    subprocess.run(
        [npm, "ci", "--no-fund", "--no-audit"], cwd=root / "web", env=environment, check=True
    )
    subprocess.run([npm, "run", "build"], cwd=root / "web", env=environment, check=True)
    # The generated directory is fixed beneath the explicit project root. Verify
    # it before replacing stale hashed assets (never remove a computed caller path).
    if target.resolve() != root / "src/demeter/explorer/static" or target.is_symlink():
        raise ValueError("Frontend asset directory must be inside the project")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(root / "web/out", target)
    marker.write_text(json.dumps({"source_sha256": fingerprint(root)}) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    print(build(Path(__file__).resolve().parents[1]))
