# COLMENA — INVOCACIÓN LIGERA

Repositorio único: `DrRomanSalvador/coalicion`, rama `main`.
Fuente de verdad: GitHub. Fail-closed: un fallo bloquea el checkpoint.

## Activación
En GitHub: Actions → **COALICIÓN — Colmena ligera** → Run workflow.
También se ejecuta con cambios en el estado, contratos, motor de coaliciones y demo E2E.

## Qué valida
1. `docs/COLMENA_STATE.json` y su gate fail-closed.
2. Continuidad: `python -m src.colmena_resume`.
3. Contrato reproducible: `python -m src.reproducibility_contract`.
4. Tests de contrato, registro de errores, producto, motor de coaliciones y auditoría.
5. Demo E2E real: `python scripts/demo_e2e.py`.

## Persistencia
El workflow registra `last_colmena_checkpoint` en `docs/COLMENA_STATE.json`
solo tras superar todas las comprobaciones. Incluye commit probado, run ID,
intento, lista de checks y timestamp UTC.

## Límites
- No hay 179 agentes, pool de IA local ni descargas de modelos en Actions.
- No se declara PASS si falla una comprobación.
- El checkpoint valida únicamente los checks enumerados; no es certificación externa.
- La demo E2E y el motor de coaliciones conservan sus propios tests.
