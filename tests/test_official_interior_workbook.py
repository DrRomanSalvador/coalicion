from pathlib import Path

from src.data import available_elections, load_official_constituency_matrix, load_rows

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "raw" / "Elecciones-Congreso.xlsx"


def test_official_workbook_has_complete_historical_coverage():
    elections = available_elections(WORKBOOK)
    assert len(elections) == 16
    assert elections[0] == "1977-06-15"
    assert elections[-1] == "2023-07-23"


def test_official_2023_matrix_is_complete_and_reconciled():
    result = load_official_constituency_matrix(WORKBOOK, "2023-07-23")
    assert result["validation"]["status"] == "PASS"
    assert result["validation"]["circunscripciones"] == 52
    assert result["validation"]["escaños"] == 350
    assert result["validation"]["candidate_votes_total"] == 24487414
    assert result["validation"]["blank_votes_total"] == 200673
    assert result["validation"]["valid_votes_total"] == 24688087
    assert result["constituencies"]["Madrid"]["seats"] == 37
    assert result["constituencies"]["Barcelona"]["seats"] == 32
    assert result["constituencies"]["Ceuta"]["seats"] == 1
    assert result["constituencies"]["Melilla"]["seats"] == 1


def test_official_loader_aggregates_duplicate_published_candidate_rows():
    result = load_official_constituency_matrix(WORKBOOK, "2023-07-23")
    madrid = result["constituencies"]["Madrid"]["parties"]
    assert madrid["FRENTE OBRERO - FO"] == 7652
    assert madrid["PARTIDO COMUNISTA DE LOS TRABAJADORES DE ESPAÑA - PCTE"] == 3407


def test_load_rows_supports_official_wide_workbook():
    rows = load_rows(WORKBOOK, "2023-07-23")
    assert len({r["province"] for r in rows}) == 52
    assert all(isinstance(r["votes"], int) and r["votes"] >= 0 for r in rows)
