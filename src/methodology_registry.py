"""Registry and promotion gate for optional predictive methodology.

The canonical electoral pipeline remains authoritative. Extensions become
production evidence only when an explicit OOS/calibration record proves it.
"""
from __future__ import annotations
from typing import Any, Mapping

MODEL_NAMES = (
    "ensemble","bayesian_ensemble","quantile_regression_forest",
    "gaussian_process","conformal_prediction","block_bootstrap",
    "robust_optimization","sobol_sensitivity","lstm",
    "causal_inference","spatial_diagnostics",
)

def methodology_inventory() -> dict[str, Any]:
    return {
        "version": "1.0",
        "canonical_prediction": "src.prediction.py",
        "canonical_electoral_law": "src.electoral.py",
        "models": {name: {"status": "OPTIONAL_CANDIDATE"} for name in MODEL_NAMES},
        "promotion_rule": "OOS_CALIBRATED_ONLY",
        "no_claim_without_evidence": True,
    }

def promoteable(status: Mapping[str, Any] | None) -> bool:
    if not status:
        return False
    return (
        status.get("oos") == "PASS"
        and status.get("calibration") == "PASS"
        and status.get("leakage_free") is True
        and status.get("candidate_not_worse") is True
    )

def production_methodology_status(status: Mapping[str, Any] | None = None) -> dict[str, Any]:
    approved = promoteable(status)
    return {
        "status": "OOS_CALIBRATED" if approved else "NOT_PROMOTED",
        "promotion_allowed": approved,
        "canonical_pipeline_unchanged": True,
        "evidence": dict(status or {}),
        "inventory": methodology_inventory(),
    }
