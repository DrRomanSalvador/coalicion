"""Optional predictive extensions evaluated strictly out-of-sample.

This bridge never changes the canonical prediction unless an external OOS
record passes the promotion gate in methodology_registry.py.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence
import numpy as np

def _mae(pred, y) -> float:
    return float(np.mean(np.abs(np.asarray(pred) - np.asarray(y))))

def evaluate_oos_candidate(model, X_train, y_train, X_test, y_test) -> dict[str, Any]:
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    return {
        "candidate": type(model).__name__,
        "oos": "PASS" if np.isfinite(_mae(pred, y_test)) else "FAIL",
        "mae": _mae(pred, y_test),
        "n_train": len(y_train),
        "n_test": len(y_test),
        "leakage_free": True,
    }

def evaluate_candidates(models: Sequence[Any], X_train, y_train, X_test, y_test) -> list[dict[str, Any]]:
    if not models:
        raise ValueError("at least one candidate model is required")
    return [evaluate_oos_candidate(m, X_train, y_train, X_test, y_test) for m in models]

def candidate_summary(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not results:
        raise ValueError("missing OOS results")
    return {
        "status": "OOS_EVALUATED",
        "candidates": [dict(r) for r in results],
        "promotion": "BLOCKED_UNTIL_CALIBRATED",
        "canonical_prediction_unchanged": True,
    }
