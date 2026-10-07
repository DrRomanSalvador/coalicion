# Correcciones aplicadas

**Agente:** Auditor 3  
**Rama:** `refactor/minimal-domain-architecture`  
**Commit:** `e98150e`

## 1. Fusión real

Se trasladó código funcional de:

- `bias_filter.py`
- `calibration.py`
- `poll_error.py`
- `context_corrections.py`

a `src/prediction.py`.

No se dejaron wrappers que importasen los módulos antiguos.

También se trasladó `PollObservation` a `prediction.py` para evitar conservar una dependencia artificial en otro módulo.

## 2. Eliminación de duplicados

Se eliminaron:

- `coalition_value.py`
- `scenarios.py`
- `decision_engine.py`
- `electoral_reference.py`

La calculadora protegida `coalition.py` no fue modificada.

La implementación congelada `electoral.py` tampoco fue modificada.

## 3. Consumidores actualizados

`scripts/analyze_poll_error.py` y `src/evidence_certificate.py` utilizan ahora `src.prediction` para `PollObservation` y las funciones estadísticas correspondientes.

## 4. Tests

Se añadió `tests/test_architecture_invariants.py`.

Comprueba unicidad de implementación y las invariantes matemáticas exigidas por la arquitectura.

También se conserva el test diferencial electoral sin utilizar `electoral_reference.py`.

## 5. Verificación de referencias

Se revisaron los archivos Python de `src/`, `tests/` y `scripts/` de la rama buscando referencias a los módulos eliminados.

No se encontraron imports activos hacia:

- `bias_filter`
- `calibration`
- `poll_error`
- `context_corrections`
- `coalition_value`
- `scenarios`
- `decision_engine`
- `electoral_reference`

## 6. Protección de otros agentes

No se incorporaron cambios a:

- `src/seec_bayesian.py`
- `tests/test_seec_bayesian.py`
- `src/coalition.py`
- `src/electoral.py`

## 7. Estado de CI

En el momento de generar este informe no se dispone de una ejecución CI nueva asociada al commit `e98150e`.

Por tanto, el estado correcto es **PENDIENTE DE CI**, no PASS.

## 8. Resultado

La simplificación elimina ocho implementaciones/módulos paralelos y deja una arquitectura más fácil de inspeccionar:

- electoral → `electoral.py`
- coalición → `coalition.py`
- predicción estadística → `prediction.py`
