#!/usr/bin/env python3
"""Fail-closed Queen closure gate for worker evidence."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--approval",required=True)
    ap.add_argument("--evidence-dir",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    approval=json.loads(Path(a.approval).read_text(encoding="utf-8"))
    expected={m["id"] for m in approval["missions"]}
    files=sorted(Path(a.evidence_dir).glob("*.json"))
    parsed=[]
    for p in files:
        try:
            data=json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("mission_id"), str):
            parsed.append((p, data))
    evidence={data["mission_id"]: data for _, data in parsed}
    mission_files=[p for p, _ in parsed]
    missing=sorted(expected-set(evidence))
    extra=sorted(set(evidence)-expected)
    failed=sorted(k for k,v in evidence.items() if v.get("status")!="PASS")
    runtime_failed=sorted(k for k,v in evidence.items() if v.get("runtime_status")!="PASS")
    runtime_missing=sorted(k for k,v in evidence.items() if not (
        v.get("agent_runtime",{}).get("provider") and
        v.get("agent_runtime",{}).get("execution_id") and
        v.get("agent_runtime",{}).get("independent") is True and
        v.get("agent_runtime",{}).get("ai_execution") is True and
        isinstance(v.get("ai_inference"), dict) and
        v.get("ai_inference",{}).get("response_sha256")
    ))
    bad_agents=sorted(k for k,v in evidence.items() if v.get("agent_id") != "agent-"+k)
    statuses={}
    for v in evidence.values(): statuses[v.get("status","UNKNOWN")]=statuses.get(v.get("status","UNKNOWN"),0)+1
    runtime_closed=(not missing and not extra and not runtime_missing and not bad_agents and not runtime_failed and len(evidence)==len(expected))
    closed=runtime_closed
    result={
        "schema":"COLMENA_CLOSURE_EVIDENCE_V1",
        "plan_sha256":approval["plan_sha256"],
        "expected_missions":len(expected),
        "evidence_files":len(mission_files),
        "missing":missing,"extra":extra,"failed":failed,
        "runtime_missing":runtime_missing,"runtime_failed":runtime_failed,"bad_agents":bad_agents,
        "mission_failures":failed,
        "status_counts":statuses,
        "status":"PASS" if closed else "BLOCKED",
        "fail_closed":True,
    }
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"expected":len(expected),"evidence":len(files),"failed":len(failed),"missing":len(missing)}))
    return 0 if closed else 1

if __name__=="__main__":
    raise SystemExit(main())
