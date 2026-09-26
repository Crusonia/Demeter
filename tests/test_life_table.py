import pytest

from demeter.life_table import AgeInterval, period_life_table


def test_known_synthetic_fixture() -> None:
    # 100 births, half die in the first ten years at mean age 5;
    # the other half live five further years in the open terminal group.
    rows = period_life_table(
        [
            AgeInterval(0, 10, 0.5, 5),
            AgeInterval(10, None, 1, terminal_person_years_per_survivor=5),
        ],
        radix=100,
    )
    assert rows[0].survivors == 100
    assert rows[0].deaths == 50
    assert rows[0].person_years == 750
    assert rows[1].survivors == 50
    assert rows[1].person_years == 250
    assert rows[0].life_expectancy == 10
    assert rows[1].life_expectancy == 5


@pytest.mark.parametrize(
    "intervals",
    [
        [AgeInterval(1, None, 1, terminal_person_years_per_survivor=5)],
        [
            AgeInterval(0, 10, 0.2, 5),
            AgeInterval(11, None, 1, terminal_person_years_per_survivor=5),
        ],
        [AgeInterval(0, None, 0.9, terminal_person_years_per_survivor=5)],
        [
            AgeInterval(0, 10, 0.2, 12),
            AgeInterval(10, None, 1, terminal_person_years_per_survivor=5),
        ],
    ],
)
def test_rejects_invalid_tables(intervals) -> None:
    with pytest.raises(ValueError):
        period_life_table(intervals)


def test_rejects_missing_open_terminal_interval() -> None:
    with pytest.raises(ValueError, match="final open"):
        period_life_table([AgeInterval(0, 10, 0.5, 5)])
