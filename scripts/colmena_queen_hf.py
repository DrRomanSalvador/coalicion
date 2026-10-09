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


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlador de 179 slots lógicos COALICIÓN")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true")
    group.add_argument("--assign", type=int, metavar="N")
    args = parser.parse_args()
    try:
        if args.assign is not None:
            assign_next_batch(args.assign)
        else:
            status_report()
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
