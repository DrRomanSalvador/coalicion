#!/usr/bin/env python3
"""Fail-closed executable atomic worker for the COALICION Queen."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def canon(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def sha(s): return hashlib.sha256(s.encode()).hexdigest()

def command_for(title: str):
    t = title.lower()
    if any(x in t for x in ("release v1.0.0", "actualización", "integración física", "conexión ", "eliminación ", "crear ", "corregir ")):
        return None, "WRITE_OR_CHANGE_REQUIRES_EXPLICIT_SCOPE"
    if "muestreo pymc" in t or "seec producción" in t or "seec producción genuino" in t:
        return [sys.executable, "scripts/run_seec_production.py"], "SEEC_REAL_SAMPLING"
    if "calibración probabilística" in t:
        return [sys.executable, "scripts/run_probabilistic_calibration.py"], "PROBABILISTIC_CALIBRATION"
    if "backtest 1977-2023" in t:
        return [sys.executable, "scripts/run_complete_backtest.py"], "BACKTEST_COMPLETE"
    if "backtest oos" in t or "oos" in t:
        return [sys.executable, "scripts/run_full_oos.py"], "OOS"
    if "backtest 2023" in t:
        return [sys.executable, "scripts/backtest_2023_baseline.py"], "BACKTEST_2023"
    if "mc 10000" in t or "10.000" in t or "10000" in t:
        return [sys.executable, "scripts/run_mc_10000.py"], "MC_10000"
    if "temporal" in t and "decaimiento" in t:
        return [sys.executable, "scripts/add_temporal_decay.py"], "TEMPORAL_DECAY"
    if "contratos" in t and "históric" in t:
        return [sys.executable, "scripts/verify_historical_contracts.py"], "HISTORICAL_CONTRACTS"
    if "canonical" in t or "canónica" in t:
        return [sys.executable, "scripts/verify_canonical_2023.py"], "CANONICAL_2023"
    if "validación histórica" in t or "histórica" in t and "validar" in t:
        return [sys.executable, "scripts/validate_historical_data.py"], "HISTORICAL_DATA"
    if "telegram" in t:
        return [sys.executable, "scripts/verify_telegram_integration.py"], "TELEGRAM"
    if "estado certificación" in t or "estado" in t and "colmena" in t:
        return [sys.executable, "scripts/validate_colmena_state.py"], "STATE"
    if "audit" in t or "auditoría" in t:
        return [sys.executable, "scripts/audit_2023.py"], "AUDIT_2023"
    if "py_compile" in t or "compil" in t:
        return [sys.executable, "-m", "compileall", "-q", "src", "scripts"], "PY_COMPILE"
    if any(x in t for x in ("test", "regresión", "batería completa", "end-to-end", "integración", "seguridad")):
        return [sys.executable, "-m", "pytest", "-q"], "PYTEST"
    return None, "NO_EXECUTABLE_ADAPTER"

def load_approval(path, mission_id, ref):
    if not path.is_file():
        raise SystemExit("FAIL_CLOSED: Queen approval missing")
    d = json.loads(path.read_text(encoding="utf-8"))
    m = next((x for x in d.get("missions", []) if x.get("id") == mission_id), None)
    if m is None or m.get("ref") != ref:
        raise SystemExit("FAIL_CLOSED: mission/ref not approved")
    expected = sha(canon({
        "mission_id": m["id"], "ref": m["ref"], "plan_sha256": d["plan_sha256"],
        "write_authorized": m["write_authorized"], "scope": m["scope"],
    }))
    if expected != m.get("approval"):
        raise SystemExit("FAIL_CLOSED: invalid Queen approval")
    return d, m

def run(m, ref):
    started = datetime.now(timezone.utc).isoformat()
    command, adapter = command_for(m["title"])
    if m["write_authorized"] and not m["scope"]:
        status, rc, out, err = "FAIL_CLOSED", 1, "", "write authorization without scope"
    elif command is None:
        status, rc, out, err = "BLOCKED", 2, "", adapter
    else:
        p = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        rc, out, err = p.returncode, p.stdout[-12000:], p.stderr[-12000:]
        status = "PASS" if rc == 0 else "FAIL"
    return {
        "schema": "COLMENA_WORKER_EVIDENCE_V2",
        "mission_id": m["id"], "title": m["title"], "kind": m["kind"],
        "status": status, "adapter": adapter, "command": command,
        "ref": ref, "queen_approval": m["approval"],
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "source_write": False, "returncode": rc, "stdout": out, "stderr": err,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mission-id", required=True)
    ap.add_argument("--approval", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _, m = load_approval(Path(a.approval), a.mission_id, a.ref)
    evidence = run(m, a.ref)
    o = Path(a.out); o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mission_id": m["id"], "status": evidence["status"], "adapter": evidence["adapter"]}))
    if evidence["status"] != "PASS":
        if evidence.get("stdout"):
            print(evidence["stdout"])
        if evidence.get("stderr"):
            print(evidence["stderr"], file=sys.stderr)
    return 0 if evidence["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
