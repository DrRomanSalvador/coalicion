#!/usr/bin/env python3
"""Fail-closed executable atomic worker for the COALICION Queen."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, time, os, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK_COMMAND_TIMEOUT_SECONDS = int(os.environ.get("COLMENA_COMMAND_TIMEOUT_SECONDS", "600"))

def canon(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def sha(s): return hashlib.sha256(s.encode()).hexdigest()

def command_for(title: str):
    t = title.lower()
    if any(x in t for x in ("release v1.0.0", "actualización", "integración física", "conexión ", "eliminación ", "crear ", "corregir ")):
        return None, "WRITE_OR_CHANGE_REQUIRES_EXPLICIT_SCOPE"
    if "muestreo pymc" in t or "seec producción" in t or "seec producción genuino" in t:
        return [sys.executable, "scripts/run_seec_production.py"], "SEEC_REAL_SAMPLING"
    if "calibración probabilística" in t:
        candidate = ROOT / "artifacts/data/cis_historical_2004_2023.csv"
        if not candidate.is_file():
            return None, "CALIBRATION_REQUIRES_MATERIALIZED_INPUT"
        return [sys.executable, "scripts/complete_historical_calibration.py", "--input", str(candidate), "--output", "ci_evidence/oos_calibration.json"], "PROBABILISTIC_CALIBRATION"
    if "backtest 1977-2023" in t or "backtest histórico reproducible" in t:
        return [sys.executable, "scripts/run_complete_backtest.py", "--input", "artifacts/data/cis_historical_2004_2023.csv"], "BACKTEST_COMPLETE"
    if "backtest oos" in t or "oos" in t:
        return [sys.executable, "scripts/run_full_oos.py"], "OOS"
    if "backtest 2023" in t:
        return [sys.executable, "scripts/backtest_2023_baseline.py"], "BACKTEST_2023"
    if "mc 10000" in t or "10.000" in t or "10000" in t:
        return [sys.executable, "scripts/run_mc_10000.py"], "MC_10000"
    if "temporal" in t and "decaimiento" in t:
        return [sys.executable, "scripts/add_temporal_decay.py", "--dates", "2019-11-10", "2023-07-23", "--reference-date", "2023-07-23"], "TEMPORAL_DECAY"
    if "contratos" in t and "históric" in t:
        return [sys.executable, "scripts/verify_historical_contracts.py"], "HISTORICAL_CONTRACTS"
    if "canonical" in t or "canónica" in t:
        return [sys.executable, "scripts/verify_canonical_2023.py"], "CANONICAL_2023"
    if "validación histórica" in t or ("histórica" in t and "validar" in t):
        return [sys.executable, "scripts/validate_historical_data.py"], "HISTORICAL_DATA"
    if "telegram" in t:
        return [sys.executable, "scripts/verify_telegram_integration.py"], "TELEGRAM"
    if "estado certificación" in t or ("estado" in t and "colmena" in t):
        return [sys.executable, "scripts/validate_colmena_state.py"], "STATE"
    if "audit" in t or "auditoría" in t:
        return [sys.executable, "scripts/audit_2023.py"], "AUDIT_2023"
    if "py_compile" in t or "compil" in t:
        return [sys.executable, "-m", "compileall", "-q", "src", "scripts"], "PY_COMPILE"
    if any(x in t for x in ("batería completa de tests", "tests unitarios", "tests integración", "tests end-to-end", "tests seguridad", "regresión motor", "regresión coaliciones", "regresión incertidumbre", "regresión bot", "regresión monitor", "regresión telegram")):
        return [sys.executable, "-m", "pytest", "-q"], "PYTEST"
    return None, "AI_ANALYSIS"

def load_approval(path, mission_id, ref):
    if not path.is_file():
        raise SystemExit("FAIL_CLOSED: Queen approval missing")
    d = json.loads(path.read_text(encoding="utf-8"))
    m = next((x for x in d.get("missions", []) if x.get("id") == mission_id), None)
    if m is None or m.get("ref") != ref:
        raise SystemExit("FAIL_CLOSED: mission/ref not approved")
    expected = sha(canon({
        "mission_id": m["id"], "agent_id": m["agent_id"], "ref": m["ref"], "plan_sha256": d["plan_sha256"],
        "write_authorized": m["write_authorized"], "scope": m["scope"],
    }))
    if expected != m.get("approval"):
        raise SystemExit("FAIL_CLOSED: invalid Queen approval")
    return d, m

def invoke_ai_agent(m, agent_id):
    model = os.environ.get("COLMENA_AGENT_MODEL", "onnx-community/Qwen3-0.6B-ONNX:q4f16").strip()
    payload = {"agent_id": agent_id, "mission_id": m["id"], "mission": m["title"], "scope": m.get("scope", "")}
    server = os.environ.get("COLMENA_AI_SERVER_URL", "").strip()
    if server:
        req = urllib.request.Request(
            server.rstrip("/") + "/infer",
            data=canon(payload).encode(),
            headers={"content-type":"application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
    else:
        p = subprocess.run(["node", "scripts/colmena_local_ai.mjs"], cwd=ROOT, input=canon(payload), text=True, capture_output=True, timeout=180)
        if p.returncode != 0:
            raise RuntimeError("LOCAL_AI_RUNTIME_ERROR: " + (p.stderr[-4000:] or p.stdout[-4000:]))
        rows = [x for x in p.stdout.splitlines() if x.strip()]
        if not rows:
            raise RuntimeError("FAIL_CLOSED: empty local AI runtime response")
        data = json.loads(rows[-1])
    content = str(data.get("content", "")).strip()
    if not content:
        raise RuntimeError("FAIL_CLOSED: empty local AI runtime content")
    return {"backend":"transformers.js-local","model":str(data.get("model") or model),"response_sha256":sha(content),"response_excerpt":content[:2000]}

def run(m, ref, agent_id, runtime):
    started = datetime.now(timezone.utc).isoformat()
    command, adapter = command_for(m["title"])
    if m["write_authorized"] and not m["scope"]:
        status, rc, out, err = "FAIL_CLOSED", 1, "", "write authorization without scope"
    elif command is None and adapter == "AI_ANALYSIS":
        status, rc, out, err = "PASS", 0, "", "AI_ANALYSIS_EXECUTED"
    elif command is None:
        status, rc, out, err = "BLOCKED", 2, "", adapter
    else:
        p = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=WORK_COMMAND_TIMEOUT_SECONDS)
        rc, out, err = p.returncode, p.stdout[-12000:], p.stderr[-12000:]
        if rc != 0 and "run_complete_backtest.py" in command:
            diagnostic = ROOT / "ci_evidence/backtest_complete_2004_2023.json"
            if diagnostic.is_file():
                try:
                    err = (err + "\\nBACKTEST_ARTIFACT_DIAGNOSTIC\\n" + diagnostic.read_text(encoding="utf-8")[-12000:])[-12000:]
                except OSError as exc:
                    err = (err + "\\nBACKTEST_ARTIFACT_READ_ERROR: " + str(exc))[-12000:]
        status = "PASS" if rc == 0 else "FAIL"
    return {
        "schema":"COLMENA_WORKER_EVIDENCE_V4","agent_id":agent_id,"agent_runtime":runtime,
        "mission_id":m["id"],"title":m["title"],"kind":m["kind"],"status":status,"adapter":adapter,
        "command":command,"ref":ref,"queen_approval":m["approval"],
        "started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),
        "source_write":False,"returncode":rc,"stdout":out,"stderr":err,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mission-id",required=True); ap.add_argument("--approval",required=True)
    ap.add_argument("--ref",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args()
    _,m=load_approval(Path(a.approval),a.mission_id,a.ref)
    agent_id=m.get("agent_id")
    if agent_id!="agent-"+m["id"]:
        raise SystemExit("FAIL_CLOSED: invalid agent identity")
    provider=os.environ.get("COLMENA_AGENT_PROVIDER","").strip()
    execution_id=os.environ.get("COLMENA_AGENT_EXECUTION_ID","").strip()
    ai_execution=os.environ.get("COLMENA_AI_AGENT_EXECUTION","").strip().lower()=="true"
    runtime={"provider":provider,"execution_id":execution_id,"independent":bool(provider and execution_id),"ai_execution":ai_execution,"model":os.environ.get("COLMENA_AGENT_MODEL",""),"server_mode":bool(os.environ.get("COLMENA_AI_SERVER_URL","").strip())}
    if not runtime["independent"] or not ai_execution:
        evidence={"schema":"COLMENA_WORKER_EVIDENCE_V4","mission_id":m["id"],"title":m["title"],"agent_id":agent_id,"agent_runtime":runtime,"status":"BLOCKED","adapter":"AI_AGENT_RUNTIME_REQUIRED","command":None,"ref":a.ref,"queen_approval":m["approval"],"started_at":datetime.now(timezone.utc).isoformat(),"finished_at":datetime.now(timezone.utc).isoformat(),"source_write":False,"returncode":2,"stdout":"","stderr":"FAIL_CLOSED: real independent AI-agent runtime evidence required"}
    else:
        try:
            ai=invoke_ai_agent(m,agent_id)
            evidence=run(m,a.ref,agent_id,runtime)
            evidence["ai_inference"]=ai; evidence["runtime_status"]="PASS"
            evidence["mission_status"]="ANALYSIS_COMPLETE" if evidence.get("adapter")=="AI_ANALYSIS" else evidence.get("status")
            evidence["mission_claim"]="agent_analysis_only" if evidence.get("adapter")=="AI_ANALYSIS" else "deterministic_command_execution"
        except Exception as exc:
            evidence={"schema":"COLMENA_WORKER_EVIDENCE_V4","mission_id":m["id"],"title":m["title"],"agent_id":agent_id,"agent_runtime":runtime,"status":"BLOCKED","adapter":"AI_AGENT_RUNTIME_ERROR","command":None,"ref":a.ref,"queen_approval":m["approval"],"started_at":datetime.now(timezone.utc).isoformat(),"finished_at":datetime.now(timezone.utc).isoformat(),"source_write":False,"returncode":2,"stdout":"","stderr":str(exc)}
    o=Path(a.out); o.parent.mkdir(parents=True,exist_ok=True); o.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"mission_id":m["id"],"status":evidence["status"],"adapter":evidence["adapter"],"returncode":evidence.get("returncode"),"stderr_tail":str(evidence.get("stderr",""))[-2000:],"stdout_tail":str(evidence.get("stdout",""))[-2000:]}, ensure_ascii=False))
    return 0 if evidence["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
