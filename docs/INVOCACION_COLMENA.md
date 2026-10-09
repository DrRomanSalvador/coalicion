# COLMENA — INVOCACIÓN LIGERA

Repositorio único: `DrRomanSalvador/coalicion`, rama `main`.
Fuente de verdad: GitHub. Fail-closed: un fallo bloquea el checkpoint.

## Activación y validación base
En GitHub: Actions → **COALICIÓN — Colmena ligera** → Run workflow.
También se ejecuta con cambios en el estado, contratos, motor de coaliciones y demo E2E.

Valida:
1. `docs/COLMENA_STATE.json` y su gate fail-closed.
2. Continuidad: `python -m src.colmena_resume`.
3. Contrato reproducible: `python -m src.reproducibility_contract`.
4. Tests de contrato, registro de errores, producto, motor de coaliciones y auditoría.
5. Demo E2E real: `python scripts/demo_e2e.py`.

## Reina Hugging Face opcional

Modo formal: `QUEEN_COORDINATION_MODE + 179_AGENTS_HF`. La credencial exacta es `Reina_token`. La asignación y ejecución de misiones requiere aprobación explícita del usuario; el estado actual tiene 179 misiones sin tarea, por lo que no se asigna ninguna.
La integración complementaria está documentada en `docs/COLMENA_HF_AGENTS.md`.
- `python scripts/colmena_queen_hf.py --status`: inspeccionar 179 slots lógicos.
- `python scripts/colmena_queen_hf.py --assign 5`: asignar hasta cinco misiones con tarea concreta.
- GitHub Actions → **COALICIÓN — Agentes lógicos Hugging Face**: ejecución manual de una misión mediante HF.
- El workflow exige un mission_id ya asignado, usa exactamente el secreto Reina_token, reconcilia el JSON con la Reina y persiste docs/COLMENA_MISSION_CONTROL.json, docs/COLMENA_STATE.json y artifacts/colmena/agents/ mediante commit en la rama invocada; además sube un artefacto recuperable de 90 días. Un artefacto de Actions por sí solo no equivale a persistencia en Git.
- Requiere secreto `Reina_token`; no se invoca HF ni se consumen créditos en la validación base.
- Los 179 slots no son 179 procesos concurrentes. Cada ejecución invoca un agente explícitamente.
- La respuesta del modelo queda en `REVIEW_REQUIRED`; no puede certificar PASS ni afirmar que ejecutó pruebas/cambió código sin evidencia.

## Persistencia y límites
El workflow base registra `last_colmena_checkpoint` en `docs/COLMENA_STATE.json` solo tras superar todas las comprobaciones. Incluye commit probado, run ID, intento, lista de checks y timestamp UTC.
- No se declara PASS si falla una comprobación.
- El checkpoint valida únicamente los checks enumerados; no es certificación externa.
- La demo E2E y el motor de coaliciones conservan sus propios tests.
