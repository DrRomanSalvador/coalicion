# 🐝 COLMENA — REINVOCACIÓN

**Si una nueva conversación dice “Activa la colmena”, “Habla la abeja reina”, “Reinvoca la colmena” o “Continúa donde quedó la colmena”: leer primero `docs/INVOCACION_COLMENA.md` y recuperar el estado desde GitHub. No reconstruir desde el chat.**

# COALICIÓN — PUNTO DE ENTRADA ÚNICO

Este repositorio es la memoria operativa y reproducible del proyecto. Toda IA debe leer primero este README y `CONTRATO_MAESTRO_IA.md`.

## Regla suprema
**Mismos datos + mismas reglas + mismos parámetros + misma versión = mismo resultado.**

No se ajusta el modelo para acercarlo a una encuesta, partido, escaño o resultado esperado.

## Cadena única
FUENTES → DATOS → VALIDACIÓN → SESGOS → TERRITORIO → ESCENARIO → COALICIÓN → LEY ELECTORAL → MARGINALIDAD → INCERTIDUMBRE → RESULTADO → AUDITORÍA

## Filtro anti-sesgos
El modelo base compite contra correcciones candidatas mediante validación temporal fuera de muestra. No existe una corrección obligatoria por teoría o por observar que las encuestas se equivocaron.

Una corrección solo se acepta si:
- usa únicamente información disponible antes del periodo validado;
- se estima dentro de cada ventana de entrenamiento;
- no depende de la elección que está siendo predicha;
- mejora o mantiene las métricas predefinidas de voto, partido, territorio y escaños;
- no degrada calibración/estabilidad;
- y mejora estrictamente al menos una métrica, salvo justificación estadística preregistrada.

Si ninguna corrección supera al modelo base, **la corrección es cero**.

## Precisión electoral
- 52 circunscripciones y 350 diputados.
- Umbral provincial del 3% de votos válidos.
- D'Hondt con aritmética racional/exacta.
- Desempate por votos totales.
- Empate absoluto: bloqueo; nunca desempate arbitrario.
- Ceuta y Melilla: un escaño por mayoría; no D'Hondt.
- Coaliciones/fusiones: agregación de votos por circunscripción antes de asignar escaños.
- Nunca se convierte una distribución de escaños publicada en porcentajes no publicados.

## Territorialización
La cadena obligatoria es:
**voto nacional → voto territorial → candidatura elegible → ley electoral → escaños**.

No se inventa territorialidad para candidaturas sin base comparable. Toda imputación se etiqueta y propaga como incertidumbre. Las CCAA sirven para agregación/control; D'Hondt se ejecuta por circunscripción.

## Neutralidad y auditoría de coaliciones

El núcleo neutral está implementado en `src/neutral_coalition.py` y su auditoría estructural en `src/neutral_audit.py`. La matriz canónica 2023 no se fabrica: si `artifacts/data/election_2023_canonical.json` no existe o no cumple la estructura exigida, el sistema permanece **BLOCKED**. El esquema esperado está versionado en `artifacts/data/election_2023_canonical.schema.json`.

## Demo ejecutable de coaliciones — generales 2023

Desde la raíz del repositorio:

```bash
python scripts/demo_e2e.py
python scripts/demo_multiparty.py
pytest -q tests/test_demo_e2e.py tests/test_demo_multiparty.py tests/test_coalition.py tests/test_neutral_audit.py
```

La demo multiparty cubre Madrid y Barcelona y guarda el resultado en `artifacts/demo_multiparty_2023.json`; los supuestos están separados en `config/demo_multiparty_2023.json`. Incluye fragmentación observada, bloque seleccionado sin PSOE/PSC y bloque amplio con PSOE/PSC. Las agrupaciones son contrafactuales de suma mecánica de votos reales, no predicciones ni certificación electoral independiente. El workflow `.github/workflows/demo-multiparty.yml` ejecuta las pruebas focalizadas, la demo E2E existente y valida el JSON generado.

## Inteligencia electoral integrada

La bibliografía oficial y de contraste está conectada mediante `config/political_intelligence_sources.json` y `src/political_intelligence.py`.

La capa integra procedencia → evidencia → OOS/calibración → territorio → ley electoral → marginalidad → contrafactuales de coalición → snapshot de decisión, reutilizando los motores canónicos existentes y sin duplicar D'Hondt, predicción ni coaliciones.

Validación estructural: `tests/test_political_intelligence.py` y `.github/workflows/political_intelligence.yml`. La existencia del registro no certifica materialización de datos: `readiness()` falla cerrado hasta disponer de las evidencias físicas requeridas.

## Estado actual
- Contrato maestro: incorporado.
- Magnitudes oficiales 2026: incorporadas.
- Motor electoral: incorporado y endurecido en modo fail-closed.
- Tests legales básicos: incorporados; ejecución aislada del núcleo verificada.
- Filtro OOS anti-sesgos: en esta versión.
- Dataset histórico del Interior: el manifest `data/manifests/official_interior_congreso.json` registra materialización de 16 elecciones (1977–2023), 52 circunscripciones y 322.556 registros; la reconciliación 2023 declarada en el manifest es de 0 discrepancias. La auditoría independiente sigue siendo distinta de esta evidencia interna.
- Analizador reproducible de error encuesta→resultado desde 2004: incorporado.
- Matriz histórica normalizada: `data/official_interior_congreso_1977_2023.csv`, con SHA-256 y tamaño fijados en el manifest. Cobertura y calidad de las encuestas históricas siguen siendo una tarea separada.
- Archivo histórico completo de encuestas y resultados: pendiente de consolidación.
- Contexto gobierno/oposición y análisis de movimiento entre elecciones: codificado; pendiente de carga documental de observaciones.
- Territorialización reproducible 2026: pendiente de cierre.
- Resultado 2026: **no declarado auditado** hasta superar todos los controles.

## Regla de cierre
**DATOS → PARÁMETROS → CÓDIGO → TESTS → RESULTADOS → HASH/VERSIÓN.**

Si falta un dato esencial, la suma de votos no cuadra, existe contradicción, se necesita territorialidad inventada, falla una prueba o no se puede reproducir el resultado:

**DETENER → IDENTIFICAR → REGISTRAR → NO PROPAGAR.**


## INVOCACIÓN Y CONTINUIDAD DE LA COLMENA

Entrada obligatoria para cualquier IA nueva: `docs/INVOCACION_COLMENA.md`.

Estado máquina heredable: `docs/COLMENA_STATE.json`.

### Regla de reanudación
La IA nueva debe leer primero `README.md`, `CONTRATO_MAESTRO_IA.md`, `docs/INVOCACION_COLMENA.md` y `docs/COLMENA_STATE.json`, ejecutar el contrato reproducible y continuar únicamente desde `next_single_action`.

**No se reconstruye el contexto desde el chat.** El chat sirve para interacción; el repositorio contiene la memoria operativa.

### Economía de tokens
No repetir búsquedas, cálculos o auditorías ya registrados. No buscar de nuevo una fuente anclada. No narrar llamadas de herramientas. Si una comprobación ya tiene evidencia versionada, verificarla y avanzar.

### Contrato ejecutable
`src/reproducibility_contract.py` verifica contrato y ancla primaria. Debe pasar antes de modelar:

```bash
python -m src.reproducibility_contract
pytest -q tests/test_reproducibility_contract.py
```

Si falla: **DETENER**. No sustituir fuentes, parámetros, semilla ni metodología.

### Huella de continuidad
Cada cierre debe actualizar `docs/COLMENA_STATE.json` y `docs/INVOCACION_COLMENA.md` con commit, estado, errores abiertos, evidencias y **una única siguiente acción**. Un razonamiento o mensaje no persistido no se considera heredable.


## PROTOCOLO CANÓNICO DE REANUDACIÓN — NO RECONSTRUIR DESDE EL CHAT

La continuidad de la colmena está **codificada**, no confiada a memoria conversacional.

Archivos canónicos:
- `config/seec_reproducibility.json`: metodología, RNG, semilla, MC, ley electoral, OOS y reglas de invariancia.
- `src/reproducibility_contract.py`: gate ejecutable; verifica también los bytes reales de la fuente primaria.
- `src/error_registry.py`: catálogo cerrado de errores; los errores críticos bloquean.
- `src/colmena_resume.py`: arranque de contexto cero.
- `docs/COLMENA_STATE.json`: único estado máquina heredable.
- `docs/INVOCACION_COLMENA.md`: PROM mínimo de arranque y huella de continuidad.

### PROM DE ARRANQUE PARA UN CHAT NUEVO

```
LEER README.md
LEER CONTRATO_MAESTRO_IA.md
LEER docs/INVOCACION_COLMENA.md
LEER docs/COLMENA_STATE.json
EJECUTAR python -m src.colmena_resume
EJECUTAR pytest -q tests/test_reproducibility_contract.py tests/test_error_registry.py tests/test_colmena_resume.py
LEER next_single_action
EJECUTAR SOLO next_single_action
PERSISTIR checkpoint inmediatamente
NO RECONSTRUIR EL CHAT
NO REPETIR INVESTIGACIÓN YA VERSIONADA
```

### Regla de herencia

El último mensaje del chat, incluso si quedó incompleto o no llegó a enviarse, **no es estado**. Solo es heredable lo que haya quedado persistido en el repositorio.

Cada unidad de trabajo debe cerrar con:
1. commit;
2. `last_action`;
3. `last_action_result`;
4. evidencias/errores abiertos;
5. **una única** `next_single_action`.

### Regla de ahorro de tokens

Repositorio primero. Si una fuente, cálculo, hash, prueba o decisión ya está versionada y verificada, no se vuelve a investigar ni explicar. El nuevo agente debe consumir el estado y actuar sobre la siguiente acción, no volver a descubrir el proyecto.

### Regla de fuente primaria

El manifiesto no sustituye al documento. El PDF canónico debe existir como objeto binario versionado y su SHA-256 debe coincidir exactamente con:

`b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7`

Si falta el binario o cambia un solo byte: `PRIMARY_BINARY_NOT_REPOSITORY_PINNED` / `PRIMARY_HASH_MISMATCH` → **DETENER**. No buscar sustituto automáticamente.

### Regla de metodología

No se puede cambiar silenciosamente SEEC, semilla, RNG, número mínimo de simulaciones, ley electoral, ventanas OOS, umbrales de calibración, fuente primaria, reglas de desempate ni tratamiento territorial. Cualquier cambio exige nueva versión, evidencia y pruebas.


## OPERATIONAL_BETA

**Estado de producto: utilizable con transparencia; no certificado oficialmente.**

- Motor D'Hondt: verificado y determinista.
- Datos históricos/2023 disponibles: réplica secundaria verificable.
- Comparación de coaliciones y escenarios explícitos: permitida.
- Certificación estricta de fuente primaria: pendiente.
- Predicción electoral: no validada.

Los resultados beta deben mostrar siempre la procedencia secundaria y no deben presentarse como certificación oficial.

## Decision Engine MVP — uso operativo

El repositorio incluye ahora `coalicion.py` como interfaz mínima:

- `python coalicion.py audit 2023` — comprueba el estado de la cadena de auditoría y falla cerrado si falta evidencia primaria.
- `python coalicion.py coalition A B --input scenario.json` — fusiona votos por circunscripción y vuelve a ejecutar D'Hondt.
- `python coalicion.py scenario --party A --shift 2 --distribution uniform_by_province --input scenario.json` — aplica un shock de +2 puntos con territorialización explícita.
- `python coalicion.py verify certificate.json` — inspecciona el estado del certificado.

El MVP no inventa una matriz candidatura×circunscripción. La matriz 2023 completa ya está materializada como `SECONDARY_REPLICA_VERIFIED` y permite análisis reales en `OPERATIONAL_BETA`; la certificación primaria permanece bloqueada hasta reconciliarla con Interior. Esto es intencionado.

## DECISION ENGINE DE COALICIONES — V1

Implementado en `src/coalition_decision_engine.py` y `scripts/coalition_decision_engine.py`.

Calcula resultado separado, resultado coaligado con D'Hondt recalculado por circunscripción, ganancia/pérdida real, contribución de voto, votos bajo el 3%, escenarios explícitos y ponderados, probabilidad de no mejora, peor/mejor caso, ganancia esperada, dispersión y circunscripciones decisivas. La recomendación distingue máxima ganancia esperada de robustez.

Ejemplo: `python scripts/coalition_decision_engine.py --input decision_scenarios.json --parties PARTIDO_A PARTIDO_B PARTIDO_C --max-size 2 --output reports/coalition_decision.json`

El motor no inventa escenarios ni considera certificada una predicción. Si el espacio combinatorio es demasiado grande, falla cerrado en vez de muestrear coaliciones silenciosamente.
## Monitorización autónoma de encuestas

El sistema operativo de vigilancia está en `src/poll_monitor.py`, configurado por
`config/poll_monitor.json` y ejecutado por `.github/workflows/poll_monitor.yml`.

- Captura cada 5 minutos mediante GitHub Actions, con ejecución manual disponible.
- Fuentes configuradas: CIS, Electomanía, Dato Electoral, Europe Elects, MyF Data, Sigma Dos, GAD3, NC Report, Demoscopia, Celeste-Tel, Invymark y Political Stats.
- Las fuentes estructuradas se validan antes de generar una encuesta utilizable.
- RSS y páginas sin estructura reproducible quedan como **DISCOVERY_ONLY/PAGE_FINGERPRINT_ONLY**; nunca se inventan porcentajes.
- Cada captura cruda recibe SHA-256 y se conserva en `artifacts/surveys/`.
- El histórico longitudinal queda en `artifacts/survey_history.jsonl` y el estado en `artifacts/poll_monitor_state.json`.
- Telegram alerta ante encuesta validada nueva/modificada y ante el primer cambio de un fallo de fuente.
- No se convierte voto nacional en voto territorial ni en escaños. La proyección de escaños permanece bloqueada hasta disponer de matriz territorial verificable.

La documentación completa está en `docs/POLL_MONITORING.md`.

**Importante:** GitHub documenta que 5 minutos es el intervalo mínimo de los schedules, pero también que las ejecuciones programadas pueden retrasarse o incluso perderse bajo carga; por ello la latencia es *near-real-time*, no una garantía dura de cinco minutos.


## MEMORIA MAESTRA ULTRACOMPRIMIDA — COALICIÓN

> **Fuente de verdad:** este repositorio y su evidencia materializada. Esta sección es un índice operativo comprimido; no sustituye los archivos fuente.

### 0. Identidad y objetivo
- Proyecto único: `DrRomanSalvador/coalicion`, rama `main`.
- Infraestructura neutral, reusable y reproducible para auditoría electoral española, análisis territorial, simulación, predicción, incertidumbre y evaluación de coaliciones/pactos.
- No es herramienta de propaganda, persuasión, microtargeting ni optimización partidista.
- Prioridad: **evidencia > inferencia > memoria > suposición**. Evidencia crítica ausente ⇒ **FAIL_CLOSED**.

### 1. Principios
Neutralidad; reproducibilidad; trazabilidad; fuentes primarias primero; provenance/hash/manifest; no datos inventados; no imputación oculta; no información futura; no sustitución silenciosa; no overrides manuales; no optimización partidista; no convertir encuestas nacionales en escaños territoriales sin input territorial; no reconstruir votos desde escaños; no sumar escaños de partidos para coaliciones; contradicción ⇒ bloqueo; repositorio = estado persistente.

### 2. Método y pipeline
`REINA-SEEC 4.0`.
`FUENTES→DATOS→VALIDACIÓN→SESGOS→TERRITORIO→ESCENARIO→COALICIÓN→LEY_ELECTORAL→MARGINALIDAD→INCERTIDUMBRE→RESULTADO→AUDITORÍA`.
Separar observación, modelización, simulación y decisión.

### 3. Arquitectura
Boundary de datos; `electoral.py` como lógica electoral canónica/frozen; `prediction.py` estadística consolidada; coalition decision como lógica de coaliciones; `uncertainty.py` probabilística; decision como orquestación mínima; auditoría/evidencia/reproducibilidad transversales. Evitar implementaciones paralelas de `electoral_reference`, `coalition_value`, `scenarios`, `decision_engine` y motores duplicados. Una implementación canónica por concepto matemático crítico.

### 4. Ley electoral e invariantes
Congreso = **350 escaños / 52 circunscripciones**. Umbral provincial = **3% votos válidos**. D’Hondt con aritmética exacta cuando corresponda. Ceuta/Melilla = candidatura más votada. Empate absoluto ⇒ **BLOCK**, nunca desempate lexicográfico. `sum(escaños circunscripción)=magnitud`; `sum(escaños nacionales)=350`; votos/asignaciones no negativos. Coalición = **agregar votos por circunscripción → aplicar umbral → recalcular D’Hondt**, jamás sumar escaños.

### 5. Datos y evidencia
Prioridad: Ministerio del Interior → JEC → BOE → INE → otras oficiales → CIS para encuestas oficiales → privadas con procedencia. Agregadores sirven para discovery, no sustituyen fuentes primarias. Anchor/hash mismatch ⇒ hard failure. Provenance: fuente, fecha, field date si existe, publicación, hash, versión/código, seed, transformación y evidencia materializada. Distinguir Git blob SHA, SHA-256 de contenido y hash declarado por manifest.

### 6. 2023 canónico
`artifacts/data/election_2023_canonical.json` + `.sha256`. Anchor: `INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO`. SHA declarado del anchor: `b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7`.

### 7. Histórico
Elecciones de referencia: **2004, 2008, 2011, 2015, 2016, 2019A, 2019N, 2023**. Uso: backtest, validación temporal, OOS, calibración, drift y estabilidad. Prohibido usar información futura para explicar/predicir pasado.

### 8. Predicción/calibración
OOS = expanding window. Métricas: MAE, RMSE, mediana abs, máximo abs, bias y cobertura probabilística. Un candidato debe no empeorar dentro de tolerancias y mejorar estrictamente una métrica relevante OOS. Separar **observación→predicción→calibración→evaluación**; nunca calibrar con el resultado evaluado.

### 9. Incertidumbre/SEEC
RNG = NumPy PCG64; seed = **20261006**; mínimo Monte Carlo **10.000**, preferido **50.000**. Reproducibilidad = seed + versión de código + datos/hash. SEEC composicional cuando proceda; no binomios independientes para componentes dependientes; field_date; drift; house effects; conteos deterministas cuando corresponda; PyMC/PyTensor fail-closed si entorno inválido.

### 10. Sesgos/correcciones
Candidatos BASE/COMMON/PARTY/HOUSE/GOVERNMENT y combinaciones justificadas. Ninguna corrección por intuición: mejora OOS + no empeoramiento relevante. Agregación histórica sin permitir que una elección con más encuestas domine artificialmente.

### 11. Temporalidad
Distinguir publication date, field date/field_end y election date. Temporal decay explícito/reproducible. Detectar drift, envejecimiento, cambios de casa y cambios metodológicos.

### 12. Poll monitor
Estado V3: hashes, identidades, discovery hashes, source hashes, failures, failure streaks, versiones y raw bodies. Detecta `NEW` y `CORRECTION_OR_REPUBLICATION`. Raw materializado = evidencia reproducible. Diferenciar fallo de fuente/parser, ausencia de publicación y cambio estructural. No inventar valores, usar snippets como datos, nacional→territorial ni escaños sin territorialidad válida. Telegram: destino dinámico del chat privado iniciador; no hardcodear chat.

### 13. Survey watch
`config/poll_monitor.json` = universo/health/cobertura/fail-closed. `config/survey_watch.json` = frecuencia, alertas, fuentes, publicación, pollster, escenarios y Telegram. Escenarios SUMAR/PODEMOS/PSOE pueden ser descriptivos, nunca recomendaciones/rankings ni transferencias inventadas; escaños solo con territorialidad válida.

### 14. Certificación
No certificar con blocker, evidencia primaria ausente, hash mismatch, contradicción, leakage, reproducibilidad fallida, OOS/calibración pendiente cuando sea requisito, auditoría externa pendiente, ejecución productiva no demostrada o materialización no comprobada. **Certificación ≠ código aparentemente correcto**; requiere evidencia materializada y verificable.

### 15. Bloqueadores canónicos
`COLMENA_STATE_MISSING`, `COLMENA_STATE_INVALID`, `INVOCATION_MISSING`, `CONTRACT_MISSING`, `METHOD_MISMATCH`, `SEED_MISMATCH`, `SOURCE_ANCHOR_MISSING`, `SOURCE_HASH_DECLARATION_MISMATCH`, `PRIMARY_BINARY_NOT_REPOSITORY_PINNED`, `PRIMARY_HASH_MISMATCH`, `EVIDENCE_MISSING`, `EVIDENCE_STALE`, `FUTURE_INFORMATION`, `DATA_CONTRADICTION`, `REPRODUCIBILITY_FAILURE`, `PARAMETER_DRIFT`, `METHODOLOGY_DRIFT`, `UNSUPPORTED_INFERENCE`, `HIDDEN_IMPUTATION`, `COALITION_SEAT_SUMMATION`, `PARTISAN_OPTIMIZATION`, `EXTERNAL_AUDIT_UNAVAILABLE`, `UNPERSISTED_CHECKPOINT`, `MULTIPLE_NEXT_ACTIONS`, `CHAT_CONTEXT_DEPENDENCY`, `CERTIFICATION_WITH_OPEN_BLOCKER`, `PRIMARY_RECONCILIATION`, `SEEC_PRODUCTION_EXECUTION`, `OOS_CALIBRATION`, `EXTERNAL_AUDIT`, `ABSOLUTE_TIE`, `INVALID_VALID_VOTES`, `SEAT_CONSERVATION`, `UNVERSIONED_DATA`, `INVENTED_TERRITORIALITY`, `MANUAL_RESULT_OVERRIDE`, `NONDETERMINISTIC_EXECUTION`, `CI_EVIDENCE_MISSING_FOR_CONTINUITY_COMMIT`, `PRIMARY_2023_MATRIX_MATERIALIZATION`.

### 16. Reproducibilidad
Contrato = **seed + code version + data hash + config + environment**. No outputs manuales/no persistidos/no trazables ni diferencias inexplicadas. Mismos inputs+versión+seed ⇒ mismo resultado; mismas condiciones probabilísticas ⇒ misma simulación.

### 17. CI/automatización
Workflows/scripts/artifacts cubren auditoría, backtest, OOS, calibración, histórico, poll monitoring, vigilance, Telegram, materialización y certificación. CI creado ≠ PASS; test existente ≠ PASS; solo ejecución verificable puede sostener una afirmación.

### 18. Componentes conocidos
Top-level: README, contratos/guías, DATA_PIPELINE, LIMITATIONS, OPERATIONAL_BETA, QUICKSTART, REPRODUCIBILITY, `cli.py`, `coalicion.py`, `political_product.py`, `run26.py`, requirements. Docs: arquitectura, auditoría maestra, bibliografía, estado Colmena, contrato producto, errores, política exhaustiva, histórico, invocación, poll monitoring, prompts, sesgos, SEEC, sources/status, Telegram, test plan. SRC: auditoría, bias, calibration, coalition, data, electoral, evidence, OOS, polls, prediction, probabilistic calibration, reconciliation, reproducibility, SEEC, temporalidad, uncertainty y monitores CIS/dato/electomanía/Twitter. Scripts: adquisición, auditoría, backtest, OOS, calibración, materialización, validación, certificación, ingestión, Telegram y queen/worker.

### 19. Política de fuentes
`config/electoral_sources.json`: Interior/JEC/BOE/INE según dato; CIS para encuestas oficiales; privados con procedencia; Electomanía principalmente discovery. Fecha correcta de elecciones generales 2023 = **2023-07-23**. No synthetic, no territorial inference, no seat→vote inversion.

### 20. Operational Beta
`config/operational_beta.json`: `OPERATIONAL_BETA`; strict certification unchanged; réplica secundaria solo con manifest+consistencia+warning; uso parcial permitido; `prediction_certified=false` mientras falte evidencia.

### 21. Colmena
`queen=coordinator`; workers especializados reportan hallazgos; no modificaciones arbitrarias cuando el contrato exige coordinación. Repositorio = estado persistente. Conversación incompleta ≠ checkpoint. Múltiples siguientes acciones ambiguas ⇒ bloqueo.

### 22. Lectura exhaustiva
Protocolo: **refresh tree → inventory → path+SHA → leer legibles → no releer path+SHA estable → releer SHA cambiado → añadir nuevos → refresh antes de declarar fin → repetir hasta cero pendientes legibles**. Último estado conocido durante esta continuidad: **728 blobs; 272 text/code/config cubiertos; 16 extras cubiertos; 357 raw actuales; 45 raw cubiertos en último contador; 77 pyc binarios identificados/no fuente-readable; lectura entonces no terminada**. Identificado ≠ leído; fetch ≠ comprensión exhaustiva; workflow ≠ ejecución; test ≠ PASS; hash declarado ≠ verificado; código correcto ≠ certificado.

### 23. Estados de evidencia
Distinguir siempre: **IMPLEMENTADO / TESTEADO / EJECUTADO / VALIDADO / OOS / CALIBRADO / MATERIALIZADO / AUDITADO / CERTIFICADO**. Nunca colapsarlos en “hecho”.

### 24. Intervenciones futuras
“Termina” ⇒ continuar desde estado real, refresh, resolver bloqueos, ejecutar, persistir evidencia, verificar, no sobreafirmar. “Lee todo” ⇒ refresh→inventory→diff→read→update→refresh. “Corrige todo” ⇒ diagnose→patch→test→integration→evidence→refresh→verify. Incertidumbre ⇒ STOP/preguntar salvo contrato inequívoco.

### 25. Compresión de memoria
**MEMORIA = MAPA; REPOSITORIO = CONTENIDO COMPLETO.** Memorizar arquitectura, invariantes, contratos, decisiones, fuentes, hashes críticos, metodología, blockers, estado, frontera de lectura y reglas de continuidad; no logs/código/raw completos. La memoria debe permitir saber qué es el sistema, cómo funciona, qué está prohibido, qué está demostrado, qué falta, dónde continuar y cómo evitar repetición/contradicción.

### 26. Regla maestra
**REFRESH → DIFF(path+SHA) → READ(new/changed) → EXTRACT(invariants/evidence/state) → UPDATE(compact-memory) → VERIFY → REFRESH → REPEAT**.
Solo STOP cuando **árbol estable + cero pendientes legibles + ningún blocker abierto que impida la afirmación realizada**.

> **Principio final:** nunca decir “terminado” porque el modelo lo recuerde; decir “terminado” solo porque la evidencia del repositorio lo demuestre.

## Telegram bot (fail-closed)

The repository includes `src/telegram_bot.py`, a lightweight long-poll command bot using the existing `requests` dependency.

Run with:

    export TELEGRAM_BOT_TOKEN='...'
    python -m src.telegram_bot

Commands: `/prediccion`, `/encuestas`, `/estado`, `/ayuda`.

`/prediccion` shows seats only when `artifacts/decision_snapshot.json` exists and contains an explicit materialized territorial projection; otherwise it reports BLOCKED. `/encuestas` reads validated observations persisted by the poll monitor. Replies are sent to the same Telegram chat ID that issued the command.

The bot does not contain hard-coded polling, seat projections, probabilities, MAE, coverage or political recommendations. Predictive methodology extensions under `src/models/` remain optional candidates and are not promoted to production without the repository's OOS, calibration and leakage gates.


## MVP vendible — estado operativo

La superficie no-Telegram del MVP está materializada en:

- src/web/dashboard.py: dashboard Streamlit para usuario político.
- api.py: estado, encuestas, evidencia y demo JSON.
- src/email/newsletter.py: newsletter determinista y envío SMTP opcional.
- render.yaml: API + dashboard con plan gratuito.
- .github/workflows/mvp-validation.yml: compilación, tests y materialización de newsletter.
- ci_evidence/mvp_product_checkpoint.json: punto de reanudación.

Regla: el MVP no convierte encuestas nacionales en observaciones territoriales ficticias. Cuando falta evidencia territorial suficiente, muestra NO DISPONIBLE.

Telegram queda deliberadamente fuera de esta iteración para evitar conflictos con el trabajo concurrente del otro agente.


## Análisis de decisiones de la demo 2023

Ejecuta `python scripts/demo_decision_analysis.py` para generar el registro auditable `artifacts/demo_decision_analysis_2023.json` y el informe ejecutivo `reports/demo_decision_analysis_2023.md`. Reutiliza `src.electoral.allocate`, explica cambios de escaños y cocientes marginales y calcula fronteras matemáticas con votos rivales fijos. No modela transferencias ni es una predicción. Consulta `DECISION_ANALYSIS_USAGE.md`.
