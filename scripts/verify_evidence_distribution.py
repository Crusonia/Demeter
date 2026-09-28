"""Check the built wheel and sdist carry notices and exclude local data caches."""

from __future__ import annotations

import json
import tarfile
import zipfile
from pathlib import Path

from demeter.data.ingest import digest
from demeter.data.packages import verify_packages


def verify_distribution(dist: Path = Path("dist")) -> dict:
    report = verify_packages()
    if not report["passed"]:
        raise ValueError("Repository evidence package audit failed")
    # One build version only: stale artifacts must not make this check ambiguous.
    wheels, sdists = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Expected exactly one wheel and one source distribution")
    forbidden_hashes = {s["sha256"] for s in report["sources"] if s["distribution"] == "fetch_only"}
    expected_bundles = {
        a["path"][4:]: a["sha256"]
        for a in report["artifacts"]
        if a["path"].startswith("src/demeter/data/bundled/")
    }
    expected_notices = {
        f"demeter/data/notices/{name}": digest((Path("data") / name).read_bytes())
        for name in ("rights.json", "evidence-packages.json", "NOTICE.md")
    }
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        for name in (
            "demeter/explorer/static/index.html",
            "demeter/explorer/static/build.json",
            "demeter/analysis/content/charts.md",
        ):
            if name not in names:
                raise ValueError(f"Missing learning interface artifact: {name}")
        if not any(name.startswith("demeter/explorer/static/_next/") for name in names):
            raise ValueError("Missing compiled Next.js assets")
        for name, sha in (expected_bundles | expected_notices).items():
            if name not in names or digest(wheel.read(name)) != sha:
                raise ValueError(f"Missing or altered wheel evidence artifact: {name}")
        for name in names:
            if name.endswith("/"):
                continue
            content = wheel.read(name)
            if digest(content) in forbidden_hashes or "/raw/" in name or "/sources/" in name:
                raise ValueError(f"Raw source entered wheel: {name}")
            if name.startswith("demeter/data/") and not name.endswith(".py"):
                if name not in expected_bundles and name not in expected_notices:
                    raise ValueError(f"Undeclared data file in wheel: {name}")
    with tarfile.open(sdists[0]) as sdist:
        files = {}
        for member in sdist.getmembers():
            if not member.isfile():
                continue
            name = member.name.split("/", 1)[-1]
            if name.startswith(
                (
                    "data/raw/",
                    "data/processed/",
                    "outputs/",
                    "web/node_modules/",
                    "web/.next/",
                    "web/out/",
                )
            ):
                raise ValueError(f"Local cache entered source distribution: {name}")
            content = sdist.extractfile(member).read()
            if digest(content) in forbidden_hashes:
                raise ValueError(f"Fetch-only article entered source distribution: {name}")
            files[name] = digest(content)
        expected = {
            s["path"]: s["sha256"] for s in report["sources"] if s["distribution"] == "archived"
        }
        expected.update({a["path"]: a["sha256"] for a in report["artifacts"]})
        required_paths = {s["manifest"] for s in report["sources"] if s.get("manifest")}
        required_paths.update(report["transform_sha256"])
        required_paths.update({"evidence/parameters.yaml", "data/sources/archive.json", "uv.lock"})
        for name in required_paths:
            expected[name] = digest(Path(name).read_bytes())
        for name in ("rights.json", "evidence-packages.json", "NOTICE.md", "catalog.json"):
            path = Path("data") / name
            expected[path.as_posix()] = digest(path.read_bytes())
        for name, sha in expected.items():
            if files.get(name) != sha:
                raise ValueError(f"Missing or altered source-distribution artifact: {name}")
    return {
        "passed": True,
        "wheel_bundles": len(expected_bundles),
        "wheel_notices": len(expected_notices),
        "archived_sources": sum(s["distribution"] == "archived" for s in report["sources"]),
    }


if __name__ == "__main__":
    print(json.dumps(verify_distribution(), indent=2))
