# Auditoría metodológica: Kiko Llaneras vs COALICIÓN

Fecha: 2026-10-07.

## Evidencia
Se separan hechos documentados, inferencias y pendientes. No se atribuyen MRP ni fundamentals a Llaneras sin evidencia pública suficiente.

## Metodología documentada
En 2023 Llaneras describe: promedio ponderado de decenas de sondeos por tamaño muestral, casa/historial y fecha; penalización de encuestas repetidas; proyección nacional a provincias usando resultados anteriores; incertidumbre calibrada con precisión histórica y distancia a la elección; 15.000 simulaciones; y reparto D'Hondt con barrera del 3%.

En 2026 mantiene la estructura, con 20.000 simulaciones y uso de resultados de 2023 y, para candidaturas nuevas/separadas, europeas de 2024 y andaluzas de 2026.

En una metodología de 2018 sobre México describe además corrección parcial de efectos de casa y decaimiento temporal exponencial.

## Comparación con COALICIÓN

| Técnica | Llaneras | COALICIÓN | Diagnóstico |
|---|---|---|---|
| Agregación de encuestas | Sí | Capacidad prevista; dataset histórico consolidado pendiente | Brecha operativa |
| Peso por tamaño muestral | Sí | No activo en el agregador operacional | Candidato |
| Peso por casa/historial | Sí | House effect latente en SEEC; baseline operacional no lo activa | Capacidad existente |
| Decaimiento temporal | Sí | No hay agregador equivalente activo | Candidato |
| Repetición de una casa | Sí | No activo como componente del agregador | Candidato |
| Calibración histórica | Sí | poll_error + OOS | Compatible |
| Territorialización | Sí | Sí, cadena territorial explícita | Compatible |
| Monte Carlo | Sí | Sí, PCG64, mínimo 10.000 | Compatible |
| D'Hondt | Sí | Sí, aritmética exacta | Igual |
| Barrera 3% | Sí | Sí | Igual |
| House effects jerárquicos | Parcial/documentado | Sí en SEEC | Capacidad nuestra, pendiente de validación predictiva |
| MRP | No demostrado | No activo | No incorporar por imitación |
| Fundamentals | No demostrado | No activo | No incorporar por imitación |
| Coaliciones como suma de escaños | No: recalcula D'Hondt desde votos | No: recalcula D'Hondt por circunscripción | Premisa del prompt corregida |

## Riesgos a auditar
1. Recencia demasiado agresiva.
2. House effects inestables con pocas observaciones.
3. Sesgo de selección al excluir encuestadoras.
4. Territorialización desde resultados anteriores cuando cambia la geografía electoral.
5. Correlación entre encuestas.
6. Eventos posteriores al último campo.
7. Cambios de candidatura sin serie comparable.

Son riesgos estructurales, no acusaciones de sesgo político.

## Filtro “mejorar a Llaneras”
baseline reproducible → candidato → entrenamiento histórico → test OOS → métricas → calibración → activar/no activar.

Métricas mínimas: MAE/RMSE de voto por partido, MAE de escaños, error territorial, cobertura 50/80/90%, calibración y estabilidad entre elecciones.

Una mejora solo se activa si supera al baseline sin fuga temporal.

## Integración decidida
**Integrado ahora:** auditoría metodológica y protocolo OOS como regla de activación.

**No activado como predictor:** pesos concretos copiados de Llaneras, MRP, fundamentals y corrección fija de house effects.

El motivo es verificable: la CSV histórica de encuestas versionada actualmente no contiene observaciones. Activar una corrección aprendería parámetros sin evidencia OOS.

## Estado
KIKO_AUDIT = COMPLETE
HOUSE_EFFECT_CAPABILITY = PRESENT_IN_SEEC
POLL_AGGREGATOR_LLANERAS_STYLE = NOT_ACTIVATED
MRP = NOT_SUPPORTED_BY_EVIDENCE
FUNDAMENTALS = NOT_SUPPORTED_BY_EVIDENCE
COALITION_DHONDT = ALREADY_PRESENT
CERTIFICATION = PENDING_APPROVAL
