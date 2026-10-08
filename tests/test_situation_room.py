from src.situation_room import evidence_level, situation, trends, uncertainty


def test_secondary_replica_is_not_primary_verified():
    poll = {
        "source_tier": "SECONDARY_REPLICA",
        "validation": "VALIDATED",
        "sample_size": 4000,
    }
    assert evidence_level(poll) == "SECONDARY_REPLICA"


def test_incomplete_primary_is_not_verified():
    poll = {
        "source_tier": "PRIMARY_POLLSTER",
        "validation": "PRIMARY_VERIFIED",
        "sample_size": 1000,
        "fieldwork_start": "2026-10-01",
        "fieldwork_end": "2026-10-03",
        "methodology": None,
    }
    assert evidence_level(poll) == "INCOMPLETE"


def test_situation_reports_materialized_source_status():
    state = {
        "last_run": "2026-10-08T12:09:21+00:00",
        "last_failures": [{"source_id": "invymark", "error": "SSLError"}],
        "last_coverage": {"claim": "COBERTURA_TOTAL_NO_VERIFICADA", "blockers": ["SOURCE_NOT_HEALTHY:invymark"]},
    }
    sources = [
        {"id": "cis_catalog", "status": "OK"},
        {"id": "invymark", "status": "FAILED"},
    ]
    text = situation(state, [], sources)
    assert "Registradas: 2" in text
    assert "fallidas: 1" in text
    assert "invymark: SSLError" in text
    assert "No se convierte una encuesta nacional en escaños provinciales." in text


def test_trends_are_descriptive():
    polls = [
        {"publication_date": "2026-10-08", "parties": {"PP": 33.0, "PSOE": 28.0}},
        {"publication_date": "2026-09-08", "parties": {"PP": 31.0, "PSOE": 29.0}},
    ]
    text = trends(polls)
    assert "PP: +2.0 pp" in text
    assert "Sin atribución causal" in text


def test_uncertainty_fails_closed_without_posterior():
    assert "No hay posterior/calibración" in uncertainty({})
