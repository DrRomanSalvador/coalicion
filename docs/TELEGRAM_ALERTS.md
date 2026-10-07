# Alertas Telegram de la Colmena

La vigilancia diaria ya genera un informe neutral y un adaptador de notificación. Telegram usa el Bot API HTTP y el método sendMessage.

## Configuración única

1. En Telegram abre @BotFather, ejecuta /newbot y guarda el token como una contraseña.
2. Abre una conversación con el bot y pulsa Start.
3. Obtén el chat_id de tu conversación usando el mecanismo oficial de actualizaciones del Bot API.
4. En GitHub, abre Settings → Secrets and variables → Actions y crea:
   - NOTIFY_WEBHOOK_URL: endpoint completo de sendMessage, con el token del bot incorporado, guardado como secreto.
   - TELEGRAM_CHAT_ID: identificador del chat.
5. El workflow debe exponer esos dos secretos al paso scripts/notify_webhook.py.

El token nunca debe entrar en el repositorio. Telegram indica expresamente que el token identifica al bot y debe tratarse como una contraseña.

## Qué se notifica

- encuesta nueva;
- encuesta modificada;
- fuente inaccesible o parseo bloqueado;
- referencia al informe generado.

Las cifras se normalizan y validan antes de entrar en el informe. Los escenarios de coalición son descriptivos; no hay recomendación, ranking ni asesoramiento de campaña.

## Límites deliberados

Un feed RSS puede demostrar que apareció un nuevo sondeo, pero no necesariamente contiene sus porcentajes. En ese caso el informe queda marcado como METADATA_ONLY y no inventa cifras. Los escaños solo se calculan cuando existe entrada territorial válida; no se proyectan porcentajes nacionales a provincias mediante supuestos de transferencia de voto.
