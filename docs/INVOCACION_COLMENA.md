# INVOCACIÓN — ESTADO HEREDABLE DE LA COLMENA

## PROM DE ARRANQUE — NO RECONSTRUIR

**ÚNICA FUENTE DE CONTINUIDAD:** `docs/COLMENA_STATE.json`. El chat no es almacenamiento de estado.
1. Leer `README.md`, `CONTRATO_MAESTRO_IA.md`, este archivo y `docs/COLMENA_STATE.json`.
2. Ejecutar `python -m src.colmena_resume`.
3. Ejecutar `python -m src.reproducibility_contract`.
4. Ejecutar `pytest -q tests/test_reproducibility_contract.py tests/test_error_registry.py tests/test_colmena_resume.py`.
5. Leer `next_single_action` del estado.
6. Ejecutar únicamente esa acción.
7. Persistir inmediatamente `last_action`, resultado, commit y una sola `next_single_action`.
8. Si código, estado o evidencia discrepan: DETENER y registrar contradicción; no reconstruir desde el chat.

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


## HUELLA CANÓNICA ACTUAL

Último checkpoint persistido: `0e30da0742f871f31e2357da1424a340e03703d3`.
Estado: **BLOCKED / FAIL-CLOSED**.
La verificación del hash ahora exige los **bytes reales** del PDF; el manifiesto por sí solo no puede pasar.
No se ha certificado el sistema: permanecen bloqueos explícitos en fuente binaria, reconciliación primaria, ejecución SEEC, calibración OOS y auditoría externa.
Siguiente acción única: fijar el PDF binario con SHA-256 `b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7`.

**Regla de mensaje incompleto:** si una IA muere, se queda sin tokens o termina una respuesta a mitad, se ignora cualquier intención no persistida. El siguiente agente ejecuta el estado del repositorio y no vuelve a pensar lo ya resuelto.


## HUELLA DE PRODUCTO — CHECKPOINT ACTUAL

Último checkpoint persistido: b96d87f924546c4a9ffe24349a8ed7214cef7b8f.
Estado: SELLABLE_BETA / READY_FOR_EXTERNAL_AUDIT.
Gate comercial materializado: ci_evidence/product_release_gate.json = SELLABLE_BETA.
SEEC, MC, OOS y cobertura de fuentes tienen evidencia PASS; auditoría externa permanece abierta.

### PROM MÍNIMO PARA CUALQUIER CHAT NUEVO

REPOSITORIO = MEMORIA.
CHAT = INTERFAZ.

1. Leer README.md.
2. Leer CONTRATO_MAESTRO_IA.md.
3. Leer docs/INVOCACION_COLMENA.md.
4. Leer docs/COLMENA_STATE.json.
5. Ejecutar: python -m src.colmena_resume
6. Ejecutar los tests canónicos indicados por la invocación.
7. Tomar únicamente docs/COLMENA_STATE.json.next_single_action.
8. Ejecutar esa acción y ninguna otra acción paralela.
9. Persistir resultado, evidencia, commit y una única next_single_action.
10. Detenerse.

No buscar de nuevo fuentes ancladas. No repetir cálculos ya evidenciados. No usar memoria del chat para reconstruir estado.

Siguiente acción única: desplegar el blueprint Render y materializar una URL pública verificable.
