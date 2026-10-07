"""Validate COLMENA state invariants.

Operational blockers must only represent executable failures. Certification
prerequisites belong in certification_requirements and must never be copied
back into blocking_errors.
"""
from __future__ import annotations
from pathlib import Path
import json

STALE_IDS = {
    "PRIMARY_RECONCILIATION",
    "PRIMARY_BINARY_NOT_REPOSITORY_PINNED",
    "SEEC_PRODUCTION_EXECUTION",
    "OOS_CALIBRATION",
    "EXTERNAL_AUDIT",
    "POLL_SOURCE_COVERAGE",
    "CI_MASTER_CERTIFICATION",
}

def validate(path="docs/COLMENA_STATE.json"):
    state=json.loads(Path(path).read_text(encoding="utf-8"))
    blockers=state.get("blocking_errors", [])
    ids={x.get("id") for x in blockers}
    stale=ids & STALE_IDS
    if stale:
        raise SystemExit(f"stale certification IDs in blocking_errors: {sorted(stale)}")
    if blockers:
        raise SystemExit(f"unexpected operational blockers: {sorted(ids)}")
    if not state.get("fail_closed", False):
        raise SystemExit("fail_closed must remain enabled")
    return True

if __name__=="__main__":
    validate()
    print("COLMENA_STATE: PASS")
