#!/usr/bin/env python3
"""Executable Queen Gate for COALMENA.

The Queen validates the mission registry before workers start. Workers receive
an immutable gate artifact containing the exact mission text, commit SHA and
write authority. No mission is granted code-write authority by default.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from colmena_missions import ROOT, CONTROL, registry, matrix

OUT=ROOT/"artifacts"/"colmena"
OUT.mkdir(parents=True, exist_ok=True)

def sha256(path: Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def now()->str:
    return datetime.now(timezone.utc).isoformat()

def git(*args:str)->str:
    p=subprocess.run(["git",*args],cwd=ROOT,text=True,capture_output=True,check=True)
    return p.stdout.strip()

def main()->int:
    try:
        missions=registry()
        commit=git("rev-parse","HEAD")
        control_sha=sha256(CONTROL)
        gate={
            "schema":"COLMENA_QUEEN_GATE_V1",
            "status":"APPROVED_FOR_WORKERS",
            "repository":"DrRomanSalvador/coalicion",
            "commit":commit,
            "mission_control_sha256":control_sha,
            "generated_at":now(),
            "worker_write_gate":"DENY_BY_DEFAULT",
            "write_authorized_missions":[],
            "mission_count":len(missions),
            "missions":missions,
            "fail_closed":True,
            "rules":[
                "exact mission text comes only from mission control",
                "worker cannot write code without explicit authorization in this gate",
                "unknown handler is BLOCKED, never PASS",
                "duplicate mission ids are fatal",
                "wrong repository is fatal",
            ],
        }
        (OUT/"queen_gate.json").write_text(json.dumps(gate,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (OUT/"worker_matrix.json").write_text(json.dumps(matrix(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({
            "status":gate["status"],"mission_count":len(missions),
            "commit":commit,"gate":str((OUT/"queen_gate.json").relative_to(ROOT))
        },ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"FAIL_CLOSED: QUEEN_GATE: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
