"""Publishable one-line alerts derived from a canonical situation state.

The function deliberately returns no alert when the state contains only
uncertainty or routine information. It is a transport-neutral presentation
filter; it does not decide political importance or make recommendations.
"""
from __future__ import annotations

from typing import Any, Mapping


def build_publishable_alerts(state: Mapping[str, Any]) -> list[dict[str, str]]:
    if not state.get("policy", {}).get("fail_closed"):
        return []
    if not state.get("policy", {}).get("descriptive_only"):
        return []
    alerts: list[dict[str, str]] = []
    for item in state.get("headline", {}).get("changed", []):
        if item.get("type") != "poll_observation_change":
            continue
        delta = float(item.get("delta_pp", 0))
        if abs(delta) < 1.0:
            continue
        direction = "sube" if delta > 0 else "baja"
        alerts.append({
            "severity": "ALERT",
            "message": f"Cambio relevante observado: {item.get('party')} {direction} {abs(delta):g} pp entre las dos últimas observaciones materializadas.",
            "evidence": ",".join(str(x) for x in item.get("evidence", []) if x),
        })
    return alerts


__all__ = ["build_publishable_alerts"]
