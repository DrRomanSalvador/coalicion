from src.poll_uncertainty import (
    ErrorObservation, calibrate_coverage, calibrate_error_surface,
    normal_interval, party_sigma,
)


def obs(party, estimate, actual, field_end="2023-07-20"):
    return ErrorObservation(party, "2019N", field_end, "2019-11-10", estimate, actual)


def test_error_surface_is_temporal_and_party_specific():
    s = calibrate_error_surface([
        obs("P", 40, 38), obs("P", 41, 40), obs("Q", 10, 12)
    ])
    assert s.by_party_mae["P"] == 1.5
    assert s.by_party_mae["Q"] == 2
    assert party_sigma(s, "P", 10) > 0


def test_interval_is_bounded_and_explicit():
    low, high = normal_interval(40, 2, 0.90)
    assert 0 <= low < 40 < high <= 100


def test_coverage_is_measured_not_assumed():
    r = calibrate_coverage([
        (39, 41, 38, 42, 37, 43, 36, 44, 40),
        (39, 41, 38, 42, 37, 43, 36, 44, 50),
    ])
    assert r["coverage_50"] == 0.5
    assert r["coverage_80"] == 0.5
    assert r["coverage_90"] == 0.5
    assert r["coverage_95"] == 0.5
