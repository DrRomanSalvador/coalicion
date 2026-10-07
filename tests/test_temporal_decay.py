from src.temporal_decay import exponential_weights, weighted_median


def test_decay_is_monotone():
    w=exponential_weights(["2020-01-01","2025-01-01"],"2025-01-01",365.25)
    assert w[0] < w[1] == 1.0


def test_weighted_median_deterministic():
    assert weighted_median([0.1,0.2,0.9],[1,1,1]) == 0.2
