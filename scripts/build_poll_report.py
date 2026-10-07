#!/usr/bin/env python3
"""Build a descriptive report from validated poll records."""
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def scenario_view(parties, scenario_sets):
    rows=[]
    for coalition in scenario_sets:
        members=[p for p in coalition if p in parties]
        combined=round(sum(parties[p] for p in members),2)
        rows.append({"coalition":members,"combined_vote_share":combined,
                     "all_separate":{p:parties[p] for p in sorted(parties)}})
    return rows

def build(poll_records, scenario_sets):
    reports=[]
    for poll in poll_records:
        reports.append({
            "poll":poll,
            "status":"DESCRIPTIVE_ONLY",
            "national_vote_share_scenarios":scenario_view(poll.get("parties",{}),scenario_sets),
            "seat_scenarios":"OMITTED_NO_VALID_TERRITORIAL_INPUT",
            "policy":{"recommendations":False,"ranking_as_best_option":False,
                      "campaign_advice":False,"vote_transfer_assumptions":False,
                      "descriptive_math_only":True}
        })
    return {"schema":"NEUTRAL_POLL_REPORT_V1","status":"DESCRIPTIVE_ONLY",
            "poll_count":len(reports),"reports":reports}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--scenarios",type=Path,default=ROOT/"config/survey_watch.json")
    a=ap.parse_args()
    records=json.loads(a.input.read_text(encoding="utf-8"))
    cfg=json.loads(a.scenarios.read_text(encoding="utf-8"))
    payload=build(records,cfg.get("scenario_sets",[]))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"poll_count":payload["poll_count"]},ensure_ascii=False))
if __name__=="__main__":
    raise SystemExit(main())
