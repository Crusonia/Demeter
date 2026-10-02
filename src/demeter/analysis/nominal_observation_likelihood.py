"""Synthetic discrete observation kernels on nominal visit indices only.

Caller-declared interval probabilities are not rates, elapsed times, biological
state mappings or engine operators. Complete channels include unavailable or
protocol-omitted observations as explicit tokens; no missingness mask is inferred.
Design trace: I-11/I-12 -> F-08 -> T-05/T-08.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite

import numpy as np
from scipy.special import logsumexp

from demeter.analysis.longitudinal_likelihood import (
    StateSpace,
    _array,
    _tolerance,
    validate_categorical_emissions,
)


def _index(value) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Nominal visit index must be a nonnegative Python integer")
    return value


def _tokens(value) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or any(
        type(item) is not str or not item or item != item.strip() for item in value
    ):
        raise ValueError("Observation tokens must be explicitly named strings")
    return tuple(value)


def _snapshot(value, name):
    return tuple(tuple(row) for row in _probability_array(value, name, 2).tolist())


def _probability_array(value, name, dimensions):
    """Reject positive extended-precision inputs lost in the binary64 snapshot."""
    result = _array(value, name, dimensions)
    raw = np.asarray(value)
    if (raw < 0).any() or (raw > 1).any():
        raise ValueError(f"{name} probabilities must be between zero and one")
    if np.any((raw > 0) & (result == 0)):
        raise ValueError(f"{name} positive probabilities must be representable in binary64")
    return result


@dataclass(frozen=True)
class NominalTransition:
    """One consecutive nominal interval; matrix rows are source-state probabilities."""

    from_visit: int
    to_visit: int
    matrix: tuple[tuple[float, ...], ...]

    def __post_init__(self):
        if _index(self.to_visit) != _index(self.from_visit) + 1:
            raise ValueError("Transitions must connect consecutive nominal visit indices")
        object.__setattr__(self, "matrix", _snapshot(self.matrix, "nominal transition"))


@dataclass(frozen=True)
class NominalObservationChannel:
    """Full exclusive token channel conditional on state and, optionally, observed past.

    ``conditioning_tokens=None`` declares state-only conditioning. A tuple declares
    the complete preceding observation prefix, including unavailable tokens.
    Each state's token probabilities must sum to one; exhaustiveness is a caller
    assumption validated mathematically, not verified against a real source.
    """

    visit_index: int
    tokens: tuple[str, ...]
    probabilities: tuple[tuple[float, ...], ...]
    conditioning_tokens: tuple[str, ...] | None = None

    def __post_init__(self):
        _index(self.visit_index)
        tokens = _tokens(self.tokens)
        if not tokens or len(set(tokens)) != len(tokens):
            raise ValueError("A channel requires unique exhaustive observation tokens")
        object.__setattr__(self, "tokens", tokens)
        object.__setattr__(self, "probabilities", _snapshot(self.probabilities, "channel"))
        if self.conditioning_tokens is not None:
            context = _tokens(self.conditioning_tokens)
            if len(context) != self.visit_index:
                raise ValueError("Channel context must contain the complete prior nominal prefix")
            object.__setattr__(self, "conditioning_tokens", context)


@dataclass(frozen=True)
class NominalObservation:
    visit_index: int
    token: str

    def __post_init__(self):
        _index(self.visit_index)
        _tokens([self.token])


@dataclass(frozen=True)
class NominalObservationContract:
    """Explicit software assumptions; no source selection mechanism is inferred."""

    selection: str
    baseline: str
    channel_dependence: str
    time_basis: str

    def __post_init__(self):
        choices = {
            "selection": ("synthetic_fixed_cohort", "conditioned_on_selected_cohort"),
            "baseline": ("joint", "conditioned"),
            "channel_dependence": (
                "conditionally_independent_given_state",
                "conditioned_on_declared_observation_prefix",
            ),
            "time_basis": ("nominal_visit_index",),
        }
        if any(
            type(getattr(self, key)) is not str or getattr(self, key) not in allowed
            for key, allowed in choices.items()
        ):
            raise ValueError("Nominal observation assumptions must be explicitly declared")


def validate_nominal_transition(space: StateSpace, matrix, *, tolerance: float) -> np.ndarray:
    """Stochastic rows, exactly absorbing death, and no live diagnosis-history erasure."""
    if type(space) is not StateSpace:
        raise ValueError("A declared StateSpace is required")
    count = len(space.labels)
    matrix = _probability_array(matrix, "nominal transition", 2)
    values = validate_categorical_emissions(matrix, state_count=count, tolerance=tolerance)
    if values.shape != (count, count):
        raise ValueError("Nominal transition dimensions must match the state space")
    expected_death = np.zeros(count)
    expected_death[space.death_index] = 1
    if not np.array_equal(values[space.death_index], expected_death):
        raise ValueError("Death must be exactly absorbing")
    for i, source in enumerate(space.diagnosis_history):
        for j, target in enumerate(space.diagnosis_history):
            if source is True and target is False and values[i, j] != 0:
                raise ValueError("A live transition cannot erase diagnosed history")
    return values


def _log_probabilities(values):
    result = np.full(values.shape, -np.inf)
    positive = values > 0
    result[positive] = np.log(values[positive])
    return result


def nominal_path_likelihood(
    space: StateSpace,
    initial,
    transitions,
    channels,
    observations,
    *,
    contract: NominalObservationContract,
    tolerance: float,
) -> dict:
    """One linked path; conditional baseline removes only its own probability.

    Every nominal visit from zero must contain a full channel and an observed
    token. Missingness has no automatic operator. Initial probabilities refer to
    the caller-declared cohort *before* its baseline token; source selection is
    already conditioned on when declared, never estimated here. Prefix-dependent
    channels must match the observed past. No pooling or cluster independence is
    assumed. Log-domain filtering retains positive paths whose displayed ordinary
    probability underflows, including a tiny posterior that becomes relevant later.
    """
    tolerance = _tolerance(tolerance)
    if type(space) is not StateSpace or type(contract) is not NominalObservationContract:
        raise ValueError("Declared state space and nominal observation contract are required")
    count = len(space.labels)
    initial = _probability_array(initial, "initial distribution", 1)
    if (
        initial.shape != (count,)
        or (initial < 0).any()
        or (initial > 1).any()
        or not np.isclose(initial.sum(), 1, atol=tolerance, rtol=0)
    ):
        raise ValueError("Initial probabilities must match states and sum to one")
    for sequence, cls, name in (
        (transitions, NominalTransition, "transitions"),
        (channels, NominalObservationChannel, "channels"),
        (observations, NominalObservation, "observations"),
    ):
        if type(sequence) not in (tuple, list) or any(type(item) is not cls for item in sequence):
            raise ValueError(f"A finite declared sequence of nominal {name} is required")
    transitions, channels, observations = tuple(transitions), tuple(channels), tuple(observations)
    visits = len(observations)
    if not visits or len(channels) != visits or len(transitions) != visits - 1:
        raise ValueError("Every nominal visit requires one observation and one full channel")
    matrices, emissions = [], []
    channel_row_deviations, transition_row_deviations = [], []
    prefix = ()
    for index, (channel, observation) in enumerate(zip(channels, observations, strict=True)):
        if channel.visit_index != index or observation.visit_index != index:
            raise ValueError("Nominal visits must start at zero without gaps or duplicates")
        expected_context = (
            None
            if contract.channel_dependence == "conditionally_independent_given_state"
            else prefix
        )
        if channel.conditioning_tokens != expected_context:
            raise ValueError("Channel conditioning must match its declared observed prefix")
        if observation.token not in channel.tokens:
            raise ValueError("Observed token is absent from the declared exhaustive channel")
        values = validate_categorical_emissions(
            channel.probabilities, state_count=count, tolerance=tolerance
        )
        if values.shape[1] != len(channel.tokens):
            raise ValueError("Channel token count must match emission columns")
        channel_row_deviations.append(float(np.max(np.abs(values.sum(axis=1) - 1))))
        emissions.append(values[:, channel.tokens.index(observation.token)])
        prefix += (observation.token,)
        if index < visits - 1:
            interval = transitions[index]
            if interval.from_visit != index or interval.to_visit != index + 1:
                raise ValueError("Transitions must cover each declared nominal interval in order")
            matrix = validate_nominal_transition(space, interval.matrix, tolerance=tolerance)
            matrices.append(matrix)
            transition_row_deviations.append(float(np.max(np.abs(matrix.sum(axis=1) - 1))))

    log_alpha = _log_probabilities(initial)
    support = initial > 0
    total_log = 0.0
    log_normalizers = []
    structurally_zero = False
    baseline_log = None
    for index, emission in enumerate(emissions):
        if index:
            matrix = matrices[index - 1]
            support = np.any(support[:, None] & (matrix > 0), axis=0)
            log_alpha = logsumexp(log_alpha[:, None] + _log_probabilities(matrix), axis=0)
        support &= emission > 0
        log_alpha += _log_probabilities(emission)
        if not support.any():
            if index == 0 and contract.baseline == "conditioned":
                raise ValueError("Cannot condition on a structurally impossible baseline token")
            structurally_zero = True
            total_log = -np.inf
            log_normalizers.append(float("-inf"))
            break
        normalizer = float(logsumexp(log_alpha))
        if not isfinite(normalizer):
            raise FloatingPointError("Positive nominal path lost its finite log probability")
        log_normalizers.append(normalizer)
        log_alpha -= normalizer
        if index == 0:
            baseline_log = normalizer
        if index or contract.baseline == "joint":
            total_log += normalizer
    try:
        likelihood = 0.0 if structurally_zero else exp(total_log)
    except OverflowError as error:
        raise FloatingPointError(
            "Accumulated nominal row errors exceed floating representation"
        ) from error
    return {
        "validation_only": True,
        "single_path_only": True,
        "batch_iid_likelihood_supplied": False,
        "mode": "discrete_nominal_observation_path",
        "contribution_kind": "probability",
        "units": "dimensionless",
        "likelihood": likelihood,
        "log_likelihood": float(total_log),
        "structurally_zero": structurally_zero,
        "floating_likelihood_underflow": not structurally_zero and likelihood == 0,
        "log_normalizers": tuple(log_normalizers),
        "row_sum_diagnostics": {
            "tolerance": tolerance,
            "initial_absolute_deviation": float(abs(initial.sum() - 1)),
            "channel_max_absolute_deviations": tuple(channel_row_deviations),
            "transition_max_absolute_deviations": tuple(transition_row_deviations),
            "input_rows_renormalized": False,
        },
        "baseline_token_log_probability": baseline_log,
        "baseline_token_conditioned_on": contract.baseline == "conditioned",
        "declared_assumptions": asdict(contract),
        "nominal_visit_count": visits,
        "elapsed_time_inferred": False,
        "missingness_mask_inferred": False,
        "termination_implies_alive": False,
        "history_erased": False,
        "cohort_selection_model_fitted": False,
        "cluster_independence_assumed": False,
        "clinical_fit_ready": False,
        "engine_activation_allowed": False,
        "numerical_policy": "Log-domain forward normalization; zero input edges alone determine structural impossibility; no row repair.",
    }
