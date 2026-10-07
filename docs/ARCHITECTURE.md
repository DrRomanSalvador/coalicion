# Arquitectura del monitor de encuestas

## Capas
1. Fuentes: adaptadores nominales en src/monitors/ y configuración en config/poll_monitor.json.
2. Captura: src/poll_monitor.py conserva el cuerpo bruto y su SHA-256.
3. Normalización: src/poll_normalizer.py expone el registro canónico de partidos.
4. Validación: src/poll_validator.py aplica el contrato fail-closed.
5. Identidad: src/poll_hasher.py expone hash de contenido e identidad de estudio.
6. Persistencia: snapshots, histórico JSONL y estado operacional.
7. Alertas: src/telegram_notifier.py.
8. Orquestación: .github/workflows/poll_monitor.yml.

## Regla de evidencia
Una página que menciona una encuesta no se convierte automáticamente en una encuesta estructurada. Solo un extractor que encuentre valores explícitos y pase validación crea un objeto Poll utilizable.

## Fail-closed
No se completan residuos, no se inventan valores territoriales y no se convierten porcentajes nacionales en escaños. Una fuente primaria sin extractor estructurado mantiene bloqueada la cobertura total.

## Telegram
El notifier resuelve dinámicamente la conversación privada más reciente del bot. El token procede exclusivamente de TELEGRAM_BOT_TOKEN. TELEGRAM_CHAT_ID puede conservarse como secreto de compatibilidad, pero no se hard-codea.

## CI
El workflow valida configuración, ejecuta tests y ejecuta el monitor. El schedule de cinco minutos es near-real-time, no una garantía dura de latencia.
