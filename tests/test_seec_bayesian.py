import pytest

from src.seec_bayesian import (
    ProvinceObservation,
    SurveyRow,
    _survey_counts,
    build_model,
    validate_composition,
)


def _poll(poll_id="p1", field_date="2026-10-01", house="house", estimates=(0.333, 0.333, 0.334)):
    parties = ["A", "B", "C"]
    return [
        SurveyRow(poll_id, field_date, house, party, value, 100)
        for party, value in zip(parties, estimates)
    ]


def _historical():
    return [
        ProvinceObservation("2019", "P1", "A", 60, 100, 0.7),
        ProvinceObservation("2019", "P1", "B", 30, 100, 0.7),
        ProvinceObservation("2019", "P1", "C", 10, 100, 0.7),
    ]


def test_survey_counts_are_compositional_and_sum_to_sample_size():
    counts, n = _survey_counts(["A", "B", "C"], _poll())
    assert n == 100
    assert sum(counts) == n
    assert all(count >= 0 for count in counts)


def test_incomplete_poll_fails_closed_instead_of_treating_missing_party_as_zero():
    with pytest.raises(ValueError, match="exactamente todos los partidos"):
        _survey_counts(["A", "B", "C"], _poll(estimates=(0.5, 0.5))[:2])


def test_composition_validation_rejects_non_unit_sum():
    with pytest.raises(ValueError, match="deben sumar 1"):
        validate_composition(["A", "B"], {"A": 0.6, "B": 0.3})


def test_survey_count_reconstruction_is_deterministic():
    rows = _poll(estimates=(0.335, 0.335, 0.330))
    assert _survey_counts(["A", "B", "C"], rows) == _survey_counts(["A", "B", "C"], rows)


def test_model_is_joint_compositional_and_temporal():
    pm = pytest.importorskip("pymc")
    model = build_model(
        ["P1"],
        ["A", "B", "C"],
        _historical(),
        _poll(field_date="2026-10-01"),
    )
    names = set(model.named_vars)
    assert {"national_0", "national_drift", "national_t", "province_share", "house_effect"} <= names
    assert "poll_p1" in names
    assert "election_0" in names
    assert model.named_vars["national_t"].eval().shape == (1, 3)


def test_field_date_changes_temporal_state_dimension():
    pytest.importorskip("pymc")
    model = build_model(
        ["P1"],
        ["A", "B", "C"],
        _historical(),
        _poll(poll_id="p1", field_date="2026-10-01")
        + _poll(poll_id="p2", field_date="2026-10-05", house="house"),
    )
    assert model.named_vars["national_t"].eval().shape == (2, 3)
