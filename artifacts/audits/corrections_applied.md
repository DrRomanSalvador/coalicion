# Correcciones aplicadas

## Consolidación arquitectónica
- Cuatro módulos estadísticos fusionados realmente en `src/prediction.py`.
- Cuatro implementaciones paralelas eliminadas.
- Sin wrappers hacia los módulos antiguos.
- `src/seec_bayesian.py`, `tests/test_seec_bayesian.py`, `src/coalition.py` y `src/electoral.py` permanecen protegidos.

## Bugs funcionales corregidos

### Cambio electoral
Antes:
`new.poll - old.actual`

Ahora:
`new.poll - old.poll`

Y:
`change_error = poll_change - actual_change`.

### Descomposición de movimiento
Antes mezclaba la encuesta actual con el resultado anterior.

Ahora:
`observed_change = new.poll - old.poll`.

### OOS
`min_train_elections` ahora cuenta elecciones únicas, no número bruto de observaciones.

## Tests de regresión
`tests/test_prediction.py` contiene pruebas explícitas para los tres casos anteriores.

## Estado de validación

Los cambios están demostrados por revisión de código y regresiones diseñadas. No se declara CI PASS: no existe ejecución de workflow asociada al commit actual. El backtest histórico completo también queda pendiente.
