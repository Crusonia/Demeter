"""Synthetic mathematical checks; no observed participant or clinical values."""

from dataclasses import FrozenInstanceError
from itertools import product
from math import exp, expm1, log

import numpy as np
import pytest

from demeter.analysis.longitudinal_likelihood import (
    PanelObservation,
    RateSegment,
    SoftwareObservationContract,
    StateSpace,
    TerminalObservation,
    observable_jacobian,
    path_likelihood,
    transition_matrix,
    validate_categorical_emissions,
    validate_generator,
)


TOL = 1e-12


@pytest.mark.parametrize("tolerance", [0.5, 0.1, 1e-6, np.nextafter(1e-10, 1)])
@pytest.mark.parametrize("api", ["generator", "emissions", "transition", "path"])
def test_stochastic_tolerance_cannot_admit_material_mass_errors(tolerance, api):
    space = StateSpace(("live", "dead"), (False, None), 1)
    with pytest.raises(ValueError, match="Stochastic roundoff"):
        if api == "generator":
            validate_generator(space, [[-0.1, 0.4], [0, 0]], tolerance=tolerance)
        elif api == "emissions":
            validate_categorical_emissions([[1, 0.4], [1, 0]], state_count=2, tolerance=tolerance)
        elif api == "transition":
            transition_matrix(space, [[0, 0], [0, 0]], 1, tolerance=tolerance)
        else:
            path_likelihood(
                space,
                [1, 0.4],
                [RateSegment(0, 1, [[0, 0], [0, 0]])],
                [PanelObservation(0, [1, 1], "category")],
                terminal=TerminalObservation("panel", 1),
                contract=contract(),
                tolerance=tolerance,
            )


@pytest.mark.parametrize("mass", [0.6, 1.4])
def test_material_initial_and_channel_mass_fail_at_valid_ceiling(mass):
    space = StateSpace(("live", "dead"), (False, None), 1)
    with pytest.raises(ValueError, match="Initial state probabilities"):
        path_likelihood(
            space,
            [mass, 0],
            [RateSegment(0, 1, [[0, 0], [0, 0]])],
            [],
            terminal=TerminalObservation("panel", 1),
            contract=contract(),
            tolerance=1e-10,
        )
    with pytest.raises(ValueError, match="sum to one"):
        validate_categorical_emissions([[mass / 2, mass / 2]], state_count=1, tolerance=1e-10)


@pytest.mark.parametrize("scale", [1e-200, 1e-20, 1, 1e200])
@pytest.mark.parametrize("sign", [-1, 1])
def test_generator_conservation_is_relative_to_hazard_scale(scale, sign):
    space = StateSpace(("live", "dead"), (False, None), 1)
    with pytest.raises(ValueError, match="zero row sums"):
        validate_generator(space, [[-scale, scale * (1 + sign * 0.1)], [0, 0]], tolerance=1e-10)


def test_valid_tiny_rate_process_matches_independent_competing_event_formula():
    # Long time is caller-known synthetic years, never inferred from source labels.
    result = event_path("interval_first_entry", time=1e20, start=0, lam=1e-20, mu=2e-20)
    assert result["likelihood"] == pytest.approx(-expm1(-3) / 3, rel=1e-12, abs=0)


def test_accepted_initial_roundoff_is_visible_and_never_normalized():
    space = StateSpace(("live", "dead"), (False, None), 1)
    epsilon = 1e-13
    result = path_likelihood(
        space,
        [0.5, 0.5 - epsilon],
        [RateSegment(0, 1, [[0, 0], [0, 0]])],
        [],
        terminal=TerminalObservation("panel", 1),
        contract=contract(),
        tolerance=TOL,
    )
    assert result["likelihood"] == pytest.approx(1 - epsilon, rel=0, abs=np.spacing(1.0))
    assert result["likelihood"] < 1
    deviations = result["numerical_input_deviations"]
    assert deviations["initial_sum_minus_one"] < 0
    assert deviations["inputs_repaired"] is False
    assert deviations["generator_scaled_row_sums"] == ((0.0, 0.0),)


def test_accepted_generator_roundoff_is_visible_and_not_repaired():
    space = StateSpace(("live", "dead"), (False, None), 1)
    q = [[-0.1, 0.1 - 1e-15], [0, 0]]
    snapshot = np.asarray(q).copy()
    assert np.array_equal(validate_generator(space, q, tolerance=TOL), snapshot)
    result = path_likelihood(
        space,
        [1, 0],
        [RateSegment(0, 1, q)],
        [PanelObservation(1, [1, 0], "category")],
        terminal=TerminalObservation("panel", 1),
        contract=contract(),
        tolerance=TOL,
    )
    assert result["numerical_input_deviations"]["generator_scaled_row_sums"][0][0] < 0
    assert result["likelihood"] == pytest.approx(exp(-0.1))


def test_accepted_channel_roundoff_is_not_repaired():
    matrix = np.array([[0.5, 0.5 - 1e-13]])
    result = validate_categorical_emissions(matrix, state_count=1, tolerance=TOL)
    assert np.array_equal(result, matrix)
    assert result.sum() < 1


def test_even_roundoff_surplus_cannot_return_a_probability_above_one():
    space = StateSpace(("live", "dead"), (False, None), 1)
    with pytest.raises(FloatingPointError, match="probability exceeds one"):
        path_likelihood(
            space,
            [0.5, 0.5 + 1e-13],
            [RateSegment(0, 1, [[0, 0], [0, 0]])],
            [PanelObservation(0, [1, 1], "category")],
            terminal=TerminalObservation("panel", 1),
            contract=contract(),
            tolerance=TOL,
        )


@pytest.mark.parametrize("time", [0, 1])
@pytest.mark.parametrize("deviation", [-1e-13, 1e-13])
def test_no_observations_still_account_for_initial_mass_at_zero_time(time, deviation):
    space = StateSpace(("live", "dead"), (False, None), 1)

    def evaluate():
        return path_likelihood(
            space,
            [0.5, 0.5 + deviation],
            [RateSegment(0, 1, [[0, 0], [0, 0]])],
            [],
            terminal=TerminalObservation("panel", time),
            contract=contract(),
            tolerance=TOL,
        )

    if deviation > 0:
        with pytest.raises(FloatingPointError, match="probability exceeds one"):
            evaluate()
    else:
        result = evaluate()
        assert result["likelihood"] < 1
        assert result["log_likelihood"] == pytest.approx(log(1 + deviation), abs=TOL / 100)
        assert result["normalizers"][0] < 1


def test_original_decimal_rate_all_state_boundary_remains_explicit(monkeypatch):
    import demeter.analysis.longitudinal_likelihood as module

    space, q, _ = event_model()  # Original [-.3, .1, .2] numerical boundary.
    kernel = module.expm(np.asarray(q))

    def evaluate():
        return path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(0, 1, q)],
            [PanelObservation(1, [1, 1, 1], "coarsened")],
            terminal=TerminalObservation("panel", 1),
            contract=contract(missingness="explicit_coarsening"),
            tolerance=TOL,
        )

    # Native expm and forward-sum arithmetic differ by platform. The analytic
    # all-state probability is one; either a bounded result or an explicit
    # numerical failure is allowed, never an out-of-range returned probability.
    try:
        result = evaluate()
    except FloatingPointError as error:
        assert "probability exceeds one" in str(error)
    else:
        assert result["likelihood"] == pytest.approx(1, abs=TOL)
        assert result["likelihood"] <= 1
    # Deterministically retain the observed one-ulp surplus failure on every platform.
    rounded = kernel.copy()
    rounded[0, 0] += 2 * np.spacing(1.0)
    monkeypatch.setattr(module, "expm", lambda matrix: rounded)
    with pytest.raises(FloatingPointError, match="probability exceeds one"):
        evaluate()


def test_exact_first_entry_density_is_allowed_above_one():
    result = event_path("exact_first_entry", time=0, lam=4, mu=1)
    assert result["likelihood"] == 4
    assert result["contribution_kind"] == "density"
    assert result["units"] == "per_year"


def test_finite_near_ceiling_grouped_event_hazards_cannot_return_infinite_density():
    maximum = np.finfo(float).max
    q = [[-maximum, maximum * (0.5 + 1e-12), maximum * (0.5 + 1e-12), 0]] + [[0] * 4] * 3
    space = StateSpace(("live", "event1", "event2", "dead"), (False, True, True, None), 3)
    # Relative roundoff allowance legitimately accepts the finite input entries;
    # the aggregate exact-event hazard still has no finite binary64 representation.
    validate_generator(space, q, tolerance=1e-10)
    with np.errstate(over="raise", invalid="raise"):
        with pytest.raises(FloatingPointError, match="aggregate hazard is not finite"):
            path_likelihood(
                space,
                [1, 0, 0, 0],
                [RateSegment(0, 1, q)],
                [],
                terminal=TerminalObservation("exact_first_entry", 0, event="event"),
                contract=contract("first_entry_ascertainment"),
                event_targets={"event": (1, 2), "death": (3,)},
                tolerance=1e-10,
            )


def test_largest_finite_exact_event_density_remains_supported_at_zero_time():
    maximum = np.finfo(float).max
    result = event_path("exact_first_entry", time=0, lam=maximum, mu=0)
    assert np.isfinite(result["likelihood"])
    assert result["likelihood"] == pytest.approx(maximum, rel=1e-13)
    assert np.isfinite(result["log_likelihood"])
    assert result["contribution_kind"] == "density"


def test_nonfinite_exact_event_factor_is_rejected_without_clamping(monkeypatch):
    import demeter.analysis.longitudinal_likelihood as module

    original = module._advance

    def corrupt_forward(*args, **kwargs):
        alpha, support, increment = original(*args, **kwargs)
        return np.full_like(alpha, np.inf), support, increment

    monkeypatch.setattr(module, "_advance", corrupt_forward)
    with pytest.raises(FloatingPointError, match="density factor is not finite"):
        event_path("exact_first_entry", time=0)


@pytest.mark.parametrize("log_increment", [float("inf"), float("nan")])
def test_nonfinite_accumulated_log_likelihood_is_rejected(monkeypatch, log_increment):
    import demeter.analysis.longitudinal_likelihood as module

    original = module._advance

    def corrupt_log(*args, **kwargs):
        alpha, support, _ = original(*args, **kwargs)
        return alpha, support, log_increment

    monkeypatch.setattr(module, "_advance", corrupt_log)
    with pytest.raises(FloatingPointError, match="Log likelihood"):
        event_path("exact_first_entry", time=0)


def test_nonfinite_displayed_density_is_rejected(monkeypatch):
    import demeter.analysis.longitudinal_likelihood as module

    monkeypatch.setattr(module, "exp", lambda _: float("inf"))
    with pytest.raises(FloatingPointError, match="Likelihood is outside finite"):
        event_path("exact_first_entry", time=0)


def test_rank_threshold_remains_a_distinct_relative_design_choice():
    result = observable_jacobian(
        lambda x: [x[0], 0.1 * x[1]], [1, 1], [1e-4] * 2, rank_tolerance=0.5
    )
    assert result["relative_rank_tolerance"] == 0.5
    assert result["local_numerical_rank"] == 1


def contract(
    stopping="administrative_observation_end", *, missingness="no_missing", treatment="held_fixed"
):
    return SoftwareObservationContract(
        time_unit="years",
        observation_timing="exogenous",
        missingness=missingness,
        selection="synthetic_fixed_cohort",
        treatment=treatment,
        stopping=stopping,
    )


def event_model(lam=0.1, mu=0.2):
    space = StateSpace(("P", "D", "dead"), (False, True, None), 2)
    q = [[-(lam + mu), lam, mu], [0, 0, 0], [0, 0, 0]]
    return space, q, {"diabetes": (1,), "death": (2,)}


def event_path(kind, *, time=1.0, lam=0.1, mu=0.2, start=None, observations=()):
    space, q, targets = event_model(lam, mu)
    stopping = (
        "independent_right_censoring" if kind == "right_censor" else "first_entry_ascertainment"
    )
    return path_likelihood(
        space,
        [1.0, 0.0, 0.0],
        [RateSegment(0, max(time, 1), q)],
        observations,
        terminal=TerminalObservation(
            kind,
            time,
            event=None if kind == "right_censor" else "diabetes",
            interval_start_year=start,
        ),
        contract=contract(stopping),
        event_targets=targets,
        tolerance=TOL,
    )


def uniformization(q, time):
    """Independent Poisson jump-chain sum, deliberately not a call to expm."""
    q = np.asarray(q, dtype=float)
    rate = max(-np.diag(q))
    if rate == 0:
        return np.eye(len(q))
    jump = np.eye(len(q)) + q / rate
    power = np.eye(len(q))
    weight = exp(-rate * time)
    total = weight * power
    for count in range(1, 150):
        power = power @ jump
        weight *= rate * time / count
        total += weight * power
    return total


def five_state_generator(rates):
    q = np.zeros((5, 5))
    edges = ((0, 1), (1, 0), (1, 2), (2, 3), (3, 2), (0, 4), (1, 4), (2, 4), (3, 4))
    for (source, target), rate in zip(edges, rates, strict=True):
        q[source, target] = rate
    np.fill_diagonal(q, -q.sum(axis=1))
    return q


def test_matrix_exponential_matches_independent_jump_chain():
    space = StateSpace(("N", "P", "D", "C", "dead"), (False, False, True, True, None), 4)
    q = five_state_generator([0.08, 0.10, 0.06, 0.12, 0.09, 0.01, 0.015, 0.03, 0.02])
    actual = transition_matrix(space, q, 3.0, tolerance=TOL)
    assert actual == pytest.approx(uniformization(q, 3.0), abs=TOL)
    assert actual.sum(axis=1) == pytest.approx(np.ones(5), abs=TOL)
    assert actual[4] == pytest.approx([0, 0, 0, 0, 1])


@pytest.mark.parametrize("time", [0, 0.5, 1, 3])
def test_reversible_two_state_probability_has_known_closed_form(time):
    space = StateSpace(("N", "P", "dead"), (False, False, None), 2)
    a, b = 0.1, 0.2
    q = [[-a, a, 0], [b, -b, 0], [0, 0, 0]]
    result = transition_matrix(space, q, time, tolerance=TOL)
    expected = b / (a + b) * -expm1(-(a + b) * time)
    assert result[1, 0] == pytest.approx(expected, abs=TOL)
    assert result[1, 1] == pytest.approx(1 - expected, abs=TOL)


def test_linked_panel_forward_matches_explicit_hidden_path_enumeration():
    space = StateSpace(("N", "P", "dead"), (False, False, None), 2)
    q = [[-0.12, 0.10, 0.02], [0.20, -0.23, 0.03], [0, 0, 0]]
    initial = np.array([0.6, 0.4, 0])
    first, second = np.array([0.2, 0.8, 0]), np.array([0.7, 0.3, 0])
    p1, p2 = uniformization(q, 1), uniformization(q, 2)
    expected = sum(
        initial[i] * p1[i, j] * first[j] * p2[j, k] * second[k]
        for i, j, k in product(range(3), repeat=3)
    )
    actual = path_likelihood(
        space,
        initial,
        [RateSegment(0, 3, q)],
        [PanelObservation(1, first, "category"), PanelObservation(3, second, "category")],
        terminal=TerminalObservation("panel", 3),
        contract=contract(),
        tolerance=TOL,
    )
    independent_marginals = float(initial @ p1 @ first) * float(
        initial @ uniformization(q, 3) @ second
    )
    assert actual["likelihood"] == pytest.approx(expected, abs=TOL)
    assert actual["likelihood"] != pytest.approx(independent_marginals, abs=1e-6)
    assert actual["log_likelihood"] == pytest.approx(log(expected))


def test_scaled_panel_retains_finite_log_when_float_probability_underflows():
    space, _, _ = event_model()
    observations = [
        PanelObservation(float(i), [1e-20, 1e-20, 1e-20], "category") for i in range(50)
    ]
    actual = path_likelihood(
        space,
        [1, 0, 0],
        [RateSegment(0, 50, np.zeros((3, 3)))],
        observations,
        terminal=TerminalObservation("panel", 50),
        contract=contract(),
        tolerance=TOL,
    )
    assert actual["likelihood"] == 0
    assert actual["log_likelihood"] == pytest.approx(50 * log(1e-20))
    assert actual["floating_likelihood_underflow"] is True
    assert actual["structurally_zero"] is False


def test_impossible_observation_retains_zero_and_negative_infinity():
    space, q, _ = event_model()
    actual = path_likelihood(
        space,
        [1, 0, 0],
        [RateSegment(0, 1, q)],
        [PanelObservation(0, [0, 1, 0], "category")],
        terminal=TerminalObservation("panel", 1),
        contract=contract(),
        tolerance=TOL,
    )
    assert actual["likelihood"] == 0
    assert actual["log_likelihood"] == -np.inf
    assert actual["structurally_zero"] is True
    assert actual["floating_likelihood_underflow"] is False


def test_panel_episode_end_does_not_impute_alive():
    space, q, _ = event_model()
    actual = path_likelihood(
        space,
        [1, 0, 0],
        [RateSegment(0, 3, q)],
        [],
        terminal=TerminalObservation("panel", 3),
        contract=contract("observation_sequence_only"),
        tolerance=TOL,
    )
    assert actual["likelihood"] == pytest.approx(1)
    assert actual["panel_termination_implies_alive"] is False
    assert transition_matrix(space, q, 3, tolerance=TOL)[0, 2] > 0


def test_exact_interval_and_censor_modes_have_distinct_known_contributions():
    time, lam, mu = 3, 0.1, 0.2
    survival = exp(-(lam + mu) * time)
    density = event_path("exact_first_entry", time=time, lam=lam, mu=mu)
    interval = event_path("interval_first_entry", time=time, start=0, lam=lam, mu=mu)
    censor = event_path("right_censor", time=time, lam=lam, mu=mu)
    assert density["likelihood"] == pytest.approx(survival * lam)
    assert density["units"] == "per_year"
    assert density["contribution_kind"] == "density"
    assert interval["likelihood"] == pytest.approx(lam / (lam + mu) * (1 - survival))
    assert interval["units"] == censor["units"] == "dimensionless"
    assert censor["likelihood"] == pytest.approx(survival)
    assert censor["likelihood"] + interval["likelihood"] < 1  # Death is not dropped.


def test_exact_density_can_exceed_one_and_zero_interval_is_not_density():
    density = event_path("exact_first_entry", time=0, lam=2, mu=0)
    interval = event_path("interval_first_entry", time=0, start=0, lam=2, mu=0)
    assert density["likelihood"] == 2
    assert density["log_likelihood"] == pytest.approx(log(2))
    assert interval["likelihood"] == 0
    assert interval["log_likelihood"] == -np.inf


def test_tiny_interval_uses_positive_integral_not_cdf_subtraction():
    width, lam, mu = 1e-18, 0.1, 0.2
    actual = event_path("interval_first_entry", time=width, start=0, lam=lam, mu=mu)
    expected = lam / (lam + mu) * -expm1(-(lam + mu) * width)
    assert actual["likelihood"] > 0
    assert actual["likelihood"] == pytest.approx(expected, rel=1e-12, abs=0)


def test_piecewise_interval_can_cross_treatment_phase_boundary():
    space, q1, targets = event_model(0.1, 0.2)
    _, q2, _ = event_model(0.3, 0.4)
    actual = path_likelihood(
        space,
        [1, 0, 0],
        [RateSegment(0, 1, q1), RateSegment(1, 2, q2)],
        [],
        terminal=TerminalObservation(
            "interval_first_entry", 1.5, event="diabetes", interval_start_year=0.5
        ),
        contract=contract("first_entry_ascertainment", treatment="piecewise_declared"),
        event_targets=targets,
        tolerance=TOL,
    )
    expected = exp(-0.3 * 0.5) * (0.1 / 0.3) * -expm1(-0.3 * 0.5)
    expected += exp(-0.3) * (0.3 / 0.7) * -expm1(-0.7 * 0.5)
    assert actual["likelihood"] == pytest.approx(expected, abs=TOL)


@pytest.mark.parametrize("time,lam", [(1, 0.3), (2, 0.3)])
def test_exact_event_boundary_uses_declared_right_or_final_left_rate(time, lam):
    space, q1, targets = event_model(0.1, 0.2)
    _, q2, _ = event_model(0.3, 0.4)
    actual = path_likelihood(
        space,
        [1, 0, 0],
        [RateSegment(0, 1, q1), RateSegment(1, 2, q2)],
        [],
        terminal=TerminalObservation("exact_first_entry", time, event="diabetes"),
        contract=contract("first_entry_ascertainment", treatment="piecewise_declared"),
        event_targets=targets,
        tolerance=TOL,
    )
    expected = exp(-0.3 * min(time, 1) - 0.7 * max(0, time - 1)) * lam
    assert actual["likelihood"] == pytest.approx(expected, abs=TOL)


def test_first_entry_density_retains_linked_panel_prefix():
    space = StateSpace(("N", "P", "D", "dead"), (False, False, True, None), 3)
    q = [[-0.15, 0, 0.1, 0.05], [0, -0.35, 0.3, 0.05], [0, 0, 0, 0], [0, 0, 0, 0]]
    actual = path_likelihood(
        space,
        [0.5, 0.5, 0, 0],
        [RateSegment(0, 2, q)],
        [PanelObservation(1, [0.2, 0.8, 0, 0], "category")],
        terminal=TerminalObservation("exact_first_entry", 2, event="diabetes"),
        contract=contract("first_entry_ascertainment"),
        event_targets={"diabetes": (2,), "death": (3,)},
        tolerance=TOL,
    )
    expected = 0.5 * 0.2 * exp(-0.15 * 2) * 0.1 + 0.5 * 0.8 * exp(-0.35 * 2) * 0.3
    marginal_visit = 0.5 * 0.2 * exp(-0.15) + 0.5 * 0.8 * exp(-0.35)
    marginal_density = 0.5 * exp(-0.15 * 2) * 0.1 + 0.5 * exp(-0.35 * 2) * 0.3
    assert actual["likelihood"] == pytest.approx(expected, abs=TOL)
    assert actual["likelihood"] != pytest.approx(marginal_visit * marginal_density, abs=1e-6)


def test_endpoint_occupancy_is_not_first_entry_when_later_control_is_allowed():
    space = StateSpace(("N", "P", "D", "C", "dead"), (False, False, True, True, None), 4)
    q = five_state_generator([0, 0, 0.1, 0.2, 0, 0, 0, 0, 0])
    endpoint = transition_matrix(space, q, 3, tolerance=TOL)[1, 2]
    first = path_likelihood(
        space,
        [0, 1, 0, 0, 0],
        [RateSegment(0, 3, q)],
        [],
        terminal=TerminalObservation(
            "interval_first_entry", 3, event="diabetes", interval_start_year=0
        ),
        contract=contract("first_entry_ascertainment"),
        event_targets={"diabetes": (2, 3), "death": (4,)},
        tolerance=TOL,
    )
    assert endpoint == pytest.approx(0.1 / (0.2 - 0.1) * (exp(-0.1 * 3) - exp(-0.2 * 3)))
    assert first["likelihood"] == pytest.approx(-expm1(-0.1 * 3))
    assert first["likelihood"] > endpoint


def test_non_event_endpoint_is_joint_not_survival_conditioned():
    space = StateSpace(("N", "P", "D", "dead"), (False, False, True, None), 3)
    q = [[-0.1, 0, 0.1, 0], [0, -0.2, 0.2, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    actual = path_likelihood(
        space,
        [0.5, 0.5, 0, 0],
        [RateSegment(0, 1, q)],
        [],
        terminal=TerminalObservation("non_event_endpoint", 1, endpoint_emission=(0, 1, 0, 0)),
        contract=contract("non_event_assessment"),
        event_targets={"diabetes": (2,), "death": (3,)},
        tolerance=TOL,
    )
    assert actual["likelihood"] == pytest.approx(0.5 * exp(-0.2))
    assert actual["units"] == "dimensionless"


def test_finite_time_killed_underflow_is_not_declared_structural_zero():
    with pytest.raises(FloatingPointError, match="survival underflowed"):
        event_path("right_censor", time=10000)


def test_immutable_models_snapshot_caller_owned_collections():
    labels, history = ["P", "D", "dead"], [False, True, None]
    space = StateSpace(labels, history, 2)
    _, q, _ = event_model()
    segment = RateSegment(0, 1, q)
    weights = [1, 0, 0]
    observation = PanelObservation(0, weights, "category")
    labels[0], history[0], q[0][1], weights[0] = "changed", True, 9, 0
    assert space.labels == ("P", "D", "dead")
    assert space.diagnosis_history == (False, True, None)
    assert segment.generator[0][1] == 0.1
    assert observation.emission == (1, 0, 0)
    with pytest.raises(FrozenInstanceError):
        segment.start_year = 2
    with pytest.raises(TypeError):
        segment.generator[0][1] = 2


@pytest.mark.parametrize(
    "labels,history,death",
    [
        (["P", "P", "dead"], [False, True, None], 2),
        ([["P"], "D", "dead"], [False, True, None], 2),
        (["P", "D", "dead"], [False, None, None], 2),
        (["P", "D", "dead"], [False, True, False], 2),
        (["P", "D", "dead"], [False, True, None], True),
    ],
)
def test_state_space_rejects_ambiguous_history_or_dimensions(labels, history, death):
    with pytest.raises(ValueError):
        StateSpace(labels, history, death)


@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), -1])
def test_time_requires_real_finite_nonnegative_years(value):
    with pytest.raises(ValueError):
        PanelObservation(value, [1, 0, 0], "category")


@pytest.mark.parametrize(
    "weights",
    [[True, 0, 0], [1.1, 0, 0], [-0.1, 1, 0], [1, float("nan"), 0], ["1", "0", "0"], [[1, 0, 0]]],
)
def test_emissions_do_not_coerce_or_hide_invalid_values(weights):
    with pytest.raises(ValueError):
        PanelObservation(0, weights, "category")


def test_categorical_matrix_requires_exclusive_probability_rows():
    matrix = [[0.2, 0.8], [0.6, 0.4], [1, 0]]
    assert validate_categorical_emissions(matrix, state_count=3, tolerance=TOL) == pytest.approx(
        np.asarray(matrix)
    )
    for invalid in (
        [[0.2, 0.7], [0.6, 0.4], [1, 0]],
        [[1.1, -0.1]] * 3,
        [[True, 0]] * 3,
        np.ma.array(matrix, mask=False),
    ):
        with pytest.raises(ValueError):
            validate_categorical_emissions(invalid, state_count=3, tolerance=TOL)


@pytest.mark.parametrize(
    "mutation",
    [
        "row_sum",
        "negative_off_diagonal",
        "death_exit",
        "erase_history",
        "tiny_erase_history",
        "nan",
        "bool",
        "complex",
    ],
)
def test_generator_rejects_invalid_rates_and_never_erases_history(mutation):
    space, q, _ = event_model()
    if mutation == "row_sum":
        q[0][0] = -0.5
    elif mutation == "negative_off_diagonal":
        q[0][1] = -0.1
    elif mutation == "death_exit":
        q[2] = [0.1, 0, -0.1]
    elif mutation in ("erase_history", "tiny_erase_history"):
        rate = 0.1 if mutation == "erase_history" else 1e-16
        q[1] = [rate, -rate, 0]
    elif mutation == "nan":
        q[0][1] = float("nan")
    elif mutation == "bool":
        q[0][1] = True
    else:
        q[0][1] = 0.1 + 0j
    with pytest.raises(ValueError):
        validate_generator(space, q, tolerance=TOL)


@pytest.mark.parametrize(
    "field",
    ["time_unit", "observation_timing", "missingness", "selection", "treatment", "stopping"],
)
def test_unknown_required_assumptions_cannot_default(field):
    fields = dict(
        time_unit="years",
        observation_timing="exogenous",
        missingness="no_missing",
        selection="synthetic_fixed_cohort",
        treatment="held_fixed",
        stopping="administrative_observation_end",
    )
    fields[field] = "unknown"
    with pytest.raises(ValueError, match="explicitly declared"):
        SoftwareObservationContract(**fields)


@pytest.mark.parametrize(
    "segments", [[(0.1, 1)], [(0, 0.4), (0.5, 1)], [(0, 0.6), (0.5, 1)], [(0, 0.9)]]
)
def test_schedule_does_not_guess_origin_gaps_overlaps_or_final_rates(segments):
    space, q, _ = event_model()
    with pytest.raises(ValueError, match="schedule"):
        path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(a, b, q) for a, b in segments],
            [],
            terminal=TerminalObservation("panel", 1),
            contract=contract(),
            tolerance=TOL,
        )


def test_coarsened_unknown_keeps_death_possible_under_explicit_assumption():
    # Binary-representable hazards isolate observation semantics. The original
    # decimal-rate numerical boundary remains covered separately below.
    space, q, _ = event_model(lam=0.125, mu=0.25)
    obs = [PanelObservation(1, [1, 1, 1], "coarsened")]
    with pytest.raises(ValueError, match="Coarsened"):
        path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(0, 1, q)],
            obs,
            terminal=TerminalObservation("panel", 1),
            contract=contract(),
            tolerance=TOL,
        )
    actual = path_likelihood(
        space,
        [1, 0, 0],
        [RateSegment(0, 1, q)],
        obs,
        terminal=TerminalObservation("panel", 1),
        contract=contract(missingness="explicit_coarsening"),
        tolerance=TOL,
    )
    assert actual["likelihood"] == pytest.approx(1)


def test_duplicate_out_of_order_and_unsupported_panel_times_are_rejected():
    space, q, _ = event_model()
    for times in ((0.5, 0.5), (0.8, 0.2), (0.5, 2)):
        with pytest.raises(ValueError, match="chronological"):
            path_likelihood(
                space,
                [1, 0, 0],
                [RateSegment(0, 1, q)],
                [PanelObservation(t, [1, 1, 1], "category") for t in times],
                terminal=TerminalObservation("panel", 1),
                contract=contract(),
                tolerance=TOL,
            )


def test_changing_generator_cannot_silently_change_fixed_treatment():
    space, q1, _ = event_model(0.1, 0.2)
    _, q2, _ = event_model(0.2, 0.2)
    with pytest.raises(ValueError, match="piecewise"):
        path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(0, 1, q1), RateSegment(1, 2, q2)],
            [],
            terminal=TerminalObservation("panel", 2),
            contract=contract(),
            tolerance=TOL,
        )


@pytest.mark.parametrize(
    "targets",
    [
        {"diabetes": (1,)},
        {"diabetes": (1, 2), "death": (2,)},
        {"diabetes": (1, 1), "death": (2,)},
        {"diabetes": (True,), "death": (2,)},
        {"all": (0, 1), "death": (2,)},
    ],
)
def test_event_targets_preserve_distinct_death_and_valid_risk_set(targets):
    space, q, _ = event_model()
    with pytest.raises(ValueError):
        path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(0, 1, q)],
            [],
            terminal=TerminalObservation("right_censor", 1),
            contract=contract("independent_right_censoring"),
            event_targets=targets,
            tolerance=TOL,
        )


def test_existing_event_and_stopping_mismatch_cannot_be_relabelled_censoring():
    space, q, targets = event_model()
    with pytest.raises(ValueError, match="already contains"):
        path_likelihood(
            space,
            [0, 1, 0],
            [RateSegment(0, 1, q)],
            [],
            terminal=TerminalObservation("right_censor", 1),
            contract=contract("independent_right_censoring"),
            event_targets=targets,
            tolerance=TOL,
        )
    with pytest.raises(ValueError, match="Stopping"):
        path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(0, 1, q)],
            [],
            terminal=TerminalObservation("right_censor", 1),
            contract=contract(),
            event_targets=targets,
            tolerance=TOL,
        )
    with pytest.raises(ValueError, match="exclude"):
        path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(0, 1, q)],
            [],
            terminal=TerminalObservation("non_event_endpoint", 1, endpoint_emission=(1, 1, 1)),
            contract=contract("non_event_assessment"),
            event_targets=targets,
            tolerance=TOL,
        )


def test_interval_cannot_ignore_a_later_linked_assessment():
    with pytest.raises(ValueError, match="last linked"):
        event_path(
            "interval_first_entry",
            time=1,
            start=0.2,
            observations=[PanelObservation(0.5, [1, 0, 0], "category")],
        )


def test_validation_still_checks_later_input_after_impossible_earlier_observation():
    space, q, _ = event_model()
    with pytest.raises(ValueError, match="dimensions"):
        path_likelihood(
            space,
            [1, 0, 0],
            [RateSegment(0, 1, q)],
            [PanelObservation(0, [0, 1, 0], "category"), PanelObservation(0.5, [1, 0], "category")],
            terminal=TerminalObservation("panel", 1),
            contract=contract(),
            tolerance=TOL,
        )


@pytest.mark.parametrize("tol", [0, -1, True, float("nan"), float("inf"), 1])
def test_numerical_tolerance_is_explicit_valid_and_bounded(tol):
    space, q, _ = event_model()
    with pytest.raises(ValueError):
        transition_matrix(space, q, 1, tolerance=tol)


def test_exponential_failures_are_rejected_beyond_roundoff_tolerance(monkeypatch):
    import demeter.analysis.longitudinal_likelihood as module

    space, q, _ = event_model()
    for bad in (np.array([[1, -0.01, 0], [0, 1, 0], [0, 0, 1]]), np.eye(3) * 2, np.eye(3) * np.nan):
        monkeypatch.setattr(module, "expm", lambda matrix, result=bad: result)
        with pytest.raises(FloatingPointError):
            transition_matrix(space, q, 1, tolerance=TOL)
    rounded = np.eye(3)
    rounded[0, 1] = -TOL / 2
    monkeypatch.setattr(module, "expm", lambda matrix: rounded)
    actual = transition_matrix(space, q, 1, tolerance=TOL)
    assert actual[0, 1] == 0


def test_jacobian_distinguishes_one_scalar_from_two_independent_observables():
    scalar = observable_jacobian(
        lambda x: [x[0] + x[1]], [0.1, 0.2], [1e-5, 1e-5], rank_tolerance=1e-7
    )
    full = observable_jacobian(
        lambda x: [x[0] + x[1], x[0] - x[1]], [0.1, 0.2], [1e-5, 1e-5], rank_tolerance=1e-7
    )
    assert scalar["local_numerical_rank"] == 1
    assert scalar["full_column_rank_at_point"] is False
    assert full["local_numerical_rank"] == 2
    assert np.asarray(full["jacobian"]) == pytest.approx(np.array([[1, 1], [1, -1]]), abs=1e-10)
    assert full["global_identification_established"] is False
    assert full["causal_identification_established"] is False


def test_relative_rank_cutoff_is_reported_and_zero_map_has_rank_zero():
    actual = observable_jacobian(
        lambda x: [x[0], 1e-9 * x[1]], [0.1, 0.2], [1e-5, 1e-5], rank_tolerance=1e-7
    )
    assert actual["local_numerical_rank"] == 1
    assert actual["relative_rank_tolerance"] == 1e-7
    assert actual["effective_absolute_singular_cutoff"] == pytest.approx(1e-7)
    zero = observable_jacobian(lambda x: [0, 0], [0.1, 0.2], [1e-5, 1e-5], rank_tolerance=1e-7)
    assert zero["local_numerical_rank"] == 0
    assert zero["effective_absolute_singular_cutoff"] == 0


def test_jacobian_does_not_silently_switch_to_one_sided_domain_derivative():
    def positive_only(values):
        if (values < 0).any():
            raise ValueError("Outside declared rate domain")
        return [values.sum()]

    with pytest.raises(ValueError, match="declared rate domain"):
        observable_jacobian(positive_only, [0], [1e-5], rank_tolerance=1e-7)


@pytest.mark.parametrize("steps", [[0], [-1], [float("nan")], [True], [1e-30], [1e-5, 1e-5]])
def test_jacobian_requires_representable_matching_positive_steps(steps):
    with pytest.raises(ValueError):
        observable_jacobian(lambda x: [x[0]], [1], steps, rank_tolerance=1e-7)


def test_jacobian_rejects_perturbed_observable_shape_drift():
    with pytest.raises(ValueError, match="dimensions changed"):
        observable_jacobian(
            lambda x: [x[0]] if x[0] <= 1 else [x[0], x[0]], [1], [1e-5], rank_tolerance=1e-7
        )


def test_panel_segments_match_independently_composed_phase_kernels():
    space = StateSpace(("N", "P", "dead"), (False, False, None), 2)
    q1 = [[-0.12, 0.1, 0.02], [0.2, -0.23, 0.03], [0, 0, 0]]
    q2 = [[-0.12, 0.1, 0.02], [0.24, -0.27, 0.03], [0, 0, 0]]
    initial = np.array([0, 1, 0])
    weights = [np.array([1, 1, 0]), np.array([0.2, 0.8, 0]), np.array([1, 0, 0])]
    expected = initial @ uniformization(q1, 0.5) @ np.diag(weights[0])
    expected = expected @ uniformization(q1, 0.5) @ uniformization(q2, 0.5) @ np.diag(weights[1])
    expected = float(expected @ uniformization(q2, 1.5) @ weights[2])
    actual = path_likelihood(
        space,
        initial,
        [RateSegment(0, 1, q1), RateSegment(1, 3, q2)],
        [PanelObservation(t, w, "category") for t, w in zip((0.5, 1.5, 3), weights, strict=True)],
        terminal=TerminalObservation("panel", 3),
        contract=contract(treatment="piecewise_declared"),
        tolerance=TOL,
    )
    assert actual["likelihood"] == pytest.approx(expected, abs=TOL)


def test_history_contradiction_is_impossible_without_reassigning_control():
    space = StateSpace(("N", "P", "D", "R", "dead"), (False, False, True, True, None), 4)
    q = five_state_generator([0.1, 0.2, 0.05, 0.07, 0.09, 0.01, 0.02, 0.03, 0.025])
    actual = path_likelihood(
        space,
        [0, 1, 0, 0, 0],
        [RateSegment(0, 3, q)],
        [
            PanelObservation(1, [0, 0, 1, 1, 0], "category"),
            PanelObservation(3, [1, 1, 0, 0, 0], "category"),
        ],
        terminal=TerminalObservation("panel", 3),
        contract=contract(),
        tolerance=TOL,
    )
    assert actual["structurally_zero"] is True
    assert actual["log_likelihood"] == -np.inf
    assert actual["history_erased"] is False


def test_exact_death_after_history_observation_is_density_with_shared_prefix():
    space = StateSpace(("N", "P", "D", "R", "dead"), (False, False, True, True, None), 4)
    death_rate, emission_probability = 0.03, 0.4
    q = five_state_generator([0, 0, 0, 0, 0, 0, 0, death_rate, 0])
    actual = path_likelihood(
        space,
        [0, 0, 1, 0, 0],
        [RateSegment(0, 3, q)],
        [PanelObservation(1, [0, 0, emission_probability, 0, 0], "category")],
        terminal=TerminalObservation("exact_first_entry", 3, event="death"),
        contract=contract("first_entry_ascertainment"),
        event_targets={"death": (4,)},
        tolerance=TOL,
    )
    assert actual["likelihood"] == pytest.approx(
        emission_probability * exp(-death_rate * 3) * death_rate
    )
    assert actual["units"] == "per_year"
    assert actual["likelihood"] != pytest.approx(
        transition_matrix(space, q, 3, tolerance=TOL)[2, 4]
    )


def test_competing_integrals_and_survival_partition_one_in_piecewise_model():
    space, q1, targets = event_model(0.1, 0.2)
    _, q2, _ = event_model(0.3, 0.4)
    segments = [RateSegment(0, 1, q1), RateSegment(1, 3, q2)]
    probabilities = []
    for event in ("diabetes", "death"):
        result = path_likelihood(
            space,
            [1, 0, 0],
            segments,
            [],
            terminal=TerminalObservation(
                "interval_first_entry", 3, event=event, interval_start_year=0
            ),
            contract=contract("first_entry_ascertainment", treatment="piecewise_declared"),
            event_targets=targets,
            tolerance=TOL,
        )
        probabilities.append(result["likelihood"])
    censor = path_likelihood(
        space,
        [1, 0, 0],
        segments,
        [],
        terminal=TerminalObservation("right_censor", 3),
        contract=contract("independent_right_censoring", treatment="piecewise_declared"),
        event_targets=targets,
        tolerance=TOL,
    )
    assert sum(probabilities) + censor["likelihood"] == pytest.approx(1, abs=TOL)


def test_zero_generator_and_event_hazard_have_exact_limits():
    for kind in ("exact_first_entry", "interval_first_entry", "right_censor"):
        result = event_path(
            kind, time=3, start=0 if kind == "interval_first_entry" else None, lam=0, mu=0
        )
        assert result["likelihood"] == (1 if kind == "right_censor" else 0)
        assert result["log_likelihood"] == (0 if kind == "right_censor" else -np.inf)


def test_actual_bounded_negative_exponential_correction_is_disclosed(monkeypatch):
    import demeter.analysis.longitudinal_likelihood as module

    space, q, _ = event_model()
    rounded = np.eye(3)
    rounded[0, 1] = -TOL / 2
    monkeypatch.setattr(module, "expm", lambda matrix: rounded)
    result = path_likelihood(
        space,
        [1, 0, 0],
        [RateSegment(0, 1, q)],
        [],
        terminal=TerminalObservation("panel", 1),
        contract=contract(),
        tolerance=TOL,
    )
    assert result["numerical_roundoff_corrections"] == {
        "entries_zeroed": 1,
        "most_negative_entry": -TOL / 2,
    }


@pytest.mark.parametrize("mode", ["emission", "exact", "interval", "endpoint"])
def test_positive_tiny_contributions_do_not_become_false_impossible_paths(mode):
    space = StateSpace(("N", "P", "D", "dead"), (False, False, True, None), 3)
    q = [[0, 0, 0, 0], [0, -1e-250, 1e-250, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    initial = [1, 1e-100, 0, 0]
    observations, targets = [], {"diabetes": (2,), "death": (3,)}
    if mode == "emission":
        observations = [PanelObservation(0, [0, 1e-250, 0, 0], "category")]
        terminal, assumptions, targets = TerminalObservation("panel", 1), contract(), None
    elif mode == "exact":
        terminal, assumptions = (
            TerminalObservation("exact_first_entry", 1, event="diabetes"),
            contract("first_entry_ascertainment"),
        )
    elif mode == "interval":
        terminal, assumptions = (
            TerminalObservation("interval_first_entry", 1, event="diabetes", interval_start_year=0),
            contract("first_entry_ascertainment"),
        )
    else:
        terminal, assumptions = (
            TerminalObservation("non_event_endpoint", 1, endpoint_emission=(0, 1e-250, 0, 0)),
            contract("non_event_assessment"),
        )
    with pytest.raises(FloatingPointError, match="underflowed"):
        path_likelihood(
            space,
            initial,
            [RateSegment(0, 1, q)],
            observations,
            terminal=terminal,
            contract=assumptions,
            event_targets=targets,
            tolerance=TOL,
        )
