from src.marginality import marginal_seat


def test_marginality_reports_quotients_and_displacement_votes():
    result = marginal_seat({"A": 100, "B": 80, "C": 20}, 3)
    assert result["last_seat_holder"] == "A"
    assert result["challenger"] == "B"
    assert result["votes_to_change"] == 21
    assert result["challenger_next_quotient"] == 40
    assert result["last_quotient"] == 50


def test_rank_marginality():
    from src.marginality import rank_marginality
    rows=[{"name":"A","votes":{"X":100,"Y":80,"Z":20},"seats":3},
          {"name":"B","votes":{"X":120,"Y":70,"Z":20},"seats":3}]
    ranked=rank_marginality(rows)
    assert [x["constituency"] for x in ranked] == ["A","B"]


def test_compare_marginality():
    from src.marginality import compare_marginality
    rows=[{"name":"A","votes":{"X":100,"Y":80,"Z":20},"seats":3}]
    out=compare_marginality([{"date":"2026-10-01","constituencies":rows}])
    assert out[0]["ranking"][0]["votes_to_change"] == 21
