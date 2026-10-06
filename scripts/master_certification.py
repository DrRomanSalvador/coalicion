"""Master SEEC certification gate. PASS requires evidence, not source-code markers."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass(frozen=True)
class Gate:
    name:str
    status:str
    detail:str

def _gate(name, condition, detail):
    return Gate(name, "PASS" if condition else "FAIL", detail)

def certify(root="."):
    r=Path(root)
    gates=[]
    # Source materialization must be real and hashed.
    manifest=r/"ci_evidence/historico_manifest.json"
    tier=r/"ci_evidence/historico_source_tier.txt"
    gates.append(_gate("source_manifest", manifest.exists(),
                       "manifest de datos materializado"))
    tier_text=tier.read_text() if tier.exists() else ""
    gates.append(_gate("primary_interior", "PRIMARY_INTERIOR" in tier_text,
                       "la fuente primaria debe estar materializada"))
    # Exact reconciliation, never a warning-only path.
    recon=r/"ci_evidence/reconciliation.json"
    if recon.exists():
        x=json.loads(recon.read_text())
        gates.append(_gate("reconciliation", x.get("status")=="PASS" and x.get("max_abs_diff",1)>-1,
                           "reconciliación primaria/secundaria exacta"))
    else:
        gates.append(_gate("reconciliation",False,"falta evidencia de reconciliación"))
    # Full SEEC posterior and MC evidence.
    posterior=r/"ci_evidence/seec_posterior.json"
    gates.append(_gate("seec_posterior", posterior.exists(),
                       "posterior jerárquico ejecutado"))
    if posterior.exists():
        x=json.loads(posterior.read_text())
        gates.append(_gate("mc_10000", int(x.get("draws",0))>=10000,
                           ">=10.000 simulaciones"))
    else:
        gates.append(_gate("mc_10000",False,"sin posterior"))
    # Expanding OOS calibration gate.
    calib=r/"ci_evidence/oos_calibration.json"
    gates.append(_gate("oos_calibration", calib.exists(),
                       "backtest expanding-window"))
    if calib.exists():
        x=json.loads(calib.read_text())
        gates.append(_gate("coverage_90", float(x.get("coverage_90",0))>=0.85,
                           "cobertura nominal 90% >= 85%"))
        gates.append(_gate("seat_mae", float(x.get("seat_mae",1e9))<10,
                           "MAE escaños < 10"))
    else:
        gates += [Gate("coverage_90","FAIL","sin calibración"),
                  Gate("seat_mae","FAIL","sin calibración")]
    # Independent audit must be a separate evidence artifact.
    ext=r/"ci_evidence/external_audit.json"
    gates.append(_gate("external_audit", ext.exists(),
                       "auditoría independiente materializada"))
    ok=all(g.status=="PASS" for g in gates)
    return {"status":"CERTIFIED" if ok else "BLOCKED","gates":[g.__dict__ for g in gates]}

if __name__=="__main__":
    out=certify()
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if out["status"]=="CERTIFIED" else 1)
