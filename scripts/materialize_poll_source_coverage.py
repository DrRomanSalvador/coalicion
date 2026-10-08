#!/usr/bin/env python3
"""Materialize truthful poll-source coverage evidence from runtime state."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "config/poll_source_registry.json"
CFG = ROOT / "config/poll_monitor.json"
STATE = ROOT / "artifacts/poll_monitor_state.json"
OUT = ROOT / "ci_evidence/poll_source_coverage.json"

def main():
    registry = json.loads(REG.read_text(encoding="utf-8"))
    config = json.loads(CFG.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    statuses = state.get("source_status", {})
    configured = [s for s in config.get("sources", []) if not s.get("disabled")]
    primary = [s for s in configured if s.get("coverage_role") == "primary" and not s.get("optional")]
    unhealthy = [s["id"] for s in primary if statuses.get(s["id"], {}).get("status") != "OK"]
    disabled_without_reason = [
        s["id"] for s in config.get("sources", [])
        if s.get("disabled") and not s.get("reason")
    ]
    registry_ok = bool(registry.get("known_pollsters")) and bool(registry.get("reference_sources"))
    runtime_total = bool(state.get("last_coverage", {}).get("total"))
    # A cached "total=true" is not live coverage evidence. Every active primary
    # source must have a recent successful check in the persisted runtime state.
    now = datetime.now(timezone.utc)
    stale_primary = []
    for source in primary:
        sid = source["id"]
        status = statuses.get(sid, {})
        checked = status.get("checked_at")
        try:
            checked_at = datetime.fromisoformat(str(checked).replace("Z", "+00:00"))
            if checked_at.tzinfo is None:
                checked_at = checked_at.replace(tzinfo=timezone.utc)
            age_seconds = (now - checked_at.astimezone(timezone.utc)).total_seconds()
            if age_seconds < -300 or age_seconds > 900 or status.get("status") != "OK":
                stale_primary.append(sid)
        except (TypeError, ValueError):
            stale_primary.append(sid)
    total_ok = runtime_total and not unhealthy and not stale_primary and not disabled_without_reason and registry_ok
    result = {
        "schema": "POLL_SOURCE_COVERAGE_V1",
        "status": "PASS" if total_ok else "BLOCKED",
        "claim": "TRANSPORT_COVERAGE_VERIFIED" if total_ok else "TRANSPORT_COVERAGE_BLOCKED",
        "scope": "configured_national_poll_universe",
        "known_pollsters": len(registry.get("known_pollsters", [])),
        "configured_sources": len(configured),
        "primary_sources": len(primary),
        "healthy_primary_sources": len(primary) - len(unhealthy),
        "unhealthy_primary_sources": unhealthy,
        "stale_or_unverified_primary_sources": stale_primary,
        "freshness_window_seconds": 900,
        "disabled_without_reason": disabled_without_reason,
        "registry_contract": "PASS" if registry_ok else "FAIL",
        "last_runtime_coverage": state.get("last_coverage", {}),
        "evidence_limit": "Does not assert that every known pollster has a validated poll; discovery coverage is not primary evidence.",
        "fail_closed": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if total_ok else 1)

if __name__ == "__main__":
    main()
