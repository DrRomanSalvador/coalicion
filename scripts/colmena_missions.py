#!/usr/bin/env python3
"""Mission registry and deterministic scheduling primitives for COALMENA.

This module never invents missions. The repository mission-control JSON is the
only source of mission text. Each mission gets a stable ID derived from its
ordinal and exact text. Unknown execution semantics remain BLOCKED.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "docs" / "COLMENA_MISSION_CONTROL.json"

def load_control() -> dict[str, Any]:
    data = json.loads(CONTROL.read_text(encoding="utf-8"))
    if data.get("repository") != "DrRomanSalvador/coalicion":
        raise RuntimeError("FAIL_CLOSED: wrong repository")
    if data.get("fail_closed") is not True:
        raise RuntimeError("FAIL_CLOSED: mission control is not fail-closed")
    missions = data.get("missions")
    if not isinstance(missions, list) or not missions:
        raise RuntimeError("FAIL_CLOSED: empty mission registry")
    return data

def mission_id(index: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"M{index:04d}-{digest}"

def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value[:48] or "mission"

def phase(text: str) -> str:
    t=text.lower()
    if any(k in t for k in ("release", "certificación honesta", "preparar certificación")):
        return "final"
    if any(k in t for k in ("ci ", "evidencia ci", "workflow", "checkpoint", "certificación probabilística")):
        return "ci"
    if any(k in t for k in ("backtest", "oos", "seec", "muestreo", "calibración", "drift", "house effects", "multinomial")):
        return "probabilistic"
    if any(k in t for k in ("test", "regresión", "py_compile", "imports", "healthcheck", "seguridad", "reproducibilidad")):
        return "verification"
    if any(k in t for k in ("data.py", "prediction.py", "coalition.py", "uncertainty.py", "decision.py", "electoral.py", "conexión", "contratos", "invariantes")):
        return "architecture"
    return "provenance"

def registry() -> list[dict[str, Any]]:
    raw=load_control()["missions"]
    out=[]
    seen=set()
    for i,text in enumerate(raw,1):
        if not isinstance(text,str) or not text.strip():
            raise RuntimeError(f"FAIL_CLOSED: invalid mission at {i}")
        mid=mission_id(i,text.strip())
        if mid in seen:
            raise RuntimeError("FAIL_CLOSED: duplicate mission id")
        seen.add(mid)
        out.append({
            "id": mid, "ordinal": i, "title": text.strip(),
            "slug": slug(text), "phase": phase(text),
            "write_authorized": False,
            "handler": "contract"
        })
    return out

def matrix() -> dict[str, Any]:
    missions=registry()
    return {"include":[{"mission_id":m["id"],"ordinal":m["ordinal"],
                         "phase":m["phase"],"title":m["title"]} for m in missions]}

if __name__ == "__main__":
    print(json.dumps(matrix(), ensure_ascii=False, separators=(",",":")))
