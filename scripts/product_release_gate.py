#!/usr/bin/env python3
"""Fail-closed product release gate."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.reproducibility_contract import ExecutionContract
REQUIRED_FILES=("README.md","QUICKSTART.md","Dockerfile","docker_entrypoint.py","api.py","web/dashboard/index.html","src/telegram_bot.py","src/pipeline/full_election.py","requirements.lock","docs/DEPLOYMENT.md")
EVIDENCE={"SEEC":"ci_evidence/seec_production.json","MC":"ci_evidence/mc_10000.json","OOS":"ci_evidence/oos_calibration.json","MASTER":"ci_evidence/master_certification.json","POLL_COVERAGE":"ci_evidence/poll_source_coverage.json"}
OUT=ROOT/"ci_evidence/product_release_gate.json"
def load(name):
    path=ROOT/name
    if not path.is_file(): raise SystemExit(f"BLOCKED:MISSING_EVIDENCE:{name}")
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc: raise SystemExit(f"BLOCKED:INVALID_EVIDENCE:{name}:{exc}") from exc
    if not isinstance(value,dict): raise SystemExit(f"BLOCKED:INVALID_EVIDENCE_SHAPE:{name}")
    return value
def main():
    missing=[p for p in REQUIRED_FILES if not (ROOT/p).is_file()]
    if missing: raise SystemExit("BLOCKED:MISSING_PRODUCT_FILES:"+",".join(missing))
    evidence={k:load(v) for k,v in EVIDENCE.items()}
    checks={"seec_pass":evidence["SEEC"].get("status")=="PASS",
        "seec_seed_canonical":evidence["SEEC"].get("seed")==ExecutionContract.seed==evidence["SEEC"].get("canonical_seed"),"mc_pass":evidence["MC"].get("status")=="PASS",
        "mc_seed_canonical":evidence["MC"].get("seed")==ExecutionContract.seed==evidence["MC"].get("canonical_seed"),"oos_pass":evidence["OOS"].get("status")=="PASS",
        "oos_contract_valid":bool(evidence["OOS"].get("leakage_checks",{}).get("all_test_elections_use_only_prior_elections")) and bool(evidence["OOS"].get("coverage_gate",{}).get("passed")),"poll_coverage_pass":evidence["POLL_COVERAGE"].get("status")=="PASS","internal_master_gates_pass":all(g.get("status")=="PASS" for g in evidence["MASTER"].get("gates",[]) if g.get("name")!="external_audit"),"external_audit_not_claimed":evidence["MASTER"].get("status")=="READY_FOR_EXTERNAL_AUDIT","fail_closed":all(bool(evidence[k].get("fail_closed",False)) for k in ("SEEC","MC","POLL_COVERAGE","MASTER"))}
    if not all(checks.values()):
        OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps({"schema":"PRODUCT_RELEASE_GATE_V1","status":"BLOCKED","checks":checks},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        raise SystemExit("BLOCKED:PRODUCT_RELEASE_GATE:"+",".join(k for k,v in checks.items() if not v))
    result={"schema":"PRODUCT_RELEASE_GATE_V1","status":"SELLABLE_BETA","certification":"READY_FOR_EXTERNAL_AUDIT","external_audit":"OPEN","checks":checks,"product_surfaces":["API","dashboard","Telegram","full_election_pipeline","evidence_exports"],"claim_boundary":"Sellable operational beta; not externally audited and not predictive-certification."}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": raise SystemExit(main())
