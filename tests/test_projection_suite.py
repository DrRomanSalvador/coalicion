from src.projection_suite import project, compare_projections, uncertainty_summary, backtest_rows


def test_projection_exposes_national_provincial_party_views():
    votes={"A":{"X":60,"Y":40},"B":{"X":40,"Y":60}}
    seats={"A":2,"B":2}
    blank={"A":0,"B":0}
    out=project(votes,seats,blank)
    assert sum(out["national"]["seats"].values()) == 4
    assert set(out["provincial"]) == {"A","B"}
    assert out["party"]["X"]["votes"] == 100


def test_projection_comparison_and_uncertainty():
    a={"party":{"X":{"votes":100,"seats":2,"vote_share":.5}}}
    b={"party":{"X":{"votes":110,"seats":3,"vote_share":.55}}}
    assert compare_projections(a,b)["X"]["seat_change"] == 1
    u=uncertainty_summary([{"X":1},{"X":3},{"X":5}])
    assert u["X"]["0.5"] == 3


def test_backtest_is_partitionable():
    rows=[
        {"election":"2023","party":"X","constituency":"A","votes":110,"seats":2},
        {"election":"2023","party":"Y","constituency":"A","votes":90,"seats":1},
    ]
    actual=[
        {"election":"2023","party":"X","constituency":"A","votes":100,"seats":1},
        {"election":"2023","party":"Y","constituency":"A","votes":100,"seats":2},
    ]
    out=backtest_rows(rows,actual)
    assert out["status"]=="PASS"
    assert out["vote_mae"]==10
    assert out["seat_mae"]==1

def test_projection_fails_closed_when_blank_votes_are_missing():
    import pytest
    votes={"A":{"X":60,"Y":40}}
    with pytest.raises(ValueError, match="votos en blanco"):
        project(votes, {"A": 2}, {})


def test_projection_requires_legal_special_rule_for_ceuta():
    import pytest
    votes={"Ceuta":{"X":60,"Y":40}}
    with pytest.raises(ValueError, match="Ceuta"):
        project(votes, {"Ceuta": 1}, {"Ceuta": 0})
