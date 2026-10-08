from src.rapid_decision_center import decision_snapshot


def _matrix():
    from src.electoral import official_2026_seats
    seats = official_2026_seats()
    votes = {c: {"A": 600, "B": 400, "C": 50} for c in seats}
    blank = {c: 0 for c in seats}
    special = {"Ceuta": "Ceuta", "Melilla": "Melilla"}
    return votes, seats, blank, special


def test_decision_snapshot_is_complete_and_traced():
    votes, seats, blank, special = _matrix()
    out = decision_snapshot(votes, seats, blank, special_by_constituency=special)
    assert out["status"] == "OK"
    assert out["territory"]["constituencies"] == 52
    assert out["territory"]["seats"] == 350
    assert out["projection"]["national"]["seats"]
    assert out["marginality"]["most_marginal"]
    assert len(out["traceability"]["input_hash"]) == 64
    assert len(out["traceability"]["output_hash"]) == 64
    again = decision_snapshot(votes, seats, blank, special_by_constituency=special)
    assert out["traceability"]["output_hash"] == again["traceability"]["output_hash"]


def test_decision_snapshot_compares_previous_projection():
    votes, seats, blank = _matrix()
    first = decision_snapshot(votes, seats, blank)
    changed = {k: dict(v) for k, v in votes.items()}
    changed["Madrid"]["A"] += 100
    second = decision_snapshot(
        changed, seats, blank, special_by_constituency=special,
        previous_projection=first["projection"]
    )
    assert second["changes"]
    assert any(row["party"] == "A" for row in second["changes"])


def test_decision_snapshot_rejects_non_52_in_strict_mode():
    votes = {"A": {"X": 1, "Y": 0}}
    seats = {"A": 1}
    blank = {"A": 0}
    try:
        decision_snapshot(votes, seats, blank, special_by_constituency=special)
    except ValueError as exc:
        assert "52" in str(exc)
    else:
        raise AssertionError("strict territory must reject incomplete matrix")


def test_decision_snapshot_requires_explicit_blank_votes():
    import pytest
    votes, seats, blank, special = _matrix()
    with pytest.raises(ValueError, match="votos en blanco"):
        decision_snapshot(votes, seats, special_by_constituency=special)


def test_decision_snapshot_rejects_wrong_seat_total():
    votes, seats, blank = _matrix()
    seats["Madrid"] -= 1
    try:
        decision_snapshot(votes, seats, blank)
    except ValueError as exc:
        assert "350" in str(exc)
    else:
        raise AssertionError("strict territory must reject a non-350 seat total")


def test_decision_snapshot_exposes_methodology_gate():
    votes, seats, blank = _matrix()
    out = decision_snapshot(votes, seats, blank)
    assert out["methodology"]["status"] == "NOT_PROMOTED"
    assert out["methodology"]["promotion_allowed"] is False
