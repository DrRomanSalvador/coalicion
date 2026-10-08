#!/usr/bin/env python3
"""Materialize the reproducible Phase 2 demonstration package."""
from pathlib import Path
from src.models.territorial_prediction_2026 import predict

ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    result=predict(
        survey_path=ROOT/"data/surveys/current_2026/current_national.json",
        canonical_2023=ROOT/"artifacts/data/election_2023_canonical.json",
        seats_path=ROOT/"data/2026_circunscripciones_oficiales.csv",
        output=ROOT/"artifacts/territorial_prediction_20261008.json",
    )
    assert result["status"]=="PASS"
    assert len(result["constituencies"])==52
    assert result["seat_total"]==350
    return 0

if __name__=="__main__":
    raise SystemExit(main())
