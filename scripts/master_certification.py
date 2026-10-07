"""Master SEEC certification gate. PASS requires evidence, not source-code markers."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

@dataclass(frozen=True)
class Gate:
    name:str
    status:str
    detail:str

def _gate(name, condition, detail):
    return Gate(name, "PASS" if condition else "FAIL", detail)
def _approval_evidence_digest(gates):
    payload = [g.__dict__ for g in gates]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def _valid_request(path: Path) -> bool:
    try:
        x = json.loads(path.read_text(encoding="utf-8"))
        return (
            x.get("schema") == "CERTIFICATION_REQUEST_V1"
            and x.get("status") == "PENDING_APPROVAL"
            and x.get("approval_required") is True
            and x.get("approved") is False
        )
    except Exception:
        return False

def _valid_approval(path: Path, gates) -> bool:
    try:
        x = json.loads(path.read_text(encoding="utf-8"))
        return (
            x.get("schema") == "CERTIFICATION_APPROVAL_V1"
            and x.get("decision") == "CERTIFY"
            and x.get("approved") is True
            and bool(x.get("approved_by"))
            and bool(x.get("approved_at"))
            and x.get("evidence_digest") == _approval_evidence_digest(gates)
        )
    except Exception:
        return False


def certify(root="."):
    r=Path(root)
    gates=[]
    # Source materialization must be real and hashed.
    manifest=r/"ci_evidence/historico_manifest.json"
    tier=r/"ci_evidence/historico_source_tier.txt"
    manifest_ok=False
    if manifest.exists():
        try:
            mx=json.loads(manifest.read_text(encoding="utf-8"))
            manifest_ok=mx.get("status") in {"PASS","CERTIFIED"} and mx.get("source_tier")=="PRIMARY_INTERIOR"
        except Exception:
            manifest_ok=False
    gates.append(_gate("source_manifest", manifest_ok,
                       "manifest primario materializado y validado"))
    tier_text=tier.read_text() if tier.exists() else ""
    gates.append(_gate("primary_interior", tier_text.strip()=="PRIMARY_INTERIOR",
                       "la fuente primaria debe estar materializada y declarada explícitamente"))
    # Exact reconciliation, never a warning-only path.
    recon=r/"ci_evidence/reconciliation.json"
    if recon.exists():
        x=json.loads(recon.read_text())
        gates.append(_gate("reconciliation", x.get("status")=="PASS" and float(x.get("max_abs_diff",1))==0,
                           "reconciliación exacta; diferencia máxima = 0"))
    else:
        gates.append(_gate("reconciliation",False,"falta evidencia de reconciliación"))
    # Full SEEC posterior and MC evidence.
    posterior=r/"ci_evidence/seec_posterior.json"
    posterior_ok=False
    if posterior.exists():
        try:
            px=json.loads(posterior.read_text(encoding="utf-8"))
            posterior_ok=px.get("status") in {"PASS","CERTIFIED"} and int(px.get("draws",0))>=10000
        except Exception:
            posterior_ok=False
    gates.append(_gate("seec_posterior", posterior_ok,
                       "posterior jerárquico ejecutado y certificado"))
    if posterior.exists():
        x=json.loads(posterior.read_text())
        gates.append(_gate("mc_10000", x.get("status") in {"PASS","CERTIFIED"} and int(x.get("draws",0))>=10000,
                           ">=10.000 simulaciones en posterior válido"))
    else:
        gates.append(_gate("mc_10000",False,"sin posterior"))
    # Expanding OOS calibration gate.
    calib=r/"ci_evidence/oos_calibration.json"
    calib_ok=False
    if calib.exists():
        try:
            cx=json.loads(calib.read_text(encoding="utf-8"))
            calib_ok=cx.get("status") in {"PASS","CERTIFIED"}
        except Exception:
            calib_ok=False
    gates.append(_gate("oos_calibration", calib_ok,
                       "backtest expanding-window certificado"))
    if calib.exists():
        x=json.loads(calib.read_text())
        gates.append(_gate("coverage_90", x.get("status") in {"PASS","CERTIFIED"} and float(x.get("coverage_90",0))>=0.85,
                           "cobertura nominal 90% >= 85%"))
        gates.append(_gate("seat_mae", x.get("status") in {"PASS","CERTIFIED"} and float(x.get("seat_mae",1e9))<10,
                           "MAE escaños < 10"))
    else:
        gates += [Gate("coverage_90","FAIL","sin calibración"),
                  Gate("seat_mae","FAIL","sin calibración")]
    # Independent audit must be a separate evidence artifact.
    ext=r/"ci_evidence/external_audit.json"
    external_ok=False
    if ext.exists():
        try:
            ex=json.loads(ext.read_text(encoding="utf-8"))
            external_ok=(ex.get("status") in {"PASS","CERTIFIED"} and ex.get("independent") is True and bool(ex.get("auditor")))
        except Exception:
            external_ok=False
    gates.append(_gate("external_audit", external_ok,
                       "auditoría independiente materializada y declarada"))
    gates_pass = all(g.status=="PASS" for g in gates)
    request = r/"ci_evidence/certification_request.json"
    approval = r/"ci_evidence/certification_approval.json"
    request_valid = request.exists() and _valid_request(request)
    approval_valid = approval.exists() and _valid_approval(approval, gates)

    # Nunca se certifica por existencia de archivos. La aprobación debe ser
    # humana, explícita y vinculada exactamente a los gates evaluados.
    certified = gates_pass and request_valid and approval_valid
    if certified:
        status = "CERTIFIED"
    elif request_valid:
        status = "PENDING_APPROVAL"
    else:
        status = "PENDING_REQUEST"
    return {
        "status": status,
        "eligible_for_approval": gates_pass,
        "certification_request": request_valid,
        "certification_approval": approval_valid,
        "approval_evidence_digest": _approval_evidence_digest(gates),
        "gates": [g.__dict__ for g in gates],
        "rule": "La solicitud y la aprobación son estados distintos; ningún archivo de solicitud certifica por sí mismo. La aprobación válida debe enlazar el digest exacto de los gates.",
    }

if __name__=="__main__":
    out=certify()
    print(json.dumps(out,ensure_ascii=False,indent=2))
    raise SystemExit(0 if out["status"]=="CERTIFIED" else 1)
