"""Rebuild the small offline source bundle from pinned government artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook

BUNDLE = Path(__file__).parent / "bundled"
SOURCES = {
    f"nchs_{year}_{sex}.xlsx": {
        "url": f"https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/NVSR/{folder}/{case}{i:02}.xlsx",
        "publisher": "CDC/NCHS",
        "title": f"United States Life Tables, {year}, Table {i}",
        "vintage": str(year),
        "sex": sex,
        "year": year,
    }
    for year, folder, case in [
        (2022, "74-02", "table"),
        (2023, "74-06", "Table"),
        (2024, "75-05", "Table"),
    ]
    for i, sex in [(1, "all"), (2, "male"), (3, "female")]
}
SOURCES["census_2025.csv"] = {
    "url": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/national/asrh/nc-est2025-agesex-res.csv",
    "publisher": "U.S. Census Bureau",
    "title": "Resident population by single year of age and sex, Vintage 2025",
    "vintage": "2025 (using 2022–2024 estimates)",
}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def transform_life_table(path: Path) -> list[dict]:
    rows = []
    for cells in load_workbook(path, data_only=True, read_only=True).active.values:
        label = str(cells[0])
        match = re.match(r"^(\d+)(?:[-–]| and (?:over|older))", label)
        if match is None:
            continue
        age = int(match.group(1))
        q, lx, dx, person_years, total_years, ex = map(float, cells[1:7])
        rows.append(
            {
                "age": age,
                "qx": q,
                "lx": lx,
                "dx": dx,
                "Lx": person_years,
                "Tx": total_years,
                "ex": ex,
                "ax": (person_years - lx + dx) / dx if age < 100 else None,
            }
        )
    if [r["age"] for r in rows] != list(range(101)):
        raise ValueError(f"{path}: expected single ages 0–99 and open 100+ group")
    return rows


def rebuild(raw: Path, destination: Path = BUNDLE) -> dict:
    """Refuse changed source bytes once a manifest has been pinned."""
    raw.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    records, mortality = {}, {}
    for name, metadata in SOURCES.items():
        path = raw / name
        if not path.exists():
            request = urllib.request.Request(
                metadata["url"], headers={"User-Agent": "Demeter/0.1 public data"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                content = response.read()
            expected = previous.get("sources", {}).get(name, {}).get("sha256")
            if expected and digest(content) != expected:
                raise ValueError(f"Source changed: {name}; review and version the source manifest")
            path.write_bytes(content)
        sha = digest(path.read_bytes())
        old = previous.get("sources", {}).get(name, {})
        if old.get("sha256", sha) != sha:
            raise ValueError(f"Raw source checksum mismatch: {name}")
        records[name] = dict(
            metadata,
            sha256=sha,
            retrieved_at=old.get("retrieved_at", datetime.now(timezone.utc).isoformat()),
        )
        if name.endswith(".xlsx"):
            mortality.setdefault(str(metadata["year"]), {})[metadata["sex"]] = transform_life_table(
                path
            )
    population = {
        str(year): {sex: [0] * 101 for sex in ("all", "male", "female")}
        for year in (2022, 2023, 2024)
    }
    for row in csv.DictReader((raw / "census_2025.csv").open()):
        age = int(row["AGE"])
        if age <= 100:
            sex = {"0": "all", "1": "male", "2": "female"}[row["SEX"]]
            for year in population:
                population[year][sex][age] = int(row[f"POPESTIMATE{year}"])
    bundle = {"mortality": mortality, "population": population}
    content = (json.dumps(bundle, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (destination / "us_baseline.json").write_bytes(content)
    manifest = {
        "schema_version": 1,
        "sources": records,
        "bundle_sha256": digest(content),
        "transform": "demeter.data.ingest.rebuild",
        "license": "U.S. federal government data",
        "output_schema": "mortality[year][sex][age]: qx,lx,dx,Lx,Tx,ex,ax; population[year][sex][age]: people",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    rebuild(Path("data/raw"))
