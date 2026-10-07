# Monitorización autónoma de encuestas

## Arquitectura

`config/poll_monitor.json` define las fuentes. `src/poll_monitor.py` captura, hashea, normaliza, valida y persiste. El workflow `.github/workflows/poll_monitor.yml` ejecuta el proceso cada cinco minutos y en modo manual.

## Fuentes

Se vigilan CIS, Electomanía, Dato Electoral, Europe Elects, MyF Data, Sigma Dos, GAD3, NC Report, Demoscopia, Celeste-Tel, Invymark y Political Stats. Europe Elects X queda preparado como adaptador opcional mediante `X_BEARER_TOKEN` y un ID de usuario configurado; no se inventa ese identificador.

La cobertura tiene tres niveles:
- **VALIDATED:** se han extraído valores de partido y han superado validación.
- **DISCOVERY_ONLY / PAGE_FINGERPRINT_ONLY:** la fuente ha sido capturada y trazada, pero no se reproducen cifras no estructuradas.
- **BLOCKED:** la fuente no pudo recuperarse o su formato no pudo validarse.

## Fail-closed

Nunca se completan partidos faltantes, nunca se normaliza una suma nacional a 100 %, nunca se convierte voto nacional en voto provincial y nunca se calcula escaños sin una matriz territorial verificable.

Dato Electoral se usa para cifras únicamente cuando la página contiene explícitamente el bloque de «Estimación de voto publicada por el sondeo» y los valores superan la validación. La propia fuente explica que distingue sondeos con ficha técnica completa de los que no publica con cifras; el monitor respeta esa distinción.

## Trazabilidad longitudinal

Cada captura cruda recibe SHA-256 y se guarda como `artifacts/surveys/<source>__<sha>.raw`. Cada ejecución se registra en `artifacts/surveys/polls_YYYYMMDD_HHMMSS.json` y en `artifacts/survey_history.jsonl`. `artifacts/poll_monitor_state.json` conserva hashes de encuestas, fuentes, fallos y contadores.

El workflow tiene `contents: write` para que el estado sobreviva a ejecuciones independientes. El commit solo se crea si cambian artefactos.

## Telegram

Una encuesta validada nueva o modificada genera alerta inmediata. También se registra un fallo de fuente cuando aparece por primera vez o cambia. El bot usa `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. `X_BEARER_TOKEN` es opcional para X/Twitter.

## Frecuencia

GitHub permite un intervalo mínimo programado de cinco minutos, pero la ejecución programada puede sufrir retrasos por carga de la plataforma. Por ello el sistema es **near-real-time sobre GitHub Actions**, no una garantía de latencia de cinco minutos.

## Integración electoral

Este monitor no altera `src/neutral_coalition.py`. Una encuesta nacional no se transforma en territorialidad. Las proyecciones de escaños permanecen bloqueadas hasta disponer de datos territoriales verificables.

## Diagnóstico

Ejecutar:

`pytest -q tests/test_poll_monitor.py`

y:

`python -m src.poll_monitor`

Los logs deben mostrar número de encuestas validadas, nuevas/cambiadas y ruta del snapshot.
