# Plan mínimo de pruebas

## Estructura
- 52 circunscripciones.
- 350 diputados.
- Magnitudes 2026 suman 350.
- Ceuta y Melilla tienen 1 cada una.

## Ley electoral
- Umbral provincial del 3%.
- Frontera exactamente 3%.
- D'Hondt sin redondeo.
- Desempate por votos totales.
- Empate absoluto no resuelto arbitrariamente.
- Ceuta/Melilla por mayoría.

## Datos
- Conservación de votos.
- Ausencia de duplicados.
- Matriz partido×circunscripción validada contra fuente oficial.
- Candidaturas nuevas sin territorialidad inventada.

## Modelado
- Coaliciones/fusiones antes de D'Hondt.
- Separación observado/imputado/supuesto/escenario.
- No inversión escaños→porcentajes.
- No corrección de encuesta sin backtesting OOS.
- Determinismo.

## Cierre
No se declara cerrado el modelo 2026 hasta automatizar todos los controles esenciales y disponer de las fuentes oficiales necesarias.


## Ejecución actual
La auditoría de código se complementa con pruebas ejecutables del núcleo electoral. Se exige cobertura de:
- validación de entradas;
- umbral exacto y por debajo del 3%;
- cocientes D'Hondt;
- empate de cociente resuelto por votos;
- empate absoluto bloqueado;
- Ceuta y Melilla;
- fusión a nivel de votos;
- conservación de escaños;
- determinismo;
- estructura oficial 52/350 y magnitudes críticas.

La ausencia de `run26.py` en el repositorio actual impide certificar un archivo con ese nombre.

## Criterio de evidencia
PASS solo si existe fuente primaria, prueba ejecutable o ambas. Ausencia de evidencia se marca NO DEMOSTRADO, nunca PASS por inferencia.
