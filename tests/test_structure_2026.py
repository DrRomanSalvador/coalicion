from pathlib import Path
import csv

def _rows():
    path = Path(__file__).parents[1] / "data" / "2026_circunscripciones_oficiales.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def test_exactly_52_constituencies():
    assert len(_rows()) == 52

def test_exactly_350_seats():
    assert sum(int(r["escanos_2026"]) for r in _rows()) == 350

def test_constituencies_unique():
    names = [r["circunscripcion"] for r in _rows()]
    assert len(names) == len(set(names))

def test_madrid_38():
    assert next(r for r in _rows() if r["circunscripcion"] == "Madrid")["escanos_2026"] == "38"

def test_cadiz_8():
    assert next(r for r in _rows() if r["circunscripcion"] == "Cádiz")["escanos_2026"] == "8"

def test_ceuta_and_melilla_one_each():
    rows = {r["circunscripcion"]: int(r["escanos_2026"]) for r in _rows()}
    assert rows["Ceuta"] == 1
    assert rows["Melilla"] == 1

def test_all_rows_have_primary_source():
    assert all(r["fuente"] == "BOE-A-2026-20742" for r in _rows())
