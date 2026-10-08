from pathlib import Path
import json
from src.models.territorial_prediction_2026 import predict

def test_demo_prediction_has_52_constituencies_and_350_seats():
    root=Path(__file__).resolve().parents[1]
    out=root/"artifacts/territorial_prediction_20261008.json"
    r=predict(survey_path=root/"data/surveys/current_2026/current_national.json",
              canonical_2023=root/"artifacts/data/election_2023_canonical.json",
              seats_path=root/"data/2026_circunscripciones_oficiales.csv",output=out)
    assert r["status"]=="PASS"
    assert len(r["constituencies"])==52
    assert r["seat_total"]==350
    assert r["territorial_input"]=="MODELLED_NOT_OBSERVED"
    assert r["calibration_status"]=="NOT_2026_CALIBRATED"
