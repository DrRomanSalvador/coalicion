#!/usr/bin/env python3
"""Persist a checkpoint only when the tested commit is still origin/main."""
import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def fail(message):
    print("FAIL_CLOSED: " + message, file=sys.stderr)
    raise SystemExit(2)

def main():
    tested = os.environ.get("COMMIT_SHA", "").strip()
    run_id = os.environ.get("RUN_ID", "").strip()
    attempt = os.environ.get("RUN_ATTEMPT", "").strip()
    if not tested or not run_id or not attempt:
        fail("missing workflow identity")
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    remote = subprocess.check_output(["git", "rev-parse", "origin/main"], text=True).strip()
    if remote != tested:
        fail(f"stale validation: tested={tested}, origin/main={remote}")
    path = Path("docs/COLMENA_STATE.json")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read canonical state: {exc}")
    if state.get("schema") != "COLMENA_STATE_V1" or state.get("fail_closed") is not True:
        fail("canonical state schema/gate invalid")
    if state.get("status") not in {"SELLABLE_BETA", "OPERATIONAL_BETA"}:
        fail("unsupported product status")
    state["last_colmena_checkpoint"] = {
        "schema": "COLMENA_LIGHT_CHECKPOINT_V1",
        "status": "PASS",
        "workflow": ".github/workflows/colmena_atomic_swarm.yml",
        "tested_commit": tested,
        "run_id": run_id,
        "run_attempt": attempt,
        "checks": ["state_fail_closed", "resume_gate", "reproducibility_contract",
                   "core_and_coalition_regression", "demo_e2e"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
