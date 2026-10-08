"""Fail-closed 2026 territorial prediction boundary.

National surveys cannot be converted into constituency predictions without
explicit territorial observations. The 2026 territorial model therefore
materializes a BLOCKED evidence artifact until territorial inputs exist.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

def h(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def predict(*, survey_path: Path, canonical_2023: Path, seats_path: Path, output: Path,
            territorial_observations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    surveys = json.loads(survey_path.read_text(encoding="utf-8")).get("surveys", [])
    observations = list(territorial_observations or [])
    result = {
        "schema": "TERRITORIAL_PREDICTION_2026_V2",
        "status": "PASS" if len(observations) >= 3 else "BLOCKED",
        "mode": "OBSERVED_TERRITORIAL_ONLY",
        "as_of": "2026-10-08",
        "current_survey_count": len(surveys),
        "observed_territorial_polls": len(observations),
        "territorial_input": "OBSERVED" if observations else "NONE",
        "calibration_status": "NOT_2026_CALIBRATED",
        "policy": {
            "national_to_territorial_inference": False,
            "synthetic_territorial_values": False,
            "fail_closed": True,
        },
        "input_hash": h({
            "survey_registry": surveys,
            "territorial_observations": observations,
            "canonical_2023": str(canonical_2023),
            "seats_path": str(seats_path),
        }),
    }
    if not observations:
        result["blockers"] = [
            "BLOCKED_NO_TERRITORIAL_OBSERVATIONS",
            "BLOCKED_NO_2026_TERRITORIAL_CALIBRATION",
        ]
        result["constituencies"] = {}
        result["national_seats"] = {}
        result["seat_total"] = 0
    else:
        result["blockers"] = ["BLOCKED_TERRITORIAL_MODEL_NOT_IMPLEMENTED_FOR_OBSERVED_INPUT"]
        result["status"] = "BLOCKED"
        result["constituencies"] = {}
        result["national_seats"] = {}
        result["seat_total"] = 0
    result["output_hash"] = h(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
