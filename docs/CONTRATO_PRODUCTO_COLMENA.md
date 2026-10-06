# CONTRATO DE PRODUCTO — COLMENA DE COALICIÓN

## Propósito
La Colmena es un sistema reproducible de análisis de escenarios de coalición. Su memoria operativa vive en el repositorio, no en una conversación.

## Garantías del producto
1. Determinismo: misma versión, datos, parámetros y semilla producen la misma salida.
2. Fail-closed: una fuente, evidencia, regla o estado inválido bloquea.
3. Trazabilidad: cada resultado debe identificar código, datos, hashes, parámetros y semilla.
4. Continuidad: una nueva sesión arranca desde COLMENA_STATE y ejecuta una sola next_single_action.
5. Economía de tokens: no se repite trabajo ya certificado.
6. Neutralidad: compara escenarios definidos; no optimiza poder para una organización política.
7. No sustitución: una fuente anclada nunca se reemplaza automáticamente.
8. Checkpoint atómico: ningún avance cuenta como heredable hasta persistirse.

## Superficie canónica
- README.md: entrada humana.
- CONTRATO_MAESTRO_IA.md: normas inviolables.
- docs/INVOCACION_COLMENA.md: PROM de arranque.
- docs/COLMENA_STATE.json: estado máquina único.
- config/seec_reproducibility.json: configuración canónica.
- src/reproducibility_contract.py: gate de reproducibilidad.
- src/colmena_resume.py: gate de contexto cero.
- src/error_registry.py: errores cerrados.
- docs/ERRORES_CANONICOS.md: catálogo legible.
- tests/: pruebas ejecutables.

## Ciclo de vida de una acción
READ STATE → VERIFY CONTRACT → EXECUTE ONE ACTION → TEST → PERSIST EVIDENCE → UPDATE STATE → COMMIT → STOP.

## Regla de caída
Si una sesión termina, se queda sin tokens o pierde conexión, no se intenta reconstruir lo no persistido. La siguiente sesión ejecuta el gate y continúa desde el único checkpoint registrado.

## Criterio de producto
No se declara READY/CERTIFIED por la existencia del código. Se exige evidencia ejecutada para cada garantía y no puede existir ningún BLOCKER abierto.
