# Autonomous execution log — 2026-10-06

## 20:03 — Baseline
- Commit inicial: 49334640c99fc98b4aa466b75c9b784a001ad961
- Inventario: 73 archivos / 10 directorios.
- CI Colmena run 37523506246: FAIL en `src.colmena_resume` por `UNKNOWN_ERROR_CODE:CI_EVIDENCE_MISSING_FOR_CONTINUITY_COMMIT`.
- Fuente primaria binaria declarada en el contrato: ausente del repositorio.

## 20:42 — Corrección
- Se registró `CI_EVIDENCE_MISSING_FOR_CONTINUITY_COMMIT` en el registro canónico.
- Se añadió regresión para impedir que el estado y el registro vuelvan a divergir.

## 20:43 — Validación CI
- Reanudación pasó.
- Contrato reproducible falló correctamente por `PRIMARY_BINARY_NOT_REPOSITORY_PINNED`.
- Histórico: la fuente oficial XLSX pudo descargarse en CI; la validación histórica ejecutada siguió usando réplica secundaria y mostró discrepancia máxima de votos válidos de 1722.0; esto queda como evidencia no certificante.

## 20:45 — Endurecimiento
- Se añadió oráculo electoral independiente y pruebas diferenciales.
- Monte Carlo alineado con PCG64.
- Escenarios preservan Ceuta/Melilla.
- CI modificado para ejecutar tests independientes aunque falle el contrato y para no hacer push automático a main.
