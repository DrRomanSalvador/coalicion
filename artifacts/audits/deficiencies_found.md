# Informe de deficiencias encontradas

**Agente:** Auditor 3  
**Rama:** `refactor/minimal-domain-architecture`  
**Actualización:** 2026-10-07

## Deficiencias y correcciones verificadas

### 1. Duplicidad arquitectónica
Se eliminaron ocho módulos paralelos:
- `bias_filter.py`
- `calibration.py`
- `poll_error.py`
- `context_corrections.py`
- `coalition_value.py`
- `scenarios.py`
- `decision_engine.py`
- `electoral_reference.py`

La lógica estadística quedó consolidada en `src/prediction.py`; `electoral.py` y `coalition.py` permanecen como fuentes de verdad protegidas.

### 2. Bug contextual
La implementación antigua podía usar el gobierno de la observación objetivo al evaluar las filas de entrenamiento. La implementación consolidada construye la clave de cada fila de entrenamiento con sus propios metadatos.

**Corrección:** aplicada.

### 3. Bug de cambio encuesta→encuesta
`change_vs_previous_election()` calculaba:
`poll_change = encuesta_actual - resultado_real_anterior`.

Eso mezcla magnitudes distintas. La definición correcta es:
`poll_change = encuesta_actual - encuesta_anterior`.

**Corrección:** aplicada y cubierta por regresión con caso 40→45 de encuesta y 42→44 de resultado.

### 4. Bug equivalente en descomposición de movimiento
`decompose_movement()` repetía la misma mezcla entre encuesta actual y resultado anterior.

**Corrección:** aplicada: `observed_change = new.poll - old.poll`.

### 5. Bug de `min_train_elections`
`expanding_oos()` interpretaba el parámetro como número de filas, aunque su nombre y contrato indican número de elecciones.

**Corrección:** ahora cuenta elecciones únicas y registra también la tupla de elecciones realmente usadas.

### 6. Redondeo de votos
`round(voto * factor)` se conserva. No hay evidencia suficiente para declararlo bug ni para cambiarlo sin alterar resultados electorales potenciales.

## Evidencia de regresión

Se añadieron pruebas que demuestran:
- el cambio encuesta→encuesta correcto;
- la descomposición de movimiento coherente;
- `min_train_elections` cuenta elecciones, no encuestas duplicadas;
- no se usa información futura;
- las invariantes arquitectónicas y matemáticas existentes permanecen protegidas.

## Límites

La corrección de estos bugs queda demostrada por inspección estática + regresiones diseñadas. La ejecución completa de CI y un backtest histórico OOS siguen siendo necesarios para certificar el comportamiento global.

No se certifican resultados electorales ni predicciones políticas.
