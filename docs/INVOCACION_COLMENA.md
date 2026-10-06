# INVOCACIÓN — ESTADO HEREDABLE DE LA COLMENA

## Propósito
Este archivo es el checkpoint de arranque para cualquier IA nueva. Evita reconstruir por conversación lo que ya está codificado.

## Economía de tokens
No rehacer análisis registrados. No volver a buscar una fuente si existe un ancla local con hash válido. No pedir al usuario información ya presente. Ejecutar, verificar y registrar; no narrar cada llamada de herramienta.

## Contrato determinista
- Metodología: SEEC.
- Cadena: FUENTES → DATOS → VALIDACIÓN → SESGOS → TERRITORIO → ESCENARIO → COALICIÓN → LEY ELECTORAL → MARGINALIDAD → INCERTIDUMBRE → RESULTADO → AUDITORÍA.
- RNG: NumPy PCG64.
- Semilla canónica: 20261006.
- Monte Carlo mínimo: 10.000; preferencia 50.000+ cuando sea viable.
- Fail-closed: contradicción, ausencia esencial, hash incorrecto o resultado no reproducible bloquea.
- No cambiar metodología, semilla o parámetros sin cambio versionado y backtest OOS.

## Ancla primaria
`data/source_anchors/INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.json`
- source_id: `INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO`
- SHA-256 del documento original: `b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7`
- Si falta el ancla o su hash declarado no coincide: DETENER. No sustituirla automáticamente.

## Punto exacto de ejecución
1. Manifiesto de fuente ancla y README del ancla: versionados.
2. Contrato reproducible: codificado en `src/reproducibility_contract.py`.
3. Prueba del contrato: `tests/test_reproducibility_contract.py`.
4. Siguiente paso obligatorio: integrar el contrato en CI/master gate y ejecutar la suite.
5. Después: checkpoint JSON por commit con pruebas, estado y siguiente paso único.
6. Certificación global sigue bloqueada hasta fuente primaria reconciliada, SEEC completo, calibración OOS y auditoría externa real.

## Arranque de un chat nuevo
1. Leer `README.md`.
2. Leer `CONTRATO_MAESTRO_IA.md`.
3. Leer este archivo.
4. Leer `docs/REGISTRO_MAESTRO_SESGOS.md` antes de tocar correcciones.
5. Comprobar `main` y ejecutar `python -m src.reproducibility_contract`.
6. Ejecutar la prueba mínima.
7. Continuar solo desde el siguiente paso no completado. Nunca empezar de cero.

## Última huella
Estado: IMPLEMENTACIÓN DEL CONTRATO DE CONTINUIDAD EN CURSO.
Objetivo: que metodología, estado y punto de reanudación sobrevivan al cambio de conversación sin depender de memoria del modelo.