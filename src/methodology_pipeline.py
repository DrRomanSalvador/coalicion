"""Single integration point for optional methodology extensions.

This module wires the optional methods into one auditable stage without making
any numerical estimate part of the canonical electoral result. Promotion is
fail-closed until real OOS, calibration and leakage evidence are supplied.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .methodology_registry import MODEL_NAMES, promoteable


REQUIRED_EVIDENCE = ("oos", "calibration", "leakage_free", "candidate_not_worse")


def methodology_stage(
    *,
    oos_results: Sequence[Mapping[str, Any]] = (),
    calibration: Mapping[str, Any] | None = None,
    sensitivity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble one neutral methodology stage.

    No model is promoted from training-fit metrics, synthetic data, or missing
    evidence. Numerical results are passed through only when explicitly supplied
    by a real evaluation run.
    """
    rows = [dict(row) for row in oos_results]
    names = {str(row.get("candidate", "")) for row in rows}
    missing_models = sorted(set(MODEL_NAMES) - names) if rows else list(MODEL_NAMES)

    calibration_payload = dict(calibration or {})
    sensitivity_payload = dict(sensitivity or {})

    calibrated = calibration_payload.get("status") == "PASS"
    sensitivity_ok = (
        not sensitivity_payload
        or sensitivity_payload.get("status") == "PASS"
    )
    candidates_ok = bool(rows) and all(
        all(key in row for key in REQUIRED_EVIDENCE)
        and row["oos"] == "PASS"
        and row["leakage_free"] is True
        and row["candidate_not_worse"] is True
        for row in rows
    )
    promotion = candidates_ok and calibrated and sensitivity_ok and not missing_models

    return {
        "schema": "METHODOLOGY_STAGE_V1",
        "status": "OOS_CALIBRATED" if promotion else "NOT_PROMOTED",
        "promotion_allowed": promotion,
        "canonical_pipeline_unchanged": True,
        "models": list(MODEL_NAMES),
        "evaluated_candidates": sorted(names),
        "missing_evidence_for_models": missing_models,
        "oos": rows,
        "calibration": calibration_payload,
        "sensitivity": sensitivity_payload,
        "policy": {
            "real_estimates_only": True,
            "synthetic_estimates_forbidden": True,
            "training_fit_cannot_promote": True,
            "territorialization_not_inferred": True,
            "electoral_law_remains_canonical": True,
        },
    }


def production_ready(stage: Mapping[str, Any]) -> bool:
    return bool(stage.get("promotion_allowed") is True and
                stage.get("status") == "OOS_CALIBRATED")
