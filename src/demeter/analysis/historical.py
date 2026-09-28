"""Calendar-time holdouts for historical benchmarks, never a causal diet fit.

Forecast functions receive training observations only. Intervals use earlier
same-horizon forecast errors whose target years are no later than the origin.
"""

from __future__ import annotations

import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Literal

import numpy as np

from demeter import __version__
from demeter.data.historical import load_history, validate_series
from demeter.data.ingest import digest
from demeter.schema import EvidenceRegistry

Method = Literal["persistence", "linear_trend"]
SHOCKS = [
    {
        "id": "nhis_redesign",
        "start": 2019,
        "end": None,
        "domain": "diabetes",
        "treatment": "Comparability boundary: never train or score across it.",
        "source": "https://usdss.cdc.gov/diabetes/data/socrata/National_Burden_Magnitude_methods.html",
    },
    {
        "id": "covid",
        "start": 2020,
        "end": 2022,
        "domain": "all",
        "treatment": "Flag affected holdouts; no post-origin shock magnitude fitted.",
        "source": "https://www.cdc.gov/nchs/data/databriefs/db456.pdf",
    },
    {
        "id": "glp1_obesity_regime",
        "start": 2021,
        "end": None,
        "domain": "all",
        "treatment": "Post-Wegovy approval context; optional GLP-1 mechanics exist, but historical adoption/effects remain uncalibrated and are not fitted by these benchmarks.",
        "source": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/215256s000lbl.pdf",
    },
]
OMITTED_FACTORS = [
    "Smoking trends",
    "Antihypertensive and lipid-lowering medication use",
    "Diagnostic/testing changes",
    "Demographic aging",
    "Opioids and other non-food mortality",
]


def forecast(training: list[dict], target: int, method: Method, window: int = 10) -> dict:
    """Fit an inspectable benchmark to the last window observations in one segment."""
    if method not in ("persistence", "linear_trend") or window < 3:
        raise ValueError("Choose persistence or linear_trend and window >= 3")
    if len(training) < window:
        raise ValueError("Insufficient training observations")
    rows = training[-window:]
    years = [r["year"] for r in rows]
    if years != sorted(set(years)) or target <= years[-1]:
        raise ValueError("Forecast requires sorted unique training years before target")
    if len({r["segment"] for r in rows}) != 1:
        raise ValueError("Cannot fit across a comparability boundary")
    if years != list(range(years[0], years[-1] + 1)):
        raise ValueError("Annual benchmark cannot bridge missing observations")
    y = np.array([r["value"] for r in rows], dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("Training observations must be finite")
    x = np.array(years) - years[-1]
    slope = float(np.dot(x - x.mean(), y - y.mean()) / np.dot(x - x.mean(), x - x.mean()))
    intercept = float(y.mean() - slope * x.mean())
    if method == "persistence":
        slope, intercept = 0.0, float(y[-1])
    fitted = intercept + slope * x
    residuals = y - fitted
    return {
        "predicted": intercept + slope * (target - years[-1]),
        "parameters": {"level_at_origin": intercept, "slope_per_year": slope},
        "training_years": years,
        "calibration_rmse": float(np.sqrt(np.mean(residuals**2))),
    }


def interval_errors(training: list[dict], horizon: int, method: Method, window: int) -> list[dict]:
    """Historical pseudo-validation entirely before the outer holdout."""
    by_year = {r["year"]: r for r in training}
    errors = []
    for i in range(window - 1, len(training)):
        target = training[i]["year"] + horizon
        if target not in by_year:
            continue
        prediction = forecast(training[: i + 1], target, method, window)["predicted"]
        errors.append(
            {
                "origin": training[i]["year"],
                "target": target,
                "absolute_error": abs(by_year[target]["value"] - prediction),
            }
        )
    return errors


def metrics(rows: list[dict]) -> dict:
    if not rows:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "mape_percent": None,
            "interval_n": 0,
            "coverage": None,
        }
    errors = np.array([r["residual"] for r in rows])  # observed minus predicted
    observed = np.array([r["observed"] for r in rows])
    eligible = [r for r in rows if r["lower"] is not None]
    return {
        "n": len(rows),
        "mae": float(np.mean(abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "bias": float(np.mean(errors)),
        "mape_percent": float(np.mean(abs(errors / observed)) * 100)
        if np.all(observed != 0)
        else None,
        "interval_n": len(eligible),
        "coverage": sum(r["lower"] <= r["observed"] <= r["upper"] for r in eligible) / len(eligible)
        if eligible
        else None,
    }


def backtest_series(
    series: dict,
    *,
    horizons: tuple[int, ...] = (5, 10),
    window: int = 10,
    methods: tuple[Method, ...] = ("persistence", "linear_trend"),
    origins: tuple[int, ...] | None = None,
    coverage: float = 0.9,
) -> dict:
    """Rolling-origin folds; origins=(T,) also gives a frozen-origin era diagnostic."""
    validate_series([series])
    if window < 3 or not horizons or any(h <= 0 or not isinstance(h, int) for h in horizons):
        raise ValueError("Positive integer horizons and window >= 3 required")
    if not 0 < coverage < 1 or not methods or set(methods) - {"persistence", "linear_trend"}:
        raise ValueError("Invalid coverage or benchmark method")
    all_rows = series["observations"]
    by_year = {r["year"]: r for r in all_rows}
    folds, skipped = [], []
    for origin in origins if origins is not None else tuple(by_year):
        if origin not in by_year:
            skipped.append({"origin": origin, "reason": "origin unavailable"})
            continue
        # Restrict to the latest uninterrupted comparability segment ending at origin.
        training = []
        for year in range(origin, min(by_year) - 1, -1):
            if year not in by_year or by_year[year]["segment"] != by_year[origin]["segment"]:
                break
            training.append(by_year[year])
        training.reverse()
        if len(training) < window:
            skipped.append({"origin": origin, "reason": "insufficient comparable annual training"})
            continue
        for horizon in horizons:
            target = origin + horizon
            if target not in by_year:
                skipped.append(
                    {"origin": origin, "horizon": horizon, "reason": "target unavailable"}
                )
                continue
            future = [by_year.get(y) for y in range(origin + 1, target + 1)]
            if any(r is None or r["segment"] != training[-1]["segment"] for r in future):
                skipped.append(
                    {
                        "origin": origin,
                        "horizon": horizon,
                        "reason": "comparability boundary or missing year",
                    }
                )
                continue
            for method in methods:
                fit = forecast(training, target, method, window)
                validation = interval_errors(training, horizon, method, window)
                n = len(validation)
                rank = math.ceil((n + 1) * coverage)
                radius = (
                    sorted(r["absolute_error"] for r in validation)[rank - 1]
                    if n and rank <= n
                    else None
                )
                observed = by_year[target]["value"]
                pred = fit.pop("predicted")
                flags = [
                    s["id"]
                    for s in SHOCKS
                    if s["domain"] in ("all", series["domain"])
                    and target >= s["start"]
                    and (s["end"] is None or origin < s["end"])
                ]
                folds.append(
                    dict(
                        origin=origin,
                        target_year=target,
                        horizon=horizon,
                        method=method,
                        segment=training[-1]["segment"],
                        predicted=pred,
                        observed=observed,
                        observed_lower=by_year[target].get("lower"),
                        observed_upper=by_year[target].get("upper"),
                        residual=observed - pred,
                        lower=pred - radius if radius is not None else None,
                        upper=pred + radius if radius is not None else None,
                        interval_validation=validation,
                        interval_n=n,
                        shock_flags=flags,
                        roles={
                            "calibration": fit["training_years"],
                            "interval_validation_targets": [r["target"] for r in validation],
                            "holdout": [target],
                            "exogenous_inputs": [],
                        },
                        **fit,
                    )
                )
    grouped = defaultdict(list)
    for f in folds:
        grouped[(f["method"], f["horizon"], f["segment"])].append(f)
    summaries = [
        dict(
            method=k[0],
            horizon=k[1],
            segment=k[2],
            **metrics(v),
            calibration_rmse=float(np.mean([r["calibration_rmse"] for r in v])),
            holdout_minus_calibration_rmse=metrics(v)["rmse"]
            - float(np.mean([r["calibration_rmse"] for r in v])),
        )
        for k, v in sorted(grouped.items())
    ]
    return {
        **{k: v for k, v in series.items() if k != "observations"},
        "observations": all_rows,
        "folds": folds,
        "skipped": skipped,
        "metrics": summaries,
    }


def provenance() -> dict:
    source = Path(__file__).resolve().parents[1]
    h = digest(
        b"".join(
            p.relative_to(source).as_posix().encode() + b"\0" + p.read_bytes()
            for p in sorted(source.rglob("*.py"))
        )
    )
    try:
        root = source.parents[1]
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {
        "model_version": __version__,
        "git_commit": commit,
        "working_tree_dirty": dirty,
        "python_source_sha256": h,
    }


def historical_backtest(
    registry: EvidenceRegistry,
    *,
    window: int = 10,
    horizons: tuple[int, ...] = (5, 10),
    origins: tuple[int, ...] | None = None,
    coverage: float = 0.9,
) -> dict:
    series, manifest = load_history()
    return {
        "schema_version": 1,
        "kind": "historical_benchmarks",
        "scientific_validation_of_diet": False,
        "integrated_health_model_validated": False,
        "configuration": {
            "window": window,
            "horizons": list(horizons),
            "origins": list(origins) if origins is not None else None,
            "interval_nominal_coverage": coverage,
            "random_seed": None,
        },
        "metadata": {
            **provenance(),
            "evidence_sha256": registry.content_hash,
            "data_sha256": manifest["bundle_sha256"],
            "manifest_sha256": digest(json.dumps(manifest, sort_keys=True).encode()),
            "sources": manifest["sources"],
            "vintage_policy": manifest["vintage_policy"],
        },
        "interval_method": "Same-horizon past absolute errors, order ceil((n+1)*coverage); "
        "null if too few errors. No exchangeability guarantee for serial history.",
        "role_policy": "Earlier interval-validation observations may later enter calibration; "
        "they are not independent validation of the final fit. Outer holdout never enters its fit.",
        "structural_breaks": SHOCKS,
        "unmodeled_exogenous_factors": OMITTED_FACTORS,
        "causal_policy": "Univariate benchmarks only. No food coefficient can absorb omitted shocks. "
        "Food series are external historical context, not individual exposure.",
        "limitations": [
            "Revised vintages: not a recreation of information available at the origin.",
            "No age-specific historical cohort reconstruction or causal attribution yet.",
            "Survey estimates are noisy; coverage evaluates their point estimates.",
            "Intervals can fail under trends or structural breaks; failures are retained.",
            "Long-history mortality ends before COVID; no missing-year interpolation.",
            "Parameter/sensitivity drift of the integrated health model remains unvalidated.",
        ],
        "series": [
            backtest_series(s, horizons=horizons, window=window, origins=origins, coverage=coverage)
            for s in series
        ],
    }
