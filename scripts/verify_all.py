#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"artifacts"; PLAN=ART/"repair_plan.json"; OUT=ART/"verification_report.json"
def main():
    if not PLAN.is_file(): raise SystemExit("FAIL_CLOSED: repair_plan.json missing")
    faults=json.loads(PLAN.read_text(encoding="utf-8")).get("faults",[])
    if len(faults)!=466: raise SystemExit(f"FAIL_CLOSED: expected 466 faults, found {len(faults)}")
    invalid=[f for f in faults if f.get("status") not in {"pending","in_progress","completed","failed"}]
    if invalid: raise SystemExit(f"FAIL_CLOSED: invalid statuses: {len(invalid)}")
    counts={s:sum(f.get("status")==s for f in faults) for s in ("pending","in_progress","completed","failed")}
    report={"schema":"COALICION_REPAIR_VERIFICATION_V1","timestamp":datetime.now(timezone.utc).isoformat(),"total":466,**counts,"verified_completed":0,"status":"BLOCKED" if counts["pending"] or counts["failed"] else "READY_FOR_FINAL_VERIFICATION"}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
