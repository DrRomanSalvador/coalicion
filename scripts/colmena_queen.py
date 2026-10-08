#!/usr/bin/env python3
"""Executable Queen Gate for the COALICION mission swarm."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/"docs/COLMENA_MISSION_CONTROL.json"
WRITE_TOKENS=("integración física","conexión","eliminación","actualización","crear","release")
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def load():
    if not CONTROL.is_file(): raise SystemExit("FAIL_CLOSED: mission registry missing")
    d=json.loads(CONTROL.read_text(encoding="utf-8"))
    if d.get("repository")!="DrRomanSalvador/coalicion" or d.get("branch")!="main" or d.get("fail_closed") is not True:
        raise SystemExit("FAIL_CLOSED: invalid mission control contract")
    ms=d.get("missions")
    if not isinstance(ms,list) or not ms or len(set(ms))!=len(ms): raise SystemExit("FAIL_CLOSED: invalid/duplicate missions")
    return d
def mid(i,t): return f"M{i:04d}-{re.sub(r'[^a-z0-9]+','-',t.lower()).strip('-')[:72]}"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--ref",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    d=load(); missions=[]
    for i,t in enumerate(d["missions"],1):
        kind="WRITE_CANDIDATE" if any(x in t.lower() for x in WRITE_TOKENS) else "READ_ONLY"
        missions.append({"id":mid(i,t),"index":i,"title":t,"kind":kind,"write_authorized":False,"scope":[],"depends_on":[],"ref":a.ref})
    ro=[m["id"] for m in missions if m["kind"]=="READ_ONLY"]
    for m in missions:
        if m["kind"]=="WRITE_CANDIDATE": m["depends_on"]=ro
    plan={"schema":"COLMENA_EXECUTION_PLAN_V1","ref":a.ref,"fail_closed":True,"missions":missions}
    plan["plan_sha256"]=sha(canon(plan))
    approved=[]
    for m in missions:
        token=sha(canon({"mission_id":m["id"],"ref":m["ref"],"plan_sha256":plan["plan_sha256"],"write_authorized":False,"scope":[]}))
        approved.append({**m,"approval":token})
    out={"schema":"COLMENA_QUEEN_APPROVAL_V1","created_at":datetime.now(timezone.utc).isoformat(),"plan_sha256":plan["plan_sha256"],"fail_closed":True,"missions":approved}
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"QUEEN_GATE_PASS","missions":len(approved),"plan_sha256":plan["plan_sha256"]}))
if __name__=="__main__": main()
