#!/usr/bin/env python3
"""Ejecutor local Ollama de una misión COALICIÓN; no requiere API ni créditos externos."""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MISSION_CONTROL = ROOT / "docs" / "COLMENA_MISSION_CONTROL.json"
AGENTS_DIR = ROOT / "artifacts" / "colmena" / "agents"
DEFAULT_MODEL = os.getenv("COLMENA_LOCAL_MODEL", "qwen2.5:3b")
DEFAULT_URL = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def load_context(mission: dict[str, Any]) -> str:
    paths = mission.get("context_paths", [])
    if not isinstance(paths, list) or len(paths) > 4:
        raise ValueError("context_paths debe ser una lista de hasta 4 rutas.")
    chunks: list[str] = []
    total_chars = 0
    root = ROOT.resolve()
    for raw_path in paths:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("Cada context_path debe ser una ruta relativa no vacía.")
        candidate = (root / raw_path).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError(f"Ruta de contexto no permitida o inexistente: {raw_path}")
        text = candidate.read_text(encoding="utf-8")
        if len(text) > 12000:
            raise ValueError("Un archivo de contexto supera 12000 caracteres.")
        total_chars += len(text)
        if total_chars > 24000:
            raise ValueError("El contexto supera el límite de 24000 caracteres.")
        chunks.append(f"### Archivo: {candidate.relative_to(root)}\n{text}")
    return "\n\n".join(chunks)


def save_evidence(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_mandatory_contract() -> str:
    """Carga las normas canónicas; la inferencia no arranca si faltan."""
    required = (
        "AGENTS.md",
        "CONTRATO_MAESTRO_IA.md",
        "README.md",
        "docs/ENGINEERING_CHARTER.md",
        "docs/ENGINEERING_ENFORCEMENT_MATRIX.md",
        "docs/COLMENA_STATE.json",
    )
    root = ROOT.resolve()
    chunks: list[str] = []
    total_chars = 0
    for relative in required:
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Fail-closed: falta el contrato obligatorio {relative}.")
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"Fail-closed: contrato obligatorio vacío: {relative}.")
        # Se lee el README completo; se envían el inicio y el índice para no consumir
        # el contexto disponible con secciones ajenas a la misión.
        if relative == "README.md":
            headings = "\n".join(line for line in text.splitlines() if line.startswith("#"))[:5000]
            text = text[:6000] + "\n\n[ÍNDICE DE SECCIONES DEL README]\n" + headings
        total_chars += len(text)
        chunks.append(f"### Norma canónica: {relative}\n{text}")
    matrix = (root / "docs/ENGINEERING_ENFORCEMENT_MATRIX.md").read_text(encoding="utf-8")
    covered = set(re.findall(r"^\|\s*(\d{2})\s*\|", matrix, flags=re.MULTILINE))
    expected = {f"{number:02d}" for number in range(1, 26)}
    if covered != expected:
        missing = sorted(expected - covered)
        raise ValueError(f"Fail-closed: la matriz no cubre los 25 principios; faltan {missing}.")
    if total_chars > 45000:
        raise ValueError("Fail-closed: los contratos obligatorios exceden el límite de contexto.")
    return "\n\n".join(chunks)


def run_agent(mission_id: str, model: str = DEFAULT_MODEL, ollama_url: str = DEFAULT_URL) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "COLMENA_AGENT_EVIDENCE_V1",
        "status": "BLOCKED",
        "provider": "local-ollama",
        "model": model,
        "backend": "ollama",
        "mission_id": mission_id,
        "executed_at": now(),
    }
    try:
        if not re.fullmatch(r"M\d{4}", mission_id):
            raise ValueError("mission_id inválido; formato esperado M0001.")
        control = json.loads(MISSION_CONTROL.read_text(encoding="utf-8"))
        missions = control.get("missions", [])
        matches = [m for m in missions if m.get("id") == mission_id]
        if len(matches) != 1:
            raise ValueError("Misión inexistente o ambigua en Mission Control.")
        mission = matches[0]
        result.update(agent_id=mission.get("agent_id"), task=mission.get("task", ""))
        if mission.get("status") != "ASSIGNED" or mission.get("assigned") is not True:
            raise ValueError("Fail-closed: la Reina no ha asignado esta misión.")
        if not isinstance(mission.get("task"), str) or not mission["task"].strip():
            raise ValueError("Fail-closed: la misión no tiene tarea concreta.")
        if not model.strip():
            raise ValueError("El modelo Ollama no puede estar vacío.")
        context = load_context(mission)
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": (
                    "Eres un agente de ingeniería de COALICIÓN. Debes obedecer las normas canónicas "
                    "incluidas a continuación y los 25 principios con su matriz de control. Si hay "
                    "contradicción, falta un contrato o no puedes verificar algo, DETENTE, explica el "
                    "bloqueo y no inventes. Aplica la regla boy scout: deja cada área mejor de como la "
                    "encontraste; corrige la causa raíz con el cambio mínimo, reutiliza lo válido, elimina "
                    "solo lo obsoleto o sin uso tras revisar referencias, y no introduzcas duplicación. "
                    "No afirmes haber editado archivos, ejecutado pruebas o consultado fuentes si no ocurrió. "
                    "Distingue hechos, hipótesis y recomendaciones. Usa evidencia del repositorio, identifica "
                    "rutas/funciones, añade regresión para cada bug cuando sea viable, preserva trazabilidad, "
                    "seguridad, determinismo y rollback. Nunca declares PASS: la salida requiere revisión "
                    "independiente.\n\nNORMAS CANÓNICAS OBLIGATORIAS:\n"
                    + load_mandatory_contract()
                )},
                {"role": "user", "content": (
                    f"Agente: {mission.get('agent_id')}\nMisión: {mission_id}\n"
                    f"Título: {mission.get('title', mission_id)}\nTarea:\n{mission['task']}\n\n"
                    f"Contexto real del repositorio:\n{context or '(Sin archivos de contexto.)'}\n\n"
                    "Entrega un informe auditable: causa raíz, cambio mínimo, principios 01–25 aplicables, "
                    "pruebas concretas y resultado solo si se ejecutó, riesgos y rollback. "
                    "No inventes ejecuciones ni resultados."
                )},
            ],
            "options": {"temperature": 0.2, "num_predict": 700, "num_ctx": 24576},
        }
        request = Request(
            f"{ollama_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=180) as response:
            decoded = json.loads(response.read().decode("utf-8"))
        message = decoded.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama devolvió una respuesta vacía.")
        result.update(status="REVIEW_REQUIRED", response=content.strip())
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["completed_at"] = now()
    evidence_path = AGENTS_DIR / f"{safe_name(str(result.get('agent_id', 'unknown')))}_{safe_name(mission_id)}.json"
    try:
        result["evidence_path"] = str(evidence_path.relative_to(ROOT))
    except ValueError:
        result["evidence_path"] = str(evidence_path)
    save_evidence(evidence_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una misión aprobada con Ollama local")
    parser.add_argument("mission_id")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_URL)
    args = parser.parse_args()
    result = run_agent(args.mission_id, model=args.model, ollama_url=args.ollama_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "REVIEW_REQUIRED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
