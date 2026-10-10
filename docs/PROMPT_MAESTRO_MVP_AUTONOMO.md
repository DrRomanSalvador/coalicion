# PROMPT MAESTRO — MVP AUTÓNOMO COALICIÓN
**Repositorio único:** `DrRomanSalvador/coalicion` · **Rama objetivo:** `main` · **Modo:** ejecutar código real, no redactar propuestas.

## MISIÓN
Convierte el repositorio existente en un MVP electoral neutral, utilizable y demostrable: monitorización web de encuestas y datos oficiales, detección de novedades, alertas fiables por Telegram, informes ejecutivos breves, escenarios electorales reproducibles y autocontrol de calidad. Activa y aprovecha la Colmena y la Abeja Reina ya existentes. No construyas una segunda colmena, otra reina ni una arquitectura paralela.

## ORDEN DE EJECUCIÓN
Trabaja en ciclos autónomos hasta agotar el tiempo/contexto disponible:
1. Inspecciona el estado actual de `main`, instrucciones, diff, historial, CI y evidencias recientes.
2. Reanuda la misión pendiente desde `docs/COLMENA_STATE.json`, `docs/COLMENA_MISSION_CONTROL.json` y los artefactos canónicos; contrasta siempre su vigencia con GitHub.
3. Lee solo los archivos relevantes y sus consumidores. Localiza la implementación existente antes de añadir código.
4. Elige la tarea de mayor impacto demostrable para desbloquear el MVP.
5. Implementa el cambio mínimo completo; añade/actualiza pruebas de regresión.
6. Ejecuta pruebas específicas, controles estáticos y pruebas integradas disponibles.
7. Inspecciona el diff, riesgos, duplicidades y estado de la rama; corrige los defectos detectados.
8. Persiste evidencias verificables y continúa con la siguiente tarea segura.
9. Al terminar, informa en un máximo de cinco líneas: corregido, pruebas, commit, bloqueos, siguiente acción.

No pares tras diagnosticar. No preguntes por decisiones que puedan resolverse leyendo el repositorio o la documentación oficial. Pregunta solo cuando sea imprescindible una autorización, credencial o decisión irreversible. Nunca afirmes haber editado, probado, enviado, activado o desplegado algo que no se haya realizado realmente.

## COLMENA / ABEJA REINA — ACTIVACIÓN REAL
Componentes conocidos que deben verificarse antes de modificarlos:
- `scripts/queen_bee_v3.py`, `scripts/queen_bee.py`, `scripts/queen_bee_v2.py`
- `.github/workflows/colmena_atomic_swarm.yml`
- `docs/COLMENA_STATE.json`, `docs/COLMENA_MISSION_CONTROL.json`
- `scripts/colmena_checkpoint.py`, `scripts/validate_colmena_state.py`, `src/colmena_resume.py`
- `docs/INVOCACION_COLMENA.md`, `docs/COLMENA_AGENT_RUNTIME.md`

Confirma los nombres y rutas en el árbol actual: no des por existentes rutas históricas sin comprobarlas. Usa el workflow de Colmena existente y sus controles fail-closed. No consumas créditos ni invoques proveedores de inferencia externos de pago. La coordinación lógica de agentes no equivale a ejecución paralela real. Cada misión debe tener objetivo, archivos acotados, pruebas, evidencia y estado persistido. Evita que dos agentes editen los mismos archivos. Las respuestas de agentes quedan en revisión hasta que una comprobación independiente verifique el cambio. No concedas PASS por afirmación del propio agente.

## MVP PRIORITARIO
Entrega primero el flujo vertical que produzca valor hoy:
**fuente → adquisición → validación → normalización → deduplicación → análisis → alerta/informe → persistencia → pruebas/evidencia.**

### 1. Monitorización
Audita y reutiliza `src/poll_monitor.py`, `config/poll_monitor.json`, `artifacts/poll_monitor_state.json`, `artifacts/survey_history.jsonl`, `artifacts/surveys/` y `.github/workflows/poll_monitor.yml`.
- Mantén fuentes oficiales y privadas diferenciadas por autoridad, procedencia y tipo.
- Verifica cada URL, estado HTTP, formato, fecha, cobertura y esquema; tolera fallos transitorios con timeout y reintentos limitados.
- Valida y normaliza antes de usar; guarda hash SHA-256, origen, fecha de captura y referencia pública cuando sea posible.
- Deduplica por identidad estable y contenido; una revisión real de una encuesta debe distinguirse de una encuesta nueva.
- No conviertas errores, páginas vacías, datos caducados o HTML de error en observaciones válidas.
- Una fuente caída no debe borrar el último dato válido: marca su antigüedad y la degradación de cobertura.
- Corrige conectores rotos con pruebas de contrato y fixtures reproducibles; no inventes encuestas para cubrir huecos.
- El cron de GitHub Actions es periódico, no tiempo real estricto. Optimiza el intervalo dentro de límites reales gratuitos y explica el retraso medido; no prometas latencia que no se ha probado.

### 2. Telegram operativo
Audita y reutiliza `src/telegram_bot.py`, `src/telegram_notifier.py`, `src/telegram_persistence.py`, `scripts/telegram_notifier.py`, `scripts/verify_telegram_integration.py`, workflows y pruebas existentes.
- Flujo verificable: evento nuevo/cambio relevante → validación → deduplicación persistente → mensaje conciso → registro de envío/error.
- Enviar inmediatamente después de detectar una novedad válida en cada ejecución; no mandar una alerta por cada encuesta antigua en cada ciclo.
- Incluir fuente y enlace, fecha, cambio medido, significado, nivel de confianza y limitaciones; nunca inventar cifras.
- Alertar sobre fuentes caídas/recuperadas, cobertura insuficiente y errores críticos sin confundirlos con novedades electorales.
- Gestionar rate limits, timeouts, reintentos acotados y respuestas de API; evitar bucles y duplicados.
- Respetar chats permitidos y responder al chat de origen solo si el diseño y la autorización lo permiten.
- Los tokens y chats solo en GitHub Secrets/variables protegidas; nunca en código, logs o artefactos públicos.
- Prueba sintética aislada para notificación; nunca contaminar el histórico productivo.
- No declarar entrega real hasta verificar una respuesta satisfactoria de Telegram. Si faltan secretos, dejar el envío BLOCKED y probar el resto sin fingir éxito.

### 3. Informes ejecutivos de alta calidad
Genera informes breves, accionables y neutrales en JSON y texto/Markdown, reutilizando el sistema de informes existente:
- Qué ha cambiado, cuándo y según qué fuente.
- Magnitud de la variación y comparación correcta con la observación anterior.
- Impacto potencial en votos/escaños/escenarios solo si los datos y el modelo lo respaldan.
- Incertidumbre, limitaciones, fuentes fallidas y antigüedad de los datos.
- Enlace directo a la evidencia.
- Separación inequívoca entre hecho oficial, encuesta, estimación y simulación.
- Orden por relevancia calculada y regla explícita; no por preferencia partidista.
No envíes digest vacío ni repitas información sin cambios. Longitud objetivo: lectura inferior a un minuto. La brevedad nunca elimina fuente, fecha, incertidumbre ni limitaciones esenciales.

### 4. Rigor matemático y electoral
Reutiliza los motores canónicos; no crees cálculos paralelos. Verifica la legislación y resultados oficiales aplicables a cada elección.
- D'Hondt, umbrales, magnitudes, desempates y reglas especiales deben estar codificados según la elección/circunscripción correspondiente.
- Usa aritmética exacta para cocientes y desempates cuando sea pertinente.
- Invariantes: escaños asignados = escaños disponibles; porcentajes y denominadores coherentes; resultados deterministas con entradas idénticas.
- Distingue votos válidos, blancos, nulos, participación, candidatura y coalición electoral.
- No trates promedios de encuestas como resultados oficiales.
- No generes probabilidades, transferencias de voto, intervalos o recomendaciones sin método declarado y validado.
- Backtests estrictamente temporales: prohibido usar información publicada después de la fecha pronosticada.
- Publica métricas de error/calibración solo si se han calculado con datos trazables.
- Neutralidad comprobable: mismas reglas, fuentes, umbrales y métricas para todas las candidaturas.

### 5. Web y acceso público
Prioriza fuentes oficiales, RSS/Atom, páginas públicas y endpoints documentados con acceso permitido. Reutiliza conectores actuales. Respeta robots, términos, copyright, límites y TLS. No uses scraping evasivo, credenciales no autorizadas ni APIs de pago. Si una fuente falla, informa y continúa con las demás fuentes válidas. Los enlaces de cada alerta deben abrir la fuente original o evidencia reproducible.

## AUTORREGULACIÓN Y SEGURIDAD
Mantén el control **detectar → reproducir → diagnosticar → parche mínimo → test de regresión → suite relevante → revisión independiente del diff → persistir evidencia**.
- P0: exposición de secretos, corrupción, ejecución insegura o resultados electorales incorrectos.
- P1: flujo MVP roto, alertas engañosas, pérdida de estado o fallo de cálculo.
- P2: conectores degradados, incompatibilidades o cobertura insuficiente.
- P3: mejoras no bloqueantes.
Corrige P0/P1 antes de mejoras cosméticas. No escondas errores con excepciones genéricas, valores por defecto ficticios, mocks en producción ni tests debilitados. Limita reintentos y duración; evita ciclos de autocorrección infinitos. Una reparación que no pasa pruebas se revierte o queda aislada. No hagas push forzado, no desactives protecciones y no fusiones sin las validaciones exigidas.

## COSTE Y EFICIENCIA
- Solo soluciones gratuitas y dentro de cuotas/condiciones verificadas.
- No incorporar APIs/modelos de pago, infraestructura persistente facturable o nuevos servicios con coste potencial.
- Evitar dependencias nuevas si la biblioteca existente resuelve el problema.
- Reducir llamadas, lecturas repetidas, ejecuciones redundantes y artefactos duplicados.
- Mantener estado incremental y hashes para procesar solo cambios.
- Usar informes compactos y un registro persistente de tareas con evidencia.
- No sacrificar seguridad, rigor matemático ni pruebas para ahorrar tokens.
- Nunca persistir tokens, IDs personales innecesarios ni datos sensibles en Git.

## DEFINITION OF DONE — MVP
Cada criterio se marca PASS solo con evidencia; de lo contrario FAIL, BLOCKED o NOT_TESTED.
1. Instalación/configuración reproducible y guía de inicio correcta.
2. Al menos una fuente funcional verificada de extremo a extremo, y cobertura de fuentes declarada con precisión.
3. Novedad nueva detectada y deduplicación demostrada en pruebas.
4. Estado e historial persistentes sin pérdida ante concurrencia o reintentos.
5. Informe breve con fuente, fecha, cambio, enlace y limitaciones.
6. Cálculos electorales cubiertos por pruebas de invariantes y casos límite.
7. Telegram probado de verdad si existen secretos; si no, integración probada y envío real BLOCKED.
8. Workflow validado, permisos mínimos y frecuencia descrita con honestidad.
9. Pruebas relevantes superadas, sin regresiones introducidas y diff revisado.
10. Ninguna afirmación comercial de precisión, tiempo real, autonomía o disponibilidad sin evidencia.
11. Demo reproducible que muestre el flujo vertical con datos reales verificables.
12. Bloqueos externos explícitos, sin ocultarlos bajo un estado global PASS.

## RESTRICCIONES DE CAMBIO
- Repositorio único: `DrRomanSalvador/coalicion`; fuente de verdad: GitHub.
- Antes de editar, inspecciona estado y consumidores. Evita sobrescribir cambios ajenos.
- No reescribas archivos grandes si basta un parche acotado.
- No dupliques módulos, workflows, monitores, bots, informes ni fuentes de estado.
- Conserva contratos válidos y añade pruebas al cambiar interfaces.
- No hagas despliegues, releases, cambios de permisos o acciones irreversibles sin autorización.
- No afirmes que una función está activada solo porque el workflow existe: comprueba ejecución y resultado.
- No digas “100 % perfecto”, “infalible” ni “tiempo real” sin definición medible y evidencia.

## RESPUESTA FINAL — MÁXIMO 5 LÍNEAS
`Corregido: …`
`Pruebas: …`
`Commit: <SHA real | NO CREADO>`
`Bloqueos: …`
`Siguiente: …`

**Empieza ahora en el repositorio real. Inspecciona estado, activa/valida la Colmena existente mediante su workflow disponible, identifica el primer bloqueo del flujo MVP y ejecuta la corrección verificable de mayor valor. No respondas con otro plan: modifica y prueba código.**