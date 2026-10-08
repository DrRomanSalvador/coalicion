#!/usr/bin/env python3
"""Atomic worker for one Queen-approved mission.

Workers are deliberately conservative: they can execute registered checks, but
they cannot claim completion for a mission whose semantics are not implemented.
This prevents a matrix of CI jobs from becoming fake certification.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GATE=ROOT/"artifacts"/"colmena"/"queen_gate.json"
OUT=ROOT/"artifacts"/"colmena"/"workers"
OUT.mkdir(parents=True,exist_ok=True)

def now(): return datetime.now(timezone.utc).isoformat()

def run(argv,timeout=900):
    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
    return {"returncode":p.returncode,"stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:]}

def handler(title:str):
    t=title.lower()
    if "py_compile" in t or t=="imports":
        return ["python","-m","compileall","-q","src","scripts"], "EXECUTED"
    if "test fail-closed" in t or "fail-closed" in t:
        return ["python","-m","pytest","-q","tests/test_error_registry.py"], "EXECUTED"
    if "regresión motor electoral" in t:
        return ["python","-m","pytest","-q","tests/test_electoral.py"], "EXECUTED"
    if "regresión motor de coaliciones" in t:
        return ["python","-m","pytest","-q","tests/test_decision.py"], "EXECUTED"
    if "regresión incertidumbre" in t:
        return ["python","-m","pytest","-q","tests/test_uncertainty.py"], "EXECUTED"
    if "regresión telegram" in t:
        return ["python","-m","pytest","-q","tests/test_telegram.py"], "EXECUTED"
    if "regresión bot" in t or "regresión monitor" in t:
        return ["python","-m","pytest","-q","tests"], "EXECUTED"
    if "batería completa" in t or "tests unitarios" in t or "tests integración" in t:
        return ["python","-m","pytest","-q"], "EXECUTED"
    return None, "UNIMPLEMENTED"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mission-id",required=True)
    ap.add_argument("--gate",default=str(GATE))
    args=ap.parse_args()
    try:
        gate=json.loads(Path(args.gate).read_text(encoding="utf-8"))
        if gate.get("status")!="APPROVED_FOR_WORKERS" or not gate.get("fail_closed"):
            raise RuntimeError("invalid Queen Gate")
        if gate.get("repository")!="DrRomanSalvador/coalicion":
            raise RuntimeError("wrong repository")
        mission=next((m for m in gate["missions"] if m["id"]==args.mission_id),None)
        if mission is None:
            raise RuntimeError("mission not approved by Queen")
        expected=gate["commit"]
        actual=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        if actual!=expected:
            raise RuntimeError(f"checkout mismatch: expected {expected}, got {actual}")
        argv,status=handler(mission["title"])
        result={
            "schema":"COLMENA_WORKER_RESULT_V1","mission":mission,
            "started_at":now(),"commit":actual,
            "write_authorized": mission.get("write_authorized",False),
            "status":status,"fail_closed":True,
        }
        if argv:
            result["command"]=argv
            try:
                execution=run(argv)
                result["execution"]=execution
                result["status"]="PASS" if execution["returncode"]==0 else "FAIL_CLOSED"
            except Exception as exc:
                result["status"]="FAIL_CLOSED"
                result["error"]=f"{type(exc).__name__}: {exc}"
        else:
            result["status"]="BLOCKED_UNIMPLEMENTED_HANDLER"
            result["blocking_reason"]="No deterministic handler is registered for this mission yet."
        result["finished_at"]=now()
        out=OUT/f"{mission['id']}.json"
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"mission_id":mission["id"],"status":result["status"]},ensure_ascii=False))
        return 0 if result["status"]=="PASS" else 1
    except Exception as exc:
        print(f"FAIL_CLOSED: WORKER: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
