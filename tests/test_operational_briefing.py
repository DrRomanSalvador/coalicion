from datetime import date

from src.operational_briefing import build_briefing


def test_briefing_prioritizes_imminent_legal_deadline():
    items = build_briefing(as_of=date(2026, 10, 8), polls=[], sources=[], observations={})
    assert items[0]["priority"] == "HIGH"
    assert items[0]["code"] == "LEGAL_CENSO_CONSULTA_INICIO"
    assert items[0]["due"] == "2026-10-12"


def test_briefing_detects_stale_polls():
    items = build_briefing(
        as_of=date(2026, 10, 8),
        polls=[{"publication_date": "2026-10-01"}],
        sources=[],
        observations={"territorial_poll_count": 1},
    )
    assert any(x["code"] == "POLL_STALENESS" for x in items)


def test_briefing_detects_source_incident_and_missing_territory():
    items = build_briefing(
        as_of=date(2026, 10, 8),
        polls=[{"publication_date": "2026-10-08"}],
        sources=[{"id": "source_x", "status": "DOWN"}],
        observations={"territorial_poll_count": 0},
    )
    codes = {x["code"] for x in items}
    assert "SOURCE_HEALTH" in codes
    assert "TERRITORIAL_INPUT" in codes


def test_briefing_is_deterministic():
    kwargs = dict(
        as_of=date(2026, 10, 8),
        polls=[{"publication_date": "2026-10-08"}],
        sources=[{"id": "x", "status": "OK"}],
        observations={"territorial_poll_count": 1},
    )
    assert build_briefing(**kwargs) == build_briefing(**kwargs)
