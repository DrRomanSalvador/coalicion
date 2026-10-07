# Informe de deficiencias encontradas

**Agente:** Auditor 3  
**Rama auditada:** `refactor/minimal-domain-architecture`  
**Commit de referencia:** `e98150e`  
**Fecha:** 2026-10-07

## Resumen ejecutivo

La auditoría encontró **8 módulos que representaban duplicidad arquitectónica**: cuatro módulos estadísticos separados y cuatro módulos que reproducían lógica de predicción electoral/coalición ya existente.

La corrección aplicada concentra la lógica estadística en `src/prediction.py` y elimina las implementaciones paralelas. El objetivo es reducir el número de lugares donde una regla puede divergir y facilitar la auditoría futura.

**Impacto cuantificado**
- **8 archivos de implementación eliminados** por fusión o duplicidad.
- **4 dominios estadísticos** pasan a una única fuente de código: error, calibración, filtros/sesgos y correcciones contextuales.
- **3 invariantes arquitectónicos** protegen la unicidad de D'Hondt, coaliciones y predicción.
- **4 invariantes matemáticos** documentan conservación de escaños, conservación de votos al combinar, y la diferencia entre sumar votos y recalcular escaños.
- La rama protegida del Agente 3 **no modifica** `src/seec_bayesian.py`, `tests/test_seec_bayesian.py`, `src/coalition.py` ni `src/electoral.py`.

## 1. Duplicidades encontradas

### 1.1 Predicción estadística fragmentada

Existían cuatro módulos independientes:

- `src/bias_filter.py`
- `src/calibration.py`
- `src/poll_error.py`
- `src/context_corrections.py`

Su separación hacía posible que métricas, correcciones o reglas de validación evolucionaran de forma distinta.

**Corrección:** código integrado realmente en `src/prediction.py`; los cuatro archivos originales fueron eliminados.

### 1.2 Lógica de coaliciones y escenarios repetida

Se identificaron:

- `src/coalition_value.py`
- `src/scenarios.py`
- `src/decision_engine.py`

La arquitectura definida por el proyecto reserva `src/coalition.py` como fuente de verdad de la calculadora de coaliciones.

**Corrección:** se eliminaron los tres módulos paralelos sin modificar `src/coalition.py`.

### 1.3 Segunda implementación de D'Hondt

`src/electoral_reference.py` reproducía lógica de asignación electoral que debe tener una única fuente en `src/electoral.py`.

**Corrección:** eliminación de `electoral_reference.py` y actualización de los tests que dependían de esa referencia.

## 2. Deficiencias funcionales identificadas

### 2.1 Correcciones contextuales

La lógica contextual necesitaba agrupar por el contexto real de cada observación. El análisis anterior identificó un riesgo en el tratamiento del gobierno: usar el gobierno de la observación objetivo para representar todo el grupo de entrenamiento podía mezclar contextos históricos distintos.

La versión consolidada calcula el contexto a partir de cada fila de entrenamiento mediante sus propios metadatos.

**Impacto:** evita atribuir a un mismo contexto observaciones históricas que pertenecen a gobiernos diferentes.

### 2.2 Redondeo de votos

La transformación de votos utiliza redondeo entero al aplicar factores de participación:

`round(voto × factor)`

Esto conserva la semántica existente durante la simplificación, pero **no debe presentarse como un bug demostrado y corregido por esta auditoría**. El comportamiento requiere una validación específica si se pretende cambiar la política de redondeo.

**Pendiente recomendado:** comparar redondeo convencional, truncamiento y métodos de conservación de suma antes de modificarlo.

### 2.3 Validación fuera de muestra

La arquitectura consolidada contiene validación temporal OOS y exige una ventana entrenable antes de aceptar candidatos.

Esto reduce el riesgo de elegir una corrección porque mejora sobre los mismos datos utilizados para construirla.

**Pendiente:** ejecutar el pipeline completo con datos históricos documentados y comprobar resultados OOS en CI.

## 3. Deficiencias de arquitectura

El problema principal no era solamente el número de archivos: era la existencia de varias posibles fuentes de verdad.

Una futura modificación podía cambiar:
- la predicción en un módulo,
- la calibración en otro,
- la lógica contextual en un tercero,
- y dejar consumidores utilizando una implementación distinta.

La nueva arquitectura fuerza:

`electoral.py → D'Hondt`  
`coalition.py → coaliciones`  
`prediction.py → predicción estadística`

## 4. Tests creados

`tests/test_architecture_invariants.py` comprueba:

1. No existen los módulos eliminados.
2. Solo `electoral.py` define D'Hondt.
3. Solo `coalition.py` define las funciones de coalición seleccionadas.
4. Solo `prediction.py` define la API estadística seleccionada.
5. La asignación conserva el número de escaños.
6. Las participaciones suman uno.
7. La combinación de votos conserva el total.
8. Los escaños de una coalición se recalculan; no se obtienen sumando escaños individuales.

## 5. Archivos eliminados

**Por fusión estadística**
- `src/bias_filter.py`
- `src/calibration.py`
- `src/poll_error.py`
- `src/context_corrections.py`

**Por duplicidad**
- `src/coalition_value.py`
- `src/scenarios.py`
- `src/decision_engine.py`
- `src/electoral_reference.py`

**Total: 8 archivos de implementación.**

## 6. Archivos protegidos

No forman parte del trabajo del Agente 3:

- `src/seec_bayesian.py`
- `tests/test_seec_bayesian.py`
- `src/coalition.py`
- `src/electoral.py`

## 7. Recomendaciones para otros auditores

### Para auditoría funcional
Comprobar que los resultados antes y después de la simplificación son equivalentes cuando se usan exactamente los mismos datos y parámetros.

### Para auditoría estadística
Exigir:
- separación temporal entre entrenamiento y prueba;
- datos históricos trazables;
- comparación contra una línea base;
- métricas MAE/RMSE;
- registro de cambios de modelo.

### Para auditoría electoral
Tratar `src/electoral.py` como fuente de verdad y no reintroducir implementaciones de D'Hondt en scripts, referencias o notebooks.

### Para desarrollo
Antes de crear otro módulo de predicción, coalición o asignación electoral, añadir primero un test que demuestre por qué la lógica no pertenece a la fuente de verdad existente.

## 8. Límites del informe

Este informe **no certifica resultados electorales ni predicciones políticas**. Certifica únicamente las deficiencias arquitectónicas observadas y las medidas de simplificación realizadas en esta rama.

Los resultados sustantivos deben validarse con datos primarios y con la suite completa de CI.
