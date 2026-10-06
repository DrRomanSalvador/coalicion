# INVOCACIÓN — ESTADO HEREDABLE DE LA COLMENA

## Propósito
Este archivo es el checkpoint de arranque para cualquier IA nueva. Evita reconstruir por conversación lo que ya está codificado.

## Economía de tokens
- El repositorio es la memoria operativa primaria; el chat no lo es.
- No rehacer análisis registrados.
- No volver a buscar una fuente si existe un ancla local con hash válido.
- No pedir al usuario información ya presente.
- Ejecutar, verificar y registrar; no narrar llamadas de herramientas.
- Un mensaje no enviado o un razonamiento no persistido **no es estado heredable**.
- Al cerrar una tarea, persistir siempre estado, errores abiertos, último commit y siguiente acción única.

## Contrato determinista
- Metodología: SEEC.
- Cadena: FUENTES → DATOS → VALIDACIÓN → SESGOS → TERRITORIO → ESCENARIO → COALICIÓN → LEY ELECTORAL → MARGINALIDAD → INCERTIDUMBRE → RESULTADO → AUDITORÍA.
- RNG: NumPy PCG64.
- Semilla canónica: 20261006.
- Monte Carlo mínimo: 10.000; preferencia 50.000+ cuando sea viable.
- Fail-closed: contradicción, ausencia esencial, hash incorrecto o resultado no reproducible bloquea.
- No cambiar metodología, semilla o parámetros sin cambio versionado y backtest OOS.
- La misma versión de código + mismos datos + mismos parámetros + misma semilla debe producir la misma salida.

## Estado máquina
Fuente de verdad estructurada: `docs/COLMENA_STATE.json`.
Ese archivo contiene el estado, errores bloqueantes, trabajos completados, último punto verificado y **una sola siguiente acción**.

## Ancla primaria
`data/source_anchors/INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.json`
- source_id: `INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO`
- SHA-256 del documento original: `b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7`
- Si falta el ancla o su hash declarado no coincide: DETENER. No sustituirla automáticamente.
- Importante: el manifiesto fija la identidad criptográfica del PDF; el binario original aún debe incorporarse a un almacenamiento binario versionado para que el repositorio conserve también los bytes originales.

## Punto exacto de ejecución
1. Contrato reproducible: `src/reproducibility_contract.py`.
2. Prueba: `tests/test_reproducibility_contract.py`.
3. Ancla: `data/source_anchors/INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.json`.
4. Estado heredable: `docs/COLMENA_STATE.json`.
5. La certificación global permanece bloqueada hasta superar los gates registrados en el estado.
6. **Siguiente acción única:** verificar el estado real de CI para el contrato reproducible; si no existe evidencia verificable para el commit registrado, ejecutar la suite y registrar el resultado. Después, continuar con el primer error bloqueante, sin repetir investigación ya cerrada.

## Arranque de un chat nuevo
1. Leer `README.md`.
2. Leer `CONTRATO_MAESTRO_IA.md`.
3. Leer `docs/INVOCACION_COLMENA.md`.
4. Leer `docs/COLMENA_STATE.json`.
5. Ejecutar `python -m src.reproducibility_contract`.
6. Ejecutar `pytest -q tests/test_reproducibility_contract.py`.
7. Continuar **solo** desde `next_single_action`.
8. Si el estado y el código discrepan, detener y registrar la contradicción; no reconstruirla por memoria del chat.

## Última huella
- Checkpoint anterior: `a05043c009996e981ebfe2ec5d93118dfa592b65`.
- Nuevo estado persistido: `ab31768ef7e3341d29113dfd4d28129dd9663524`.
- Estado: **CONTRATO DE CONTINUIDAD CODIFICADO; CERTIFICACIÓN GLOBAL BLOQUEADA**.
- Objetivo: que metodología, estado, errores y punto de reanudación sobrevivan al cambio de conversación sin depender de memoria del modelo.
