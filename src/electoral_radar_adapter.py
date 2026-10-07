"""Adapter between the canonical rapid decision snapshot and the neutral radar."""
from __future__ import annotations
from datetime import date
from typing import Any, Mapping, Sequence
from .electoral_intelligence import build_monthly_radar

def _national(s):
    return s.get("projection", {}).get("party", {}) if s else None

def _marginality(s):
    return s.get("marginality", {}).get("most_marginal", []) if s else None

def _uncertainty(s):
    return s.get("uncertainty") if s else None

def _coalition_state(s):
    value = s.get("coalitions") if s else None
    if not value:
        return None
    if isinstance(value, Mapping) and "all_coalitions" in value:
        rows = value["all_coalitions"]
        if len(rows) != 1:
            return None
        value = rows[0]
    if isinstance(value, Mapping):
        return {k: value[k] for k in ("separate_seats", "coalition_seats", "delta") if k in value}
    return None

def _priority(code, severity):
    if severity == "CRITICAL":
        return "P0"
    if code.startswith(("MARGINALITY_", "COALITION_")):
        return "P1"
    if code.startswith(("NATIONAL_", "UNCERTAINTY_")):
        return "P2"
    if code.startswith("SOURCE_"):
        return "P3"
    return "P4"

def build_radar_from_snapshot(*, today: date, current: Mapping[str, Any],
                              previous: Mapping[str, Any] | None = None,
                              sources: Sequence[Mapping[str, Any]] = (),
                              evidence_refs: Sequence[str] = ()) -> dict:
    radar = build_monthly_radar(
        today=today,
        national_previous=_national(previous),
        national_current=_national(current),
        marginality_previous=_marginality(previous),
        marginality_current=_marginality(current),
        coalition_previous=_coalition_state(previous),
        coalition_current=_coalition_state(current),
        uncertainty_previous=_uncertainty(previous),
        uncertainty_current=_uncertainty(current),
        sources=sources,
        evidence_refs=evidence_refs,
    )
    for alert in radar["alerts"]:
        alert["priority"] = _priority(alert["code"], alert["severity"])
    radar["decision_snapshot"] = {
        "current_input_hash": current.get("traceability", {}).get("input_hash"),
        "current_output_hash": current.get("traceability", {}).get("output_hash"),
        "previous_output_hash": (previous or {}).get("traceability", {}).get("output_hash"),
        "territory": current.get("territory"),
        "model_status": current.get("status", "UNKNOWN"),
        "methodology_status": current.get("methodology", {}).get("status", "UNKNOWN"),
        "methodology_promotion_allowed": current.get("methodology", {}).get("promotion_allowed", False),
    }
    radar["integration"] = {
        "source": "src.rapid_decision_center.decision_snapshot",
        "territorial_math": "src.projection_suite",
        "electoral_law": "src.electoral",
        "marginality": "src.marginality",
        "coalition": "src.coalition",
        "uncertainty": "src.uncertainty",
        "transport": "scripts.notify_webhook",
        "descriptive_only": True,
    }
    return radar
