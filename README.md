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
