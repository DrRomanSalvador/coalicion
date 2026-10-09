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
DEFAULT_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
DEFAULT_PROVIDER = os.getenv("HF_PROVIDER", "auto")

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)

def save_evidence(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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
        total_chars += len(text)
        if len(text) > 12000 or total_chars > 24000:
            raise ValueError("El contexto supera el límite de 24000 caracteres.")
        chunks.append(f"### Archivo: {candidate.relative_to(root)}\n{text}")
    return "\n\n".join(chunks)


def run_agent(mission: dict[str, Any], hf_token: str | None = None, model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER, backend: str = "hf", local_model: str = "qwen2.5:3b", ollama_url: str | None = None) -> dict[str, Any]:
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
    if not provider.strip():
        raise ValueError("HF_PROVIDER no puede estar vacío; usa auto o un proveedor habilitado en Hugging Face.")
    result: dict[str, Any] = {
        "schema": "COLMENA_AGENT_EVIDENCE_V1", "agent_id": agent_id, "mission_id": mission_id,
        "status": "BLOCKED", "provider": provider, "model": model, "backend": backend, "task": task, "executed_at": now()
    }
    try:
        if backend not in {"hf", "ollama"}:
            raise ValueError("backend debe ser 'hf' u 'ollama'.")
        if backend == "ollama":
            from urllib.request import Request, urlopen
            from urllib.error import URLError, HTTPError
            import socket
            base_url = (ollama_url or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
            selected_model = local_model.strip()
            if not selected_model:
                raise ValueError("local_model no puede estar vacío.")
            context = load_context(mission)
            payload = {"model": selected_model, "stream": False, "messages": [
                {"role": "system", "content": (
                    "Eres un agente analítico de COALICIÓN. No afirmes haber cambiado archivos, ejecutado comandos, "
                    "consultado fuentes o pasado pruebas si no ocurrió. Distingue hechos, hipótesis y recomendaciones. "
                    "Usa únicamente el contexto adjunto como evidencia del repositorio. Responde en español, breve, "
                    "con hallazgos concretos, rutas/funciones, riesgos y siguiente acción. Tu salida requiere revisión "
                    "humana; no puedes certificar PASS."
                )},
                {"role": "user", "content": f"Agente lógico: {agent_id}\nMisión: {mission_id}\nTítulo: {mission.get('title', mission_id)}\nTarea:\n{task}\n\nContexto real del repositorio:\n{context or '(No se adjuntaron archivos de contexto.)'}\n\nEntrega un informe auditable y no afirmes haber ejecutado pruebas."}
            ], "options": {"temperature": 0.2, "num_predict": 700}}
            request = Request(f"{base_url}/api/chat", data=json.dumps(payload).encode("utf-8"),
                              headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urlopen(request, timeout=180) as response:
                    decoded = json.loads(response.read().decode("utf-8"))
            except (HTTPError, URLError, socket.timeout, TimeoutError) as exc:
                raise RuntimeError(
                    f"Ollama local no disponible o falló ({base_url}). Comprueba que Ollama está iniciado "
                    "y que el modelo está descargado. No se ha llamado a Hugging Face ni consumido créditos de inferencia."
                ) from exc
            message = decoded.get("message", {})
            content = message.get("content") if isinstance(message, dict) else None
            result.update(provider="local-ollama", model=selected_model, backend="ollama")
        else:
            if not token:
                raise RuntimeError("Falta Reina_token; no se invocará Hugging Face.")
            from huggingface_hub import InferenceClient
            context = load_context(mission)
            fallbacks = [
                item.strip() for item in os.getenv(
                    "HF_PROVIDER_FALLBACKS", "deepinfra,featherless-ai"
                ).split(",") if item.strip()
            ]
            candidates = fallbacks if provider.strip().lower() == "auto" else [provider.strip()]
            if not candidates:
                raise RuntimeError("No hay proveedores configurados; define HF_PROVIDER o HF_PROVIDER_FALLBACKS.")
            last_provider_error: Exception | None = None
            response = None
            selected_provider = ""
            for candidate_provider in dict.fromkeys(candidates):
                result["provider"] = candidate_provider
                try:
                    client = InferenceClient(model=model, provider=candidate_provider, token=token, timeout=90)
                    response = client.chat_completion(messages=[
                        {"role": "system", "content": (
                            "Eres un agente analítico de COALICIÓN. No afirmes haber cambiado archivos, ejecutado comandos, "
                            "consultado fuentes o pasado pruebas si no ocurrió. Distingue hechos, hipótesis y recomendaciones. "
                            "Usa únicamente el contexto adjunto como evidencia del repositorio. Responde en español, breve, "
                            "con hallazgos concretos, rutas/funciones, riesgos y siguiente acción. Tu salida requiere revisión "
                            "humana; no puedes certificar PASS."
                        )},
                        {"role": "user", "content": f"Agente lógico: {agent_id}\nMisión: {mission_id}\nTítulo: {mission.get('title', mission_id)}\nTarea:\n{task}\n\nContexto real del repositorio:\n{context or '(No se adjuntaron archivos de contexto.)'}\n\nEntrega un informe auditable y no afirmes haber ejecutado pruebas."}
                    ], max_tokens=700, temperature=0.2)
                    selected_provider = candidate_provider
                    break
                except Exception as exc:
                    last_provider_error = exc
                    error_text = str(exc).lower()
                    unsupported = ("model_not_supported" in error_text
                                   or "not supported by any provider" in error_text
                                   or "provider_not_supported" in error_text)
                    if not unsupported:
                        raise
            if response is None:
                raise RuntimeError(
                    f"El modelo {model!r} no pudo usarse con los proveedores probados "
                    f"({', '.join(dict.fromkeys(candidates))}). Ninguno acepta este modelo "
                    "con la credencial Reina_token. Revisa proveedores habilitados y configura "
                    "HF_PROVIDER o HF_PROVIDER_FALLBACKS. No se marcará la misión como completada."
                ) from last_provider_error
            content = response.choices[0].message.content
            result.update(provider=selected_provider, backend="hf")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"El backend {backend} devolvió una respuesta vacía desde {result.get('provider', provider)}.")
        result.update(status="REVIEW_REQUIRED", response=content.strip())
    except Exception as exc:
        message = str(exc)
        lowered = message.lower()
        if backend == "hf" and ("402" in lowered or "payment required" in lowered or "no remaining credits" in lowered or "purchase pre-paid credits" in lowered):
            message = (
                "Hugging Face rechazó la inferencia por falta de créditos (HTTP 402). "
                "No se probarán otros proveedores para evitar llamadas innecesarias. "
                "Añade crédito/plan a la cuenta asociada a Reina_token o configura un proveedor "
                "que tenga crédito disponible; después reintenta la misión bloqueada."
            )
        elif "model_not_supported" in lowered or "not supported by any provider" in lowered:
            message = (f"El modelo {model!r} no está disponible para la credencial Reina_token "
                       f"con el proveedor {provider!r}. Usa un proveedor que figure como activo para "
                       "ese modelo en Hugging Face y esté habilitado para la cuenta.")
        result.update(status="BLOCKED", error=f"{type(exc).__name__}: {message}")
    result["completed_at"] = now()
    evidence_path = AGENTS_DIR / f"{safe_name(agent_id)}_{safe_name(mission_id)}.json"
    try:
        result["evidence_path"] = str(evidence_path.relative_to(ROOT))
    except ValueError:
        result["evidence_path"] = str(evidence_path)
    save_evidence(evidence_path, result)
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una misión analítica con Hugging Face")
    parser.add_argument("mission_json", help="JSON de misión o ruta a un archivo JSON")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="Proveedor HF habilitado (auto por defecto)")
    parser.add_argument("--backend", choices=("hf", "ollama"), default=os.getenv("COLMENA_BACKEND", "hf"))
    parser.add_argument("--local-model", default=os.getenv("COLMENA_LOCAL_MODEL", "qwen2.5:3b"))
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
    args = parser.parse_args()
    try:
        candidate = Path(args.mission_json)
        if candidate.is_file():
            raw = candidate.read_text(encoding="utf-8")
        elif re.fullmatch(r"M\d{4}", args.mission_json):
            control = json.loads(MISSION_CONTROL.read_text(encoding="utf-8"))
            matches = [item for item in control.get("missions", []) if item.get("id") == args.mission_json]
            if len(matches) != 1:
                raise ValueError(f"Misión {args.mission_json} inexistente o ambigua en Mission Control.")
            raw = json.dumps(matches[0], ensure_ascii=False)
        else:
            raw = args.mission_json
        result = run_agent(json.loads(raw), model=args.model, provider=args.provider, backend=args.backend, local_model=args.local_model, ollama_url=args.ollama_url)
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "REVIEW_REQUIRED" else 1

if __name__ == "__main__":
    raise SystemExit(main())
