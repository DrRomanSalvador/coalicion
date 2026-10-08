from pathlib import Path
import json
from src.models.territorial_prediction_2026 import predict

def test_territorial_prediction_is_blocked_without_observations():
    root = Path(__file__).resolve().parents[1]
    out = root / "artifacts/territorial_prediction_20261008.json"
    r = predict(
        survey_path=root / "data/surveys/current_2026/current_national.json",
        canonical_2023=root / "artifacts/data/election_2023_canonical.json",
        seats_path=root / "data/2026_circunscripciones_oficiales.csv",
        output=out,
    )
    assert r["status"] == "BLOCKED"
    assert r["observed_territorial_polls"] == 0
    assert r["territorial_input"] == "NONE"
    assert r["policy"]["national_to_territorial_inference"] is False
    assert len(r["constituencies"]) == 0
    persisted = json.loads(out.read_text(encoding="utf-8"))
    assert persisted["status"] == "BLOCKED"
