import pytest

from src.seec_bayesian import SurveyRow, _survey_counts, validate_composition


def _poll(*estimates):
    parties = ["A", "B", "C"]
    return [
        SurveyRow(
            poll_id="p1",
            field_date="2026-10-01",
            house="house",
            party=party,
            estimate=value,
            sample_size=100,
        )
        for party, value in zip(parties, estimates)
    ]


def test_survey_counts_are_compositional_and_sum_to_sample_size():
    rows = _poll(0.333, 0.333, 0.334)
    counts, n = _survey_counts(["A", "B", "C"], rows)

    assert n == 100
    assert sum(counts) == n
    assert all(count >= 0 for count in counts)


def test_incomplete_poll_fails_closed_instead_of_treating_missing_party_as_zero():
    rows = _poll(0.5, 0.5)[:2]

    with pytest.raises(ValueError, match="exactamente todos los partidos"):
        _survey_counts(["A", "B", "C"], rows)


def test_composition_validation_rejects_non_unit_sum():
    with pytest.raises(ValueError, match="deben sumar 1"):
        validate_composition(
            ["A", "B"],
            {"A": 0.6, "B": 0.3},
        )


def test_survey_count_reconstruction_is_deterministic():
    rows = _poll(0.335, 0.335, 0.330)
    first, _ = _survey_counts(["A", "B", "C"], rows)
    second, _ = _survey_counts(["A", "B", "C"], rows)

    assert first == second
