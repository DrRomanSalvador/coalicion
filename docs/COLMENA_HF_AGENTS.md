# Colmena Hugging Face — uso controlado

Los 179 elementos son **slots lógicos**, no 179 procesos ni agentes ya ejecutados. La Reina no lanza trabajos de forma implícita. El modo formal es `QUEEN_COORDINATION_MODE + 179_AGENTS_HF`; queda en `READY_FOR_USER_APPROVAL` hasta que el usuario apruebe un lote. La credencial se llama exactamente `Reina_token`.

## Requisitos
- Python 3.12.
- Para invocar HF: instalar `huggingface_hub` y configurar `Reina_token` como variable local o secreto de Actions.
- Modelo configurable mediante `HF_MODEL` o `--model`; el proveedor puede no ofrecer el modelo en todos los planes/regiones.

## Local
```bash
python scripts/colmena_queen_hf.py --status
python scripts/colmena_queen_hf.py --assign 5
# Tras ejecutar un agente para una misión ya asignada y guardar su evidencia JSON:
python scripts/colmena_queen_hf.py --record-result artifacts/colmena/agents/agent-001_M0001.json
python scripts/colmena_agent_hf.py M0001
```

El comando por ID carga la misión canónica desde Mission Control y solo ejecuta si la Reina ya la asignó y la tarea coincide. No ejecutar hasta aprobación explícita. La asignación solo selecciona misiones con `task` no vacía. Las misiones iniciales se crean pendientes y sin tarea: no se inventa trabajo ni se marca como realizado. Lote máximo: 5. La reconciliación exige que la misión esté en `ASSIGNED`, que coincidan `mission_id` y `agent_id`, y solo acepta `REVIEW_REQUIRED` o `BLOCKED`; nunca acepta `PASS` del modelo.

## Persistencia duradera en GitHub
La Reina reconcilia cada evidencia mediante `--record-result` y guarda en `docs/COLMENA_MISSION_CONTROL.json` el estado, la ruta y el SHA-256 del JSON. También actualiza `docs/COLMENA_STATE.json` con misión, agente, proveedor, hash, timestamp y metadatos del run; nunca guarda el secreto. Estos cambios solo cuentan como persistidos cuando el commit aparece en la rama invocada. Si el push falla, la ejecución debe considerarse no persistida y el artefacto de Actions es solo recuperación temporal.

## Asignación persistente (sin ejecución)
Workflow manual **COALICIÓN — Asignación persistente de misiones HF**. Solo tras aprobación explícita del usuario, permite a la Reina asignar de 1 a 5 misiones que ya tengan tarea concreta y guarda Mission Control en la rama invocada. No llama a Hugging Face.

## GitHub Actions
Workflow manual **COALICIÓN — Agentes lógicos Hugging Face**. Introducir el ID de una misión ya asignada (por ejemplo `M0001`) y disponer del secreto cuyo nombre exacto es `Reina_token`. El workflow valida contra Mission Control, ejecuta un único agente, reconcilia el resultado y trata de persistir evidencia, Mission Control y estado en la rama invocada. Publica además una copia como artefacto de 90 días. No ejecutarlo en `main` con misiones asignadas si no se desea que el commit de evidencia llegue a `main`.

## Estados y límites
- `PENDING`: misión aún no asignada.
- `ASSIGNED`: seleccionada por el controlador.
- `REVIEW_REQUIRED`: HF produjo un informe que requiere revisión independiente.
- `BLOCKED`: faltan credenciales, hay error del proveedor o no se pudo ejecutar.
- `PASS`: reservado para una verificación externa determinista; el modelo nunca puede asignarlo.

La respuesta de un modelo no demuestra que se hayan leído archivos, ejecutado pruebas o modificado el repositorio. No compartir secretos en la misión. El token solo se pasa por variable de entorno y nunca se escribe en la evidencia.
