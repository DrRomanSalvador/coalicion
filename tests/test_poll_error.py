from src.poll_error import PollObservation, summarize, by_election, leave_one_election_out


def row(e, d, p, poll, actual, field, house="H"):
    return PollObservation(e, d, p, poll, actual, house, field, "test")


def test_summary_exact():
    s = summarize([
        row("2004", "2004-03-14", "A", 40, 42, "2004-03-01"),
        row("2004", "2004-03-14", "A", 44, 42, "2004-03-10"),
    ])
    assert s.n == 2
    assert s.mean_error == 0
    assert s.mae == 2
    assert s.minimum == -2
    assert s.maximum == 2
    assert s.p95_abs == 2


def test_group_by_election():
    rows = [
        row("2004", "2004-03-14", "A", 40, 42, "2004-03-01"),
        row("2008", "2008-03-09", "A", 40, 39, "2008-03-01"),
    ]
    out = by_election(rows)
    assert set(out) == {"2004", "2008"}


def test_leave_one_election_out_is_temporal():
    rows = [
        row("2004", "2004-03-14", "A", 40, 42, "2004-03-01"),
        row("2008", "2008-03-09", "A", 40, 39, "2008-03-01"),
        row("2011", "2011-11-20", "A", 40, 41, "2011-11-01"),
    ]
    out = leave_one_election_out(rows)
    assert "2004" not in out
    assert "2008" in out
    assert "2011" in out
