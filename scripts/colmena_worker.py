#!/usr/bin/env python3
"""Fail-closed executable atomic worker for the COALICION Queen."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, time, os, urllib.request, urllib.error
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
        return [sys.executable, "scripts/add_temporal_decay.py", "--dates", "2019-11-10", "2023-07-23", "--reference-date", "2023-07-23"], "TEMPORAL_DECAY"
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
        "mission_id": m["id"], "agent_id": m["agent_id"], "ref": m["ref"], "plan_sha256": d["plan_sha256"],
        "write_authorized": m["write_authorized"], "scope": m["scope"],
    }))
    if expected != m.get("approval"):
        raise SystemExit("FAIL_CLOSED: invalid Queen approval")
    return d, m

def invoke_ai_agent(m, agent_id):
    token = os.environ.get("HF_TOKEN", "").strip()
    model = os.environ.get("COLMENA_AGENT_MODEL", "openai/gpt-oss-120b:fastest").strip()
    if not token:
        raise RuntimeError("FAIL_CLOSED: HF_TOKEN missing")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an isolated COALICION worker agent. You do not govern the repository. Return JSON only."},
            {"role": "user", "content": json.dumps({"agent_id": agent_id, "mission_id": m["id"], "mission": m["title"], "scope": m.get("scope","")}, ensure_ascii=False)}
        ],
        "stream": False,
        "max_tokens": 300
    }
    req = urllib.request.Request("https://router.huggingface.co/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("FAIL_CLOSED: empty AI runtime response")
    return {"model": model, "response_sha256": sha(content), "response_excerpt": content[:2000]}

def run(m, ref, agent_id, runtime):
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
        "schema": "COLMENA_WORKER_EVIDENCE_V3",
        "agent_id": agent_id,
        "agent_runtime": runtime,
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
    agent_id = m.get("agent_id")
    if agent_id != "agent-" + m["id"]:
        raise SystemExit("FAIL_CLOSED: invalid agent identity")
    provider = os.environ.get("COLMENA_AGENT_PROVIDER", "").strip()
    execution_id = os.environ.get("COLMENA_AGENT_EXECUTION_ID", "").strip()
    ai_execution = os.environ.get("COLMENA_AI_AGENT_EXECUTION", "").strip().lower() == "true"
    runtime = {"provider": provider, "execution_id": execution_id, "independent": bool(provider and execution_id), "ai_execution": ai_execution, "model": os.environ.get("COLMENA_AGENT_MODEL", "")}
    if not runtime["independent"] or not ai_execution:
        evidence = {"schema":"COLMENA_WORKER_EVIDENCE_V3","mission_id":m["id"],"title":m["title"],"agent_id":agent_id,"agent_runtime":runtime,"status":"BLOCKED","adapter":"AI_AGENT_RUNTIME_REQUIRED","command":None,"ref":ref,"queen_approval":m["approval"],"started_at":datetime.now(timezone.utc).isoformat(),"finished_at":datetime.now(timezone.utc).isoformat(),"source_write":False,"returncode":2,"stdout":"","stderr":"FAIL_CLOSED: real independent AI-agent runtime evidence required"}
    else:
        try:
            ai = invoke_ai_agent(m, agent_id)
            evidence = run(m, a.ref, agent_id, runtime)
            evidence["ai_inference"] = ai
            evidence["runtime_status"] = "PASS"
            evidence["mission_status"] = evidence.get("status")
        except Exception as exc:
            evidence = {"schema":"COLMENA_WORKER_EVIDENCE_V3","mission_id":m["id"],"title":m["title"],"agent_id":agent_id,"agent_runtime":runtime,"status":"BLOCKED","adapter":"AI_AGENT_RUNTIME_ERROR","command":None,"ref":a.ref,"queen_approval":m["approval"],"started_at":datetime.now(timezone.utc).isoformat(),"finished_at":datetime.now(timezone.utc).isoformat(),"source_write":False,"returncode":2,"stdout":"","stderr":str(exc)}
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
