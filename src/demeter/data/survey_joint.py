"""Joint Taylor sampling covariance of observed ratios, without state allocation.

Every supplied row must have a positive survey weight. Domain restriction is an
indicator, so out-of-domain respondents and PSUs remain in the survey design.
Membership indicators may overlap: their covariance is not an independence
assumption or a distribution for clinical initialization.
"""

from __future__ import annotations

from math import fsum

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

WEIGHT = "WTSAFPRP"
STRATUM = "SDMVSTRA"
PSU = "SDMVPSU"


def _labels(values, name: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} requires a sequence of labels")
    try:
        labels = list(values)
    except TypeError as exc:
        raise ValueError(f"{name} requires a sequence of labels") from exc
    if (
        not labels
        or any(not isinstance(value, str) or not value.strip() for value in labels)
        or len(set(labels)) != len(labels)
    ):
        raise ValueError(f"{name} requires unique nonempty string labels")
    return labels


def _numeric(series: pd.Series, name: str) -> np.ndarray:
    if (
        not is_numeric_dtype(series.dtype)
        or is_bool_dtype(series.dtype)
        or is_complex_dtype(series.dtype)
        or series.isna().any()
    ):
        raise ValueError(f"{name} requires real numeric nonmissing values")
    values = series.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"{name} requires finite values")
    return values


def _aligned(frame: pd.DataFrame, indicators: pd.DataFrame, name: str) -> list[str]:
    if not isinstance(indicators, pd.DataFrame):
        raise ValueError(f"{name} must be a DataFrame")
    if not indicators.index.is_unique or not indicators.index.equals(frame.index):
        raise ValueError(f"{name} requires unique indices aligned in frame order")
    return _labels(indicators.columns, name)


def _valid_index(index: pd.Index) -> bool:
    missing = (
        index.to_frame(index=False).isna().to_numpy().any()
        if isinstance(index, pd.MultiIndex)
        else index.isna().any()
    )
    return bool(index.is_unique and not missing)


def _joint_sum(values) -> float:
    """Use a compensated scalar reduction and reject unrepresentable sums."""
    try:
        value = fsum(values)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Nonfinite joint survey calculation") from exc
    if not np.isfinite(value):
        raise ValueError("Nonfinite joint survey calculation")
    return value


def joint_proportions(
    frame: pd.DataFrame, domains: pd.DataFrame, memberships: pd.DataFrame
) -> dict:
    """Estimate domain-major/member-minor ratios and their full joint covariance.

    Use the with-replacement first-stage Taylor method already used by
    ``nhanes.survey_proportion``. Empty-domain coordinates are unavailable, not
    zero. A singular covariance is valid and is returned without repair.
    """
    if (
        not isinstance(frame, pd.DataFrame)
        or frame.empty
        or not _valid_index(frame.index)
        or not frame.columns.is_unique
        or any(name not in frame for name in (WEIGHT, STRATUM, PSU))
    ):
        raise ValueError("Survey frame requires nonempty unique rows and design/weight columns")
    domain_names = _aligned(frame, domains, "Domains")
    membership_names = _aligned(frame, memberships, "Memberships")
    weight = _numeric(frame[WEIGHT], "Weights")
    if (weight <= 0).any():
        raise ValueError("Weights must be positive; retain every positive-weight design row")
    for name in (STRATUM, PSU):
        _numeric(frame[name], name)
    for name in domain_names:
        if not is_bool_dtype(domains[name].dtype) or domains[name].isna().any():
            raise ValueError("Domains require Boolean nonmissing indicators")
    for name in membership_names:
        if is_bool_dtype(memberships[name].dtype):
            if memberships[name].isna().any():
                raise ValueError("Memberships require binary nonmissing indicators")
            values = memberships[name].to_numpy(dtype=float)
        else:
            values = _numeric(memberships[name], "Memberships")
        if not np.isin(values, [0, 1]).all():
            raise ValueError("Memberships require binary indicators")

    # Common weight rescaling matches the existing scalar ratio calculation.
    # Never discard rows whose contribution to a particular domain is zero.
    weight = weight / weight.max()
    design = frame[[STRATUM, PSU]]
    support = design.drop_duplicates()
    stratum_counts = support.groupby(STRATUM, observed=True).size()
    if (stratum_counts < 2).any():
        raise ValueError("Singleton full-design stratum: covariance is unidentified")
    coordinates, estimates, summaries = [], [], []
    influence = np.zeros((len(frame), len(domain_names) * len(membership_names)))
    available = []
    for domain_name in domain_names:
        mask = domains[domain_name].to_numpy(dtype=bool)
        represented = design.loc[mask].drop_duplicates()
        n, represented_psus = int(mask.sum()), len(represented)
        represented_strata = int(represented[STRATUM].nunique())
        summaries.append(
            {
                "domain": domain_name,
                "n": n,
                "represented_psus": represented_psus,
                "represented_strata": represented_strata,
                "degrees_of_freedom": represented_psus - represented_strata,
                "status": "estimated" if n else "empty_domain",
            }
        )
        denominator = _joint_sum(weight[mask])
        if n and (denominator <= 0 or not np.isfinite(denominator)):
            raise ValueError("Domain denominator is numerically unavailable")
        for membership_name in membership_names:
            coordinate = len(coordinates)
            coordinates.append({"domain": domain_name, "membership": membership_name})
            available.append(bool(n))
            if not n:
                estimates.append(None)
                continue
            values = memberships[membership_name].to_numpy(dtype=float)[mask]
            # Constant domains have exact 0/1 estimates and zero residuals.
            p = (
                float(values[0])
                if np.all(values == values[0])
                else _joint_sum(weight[mask] * values) / denominator
            )
            estimates.append(p)
            influence[mask, coordinate] = weight[mask] * (values - p) / denominator
    if not np.isfinite(influence).all():
        raise ValueError("Nonfinite joint survey calculation")
    # Grouping determines design membership only. All floating reductions use
    # compensated scalar sums, avoiding BLAS/pandas/NumPy reduction order.
    # Numeric stratum/PSU ordering and coordinate ordering are fixed, including
    # full-design PSUs with zero contributions to every requested domain.
    psu_rows = design.groupby([STRATUM, PSU], observed=True, sort=True).indices
    strata = {}
    for (stratum, _), positions in sorted(psu_rows.items()):
        strata.setdefault(stratum, []).append(
            [_joint_sum(influence[positions, k]) for k in range(len(coordinates))]
        )
    stratum_covariances = []
    for totals in strata.values():
        totals = np.asarray(totals, dtype=float)
        m = len(totals)
        mean = np.asarray([_joint_sum(totals[:, k]) / m for k in range(len(coordinates))])
        centered = totals - mean
        # Elementwise products retain the same sum-of-outer-products formula;
        # no symmetry, positivity, closure or other matrix repair is applied.
        products = centered[:, :, None] * centered[:, None, :]
        if not np.isfinite(products).all():
            raise ValueError("Nonfinite joint survey calculation")
        stratum_covariance = [
            [m / (m - 1) * _joint_sum(products[:, i, j]) for j in range(len(coordinates))]
            for i in range(len(coordinates))
        ]
        if not np.isfinite(stratum_covariance).all():
            raise ValueError("Nonfinite joint survey calculation")
        stratum_covariances.append(stratum_covariance)
    contributions = np.asarray(stratum_covariances)
    covariance = [
        [_joint_sum(contributions[:, i, j]) for j in range(len(coordinates))]
        for i in range(len(coordinates))
    ]
    return {
        "coordinates": coordinates,
        "estimates": estimates,
        "covariance": [
            [float(value) if available[i] and available[j] else None for j, value in enumerate(row)]
            for i, row in enumerate(covariance)
        ],
        "design": {
            "weight": WEIGHT,
            "stratum": STRATUM,
            "psu": PSU,
            "positive_weight_n": len(frame),
            "strata": len(stratum_counts),
            "psus": len(support),
            "degrees_of_freedom": int((stratum_counts - 1).sum()),
            "finite_population_correction": False,
        },
        "domains": summaries,
    }


def _real(value) -> bool:
    if not isinstance(value, (int, float, np.integer, np.floating)) or isinstance(
        value, (bool, np.bool_)
    ):
        return False
    try:
        return bool(np.isfinite(float(value)))
    except (OverflowError, ValueError):
        return False


def _projection_matrix(value) -> np.ndarray:
    if isinstance(value, (list, tuple)):
        if any(
            not isinstance(row, (list, tuple, np.ndarray))
            or (isinstance(row, np.ndarray) and row.ndim != 1)
            or any(not _real(x) for x in row)
            for row in value
        ):
            raise ValueError("Projection requires a real finite matrix")
    try:
        matrix = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Projection requires a rectangular matrix") from exc
    if (
        matrix.ndim != 2
        or not is_numeric_dtype(matrix.dtype)
        or is_bool_dtype(matrix.dtype)
        or is_complex_dtype(matrix.dtype)
        or not np.isfinite(matrix).all()
    ):
        raise ValueError("Projection requires a real finite matrix")
    return matrix.astype(float)


def linear_projection(result: dict, A, labels) -> dict:
    """Propagate a fixed linear map without imputing unavailable coordinates.

    A projected row is unavailable when it has a nonzero coefficient on an
    unavailable input. A zero coefficient needs no information from that input.
    No sampling distribution, confidence interval or covariance repair is added.
    """
    if not isinstance(result, dict):
        raise ValueError("Projection requires a joint result")
    coordinates = result.get("coordinates")
    estimates = result.get("estimates")
    covariance = result.get("covariance")
    if (
        not isinstance(coordinates, list)
        or not coordinates
        or not isinstance(estimates, list)
        or len(estimates) != len(coordinates)
        or not isinstance(covariance, list)
        or len(covariance) != len(coordinates)
        or any(not isinstance(row, list) or len(row) != len(coordinates) for row in covariance)
    ):
        raise ValueError("Malformed joint result dimensions")
    pairs = []
    for coordinate in coordinates:
        if not isinstance(coordinate, dict) or set(coordinate) != {"domain", "membership"}:
            raise ValueError("Malformed joint result coordinates")
        pair = tuple(coordinate[k] for k in ("domain", "membership"))
        if any(not isinstance(value, str) or not value.strip() for value in pair):
            raise ValueError("Malformed joint result coordinate labels")
        pairs.append(pair)
    if len(set(pairs)) != len(pairs):
        raise ValueError("Duplicate joint result coordinates")
    available = np.array([value is not None for value in estimates])
    if any(value is not None and not _real(value) for value in estimates):
        raise ValueError("Joint estimates must be finite or unavailable")
    for i, row in enumerate(covariance):
        for j, value in enumerate(row):
            if available[i] and available[j]:
                if not _real(value):
                    raise ValueError("Available joint covariance must be finite")
            elif value is not None:
                raise ValueError("Unavailable joint covariance must remain None")
    projection_labels = _labels(labels, "Projection")
    matrix = _projection_matrix(A)
    if matrix.shape != (len(projection_labels), len(coordinates)):
        raise ValueError("Projection dimensions do not match labels and coordinates")
    output_available = ~np.any(matrix[:, ~available] != 0, axis=1)
    known = matrix[:, available]
    p = np.asarray([value for value in estimates if value is not None], dtype=float)
    v = np.asarray(
        [[covariance[i][j] for j in np.flatnonzero(available)] for i in np.flatnonzero(available)],
        dtype=float,
    ).reshape((int(available.sum()), int(available.sum())))
    # Fixed-order compensated sparse sums avoid BLAS-specific reduction order.
    # Preserve the two-stage A V then A V A^T calculation and its nonfinite
    # failure boundary; do not clip, repair or impute any matrix element.
    active = np.flatnonzero(output_available)
    nonzero = [np.flatnonzero(row) for row in known]
    projected_estimates = np.zeros(len(projection_labels))
    intermediate = np.zeros((len(projection_labels), len(p)))
    projected_covariance = np.zeros((len(projection_labels), len(projection_labels)))
    try:
        for i in active:
            projected_estimates[i] = fsum(float(known[i, k]) * float(p[k]) for k in nonzero[i])
            for j in range(len(p)):
                intermediate[i, j] = fsum(float(known[i, k]) * float(v[k, j]) for k in nonzero[i])
        if not np.isfinite(intermediate[output_available]).all():
            raise ValueError("Nonfinite intermediate projection")
        for i in active:
            for j in active:
                projected_covariance[i, j] = fsum(
                    float(intermediate[i, k]) * float(known[j, k]) for k in nonzero[j]
                )
    except (OverflowError, ValueError) as exc:
        raise ValueError("Nonfinite linear projection") from exc
    if (
        not np.isfinite(projected_estimates[output_available]).all()
        or not np.isfinite(projected_covariance[np.ix_(output_available, output_available)]).all()
    ):
        raise ValueError("Nonfinite linear projection")
    return {
        "labels": projection_labels,
        "estimates": [
            float(x) if output_available[i] else None for i, x in enumerate(projected_estimates)
        ],
        "covariance": [
            [
                float(value) if output_available[i] and output_available[j] else None
                for j, value in enumerate(row)
            ]
            for i, row in enumerate(projected_covariance)
        ],
    }
