#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/"artifacts"; PLAN=ART/"repair_plan.json"; STATE=ART/"repair_state.json"; OUT=ART/"COMPLETE_REPORT.md"
def main():
    if not PLAN.is_file(): raise SystemExit("FAIL_CLOSED: repair_plan.json missing")
    faults=json.loads(PLAN.read_text(encoding="utf-8")).get("faults",[])
    if len(faults)!=466: raise SystemExit(f"FAIL_CLOSED: expected 466 faults, found {len(faults)}")
    counts={s:sum(f.get("status")==s for f in faults) for s in ("pending","in_progress","completed","failed")}
    state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {}
    lines=["# COALICIÓN — Reparación de 466 fallos","","- Total: 466",f"- Completados: {counts['completed']}",f"- Fallidos: {counts['failed']}",f"- Pendientes: {counts['pending']}",f"- En curso: {counts['in_progress']}",f"- Estado: {state.get('status','unknown')}",f"- Generado: {datetime.now(timezone.utc).isoformat()}"]
    OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(OUT)
if __name__=="__main__": main()
