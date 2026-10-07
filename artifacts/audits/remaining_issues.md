# Deficiencias restantes

## Alta prioridad

1. Ejecutar la suite completa en CI sobre el commit actual.
2. Ejecutar el pipeline histórico OOS con dataset trazable.
3. Comparar resultados antes/después con inputs idénticos.

## Media prioridad

4. Auditar específicamente la política de redondeo de votos escalados: `round(voto * factor)`. No se ha demostrado que sea un bug.
5. Ampliar el inventario de APIs protegidas contra duplicación.
6. Verificar trazabilidad de datos históricos.

## Ya corregido y cubierto por regresión

- contexto de gobierno en entrenamiento;
- cálculo de cambio encuesta→encuesta;
- descomposición de movimiento;
- conteo de elecciones únicas en `min_train_elections`;
- prevención de uso de futuro en OOS;
- invariantes arquitectónicas y matemáticas.

## Restricciones

No reintroducir implementaciones paralelas de D'Hondt, coaliciones o predicción.
No modificar SEEC ni `electoral.py` en esta fase.

## Cierre realista

**Bugs identificados y reproducibles:** corregidos y cubiertos por regresiones.  
**CI completo:** pendiente.  
**Backtest/OOS histórico:** pendiente.  
**Política de redondeo:** pendiente de auditoría, no clasificada como bug.  
**Certificación electoral externa:** pendiente.
