# Estrategia de repositorio: monorepo frente a multirrepo

## Decisión actual
COALICIÓN mantiene el repositorio canónico `DrRomanSalvador/coalicion` como fuente de verdad. No crear repositorios satélite ni duplicar contratos, workflows o lógica para imitar a grandes empresas. La arquitectura actual debe evolucionar según límites de dominio y evidencia operativa.

## Cuándo mantener un monorepo
Mantener módulos en el mismo repositorio cuando comparten contratos, datos, releases coordinadas, seguridad, ownership o pruebas de integración. Ventajas: cambios atómicos entre capas, una fuente de verdad, auditoría conjunta y menor deriva de versiones.

## Cuándo considerar multirrepo
Separar un componente solo si hay evidencia de al menos una necesidad persistente: ciclo de release independiente, equipo/propietario y permisos distintos, límites de seguridad o cumplimiento diferentes, escala de CI que justifique el coste, o contrato estable que permita evolucionar sin cambios coordinados constantes.

Antes de dividir:
1. Definir bounded context, dueño, API y contrato de datos.
2. Medir duración de CI, frecuencia de cambios coordinados, fallos de integración y costes operativos.
3. Diseñar versionado, compatibilidad, provenance, publicación de artefactos, dependencias y rollback.
4. Probar una migración reversible y documentarla como ADR.
5. Confirmar que la separación reduce complejidad total; si solo mueve complejidad entre repositorios, no dividir.

## Estructura lógica recomendada
- `src/`, `scripts/`, `tests/`: implementación, herramientas y pruebas canónicas.
- `docs/`: contratos, ADRs, runbooks, métricas y arquitectura.
- `.github/workflows/`: pipelines versionados con permisos mínimos y concurrencia declarada.
- `artifacts/`, `ci_evidence/`: evidencia materializada conforme a la política del proyecto; no almacenar secretos ni duplicados derivados innecesarios.
- `telegram-worker/`: Worker y sus pruebas/dependencias, como módulo desplegable con su propio pipeline dentro del mismo repo mientras el acoplamiento y ownership actuales lo justifiquen.

No se impone una estructura por nombre si el repositorio ya tiene un equivalente canónico: primero inspeccionar y reutilizar.

## Commits y métricas de escala
- El tamaño del historial depende de años, equipos, automatización y estrategia de integración; no existe una cifra de commits que garantice calidad.
- Preferir commits coherentes, PR pequeñas revisables y mensajes descriptivos. El squash es una opción, no una regla universal: preservar commits cuando su secuencia tenga valor de auditoría o depuración.
- Evaluar rendimiento del flujo con DORA, duración de CI, flakiness, defectos escapados, rollback, vulnerabilidades y tiempo de revisión.
- No copiar cifras de Linux, Chromium u organizaciones privadas como objetivos para COALICIÓN. Los números sin una fuente y fecha verificables no son una línea base.
- Automatizar lo repetible sin generar commits de ruido ni ocultar quién/qué produjo una modificación.

## Referencias operativas
- Obligaciones de agentes: `AGENTS.md`
- Principios de ingeniería: `docs/ENGINEERING_CHARTER.md`
- DORA y sus limitaciones: `docs/DORA_METRICS.md`
- Protección de `main`: `docs/BRANCH_PROTECTION.md`
