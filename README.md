undefined

---

# PUNTO DE ENTRADA ÚNICO

**Contrato obligatorio para cualquier IA:** `CONTRATO_MAESTRO_IA.md`

Antes de tocar datos, código o resultados, leer el contrato y este README.

## Estado operativo 2026-10-06

- Permiso de repositorio: escritura y administración disponibles.
- Magnitudes electorales 2026: incorporadas en `data/2026_circunscripciones_oficiales.csv`.
- Motor electoral determinista: `src/electoral.py`.
- Pruebas mínimas: `tests/test_electoral.py`.
- Fuentes y limitaciones: `docs/SOURCES_AND_STATUS.md`.
- Plan de pruebas: `docs/TEST_PLAN.md`.

**No existe todavía un resultado 2026 auditado.** La matriz oficial completa partido×circunscripción de 2023, el inventario consolidado de encuestas y la territorialización reproducible deben incorporarse y validarse antes de cerrar la simulación.

## Regla de continuidad

El repositorio es la memoria operativa del proyecto. Ninguna IA debe depender de conversaciones anteriores para conocer las reglas. Toda modificación posterior debe ser reproducible, versionada y trazable.
