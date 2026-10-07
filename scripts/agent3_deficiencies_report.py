#!/usr/bin/env python3
"""Genera los informes de deficiencias del Agente 3.

El script escribe tres documentos de auditoría sin afirmar resultados de CI
o certificación que no hayan sido verificados.
"""
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "audits"

REPORTS = {
    "deficiencies_found.md": """# INFORME DE DEFICIENCIAS ENCONTRADAS

**Agente:** Auditor 3  
**Rama:** `refactor/minimal-domain-architecture`  
**Commit:** `e98150e`

## Resumen

Se detectaron 8 módulos de implementación que introducían duplicidad: cuatro
módulos estadísticos y cuatro módulos de lógica paralela. La corrección concentra
la predicción estadística en `src/prediction.py` y mantiene `electoral.py` y
`coalition.py` como fuentes de verdad protegidas.

### Impacto cuantificado

- 8 archivos de implementación eliminados.
- 4 dominios estadísticos fusionados en 1 módulo.
- 3 invariantes de unicidad arquitectónica.
- 4 invariantes matemáticos.
- 4 archivos protegidos fuera del alcance del Agente 3.

## Duplicidades

### Predicción

- `bias_filter.py`
- `calibration.py`
- `poll_error.py`
- `context_corrections.py`

Todos fueron fusionados realmente en `prediction.py`.

### Coaliciones y escenarios

- `coalition_value.py`
- `scenarios.py`
- `decision_engine.py`

Se eliminaron como implementaciones paralelas; `coalition.py` permanece protegido.

### D'Hondt

`electoral_reference.py` duplicaba la lógica electoral de `electoral.py` y fue eliminado.

## Deficiencias funcionales

Se identificó un riesgo de agrupación contextual por gobierno: usar el contexto
de la observación objetivo para representar todo el entrenamiento podía mezclar
gobiernos históricos. La implementación consolidada deriva el contexto de cada
fila de entrenamiento.

El uso de `round(voto * factor)` se conserva, pero no se declara aquí como bug
demostrado: requiere una auditoría matemática específica antes de cambiarlo.

## Tests

`tests/test_architecture_invariants.py` protege:

- unicidad de D'Hondt;
- unicidad de coaliciones;
- unicidad de predicción;
- conservación de escaños;
- suma de shares;
- conservación de votos al combinar;
- recálculo de escaños de coalición.

## Límites

Este informe describe arquitectura y correcciones de código. No certifica
predicciones, resultados electorales ni evidencia primaria.
""",
    "corrections_applied.md": """# CORRECCIONES APLICADAS

## Fusión

Código real de `bias_filter.py`, `calibration.py`, `poll_error.py` y
`context_corrections.py` integrado en `src/prediction.py`.

No se conservaron wrappers hacia los módulos antiguos.

## Eliminaciones

- `src/bias_filter.py`
- `src/calibration.py`
- `src/poll_error.py`
- `src/context_corrections.py`
- `src/coalition_value.py`
- `src/scenarios.py`
- `src/decision_engine.py`
- `src/electoral_reference.py`

## Actualizaciones

Los consumidores relevantes importan desde `src.prediction`.

Se añadió `tests/test_architecture_invariants.py`.

## Protegidos

No se modificaron como parte de esta fase:

- `src/seec_bayesian.py`
- `tests/test_seec_bayesian.py`
- `src/coalition.py`
- `src/electoral.py`

## Estado

CI nuevo para el commit final: pendiente. No se declara PASS sin ejecución.
""",
    "remaining_issues.md": """# DEFICIENCIAS RESTANTES

## Alta prioridad

1. Ejecutar la suite completa en CI.
2. Ejecutar el pipeline OOS histórico con datos trazables.
3. Comparar resultados antes/después con inputs idénticos.

## Media prioridad

4. Auditar específicamente la política de redondeo de votos escalados.
5. Ampliar el inventario de APIs protegidas contra duplicación.
6. Verificar trazabilidad de los datos históricos.

## Integración

7. Integrar cambios de otros agentes solo respetando sus fronteras.
8. Completar certificación independiente con evidencia primaria.

## Restricciones

No reintroducir implementaciones paralelas de D'Hondt, coaliciones o predicción.
No modificar SEEC ni `electoral.py` dentro de esta fase.

## Estado

Arquitectura: simplificada.  
Duplicidades declaradas: eliminadas.  
CI final: pendiente.  
Backtest/OOS completo: pendiente.  
Certificación externa: pendiente.
"""
}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    for name, body in REPORTS.items():
        header = f"\n\n*Generado por `scripts/agent3_deficiencies_report.py`: {stamp}*\n"
        (OUT / name).write_text(body + header, encoding="utf-8")
        print(f"OK {OUT / name}")

if __name__ == "__main__":
    main()
