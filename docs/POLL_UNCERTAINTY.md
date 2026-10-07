# Incertidumbre de encuestas

La predicción no debe tratar el promedio de sondeos como un punto exacto. Este módulo
separa la estimación central de la incertidumbre histórica.

Implementa:

- error histórico por partido;
- error histórico por distancia al día electoral;
- RMSE/MAE para calibrar magnitudes;
- sigma explícito por partido y horizonte temporal;
- intervalos 50/80/90/95;
- medición OOS de cobertura.

El componente de error común se mantiene explícito para representar correlación entre
encuestas. No se presenta como un parámetro “exacto de Llaneras”: debe calibrarse con
datos históricos y compararse OOS.

Regla de producto: ninguna cobertura se considera calibrada por el hecho de generar
un intervalo. La cobertura 50/80/90/95 debe medirse sobre elecciones no utilizadas
para estimar los parámetros.
