#!/usr/bin/env python3
"""Build one fail-closed manifest for the complete COALICIÓN intelligence stack."""
from __future__ import annotations
import hashlib, json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts"/"political_intelligence_master_manifest.json"

FILES={
 "historical_results":"data/resultados_oficiales_2004_2023.csv",
 "historical_polls":"data/encuestas_historicas_2004_2023.csv",
 "historical_manifest":"data/manifests/HISTORICAL_DATA_MATERIALIZATION.json",
 "interior_acquisition":"data/manifests/INTERIOR_ACQUISITION.json",
 "oos":"artifacts/oos_historical_2004_2023.json",
 "oos_calibration":"ci_evidence/oos_calibration.json",
 "seec":"ci_evidence/seec_posterior.json",
 "poll_coverage":"ci_evidence/poll_source_coverage.json",
 "external_audit":"ci_evidence/external_audit.json",
 "decision_snapshot":"artifacts/decision_snapshot.json",
 "execution_state":"artifacts/execution_state.json",
 "poll_state":"artifacts/poll_monitor_state.json",
}

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()

def file_gate(key,path):
 if not path.is_file(): return {"status":"MISSING","path":str(path.relative_to(ROOT))}
 return {"status":"PRESENT","path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":sha(path)}

def json_gate(key,path):
 base=file_gate(key,path)
 if base["status"]!="PRESENT": return base
 try:
  value=json.loads(path.read_text(encoding="utf-8"))
 except Exception as exc:
  base["status"]="INVALID_JSON"; base["reason"]=type(exc).__name__; return base
 base["declared_status"]=value.get("status") if isinstance(value,dict) else None
 return base

def main():
 files={}
 for key,rel in FILES.items():
  p=ROOT/rel
  files[key]=json_gate(key,p) if p.suffix==".json" else file_gate(key,p)

 gates={
  "historical_results": files["historical_results"]["status"]=="PRESENT",
  "historical_polls": files["historical_polls"]["status"]=="PRESENT",
  "historical_materialization": files["historical_manifest"].get("declared_status")=="PASS",
  "interior_acquisition": files["interior_acquisition"].get("declared_status")=="PASS",
  "oos": files["oos"].get("declared_status")=="PASS",
  "oos_calibration": files["oos_calibration"].get("declared_status")=="PASS",
  "seec": files["seec"].get("declared_status")=="PASS",
  "poll_coverage": files["poll_coverage"].get("declared_status")=="PASS",
  "decision_snapshot": files["decision_snapshot"]["status"]=="PRESENT",
  "external_audit": files["external_audit"].get("declared_status")=="PASS",
 }
 required_for_operational={"historical_results","historical_polls","historical_materialization","interior_acquisition","oos","oos_calibration","seec","poll_coverage"}
 blockers=[k for k in required_for_operational if not gates[k]]
 certification_blocked=not gates["external_audit"]
 payload={
  "schema":"COALICION_POLITICAL_INTELLIGENCE_MASTER_V1",
  "generated_at":datetime.now(timezone.utc).isoformat(),
  "as_of":date.today().isoformat(),
  "status":"READY" if not blockers else "BLOCKED",
  "operational_gates":gates,
  "blockers":sorted(blockers),
  "certification":{
   "status":"BLOCKED" if certification_blocked else "ELIGIBLE_FOR_EXTERNAL_AUDIT_REVIEW",
   "external_audit_required":True,
   "self_certification_forbidden":True,
  },
  "files":files,
  "pipeline":["primary_sources","materialization","validation","poll_monitor","historical_oos","calibration","SEEC","prediction","territories","electoral_allocation","uncertainty","marginality","counterfactuals","decision","briefing","telegram","audit","reproducibility"],
  "policy":{"neutral":True,"no_synthetic_values":True,"fail_closed":True,"no_persuasion":True,"no_microtargeting":True},
 }
 payload["sha256"]=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({"status":payload["status"],"blockers":payload["blockers"],"sha256":payload["sha256"]},ensure_ascii=False))
 return 0 if not blockers else 1

if __name__=="__main__": raise SystemExit(main())
