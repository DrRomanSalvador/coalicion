# COALICIÓN — AUDITORÍA MAESTRA EXTERNA

## Dictamen técnico
**READY_FOR_INDEPENDENT_SIGNOFF**

Este paquete reúne en un punto único la evidencia esencial para un auditor. No declara por sí mismo independencia de terceros ni certificación legal.

## Evidencia esencial

| Área | Evidencia | Estado |
|---|---|---|
| Procedencia/reconciliación | `ci_evidence/historico_manifest.json`, `ci_evidence/reconciliation.json` | PASS |
| Motor electoral | `src/electoral.py` + tests | PASS |
| Ley electoral | 52 circunscripciones / 350 escaños / 3% / D'Hondt / Ceuta-Melilla | PASS |
| OOS/leakage | `ci_evidence/oos_calibration.json` | PASS |
| MC | `ci_evidence/mc_10000.json` | PASS |
| SEEC | `ci_evidence/seec_production.json` | PASS |
| Backtest territorial | `ci_evidence/backtest_2023_baseline.json` | PASS |
| Backtest histórico | `ci_evidence/backtest_complete_2004_2023.json` | PASS |
| Encuestas | `ci_evidence/poll_source_coverage.json` | PASS |
| Tests contractuales | 288/288 | PASS |
| Cierre interno | `ci_evidence/master_certification.json` | READY_FOR_EXTERNAL_AUDIT |
| Independencia | Revisión por tercero | OPEN |

## Cifras que el auditor debe ver primero

- **OOS:** 96,30% de cobertura agregada; leakage checks PASS.
- **MC:** 10.000 simulaciones; 52 circunscripciones; 350 escaños; suma de escaños = 350 en todos los draws.
- **SEEC:** 10.000 draws PyMC/NUTS; 4 cadenas; 2.500 draws/cadena; 3.000 tune/cadena; 0 divergencias; R-hat máximo 1,0.
- **Backtest territorial 2023:** 10.000 simulaciones; cobertura calibrada 100% de las familias ganadoras observadas; conformal 95% calibrado exclusivamente con información pre-2023.
- **Tests:** 288/288 PASS.
- **Fuentes:** 7/7 fuentes primarias configuradas operativas en la evidencia actual.

## Protocolo del auditor externo

1. No aceptar `master_certification.json` como prueba suficiente.
2. Ejecutar `python scripts/external_audit.py`.
3. Ejecutar `pytest -q`.
4. Verificar hashes y commits de los artefactos.
5. Revisar las entradas y el código de los gates.
6. Confirmar ausencia de leakage y exclusión de la elección objetivo de la calibración.
7. Confirmar que cada PASS depende de evidencia subyacente, no de otro PASS.
8. Registrar identidad del auditor, fecha, commit y conclusión.
9. Si no existe independencia real, dictaminar `NOT_INDEPENDENT`, no PASS.

## Limitaciones declaradas

- SEEC es un posterior composicional de encuestas; no es por sí solo un posterior electoral territorial de escaños.
- El backtest territorial demostrado es 2023, con baseline 2019 y calibración histórica pre-2023.
- Discovery no equivale a evidencia primaria.
- `READY_FOR_EXTERNAL_AUDIT` no equivale a `CERTIFIED`.
- La independencia debe proceder de un tercero distinto del equipo que construyó/verificó el sistema.

## Dictamen correcto

**INTERNAL EVIDENCE: PASS**  
**TECHNICAL AUDIT PACKAGE: PASS**  
**INDEPENDENT EXTERNAL SIGN-OFF: OPEN UNTIL THIRD-PARTY REVIEW**
