# HISTÓRICO ELECTORAL PARA VALIDACIÓN

Este archivo registra las elecciones generales que deben poder participar en el
backtesting histórico. La existencia de una elección en este registro NO implica
que sus encuestas ya estén incorporadas.

## Regla

Una elección solo entra en una validación OOS cuando existen:
1. fecha de campo de cada encuesta;
2. casa;
3. partido/candidatura normalizada;
4. estimación publicada;
5. resultado oficial comparable;
6. correspondencia documentada entre etiquetas históricas y actuales.

No se imputan encuestas ni se reconstruyen porcentajes desde escaños.

## Elecciones objetivo

2004, 2008, 2011, 2015, 2016, 2019-04, 2019-11 y 2023.

La JEC mantiene el listado oficial de elecciones generales y sus resultados; para
2016 el BOE publica expresamente cuadros por candidaturas, votos válidos y
escaños, y para 2019 la JEC/BOE publica los resultados conforme a las actas
oficiales.

## Uso

El histórico se usa para probar si una corrección funciona repetidamente, no para
forzar una corrección.

Una corrección solo puede pasar a producción si mejora el modelo base en ventanas
OOS temporales y no degrada las métricas conjuntas preregistradas.

Si una elección carece de datos comparables, se excluye de esa prueba concreta y
se registra la exclusión; no se rellena.
