#!/usr/bin/env python3
import json
from datetime import date
from pathlib import Path
from src.real_estimation_pipeline import PipelineBlocked, run_real_estimation
ROOT=Path(__file__).resolve().parents[1]
OBS=ROOT/"artifacts/estimation/observations.json"
OUT=ROOT/"artifacts/estimation/real_estimation.json"
def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if not OBS.exists():
        OUT.write_text(json.dumps({"schema":"REAL_ESTIMATION_V1","status":"BLOCKED_NO_OBSERVATIONS"},ensure_ascii=False,indent=2)+"\n")
        return 0
    observations=json.loads(OBS.read_text(encoding="utf-8"))
    territorial=next((p.get("territorial") for p in observations.get("polls",[]) if p.get("territorial")),None)
    try:
        if not territorial:
            raise PipelineBlocked("BLOCKED_NO_TERRITORIAL_INPUT")
        result=run_real_estimation(observations=observations,votes=territorial["votes"],seats=territorial["seats"],blank=territorial["blank_votes"],special=territorial.get("special",{}),coalition_parties=territorial.get("coalition_parties",()),today=date.today(),iterations=10000,seed=20261006)
        payload={"schema":"REAL_ESTIMATION_V1","status":"EXECUTED","result":result}
    except PipelineBlocked as exc:
        payload={"schema":"REAL_ESTIMATION_V1","status":"BLOCKED","reason":str(exc),"observation_status":observations.get("status"),"national_poll_count":observations.get("national_poll_count",0),"territorial_poll_count":observations.get("territorial_poll_count",0)}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":payload["status"],"reason":payload.get("reason")},ensure_ascii=False))
if __name__=="__main__": raise SystemExit(main())
