"""Additive predictive summaries from frozen laboratory bootstrap aggregates.

The original complete-vector summary remains conditional on all eight finite
differences. Metric blocks and coordinates use their own explicitly counted
finite support. No covariance uses pairwise deletion, no draw is redrawn, and
no fit or source record is read here. Legacy unsupported log differences have a
coarsened status: their sign or zero-probability cause cannot be recovered.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

import numpy as np

from demeter.analysis import laboratory_panel as lab

_CELL_STATUSES = {"finite", "unavailable", "unavailable_or_nonfinite_difference"}
_NOT_SCORED = {
    "not_scored",
    "not_scored_fit_unavailable",
    "not_scored_iid_fit_unavailable",
}
_PREDICTION_STATUSES = {
    "performed_finite",
    "nonfinite_or_unavailable_scores",
    "numerical_prediction_failure",
    *_NOT_SCORED,
}


def predictive_coordinates() -> list[dict]:
    """Fresh copy of the frozen eight-coordinate ordering."""
    return [
        {
            "mode": mode,
            "metric": metric,
            "weighting": weighting,
            "higher_is_better": metric == "log_score",
        }
        for mode in ("one_step", "first_only")
        for metric in ("log_score", "brier")
        for weighting in ("equal_label", "transition_weighted")
    ]


def _finite_number(value) -> bool:
    return (
        isinstance(value, (int, float, np.integer, np.floating))
        and not isinstance(value, (bool, np.bool_))
        and bool(np.isfinite(value))
    )


def _levels(values) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("Explicit ordered probability levels are required")
    levels = tuple(values)
    if (
        not levels
        or any(not _finite_number(x) or not 0 <= x <= 1 for x in levels)
        or any(b <= a for a, b in zip(levels, levels[1:], strict=False))
    ):
        raise ValueError("Explicit ordered probability levels are required")
    return tuple(float(x) for x in levels)


def _status_counts(values) -> dict:
    return dict(sorted(Counter(values).items()))


def _validated_vectors(vectors) -> list[dict]:
    if not isinstance(vectors, Sequence) or isinstance(vectors, (str, bytes)):
        raise ValueError("Predictive score vectors must retain every ordered draw")
    clean = []
    for index, row in enumerate(vectors):
        if (
            not isinstance(row, Mapping)
            or type(row.get("replicate")) is not int
            or row["replicate"] != index
            or type(row.get("fit_available")) is not bool
            or row.get("fit_status") != ("performed" if row["fit_available"] else "unavailable")
            or row.get("prediction_status") not in _PREDICTION_STATUSES
            or not isinstance(row.get("values"), (list, tuple))
            or not isinstance(row.get("coordinate_status"), (list, tuple))
            or len(row["values"]) != 8
            or len(row["coordinate_status"]) != 8
        ):
            raise ValueError("Invalid ordered predictive aggregate vector")
        values, statuses = [], []
        for value, status in zip(row["values"], row["coordinate_status"], strict=True):
            if (
                status not in _CELL_STATUSES | _NOT_SCORED | {"numerical_prediction_failure"}
                or (status == "finite" and not _finite_number(value))
                or (status != "finite" and value is not None)
            ):
                raise ValueError("Predictive status cannot floor or hide a nonfinite difference")
            values.append(float(value) if status == "finite" else None)
            statuses.append(status)
        prediction = row["prediction_status"]
        complete = all(value is not None for value in values)
        if (
            (not row["fit_available"] and prediction != "not_scored_fit_unavailable")
            or (row["fit_available"] and prediction == "not_scored_fit_unavailable")
            or (prediction == "performed_finite" and not complete)
            or (prediction == "nonfinite_or_unavailable_scores" and complete)
            or (
                prediction in _NOT_SCORED | {"numerical_prediction_failure"}
                and (any(value is not None for value in values) or set(statuses) != {prediction})
            )
        ):
            raise ValueError("Predictive draw status and finite support do not reconcile")
        clean.append(
            {
                "replicate": index,
                "fit_available": row["fit_available"],
                "fit_status": row["fit_status"],
                "prediction_status": prediction,
                "values": values,
                "coordinate_status": statuses,
            }
        )
    return clean


def _block(vectors, indices, levels) -> dict:
    rows = [
        [row["values"][i] for i in indices]
        for row in vectors
        if all(row["values"][i] is not None for i in indices)
    ]
    return {
        "coordinate_indices": list(indices),
        "attempted_draws": len(vectors),
        "finite_draws": len(rows),
        "unavailable_draws": len(vectors) - len(rows),
        "nominal_contributing_draw_resolution": 1 / len(rows) if rows else None,
        "conditioning": "finite_differences_for_exactly_the_declared_coordinates",
        "summary": lab._sample_summary(rows, levels),
    }


def summarize_predictive_vectors(vectors, *, quantile_levels) -> dict:
    """Reconstruct one model's summaries from sanitized retained score vectors.

    Each block uses complete draws for exactly its declared coordinates.
    Coordinate summaries are marginal sampling summaries, not independent priors.
    One finite draw is counted but cannot establish a covariance or percentile
    summary under the frozen sample-summary rule.
    """
    levels = _levels(quantile_levels)
    vectors = _validated_vectors(vectors)
    coordinates = predictive_coordinates()
    blocks = {
        metric: _block(
            vectors,
            [i for i, coordinate in enumerate(coordinates) if coordinate["metric"] == metric],
            levels,
        )
        for metric in ("log_score", "brier")
    }
    per_coordinate = []
    for index in range(8):
        block = _block(vectors, (index,), levels)
        per_coordinate.append(
            {
                "coordinate_index": index,
                "attempted_draws": block["attempted_draws"],
                "finite_draws": block["finite_draws"],
                "unavailable_draws": block["unavailable_draws"],
                "nominal_contributing_draw_resolution": block[
                    "nominal_contributing_draw_resolution"
                ],
                "conditioning": block["conditioning"],
                "status_counts": _status_counts(row["coordinate_status"][index] for row in vectors),
                "summary": block["summary"],
            }
        )
    return {
        "complete_vector": _block(vectors, range(8), levels),
        "metric_blocks": blocks,
        "per_coordinate": per_coordinate,
        "fit_status_counts": _status_counts(row["fit_status"] for row in vectors),
        "prediction_status_counts": _status_counts(row["prediction_status"] for row in vectors),
        "covariance_uses_pairwise_deletion": False,
        "unsupported_log_difference_causes_identified": False,
    }


def _extract_vectors(records, name) -> list[dict]:
    vectors = []
    for index, record in enumerate(records):
        if type(record.get("replicate")) is not int or record["replicate"] != index:
            raise ValueError("Legacy bootstrap must retain every ordered draw")
        fit = record["models"][name]["fit_performed"]
        if type(fit) is not bool:
            raise ValueError("Invalid legacy fit availability")
        prediction = record["prediction_status"].get(name)
        detail = record["predictive_score_differences_vs_iid"].get(name)
        if prediction is None:
            prediction = (
                "not_scored_fit_unavailable"
                if not fit
                else "not_scored_iid_fit_unavailable"
                if "iid" in record["failures"]
                else "not_scored"
            )
            if detail:
                raise ValueError("Unscored legacy draw contains predictive results")
            values, statuses = [None] * 8, [prediction] * 8
        elif prediction == "numerical_prediction_failure":
            if detail != {"failure": "numerical_prediction_failure"}:
                raise ValueError("Legacy numerical prediction failure is inconsistent")
            values, statuses = [None] * 8, [prediction] * 8
        else:
            values, statuses = [], []
            for coordinate in predictive_coordinates():
                key = coordinate["weighting"] + (
                    "_brier" if coordinate["metric"] == "brier" else ""
                )
                cell = detail[coordinate["mode"]][key]
                if cell["status"] not in _CELL_STATUSES:
                    raise ValueError("Unsupported legacy difference status")
                values.append(cell["value"])
                statuses.append(cell["status"])
        vectors.append(
            {
                "replicate": index,
                "fit_available": fit,
                "fit_status": "performed" if fit else "unavailable",
                "prediction_status": prediction,
                "values": values,
                "coordinate_status": statuses,
            }
        )
    return _validated_vectors(vectors)


def summarize_predictive_bootstrap(bootstrap: Mapping, *, quantile_levels) -> dict:
    """Add metric-specific summaries without changing the frozen bootstrap result.

    Input is the legacy library return value before a source adapter removes its
    replicate records. Output retains only aggregate predictive differences and
    known availability statuses, never model rates, identifiers, paths or times.
    The complete-vector summary must exactly match the original legacy summary.
    """
    levels = _levels(quantile_levels)
    coordinates = predictive_coordinates()
    supplied = bootstrap["predictive_difference_coordinates"]
    records = bootstrap["replicates"]
    if (
        supplied != coordinates
        or any(type(row["higher_is_better"]) is not bool for row in supplied)
        or type(bootstrap["repetitions_requested"]) is not int
        or bootstrap["repetitions_requested"] < 2
        or type(bootstrap["repetitions_attempted"]) is not int
        or bootstrap["repetitions_attempted"] != len(records)
        or bootstrap["repetitions_requested"] != len(records)
        or bootstrap["failed_draws_redrawn"] is not False
    ):
        raise ValueError("Legacy predictive coordinates or draw controls drift")
    vectors, models = {}, {}
    for name, legacy in bootstrap["predictive_difference_summaries"].items():
        vectors[name] = _extract_vectors(records, name)
        models[name] = summarize_predictive_vectors(vectors[name], quantile_levels=levels)
        if models[name]["complete_vector"]["summary"] != legacy:
            raise ValueError("Complete-vector summary differs from frozen legacy result")
    return {
        "schema_version": 1,
        "scope": "additive conditional predictive metric reporting",
        "coordinates": coordinates,
        "quantile_levels": list(levels),
        "repetitions_requested": bootstrap["repetitions_requested"],
        "repetitions_attempted": bootstrap["repetitions_attempted"],
        "failed_draws_redrawn": False,
        "replicate_score_vectors": vectors,
        "models": models,
        "covariance_uses_pairwise_deletion": False,
        "clinical_fit_performed": False,
        "engine_activation_allowed": False,
    }
