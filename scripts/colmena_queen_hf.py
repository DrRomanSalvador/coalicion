#!/usr/bin/env python3
"""Controlador ligero de misiones lógicas COALICIÓN; no crea procesos por sí solo."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MISSION_CONTROL = ROOT / "docs" / "COLMENA_MISSION_CONTROL.json"
AGENTS_DIR = ROOT / "artifacts" / "colmena" / "agents"
TOTAL_AGENTS = 179
STATUSES = {"PENDING", "ASSIGNED", "REVIEW_REQUIRED", "PASS", "BLOCKED"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def get_missions() -> list[dict[str, Any]]:
    data = load_json(MISSION_CONTROL, {})
    missions = data.get("missions", [])
    if not missions:
        missions = [
            {
                "id": f"M{i:04d}",
                "agent_id": f"agent-{i:03d}",
                "title": f"Agente lógico {i:03d}",
                "task": "",
                "status": "PENDING",
                "assigned": False,
                "note": "Definir una tarea concreta y verificable antes de ejecutar."
            }
            for i in range(1, TOTAL_AGENTS + 1)
        ]
        save_json(MISSION_CONTROL, {
            "schema": "COLMENA_MISSION_CONTROL_V1",
            "total": TOTAL_AGENTS,
            "mode": "LOGICAL_SLOTS",
            "note": "Los slots no son procesos autónomos. Una tarea requiere definición, HF_TOKEN y ejecución explícita.",
            "missions": missions,
        })
    validate_missions(missions)
    return missions


def validate_missions(missions: list[dict[str, Any]]) -> None:
    if len(missions) != TOTAL_AGENTS:
        raise ValueError(f"Se esperaban {TOTAL_AGENTS} misiones; hay {len(missions)}.")
    ids = [m.get("id") for m in missions]
    agents = [m.get("agent_id") for m in missions]
    if len(set(ids)) != TOTAL_AGENTS or len(set(agents)) != TOTAL_AGENTS:
        raise ValueError("IDs de misión/agente duplicados.")
    for mission in missions:
        if mission.get("status") not in STATUSES:
            raise ValueError(f"Estado no válido en {mission.get('id')}: {mission.get('status')}")


def status_report() -> dict[str, Any]:
    missions = get_missions()
    counts = {status: sum(m["status"] == status for m in missions) for status in sorted(STATUSES)}
    report = {"total": len(missions), **{k.lower(): v for k, v in counts.items()}}
    print("COLMENA REINA — CONTROL DE MISIONES")
    print(f"Slots lógicos: {report['total']}")
    for key in sorted(counts):
        print(f"{key:17}: {counts[key]}")
    print(f"Sin tarea definida: {sum(not str(m.get('task', '')).strip() for m in missions)}")
    print("Nota: slot lógico ≠ agente ejecutado; PASS requiere verificación independiente.")
    return {**report, "missions": missions}


def assign_next_batch(batch_size: int = 5) -> list[dict[str, Any]]:
    if not 1 <= batch_size <= 5:
        raise ValueError("El lote debe estar entre 1 y 5.")
    missions = get_missions()
    eligible = [
        m for m in missions
        if m["status"] == "PENDING" and not m.get("assigned")
        and isinstance(m.get("task"), str) and m["task"].strip()
    ]
    batch = eligible[:batch_size]
    timestamp = now()
    for mission in batch:
        mission["assigned"] = True
        mission["status"] = "ASSIGNED"
        mission["assigned_at"] = timestamp
    data = load_json(MISSION_CONTROL, {})
    data["missions"] = missions
    data["updated_at"] = timestamp
    save_json(MISSION_CONTROL, data)
    print(f"Asignadas {len(batch)} misiones ejecutables (máximo 5 por lote).")
    for mission in batch:
        print(f"{mission['id']} -> {mission['agent_id']}")
    if not batch:
        print("No hay misiones ejecutables: define task en docs/COLMENA_MISSION_CONTROL.json.")
    return batch



def record_result(result_path: Path) -> dict[str, Any]:
    """Registra una evidencia HF sin permitir que el modelo certifique PASS."""
    result = load_json(result_path)
    if not isinstance(result, dict):
        raise ValueError("La evidencia debe ser un objeto JSON.")
    mission_id = str(result.get("mission_id", "")).strip()
    agent_id = str(result.get("agent_id", "")).strip()
    status = result.get("status")
    if not mission_id or not agent_id:
        raise ValueError("La evidencia debe incluir mission_id y agent_id.")
    if status not in {"REVIEW_REQUIRED", "BLOCKED"}:
        raise ValueError("Solo se aceptan resultados REVIEW_REQUIRED o BLOCKED; PASS requiere verificación independiente.")
    missions = get_missions()
    matches = [m for m in missions if m["id"] == mission_id]
    if len(matches) != 1:
        raise ValueError(f"Misión desconocida o ambigua: {mission_id}.")
    mission = matches[0]
    if mission["agent_id"] != agent_id:
        raise ValueError("agent_id de la evidencia no coincide con la misión.")
    if mission["status"] != "ASSIGNED" or not mission.get("assigned"):
        raise ValueError(f"La misión {mission_id} no está asignada; se rechaza evidencia obsoleta o no solicitada.")
    timestamp = now()
    mission["status"] = status
    mission["result_recorded_at"] = timestamp
    mission["evidence_path"] = str(result_path)
    mission["result_summary"] = (
        str(result.get("error", ""))[:500] if status == "BLOCKED"
        else "Informe recibido; requiere revisión independiente."
    )
    data = load_json(MISSION_CONTROL, {})
    data["missions"] = missions
    data["updated_at"] = timestamp
    save_json(MISSION_CONTROL, data)
    print(f"Resultado registrado: {mission_id} -> {status} (sin certificación automática).")
    return {"mission_id": mission_id, "agent_id": agent_id, "status": status, "recorded_at": timestamp}



def main() -> int:
    parser = argparse.ArgumentParser(description="Controlador de 179 slots lógicos COALICIÓN")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true")
    group.add_argument("--assign", type=int, metavar="N")
    group.add_argument("--record-result", type=Path, metavar="EVIDENCE_JSON", help="Registrar evidencia JSON de una misión asignada")
    args = parser.parse_args()
    try:
        if args.assign is not None:
            assign_next_batch(args.assign)
        elif args.record_result is not None:
            record_result(args.record_result)
        else:
            status_report()
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
