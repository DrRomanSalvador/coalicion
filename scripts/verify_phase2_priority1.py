#!/usr/bin/env python3
"""Fail-closed gate for Phase 2 Priority 1 (current data + traceability)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/surveys/current_2026/current_national.json"
MONITOR = ROOT / "artifacts/poll_monitor_state.json"
OUT = ROOT / "artifacts/phase2_priority1_status.json"

REQUIRED_TRACE = ("publication_date", "field_start", "field_end", "sample_size", "methodology", "source_url")
PRIMARY_LEVELS = {"PRIMARY_VERIFIED", "PRIMARY_PAGE_VERIFIED", "PRIMARY_VERIFIABLE"}

def sha256_record(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    surveys = registry.get("surveys", [])
    territorial = [p for p in surveys if p.get("territorial")]
    trace_failures = []
    primary = 0
    hashes = 0
    for poll in surveys:
        missing = [k for k in REQUIRED_TRACE if poll.get(k) in (None, "")]
        if not poll.get("source_url", "").startswith(("https://", "http://")):
            missing.append("source_url")
        if not poll.get("source_content_sha256"):
            missing.append("source_content_sha256")
        if missing:
            trace_failures.append({"id": poll.get("id"), "missing": sorted(set(missing))})
        else:
            hashes += 1
        if poll.get("evidence_level") in PRIMARY_LEVELS:
            primary += 1

    result = {
        "schema": "PHASE2_PRIORITY1_STATUS_V1",
        "status": "PASS" if (
            len(surveys) >= 10
            and len(territorial) >= 3
            and not trace_failures
            and primary >= 10
        ) else "BLOCKED",
        "national_survey_count": len(surveys),
        "national_requirement": 10,
        "territorial_observation_count": len(territorial),
        "territorial_requirement": 3,
        "fully_traceable_national_count": hashes,
        "primary_verified_national_count": primary,
        "traceability_failures": trace_failures,
        "official_2023_matrix_present": (ROOT / "artifacts/data/election_2023_canonical.json").is_file(),
        "official_2023_primary_evidence_present": (ROOT / "artifacts/primary_evidence/MANIFEST.json").is_file(),
        "policy": {
            "no_synthetic_values": True,
            "no_national_to_territorial_inference": True,
            "fail_closed": True,
        },
    }
    if result["status"] == "BLOCKED":
        blockers = []
        if len(surveys) < 10: blockers.append("BLOCKED_NATIONAL_SURVEY_COUNT")
        if len(territorial) < 3: blockers.append("BLOCKED_NO_3_TERRITORIAL_OBSERVATIONS")
        if trace_failures: blockers.append("BLOCKED_INCOMPLETE_TRACEABILITY")
        if primary < 10: blockers.append("BLOCKED_PRIMARY_SOURCE_COVERAGE")
        if not result["official_2023_primary_evidence_present"]:
            blockers.append("BLOCKED_2023_PRIMARY_EVIDENCE_MISSING")
        result["blockers"] = blockers
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
