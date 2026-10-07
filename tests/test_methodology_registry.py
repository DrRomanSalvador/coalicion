from src.methodology_registry import (
    methodology_inventory, production_methodology_status, promoteable
)

def test_extensions_are_candidates_until_oos_calibrated():
    out = production_methodology_status()
    assert out["status"] == "NOT_PROMOTED"
    assert out["promotion_allowed"] is False

def test_only_explicit_oos_calibration_promotes():
    good = {
        "oos": "PASS", "calibration": "PASS",
        "leakage_free": True, "candidate_not_worse": True,
        "artifact": "oos-calibration.json",
    }
    assert promoteable(good)
    assert production_methodology_status(good)["status"] == "OOS_CALIBRATED"

def test_inventory_keeps_electoral_core_canonical():
    inv = methodology_inventory()
    assert inv["canonical_electoral_law"] == "src.electoral.py"
    assert inv["no_claim_without_evidence"] is True
