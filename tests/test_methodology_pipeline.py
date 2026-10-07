import pytest
from src.methodology_pipeline import methodology_stage, production_ready
from src.methodology_registry import MODEL_NAMES

def test_methodology_stage_is_fail_closed_without_real_evidence():
    stage = methodology_stage()
    assert stage["status"] == "NOT_PROMOTED"
    assert stage["promotion_allowed"] is False
    assert set(stage["missing_evidence_for_models"]) == set(MODEL_NAMES)
    assert stage["policy"]["synthetic_estimates_forbidden"] is True

def test_methodology_stage_requires_all_evidence():
    rows = [
        {"candidate": name, "oos": "PASS", "calibration": "PASS",
         "leakage_free": True, "candidate_not_worse": True}
        for name in MODEL_NAMES
    ]
    stage = methodology_stage(
        oos_results=rows,
        calibration={"status": "PASS"},
        sensitivity={"status": "PASS"},
    )
    assert production_ready(stage)

def test_methodology_stage_rejects_missing_calibration():
    rows = [
        {"candidate": name, "oos": "PASS", "calibration": "PASS",
         "leakage_free": True, "candidate_not_worse": True}
        for name in MODEL_NAMES
    ]
    stage = methodology_stage(oos_results=rows)
    assert not production_ready(stage)
