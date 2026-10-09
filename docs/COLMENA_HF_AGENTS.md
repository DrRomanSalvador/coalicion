# Colmena Hugging Face — uso controlado

Los 179 elementos son **slots lógicos**, no 179 procesos ni agentes ya ejecutados. La Reina no lanza trabajos de forma implícita.

## Requisitos
- Python 3.12.
- Para invocar HF: instalar `huggingface_hub` y configurar `HF_TOKEN` como variable local o secreto de Actions.
- Modelo configurable mediante `HF_MODEL` o `--model`; el proveedor puede no ofrecer el modelo en todos los planes/regiones.

## Local
```bash
python scripts/colmena_queen_hf.py --status
python scripts/colmena_queen_hf.py --assign 5
# Tras ejecutar un agente para una misión ya asignada y guardar su evidencia JSON:
python scripts/colmena_queen_hf.py --record-result artifacts/colmena/agents/agent-001_M0001.json
python scripts/colmena_agent_hf.py '{"id":"M0001","agent_id":"agent-001","title":"Revisión de ejemplo","task":"Analiza este problema concreto: ..."}'
```

La asignación solo selecciona misiones con `task` no vacía. Las misiones iniciales se crean pendientes y sin tarea: no se inventa trabajo ni se marca como realizado. Lote máximo: 5. La reconciliación exige que la misión esté en `ASSIGNED`, que coincidan `mission_id` y `agent_id`, y solo acepta `REVIEW_REQUIRED` o `BLOCKED`; nunca acepta `PASS` del modelo.

## GitHub Actions
Workflow manual **COALICIÓN — Agentes lógicos Hugging Face**. Introducir una misión JSON concreta y disponer del secreto `HF_TOKEN`. El workflow ejecuta un solo agente por invocación y publica la evidencia como artefacto temporal; no hace commit ni push automático.

## Estados y límites
- `PENDING`: misión aún no asignada.
- `ASSIGNED`: seleccionada por el controlador.
- `REVIEW_REQUIRED`: HF produjo un informe que requiere revisión independiente.
- `BLOCKED`: faltan credenciales, hay error del proveedor o no se pudo ejecutar.
- `PASS`: reservado para una verificación externa determinista; el modelo nunca puede asignarlo.

La respuesta de un modelo no demuestra que se hayan leído archivos, ejecutado pruebas o modificado el repositorio. No compartir secretos en la misión. El token solo se pasa por variable de entorno y nunca se escribe en la evidencia.
