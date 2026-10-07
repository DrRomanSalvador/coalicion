import pytest
from src.poll_aggregator import (
    AggregationConfig, HistoricalError, PollEstimate, aggregate_party
)


def poll(pid, house, est, field_end, n=1000):
    return PollEstimate("2023", "P", house, est, field_end, n, pid)


def hist(house, est, actual, election="2019N", party="P"):
    return HistoricalError(
        election, party, house, est, actual, "2019-10-01", "2019-11-10"
    )


def test_aggregator_combines_sample_recency_and_repeated_house_penalty():
    rows = [
        poll("a1", "A", 40, "2023-07-20", 2000),
        poll("a2", "A", 42, "2023-07-19", 2000),
        poll("b1", "B", 46, "2023-07-18", 1000),
    ]
    r = aggregate_party(rows, "P", "2023-07-23")
    assert 40 < r.estimate_pct < 46
    assert r.effective_polls > 1


def test_house_effect_is_shrunk_with_limited_history():
    rows = [poll("a", "A", 40, "2023-07-20", 1000)]
    h = [hist("A", 45, 40)]
    r = aggregate_party(
        rows, "P", "2023-07-23", h,
        AggregationConfig(house_shrinkage=10, min_history_observations=1)
    )
    assert r.weighted_observations[0].corrected_estimate_pct > 40
    assert r.weighted_observations[0].corrected_estimate_pct < 45


def test_future_poll_is_rejected_instead_of_leaking():
    rows = [poll("future", "A", 40, "2023-07-24")]
    with pytest.raises(ValueError):
        aggregate_party(rows, "P", "2023-07-23")


def test_old_poll_is_excluded_and_missing_data_fails_closed():
    rows = [poll("old", "A", 40, "2022-01-01")]
    with pytest.raises(ValueError):
        aggregate_party(rows, "P", "2023-07-23")
