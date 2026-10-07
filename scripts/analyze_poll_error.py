"""Ejecutor reproducible del análisis encuesta -> resultado, 2004-2023.

Fail-closed: si no hay observaciones documentadas, no fabrica resultados.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from src.prediction import PollObservation
from src.prediction import (
    summarize, by_election, by_party, by_house,
    by_government, by_government_status, by_direction,
    by_days_to_election, change_vs_previous_election, direction_counts,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "encuestas_historicas_2004_2023.csv"
OUT = ROOT / ".audit_poll_error" / "summary.json"


def load() -> list[PollObservation]:
    with DATA.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {
        "election","election_date","party","poll","actual","house",
        "field_end","source","poll_id","governing_party",
        "government_status","government_change","party_family",
        "poll_method","sample_size","source_tier",
    }
    if rows and not required.issubset(rows[0]):
        raise ValueError("Esquema histórico incompleto")
    out = []
    for r in rows:
        if not r.get("election"):
            continue
        out.append(PollObservation(
            election=r["election"],
            election_date=r["election_date"],
            party=r["party"],
            poll=float(r["poll"]),
            actual=float(r["actual"]),
            house=r["house"],
            field_end=r["field_end"],
            source=r["source"],
            poll_id=r["poll_id"],
            governing_party=r["governing_party"],
            government_status=r["government_status"],
            government_change=r["government_change"],
            party_family=r["party_family"],
            poll_method=r["poll_method"],
            sample_size=int(r["sample_size"]) if r["sample_size"] else None,
            source_tier=r["source_tier"],
        ))
    return out


def main() -> None:
    rows = load()
    OUT.parent.mkdir(exist_ok=True)
    if not rows:
        result = {
            "status": "DATOS_PENDIENTES",
            "n": 0,
            "message": "No hay observaciones documentadas; no se calculan estadísticas.",
        }
    else:
        result = {
            "status": "OK",
            "n": len(rows),
            "overall": summarize(rows).__dict__,
            "direction_counts": direction_counts(rows),
            "by_election": {k: v.__dict__ for k, v in by_election(rows).items()},
            "by_party": {k: v.__dict__ for k, v in by_party(rows).items()},
            "by_house": {k: v.__dict__ for k, v in by_house(rows).items()},
            "by_government": {k: v.__dict__ for k, v in by_government(rows).items()},
            "by_government_status": {k: v.__dict__ for k, v in by_government_status(rows).items()},
            "by_direction": {k: v.__dict__ for k, v in by_direction(rows).items()},
            "by_days_to_election": {k: v.__dict__ for k, v in by_days_to_election(rows).items()},
            "changes_vs_previous": [x.__dict__ for x in change_vs_previous_election(rows)],
        }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
