"""Conditional recorded laboratory-band dynamics, separate from clinical states.

No thresholds, source parsing, diagnosis history, mortality or causal effects
are inferred here. All numerical search and uncertainty settings are supplied
by the caller. A last laboratory observation is not a survival/censoring event.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from math import fsum, isfinite, log
from numbers import Real

import numpy as np
from scipy.linalg import expm, expm_frechet
from scipy.optimize import minimize

EDGES = {
    "adjacent": ((0, 1), (1, 0), (1, 2), (2, 1)),
    "unrestricted": ((0, 1), (1, 0), (1, 2), (2, 1), (0, 2), (2, 0)),
}


def _number(value, *, nonnegative=False, positive=False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError("Expected a finite real scalar, without coercion")
    try:
        value = float(value)
    except (ValueError, OverflowError) as error:
        raise ValueError("Expected a finite real scalar") from error
    if not isfinite(value) or (nonnegative and value < 0) or (positive and value <= 0):
        raise ValueError("Scalar outside its finite domain")
    return value


def _vector(values, *, length=None, nonnegative=False) -> tuple[float, ...]:
    if isinstance(values, np.ma.MaskedArray):
        raise ValueError("A masked numerical vector is unsupported")
    if not isinstance(values, (tuple, list, np.ndarray)):
        raise ValueError("Expected an explicit numerical sequence")
    if isinstance(values, np.ndarray) and values.ndim != 1:
        raise ValueError("Expected a one-dimensional numerical sequence")
    result = tuple(_number(x, nonnegative=nonnegative) for x in values)
    if length is not None and len(result) != length:
        raise ValueError("Numerical dimensions disagree")
    return result


def _tolerance(value) -> float:
    value = _number(value, positive=True)
    if value >= 1:
        raise ValueError("Numerical tolerance must be below one")
    return value


def _paths(paths) -> tuple[PanelPath, ...]:
    if (
        type(paths) not in (tuple, list)
        or not paths
        or any(type(x) is not PanelPath for x in paths)
    ):
        raise ValueError("An explicit nonempty sequence of PanelPath objects is required")
    return tuple(paths)


def _rates(rates, structure) -> tuple[float, ...]:
    if type(structure) is not str or structure not in EDGES:
        raise ValueError("Unsupported laboratory generator structure")
    return _vector(rates, length=len(EDGES[structure]), nonnegative=True)


def _log_value(value: float) -> dict:
    if value == -np.inf:
        return {"value": None, "status": "negative_infinity_zero_probability"}
    if not isfinite(value):
        raise ValueError("Nonfinite log evaluation")
    return {"value": float(value), "status": "finite"}


@dataclass(frozen=True)
class PanelPath:
    """One label's observed bands at strictly increasing finite source-day coordinates.

    An unknown additive coordinate origin cancels. Each band is an integer 0, 1
    or 2 already selected by the caller; none denotes a clinical diagnosis.
    A one-observation path is retained but supplies no switching information.
    """

    days: tuple[float, ...]
    bands: tuple[int, ...]

    def __post_init__(self):
        days = _vector(self.days)
        if type(self.bands) not in (tuple, list):
            raise ValueError("Band labels must be an explicit integer sequence")
        bands = tuple(self.bands)
        if (
            not days
            or len(days) != len(bands)
            or any(type(b) is not int or b not in range(3) for b in bands)
        ):
            raise ValueError("Invalid observed-band path")
        if not isfinite(days[-1] - days[0]) or any(
            b <= a or not isfinite(b - a) for a, b in zip(days, days[1:], strict=False)
        ):
            raise ValueError("Observation coordinates must be strictly increasing with finite gaps")
        object.__setattr__(self, "days", days)
        object.__setattr__(self, "bands", bands)


@dataclass(frozen=True)
class FitSettings:
    """Computational bounds/settings, never clinical prior information."""

    structure: str
    initial_rates: tuple[tuple[float, ...], ...]
    rate_upper_bounds: tuple[float, ...]
    day_scale: float
    probability_tolerance: float
    optimizer_maxiter: int
    optimizer_ftol: float
    optimizer_gtol: float
    jacobian_step: float
    rank_relative_tolerance: float

    def __post_init__(self):
        caps = _rates(self.rate_upper_bounds, self.structure)
        if (
            any(x <= 0 for x in caps)
            or type(self.initial_rates) not in (tuple, list)
            or not self.initial_rates
        ):
            raise ValueError("Positive computational caps and explicit multistarts are required")
        starts = tuple(_rates(x, self.structure) for x in self.initial_rates)
        if any(x > c for row in starts for x, c in zip(row, caps, strict=False)):
            raise ValueError("A starting rate exceeds its computational cap")
        if type(self.optimizer_maxiter) is not int or self.optimizer_maxiter < 1:
            raise ValueError("A positive optimizer iteration limit is required")
        object.__setattr__(self, "initial_rates", starts)
        object.__setattr__(self, "rate_upper_bounds", caps)
        for name in ("day_scale", "optimizer_ftol", "optimizer_gtol", "jacobian_step"):
            object.__setattr__(self, name, _number(getattr(self, name), positive=True))
        for name in ("probability_tolerance", "rank_relative_tolerance"):
            object.__setattr__(self, name, _tolerance(getattr(self, name)))
        if any(not isfinite(x * self.day_scale) for x in caps):
            raise ValueError("Scaled computational bounds overflow")


def generator(rates, structure: str) -> np.ndarray:
    """Three-band row generator; rate units are reciprocal source days."""
    rates = _rates(rates, structure)
    q = np.zeros((3, 3))
    for rate, (i, j) in zip(rates, EDGES[structure], strict=False):
        q[i, j] = rate
    for i in range(3):
        try:
            q[i, i] = -fsum(q[i, j] for j in range(3) if i != j)
        except OverflowError as error:
            raise ValueError("Generator arithmetic overflow") from error
    if not np.isfinite(q).all():
        raise ValueError("Generator arithmetic overflow")
    return q


def _transition(rates, structure, gap, tolerance) -> tuple[np.ndarray, int, float]:
    gap = _number(gap, nonnegative=True)
    q = generator(rates, structure)
    with np.errstate(over="ignore", invalid="ignore"):
        argument = q * gap
    if not np.isfinite(argument).all():
        raise ValueError("Matrix-exponential argument overflow")
    matrix = expm(argument)
    if (
        not np.isfinite(matrix).all()
        or (matrix < -tolerance).any()
        or (matrix > 1 + tolerance).any()
    ):
        raise ValueError("Transition matrix failed probability checks")
    negatives = matrix < 0
    count = int(np.count_nonzero(negatives))
    minimum = float(matrix.min()) if count else 0.0
    # Only explicitly bounded floating roundoff is corrected, never rates/mass.
    matrix = np.maximum(matrix, 0)
    if any(abs(fsum(row) - 1) > tolerance for row in matrix):
        raise ValueError("Transition matrix failed conservation checks")
    return matrix, count, minimum


def transition_matrix(rates, structure, gap_days, *, probability_tolerance) -> np.ndarray:
    """Endpoint occupancy permits multiple unobserved switches during a gap."""
    return _transition(rates, structure, gap_days, _tolerance(probability_tolerance))[0]


def transition_summary(paths) -> dict:
    """Aggregate adjacent observations, not independent records or exact jump counts."""
    paths = _paths(paths)
    counts = [[0] * 3 for _ in range(3)]
    gaps = []
    for path in paths:
        for k in range(1, len(path.days)):
            counts[path.bands[k - 1]][path.bands[k]] += 1
            gaps.append(path.days[k] - path.days[k - 1])
    return {
        "label_paths": len(paths),
        "single_observation_paths": sum(len(x.days) == 1 for x in paths),
        "repeat_observation_paths": sum(len(x.days) > 1 for x in paths),
        "observations": sum(len(x.days) for x in paths),
        "adjacent_observation_pairs": len(gaps),
        "observed_pair_counts": counts,
        "distinct_elapsed_gaps": len(set(gaps)),
        "gap_range_days": [min(gaps), max(gaps)] if gaps else None,
        "exact_process_jump_counts": False,
        "independent_pair_sampling_assumed": False,
    }


def _likelihood(paths, rates, structure, tolerance) -> tuple[float, dict]:
    cache, terms = {}, []
    corrections, minimum = 0, 0.0
    for path in paths:
        for k in range(1, len(path.days)):
            gap = path.days[k] - path.days[k - 1]
            if gap not in cache:
                cache[gap], count, negative = _transition(rates, structure, gap, tolerance)
                corrections += count
                minimum = min(minimum, negative)
            probability = float(cache[gap][path.bands[k - 1], path.bands[k]])
            if probability == 0:
                # Topological support distinguishes impossible paths from underflow.
                support = {path.bands[k - 1]}
                q = generator(rates, structure)
                for _ in range(3):
                    support |= {j for i in tuple(support) for j in range(3) if q[i, j] > 0}
                if path.bands[k] in support:
                    raise ValueError("Positive-support transition underflow")
                return -np.inf, {"entries_zeroed": corrections, "most_negative_entry": minimum}
            terms.append(log(probability))
    try:
        total = fsum(terms)
    except (ValueError, OverflowError) as error:
        raise ValueError("Likelihood arithmetic failed") from error
    return total, {"entries_zeroed": corrections, "most_negative_entry": minimum}


def conditional_log_likelihood(paths, rates, structure, *, probability_tolerance) -> float:
    """Joint path log likelihood conditional on first band and recorded visit times."""
    paths = _paths(paths)
    rates = _rates(rates, structure)
    return _likelihood(paths, rates, structure, _tolerance(probability_tolerance))[0]


def design_identifiability(paths, rates, settings: FitSettings) -> dict:
    """Local observable rank using observed start-band/gap rows, not hypothetical entries."""
    paths = _paths(paths)
    if type(settings) is not FitSettings:
        raise ValueError("Explicit fitting settings are required")
    rates = _rates(rates, settings.structure)
    if any(x > cap for x, cap in zip(rates, settings.rate_upper_bounds, strict=False)):
        raise ValueError("Rates exceed computational caps")
    design = tuple(
        sorted(
            {
                (p.bands[k - 1], p.days[k] - p.days[k - 1])
                for p in paths
                for k in range(1, len(p.days))
            }
        )
    )
    theta = np.asarray(rates) * settings.day_scale
    caps = np.asarray(settings.rate_upper_bounds) * settings.day_scale
    gaps = np.asarray(sorted({gap for _, gap in design}))
    gap_index = {gap: k for k, gap in enumerate(gaps)}

    def observable(point):
        if not design:
            return np.asarray([])
        q = generator(point / settings.day_scale, settings.structure)
        matrices, _, _ = _spectral_kernels(q, gaps, (), settings.probability_tolerance)
        if (
            not np.isfinite(matrices).all()
            or (matrices < -settings.probability_tolerance).any()
            or (matrices > 1 + settings.probability_tolerance).any()
        ):
            raise ValueError("Observable transition probabilities failed")
        matrices = np.maximum(matrices, 0)
        if any(
            abs(fsum(row) - 1) > settings.probability_tolerance
            for matrix in matrices
            for row in matrix
        ):
            raise ValueError("Observable transition conservation failed")
        return np.concatenate([matrices[gap_index[gap], band] for band, gap in design])

    base = observable(theta)
    columns, schemes, denominators = [], [], []
    for i in range(len(theta)):
        step = settings.jacobian_step
        plus, minus = theta.copy(), theta.copy()
        if theta[i] >= step and theta[i] + step <= caps[i]:
            plus[i] += step
            minus[i] -= step
            denominator = plus[i] - minus[i]
            numerator = observable(plus) - observable(minus)
            scheme = "central"
        elif theta[i] + step <= caps[i]:
            plus[i] += step
            denominator = plus[i] - theta[i]
            numerator = observable(plus) - base
            scheme = "forward_at_or_near_lower_boundary"
        elif theta[i] >= step:
            minus[i] -= step
            denominator = theta[i] - minus[i]
            numerator = base - observable(minus)
            scheme = "backward_at_or_near_search_cap"
        else:
            raise ValueError("Jacobian step does not fit the computational domain")
        if not isfinite(denominator) or denominator <= 0:
            raise ValueError("Jacobian perturbation is not representable")
        derivative = numerator / denominator
        if not np.isfinite(derivative).all():
            raise ValueError("Nonfinite observable derivative")
        columns.append(derivative)
        schemes.append(scheme)
        denominators.append(float(denominator))
    jacobian = np.column_stack(columns)
    singular = np.linalg.svd(jacobian, compute_uv=False) if len(base) else np.asarray([])
    cutoff = settings.rank_relative_tolerance * float(singular[0]) if len(singular) else 0.0
    rank = int(np.count_nonzero(singular > cutoff)) if cutoff > 0 else 0
    return {
        "available": True,
        "local_numerical_rank": rank,
        "parameter_count": len(theta),
        "observable_count": len(base),
        "distinct_observed_start_band_gap_rows": len(design),
        "singular_values": singular.tolist(),
        "relative_singular_cutoff": settings.rank_relative_tolerance,
        "effective_absolute_cutoff": cutoff,
        "difference_schemes": schemes,
        "actual_scaled_difference_denominators": denominators,
        "step_in_scaled_rate_coordinates": settings.jacobian_step,
        "full_column_rank_at_point": rank == len(theta),
        "global_identification_established": False,
        "practical_identification_established": False,
        "observation_to_clinical_state_compatibility_established": False,
    }


def _compile_pairs(paths):
    """Counts are likelihood-sufficient at each gap, not independent sampling units."""
    grouped = {}
    for path in paths:
        for k in range(1, len(path.days)):
            gap = path.days[k] - path.days[k - 1]
            if gap not in grouped:
                grouped[gap] = np.zeros((3, 3), dtype=np.int64)
            grouped[gap][path.bands[k - 1], path.bands[k]] += 1
    gaps = np.asarray(sorted(grouped), dtype=float)
    return gaps, np.asarray([grouped[g] for g in gaps])


def _unreachable_pairs(paths, rates, structure):
    """Exact positive-rate graph support, independent of numerical magnitudes."""
    q = generator(rates, structure)
    reach = []
    for entry in range(3):
        support = {entry}
        for _ in range(3):
            support |= {j for i in tuple(support) for j in range(3) if q[i, j] > 0}
        reach.append(support)
    return sum(
        p.bands[k] not in reach[p.bands[k - 1]] for p in paths for k in range(1, len(p.days))
    )


def _spectral_kernels(q, gaps, edges, tolerance, selected=None, *, force_direct=False):
    """Vectorized exponential/Fréchet derivative, with direct fallback.

    For a well-conditioned eigensystem, d exp(Q t)[E] is V times the
    divided-difference exponential multiplied elementwise by V^-1 E V, times
    V^-1. Repeated eigenvalues use the continuous derivative t exp(lambda t).
    Defective/ill-conditioned systems use scipy's expm/expm_frechet instead.
    No approximation to the CTMC or visit design is introduced.
    """
    directions = []
    for i, j in edges:
        direction = np.zeros((3, 3))
        direction[i, j], direction[i, i] = 1, -1
        directions.append(direction)
    try:
        if force_direct:
            raise np.linalg.LinAlgError("Direct verification requested")
        eigenvalues, vectors = np.linalg.eig(q)
        if np.linalg.cond(vectors) * np.finfo(float).eps > tolerance:
            raise np.linalg.LinAlgError("Ill-conditioned eigensystem")
        inverse = np.linalg.inv(vectors)
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            exponentials = np.exp(gaps[:, None] * eigenvalues[None, :])
            matrices = np.einsum("ij,tj,jk->tik", vectors, exponentials, inverse)
            differences = np.empty((len(gaps), 3, 3), dtype=complex)
            for i in range(3):
                for j in range(3):
                    delta = eigenvalues[i] - eigenvalues[j]
                    if delta == 0:
                        differences[:, i, j] = gaps * exponentials[:, i]
                    elif delta.real >= 0:
                        differences[:, i, j] = (
                            exponentials[:, i] * (-np.expm1(-delta * gaps)) / delta
                        )
                    else:
                        differences[:, i, j] = exponentials[:, j] * np.expm1(delta * gaps) / delta
            derivatives = np.asarray(
                [
                    np.einsum(
                        "ij,tjk,kl->til",
                        vectors,
                        differences * (inverse @ e @ vectors)[None, :, :],
                        inverse,
                    )
                    for e in directions
                ]
            )
        for values in (matrices, derivatives):
            if not np.isfinite(values).all() or np.max(
                np.abs(values.imag), initial=0
            ) > tolerance * max(1, float(np.max(np.abs(values.real), initial=0))):
                raise np.linalg.LinAlgError("Unreliable spectral evaluation")
        matrices, derivatives = matrices.real, derivatives.real
        if (
            (matrices < -tolerance).any()
            or (matrices > 1 + tolerance).any()
            or any(abs(fsum(row) - 1) > tolerance for matrix in matrices for row in matrix)
        ):
            raise np.linalg.LinAlgError("Spectral probability check failed")
        # Absolute simplex checks cannot detect relative cancellation in tiny
        # reachable likelihood terms. Estimate reconstruction roundoff from
        # absolute factors and use direct kernels for affected gap matrices.
        budget = (
            3
            * np.finfo(float).eps
            * np.einsum("ij,tj,jk->tik", np.abs(vectors), np.abs(exponentials), np.abs(inverse))
        )
        # The factor reconstruction budget alone omits eigendecomposition error
        # in tiny eigenvector components and long-gap eigenvalue accumulation.
        eigen_budget = (
            3
            * np.finfo(float).eps
            * np.linalg.cond(vectors)
            * (1 + gaps * np.linalg.norm(q, ord=np.inf))
        )
        budget = np.maximum(budget, eigen_budget[:, None, None])
        relevant = np.ones(matrices.shape, dtype=bool) if selected is None else selected
        affected = np.any(relevant & (matrices * tolerance <= budget), axis=(1, 2))
        for index in np.flatnonzero(affected):
            gap = gaps[index]
            matrices[index] = expm(q * gap)
            for direction_index, direction in enumerate(directions):
                derivatives[direction_index, index] = expm_frechet(
                    q * gap, direction * gap, compute_expm=False
                )
        method = "hybrid_direct_expm_frechet_fallback" if affected.any() else "spectral_frechet"
        return matrices, derivatives, method
    except (np.linalg.LinAlgError, ValueError, FloatingPointError, OverflowError):
        matrices = np.asarray([expm(q * gap) for gap in gaps])
        derivatives = np.asarray(
            [
                [expm_frechet(q * gap, e * gap, compute_expm=False) for gap in gaps]
                for e in directions
            ]
        )
        return matrices, derivatives, "direct_expm_frechet_fallback"


def _compiled_likelihood(rates, structure, compiled, tolerance, *, direct=False):
    gaps, counts = compiled
    q = generator(rates, structure)
    # Graph-impossible transitions are exactly zero regardless of spectral
    # cancellation. Tiny positive roundoff must never create finite support.
    reachable = np.eye(3, dtype=bool)
    reachable |= q > 0
    for _ in range(3):
        reachable |= (reachable.astype(int) @ reachable.astype(int)) > 0
    impossible_counts = counts[:, ~reachable]
    if impossible_counts.any():
        return (
            -np.inf,
            np.zeros(len(EDGES[structure])),
            {
                "entries_zeroed": 0,
                "most_negative_entry": 0.0,
                "kernel_method": "exact_structural_zero_probability",
            },
        )
    with np.errstate(over="ignore", invalid="ignore"):
        arguments = gaps[:, None, None] * q[None, :, :]
    if not np.isfinite(arguments).all():
        raise ValueError("Matrix-exponential argument overflow")
    matrices, derivatives, method = _spectral_kernels(
        q, gaps, EDGES[structure], tolerance, selected=counts > 0, force_direct=direct
    )
    if (
        not np.isfinite(matrices).all()
        or not np.isfinite(derivatives).all()
        or (matrices < -tolerance).any()
        or (matrices > 1 + tolerance).any()
    ):
        raise ValueError("Compiled transition probability checks failed")
    negative = matrices < 0
    corrections = {
        "entries_zeroed": int(np.count_nonzero(negative)),
        "most_negative_entry": float(matrices.min()) if negative.any() else 0.0,
        "kernel_method": method,
    }
    matrices = np.maximum(matrices, 0)
    if any(abs(fsum(row) - 1) > tolerance for matrix in matrices for row in matrix):
        raise ValueError("Compiled transition conservation failed")
    selected = counts > 0
    impossible = selected & (matrices == 0)
    if impossible.any():
        for _, i, j in np.argwhere(impossible):
            support = {int(i)}
            for _ in range(3):
                support |= {k for source in tuple(support) for k in range(3) if q[source, k] > 0}
            if j in support:
                raise ValueError("Positive-support compiled transition underflow")
        return -np.inf, np.zeros(len(EDGES[structure])), corrections
    value = fsum(
        float(n) * log(float(p)) for n, p in zip(counts[selected], matrices[selected], strict=True)
    )
    gradient = np.asarray(
        [
            fsum(
                float(n * d / p)
                for n, d, p in zip(
                    counts[selected], derivative[selected], matrices[selected], strict=True
                )
            )
            for derivative in derivatives
        ]
    )
    if not isfinite(value) or not np.isfinite(gradient).all():
        raise ValueError("Compiled likelihood arithmetic failed")
    return value, gradient, corrections


def _projected_gradient(point, gradient, caps):
    """Box KKT residual, with exact boundary constraints and no rate floor."""
    residual = gradient.copy()
    residual[(point == 0) & (gradient > 0)] = 0
    residual[(point == caps) & (gradient < 0)] = 0
    return residual


def _finite_box_minimize(objective, initial, caps, settings):
    """Projected BFGS with finite-domain Armijo backtracking.

    A nonfinite trial is rejected; its placeholder gradient can never establish
    convergence. Only the independently calculated projected-gradient residual
    satisfies success. Small objective changes alone do not satisfy success.
    """
    point = initial.copy()
    value, gradient = objective(point)
    inverse = np.eye(len(point))
    status, iteration, stagnations = "iteration_limit", 0, 0
    for iteration in range(settings.optimizer_maxiter + 1):
        if not isfinite(value) or not np.isfinite(gradient).all():
            status = "nonfinite_initial_objective"
            break
        residual = _projected_gradient(point, gradient, caps)
        norm = float(np.max(np.abs(residual), initial=0))
        if norm <= settings.optimizer_gtol:
            status = "projected_gradient_converged"
            break
        if iteration == settings.optimizer_maxiter:
            break
        try:
            hessian = np.linalg.inv(inverse)
            hessian = (hessian + hessian.T) / 2
            if not np.isfinite(hessian).all() or np.linalg.eigvalsh(hessian).min() <= 0:
                raise np.linalg.LinAlgError
            quadratic = minimize(
                lambda step, gradient=gradient, hessian=hessian: (
                    gradient @ step + 0.5 * step @ hessian @ step,
                    gradient + hessian @ step,
                ),
                np.zeros(len(point)),
                method="L-BFGS-B",
                jac=True,
                bounds=list(zip(-point, caps - point, strict=True)),
                options={
                    "maxiter": 100,
                    "ftol": settings.optimizer_ftol,
                    "gtol": settings.optimizer_gtol,
                },
            )
            # This convex finite quadratic proposes a direction only. Its own
            # convergence flag is never evidence of likelihood convergence.
            direction = np.clip(point + quadratic.x, 0, caps) - point
        except (ValueError, FloatingPointError, OverflowError, np.linalg.LinAlgError):
            inverse = np.eye(len(point))
            direction = np.clip(point - residual, 0, caps) - point
        if not np.isfinite(direction).all() or gradient @ direction >= 0:
            inverse = np.eye(len(point))
            direction = np.clip(point - residual, 0, caps) - point
        accepted = False
        for backtrack in range(60):
            candidate = np.clip(point + (0.5**backtrack) * direction, 0, caps)
            step = candidate - point
            if not np.any(step):
                break
            trial_value, trial_gradient = objective(candidate)
            if (
                isfinite(trial_value)
                and np.isfinite(trial_gradient).all()
                and gradient @ step < 0
                and trial_value
                <= (
                    value
                    + 1e-4 * (gradient @ step)
                    + 8 * np.finfo(float).eps * max(1, abs(value), abs(trial_value))
                )
            ):
                accepted = True
                break
        if not accepted:
            # One reset allows an unreliable quasi-Newton direction to recover.
            if not np.array_equal(inverse, np.eye(len(point))):
                inverse = np.eye(len(point))
                continue
            status = "finite_descent_line_search_failed"
            break
        change = trial_gradient - gradient
        curvature = float(change @ step)
        if curvature > np.finfo(float).eps * np.linalg.norm(change) * np.linalg.norm(step):
            rho = 1 / curvature
            transform = np.eye(len(point)) - rho * np.outer(step, change)
            inverse = transform @ inverse @ transform.T + rho * np.outer(step, step)
        else:
            inverse = np.eye(len(point))
        relative_change = abs(trial_value - value) / max(1, abs(value), abs(trial_value))
        stagnations = stagnations + 1 if relative_change <= settings.optimizer_ftol else 0
        point, value, gradient = candidate, trial_value, trial_gradient
    residual_norm = (
        float(np.max(np.abs(_projected_gradient(point, gradient, caps)), initial=0))
        if isfinite(value) and np.isfinite(gradient).all()
        else None
    )
    return {
        "x": point,
        "success": status == "projected_gradient_converged",
        "status": status,
        "iterations": iteration,
        "projected_gradient_norm": residual_norm,
        "small_objective_change_iterations": stagnations,
    }


def _search(paths, settings, *, fixed=None):
    size = len(EDGES[settings.structure])
    free = tuple(i for i in range(size) if fixed is None or i != fixed[0])
    caps = np.asarray(settings.rate_upper_bounds) * settings.day_scale
    starts = settings.initial_rates
    records, candidates = [], []
    errors = {"numerical_evaluations_failed": 0, "zero_probability_evaluations": 0}
    compiled = _compile_pairs(paths)

    def expand(point):
        theta = np.zeros(size)
        theta[list(free)] = point
        if fixed is not None:
            theta[fixed[0]] = fixed[1] * settings.day_scale
        return theta / settings.day_scale

    def objective(point):
        try:
            value, gradient, _ = _compiled_likelihood(
                expand(point), settings.structure, compiled, settings.probability_tolerance
            )
            if value == -np.inf:
                errors["zero_probability_evaluations"] += 1
                return np.inf, np.full(len(free), np.nan)
            return -value, -gradient[list(free)] / settings.day_scale
        except (ValueError, FloatingPointError, OverflowError, np.linalg.LinAlgError):
            errors["numerical_evaluations_failed"] += 1
            return np.inf, np.full(len(free), np.nan)

    for start in starts:
        try:
            result = _finite_box_minimize(
                objective,
                np.asarray(start)[list(free)] * settings.day_scale,
                caps[list(free)],
                settings,
            )
            rates = expand(result["x"])
            value, gradient, corrections = _compiled_likelihood(
                rates, settings.structure, compiled, settings.probability_tolerance, direct=True
            )
            verified_norm = (
                float(
                    np.max(
                        np.abs(
                            _projected_gradient(
                                result["x"],
                                -gradient[list(free)] / settings.day_scale,
                                caps[list(free)],
                            )
                        ),
                        initial=0,
                    )
                )
                if isfinite(value)
                else None
            )
            finite = isfinite(value) and bool(np.isfinite(rates).all())
            success = (
                bool(result["success"]) and finite and verified_norm <= settings.optimizer_gtol
            )
            records.append(
                {
                    "converged": success,
                    "optimizer_status": result["status"]
                    if success or not result["success"]
                    else "direct_gradient_verification_failed",
                    "iterations": result["iterations"],
                    "projected_gradient_norm": verified_norm,
                    "search_gradient_norm": result["projected_gradient_norm"],
                    "direct_likelihood_gradient_verified": success,
                    "small_objective_change_iterations": result[
                        "small_objective_change_iterations"
                    ],
                    "rates": rates.tolist() if finite else None,
                    "log_likelihood": _log_value(value) if finite or value == -np.inf else None,
                }
            )
            if success:
                candidates.append((value, rates, corrections))
        except (ValueError, FloatingPointError, OverflowError, np.linalg.LinAlgError):
            records.append(
                {
                    "converged": False,
                    "optimizer_status": "numerical_optimizer_failure",
                    "iterations": None,
                    "projected_gradient_norm": None,
                    "rates": None,
                    "log_likelihood": None,
                }
            )
    best = max(candidates, key=lambda item: item[0]) if candidates else None
    return best, records, errors


def fit_ctmc(paths, settings: FitSettings, *, identification_diagnostics=True) -> dict:
    """Explicit bounded multistart MLE; failed or unidentified fits remain visible."""
    paths = _paths(paths)
    if type(settings) is not FitSettings or type(identification_diagnostics) is not bool:
        raise ValueError("Explicit fitting settings and diagnostic choice are required")
    summary = transition_summary(paths)
    report = {
        "kind": "ctmc",
        "structure": settings.structure,
        "parameter_edges": [list(edge) for edge in EDGES[settings.structure]],
        "fit_performed": False,
        "rates": None,
        "rate_unit": "per_source_day",
        "log_likelihood": None,
        "settings": asdict(settings),
        "source_support": summary,
        "search_cap_is_clinical_bound": False,
        "clinical_fit_performed": False,
        "engine_activation_allowed": False,
        "identification": None,
        "zero_rate_indices": [],
        "search_cap_indices": [],
    }
    if not summary["adjacent_observation_pairs"]:
        return {**report, "failure": "no_rate_informative_observation_pairs", "multistarts": []}
    best, starts, errors = _search(paths, settings)
    report.update(multistarts=starts, evaluation_failures=errors)
    if best is None:
        return {**report, "failure": "no_converged_finite_multistart"}
    value, rates, corrections = best
    identification = None
    if identification_diagnostics:
        try:
            identification = design_identifiability(paths, rates, settings)
        except (ValueError, FloatingPointError, OverflowError, np.linalg.LinAlgError):
            identification = {
                "available": False,
                "failure": "numerical_identification_failure",
                "full_column_rank_at_point": None,
                "local_numerical_rank": None,
            }
    return {
        **report,
        "fit_performed": True,
        "failure": None,
        "rates": rates.tolist(),
        "log_likelihood": _log_value(value),
        "identification": identification,
        "zero_rate_indices": [i for i, x in enumerate(rates) if x == 0],
        "search_cap_indices": [
            i
            for i, (x, cap) in enumerate(zip(rates, settings.rate_upper_bounds, strict=False))
            if x >= cap
        ],
        "roundoff_corrections": corrections,
        "optimizer_convergence_is_identification": False,
    }


def fit_iid(paths) -> dict:
    """Independent post-first-observation category null; first bands are conditioned on."""
    paths = _paths(paths)
    counts = [sum(p.bands[1:].count(b) for p in paths) for b in range(3)]
    n = sum(counts)
    if not n:
        return {
            "kind": "iid",
            "fit_performed": False,
            "probabilities": None,
            "failure": "no_post_first_observations",
        }
    probabilities = [x / n for x in counts]
    value = fsum(x * log(p) for x, p in zip(counts, probabilities, strict=False) if x)
    return {
        "kind": "iid",
        "fit_performed": True,
        "probabilities": probabilities,
        "post_first_counts": counts,
        "log_likelihood": _log_value(value),
        "clinical_fit_performed": False,
        "engine_activation_allowed": False,
    }


def no_switching_null(paths) -> dict:
    """Exact deterministic persistence, without a positive probability floor."""
    paths = _paths(paths)
    impossible = sum(any(b != p.bands[0] for b in p.bands[1:]) for p in paths)
    return {
        "kind": "no_switching",
        "fit_performed": False,
        "impossible_paths": impossible,
        "log_likelihood": _log_value(-np.inf if impossible else 0.0),
        "clinical_fit_performed": False,
        "engine_activation_allowed": False,
    }


def _prediction(model, gap, previous, tolerance):
    if not isinstance(model, Mapping):
        raise ValueError("A declared fitted or null laboratory model is required")
    kind = model.get("kind")
    if kind == "ctmc":
        rates = _rates(model.get("rates"), model.get("structure"))
        matrix = transition_matrix(rates, model["structure"], gap, probability_tolerance=tolerance)
        q, support = generator(rates, model["structure"]), {previous}
        if gap > 0:
            for _ in range(3):
                support |= {j for i in tuple(support) for j in range(3) if q[i, j] > 0}
        if any(matrix[previous, j] == 0 for j in support):
            raise ValueError("Positive-support prediction underflow")
        return matrix[previous]
    if kind == "iid":
        p = _vector(model.get("probabilities"), length=3, nonnegative=True)
        if any(x > 1 for x in p) or abs(fsum(p) - 1) > tolerance:
            raise ValueError("IID probabilities must lie on the simplex")
        return np.asarray(p)
    if kind == "no_switching":
        return np.eye(3)[previous]
    raise ValueError("Unsupported laboratory prediction model")


def score_predictions(paths, model, *, probability_tolerance) -> dict:
    """Held-out scores with two conditioning modes and explicit equal-label weights.

    One-step predictions condition on the previous observed band. First-only
    predictions condition solely on the first band and elapsed time, without
    updating on intermediate held-out outcomes. The latter marginal scores are
    not a joint path likelihood. No score is floored to hide impossible events.
    """
    paths = _paths(paths)
    tolerance = _tolerance(probability_tolerance)
    _prediction(model, 0, 0, tolerance)
    result = {
        "total_label_paths": len(paths),
        "scored_repeat_paths": sum(len(p.days) > 1 for p in paths),
        "single_observation_paths": sum(len(p.days) == 1 for p in paths),
        "modes": {},
    }
    for mode in ("one_step", "first_only"):
        path_logs, path_briers, steps, impossible = [], [], [], 0
        for path in paths:
            logs, briers = [], []
            for k in range(1, len(path.days)):
                start = k - 1 if mode == "one_step" else 0
                probabilities = _prediction(
                    model, path.days[k] - path.days[start], path.bands[start], tolerance
                )
                p = float(probabilities[path.bands[k]])
                logs.append(log(p) if p else -np.inf)
                impossible += int(p == 0)
                briers.append(
                    fsum(
                        (float(v) - int(j == path.bands[k])) ** 2
                        for j, v in enumerate(probabilities)
                    )
                )
            if logs:
                path_logs.append(-np.inf if -np.inf in logs else fsum(logs))
                path_briers.append(fsum(briers))
                steps.append(len(logs))
        count = sum(steps)
        total_log = -np.inf if -np.inf in path_logs else fsum(path_logs)
        equal_log = (
            -np.inf
            if -np.inf in path_logs
            else fsum(x / n for x, n in zip(path_logs, steps, strict=False)) / len(steps)
            if steps
            else None
        )
        result["modes"][mode] = {
            "scored_observations": count,
            "zero_probability_observations": impossible,
            "transition_weighted_mean_log_score": _log_value(total_log / count) if count else None,
            "equal_label_mean_log_score": _log_value(equal_log) if steps else None,
            "transition_weighted_mean_brier": fsum(path_briers) / count if count else None,
            "equal_label_mean_brier": fsum(x / n for x, n in zip(path_briers, steps, strict=False))
            / len(steps)
            if steps
            else None,
            "sum_log_score": _log_value(total_log) if count else None,
            "sum_is_joint_conditional_path_log_likelihood": mode == "one_step",
        }
    return result


def profile_rate(
    paths, fitted: Mapping, settings: FitSettings, rate_index: int, grid, *, support_cutoff
) -> dict:
    """Reoptimize nuisance rates at each supplied grid point; expose open limits.

    The caller may supply an interior-asymptotic likelihood-ratio reference.
    It is not valid automatically at zero boundaries, caps, weak identification
    or failed points. No interpolated finite confidence interval is manufactured.
    """
    paths = _paths(paths)
    if (
        type(settings) is not FitSettings
        or type(rate_index) is not int
        or not 0 <= rate_index < len(EDGES[settings.structure])
    ):
        raise ValueError("Invalid profile settings or rate index")
    grid = _vector(grid, nonnegative=True)
    cutoff = _number(support_cutoff, positive=True)
    cap = settings.rate_upper_bounds[rate_index]
    if (
        not grid
        or any(x > cap for x in grid)
        or any(y <= x for x, y in zip(grid, grid[1:], strict=False))
    ):
        raise ValueError("Profile grid must be strictly increasing within computational bounds")
    if (
        not isinstance(fitted, Mapping)
        or fitted.get("fit_performed") is not True
        or fitted.get("kind") != "ctmc"
        or fitted.get("structure") != settings.structure
    ):
        raise ValueError("Profiles require a successful matching CTMC fit")
    rates = _rates(fitted.get("rates"), settings.structure)
    if any(x > c for x, c in zip(rates, settings.rate_upper_bounds, strict=False)):
        raise ValueError("Fitted rates exceed computational bounds")
    baseline = _likelihood(paths, rates, settings.structure, settings.probability_tolerance)[0]
    if not isfinite(baseline):
        raise ValueError("Profile baseline must be finite")
    grid = tuple(sorted({*grid, rates[rate_index]}))
    points, accepted, better = [], [], False
    for value in grid:
        best, starts, errors = _search(paths, settings, fixed=(rate_index, value))
        if best is None:
            maximal_rates = list(settings.rate_upper_bounds)
            maximal_rates[rate_index] = value
            impossible = _unreachable_pairs(paths, maximal_rates, settings.structure) > 0
            points.append(
                {
                    "rate": value,
                    "converged": False,
                    "structurally_impossible_for_all_nuisance_rates": impossible,
                    "log_likelihood": _log_value(-np.inf) if impossible else None,
                    "deviance_from_fitted": None,
                    "deviance_status": "positive_infinity" if impossible else "unavailable",
                    "multistarts": starts,
                    "evaluation_failures": errors,
                }
            )
            continue
        likelihood, nuisance, _ = best
        deviance = 2 * (baseline - likelihood)
        better |= deviance < -settings.probability_tolerance
        if deviance <= cutoff:
            accepted.append(value)
        points.append(
            {
                "rate": value,
                "converged": True,
                "log_likelihood": _log_value(likelihood),
                "deviance_from_fitted": deviance,
                "rates": nuisance.tolist(),
                "nuisance_zero_indices": [
                    i for i, r in enumerate(nuisance) if i != rate_index and r == 0
                ],
                "nuisance_cap_indices": [
                    i
                    for i, (r, c) in enumerate(
                        zip(nuisance, settings.rate_upper_bounds, strict=False)
                    )
                    if i != rate_index and r >= c
                ],
                "evaluation_failures": errors,
            }
        )
    failed = sum(
        not p["converged"] and not p.get("structurally_impossible_for_all_nuisance_rates", False)
        for p in points
    )
    zero = (
        any(r == 0 for r in rates)
        or (0.0 in accepted)
        or any(p.get("nuisance_zero_indices") for p in points)
    )
    cap_hit = (
        any(x >= c for x, c in zip(rates, settings.rate_upper_bounds, strict=False))
        or (cap in accepted)
        or any(p.get("nuisance_cap_indices") for p in points)
    )
    lower_open = bool(accepted) and grid[0] in accepted
    upper_open = bool(accepted) and grid[-1] in accepted
    return {
        "rate_index": rate_index,
        "rate_unit": "per_source_day",
        "points": points,
        "support_cutoff": cutoff,
        "support_reference": "caller_declared_interior_asymptotic_only",
        "supported_grid_rates": accepted,
        "finite_confidence_interval": None,
        "lower_grid_limit_open": lower_open,
        "upper_grid_limit_open": upper_open,
        "zero_boundary_supported_or_fitted": zero,
        "computational_cap_hit_or_supported": cap_hit,
        "failed_grid_points": failed,
        "structural_zero_probability_grid_points": sum(
            p.get("structurally_impossible_for_all_nuisance_rates", False) for p in points
        ),
        "baseline_improved_by_profile_search": bool(better),
        "regular_interior_interpretation_eligible": not (
            zero or cap_hit or failed or lower_open or upper_open or better
        ),
        "interior_reference_requires_correctly_specified_independent_label_model": True,
        "clinical_confidence_interval": False,
    }


def _sample_summary(rows, levels):
    if len(rows) < 2:
        return {
            "available": False,
            "successful_draws": len(rows),
            "covariance": None,
            "quantiles": None,
        }
    matrix = np.asarray(rows, dtype=float)
    mean = np.asarray([fsum(matrix[:, j]) / len(rows) for j in range(matrix.shape[1])])
    centered = matrix - mean
    covariance = [
        [
            fsum(float(row[i] * row[j]) for row in centered) / (len(rows) - 1)
            for j in range(matrix.shape[1])
        ]
        for i in range(matrix.shape[1])
    ]
    quantiles = np.quantile(matrix, levels, axis=0).tolist()
    if not np.isfinite(covariance).all() or not np.isfinite(quantiles).all():
        raise ValueError("Bootstrap summary is nonfinite")
    return {
        "available": True,
        "successful_draws": len(rows),
        "covariance": covariance,
        "quantile_levels": list(levels),
        "quantiles": quantiles,
    }


def paired_path_bootstrap(
    paths,
    configurations: Mapping[str, FitSettings],
    *,
    repetitions: int,
    seed: int,
    quantile_levels: Sequence[float],
    evaluation_paths=None,
    include_iid=True,
) -> dict:
    """Whole-path resampling with paired models and retained failed/cap/boundary draws.

    Evaluation labels, when provided, are independently resampled as whole paths
    once per replicate and shared by all models. Successful-draw summaries are
    explicitly conditional on convergence; no failed replicate is redrawn.
    """
    paths = _paths(paths)
    evaluation = _paths(evaluation_paths) if evaluation_paths is not None else None
    if (
        not isinstance(configurations, Mapping)
        or not configurations
        or any(
            type(k) is not str or not k or type(v) is not FitSettings
            for k, v in configurations.items()
        )
    ):
        raise ValueError("Named explicit CTMC configurations are required")
    if "iid" in configurations or type(include_iid) is not bool:
        raise ValueError("Invalid bootstrap model names or IID choice")
    if type(repetitions) is not int or repetitions < 2 or type(seed) is not int or seed < 0:
        raise ValueError("Explicit repetition count and nonnegative seed are required")
    levels = _vector(quantile_levels)
    if (
        not levels
        or any(not 0 <= q <= 1 for q in levels)
        or any(b <= a for a, b in zip(levels, levels[1:], strict=False))
    ):
        raise ValueError("Quantile levels must be ordered probabilities")
    names = tuple(configurations)
    rate_coordinates = [
        {"model": name, "rate_index": i}
        for name in names
        for i in range(len(EDGES[configurations[name].structure]))
    ]
    model_rows = {name: [] for name in names}
    joint_rows, score_differences, records = [], {name: [] for name in names}, []
    rng = np.random.default_rng(seed)
    for iteration in range(repetitions):
        sampled = tuple(paths[i] for i in rng.integers(0, len(paths), size=len(paths)))
        heldout = (
            tuple(evaluation[i] for i in rng.integers(0, len(evaluation), size=len(evaluation)))
            if evaluation is not None
            else None
        )
        fits, failures = {}, {}
        for name, settings in configurations.items():
            try:
                fits[name] = fit_ctmc(sampled, settings, identification_diagnostics=True)
                if not fits[name]["fit_performed"]:
                    failures[name] = fits[name]["failure"]
            except (ValueError, FloatingPointError, OverflowError, np.linalg.LinAlgError):
                failures[name] = "numerical_fit_failure"
        iid = fit_iid(sampled) if include_iid else None
        if iid is not None and not iid["fit_performed"]:
            failures["iid"] = iid["failure"]
        record = {
            "replicate": iteration,
            "failures": failures,
            "models": {},
            "predictive_score_differences_vs_iid": {},
            "prediction_status": {},
        }
        for name in names:
            fit = fits.get(name)
            if name in failures or fit is None:
                record["models"][name] = {"fit_performed": False}
                continue
            model_rows[name].append(fit["rates"])
            record["models"][name] = {
                "fit_performed": True,
                "rates": fit["rates"],
                "zero_rate_indices": fit["zero_rate_indices"],
                "search_cap_indices": fit["search_cap_indices"],
                "identification": fit.get("identification"),
            }
            if heldout is not None and iid is not None and iid["fit_performed"]:
                try:
                    score = score_predictions(
                        heldout,
                        fit,
                        probability_tolerance=configurations[name].probability_tolerance,
                    )
                    null = score_predictions(
                        heldout,
                        iid,
                        probability_tolerance=configurations[name].probability_tolerance,
                    )
                    differences = []
                    detail = {}
                    for mode in ("one_step", "first_only"):
                        detail[mode] = {}
                        for weighting in ("equal_label", "transition_weighted"):
                            key = f"{weighting}_mean_log_score"
                            a, b = score["modes"][mode][key], null["modes"][mode][key]
                            if (
                                a is None
                                or b is None
                                or a["status"] != "finite"
                                or b["status"] != "finite"
                            ):
                                detail[mode][weighting] = {
                                    "value": None,
                                    "status": "unavailable_or_nonfinite_difference",
                                }
                            else:
                                difference = a["value"] - b["value"]
                                detail[mode][weighting] = {"value": difference, "status": "finite"}
                                differences.append(difference)
                        for weighting in ("equal_label", "transition_weighted"):
                            key = f"{weighting}_mean_brier"
                            a, b = score["modes"][mode][key], null["modes"][mode][key]
                            if a is None or b is None:
                                detail[mode][f"{weighting}_brier"] = {
                                    "value": None,
                                    "status": "unavailable",
                                }
                            else:
                                difference = a - b
                                detail[mode][f"{weighting}_brier"] = {
                                    "value": difference,
                                    "status": "finite",
                                }
                                differences.append(difference)
                    record["predictive_score_differences_vs_iid"][name] = detail
                    record["prediction_status"][name] = (
                        "performed_finite"
                        if len(differences) == 8
                        else "nonfinite_or_unavailable_scores"
                    )
                    if len(differences) == 8:
                        score_differences[name].append(differences)
                except (ValueError, FloatingPointError, OverflowError):
                    record["predictive_score_differences_vs_iid"][name] = {
                        "failure": "numerical_prediction_failure"
                    }
                    record["prediction_status"][name] = "numerical_prediction_failure"
        if all(name not in failures for name in names):
            joint_rows.append([x for name in names for x in fits[name]["rates"]])
        records.append(record)
    return {
        "repetitions_requested": repetitions,
        "repetitions_attempted": len(records),
        "seed": seed,
        "unit_resampled": "whole_label_path",
        "failed_draws_redrawn": False,
        "within_path_dependence_preserved": True,
        "independence_across_labels_assumed": True,
        "evaluation_resampled_separately_and_paired_across_models": evaluation is not None,
        "replicates": records,
        "rate_coordinates": rate_coordinates,
        "joint_rate_summary": _sample_summary(joint_rows, levels),
        "per_model_rate_summaries": {
            name: _sample_summary(rows, levels) for name, rows in model_rows.items()
        },
        "predictive_difference_coordinates": [
            {
                "mode": mode,
                "metric": metric,
                "weighting": weight,
                "higher_is_better": metric == "log_score",
            }
            for mode in ("one_step", "first_only")
            for metric in ("log_score", "brier")
            for weight in ("equal_label", "transition_weighted")
        ],
        "predictive_difference_summaries": {
            name: _sample_summary(rows, levels) for name, rows in score_differences.items()
        },
        "summaries_conditioned_on_successful_finite_draws": True,
        "rank_deficient_draws_excluded_from_covariance": False,
        "selection_measurement_or_transport_uncertainty_included": False,
        "clinical_fit_performed": False,
        "engine_activation_allowed": False,
    }
