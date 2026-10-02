"""Declared, validation-only CTMC observation kernels, separate from the engine.

Row generators and reciprocal-year hazards produce probabilities via expm(Q t).
Linked observations share one forward path. First-entry paths use a killed
process from entry, including before earlier panel observations. No laboratory
threshold, biological-state mapping, empirical fit or causal effect is inferred.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from math import exp, isfinite, log
from numbers import Real

import numpy as np
from scipy.linalg import expm


def _number(value, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real number") from error
    if not isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


def _array(value, name: str, ndim: int) -> np.ndarray:
    if isinstance(value, np.ma.MaskedArray):
        raise ValueError(f"{name} cannot silently discard a mask")

    def reject_nested_bools(item):
        if isinstance(item, (bool, np.bool_)):
            raise ValueError(f"{name} cannot coerce boolean values to numbers")
        if type(item) in (tuple, list):
            for child in item:
                reject_nested_bools(child)

    reject_nested_bools(value)
    try:
        raw = np.asarray(value)
        if raw.ndim != ndim or raw.dtype.kind not in "iuf":
            raise ValueError
        result = raw.astype(float, copy=True)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric {ndim}-dimensional array") from error
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must contain only finite values")
    return result


def _tolerance(value: float) -> float:
    value = _number(value, "tolerance")
    if not 0 < value < 1:
        raise ValueError("tolerance must be explicitly supplied between zero and one")
    return value


MAX_STOCHASTIC_ROUNDOFF_TOLERANCE = 1e-10


def _stochastic_tolerance(value: float) -> float:
    """Bound numerical mass checks separately from relative Jacobian rank cutoffs.

    The ceiling preserves the existing registered CTMC software allowance. It
    cannot be enlarged to admit empirical mass errors. Accepted input deviations
    are not normalized; an evaluated probability above one still fails.
    """
    value = _tolerance(value)
    if value > MAX_STOCHASTIC_ROUNDOFF_TOLERANCE:
        raise ValueError("Stochastic roundoff tolerance must be at most 1e-10")
    return value


def _scaled_generator_row_deviations(q: np.ndarray) -> np.ndarray:
    """Dimensionless conservation error relative to each row's hazard scale.

    Scaling before summation avoids an absolute probability allowance hiding a
    defective tiny-rate generator, and avoids overflow for finite large rates.
    A zero-rate row has exactly zero error. No generator entry is changed.
    """
    scale = np.max(np.abs(q), axis=1)
    scaled = np.divide(q, scale[:, None], out=np.zeros_like(q), where=scale[:, None] != 0)
    return scaled.sum(axis=1)


@dataclass(frozen=True)
class StateSpace:
    """Declared labels/history; death has no required live diagnosis history."""

    labels: tuple[str, ...]
    diagnosis_history: tuple[bool | None, ...]
    death_index: int

    def __post_init__(self):
        if type(self.labels) not in (tuple, list) or type(self.diagnosis_history) not in (
            tuple,
            list,
        ):
            raise ValueError("State labels and history must be finite sequences")
        labels, history = tuple(self.labels), tuple(self.diagnosis_history)
        if (
            len(labels) < 2
            or any(
                type(label) is not str or not label or label != label.strip() for label in labels
            )
            or len(set(labels)) != len(labels)
            or len(history) != len(labels)
            or type(self.death_index) is not int
            or not 0 <= self.death_index < len(labels)
        ):
            raise ValueError("Invalid state labels, dimensions or death index")
        if history[self.death_index] is not None or any(
            type(item) is not bool for i, item in enumerate(history) if i != self.death_index
        ):
            raise ValueError("Live history must be boolean; only death history is None")
        object.__setattr__(self, "labels", labels)
        object.__setattr__(self, "diagnosis_history", history)


@dataclass(frozen=True)
class RateSegment:
    """Known half-open time segment in years; snapshots numeric generator inputs."""

    start_year: float
    end_year: float
    generator: tuple[tuple[float, ...], ...]

    def __post_init__(self):
        start = _number(self.start_year, "segment start", nonnegative=True)
        end = _number(self.end_year, "segment end", nonnegative=True)
        if end <= start:
            raise ValueError("A rate segment must have positive duration")
        q = _array(self.generator, "generator", 2)
        object.__setattr__(self, "start_year", start)
        object.__setattr__(self, "end_year", end)
        object.__setattr__(self, "generator", tuple(tuple(row) for row in q.tolist()))


@dataclass(frozen=True)
class PanelObservation:
    """Declared category or set-valued/coarsened likelihood vector, not raw glucose."""

    time_year: float
    emission: tuple[float, ...]
    kind: str

    def __post_init__(self):
        time = _number(self.time_year, "observation time", nonnegative=True)
        weights = _array(self.emission, "emission", 1)
        if not len(weights) or (weights < 0).any() or (weights > 1).any():
            raise ValueError("Categorical observation weights must be between zero and one")
        if self.kind not in ("category", "coarsened"):
            raise ValueError("Observation kind must explicitly declare category or coarsening")
        object.__setattr__(self, "time_year", time)
        object.__setattr__(self, "emission", tuple(weights.tolist()))


@dataclass(frozen=True)
class TerminalObservation:
    """Distinct probability/density modes; a panel end does not assert being alive."""

    kind: str
    time_year: float
    event: str | None = None
    interval_start_year: float | None = None
    endpoint_emission: tuple[float, ...] | None = None

    def __post_init__(self):
        time = _number(self.time_year, "terminal time", nonnegative=True)
        kinds = (
            "panel",
            "exact_first_entry",
            "interval_first_entry",
            "right_censor",
            "non_event_endpoint",
        )
        if self.kind not in kinds:
            raise ValueError("Unsupported or unknown terminal observation mode")
        event_mode = self.kind in ("exact_first_entry", "interval_first_entry")
        if event_mode != (type(self.event) is str and bool(self.event)):
            raise ValueError("First-entry modes require exactly one declared event name")
        if not event_mode and self.event is not None:
            raise ValueError("A non-event mode cannot declare an event")
        if self.kind == "interval_first_entry":
            start = _number(self.interval_start_year, "interval start", nonnegative=True)
            if start > time:
                raise ValueError("Event interval must be ordered")
            object.__setattr__(self, "interval_start_year", start)
        elif self.interval_start_year is not None:
            raise ValueError("Only interval events may supply an interval start")
        if self.kind == "non_event_endpoint":
            weights = _array(self.endpoint_emission, "endpoint emission", 1)
            if not len(weights) or (weights < 0).any() or (weights > 1).any():
                raise ValueError("Endpoint weights must be between zero and one")
            object.__setattr__(self, "endpoint_emission", tuple(weights.tolist()))
        elif self.endpoint_emission is not None:
            raise ValueError("Only non-event endpoints may declare an endpoint vector")
        object.__setattr__(self, "time_year", time)


@dataclass(frozen=True)
class SoftwareObservationContract:
    """Required assumptions for mathematical evaluation, never clinical eligibility."""

    time_unit: str
    observation_timing: str
    missingness: str
    selection: str
    treatment: str
    stopping: str

    def __post_init__(self):
        choices = {
            "time_unit": ("years",),
            "observation_timing": ("exogenous", "ignorable_conditional"),
            "missingness": ("no_missing", "ignorable_conditional", "explicit_coarsening"),
            "selection": ("synthetic_fixed_cohort", "conditioned_on_selected_cohort"),
            "treatment": ("held_fixed", "piecewise_declared"),
            "stopping": (
                "observation_sequence_only",
                "administrative_observation_end",
                "independent_right_censoring",
                "first_entry_ascertainment",
                "non_event_assessment",
            ),
        }
        if any(
            type(getattr(self, key)) is not str or getattr(self, key) not in values
            for key, values in choices.items()
        ):
            raise ValueError(
                "Every observation assumption must be explicitly declared; unknowns are unsupported"
            )


def validate_generator(space: StateSpace, generator, *, tolerance: float) -> np.ndarray:
    """Validate row sums, finite hazards/year, absorbing death and retained history."""
    tolerance = _stochastic_tolerance(tolerance)
    if type(space) is not StateSpace:
        raise ValueError("A declared StateSpace is required")
    q = _array(generator, "generator", 2)
    size = len(space.labels)
    if q.shape != (size, size):
        raise ValueError("Generator dimensions must match the state space")
    off = q.copy()
    np.fill_diagonal(off, 0)
    if (
        (off < 0).any()
        or (np.diag(q) > 0).any()
        or not np.allclose(_scaled_generator_row_deviations(q), 0, atol=tolerance, rtol=0)
    ):
        raise ValueError("Row generator requires nonnegative off-diagonals and zero row sums")
    if (q[space.death_index] != 0).any():
        raise ValueError("Death must be exactly absorbing")
    for i, source_history in enumerate(space.diagnosis_history):
        for j, target_history in enumerate(space.diagnosis_history):
            if source_history is True and target_history is False and q[i, j] != 0:
                raise ValueError("A live transition cannot erase diagnosed history")
    return q


def validate_categorical_emissions(matrix, *, state_count: int, tolerance: float) -> np.ndarray:
    """States by mutually exclusive categories; each row is a probability vector."""
    tolerance = _stochastic_tolerance(tolerance)
    values = _array(matrix, "categorical emissions", 2)
    if (
        type(state_count) is not int
        or state_count < 1
        or values.shape[0] != state_count
        or values.shape[1] < 1
    ):
        raise ValueError("Invalid categorical emission dimensions")
    if (
        (values < 0).any()
        or (values > 1).any()
        or not np.allclose(values.sum(axis=1), 1, atol=tolerance, rtol=0)
    ):
        raise ValueError("Categorical emission rows must sum to one")
    return values


def _exponential(
    matrix: np.ndarray, duration: float, tolerance: float, *, killed: bool, corrections=None
) -> np.ndarray:
    """Correct negative exponential roundoff only within the declared tolerance.

    Generator entries are never repaired. Errors outside tolerance, mass failures
    and nonfinite outputs fail instead of being clipped into an accepted model.
    """
    values = expm(matrix * duration)
    if not np.isfinite(values).all() or (values < -tolerance).any() or (values > 1).any():
        raise FloatingPointError("Matrix exponential failed numerical probability checks")
    negative = values < 0
    if corrections is not None and negative.any():
        corrections["entries_zeroed"] += int(np.count_nonzero(negative))
        corrections["most_negative_entry"] = min(
            corrections["most_negative_entry"], float(values.min())
        )
    values = np.maximum(values, 0)
    sums = values.sum(axis=1)
    if (sums > 1 + tolerance).any() or (
        not killed and not np.allclose(sums, 1, atol=tolerance, rtol=0)
    ):
        raise FloatingPointError("Matrix exponential failed numerical mass checks")
    return values


def transition_matrix(
    space: StateSpace, generator, duration_years: float, *, tolerance: float
) -> np.ndarray:
    """Full endpoint occupancy, including death; unlike a killed first-entry kernel."""
    tolerance = _stochastic_tolerance(tolerance)
    q = validate_generator(space, generator, tolerance=tolerance)
    duration = _number(duration_years, "duration in years", nonnegative=True)
    return _exponential(q, duration, tolerance, killed=False)


def _targets(
    space: StateSpace, targets: Mapping[str, Sequence[int]]
) -> tuple[dict[str, tuple[int, ...]], tuple[int, ...]]:
    if not isinstance(targets, Mapping) or not targets:
        raise ValueError("Killed paths require explicit competing first-entry targets")
    groups, used = {}, set()
    for name, indices in targets.items():
        if type(name) is not str or not name or type(indices) not in (list, tuple) or not indices:
            raise ValueError("Invalid first-entry event name or target sequence")
        indices = tuple(indices)
        if any(
            type(i) is not int or not 0 <= i < len(space.labels) or i in used for i in indices
        ) or len(set(indices)) != len(indices):
            raise ValueError("First-entry target groups must be disjoint valid state indices")
        groups[name] = indices
        used.update(indices)
    if not any(indices == (space.death_index,) for indices in groups.values()):
        raise ValueError("Death must be a distinct competing first-entry target")
    transient = tuple(i for i in range(len(space.labels)) if i not in used)
    if not transient:
        raise ValueError("A killed process requires at least one non-event state")
    return groups, transient


def _pieces(start: float, end: float, segments: tuple[RateSegment, ...]):
    for segment in segments:
        lower, upper = max(start, segment.start_year), min(end, segment.end_year)
        if upper > lower:
            yield segment, upper - lower


def _reachable(support, generator):
    """Positive-time path support, independent of floating probability magnitudes."""
    reachable = support.copy()
    for _ in range(len(support)):
        expanded = reachable | np.any(generator[reachable] > 0, axis=0)
        if np.array_equal(expanded, reachable):
            break
        reachable = expanded
    return reachable


def _advance(alpha, support, start, end, segments, indices, tolerance, normalizers, corrections):
    total_log = 0.0
    killed = indices is not None
    for segment, duration in _pieces(start, end, segments):
        q = np.asarray(segment.generator)
        if killed:
            q = q[np.ix_(indices, indices)]
        support = _reachable(support, q)
        alpha = alpha @ _exponential(q, duration, tolerance, killed=killed, corrections=corrections)
        scale = float(alpha.sum())
        if scale <= 0:
            # For finite hazards and finite time, at least the no-jump path has
            # positive survival. Underflow is not a structurally impossible path.
            raise FloatingPointError("Positive finite-time forward survival underflowed")
        normalizers.append(scale)
        total_log += log(scale)
        alpha = alpha / scale
    return alpha, support, total_log


def _interval_probability(
    alpha, support, start, end, segments, indices, targets, tolerance, corrections
):
    """Accumulate event mass without subtracting nearly equal survival/CDF values."""
    count = len(indices)
    extended = np.concatenate((alpha, [0.0]))
    extended_support = np.concatenate((support, [False]))
    for segment, duration in _pieces(start, end, segments):
        q = np.asarray(segment.generator)
        block = np.zeros((count + 1, count + 1))
        block[:count, :count] = q[np.ix_(indices, indices)]
        block[:count, count] = q[np.ix_(indices, targets)].sum(axis=1)
        extended_support = _reachable(extended_support, block)
        extended = extended @ _exponential(
            block, duration, tolerance, killed=True, corrections=corrections
        )
    probability = float(extended[-1])
    if not isfinite(probability) or not 0 <= probability <= 1:
        raise FloatingPointError("Interval-event mass failed probability checks")
    if probability == 0 and extended_support[-1]:
        raise FloatingPointError("Positive interval-event probability underflowed")
    return probability


def path_likelihood(
    space: StateSpace,
    initial,
    segments: Sequence[RateSegment],
    observations: Sequence[PanelObservation],
    *,
    terminal: TerminalObservation,
    contract: SoftwareObservationContract,
    event_targets: Mapping[str, Sequence[int]] | None = None,
    tolerance: float,
) -> dict:
    """Evaluate one linked path under a declared software observation contract.

    Segments must start at zero, be contiguous without guessed gaps/overlaps and
    cover the terminal time. First-entry modes kill *all* competing targets from
    entry, including the shared prefix before panel emissions. Interval events
    start no earlier than the last prefix observation. Exact boundary density
    uses the right-hand segment, except at the schedule's final end (left limit).

    Missing/coarsened emissions require a declared assumption. A panel terminal
    multiplies no alive indicator. Right censoring is no first entry into *any*
    target; a non-event endpoint adds an explicit endpoint operator. Returned
    densities have reciprocal-year units and can exceed one. Zero contributions
    retain -inf log likelihood; float underflow retains a finite log value.
    """
    tolerance = _stochastic_tolerance(tolerance)
    if type(space) is not StateSpace:
        raise ValueError("A declared StateSpace is required")
    if (
        type(contract) is not SoftwareObservationContract
        or type(terminal) is not TerminalObservation
    ):
        raise ValueError("Explicit software and terminal observation contracts are required")
    initial = _array(initial, "initial distribution", 1)
    if (
        initial.shape != (len(space.labels),)
        or (initial < 0).any()
        or (initial > 1).any()
        or not np.isclose(initial.sum(), 1, atol=tolerance, rtol=0)
    ):
        raise ValueError("Initial state probabilities must match states and sum to one")
    if (
        type(segments) not in (tuple, list)
        or not segments
        or any(type(item) is not RateSegment for item in segments)
    ):
        raise ValueError("A finite nonempty declared rate schedule is required")
    segments = tuple(segments)
    if (
        segments[0].start_year != 0
        or segments[-1].end_year < terminal.time_year
        or any(
            left.end_year != right.start_year
            for left, right in zip(segments[:-1], segments[1:], strict=True)
        )
    ):
        raise ValueError(
            "Rate schedule has an unknown origin, gap, overlap or insufficient coverage"
        )
    generator_deviations = []
    for segment in segments:
        q = validate_generator(space, segment.generator, tolerance=tolerance)
        generator_deviations.append(tuple(_scaled_generator_row_deviations(q).tolist()))
    if contract.treatment == "held_fixed" and any(
        item.generator != segments[0].generator for item in segments[1:]
    ):
        raise ValueError("Changing generators require a piecewise-declared treatment contract")
    if type(observations) not in (tuple, list) or any(
        type(item) is not PanelObservation for item in observations
    ):
        raise ValueError("A finite declared observation sequence is required")
    observations = tuple(observations)
    if any(
        len(item.emission) != len(space.labels) or item.time_year > terminal.time_year
        for item in observations
    ) or any(
        left.time_year >= right.time_year
        for left, right in zip(observations[:-1], observations[1:], strict=True)
    ):
        raise ValueError("Observation dimensions and chronological times must be supported")
    if contract.missingness == "no_missing" and any(
        item.kind == "coarsened" for item in observations
    ):
        raise ValueError(
            "Coarsened observations require an explicit missingness/coarsening assumption"
        )
    stopping = {
        "panel": ("observation_sequence_only", "administrative_observation_end"),
        "right_censor": ("independent_right_censoring",),
        "non_event_endpoint": ("non_event_assessment",),
        "exact_first_entry": ("first_entry_ascertainment",),
        "interval_first_entry": ("first_entry_ascertainment",),
    }
    if contract.stopping not in stopping[terminal.kind]:
        raise ValueError("Stopping declaration does not support this observation mode")
    killed = terminal.kind != "panel"
    if killed:
        groups, indices = _targets(space, event_targets)
        if any(initial[i] != 0 for values in groups.values() for i in values):
            raise ValueError("First-entry entry distribution already contains an event state")
        alpha = initial[list(indices)].copy()
        if terminal.event is not None and terminal.event not in groups:
            raise ValueError("Terminal event is not a declared target")
    else:
        if event_targets is not None:
            raise ValueError("A full panel path cannot silently use a killed target set")
        groups, indices, alpha = {}, None, initial.copy()
    if (
        terminal.kind == "interval_first_entry"
        and observations
        and terminal.interval_start_year < observations[-1].time_year
    ):
        raise ValueError("An event interval cannot precede the last linked non-event observation")
    if terminal.kind == "non_event_endpoint":
        if len(terminal.endpoint_emission) != len(space.labels) or any(
            terminal.endpoint_emission[i] != 0 for values in groups.values() for i in values
        ):
            raise ValueError("Non-event endpoint must explicitly exclude all event states")

    initial_scale = float(alpha.sum())
    log_likelihood, time, normalizers = 0.0, 0.0, []
    if initial_scale != 1:
        # Likelihood-preserving forward scaling, including a zero-time terminal.
        # The original mass remains in log_likelihood; this is not input repair.
        alpha /= initial_scale
        log_likelihood = log(initial_scale)
        normalizers.append(initial_scale)
    support = alpha > 0
    corrections = {"entries_zeroed": 0, "most_negative_entry": 0.0}
    impossible = False
    for observation in observations:
        alpha, support, increment = _advance(
            alpha,
            support,
            time,
            observation.time_year,
            segments,
            indices,
            tolerance,
            normalizers,
            corrections,
        )
        log_likelihood += increment
        weights = np.asarray(observation.emission)
        if killed:
            weights = weights[list(indices)]
        alpha = alpha * weights
        support = support & (weights > 0)
        scale = float(alpha.sum())
        normalizers.append(scale)
        if scale == 0:
            if support.any():
                raise FloatingPointError("Positive emission contribution underflowed")
            impossible = True
            break
        alpha /= scale
        log_likelihood += log(scale)
        time = observation.time_year
    if not impossible:
        end = (
            terminal.interval_start_year
            if terminal.kind == "interval_first_entry"
            else terminal.time_year
        )
        alpha, support, increment = _advance(
            alpha, support, time, end, segments, indices, tolerance, normalizers, corrections
        )
        log_likelihood += increment
        factor = 1.0
        if terminal.kind == "exact_first_entry":
            segment = next(
                (item for item in segments if item.start_year <= end < item.end_year), segments[-1]
            )
            q = np.asarray(segment.generator)
            hazards = q[np.ix_(indices, groups[terminal.event])].sum(axis=1)
            factor = float(alpha @ hazards)
            if factor == 0 and np.any(support & (hazards > 0)):
                raise FloatingPointError("Positive exact-event density underflowed")
        elif terminal.kind == "interval_first_entry":
            factor = _interval_probability(
                alpha,
                support,
                end,
                terminal.time_year,
                segments,
                indices,
                groups[terminal.event],
                tolerance,
                corrections,
            )
        elif terminal.kind == "non_event_endpoint":
            endpoint = np.asarray(terminal.endpoint_emission)[list(indices)]
            factor = float(alpha @ endpoint)
            if factor == 0 and np.any(support & (endpoint > 0)):
                raise FloatingPointError("Positive endpoint contribution underflowed")
        normalizers.append(factor)
        impossible = factor == 0
        if not impossible:
            log_likelihood += log(factor)
    if impossible:
        log_likelihood = float("-inf")
    density = terminal.kind == "exact_first_entry"
    if not density and log_likelihood > 0:
        raise FloatingPointError("Evaluated probability exceeds one; inputs are not repaired")
    try:
        likelihood = 0.0 if impossible else exp(log_likelihood)
    except OverflowError as error:
        raise FloatingPointError(
            "Likelihood is outside finite floating-point representation"
        ) from error
    if not density and likelihood > 1:
        raise FloatingPointError("Evaluated probability exceeds one; inputs are not repaired")
    return {
        "validation_only": True,
        "scope": "Declared mathematical observation contribution; no empirical fit or state inference.",
        "mode": terminal.kind,
        "contribution_kind": "density" if density else "probability",
        "units": "per_year" if density else "dimensionless",
        "likelihood": likelihood,
        "log_likelihood": log_likelihood,
        "structurally_zero": impossible,
        "floating_likelihood_underflow": not impossible and likelihood == 0,
        "normalizers": tuple(normalizers),
        "declared_assumptions": asdict(contract),
        "death_is_explicit": True,
        "panel_termination_implies_alive": False,
        "history_erased": False,
        "exact_boundary_convention": "right-hand segment; final schedule end uses left limit",
        "numerical_roundoff_policy": "Only exponential negatives within supplied tolerance become zero; no generator repair.",
        "numerical_roundoff_corrections": corrections,
        "numerical_input_deviations": {
            "initial_sum_minus_one": float(initial.sum() - 1),
            "generator_scaled_row_sums": tuple(generator_deviations),
            "generator_scaling": "Each row divided by its largest absolute hazard; zero row stays zero",
            "inputs_repaired": False,
        },
    }


def observable_jacobian(
    observable: Callable[[np.ndarray], Sequence[float]],
    parameters,
    steps,
    *,
    rank_tolerance: float,
) -> dict:
    """Central finite-difference/SVD distinction at one point, not global ID.

    Parameter units, steps, observable selection and the relative singular-value
    cutoff are caller-declared design choices. Perturbations outside a model's
    domain fail; no silent one-sided derivative or optimizer is substituted.
    """
    tolerance = _tolerance(rank_tolerance)
    point = _array(parameters, "parameters", 1)
    steps = _array(steps, "finite-difference steps", 1)
    if (
        not len(point)
        or steps.shape != point.shape
        or (steps <= 0).any()
        or not callable(observable)
    ):
        raise ValueError("Explicit finite parameters and positive matching steps are required")
    baseline = _array(observable(point.copy()), "observables", 1)
    if not len(baseline):
        raise ValueError("At least one declared observable is required")
    columns = []
    for i, step in enumerate(steps):
        plus, minus = point.copy(), point.copy()
        plus[i] += step
        minus[i] -= step
        if (
            not np.isfinite(plus).all()
            or not np.isfinite(minus).all()
            or plus[i] == point[i]
            or minus[i] == point[i]
        ):
            raise ValueError("Finite-difference perturbation is not representable")
        upper = _array(observable(plus), "perturbed observables", 1)
        lower = _array(observable(minus), "perturbed observables", 1)
        if upper.shape != baseline.shape or lower.shape != baseline.shape:
            raise ValueError("Observable dimensions changed under perturbation")
        columns.append((upper - lower) / (2 * step))
    jacobian = np.column_stack(columns)
    if not np.isfinite(jacobian).all():
        raise FloatingPointError("Observable derivative is not finite")
    singular = np.linalg.svd(jacobian, compute_uv=False)
    cutoff = tolerance * float(singular[0])
    rank = int(np.count_nonzero(singular > cutoff)) if singular[0] > 0 else 0
    return {
        "validation_only": True,
        "jacobian": jacobian.tolist(),
        "singular_values": singular.tolist(),
        "local_numerical_rank": rank,
        "parameter_count": len(point),
        "observable_count": len(baseline),
        "full_column_rank_at_point": rank == len(point),
        "finite_difference_steps": steps.tolist(),
        "relative_rank_tolerance": tolerance,
        "effective_absolute_singular_cutoff": cutoff,
        "global_identification_established": False,
        "causal_identification_established": False,
        "scope": "Local numerical distinction for the supplied observable map, units and settings.",
    }
