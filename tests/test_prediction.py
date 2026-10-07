from src.prediction import (
    PollObservation, Candidate, accept_update, base, expanding_oos,
    select_best, _errors, change_vs_previous_election, decompose_movement,
)

def obs(e, poll, actual, field):
    return PollObservation(e, f"{e}-01-01", "A", poll, actual, "H", field, "test")

def test_no_oos_returns_error():
    try:
        select_best([obs("2023", 30, 31, "2023-07-20")])
    except ValueError:
        pass
    else:
        assert False

def test_filter_is_deterministic():
    data = [
        obs("2015", 30, 31, "2015-12-18"),
        obs("2016", 30, 31, "2016-06-20"),
        obs("2019A", 30, 31, "2019-04-20"),
        obs("2019B", 30, 31, "2019-11-05"),
    ]
    assert select_best(data).name == select_best(data).name

def test_oos_scores_elections_equally():
    data = [
        obs("2019", 40, 42, "2019-01-01"),
        obs("2023", 40, 40, "2023-01-01"),
        obs("2023", 40, 40, "2023-02-01"),
        obs("2023", 40, 40, "2023-03-01"),
    ]
    bs, cs = _errors(Candidate("BASE", base), data)
    assert bs.mae == 0.0 and cs.mae == 0.0

def test_oos_never_uses_future():
    r = expanding_oos(
        [("2004", 10), ("2008", 20), ("2011", 30)],
        lambda t: t[-1][1],
    )
    assert [x.train_elections for x in r.folds] == [
        ("2004",), ("2004", "2008")
    ]

def test_oos_min_train_counts_elections_not_rows():
    r = expanding_oos(
        [("2004", 10), ("2004", 11), ("2008", 20)],
        lambda t: t[-1][1],
        min_train_elections=2,
    )
    assert [x.election for x in r.folds] == ["2008"]
    assert r.folds[0].train_elections == ("2004",)

def test_change_vs_previous_uses_poll_to_poll():
    rows = [
        obs("2004", 40, 42, "2004-03-01"),
        obs("2008", 45, 44, "2008-03-01"),
    ]
    result = change_vs_previous_election(rows)[0]
    assert result.actual_change == 2
    assert result.poll_change == 5
    assert result.change_error == 3

def test_movement_decomposition_uses_poll_to_poll():
    rows = [
        obs("2004", 40, 42, "2004-03-01"),
        obs("2008", 45, 44, "2008-03-01"),
    ]
    result = decompose_movement(rows)[0]
    assert result.actual_change == 2
    assert result.observed_change == 5
    assert result.movement_error == 3

def test_equal_model_not_accepted():
    r = expanding_oos([("a", 1), ("b", 2)], lambda t: t[-1][1])
    assert not accept_update(r, r)
