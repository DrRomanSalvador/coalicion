#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"artifacts"; SOURCE=ROOT/"pasted_text_1791452605.txt"; PLAN=ART/"repair_plan.json"; STATE=ART/"repair_state.json"; LOG=ART/"repair_log.jsonl"
def main():
    ART.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    if not SOURCE.is_file():
        STATE.write_text(json.dumps({"schema":"COALICION_REPAIR_STATE_V1","status":"blocked_input_missing","current_fault":None,"current_mission":None,"total_faults_expected":466,"source":"pasted_text_1791452605.txt","updated_at":now},indent=2)+"\n",encoding="utf-8")
        with LOG.open("a",encoding="utf-8") as f: f.write(json.dumps({"timestamp":now,"action":"initialize","result":"BLOCKED_INPUT_MISSING"})+"\n")
        raise SystemExit("FAIL_CLOSED: pasted_text_1791452605.txt is required")
    if not PLAN.is_file(): raise SystemExit("FAIL_CLOSED: repair_plan.json missing")
    faults=json.loads(PLAN.read_text(encoding="utf-8")).get("faults",[])
    if len(faults)!=466: raise SystemExit(f"FAIL_CLOSED: expected 466 faults, found {len(faults)}")
    print("Repair plan valid: 466 faults")
if __name__=="__main__": main()
