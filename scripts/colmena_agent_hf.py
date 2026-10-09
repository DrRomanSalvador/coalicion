#!/usr/bin/env python3
"""Ejecutor explícito de una misión mediante Hugging Face Inference API."""
from __future__ import annotations
import argparse, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "artifacts" / "colmena" / "agents"
MISSION_CONTROL = ROOT / "docs" / "COLMENA_MISSION_CONTROL.json"
DEFAULT_MODEL = os.getenv("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

def save_evidence(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def run_agent(mission: dict[str, Any], hf_token: str | None = None, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    agent_id, mission_id = str(mission.get("agent_id", "")).strip(), str(mission.get("id", "")).strip()
    task = str(mission.get("task", "")).strip()
    if not agent_id or not mission_id or not task:
        raise ValueError("La misión debe incluir id, agent_id y task no vacío.")
    control = json.loads(MISSION_CONTROL.read_text(encoding="utf-8"))
    missions = control.get("missions", [])
    matches = [item for item in missions if item.get("id") == mission_id]
    if len(matches) != 1:
        raise ValueError(f"Misión {mission_id} inexistente o ambigua en Mission Control.")
    assigned = matches[0]
    if assigned.get("agent_id") != agent_id:
        raise ValueError("agent_id no coincide con la misión canónica.")
    if assigned.get("status") != "ASSIGNED" or assigned.get("assigned") is not True:
        raise ValueError("La Reina no ha asignado esta misión; ejecución HF bloqueada.")
    if assigned.get("task") != task:
        raise ValueError("La tarea enviada no coincide exactamente con la tarea aprobada en Mission Control.")
    token = hf_token or os.getenv("Reina_token")
    if not model.strip():
        raise ValueError("El modelo HF_MODEL no puede estar vacío.")
    result: dict[str, Any] = {
        "schema": "COLMENA_AGENT_EVIDENCE_V1", "agent_id": agent_id, "mission_id": mission_id,
        "status": "BLOCKED", "provider": "huggingface", "model": model, "task": task, "executed_at": now()
    }
    try:
        if not token:
            raise RuntimeError("Falta Reina_token; no se invocará el proveedor.")
        from huggingface_hub import InferenceClient
        client = InferenceClient(model=model, token=token, timeout=90)
        response = client.chat_completion(messages=[
            {"role": "system", "content": (
                "Eres un agente analítico de COALICIÓN. No afirmes haber cambiado archivos, ejecutado comandos, "
                "consultado fuentes o pasado pruebas si no ocurrió. Distingue hechos, hipótesis y recomendaciones. "
                "Responde en español, breve, con hallazgos, evidencia necesaria, riesgos y siguiente acción. "
                "Tu salida requiere revisión humana; no puedes certificar PASS."
            )},
            {"role": "user", "content": f"Agente lógico: {agent_id}\nMisión: {mission_id}\nTítulo: {mission.get('title', mission_id)}\nTarea:\n{task}\n\nEntrega un informe auditable y no inventes acceso al repositorio."}
        ], max_tokens=500, temperature=0.2)
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("HF devolvió una respuesta vacía.")
        result.update(status="REVIEW_REQUIRED", response=content.strip())
    except Exception as exc:
        result.update(status="BLOCKED", error=f"{type(exc).__name__}: {exc}")
    result["completed_at"] = now()
    evidence_path = AGENTS_DIR / f"{safe_name(agent_id)}_{safe_name(mission_id)}.json"
    save_evidence(evidence_path, result)
    result["evidence_path"] = str(evidence_path.relative_to(ROOT))
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una misión analítica con Hugging Face")
    parser.add_argument("mission_json", help="JSON de misión o ruta a un archivo JSON")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    try:
        candidate = Path(args.mission_json)
        raw = candidate.read_text(encoding="utf-8") if candidate.is_file() else args.mission_json
        result = run_agent(json.loads(raw), model=args.model)
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "REVIEW_REQUIRED" else 1

if __name__ == "__main__":
    raise SystemExit(main())
