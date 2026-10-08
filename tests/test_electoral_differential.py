import random

from src.electoral import dhondt


def _case(seed):
    rng = random.Random(seed)
    parties = [f"P{i}" for i in range(rng.randint(2, 8))]
    votes = {p: rng.randint(0, 5000) for p in parties}
    if sum(votes.values()) == 0:
        votes[parties[0]] = 1
    blank = rng.randint(0, 300)
    valid = sum(votes.values()) + blank
    seats = rng.randint(1, 12)
    return votes, seats, valid, blank


def test_production_allocator_preserves_seat_total_on_adversarial_edges():
    edges = [
        ({"A": 100, "B": 50}, 2, 150, 0),
        ({"A": 97, "B": 3}, 1, 100, 0),
        ({"A": 96, "B": 2, "C": 2}, 1, 100, 0),
        ({"A": 970, "B": 20}, 1, 1000, 10),
        ({"A": 1, "B": 1, "C": 100}, 7, 102, 0),
    ]
    for votes, seats, valid, blank in edges:
        result = dhondt(votes, seats, valid, blank)
        assert result.status == "OK"
        assert sum(result.seats.values()) == seats


def test_production_allocator_is_reproducible_for_random_cases():
    for seed in range(2000):
        votes, seats, valid, blank = _case(seed)
        first = dhondt(votes, seats, valid, blank)
        second = dhondt(votes, seats, valid, blank)
        assert first.status == second.status == "OK"
        assert first.seats == second.seats


def test_production_allocator_fails_closed_on_invalid_valid_votes():
    result = dhondt({"A": 100, "B": 100}, 1, 100)
    assert result.status != "OK"
