# Fuentes, estado y límites

## Fuentes primarias congeladas
1. Real Decreto 806/2026, BOE-A-2026-20742, publicado 06-10-2026.
2. LOREG, Ley Orgánica 5/1985, versión vigente.
3. Resultados oficiales 23J 2023, Junta Electoral Central/BOE-A-2023-18907.
4. Ministerio del Interior — Resultados Electorales.
5. Encuestas 2026: fuente primaria, publicación, campo, muestra, modo, voto y escaños publicados.

## Estado
- Magnitudes 2026: AUDITADAS contra BOE.
- Motor legal: IMPLEMENTADO.
- Base territorial 2023: PARCIALMENTE INCORPORADA.
- Matriz oficial 2023 partido×circunscripción: PENDIENTE.
- Inventario completo de encuestas 2026: PENDIENTE.
- Corrección histórica de sesgos: NO APLICADA hasta backtesting OOS.
- Territorialización reproducible 2026: NO CERRADA mientras falten matrices comparables.
- Resultado final 2026: NO RECONSTRUIBLE DE FORMA AUDITADA con los datos actualmente incorporados.

## Regla de publicación
Mientras falte cualquier dato esencial, el proyecto solo puede declarar AUDITADO CON LIMITACIONES, nunca 100% auditado ni resultado definitivo.


## Bibliografía oficial estructurada

La bibliografía canónica de procedencia queda integrada en `docs/BIBLIOGRAFIA_OFICIAL_ESTRUCTURADA.md`.

### Jerarquía de evidencia
- **PRIMARY:** Interior, JEC, BOE, CIS, INE y organismos electorales territoriales competentes.
- **LEGAL:** BOE y normativa electoral vigente.
- **METHODOLOGICAL:** fichas técnicas, microdatos y documentación metodológica oficial.
- **SECONDARY:** medios/agregadores; solo descubrimiento o contraste.
- **AUXILIARY:** contexto y validación cruzada.

### Trazabilidad obligatoria
Cada dato materializado debe conservar, cuando exista: `source_id`, URL, organismo, tipo, fechas, versión/identificador, `sha256`, transformación, ámbito territorial, nivel de evidencia, validación e incidencias.

### Regla crítica
La presencia de una fuente en la bibliografía no implica que sus datos estén ya materializados en `data/` ni conectados al pipeline. El estado de certificación no cambia hasta completar esa materialización y validación reproducible.

### Regla de precedencia
Ante discrepancias, prevalece la fuente oficial competente por autoridad, fecha y ámbito. No se promedian discrepancias ni se sustituyen fuentes primarias por medios.

