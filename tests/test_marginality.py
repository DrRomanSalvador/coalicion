from src.marginality import marginal_seat


def test_marginality_reports_quotients_and_displacement_votes():
    result = marginal_seat({"A": 100, "B": 80, "C": 20}, 3)
    assert result["last_seat_holder"] == "A"
    assert result["challenger"] == "B"
    assert result["votes_to_change"] == 21
    assert result["challenger_next_quotient"] == 40
    assert result["last_quotient"] == 50
