from datetime import date
from src.election_calendar import official_2026_timeline, timeline, critical_window

def test_calendar_contains_all_operational_milestones():
    rows=official_2026_timeline()
    codes={x["code"] for x in rows}
    assert {"COALICIONES","CANDIDATURAS_INICIO","CANDIDATURAS_FIN","PROCLAMACION","CAMPAÑA_INICIO","ELECCION"} <= codes
    assert len(codes) == len(rows)

def test_calendar_known_dates():
    rows={x["code"]:x["date"] for x in official_2026_timeline()}
    assert rows["COALICIONES"]=="2026-10-16"
    assert rows["CANDIDATURAS_INICIO"]=="2026-10-21"
    assert rows["CANDIDATURAS_FIN"]=="2026-10-26"
    assert rows["CAMPAÑA_INICIO"]=="2026-11-13"
    assert rows["ELECCION"]=="2026-11-29"

def test_timeline_is_deterministic_and_signed():
    by={x["code"]:x for x in timeline(date(2026,10,8))}
    assert by["COALICIONES"]["days_remaining"]==7
    assert by["ELECCION"]["days_remaining"]==52
    assert by["COALICIONES"]["status"]=="upcoming"

def test_critical_window_is_bounded():
    rows=critical_window(date(2026,10,8),31)
    assert rows
    assert all(-2 <= x["days_remaining"] <= 31 for x in rows)



def test_operational_briefing_prioritizes_imminent_deadline():
    from src.operational_briefing import build_briefing
    from datetime import date

    items = build_briefing(
        as_of=date(2026, 10, 8),
        polls=[],
        sources=[],
        observations={},
    )
    assert items[0]["code"] == "LEGAL_COALICIONES"
    assert items[0]["due"] == "2026-10-16"


def test_operational_briefing_detects_stale_polls_and_source_incident():
    from src.operational_briefing import build_briefing
    from datetime import date

    items = build_briefing(
        as_of=date(2026, 10, 8),
        polls=[{"publication_date": "2026-10-01"}],
        sources=[{"id": "source_x", "status": "DOWN"}],
        observations={"territorial_poll_count": 0},
    )
    codes = {item["code"] for item in items}
    assert "POLL_STALENESS" in codes
    assert "SOURCE_HEALTH" in codes
    assert "TERRITORIAL_INPUT" in codes
