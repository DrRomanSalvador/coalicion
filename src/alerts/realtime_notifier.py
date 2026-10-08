"""Deterministic, evidence-backed realtime alert candidates."""
from __future__ import annotations
from typing import Any, Mapping

ALERT_CATEGORIES = ("new_poll", "poll_change", "source_failure", "source_recovery")

def build_alerts(current: Mapping[str, Any], previous: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    previous = previous or {}
    alerts: list[dict[str, str]] = []
    old_hashes = previous.get("poll_hashes", {}) if isinstance(previous.get("poll_hashes"), Mapping) else {}
    new_hashes = current.get("poll_hashes", {}) if isinstance(current.get("poll_hashes"), Mapping) else {}
    for key in sorted(set(new_hashes) - set(old_hashes)):
        alerts.append({"category":"new_poll","key":str(key),"detail":"Nueva observación materializada."})
    for key in sorted(set(new_hashes) & set(old_hashes)):
        if new_hashes[key] != old_hashes[key]:
            alerts.append({"category":"poll_change","key":str(key),"detail":"Observación modificada o republicada."})
    old_sources = previous.get("sources", {}) if isinstance(previous.get("sources"), Mapping) else {}
    new_sources = current.get("sources", {}) if isinstance(current.get("sources"), Mapping) else {}
    for sid in sorted(set(new_sources) | set(old_sources)):
        old = str(old_sources.get(sid, "")).upper()
        new = str(new_sources.get(sid, "")).upper()
        if new in {"FAILED","DEGRADED"} and old not in {"FAILED","DEGRADED"}:
            alerts.append({"category":"source_failure","key":f"{sid}:{new}","detail":f"{sid}: {new}."})
        if new in {"OK","UP","HEALTHY"} and old in {"FAILED","DEGRADED"}:
            alerts.append({"category":"source_recovery","key":f"{sid}:{old}->{new}","detail":f"{sid}: recuperada."})
    return alerts
