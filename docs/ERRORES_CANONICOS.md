# REGISTRO CANÓNICO DE ERRORES — COLMENA DE COALICIÓN

Registro normativo. Cada ID tiene un único significado.

## Severidades
- BLOCKER: detiene ejecución y certificación.
- ERROR: detiene la etapa actual.
- WARNING: solo si el contrato lo permite.
- INFO: trazabilidad.

## Códigos
| ID | Sev. | Condición | Acción |
|---|---|---|---|
| COLMENA_STATE_MISSING | BLOCKER | Falta el estado | DETENER |
| COLMENA_STATE_INVALID | BLOCKER | Estado/schema inconsistente | DETENER |
| INVOCATION_MISSING | BLOCKER | Falta PROM de arranque | DETENER |
| CONTRACT_MISSING | BLOCKER | Falta contrato maestro | DETENER |
| METHOD_MISMATCH | BLOCKER | Metodología/version distinta | DETENER |
| SEED_MISMATCH | BLOCKER | RNG o semilla distinta | DETENER |
| SOURCE_ANCHOR_MISSING | BLOCKER | Falta fuente anclada | DETENER |
| SOURCE_HASH_DECLARATION_MISMATCH | BLOCKER | Hash declarado incorrecto | DETENER |
| PRIMARY_BINARY_NOT_REPOSITORY_PINNED | BLOCKER | Falta binario canónico | DETENER; no buscar sustituto |
| PRIMARY_HASH_MISMATCH | BLOCKER | SHA-256 incorrecto | DETENER |
| EVIDENCE_MISSING | BLOCKER | Falta evidencia | DETENER |
| EVIDENCE_STALE | BLOCKER | Evidencia de otro estado | DETENER |
| DUPLICATE_WORK | ERROR | Trabajo ya certificado | REUTILIZAR evidencia |
| FUTURE_INFORMATION | BLOCKER | Información posterior al cutoff | DETENER |
| DATA_CONTRADICTION | BLOCKER | Fuentes incompatibles | DETENER |
| REPRODUCIBILITY_FAILURE | BLOCKER | Misma entrada, salida distinta | DETENER |
| PARAMETER_DRIFT | BLOCKER | Parámetros no canónicos | DETENER |
| METHODOLOGY_DRIFT | BLOCKER | Cambio sin versión/validación | DETENER |
| UNSUPPORTED_INFERENCE | BLOCKER | Inferencia no sustentada | DETENER |
| HIDDEN_IMPUTATION | BLOCKER | Imputación no etiquetada | DETENER |
| COALITION_SEAT_SUMMATION | BLOCKER | Coalición simulada sumando escaños | DETENER |
| PARTISAN_OPTIMIZATION | BLOCKER | Optimización partidista | DETENER |
| EXTERNAL_AUDIT_UNAVAILABLE | BLOCKER | Auditoría externa no real | DETENER |
| UNPERSISTED_CHECKPOINT | BLOCKER | Trabajo sin checkpoint persistido | DETENER |
| MULTIPLE_NEXT_ACTIONS | BLOCKER | Más de una acción siguiente | DETENER |
| CHAT_CONTEXT_DEPENDENCY | BLOCKER | Requiere memoria del chat | USAR REPOSITORIO |
| TOKEN_BUDGET_RISK | ERROR | Riesgo de perder contexto | PERSISTIR CHECKPOINT |
| CERTIFICATION_WITH_OPEN_BLOCKER | BLOCKER | Se intenta certificar con bloqueos | DETENER |

| PRIMARY_RECONCILIATION | BLOCKER | Reconciliación oficial electoral no verificada | DETENER |
| SEEC_PRODUCTION_EXECUTION | BLOCKER | Ejecución SEEC de producción sin evidencia reproducible | DETENER |
| OOS_CALIBRATION | BLOCKER | Backtest fuera de muestra o calibración requerida ausente | DETENER |
| EXTERNAL_AUDIT | BLOCKER | Auditoría externa independiente pendiente cuando se exige certificación | DETENER release/certificación |
| ABSOLUTE_TIE | BLOCKER | Empate absoluto sin resolución legal explícita | DETENER |
| INVALID_VALID_VOTES | BLOCKER | Total de votos válidos inconsistente o inválido | DETENER |
| SEAT_CONSERVATION | BLOCKER | La asignación no conserva el total legal de escaños | DETENER |
| UNVERSIONED_DATA | BLOCKER | Dataset sin versión/hash/procedencia verificables | DETENER |
| INVENTED_TERRITORIALITY | BLOCKER | Se inventan o infieren datos electorales territoriales no observados | DETENER |
| MANUAL_RESULT_OVERRIDE | BLOCKER | Resultado canónico sobrescrito manualmente sin fuente y evidencia | DETENER |
| NONDETERMINISTIC_EXECUTION | BLOCKER | Misma entrada, código y semilla no producen resultado reproducible | DETENER |
| CI_EVIDENCE_MISSING_FOR_CONTINUITY_COMMIT | BLOCKER | Checkpoint/commit de continuidad sin evidencia CI del mismo SHA | DETENER |
| PRIMARY_2023_MATRIX_MATERIALIZATION | BLOCKER | Matriz oficial territorial 2023 ausente, incompleta o no reconciliada | DETENER |

## Regla universal
DETENER → IDENTIFICAR → REGISTRAR → PERSISTIR → NO PROPAGAR.
Nunca sustituir automáticamente fuente, semilla, parámetro, metodología, archivo o evidencia.
