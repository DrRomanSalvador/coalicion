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
