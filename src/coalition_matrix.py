"""Neutral 2023 constituency matrix loader."""
from __future__ import annotations
import csv
from pathlib import Path


def load_2023_matrix(path: str | Path = "data/2023_circunscripciones_oficiales.csv") -> dict:
    p=Path(path)
    if not p.exists():
        raise FileNotFoundError(f"matriz 2023 inexistente: {p}")
    with p.open(newline="",encoding="utf-8") as fh:
        rows=list(csv.DictReader(fh))
    required={"circunscripcion","escanos_2023","votos_validos_2023"}
    if not rows or not required <= set(rows[0]):
        raise ValueError("matriz 2023 incompleta")
    seats={r["circunscripcion"]:int(r["escanos_2023"]) for r in rows}
    valid={r["circunscripcion"]:int(r["votos_validos_2023"]) for r in rows}
    if sum(seats.values()) != 350:
        raise ValueError("la matriz 2023 no suma 350 escaños")
    if any(v <= 0 for v in valid.values()):
        raise ValueError("votos válidos 2023 inválidos")
    return {"seats":seats,"valid_votes":valid,"source":str(p)}
