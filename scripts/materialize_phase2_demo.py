#!/usr/bin/env python3
"""Materialize the reproducible Phase 2 demonstration package."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.territorial_prediction_2026 import predict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main() -> int:
    result = predict(
        survey_path=ROOT / "data/surveys/current_2026/current_national.json",
        canonical_2023=ROOT / "artifacts/data/election_2023_canonical.json",
        seats_path=ROOT / "data/2026_circunscripciones_oficiales.csv",
        output=ROOT / "artifacts/territorial_prediction_20261008.json",
    )
    # Real observations may arrive at any time. Accept only internally consistent
    # states: no observations => BLOCKED; observations => a usable forecast status.
    status = result.get("status")
    observed = result.get("observed_territorial_polls")
    if not isinstance(observed, int) or observed < 0:
        raise RuntimeError("Invalid observed_territorial_polls in materialized forecast.")
    if status == "BLOCKED" and observed != 0:
        raise RuntimeError("Forecast is BLOCKED despite having territorial poll observations.")
    if status != "BLOCKED" and observed == 0:
        raise RuntimeError("Forecast claims usability without territorial poll observations.")
    if status not in {"BLOCKED", "PASS", "READY", "REVIEW_REQUIRED"}:
        raise RuntimeError(f"Unexpected forecast status: {status!r}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
