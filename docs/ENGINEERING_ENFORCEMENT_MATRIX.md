# Matriz de cumplimiento obligatorio de los 25 principios

Esta matriz convierte la Carta de ingeniería en criterios comprobables. Un principio puede tener control automático, revisión obligatoria o ambos. No se declara cubierto por el mero hecho de aparecer en documentación. Toda excepción debe indicar motivo, alcance, responsable y vencimiento en la PR.

| Nº | Principio | Control exigible antes de integrar | Tipo |
|---:|---|---|---|
| 01 | Legibilidad | Diff revisable; lint/formato cuando estén configurados; revisión de nombres y efectos | CI + revisión |
| 02 | Automatizar lo repetible | Comprobar que tareas repetidas tienen comando/workflow canónico y no duplicado | Revisión |
| 03 | Pruebas | CI relevante en verde; regresión para cada bug corregido cuando sea viable | CI + revisión |
| 04 | Responsabilidad única | Tests de límites y revisión de acoplamiento; no crear servicios sin necesidad | Revisión |
| 05 | Diseñar para el fallo | Timeouts, límites, tratamiento de errores y reintentos acotados donde aplique | CI + revisión |
| 06 | Seguridad desde el diseño | Permisos mínimos, no secretos en cambios, análisis de dependencias disponible | CI + revisión |
| 07 | Medir antes de optimizar | Evidencia reproducible para optimizaciones con impacto material | Revisión |
| 08 | Tecnología adecuada | Justificación de dependencias/plataformas nuevas y coste de mantenimiento | Revisión |
| 09 | Listo para desplegar | CI, artefacto verificable y validación/rollback proporcional al riesgo | CI + revisión |
| 10 | Mejora continua | Revisar deuda tocada sin ampliar innecesariamente el alcance | Revisión |
| 11 | Autorreparación segura | Auditoría del self-healer, presupuesto de reintentos, idempotencia y parada segura | CI |
| 12 | Chaos con límites | Prohibido experimento destructivo sin autorización, aislamiento, abortos y rollback documentados | Revisión bloqueante |
| 13 | Inmutabilidad apropiada | Evidencia versionada; no sobrescritura silenciosa de datos/auditorías | CI + revisión |
| 14 | Latencia medible | Medición/SLO cuando el cambio afecte rendimiento; no optimización sin perfil | Revisión |
| 15 | Gobierno arquitectónico | Contratos, workflows, permisos, timeouts y dependencias auditados en CI | CI |
| 16 | Observabilidad segura | Logs útiles y estructurados donde aplique; prohibido filtrar secretos/datos innecesarios | CI + revisión |
| 17 | Contratos API | Pruebas de contrato/compatibilidad para interfaces afectadas | CI + revisión |
| 18 | Simplicidad operativa | Instrucciones reproducibles, dependencias declaradas y runbook para cambios operativos | Revisión |
| 19 | Decisiones registradas | ADR para cambios arquitectónicos relevantes; no exigir ADR para cambios triviales | Revisión |
| 20 | Postmortem sin culpas | Incidente relevante genera acción verificable y regresión cuando sea viable | Revisión |
| 21 | Uso correcto fácil | Tipos, esquemas y validaciones rechazan estados inválidos cuando sea posible | CI + revisión |
| 22 | Compatibilidad | Pruebas de compatibilidad o migración documentada si cambia una interfaz pública | CI + revisión |
| 23 | Minimalismo | Justificar abstracciones, dependencias, servicios o capas nuevos | Revisión |
| 24 | Determinismo | Pruebas reproducibles; semilla y versión explícitas para aleatoriedad | CI + revisión |
| 25 | Utilidad y responsabilidad | Revisar privacidad, accesibilidad, neutralidad, interoperabilidad y afirmaciones demostrables | Revisión bloqueante |

## Protocolo obligatorio de PR

La descripción de cada PR debe registrar: **causa raíz, solución mínima, principios aplicables (01–25), pruebas ejecutadas, resultado CI, riesgo/rollback y excepciones**.

**No basta enumerar números.** Cada principio aplicable se documenta en una línea propia con su ID y una justificación concreta: efecto del cambio, control exigido y/o evidencia de cómo se cumple. Una lista desnuda como `02, 03, 15` no satisface el contrato. El gate automático debe rechazarla. `N/A` solo es admisible si se explica por qué el cambio no afecta directamente ningún principio; no exime de cumplir los principios globales de seguridad, trazabilidad, reproducibilidad, fail-closed y responsabilidad. La revisión de aplicabilidad es habitual en todas las PR; el control concreto es proporcional al riesgo y a la naturaleza del cambio.

No se permite marcar una comprobación como PASS sin evidencia.

La auditoría automática bloquea la integración cuando faltan permisos explícitos, concurrencia, timeout por job, o existe `cancel-in-progress: true`. Los controles que requieren juicio humano deben aprobarse mediante la revisión exigida por la configuración de protección de rama. Un workflow dentro del repositorio no puede sustituir ni activar por sí solo esa protección administrativa.
