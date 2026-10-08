#!/usr/bin/env python3
"""Execute the real-estimation pipeline only from observed territorial data."""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from src.real_estimation_pipeline import PipelineBlocked, run_real_estimation
from src.electoral_radar_adapter import build_radar_from_snapshot

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
        reason=str(exc)
        blocked_snapshot={
            "status":"BLOCKED",
            "territory":"NO_EXPLICIT_TERRITORIAL_OBSERVATION",
            "projection":{"party":{}},
            "marginality":{"most_marginal":[]},
            "coalitions":None,
            "uncertainty":None,
            "methodology":{"status":"NOT_PROMOTED","promotion_allowed":False},
            "traceability":{"input_hash":observations.get("input_hash"),"output_hash":None},
        }
        radar=build_radar_from_snapshot(
            today=date.today(),
            current=blocked_snapshot,
            evidence_refs=[observations.get("input_hash","")],
        )
        payload={"schema":"REAL_ESTIMATION_V1","status":"BLOCKED","reason":reason,
                 "observation_status":observations.get("status"),
                 "national_poll_count":observations.get("national_poll_count",0),
                 "territorial_poll_count":observations.get("territorial_poll_count",0),
                 "radar":radar}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"reason":payload.get("reason")},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
