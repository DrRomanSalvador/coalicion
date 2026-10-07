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

## Estado actual
- Contrato maestro: incorporado.
- Magnitudes oficiales 2026: incorporadas.
- Motor electoral: incorporado y endurecido en modo fail-closed.
- Tests legales básicos: incorporados; ejecución aislada del núcleo verificada.
- Filtro OOS anti-sesgos: en esta versión.
- Matriz oficial completa candidatura×circunscripción 2023: pendiente de ingestión automática y validación reproducible.
- Analizador reproducible de error encuesta→resultado desde 2004: incorporado.
- Esquema de datos históricos 2004–2023: incorporado; carga de observaciones documentadas pendiente de consolidación completa.
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
