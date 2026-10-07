# Problemas pendientes

**Agente:** Auditor 3  
**Rama:** `refactor/minimal-domain-architecture`  
**Estado:** pendientes de validación posterior

## Prioridad alta

### 1. Ejecutar la suite completa en CI

La simplificación todavía necesita una ejecución CI limpia del commit final.

**Criterio de cierre:** tests contractuales, unitarios y arquitectónicos en verde.

### 2. Ejecutar el pipeline histórico OOS

La arquitectura contiene herramientas OOS, pero su existencia no demuestra que el pipeline completo haya sido ejecutado con datos históricos auditables.

**Criterio de cierre:** dataset identificado, fechas de entrenamiento/prueba documentadas y métricas reproducibles.

### 3. Verificar equivalencia funcional

Comparar resultados de la versión anterior y la consolidada con idénticos inputs.

**Criterio de cierre:** cualquier diferencia quede explicada y documentada.

## Prioridad media

### 4. Validar la política de redondeo

La conversión de votos escalados utiliza `round()`.

No se recomienda cambiarla sin una decisión explícita porque puede modificar resultados de asignación.

### 5. Completar pruebas de unicidad

Los tests actuales buscan nombres de funciones conocidos. Debe ampliarse el inventario si aparecen nuevas APIs de coalición o predicción.

**Criterio de cierre:** catálogo explícito de funciones canónicas y test que detecte cualquier segunda definición.

### 6. Validar datos históricos

Los análisis de error dependen de observaciones documentadas: elección, fecha, partido, encuesta, resultado, casa y metadatos de contexto.

**Criterio de cierre:** trazabilidad de cada observación hasta su fuente primaria.

## Prioridad de integración

### 7. Integrar ramas de otros agentes solo después de validar contratos

El Agente 3 no debe absorber cambios de:
- Agente 1 / SEEC;
- Agente 2 / calculadora de coaliciones.

La integración debe hacerse respetando las fronteras de propiedad.

### 8. Certificación externa

La certificación de resultados electorales requiere evidencia primaria independiente. Este informe no sustituye esa certificación.

## No hacer

- No reintroducir `electoral_reference.py`.
- No crear otro motor de predicción paralelo.
- No crear otra calculadora de coaliciones.
- No modificar `electoral.py` dentro de esta fase.
- No modificar SEEC dentro de esta fase.

## Estado final

**Arquitectura:** simplificada.  
**Duplicidades declaradas:** eliminadas.  
**CI final:** pendiente.  
**Backtest/OOS completo:** pendiente.  
**Certificación de datos/resultados:** pendiente.
