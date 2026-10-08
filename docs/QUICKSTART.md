# QUICKSTART

## Estado actual

COALICIÓN puede ejecutarse como sala de situación electoral con evidencia materializada.

Validación Telegram: `python -m pytest -q tests/test_telegram_bot.py tests/test_telegram_integration.py`

Validación territorial: `python -m pytest -q tests/test_territorial_data_collection.py tests/test_telegram_evidence.py`

## Telegram

Configurar credenciales y allowlist en el entorno de despliegue. La autorización permanece fail-closed si la allowlist no está configurada.

Comandos principales: `/briefing`, `/situacion`, `/fuentes`, `/territorio`, `/evidencia <survey_id>`, `/encuestas`, `/escenarios`, `/escanos`.

## Regla territorial

Las encuestas nacionales no se transforman automáticamente en votos provinciales. Sin matriz territorial explícita, el cálculo de escaños de las generales devuelve `BLOCKED`.

## Release

No usar `v1.0.0` hasta que `RELEASE_v1.0.0.md` deje de indicar `NO RELEASED — BLOQUEADO`.
