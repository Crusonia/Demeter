"""Independent finite-record checks for conditional source-panel reconstruction."""

from copy import deepcopy
from fractions import Fraction
from itertools import product

import pytest

from demeter.analysis.source_panel_reconstruction import reconstruct_source_panels

SLOTS = ("normal", "prediabetes", "total_diabetes", "mortality")


def row(values):
    return {"baseline_count": sum(values), **dict(zip(SLOTS, values, strict=True))}


def fixture():
    return (
        5,
        {"assay_a": 3, "assay_b": 2},
        {
            "assay_a": {"normal": row((1, 0, 0, 0)), "prediabetes": row((1, 0, 1, 0))},
            "assay_b": {"normal": row((0, 0, 0, 2)), "prediabetes": row((0, 1, 0, 0))},
        },
    )


def calculate(n, margins, panels, declared=True):
    return reconstruct_source_panels(n, margins, panels, source_subset_identity_declared=declared)


def rational(value):
    return None if value is None else Fraction(value["numerator"], value["denominator"])


def test_exhaustive_small_record_partitions_and_original_margins():
    """Enumerate recorded slots directly; reverse panels need not share outcomes."""
    for values in product(range(4), repeat=8):
        selected = sum(values)
        if selected > 3:
            continue
        normal, prediabetes = values[:4], values[4:]
        normal_n, prediabetes_n = sum(normal), sum(prediabetes)
        panels = {
            "assay_a": {"normal": row(normal), "prediabetes": row(prediabetes)},
            "assay_b": {
                "normal": row(tuple(reversed(prediabetes))),
                "prediabetes": row(tuple(reversed(normal))),
            },
        }
        for original in range(selected, 5):
            for original_pre in range(prediabetes_n, original - normal_n + 1):
                margins = {"assay_a": original_pre, "assay_b": original - original_pre}
                result = calculate(original, margins, panels)
                assert result["counts"] == {
                    "original_unique_people": original,
                    "selected_unique_people": selected,
                    "unrepresented_baseline_margin": original - selected,
                }
                for assay, panel in panels.items():
                    assert (
                        sum(
                            item["original_baseline_count"]
                            for item in result["panels"][assay]["rows"].values()
                        )
                        == original
                    )
                    for label, source in panel.items():
                        output = result["panels"][assay]["rows"][label]
                        original_row = (
                            margins[assay] if label == "prediabetes" else original - margins[assay]
                        )
                        selected_row = source["baseline_count"]
                        expected = {slot: source[slot] for slot in SLOTS}
                        expected["unrepresented_baseline_margin"] = original_row - selected_row
                        assert output["source_partition_counts"] == expected
                        assert sum(expected.values()) == original_row
                        assert output["original_row_fraction_denominator"] == original_row
                        assert output["selected_row_fraction_denominator"] == selected_row
                        for slot, count in expected.items():
                            assert rational(output["original_row_fractions"][slot]) == (
                                Fraction(count, original_row) if original_row else None
                            )
                        for slot in SLOTS:
                            assert rational(output["selected_row_fractions"][slot]) == (
                                Fraction(source[slot], selected_row) if selected_row else None
                            )
                        assert (
                            output["selected_row_fractions"]["unrepresented_baseline_margin"]
                            is None
                        )


def test_overlapping_panels_never_double_cohort_or_require_same_outcome_margins():
    result = calculate(*fixture())
    assert result["counts"]["selected_unique_people"] == 3
    assert result["interpretation"]["panels_share_population"] is True
    assert result["interpretation"]["panels_are_independent_samples"] is False
    a = result["panels"]["assay_a"]["rows"]
    b = result["panels"]["assay_b"]["rows"]
    assert sum(x["source_partition_counts"]["mortality"] for x in a.values()) == 0
    assert sum(x["source_partition_counts"]["mortality"] for x in b.values()) == 2


@pytest.mark.parametrize("declared", [False, 0, 1, "True", None])
def test_subset_premise_cannot_be_inferred_from_matching_counts(declared):
    with pytest.raises(ValueError, match="explicitly declared"):
        calculate(*fixture(), declared=declared)


@pytest.mark.parametrize("value", [True, False, 1.0, 0.0, "1", None, -1])
@pytest.mark.parametrize("location", ["original", "margin", "baseline", "slot"])
def test_counts_require_nonnegative_python_integers(value, location):
    n, margins, panels = fixture()
    if location == "original":
        n = value
    elif location == "margin":
        margins["assay_a"] = value
    elif location == "baseline":
        panels["assay_a"]["normal"]["baseline_count"] = value
    else:
        panels["assay_a"]["normal"]["normal"] = value
    with pytest.raises(ValueError):
        calculate(n, margins, panels)


@pytest.mark.parametrize(
    "mutation", ["missing_assay", "extra_assay", "empty", "blank", "space", "numeric"]
)
def test_named_assay_inventories_must_match(mutation):
    n, margins, panels = fixture()
    if mutation == "missing_assay":
        del panels["assay_a"]
    elif mutation == "extra_assay":
        panels["assay_c"] = deepcopy(panels["assay_a"])
    elif mutation == "empty":
        margins, panels = {}, {}
    else:
        key = {"blank": "", "space": " assay", "numeric": 1}[mutation]
        margins[key] = margins.pop("assay_a")
        panels[key] = panels.pop("assay_a")
    with pytest.raises(ValueError):
        calculate(n, margins, panels)


@pytest.mark.parametrize(
    "mutation",
    ["row_missing", "row_extra", "slot_missing", "slot_extra", "not_dict", "row_not_dict"],
)
def test_closed_source_row_shape(mutation):
    n, margins, panels = fixture()
    if mutation == "row_missing":
        del panels["assay_a"]["normal"]
    elif mutation == "row_extra":
        panels["assay_a"]["diabetes"] = row((0, 0, 0, 0))
    elif mutation == "slot_missing":
        del panels["assay_a"]["normal"]["mortality"]
    elif mutation == "slot_extra":
        panels["assay_a"]["normal"]["event_time"] = 5
    elif mutation == "not_dict":
        panels["assay_a"] = []
    else:
        panels["assay_a"]["normal"] = []
    with pytest.raises(ValueError):
        calculate(n, margins, panels)


@pytest.mark.parametrize(
    "mutation",
    [
        "too_many_original_pre",
        "selected_normal_excess",
        "selected_pre_excess",
        "row_sum",
        "selected_cohort_mismatch",
    ],
)
def test_impossible_margins_or_nonconservation_rejected(mutation):
    n, margins, panels = fixture()
    if mutation == "too_many_original_pre":
        margins["assay_a"] = n + 1
    elif mutation == "selected_normal_excess":
        margins["assay_a"] = n
    elif mutation == "selected_pre_excess":
        margins["assay_a"] = 1
    elif mutation == "row_sum":
        panels["assay_a"]["normal"]["baseline_count"] += 1
    else:
        panels["assay_b"]["normal"] = row((0, 0, 0, 1))
    with pytest.raises(ValueError):
        calculate(n, margins, panels)


def test_one_person_histories_are_not_inferred_from_the_same_disposition():
    # Two distinct synthetic hidden histories accompany the same caller-supplied
    # published slot. This supplies no empirical event-priority algorithm.
    histories = [
        {"events": ("death",), "published_slot": "mortality"},
        {"events": ("diagnosis", "death"), "published_slot": "mortality"},
    ]
    assert histories[0]["events"] != histories[1]["events"]
    outputs = []
    for history in histories:
        counts = tuple(int(history["published_slot"] == slot) for slot in SLOTS)
        panel = {"normal": row((0, 0, 0, 0)), "prediabetes": row(counts)}
        outputs.append(calculate(1, {"assay": 1}, {"assay": panel}))
    assert outputs[0] == outputs[1]
    flags = outputs[0]["interpretation"]
    assert flags["mortality_priority_identified"] is False
    assert flags["diagnosis_before_death_identified"] is False
    assert flags["exact_event_times_identified"] is False
    assert flags["common_elapsed_horizon_assumed"] is False


def test_all_unrepresented_empty_and_single_assay_are_supported():
    empty = {"normal": row((0, 0, 0, 0)), "prediabetes": row((0, 0, 0, 0))}
    result = calculate(3, {"assay": 1}, {"assay": empty})
    for output in result["panels"]["assay"]["rows"].values():
        assert rational(output["original_row_fractions"]["unrepresented_baseline_margin"]) == 1
        assert all(value is None for value in output["selected_row_fractions"].values())
    zero = calculate(0, {"assay": 0}, {"assay": empty})
    assert zero["counts"]["original_unique_people"] == 0
    assert all(
        value is None
        for value in zero["panels"]["assay"]["rows"]["normal"]["original_row_fractions"].values()
    )


def test_arbitrary_size_exact_rationals_and_display_underflow():
    n = 10**400
    result = calculate(
        n, {"assay": 0}, {"assay": {"normal": row((1, 0, 0, 0)), "prediabetes": row((0, 0, 0, 0))}}
    )
    value = result["panels"]["assay"]["rows"]["normal"]["original_row_fractions"]["normal"]
    assert rational(value) == Fraction(1, n)
    assert value["display_underflow"] is True
    assert value["display_fraction"] == 0


def test_input_snapshot_and_result_rows_do_not_alias():
    n, margins, panels = fixture()
    before = deepcopy((margins, panels))
    result = calculate(n, margins, panels)
    assert (margins, panels) == before
    panels["assay_a"]["normal"]["normal"] = 100
    assert result["panels"]["assay_a"]["rows"]["normal"]["source_partition_counts"]["normal"] == 1
    result["panels"]["assay_a"]["rows"]["normal"]["source_partition_counts"]["normal"] = 42
    assert (
        result["panels"]["assay_a"]["rows"]["prediabetes"]["source_partition_counts"]["normal"] == 1
    )


def test_residual_carries_no_alive_dead_or_wholly_untraced_assertion():
    flags = calculate(*fixture())["interpretation"]
    for key in [
        "residual_is_observed_followup_category",
        "residual_vital_status_identified",
        "residual_is_wholly_untraced",
        "source_labels_are_latent_clinical_states",
        "stochastic_or_clinical_fit_performed",
        "independently_verified_participant_subset_identity",
    ]:
        assert flags[key] is False
    assert flags["sampling_interval"] is None
