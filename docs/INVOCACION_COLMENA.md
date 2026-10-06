# INVOCACIÓN — ESTADO HEREDABLE DE LA COLMENA

## PROM DE ARRANQUE — NO RECONSTRUIR
1. Leer `README.md`, `CONTRATO_MAESTRO_IA.md`, este archivo y `docs/COLMENA_STATE.json`.
2. Ejecutar `python -m src.reproducibility_contract`.
3. Ejecutar `pytest -q tests/test_reproducibility_contract.py`.
4. Leer `next_single_action` del estado.
5. Ejecutar únicamente esa acción.
6. Persistir inmediatamente `last_action`, resultado, commit y una sola `next_single_action`.
7. Si código, estado o evidencia discrepan: DETENER y registrar contradicción; no reconstruir desde el chat.

## CONTRATO DETERMINISTA
- Metodología única: SEEC.
- Cadena: FUENTES → DATOS → VALIDACIÓN → SESGOS → TERRITORIO → ESCENARIO → COALICIÓN → LEY ELECTORAL → MARGINALIDAD → INCERTIDUMBRE → RESULTADO → AUDITORÍA.
- RNG: NumPy PCG64.
- Semilla canónica: 20261006.
- Monte Carlo mínimo: 10.000; preferencia 50.000+.
- Misma versión + mismos datos + mismos parámetros + misma semilla = misma salida.
- Fail-closed ante ausencia, contradicción, hash incorrecto, no reproducibilidad o evidencia insuficiente.
- Ninguna corrección metodológica sin validación OOS predefinida.

## ANCLA PRIMARIA
`data/source_anchors/INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.json`
SHA-256: `b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7`
Hash incorrecto o ancla ausente = DETENER. No buscar sustitutos automáticamente.
El manifiesto fija la identidad; el PDF binario aún debe fijarse en almacenamiento versionado.

## ECONOMÍA DE TOKENS
- Repositorio primero.
- No repetir búsquedas/cálculos/auditorías ya evidenciados.
- No volver a buscar una fuente anclada.
- No narrar herramientas.
- No pedir información ya presente.
- Un razonamiento o mensaje no enviado no es estado heredable.
- Cada unidad de trabajo termina en checkpoint persistido.
- El estado máquina prevalece sobre memoria conversacional.

## ÚLTIMA HUELLA
Checkpoint verificado: `d86b037d37ed63a1293583c60c931cef48c9171a`.
CI del checkpoint anterior `ab31768ef7e3341d29113dfd4d28129dd9663524`: cero estados registrados; **INCONCLUSO**, nunca PASS.
Estado global: **BLOCKED / FAIL-CLOSED**.
Última acción: verificación del checkpoint, contrato, ancla y estado CI; después se persistió el estado máquina actualizado.
Siguiente acción única: materializar y fijar los bytes originales del PDF en almacenamiento binario versionado y registrar identificador inmutable + SHA-256.
