#!/usr/bin/env python3
"""Materialize the canonical observed-poll input for real estimation."""
from __future__ import annotations
import json
from pathlib import Path
from src.real_estimation_pipeline import materialize_observations

ROOT=Path(__file__).resolve().parents[1]
SURVEYS=ROOT/"artifacts"/"surveys"
OUT=ROOT/"artifacts"/"estimation"/"observations.json"

def main():
    reports=sorted(SURVEYS.glob("polls_*.json"))
    if not reports:
        raise SystemExit("BLOCKED_NO_POLL_REPORTS")
    latest=json.loads(reports[-1].read_text(encoding="utf-8"))
    polls=latest.get("validated_polls", [])
    if not polls:
        payload={"schema":"REAL_ESTIMATION_OBSERVATIONS_V1","status":"BLOCKED_NO_OBSERVED_POLL_RECORDS","national_poll_count":0,"territorial_poll_count":0,"polls":[],"policy":{"observed_only":True,"national_to_territorial_inference":False},"input_hash":None}
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    else:
        payload=materialize_observations(polls, OUT)
    print(json.dumps({
        "status":payload["status"],
        "national_poll_count":payload["national_poll_count"],
        "territorial_poll_count":payload["territorial_poll_count"],
        "output":str(OUT),
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
