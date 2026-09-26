"""Pinned historical observations, with definitions kept separate from model states."""

from __future__ import annotations

import csv
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from demeter.data.ingest import BUNDLE, digest

NHIS_QUERY = urllib.parse.urlencode(
    {
        "$where": "indicator='Diagnosed Diabetes' AND unit='Percentage' AND race='All' "
        "AND education='All' AND sex='All' AND population='Adults Aged 18+ Years'",
        "$limit": "50000",
        "$order": "year,age",
    }
)
SOURCES = {
    "nchs_life_expectancy.csv": {
        "url": "https://data.cdc.gov/api/views/w9j2-ggv5/rows.csv?accessType=DOWNLOAD",
        "publisher": "CDC/NCHS, NVSS",
        "vintage": "2020-09-08 data revision",
        "license": "Public Domain U.S. Government",
        "documentation": "https://data.cdc.gov/d/w9j2-ggv5",
    },
    "nhis_diabetes.csv": {
        "url": "https://data.cdc.gov/resource/c9xs-vhst.csv?" + NHIS_QUERY,
        "publisher": "CDC, U.S. Diabetes Surveillance System / NHIS",
        "vintage": "2026-06-23 data revision",
        "license": "U.S. federal government data; public access",
        "documentation": "https://usdss.cdc.gov/diabetes/data/socrata/National_Burden_Magnitude_methods.html",
    },
    "sweeteners.csv": {
        "url": "https://www.ers.usda.gov/media/5365/sugar-and-sweeteners-added.csv?v=30567",
        "publisher": "USDA ERS",
        "vintage": "2024-09-27",
        "license": "U.S. federal government data; public access",
        "documentation": "https://www.ers.usda.gov/data-products/food-availability-per-capita-data-system/food-availability-documentation",
    },
}


def _series(key, label, unit, domain, population, source, observations, limitations):
    return dict(
        id=key,
        label=label,
        unit=unit,
        domain=domain,
        population=population,
        source=source,
        observations=observations,
        limitations=limitations,
    )


def transform(raw: Path) -> list[dict]:
    """No interpolation, cross-definition stitching, or inferred T2D fractions."""
    result = []
    mortality = list(csv.DictReader((raw / "nchs_life_expectancy.csv").open()))
    for sex in ("Both Sexes", "Male", "Female"):
        for column, key, unit in (
            ("Average Life Expectancy (Years)", "e0", "years"),
            ("Age-adjusted Death Rate", "death_rate", "deaths per 100000 standard population"),
        ):
            observations = []
            for r in mortality:
                if r["Race"] != "All Races" or r["Sex"] != sex or int(r["Year"]) < 1970:
                    continue
                if not r[column].strip():
                    continue
                year = int(r["Year"])
                segment = (
                    "national"
                    if key == "e0"
                    else ("historical_standard" if year < 1999 else "2000_standard")
                )
                observations.append(dict(year=year, value=float(r[column]), segment=segment))
            result.append(
                _series(
                    f"{key}_{sex.lower().replace(' ', '_')}",
                    column + ": " + sex,
                    unit,
                    "mortality",
                    "U.S., all races, " + sex,
                    "nchs_life_expectancy.csv",
                    observations,
                    [
                        "Published rounded aggregate; no age-specific schedule.",
                        "Death-rate folds cannot cross the 1999 standardization boundary.",
                    ],
                )
            )
    diabetes = list(csv.DictReader((raw / "nhis_diabetes.csv").open()))
    for age in ("18-44", "45-64", "65-74", "75+", "Age-Adjusted", "Crude"):
        observations = []
        for r in diabetes:
            if r["age"] != age:
                continue
            if (
                r["indicator"] != "Diagnosed Diabetes"
                or r["unit"] != "Percentage"
                or any(r[k] != "All" for k in ("sex", "race", "education"))
                or r["population"] != "Adults Aged 18+ Years"
                or r["datasource"] != "National Health Interview Survey (NHIS)"
                or r["other_stratification"]
            ):
                raise ValueError("NHIS endpoint/stratum changed")
            if not r["estimate"] or r["estimatefootnote"]:
                raise ValueError("Review suppressed/footnoted NHIS estimates before ingesting")
            year = int(r["year"])
            observations.append(
                dict(
                    year=year,
                    value=float(r["estimate"]),
                    lower=float(r["lowerlimit"]),
                    upper=float(r["upperlimit"]),
                    segment="nhis_pre2019" if year < 2019 else "nhis_2019_redesign",
                )
            )
        result.append(
            _series(
                "diabetes_" + age.lower().replace("+", "plus"),
                "Diagnosed diabetes: " + age,
                "percent",
                "diabetes",
                "U.S. civilian noninstitutionalized adults 18+; " + age,
                "nhis_diabetes.csv",
                observations,
                [
                    "Self-reported diagnosed diabetes of all types, not total T2D.",
                    "No forecasts cross the 2019 questionnaire/weighting redesign.",
                    "Published survey confidence limits are observation uncertainty, not forecast intervals.",
                ],
            )
        )
    sweeteners = list(csv.DictReader((raw / "sweeteners.csv").open()))
    observations = [
        dict(year=int(r["Year"]), value=float(r["Value"]), segment="availability")
        for r in sweeteners
        if r["Commodity"].strip() == "Caloric sweeteners, per capita availability"
        and r["Attribute"] == "Caloric sweeteners-Total caloric sweeteners-Pounds, dry weight"
        and int(r["Year"]) >= 1970
    ]
    result.append(
        _series(
            "sweetener_availability",
            "Total caloric sweetener availability",
            "pounds dry weight per person per year",
            "food_environment",
            "U.S. population",
            "sweeteners.csv",
            observations,
            [
                "Supply/disappearance proxy, not individual consumption or UPF exposure.",
                "Includes losses; not loss-adjusted.",
                "Exogenous context only; no fitted food-to-disease coefficient.",
            ],
        )
    )
    validate_series(result)
    return result


def validate_series(series: list[dict]) -> None:
    ids = [s["id"] for s in series]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("Series IDs must be unique and nonempty")
    for s in series:
        rows = s["observations"]
        years = [r["year"] for r in rows]
        if not years or len(years) != len(set(years)):
            raise ValueError(f"Missing/duplicate years: {s['id']}")
        rows.sort(key=lambda r: r["year"])
        for r in rows:
            if not isinstance(r["year"], int) or not r["segment"]:
                raise ValueError("Integer years and comparability segments required")
            for k in ("value", "lower", "upper"):
                if k in r and (not math.isfinite(r[k]) or r[k] < 0):
                    raise ValueError("Historical observations must be finite and nonnegative")
            if "lower" in r and not r["lower"] <= r["value"] <= r["upper"]:
                raise ValueError("Observation interval does not enclose estimate")


def rebuild_history(raw: Path, destination: Path = BUNDLE, download: bool = False) -> dict:
    """Verify immutable raw receipts before writing deterministic derived observations."""
    manifest_path = destination / "historical_manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    records = {}
    raw.mkdir(parents=True, exist_ok=True)
    for name, source in SOURCES.items():
        p = raw / name
        old = previous.get("sources", {}).get(name, {})
        if not p.exists():
            if not download:
                raise ValueError(f"Missing raw source {name}; use --download")
            with urllib.request.urlopen(source["url"], timeout=60) as response:
                content = response.read()
            if old and digest(content) != old["sha256"]:
                raise ValueError(f"Source changed: {name}; review a new data vintage")
            p.write_bytes(content)
        sha = digest(p.read_bytes())
        if old and sha != old["sha256"]:
            raise ValueError(f"Raw source checksum mismatch: {name}")
        records[name] = dict(
            source,
            sha256=sha,
            retrieved_at=old.get("retrieved_at", datetime.now(timezone.utc).isoformat()),
        )
    series = transform(raw)
    content = (json.dumps(series, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest = dict(
        schema_version=1,
        sources=records,
        bundle_sha256=digest(content),
        transform="demeter.data.historical.transform",
        start_year=1970,
        vintage_policy="Retrospective revised observations, not real-time vintage forecasts",
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "historical.json").write_bytes(content)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def load_history(destination: Path = BUNDLE) -> tuple[list[dict], dict]:
    content = (destination / "historical.json").read_bytes()
    manifest = json.loads((destination / "historical_manifest.json").read_text())
    if digest(content) != manifest["bundle_sha256"]:
        raise ValueError("Historical bundle checksum mismatch")
    series = json.loads(content)
    validate_series(series)
    return series, manifest
