# Alertas Telegram de la Colmena

## 1. Crear el bot

En Telegram abre **@BotFather** y ejecuta `/newbot`. El token que devuelve es una credencial: no lo publiques ni lo commits.

Después abre tu bot y pulsa **Start**.

## 2. Obtener el chat ID

Puedes obtenerlo mediante el Bot API, por ejemplo consultando las actualizaciones del bot después de enviarle `/start`. El valor se guarda únicamente como secreto de GitHub.

## 3. Crear los Secrets

En `DrRomanSalvador/coalicion → Settings → Secrets and variables → Actions` crea:

- `reina_token`: token entregado por @BotFather. El workflow lo inyecta en runtime como `TELEGRAM_BOT_TOKEN`; el secreto nunca se expone en el código.
- `TELEGRAM_CHAT_ID`: chat de destino de notificaciones de workflows que usan un único destinatario.
- `TELEGRAM_ALLOWED_CHATS`: lista separada por comas de chats autorizados a recibir alertas del monitor de encuestas. Si falta, el workflow usa `TELEGRAM_CHAT_ID` como destino único. No se escriben IDs en el código.

No deben aparecer en ningún archivo del repositorio.

## 4. Qué ejecuta GitHub Actions

El workflow `.github/workflows/poll_monitor.yml`:

- ejecuta la vigilancia dos veces en UTC para cubrir el cambio horario europeo;
- el programa solo continúa cuando son las 08:00 en `Europe/Madrid`;
- descarga las fuentes explícitas;
- detecta fuentes nuevas/cambiadas;
- valida y normaliza encuestas;
- genera `artifacts/neutral_poll_report.json`;
- envía Telegram ante `ALERT` o `BLOCKED`;
- persiste evidencia y estado.

La API utilizada es la oficial `sendMessage`. El token se proporciona exclusivamente mediante GitHub Secrets.

## 5. Prueba segura

Ejecuta el workflow manualmente con **Run workflow**. No se introduce una encuesta ficticia en los datos productivos. Para probar Telegram, la prueba debe usar el propio notifier con una carga sintética y no contaminar el histórico electoral.

## 6. Neutralidad

Las alertas son descriptivas. No producen:

- recomendación de coalición;
- ranking de opciones;
- asesoramiento de campaña;
- priorización territorial;
- supuestos de transferencia de voto no observados.

Los escenarios de SUMAR + Podemos, SUMAR + PSOE, SUMAR + Podemos + PSOE y candidaturas separadas se mantienen como escenarios matemáticos descriptivos.

## 7. Fallos

Si falta un secreto, Telegram rechaza el mensaje, una fuente no está disponible o una encuesta no puede validarse, el sistema falla cerrado y conserva la evidencia del incidente.

## 8. Horario

La referencia es **08:00 Europe/Madrid**. No se fija una única hora UTC durante todo el año porque Madrid alterna UTC+1 y UTC+2.
