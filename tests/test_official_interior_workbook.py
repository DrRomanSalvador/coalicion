import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.data import available_elections, download_workbook, load_official_constituency_matrix, load_rows
from src.electoral import allocate
from src.prediction import official_matrix_to_prediction_inputs, predict

ROOT=Path(__file__).resolve().parents[1]
WORKBOOK=ROOT/"data"/"raw"/"Elecciones-Congreso.xlsx"
MANIFEST=ROOT/"data"/"manifests"/"official_interior_congreso.json"

def _workbook():
    if WORKBOOK.is_file(): return WORKBOOK,None
    temp=TemporaryDirectory(); path=Path(temp.name)/"Elecciones-Congreso.xlsx"; download_workbook(path); return path,temp

def test_official_workbook_hash_matches_source_lock():
    path,temp=_workbook()
    try:
        expected=json.loads(MANIFEST.read_text(encoding="utf-8"))["sha256"]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    finally:
        if temp: temp.cleanup()

def test_official_workbook_has_complete_historical_coverage():
    path,temp=_workbook()
    try:
        elections=available_elections(path)
        assert len(elections)==16
        assert elections[0]=="1977-06-15"
        assert elections[-1]=="2023-07-23"
    finally:
        if temp: temp.cleanup()

def test_official_2023_matrix_is_complete_and_reconciled():
    path,temp=_workbook()
    try:
        result=load_official_constituency_matrix(path,"2023-07-23")
        assert result["validation"]["status"]=="PASS"
        assert result["validation"]["circunscripciones"]==52
        assert result["validation"]["escaños"]==350
        assert result["validation"]["candidate_votes_total"]==24487414
        assert result["validation"]["blank_votes_total"]==200673
        assert result["validation"]["valid_votes_total"]==24688087
        assert result["validation"]["vote_seat_reconciliation"] == {
            "status": "PASS",
            "constituencies": 52,
            "discrepancies": 0,
            "method": "src.electoral.allocate",
            "special_rules": ["Ceuta", "Melilla"],
        }
        assert result["constituencies"]["Madrid"]["seats"]==37
        assert result["constituencies"]["Barcelona"]["seats"]==32
        assert result["constituencies"]["Ceuta"]["seats"]==1
        assert result["constituencies"]["Melilla"]["seats"]==1
    finally:
        if temp: temp.cleanup()

def test_official_loader_aggregates_duplicate_published_candidate_rows():
    path,temp=_workbook()
    try:
        result=load_official_constituency_matrix(path,"2023-07-23")
        madrid=result["constituencies"]["Madrid"]["parties"]
        assert madrid["FRENTE OBRERO - FO"]==7652
        assert madrid["PARTIDO COMUNISTA DE LOS TRABAJADORES DE ESPAÑA - PCTE"]==3407
    finally:
        if temp: temp.cleanup()

def test_load_rows_supports_official_wide_workbook():
    path,temp=_workbook()
    try:
        rows=load_rows(path,"2023-07-23")
        assert len({r["province"] for r in rows})==52
        assert all(isinstance(r["votes"],int) and r["votes"]>=0 for r in rows)
    finally:
        if temp: temp.cleanup()

def test_official_2023_votes_reproduce_observed_seat_allocation():
    path, temp = _workbook()
    try:
        result = load_official_constituency_matrix(path, "2023-07-23")
        for constituency, item in result["constituencies"].items():
            special = constituency if constituency in {"Ceuta", "Melilla"} else ""
            allocation = allocate(
                item["parties"],
                item["seats"],
                item["valid_votes"],
                special=special,
                blank_votes=item["blank_votes"],
            )
            assert allocation.status == "OK", constituency
            observed = item["observed_seats"]
            predicted_positive = {p: s for p, s in allocation.seats.items() if s > 0}
            assert predicted_positive == observed, constituency
    finally:
        if temp:
            temp.cleanup()


def test_official_matrix_connects_to_prediction_without_inference():
    path, temp = _workbook()
    try:
        result = load_official_constituency_matrix(path, "2023-07-23")
        matrix = {"constituencies": result["constituencies"]}
        votes, seats, blanks, special = official_matrix_to_prediction_inputs(matrix)
        changes = {c: {p: 0.0 for p in row} for c, row in votes.items()}
        factors = {c: 1.0 for c in votes}
        predicted = predict(votes, seats, blanks, changes, factors, special)
        observed = {}
        for c, item in result["constituencies"].items():
            for p, s in item["observed_seats"].items():
                observed[p] = observed.get(p, 0) + s
        assert sum(predicted["national_seats"].values()) == 350
        assert {p: s for p, s in predicted["national_seats"].items() if s} == observed
    finally:
        if temp:
            temp.cleanup()
