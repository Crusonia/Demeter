"""Panel parity on explicitly timed synthetic CTMCs, never on source visit labels."""

from itertools import product
from math import fsum, log

import numpy as np
import pytest

from demeter.analysis.longitudinal_likelihood import (
    PanelObservation,
    RateSegment,
    SoftwareObservationContract,
    StateSpace,
    TerminalObservation,
    path_likelihood,
    transition_matrix,
)
from demeter.analysis.nominal_observation_likelihood import (
    NominalObservation,
    NominalObservationChannel,
    NominalObservationContract,
    NominalTransition,
    nominal_path_likelihood,
)

TOL = 1e-12
SPACE = StateSpace(("naive", "history_high", "history_low", "dead"), (False, True, True, None), 3)
TOKENS = ("low", "high", "unavailable")
EMISSIONS = np.array([[0.7, 0.2, 0.1], [0.1, 0.7, 0.2], [0.6, 0.2, 0.2], [0, 0, 1]])


def _generator(multiplier):
    q = np.array([[0, 0.1, 0, 0.02], [0, 0, 0.2, 0.03], [0, 0.1, 0, 0.04], [0, 0, 0, 0]])
    q *= multiplier
    np.fill_diagonal(q, -q.sum(axis=1))
    return q


@pytest.mark.parametrize("piecewise", [False, True])
@pytest.mark.parametrize("zero_rates", [False, True])
def test_all_linked_token_paths_agree_without_independent_visit_pooling(piecewise, zero_rates):
    """Exhaust all 27 token paths and 64 hidden-state paths for each joint contribution.

    A nominal matrix is derived here from explicitly known synthetic times; this
    does not assert that a caller's arbitrary nominal matrix has a CTMC generator.
    """
    q1, q2 = _generator(0 if zero_rates else 1), _generator(0 if zero_rates else 2)
    if piecewise:
        segments = [RateSegment(0, 0.5, q1), RateSegment(0.5, 2, q2)]
        first = transition_matrix(SPACE, q1, 0.5, tolerance=TOL) @ transition_matrix(
            SPACE, q2, 0.5, tolerance=TOL
        )
        second = transition_matrix(SPACE, q2, 1, tolerance=TOL)
    else:
        segments = [RateSegment(0, 2, q1)]
        first = second = transition_matrix(SPACE, q1, 1, tolerance=TOL)
    initial = np.array([0.75, 0.25, 0, 0])
    channels = [NominalObservationChannel(i, TOKENS, EMISSIONS) for i in range(3)]
    transitions = [NominalTransition(0, 1, first), NominalTransition(1, 2, second)]
    continuous_contract = SoftwareObservationContract(
        "years",
        "exogenous",
        "no_missing",
        "synthetic_fixed_cohort",
        "piecewise_declared",
        "observation_sequence_only",
    )
    discrete_contract = NominalObservationContract(
        "synthetic_fixed_cohort",
        "joint",
        "conditionally_independent_given_state",
        "nominal_visit_index",
    )
    contributions = []
    dependent_witness = False
    for tokens in product(TOKENS, repeat=3):
        columns = [EMISSIONS[:, TOKENS.index(token)] for token in tokens]
        expected = fsum(
            initial[i] * columns[0][i] * first[i, j] * columns[1][j] * second[j, k] * columns[2][k]
            for i, j, k in product(range(4), repeat=3)
        )
        continuous = path_likelihood(
            SPACE,
            initial,
            segments,
            [PanelObservation(i, columns[i], "category") for i in range(3)],
            terminal=TerminalObservation("panel", 2),
            contract=continuous_contract,
            tolerance=TOL,
        )
        discrete = nominal_path_likelihood(
            SPACE,
            initial,
            transitions,
            channels,
            [NominalObservation(i, token) for i, token in enumerate(tokens)],
            contract=discrete_contract,
            tolerance=TOL,
        )
        assert continuous["likelihood"] == pytest.approx(expected, rel=1e-12, abs=0)
        assert discrete["likelihood"] == pytest.approx(expected, rel=1e-12, abs=0)
        assert continuous["structurally_zero"] == discrete["structurally_zero"] == (expected == 0)
        if expected:
            assert continuous["log_likelihood"] == pytest.approx(log(expected), abs=TOL)
            assert discrete["log_likelihood"] == pytest.approx(log(expected), abs=TOL)
        contributions.append(continuous["likelihood"])
        naive = (
            (initial @ columns[0])
            * (initial @ first @ columns[1])
            * (initial @ first @ second @ columns[2])
        )
        dependent_witness |= abs(expected - naive) > 1e-6
    assert fsum(contributions) == pytest.approx(1, abs=TOL)
    assert dependent_witness


def test_impossible_erased_history_path_has_identical_structural_zero():
    q = _generator(1)
    initial = [0, 1, 0, 0]
    identity_emissions = np.eye(4)
    labels = SPACE.labels
    continuous = path_likelihood(
        SPACE,
        initial,
        [RateSegment(0, 1, q)],
        [
            PanelObservation(0, [0, 1, 0, 0], "category"),
            PanelObservation(1, [1, 0, 0, 0], "category"),
        ],
        terminal=TerminalObservation("panel", 1),
        contract=SoftwareObservationContract(
            "years",
            "exogenous",
            "no_missing",
            "synthetic_fixed_cohort",
            "held_fixed",
            "observation_sequence_only",
        ),
        tolerance=TOL,
    )
    discrete = nominal_path_likelihood(
        SPACE,
        initial,
        [NominalTransition(0, 1, transition_matrix(SPACE, q, 1, tolerance=TOL))],
        [NominalObservationChannel(i, labels, identity_emissions) for i in range(2)],
        [NominalObservation(0, "history_high"), NominalObservation(1, "naive")],
        contract=NominalObservationContract(
            "synthetic_fixed_cohort",
            "joint",
            "conditionally_independent_given_state",
            "nominal_visit_index",
        ),
        tolerance=TOL,
    )
    assert continuous["likelihood"] == discrete["likelihood"] == 0
    assert continuous["structurally_zero"] is discrete["structurally_zero"] is True
