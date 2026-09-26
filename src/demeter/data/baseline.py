"""Load only checked, versioned model-ready source data."""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from demeter.data.ingest import BUNDLE, digest
from demeter.life_table import AgeInterval, period_life_table


@lru_cache(maxsize=1)
def load_data() -> dict:
    content = (BUNDLE / "us_baseline.json").read_bytes()
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    if digest(content) != manifest["bundle_sha256"]:
        raise ValueError("Bundled input checksum mismatch; rebuild from pinned sources")
    return json.loads(content)


def source_rows(year: int = 2024, sex: str = "all") -> list[dict]:
    return load_data()["mortality"][str(year)][sex]


def population_counts(year: int = 2024, sex: str = "all") -> np.ndarray:
    return np.array(load_data()["population"][str(year)][sex], dtype=float)


def source_intervals(year: int = 2024, sex: str = "all") -> list[AgeInterval]:
    return [
        AgeInterval(
            r["age"],
            1 if r["age"] < 100 else None,
            r["qx"],
            r["ax"],
            r["ex"] if r["age"] == 100 else None,
        )
        for r in source_rows(year, sex)
    ]


def baseline_validation(year: int = 2024, sex: str = "all") -> dict:
    calculated = period_life_table(source_intervals(year, sex))
    source = source_rows(year, sex)
    max_error = max(
        abs(r.life_expectancy - s["ex"]) for r, s in zip(calculated, source, strict=True)
    )
    return {
        "year": year,
        "sex": sex,
        "calculated_e0": calculated[0].life_expectancy,
        "published_e0": source[0]["ex"],
        "max_age_ex_error_years": max_error,
        "tolerance_years": 0.001,
        "passed": max_error < 0.001,
        "interpretation": "Reconstruction of published qx, ax and terminal ex; not a dietary-effect validation",
    }
