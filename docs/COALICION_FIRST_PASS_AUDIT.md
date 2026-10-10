# COALICIÓN — Primera auditoría de evidencias contra la especificación maestra

**Corte:** 2026-10-11. **Base inspeccionada:** archivos accesibles de `main`. **Naturaleza:** auditoría estática inicial; no equivale a ejecución end-to-end ni certificación. No se atribuye SHA de commit porque la inspección disponible devolvió SHA de blobs por archivo, no una revisión única de repositorio.

## Regla de lectura

- **PARCIAL:** hay implementación y/o pruebas identificables, pero no está demostrado el ciclo operativo completo.
- **NO VERIFICADO:** no se ha obtenido evidencia suficiente en esta inspección. No significa automáticamente que no exista en otro archivo.
- **NO IMPLEMENTADO:** solo se utilizará después de una búsqueda/repositorio y una prueba suficientemente exhaustivas que permitan afirmarlo.
- Ninguna fila se considera OPERATIVA en esta auditoría inicial: no se ejecutaron pruebas ni se verificó una entrega real en producción durante esta inspección.

## Matriz inicial

| Dominio | Evidencia de repositorio localizada | Evidencia observada | Estado inicial | Prueba/evidencia que falta para cerrar |
|---|---|---|---|---|
| Motor electoral / D’Hondt | `src/electoral.py` blob `3db5a4efd40033bf51266db3d215d77aebdad77b`; `tests/test_electoral.py` blob `ddd99724c2dc1d061783a7a8b43f507b97129a8a` | Funciones `dhondt`, `allocate`, `allocate_congress`; 13 funciones de prueba visibles | PARCIAL | Ejecutar suite en SHA exacto; validar matriz oficial completa, todas las circunscripciones y escenarios especiales con fuente oficial y tolerancia cero |
| Motor de coaliciones | `src/coalition.py` blob `85a3baba93e52de565c5a025ee5a634042854774` | Motor contrafactual y generación de coaliciones | PARCIAL | Pruebas por circunscripción, escenario separado/conjunto, supuestos, comparación contra referencia y evidencia reproducible |
| Proyección/escenarios | `src/prediction.py` blob `51870275d60e2523976bf726d7dd432c77cbafe0`; `src/decision.py` blob `4fd0f4549f1f67e2148c9229841e6160070589de`; `src/uncertainty.py` blob `5e4ef40ce94ddf9e2fd467b145687253d112d6b9` | Simulación, predicción, escenarios históricos, hash de entradas y Monte Carlo están representados en código | PARCIAL | Ejecutar pipeline OOS completo, verificar calibración, métricas, baseline, semilla y reproducción de salida; no inferir que existe calibración solo por existir Monte Carlo |
| Monitor de encuestas | `src/poll_monitor.py` blob `e9fcc3c440cf1aec27da02b9ad2433db70564114`; `config/poll_monitor.json` blob `e7a44bf921dc8349d16d5853bbad6c8cf4017373`; `tests/test_poll_monitor.py` blob `4c1ade11ce7e60ffdf136bcfde335fcf4b2d46b3` | Monitor de 962 líneas; hashes, originales, historial, fallos de fuente y cola durable; 40 funciones de prueba visibles en el archivo de pruebas | PARCIAL | Ejecutar tests; auditar cada fuente configurada; confirmar sondeos reales detectados, correcciones, frescura y cobertura efectiva por fuente |
| Programación de monitor de encuestas | `.github/workflows/poll_monitor.yml` | Workflow con cron cada cinco minutos, timeout de 10 min y persistencia de estado/artifacts; intento de persistencia mediante commit | PARCIAL | Verificar ejecuciones recientes, conflictos de push, recuperación tras fallo, integridad del estado y operación sin intervención |
| Ingesta/vigilancia secundaria | `scripts/ingest_polls.py` blob `5a6884840f90f04212656d902529818c3f530978` | Hash SHA-256 y estado `BLOCKED_SOURCE` ante fallo parcial | PARCIAL | Confirmar workflow que lo invoca, datos brutos persistidos, alertas de recuperación y que no duplica el monitor principal |
| Telegram | `src/poll_monitor.py`; `tests/test_poll_monitor.py`; workflow de monitor | Hay lógica de entrega/reintentos y tests de token ausente, destinatarios y reintento por destinatario | PARCIAL | Prueba real controlada a chat autorizado; confirmar recepción, persistencia de pendientes, entrega tras recuperación y latencia |
| Catálogo completo de 97 alertas | Nuevo contrato `docs/COALICION_ALERT_CATALOG.json` | Especificación de 97 tipos, campos obligatorios y política configurable; esto no demuestra que cada regla esté conectada al monitor | NO VERIFICADO | Vincular cada ALT-ID a detector, fuente, test positivo/negativo, evidencia y política de entrega; ejecutar cobertura de los 97 tipos |
| Calendario electoral oficial y alertas de plazos | No localizado en los archivos de aplicación inspeccionados | No hay evidencia suficiente de un flujo completo de calendario oficial, actualización de fechas y alertas de vencimiento | NO VERIFICADO | Localizar/implementar ingesta de BOE/INE/JEC/Interior/Congreso; materializar calendario, plazos, fuentes y pruebas de cambio/recalculo |
| Monitorización institucional y política general | No localizada como pipeline completo en esta inspección | Hay requisitos definidos; falta evidencia del ciclo end-to-end de fuentes institucionales, declaraciones, votaciones, rectificaciones y cronología | NO VERIFICADO | Inventario por fuente; parsers; original y hash; clasificación hecho/declaración/análisis; pruebas de corroboración y contradicción |
| Inteligencia territorial y base histórica | Módulos de motor electoral/proyección identificados; no se verificó aquí el conjunto de datos completo | El código puede calcular escenarios, pero no se verificó cobertura materializada completa y trazable de elecciones/territorios | NO VERIFICADO | Auditar datasets y manifiestos; reconciliar datos oficiales por elección/circunscripción; cobertura y calidad por territorio |
| Briefing diario y centro de decisión | No localizado como ciclo operativo completo en esta inspección | No hay evidencia de generación programada, comparación de versiones y entrega con snapshot de datos | NO VERIFICADO | Identificar productor, scheduler, plantilla, evidencia de ejecución y prueba de informe reproducible |
| Seguridad, permisos, secretos y continuidad global | Workflow y tests de algunos contratos disponibles; no se hizo auditoría exhaustiva de todos los flujos | Evidencia parcial de controles; sin prueba integral de backup/restore, autorización, seguridad de fuentes hostiles y degradación | NO VERIFICADO | Auditoría por workflow, prueba de recuperación, revisión de permisos/secretos, tests de inyección de instrucciones y métricas de salud |
| Auditoría de alertas y calidad estadística | Tests OOS identificados en `tests/test_poll_monitor.py`; código de predicción/uncertainty presente | Existen pruebas de selección temporal y rechazo de datos posteriores al objetivo | PARCIAL | Ejecutar OOS en datos oficiales, publicar baseline/métricas, calibración probabilística, falsos positivos/negativos y resultados CI con SHA exacto |

## Calendario oficial verificado para el producto

La fuente primaria consultada es el [Real Decreto 806/2026, BOE-A-2026-20742](https://www.boe.es/buscar/doc.php?id=BOE-A-2026-20742), publicado el 6-10-2026. El decreto convoca elecciones al Congreso y al Senado para el **29-11-2026**, fija campaña del **13-11-2026 al 27-11-2026** y reunión constitutiva de las cámaras el **23-12-2026 a las 10:00**. La aplicación debe materializar estos hitos con referencia a la disposición y detectar cambios posteriores; esta comprobación documental no demuestra que el calendario ya esté implementado en COALICIÓN.

## Brechas P0 que deben cerrarse primero

1. Calendario electoral oficial versionado, plazos, alertas anticipadas y recálculo ante rectificación.
2. Estado de salud por fuente: última captura correcta, frescura, cobertura y caída/recuperación.
3. Detección de sondeos nuevos/cambiados con original, hash, metadatos y alerta Telegram entregada.
4. Briefing diario con snapshot temporal de datos y enlaces a evidencia.
5. Panel/artefacto de estado global: OPERATIVO, DEGRADADO, BLOQUEADO o SIN DATOS RECIENTES.
6. Prueba end-to-end de fallo, cola persistente, recuperación y entrega sin duplicación.

## Restricción de interpretación

Esta matriz es una **primera pasada basada en archivos identificados**, no una auditoría completa de todos los archivos ni una declaración de funcionalidades ausentes. Antes de convertir cualquier NO VERIFICADO en NO IMPLEMENTADO hay que completar el inventario del repositorio y comprobar todos los workflows, scripts, datos y pruebas relacionados. Antes de marcar OPERATIVO hay que ejecutar y conservar la evidencia correspondiente.
