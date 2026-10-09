# COLMENA — RUNTIME LIGERO

Colmena ya no ejecuta 179 agentes ni Transformers.js/Qwen dentro de GitHub Actions.

## Único runtime activo
`.github/workflows/colmena_atomic_swarm.yml` — **COALICIÓN — Colmena ligera**.

Valida estado persistente, continuidad, contrato reproducible, regresiones del motor
de coaliciones y demo E2E. Límite del job: 12 minutos.

## Evidencia persistente
`docs/COLMENA_STATE.json:last_colmena_checkpoint` registra PASS únicamente después
de completar todos los checks, junto con commit, run ID, intento y timestamp UTC.

## Fail-closed
Estado ausente/inválido, gate incompatible, contrato fallido o tests fallidos
impiden registrar un checkpoint PASS. El checkpoint no constituye certificación externa.

## Ejecución
Activar desde GitHub Actions → **COALICIÓN — Colmena ligera** → Run workflow.
