from src.cis_history import ELECTIONS, load, as_oos_rows

def test_cis_history_is_canonical():
    rows = load()
    assert len(rows) == 110
    assert {r.election for r in rows} == set(ELECTIONS)
    assert all(r.source_url.startswith("https://www.cis.es/") for r in rows)

def test_cis_history_oos_adapter_preserves_published_estimates():
    rows = as_oos_rows()
    assert len(rows) == 110
    assert all(r["tipo_encuesta"] == "preelectoral" for r in rows)
    assert all(r["estimacion_voto"] for r in rows)
