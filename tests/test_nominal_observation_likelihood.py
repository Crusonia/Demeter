"""Synthetic exact enumeration; no source categories, fitted rates or raw records."""

from dataclasses import FrozenInstanceError, replace
from itertools import product
from math import log

import numpy as np
import pytest

from demeter.analysis.longitudinal_likelihood import StateSpace
from demeter.analysis.nominal_observation_likelihood import (
    NominalObservation,
    NominalObservationChannel,
    NominalObservationContract,
    NominalTransition,
    nominal_path_likelihood,
    validate_nominal_transition,
)

TOL = 1e-12  # Numerical verification control, not an empirical parameter.
SPACE = StateSpace(
    ("naive", "diagnosed_high", "diagnosed_low", "dead"), (False, True, True, None), 3
)
MATRIX = [[0.65, 0.2, 0, 0.15], [0, 0.7, 0.2, 0.1], [0, 0.1, 0.8, 0.1], [0, 0, 0, 1]]
TOKENS = ("low", "high", "unavailable")
EMISSIONS = [[0.7, 0.2, 0.1], [0.1, 0.7, 0.2], [0.6, 0.2, 0.2], [0, 0, 1]]
INITIAL = [0.65, 0.2, 0.1, 0.05]


def contract(*, baseline="joint", prefix=False, selection="synthetic_fixed_cohort"):
    return NominalObservationContract(
        selection,
        baseline,
        "conditioned_on_declared_observation_prefix"
        if prefix
        else "conditionally_independent_given_state",
        "nominal_visit_index",
    )


def evaluate(tokens, *, channels=None, matrices=None, initial=INITIAL, declared=None):
    transitions = [
        NominalTransition(i, i + 1, matrix)
        for i, matrix in enumerate(
            matrices if matrices is not None else [MATRIX] * (len(tokens) - 1)
        )
    ]
    if channels is None:
        channels = [NominalObservationChannel(i, TOKENS, EMISSIONS) for i in range(len(tokens))]
    return nominal_path_likelihood(
        SPACE,
        initial,
        transitions,
        channels,
        [NominalObservation(i, token) for i, token in enumerate(tokens)],
        contract=declared or contract(),
        tolerance=TOL,
    )


def enumerate_hidden(tokens, channels, matrices, initial=INITIAL):
    total = 0
    for states in product(range(len(SPACE.labels)), repeat=len(tokens)):
        probability = initial[states[0]]
        for visit, state in enumerate(states):
            if visit:
                probability *= matrices[visit - 1][states[visit - 1]][state]
            probability *= channels[visit].probabilities[state][
                channels[visit].tokens.index(tokens[visit])
            ]
        total += probability
    return total


def test_forward_matches_full_hidden_path_enumeration_and_full_token_marginal():
    channels = [NominalObservationChannel(i, TOKENS, EMISSIONS) for i in range(3)]
    probabilities = []
    for tokens in product(TOKENS, repeat=3):
        actual = evaluate(tokens, channels=channels)
        expected = enumerate_hidden(tokens, channels, [MATRIX] * 2)
        assert actual["likelihood"] == pytest.approx(expected, rel=1e-13, abs=1e-16)
        assert actual["structurally_zero"] is (expected == 0)
        probabilities.append(actual["likelihood"])
    assert sum(probabilities) == pytest.approx(1)


def test_conditioned_baseline_updates_shared_state_but_removes_only_baseline_factor():
    baseline_probability = evaluate(["low"])["likelihood"]
    total = 0
    for future in product(TOKENS, repeat=2):
        tokens = ("low", *future)
        joint = evaluate(tokens)
        conditional = evaluate(
            tokens,
            declared=contract(baseline="conditioned", selection="conditioned_on_selected_cohort"),
        )
        assert conditional["likelihood"] == pytest.approx(
            joint["likelihood"] / baseline_probability
        )
        assert conditional["baseline_token_log_probability"] == pytest.approx(
            log(baseline_probability)
        )
        assert conditional["cohort_selection_model_fitted"] is False
        total += conditional["likelihood"]
    assert total == pytest.approx(1)
    assert evaluate(["low"], declared=contract(baseline="conditioned"))["likelihood"] == 1


def test_repeated_observations_share_hidden_state_not_independent_marginals():
    matrix = np.eye(4)
    channel = [[0.9, 0.1, 0], [0.1, 0.9, 0], [0.1, 0.9, 0], [0, 0, 1]]
    channels = [NominalObservationChannel(i, TOKENS, channel) for i in range(2)]
    actual = evaluate(
        ["low", "low"], initial=[0.5, 0.5, 0, 0], matrices=[matrix], channels=channels
    )
    assert actual["likelihood"] == pytest.approx(0.41)
    assert actual["likelihood"] != pytest.approx(0.5 * 0.5)
    assert actual["single_path_only"] is True
    assert actual["batch_iid_likelihood_supplied"] is False
    assert actual["cluster_independence_assumed"] is False


def test_prefix_dependent_availability_channel_full_marginal_and_hidden_enumeration():
    total = 0
    for tokens in product(TOKENS, repeat=3):
        channels = []
        for visit in range(3):
            previous = tokens[:visit]
            emission = (
                EMISSIONS
                if not previous or previous[-1] != "high"
                else [[0.1, 0.1, 0.8], [0.1, 0.1, 0.8], [0.1, 0.1, 0.8], [0, 0, 1]]
            )
            channels.append(NominalObservationChannel(visit, TOKENS, emission, previous))
        actual = evaluate(tokens, channels=channels, declared=contract(prefix=True))
        assert actual["likelihood"] == pytest.approx(
            enumerate_hidden(tokens, channels, [MATRIX] * 2)
        )
        total += actual["likelihood"]
    assert total == pytest.approx(1)


def test_unavailable_is_explicit_probability_and_does_not_assert_alive():
    missing = evaluate(["unavailable"], initial=[0, 0, 0, 1])
    assert missing["likelihood"] == 1
    assert missing["termination_implies_alive"] is False
    assert missing["missingness_mask_inferred"] is False
    assert evaluate(["unavailable"])["likelihood"] == pytest.approx(0.175)
    assert evaluate(["low"], initial=[0, 0, 0, 1])["structurally_zero"] is True


def test_lower_category_with_retained_diagnosis_history_is_allowed():
    matrix = np.eye(4)
    matrix[1] = [0, 0, 1, 0]
    channels = [
        NominalObservationChannel(0, TOKENS, EMISSIONS),
        NominalObservationChannel(1, TOKENS, EMISSIONS),
    ]
    actual = evaluate(["high", "low"], initial=[0, 1, 0, 0], matrices=[matrix], channels=channels)
    assert actual["likelihood"] == pytest.approx(0.7 * 0.6)
    assert actual["history_erased"] is False


def test_structural_impossibility_and_undefined_zero_baseline_conditioning():
    actual = evaluate(["low"], initial=[0, 0, 0, 1])
    assert actual["likelihood"] == 0
    assert actual["log_likelihood"] == -np.inf
    assert actual["structurally_zero"] is True
    assert actual["floating_likelihood_underflow"] is False
    with pytest.raises(ValueError, match="impossible baseline"):
        evaluate(["low"], initial=[0, 0, 0, 1], declared=contract(baseline="conditioned"))
    actual = evaluate(
        ["unavailable", "low"], initial=[0, 0, 0, 1], declared=contract(baseline="conditioned")
    )
    assert actual["structurally_zero"] is True


def test_tiny_positive_likelihood_underflow_retains_finite_log_probability():
    probabilities = [[1e-200, 1], [1e-200, 1], [1e-200, 1], [0, 1]]
    channels = [NominalObservationChannel(i, ("rare", "other"), probabilities) for i in range(3)]
    actual = evaluate(
        ["rare"] * 3, initial=[1, 0, 0, 0], matrices=[np.eye(4)] * 2, channels=channels
    )
    assert actual["log_likelihood"] == pytest.approx(3 * log(1e-200))
    assert actual["likelihood"] == 0
    assert actual["structurally_zero"] is False
    assert actual["floating_likelihood_underflow"] is True


def test_underflowed_posterior_state_can_be_only_viable_later_state():
    baseline = NominalObservationChannel(
        0, ("seen", "other"), [[1, 0], [1e-200, 1], [0, 1], [0, 1]]
    )
    later = NominalObservationChannel(1, ("seen", "other"), [[0, 1], [1, 0], [0, 1], [0, 1]])
    actual = evaluate(
        ["seen", "seen"],
        initial=[1, 1e-200, 0, 0],
        matrices=[np.eye(4)],
        channels=[baseline, later],
    )
    assert actual["log_likelihood"] == pytest.approx(2 * log(1e-200))
    assert actual["floating_likelihood_underflow"] is True
    assert actual["structurally_zero"] is False


def test_conditioning_on_tiny_positive_baseline_is_defined_even_if_display_underflows():
    channels = [
        NominalObservationChannel(0, ("seen", "other"), [[0, 1], [1e-200, 1], [0, 1], [0, 1]]),
        NominalObservationChannel(1, ("seen", "other"), [[0, 1], [1, 0], [0, 1], [0, 1]]),
    ]
    actual = evaluate(
        ["seen", "seen"],
        initial=[1, 1e-200, 0, 0],
        matrices=[np.eye(4)],
        channels=channels,
        declared=contract(baseline="conditioned"),
    )
    assert actual["baseline_token_log_probability"] == pytest.approx(2 * log(1e-200))
    assert actual["likelihood"] == 1
    assert actual["log_likelihood"] == 0
    assert actual["structurally_zero"] is False


def test_unrepresentable_extended_precision_positive_input_is_not_structural_zero():
    tiny = np.longdouble("1e-400")
    if tiny == 0:
        pytest.skip("Platform longdouble has no wider exponent than binary64")
    matrix = np.eye(4, dtype=np.longdouble)
    matrix[0][1] = tiny
    with pytest.raises(ValueError, match="representable in binary64"):
        NominalTransition(0, 1, matrix)
    with pytest.raises(ValueError, match="representable in binary64"):
        validate_nominal_transition(SPACE, matrix, tolerance=TOL)
    emissions = np.asarray(EMISSIONS, dtype=np.longdouble)
    emissions[3][0] = tiny
    with pytest.raises(ValueError, match="representable in binary64"):
        NominalObservationChannel(0, TOKENS, emissions)
    with pytest.raises(ValueError, match="representable in binary64"):
        evaluate(["low"], initial=np.asarray([1, tiny, 0, 0], dtype=np.longdouble))
    emissions[3][0] = -tiny
    with pytest.raises(ValueError, match="between zero and one"):
        NominalObservationChannel(0, TOKENS, emissions)


def test_tiny_two_edge_interval_path_uses_one_step_not_transitive_reachability():
    matrix = np.eye(4)
    matrix[0] = [1, 1e-200, 0, 0]
    matrix[1] = [0, 1, 1e-200, 0]
    emissions = [[1, 0], [1, 0], [0, 1], [1, 0]]
    channels = [NominalObservationChannel(i, ("not_low", "low"), emissions) for i in range(3)]
    short = evaluate(
        ["not_low", "low"], initial=[1, 0, 0, 0], matrices=[matrix], channels=channels[:2]
    )
    assert short["structurally_zero"] is True
    full = evaluate(
        ["not_low", "not_low", "low"],
        initial=[1, 0, 0, 0],
        matrices=[matrix] * 2,
        channels=channels,
    )
    assert full["structurally_zero"] is False
    assert full["log_likelihood"] == pytest.approx(2 * log(1e-200))


def test_immutable_snapshots_and_opaque_nominal_tokens_do_not_parse_elapsed_time():
    matrix, values, names, prefix = (
        [row[:] for row in MATRIX],
        [row[:] for row in EMISSIONS],
        list(TOKENS),
        ["12 months"],
    )
    interval = NominalTransition(0, 1, matrix)
    channel = NominalObservationChannel(1, names, values, prefix)
    matrix[0][0], values[0][0], names[0], prefix[0] = 9, 9, "changed", "changed"
    assert interval.matrix[0][0] == 0.65
    assert channel.probabilities[0][0] == 0.7
    assert channel.tokens == TOKENS
    assert channel.conditioning_tokens == ("12 months",)
    with pytest.raises(FrozenInstanceError):
        interval.to_visit = 24
    with pytest.raises(TypeError):
        channel.probabilities[0][0] = 0
    observation = NominalObservation(0, "24 months")
    assert observation.visit_index == 0
    assert evaluate(["low"])["elapsed_time_inferred"] is False


@pytest.mark.parametrize("value", [True, 0.0, "12 months", -1, None])
def test_visit_indices_reject_elapsed_clocks_or_coercion(value):
    with pytest.raises(ValueError):
        NominalObservation(value, "low")
    with pytest.raises(ValueError):
        NominalTransition(value, 1, MATRIX)


def test_transition_schedule_cannot_skip_or_repeat_nominal_intervals():
    with pytest.raises(ValueError, match="consecutive"):
        NominalTransition(0, 2, MATRIX)
    with pytest.raises(ValueError, match="consecutive"):
        NominalTransition(0, 0, MATRIX)
    with pytest.raises(ValueError, match="each declared nominal interval"):
        nominal_path_likelihood(
            SPACE,
            INITIAL,
            [NominalTransition(1, 2, MATRIX)],
            [NominalObservationChannel(i, TOKENS, EMISSIONS) for i in range(2)],
            [NominalObservation(0, "low"), NominalObservation(1, "high")],
            contract=contract(),
            tolerance=TOL,
        )


@pytest.mark.parametrize(
    "mutation",
    ["death_exit", "history_erase", "row_sum", "negative", "bool", "masked", "shape", "nan"],
)
def test_transition_invalidity_is_not_repaired(mutation):
    matrix = np.asarray(MATRIX).copy()
    if mutation == "death_exit":
        matrix[3] = [1e-14, 0, 0, 1]
    elif mutation == "history_erase":
        matrix[1][0] = 1e-14
    elif mutation == "row_sum":
        matrix[0][0] -= 0.1
    elif mutation == "negative":
        matrix[0][2] = -1e-14
    elif mutation == "bool":
        matrix = [[True, 0, 0, 0]] * 4
    elif mutation == "masked":
        matrix = np.ma.array(matrix, mask=False)
    elif mutation == "shape":
        matrix = [[1]] * 4
    else:
        matrix[0][0] = np.nan
    with pytest.raises(ValueError):
        validate_nominal_transition(SPACE, matrix, tolerance=TOL)


@pytest.mark.parametrize(
    "mutation",
    [
        "partial",
        "duplicate_token",
        "unknown_token",
        "column_count",
        "channel_context",
        "gap",
        "no_channel",
        "no_observation",
        "no_transition",
        "initial",
        "time_basis",
        "unknown_selection",
    ],
)
def test_complete_explicit_contract_required(mutation):
    channels = [NominalObservationChannel(i, TOKENS, EMISSIONS) for i in range(2)]
    observations = [NominalObservation(0, "low"), NominalObservation(1, "high")]
    transitions = [NominalTransition(0, 1, MATRIX)]
    declared, initial = contract(), INITIAL
    if mutation == "partial":
        channels[0] = NominalObservationChannel(0, TOKENS[:2], [row[:2] for row in EMISSIONS])
    elif mutation == "duplicate_token":
        with pytest.raises(ValueError):
            NominalObservationChannel(0, ("low", "low"), [[0.5, 0.5]] * 4)
        return
    elif mutation == "unknown_token":
        observations[0] = NominalObservation(0, "unknown")
    elif mutation == "column_count":
        channels[0] = NominalObservationChannel(0, TOKENS[:2], EMISSIONS)
    elif mutation == "channel_context":
        channels[1] = NominalObservationChannel(1, TOKENS, EMISSIONS, ("low",))
    elif mutation == "gap":
        observations[1] = NominalObservation(2, "high")
    elif mutation == "no_channel":
        channels.pop()
    elif mutation == "no_observation":
        observations = []
    elif mutation == "no_transition":
        transitions = []
    elif mutation == "initial":
        initial = [1, 1, 0, 0]
    elif mutation in ("time_basis", "unknown_selection"):
        with pytest.raises(ValueError):
            replace(
                declared,
                **(
                    {"time_basis": "years"}
                    if mutation == "time_basis"
                    else {"selection": "unknown"}
                ),
            )
        return
    with pytest.raises(ValueError):
        nominal_path_likelihood(
            SPACE, initial, transitions, channels, observations, contract=declared, tolerance=TOL
        )


def test_prefix_conditioning_cannot_use_guessed_or_partial_past():
    channels = [
        NominalObservationChannel(0, TOKENS, EMISSIONS, ()),
        NominalObservationChannel(1, TOKENS, EMISSIONS, ("high",)),
    ]
    with pytest.raises(ValueError, match="observed prefix"):
        evaluate(["low", "high"], channels=channels, declared=contract(prefix=True))
    with pytest.raises(ValueError, match="complete prior"):
        NominalObservationChannel(2, TOKENS, EMISSIONS, ("low",))


def test_small_row_sum_deviations_are_reported_without_input_normalization():
    values = [row[:] for row in EMISSIONS]
    values[0][0] += 5e-13
    matrix = [row[:] for row in MATRIX]
    matrix[0][0] += 5e-13
    initial = INITIAL.copy()
    initial[0] += 5e-13
    channels = [NominalObservationChannel(i, TOKENS, values) for i in range(2)]
    actual = evaluate(["low", "high"], channels=channels, matrices=[matrix], initial=initial)
    diagnostics = actual["row_sum_diagnostics"]
    assert diagnostics["input_rows_renormalized"] is False
    assert 0 < diagnostics["initial_absolute_deviation"] < TOL
    assert all(0 < value < TOL for value in diagnostics["channel_max_absolute_deviations"])
    assert all(0 < value < TOL for value in diagnostics["transition_max_absolute_deviations"])
    assert actual["likelihood"] == pytest.approx(
        enumerate_hidden(("low", "high"), channels, [matrix], initial), abs=1e-16
    )
