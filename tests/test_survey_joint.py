"""Independent design arithmetic; all observations in this module are synthetic."""

from copy import deepcopy
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest

from demeter.data.nhanes import survey_proportion
from demeter.data.survey_joint import joint_proportions, linear_projection


def fixture():
    frame = pd.DataFrame(
        {"WTSAFPRP": [1.0] * 4, "SDMVSTRA": [1, 1, 2, 2], "SDMVPSU": [1, 2, 1, 2]},
        index=pd.Index([11, 22, 33, 44], name="synthetic_row"),
    )
    domains = pd.DataFrame({"all": [True] * 4}, index=frame.index)
    memberships = pd.DataFrame({"yes": [0, 1, 0, 1], "no": [1, 0, 1, 0]}, index=frame.index)
    return frame, domains, memberships


def test_complement_covariance_matches_independent_hand_arithmetic():
    frame, domains, memberships = fixture()
    actual = joint_proportions(frame, domains, memberships)
    assert actual["coordinates"] == [
        {"domain": "all", "membership": "yes"},
        {"domain": "all", "membership": "no"},
    ]
    assert actual["estimates"] == [0.5, 0.5]
    # PSU vectors are (-1/8,+1/8) and their negatives in both strata.
    # Each stratum adds twice two outer products: variance 1/16,
    # complement covariance -1/16; the two strata sum to +/-1/8.
    np.testing.assert_array_equal(actual["covariance"], [[1 / 8, -1 / 8], [-1 / 8, 1 / 8]])
    assert actual["design"] == {
        "weight": "WTSAFPRP",
        "stratum": "SDMVSTRA",
        "psu": "SDMVPSU",
        "positive_weight_n": 4,
        "strata": 2,
        "psus": 4,
        "degrees_of_freedom": 2,
        "finite_population_correction": False,
    }
    assert actual["domains"][0] == {
        "domain": "all",
        "n": 4,
        "represented_psus": 4,
        "represented_strata": 2,
        "degrees_of_freedom": 2,
        "status": "estimated",
    }


def test_cross_domain_covariance_keeps_shared_design_and_coordinate_order():
    frame, domains, memberships = fixture()
    domains["subset"] = [True, False, True, True]
    result = joint_proportions(frame, domains, memberships)
    assert result["coordinates"] == [
        {"domain": d, "membership": m} for d in ("all", "subset") for m in ("yes", "no")
    ]
    assert result["estimates"] == pytest.approx([1 / 2, 1 / 2, 1 / 3, 2 / 3])
    # Subset yes residuals: (-1/9,0,-1/9,2/9). Centered vectors
    # yield cross covariance 1/36 + 1/12 = 1/9 with all-domain yes.
    assert result["covariance"][0][2] == pytest.approx(1 / 9)
    assert result["covariance"][1][2] == pytest.approx(-1 / 9)
    assert result["covariance"][2][2] == pytest.approx(10 / 81)
    assert result["domains"][1]["degrees_of_freedom"] == 1
    v = np.asarray(result["covariance"])
    np.testing.assert_array_equal(v, v.T)
    assert np.linalg.eigvalsh(v).min() >= -1e-15
    for closure in ([1, 1, 0, 0], [0, 0, 1, 1]):
        np.testing.assert_allclose(v @ closure, 0, atol=1e-16)


def test_zero_domain_psu_is_retained_in_covariance_and_df():
    frame, domains, _ = fixture()
    domains["selected"] = [True, False, True, True]
    memberships = pd.DataFrame({"yes": [1, 0, 0, 0]}, index=frame.index)
    actual = joint_proportions(frame, domains[["selected"]], memberships)
    assert actual["estimates"] == pytest.approx([1 / 3])
    # Full-design PSU 2 in stratum 1 has zero score, but must remain.
    assert actual["covariance"][0][0] == pytest.approx(4 / 81)
    assert actual["design"]["psus"] == 4
    assert actual["domains"][0]["represented_psus"] == 3
    assert actual["domains"][0]["degrees_of_freedom"] == 1


def test_scalar_points_and_variances_match_for_overlapping_memberships():
    frame, domains, memberships = fixture()
    frame["WTSAFPRP"] = [1.2, 2.7, 8.9, 4.1]
    domains["subset"] = [True, False, True, True]
    memberships["overlap"] = [1.0, 1.0, 0.0, 1.0]
    result = joint_proportions(frame, domains, memberships)
    for i, coordinate in enumerate(result["coordinates"]):
        old = survey_proportion(
            frame, domains[coordinate["domain"]], memberships[coordinate["membership"]], 0.95
        )
        assert result["estimates"][i] == old["estimate"]
        assert result["covariance"][i][i] == pytest.approx(
            old["standard_error"] ** 2, rel=1e-14, abs=1e-18
        )


@pytest.mark.parametrize("scale", [1e-100, 100000.0, 1e100])
def test_weight_scale_changes_neither_joint_estimates_nor_covariance(scale):
    frame, domains, memberships = fixture()
    frame["WTSAFPRP"] = [1.2, 2.7, 8.9, 4.1]
    before = joint_proportions(frame, domains, memberships)
    after = joint_proportions(frame.assign(WTSAFPRP=frame.WTSAFPRP * scale), domains, memberships)
    np.testing.assert_allclose(after["estimates"], before["estimates"], rtol=1e-15)
    np.testing.assert_allclose(after["covariance"], before["covariance"], rtol=1e-15, atol=1e-17)
    assert after["design"] == before["design"]
    assert after["domains"] == before["domains"]


@pytest.mark.parametrize("constant", [0, 1])
def test_fixed_boundaries_have_exact_zero_sampling_covariance(constant):
    frame, domains, memberships = fixture()
    frame["WTSAFPRP"] = [9183.123456, 65422.76543, 3357.00023, 190.234569]
    domains["subset"] = [True, False, True, True]
    memberships["constant"] = [constant, 1 - constant, constant, constant]
    result = joint_proportions(frame, domains[["subset"]], memberships)
    assert result["estimates"][-1] == constant
    assert result["covariance"][-1] == [0.0] * 3
    assert [row[-1] for row in result["covariance"]] == [0.0] * 3


def test_empty_domain_has_none_estimates_and_covariance_not_zero():
    frame, domains, memberships = fixture()
    domains["empty"] = False
    result = joint_proportions(frame, domains, memberships)
    assert result["estimates"] == [0.5, 0.5, None, None]
    assert result["covariance"][2:] == [[None] * 4, [None] * 4]
    assert all(row[2:] == [None, None] for row in result["covariance"])
    assert result["domains"][1]["status"] == "empty_domain"
    assert result["domains"][1]["degrees_of_freedom"] == 0
    only_empty = joint_proportions(frame, domains[["empty"]], memberships)
    assert only_empty["estimates"] == [None, None]
    assert only_empty["covariance"] == [[None, None], [None, None]]


def test_full_design_singleton_is_rejected_even_for_empty_domain():
    frame, domains, memberships = fixture()
    frame.loc[22, "SDMVPSU"] = 1
    domains["all"] = False
    with pytest.raises(ValueError, match="Singleton full-design"):
        joint_proportions(frame, domains, memberships)


def test_linear_projection_preserves_partition_and_bound_dependence():
    frame, domains, _ = fixture()
    patterns = pd.DataFrame(
        {"N": [1, 0, 0, 1], "P": [0, 0, 1, 0], "NP": [0, 1, 0, 0]}, index=frame.index
    )
    source = joint_proportions(frame, domains, patterns)
    A = [[1, 0, 0], [1, 0, 1], [0, 1, 0], [0, 1, 1], [1, 1, 1], [1, -1, 0]]
    projected = linear_projection(source, A, ["Nlow", "Nhigh", "Plow", "Phigh", "sum", "contrast"])
    for i, row in enumerate(A[:5]):
        membership = patterns.to_numpy() @ row
        direct = survey_proportion(
            frame, domains["all"], pd.Series(membership, index=frame.index), 0.95
        )
        assert projected["estimates"][i] == direct["estimate"]
        assert projected["covariance"][i][i] == pytest.approx(direct["standard_error"] ** 2)
    assert projected["estimates"][4] == 1
    np.testing.assert_allclose(projected["covariance"][4], 0, atol=1e-16)
    np.testing.assert_allclose(
        projected["covariance"], np.asarray(A) @ source["covariance"] @ np.asarray(A).T
    )
    assert projected["estimates"][5] == 0.25


def test_projection_cancellation_matches_independent_exact_rational_arithmetic():
    """Arbitrary software fixture; no source effect or clinical estimate."""
    source = {
        "coordinates": [{"domain": "toy", "membership": str(i)} for i in range(3)],
        "estimates": [0.5] * 3,
        "covariance": [[0.25] * 3 for _ in range(3)],
    }
    A = [[1e17, 2.0, -1e17], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    expected_estimates = [
        float(sum(Fraction(a) * Fraction(p) for a, p in zip(row, source["estimates"], strict=True)))
        for row in A
    ]
    expected_covariance = [
        [
            float(
                sum(
                    Fraction(left[i]) * Fraction(source["covariance"][i][j]) * Fraction(right[j])
                    for i in range(3)
                    for j in range(3)
                )
            )
            for right in A
        ]
        for left in A
    ]
    actual = linear_projection(source, A, ["cancellation", "known", "zero"])
    assert expected_estimates == [1.0, 0.5, 0.0]
    assert expected_covariance == [[1.0, 0.5, 0.0], [0.5, 0.25, 0.0], [0.0, 0.0, 0.0]]
    assert actual["estimates"] == expected_estimates
    assert actual["covariance"] == expected_covariance


@pytest.mark.parametrize("failure", ["sum_overflow", "opposing_infinite_products", "stage_two"])
def test_projection_nonfinite_sums_and_products_fail_explicitly(failure):
    source = {
        "coordinates": [{"domain": "toy", "membership": str(i)} for i in range(2)],
        "estimates": [1.0, 1.0],
        "covariance": [[0.0, 0.0], [0.0, 0.0]],
    }
    if failure == "sum_overflow":
        A = [[1e308, 1e308]]
    elif failure == "opposing_infinite_products":
        source["estimates"] = [0.0, 0.0]
        source["covariance"] = [[1e308, -1e308], [-1e308, 1e308]]
        A = [[2.0, 2.0]]
    else:
        source["estimates"] = [0.0, 0.0]
        source["covariance"] = [[1e308, 0.0], [0.0, 0.0]]
        A = [[1.5, 0.0]]  # A V is finite, while A V A^T is not.
    with pytest.raises(ValueError, match="Nonfinite linear projection"):
        linear_projection(source, A, ["unrepresentable"])


def test_unavailable_projection_does_not_raise_from_hidden_overflow():
    source = {
        "coordinates": [
            {"domain": "toy", "membership": "known"},
            {"domain": "toy", "membership": "unavailable"},
        ],
        "estimates": [1e308, None],
        "covariance": [[1e308, None], [None, None]],
    }
    actual = linear_projection(source, [[2.0, 1.0], [0.0, 0.0]], ["unknown", "zero"])
    assert actual["estimates"] == [None, 0.0]
    assert actual["covariance"] == [[None, None], [None, 0.0]]


def test_projection_does_not_impute_unavailable_inputs_with_zero():
    frame, domains, memberships = fixture()
    domains["empty"] = False
    source = joint_proportions(frame, domains, memberships)
    result = linear_projection(
        source, [[1, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]], ["sum", "unknown", "zero"]
    )
    assert result["estimates"] == [1.0, None, 0.0]
    assert result["covariance"] == [[0.0, None, 0.0], [None, None, None], [0.0, None, 0.0]]
    all_unknown = joint_proportions(frame, domains[["empty"]], memberships)
    assert linear_projection(all_unknown, [[0, 0], [1, 0]], ["zero", "unknown"])["estimates"] == [
        0.0,
        None,
    ]


def test_inputs_are_not_mutated_and_nullable_boolean_indicators_are_supported():
    frame, domains, memberships = fixture()
    domains = domains.astype("boolean")
    memberships = memberships.astype("boolean")
    originals = [value.copy(deep=True) for value in (frame, domains, memberships)]
    result = joint_proportions(frame, domains, memberships)
    preserved = deepcopy(result)
    linear_projection(result, [[1, -1]], ["contrast"])
    assert result == preserved
    for value, old in zip((frame, domains, memberships), originals, strict=True):
        pd.testing.assert_frame_equal(value, old)


@pytest.mark.parametrize("target", ["frame", "domains", "memberships"])
def test_duplicate_and_unaligned_row_indices_fail(target):
    frame, domains, memberships = fixture()
    values = {"frame": frame, "domains": domains, "memberships": memberships}
    values[target].index = [11, 11, 33, 44]
    with pytest.raises(ValueError, match="unique"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("multi_index", [False, True])
def test_missing_aligned_indices_are_rejected(multi_index):
    frame, domains, memberships = fixture()
    index = (
        pd.MultiIndex.from_tuples([(1, 1), (1, 2), (2, 1), (2, np.nan)])
        if multi_index
        else pd.Index([11, 22, 33, np.nan])
    )
    for value in (frame, domains, memberships):
        value.index = index
    with pytest.raises(ValueError, match="unique rows"):
        joint_proportions(frame, domains, memberships)


def test_valid_multiindex_is_supported_without_exporting_row_identifiers():
    frame, domains, memberships = fixture()
    index = pd.MultiIndex.from_tuples([(1, 1), (1, 2), (2, 1), (2, 2)])
    for value in (frame, domains, memberships):
        value.index = index
    result = joint_proportions(frame, domains, memberships)
    assert result["estimates"] == [0.5, 0.5]
    np.testing.assert_array_equal(result["covariance"], [[0.125, -0.125], [-0.125, 0.125]])
    assert "index" not in result


@pytest.mark.parametrize("target", ["domains", "memberships"])
def test_reversed_or_different_indicator_index_is_not_silently_reindexed(target):
    frame, domains, memberships = fixture()
    values = {"domains": domains, "memberships": memberships}
    values[target].index = frame.index[::-1]
    with pytest.raises(ValueError, match="aligned"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("label", ["", "  ", 1, None, ("x", "y")])
@pytest.mark.parametrize("target", ["domains", "memberships"])
def test_malformed_indicator_labels_fail(label, target):
    frame, domains, memberships = fixture()
    if target == "domains":
        domains.columns = [label]
    else:
        memberships.columns = [label, "other"]
    with pytest.raises(ValueError, match="labels"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("target", ["domains", "memberships"])
def test_duplicate_or_absent_columns_fail(target):
    frame, domains, memberships = fixture()
    if target == "domains":
        domains = pd.concat([domains, domains], axis=1)
    else:
        memberships.columns = ["same", "same"]
    with pytest.raises(ValueError, match="labels"):
        joint_proportions(frame, domains, memberships)
    frame, domains, memberships = fixture()
    if target == "domains":
        domains = domains.iloc[:, :0]
    else:
        memberships = memberships.iloc[:, :0]
    with pytest.raises(ValueError, match="labels"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("value", [0, -1, np.nan, np.inf, True, "1", 1 + 0j])
def test_bad_weights_are_rejected_without_coercion(value):
    frame, domains, memberships = fixture()
    frame["WTSAFPRP"] = pd.Series([value] * 4, index=frame.index)
    with pytest.raises(ValueError, match="Weights"):
        joint_proportions(frame, domains, memberships)


def test_underflowed_nonempty_domain_is_not_declared_empty_or_zero():
    frame, domains, memberships = fixture()
    frame["WTSAFPRP"] = [5e-324, 1e308, 5e-324, 1e308]
    domains["all"] = [True, False, True, False]
    with pytest.raises(ValueError, match="denominator is numerically unavailable"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("column", ["SDMVSTRA", "SDMVPSU"])
@pytest.mark.parametrize("value", [np.nan, np.inf, True, "1", 1 + 0j])
def test_missing_or_wrong_design_dtype_fails(column, value):
    frame, domains, memberships = fixture()
    frame[column] = pd.Series([value] * 4, index=frame.index)
    with pytest.raises(ValueError, match=column):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("column", ["WTSAFPRP", "SDMVSTRA", "SDMVPSU"])
def test_missing_design_or_weight_column_fails(column):
    frame, domains, memberships = fixture()
    with pytest.raises(ValueError, match="columns"):
        joint_proportions(frame.drop(columns=column), domains, memberships)


@pytest.mark.parametrize("values", [[1] * 4, ["yes"] * 4, [True, False, True, None]])
def test_nonboolean_or_missing_domains_fail(values):
    frame, domains, memberships = fixture()
    domains["all"] = values
    with pytest.raises(ValueError, match="Boolean"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("target", ["domains", "memberships"])
def test_nullable_boolean_missingness_is_rejected(target):
    frame, domains, memberships = fixture()
    if target == "domains":
        domains["all"] = pd.array([True, False, True, pd.NA], dtype="boolean")
    else:
        memberships["yes"] = pd.array([True, False, True, pd.NA], dtype="boolean")
    with pytest.raises(ValueError, match="nonmissing"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize(
    "values", [[2] * 4, [0.5] * 4, [np.nan] * 4, [np.inf] * 4, ["1"] * 4, [1 + 0j] * 4]
)
def test_nonbinary_or_missing_memberships_fail(values):
    frame, domains, memberships = fixture()
    memberships["yes"] = values
    with pytest.raises(ValueError, match="Memberships"):
        joint_proportions(frame, domains, memberships)


@pytest.mark.parametrize("target", ["frame", "domains", "memberships"])
def test_non_dataframe_and_empty_frame_are_rejected(target):
    frame, domains, memberships = fixture()
    values = [frame, domains, memberships]
    values[("frame", "domains", "memberships").index(target)] = None
    with pytest.raises(ValueError):
        joint_proportions(*values)
    with pytest.raises(ValueError):
        joint_proportions(frame.iloc[:0], domains.iloc[:0], memberships.iloc[:0])


@pytest.mark.parametrize(
    "A",
    [
        [[True, 0]],
        [["1", 0]],
        [[np.inf, 0]],
        [[np.nan, 0]],
        [[1 + 0j, 0]],
        [[1], [1, 2]],
        [1, 0],
        np.array([1, 0]),
        [[1, 0, 0]],
        [[np.array(1), 0]],
        None,
    ],
)
def test_malformed_projection_matrices_fail(A):
    result = joint_proportions(*fixture())
    with pytest.raises(ValueError, match="Projection"):
        linear_projection(result, A, ["test"])


@pytest.mark.parametrize("labels", [None, "test", [""], [1], ["same", "same"], []])
def test_malformed_projection_labels_fail(labels):
    result = joint_proportions(*fixture())
    with pytest.raises(ValueError, match="Projection"):
        linear_projection(result, [[1, 0]], labels)


@pytest.mark.parametrize(
    "mutation",
    [
        "bad_estimate",
        "missing_covariance",
        "bad_coordinate",
        "duplicate_coordinate",
        "wrong_dimension",
        "false_unavailable",
    ],
)
def test_malformed_joint_results_are_not_silently_projected(mutation):
    result = joint_proportions(*fixture())
    if mutation == "bad_estimate":
        result["estimates"][0] = True
    elif mutation == "missing_covariance":
        result["covariance"][0][0] = None
    elif mutation == "bad_coordinate":
        result["coordinates"][0]["domain"] = ""
    elif mutation == "duplicate_coordinate":
        result["coordinates"][1] = result["coordinates"][0].copy()
    elif mutation == "wrong_dimension":
        result["covariance"].pop()
    else:
        result["estimates"][0] = None
    with pytest.raises(ValueError):
        linear_projection(result, [[1, 0]], ["test"])
