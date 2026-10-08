#!/usr/bin/env python3
"""Fail-closed atomic worker runtime. Workers cannot modify source code by default."""
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mission-id",required=True); ap.add_argument("--approval",required=True); ap.add_argument("--ref",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    p=Path(a.approval)
    if not p.is_file(): raise SystemExit("FAIL_CLOSED: Queen approval missing")
    d=json.loads(p.read_text(encoding="utf-8")); m=next((x for x in d.get("missions",[]) if x["id"]==a.mission_id),None)
    if m is None or m["ref"]!=a.ref: raise SystemExit("FAIL_CLOSED: mission/ref not approved")
    expected=sha(canon({"mission_id":m["id"],"ref":m["ref"],"plan_sha256":d["plan_sha256"],"write_authorized":m["write_authorized"],"scope":m["scope"]}))
    if expected!=m["approval"]: raise SystemExit("FAIL_CLOSED: invalid Queen approval")
    if m["write_authorized"] and not m["scope"]: raise SystemExit("FAIL_CLOSED: write authorization without scope")
    cmd=[sys.executable,"-m","py_compile","scripts/colmena_queen.py","scripts/colmena_worker.py"]
    r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    status="PASS" if r.returncode==0 else "FAIL_CLOSED"
    evidence={"schema":"COLMENA_WORKER_EVIDENCE_V1","mission_id":m["id"],"title":m["title"],"status":status,"ref":a.ref,"queen_approval":m["approval"],"started_at":datetime.now(timezone.utc).isoformat(),"source_write":False,"stdout":r.stdout[-4000:],"stderr":r.stderr[-4000:]}
    o=Path(a.out); o.parent.mkdir(parents=True,exist_ok=True); o.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"mission_id":m["id"],"status":status}))
    return 0 if status=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
