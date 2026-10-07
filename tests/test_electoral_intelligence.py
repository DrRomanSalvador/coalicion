from datetime import date

from src.electoral_intelligence import (
    build_monthly_radar,
    compare_national_state,
    detect_coalition_changes,
    detect_marginality_changes,
)


def test_deadline_radar_contains_october_critical_coalition_deadline():
    out = build_monthly_radar(today=date(2026, 10, 8))
    codes = {x["code"] for x in out["alerts"]}
    assert "DEADLINE_COALITION_DEADLINE" in codes
    assert out["election_date"] == "2026-11-29"


def test_national_change_is_descriptive():
    alerts = compare_national_state(
        {"A": {"vote_share": .20, "seats": 20}},
        {"A": {"vote_share": .207, "seats": 21}},
    )
    assert len(alerts) == 1
    assert alerts[0].code == "NATIONAL_STATE_CHANGE"
    assert "recommend" not in alerts[0].title.lower()


def test_marginality_change_detects_holder_and_margin():
    old = [{"constituency": "X", "votes_to_change": 100,
            "last_seat_holder": "A", "challenger": "B"}]
    new = [{"constituency": "X", "votes_to_change": 140,
            "last_seat_holder": "B", "challenger": "A"}]
    alerts = detect_marginality_changes(old, new)
    assert len(alerts) == 1
    assert alerts[0].facts["holder_changed"] is True


def test_coalition_change_is_counterfactual_only():
    alerts = detect_coalition_changes(
        {"separate_seats": 100, "coalition_seats": 105},
        {"separate_seats": 100, "coalition_seats": 107},
    )
    assert len(alerts) == 1
    assert alerts[0].code == "COALITION_COUNTERFACTUAL_CHANGE"


def test_radar_is_reproducible_and_neutral():
    kwargs = dict(
        today=date(2026, 10, 8),
        national_previous={"A": {"vote_share": .20, "seats": 20}},
        national_current={"A": {"vote_share": .207, "seats": 21}},
        evidence_refs=["BOE-A-2026-20742"],
    )
    a = build_monthly_radar(**kwargs)
    b = build_monthly_radar(**kwargs)
    assert a["traceability"]["output_hash"] == b["traceability"]["output_hash"]
    assert a["policy"]["descriptive_only"] is True
    assert a["policy"]["no_recommendations"] is True
