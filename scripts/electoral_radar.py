#!/usr/bin/env python3
"""Execute the connected electoral radar over the canonical decision snapshot."""
from __future__ import annotations
import argparse, json
from datetime import date, datetime, timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.electoral_radar_adapter import build_radar_from_snapshot

DEFAULT_INPUT=ROOT/"artifacts/electoral_decision_snapshot.json"
DEFAULT_STATE=ROOT/"artifacts/electoral_radar_state.json"
DEFAULT_REPORT=ROOT/"artifacts/electoral_radar_report.json"
SURVEY_REPORT=ROOT/"artifacts/survey_watch_report.json"

def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def source_health():
    report=load(SURVEY_REPORT,{})
    out=[]
    for event in report.get("alerts",[]):
        if event.get("status") in {"BLOCKED_SOURCE_PARSE_OR_FETCH","INVALID_SOURCE_CONFIG"}:
            out.append({
                "id":event.get("source_id"),
                "status":"FAILED",
                "coverage_role":"secondary",
                "failure_streak":None,
                "last_success":None,
            })
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,default=DEFAULT_INPUT)
    ap.add_argument("--state",type=Path,default=DEFAULT_STATE)
    ap.add_argument("--output",type=Path,default=DEFAULT_REPORT)
    a=ap.parse_args()
    if not a.input.exists():
        payload={"status":"BLOCKED","code":"BLOCKED_NO_DECISION_SNAPSHOT",
                 "reason":"No existe el snapshot territorial validado; no se infiere territorialidad."}
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(payload,ensure_ascii=False))
        return 1
    current=load(a.input,{})
    if current.get("status")!="OK":
        payload={"status":"BLOCKED","code":"BLOCKED_INVALID_DECISION_SNAPSHOT",
                 "reason":"El snapshot canónico no está en estado OK.","snapshot_status":current.get("status")}
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(payload,ensure_ascii=False))
        return 1
    state=load(a.state,{"last_snapshot":None,"last_radar":None})
    previous=state.get("last_snapshot")
    evidence=list(current.get("evidence_refs",[]))
    if current.get("traceability",{}).get("input_hash"):
        evidence.append("snapshot:"+current["traceability"]["input_hash"])
    radar=build_radar_from_snapshot(
        today=date.today(),
        current=current,
        previous=previous,
        sources=source_health(),
        evidence_refs=sorted(set(evidence)),
    )
    radar["generated_at"]=datetime.now(timezone.utc).isoformat()
    radar["delivery"]={"immediate":True,"daily_digest":True,"transport":"optional"}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(radar,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state={"last_snapshot":current,"last_radar":radar,"updated_at":radar["generated_at"]}
    a.state.parent.mkdir(parents=True,exist_ok=True)
    a.state.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":radar["status"],"alert_count":radar["alert_count"],
                      "report":str(a.output.relative_to(ROOT))},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
