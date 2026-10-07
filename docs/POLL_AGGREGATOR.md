# Agregador de encuestas reproducible

Este módulo implementa, como componentes configurables y auditables, las técnicas públicas de la metodología de Kiko Llaneras que son suficientemente documentables:

- combinación de encuestas;
- peso por tamaño muestral;
- peso por recencia;
- historial de precisión de la casa;
- corrección de efecto de casa con shrinkage;
- penalización de repetición de una misma casa;
- exclusión de encuestas demasiado antiguas;
- separación estricta entre fecha de corte y datos futuros;
- trazabilidad de cada peso y corrección;
- intervalo descriptivo basado en dispersión observada.

No se presentan los parámetros por defecto como una reproducción exacta de los parámetros internos de Llaneras. Son una implementación explícita y reproducible de la estructura metodológica pública. Los parámetros que deban considerarse fieles deben calibrarse contra fuentes documentadas y validarse OOS.

## Activación

El agregador no debe sustituir automáticamente al baseline de predicción. La activación exige:

1. archivo de encuestas con party, house, estimate_pct, field_end, sample_size y poll_id;
2. histórico de errores con corte temporal correcto;
3. backtest por elecciones completas, sin fuga temporal;
4. comparación contra baseline_persistence_2019N;
5. métricas de voto, escaños y cobertura/calibración;
6. mejora estable, no solo una victoria en 2023.

Si faltan fichas técnicas o tamaños muestrales, el pipeline no los inferirá.

## Distinción metodológica

El método público de Llaneras documenta además proyección territorial desde resultados anteriores y simulación D'Hondt. Eso ya existe en COALICIÓN, pero el agregador debe alimentar la capa territorial sin alterar el reparto electoral exacto.

MRP y fundamentals no se activan porque no hay evidencia suficiente en las fuentes revisadas para atribuirlos a su modelo publicado.
